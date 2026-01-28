"""Queue consumer - processes tasks in background."""
import os
import time
import threading
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from src.queue.models import QueueTask, TaskStatus, TaskType
from src.queue.file_queue import FileQueue
from src.tts.xtts.dto.tts_dto import TtsDto
from src.tts.xtts.manager.tts_manager import TtsManager
from src.audio.converter import convert_audio


class QueueConsumer:
    """Background consumer that processes queue tasks.

    Implements a single-threaded consumer pattern that polls the queue
    and processes tasks sequentially.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(QueueConsumer, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.queue = FileQueue()
        self.tts_manager = TtsManager()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._poll_interval = 2.0
        self._on_task_complete: Optional[Callable] = None
        self._on_task_error: Optional[Callable] = None

        output_dir = Path(__file__).parent.parent.parent / "data" / "queue" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

        self._initialized = True

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """Start the consumer thread."""
        if self.is_running:
            return False

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[QueueConsumer] Started")
        return True

    def stop(self) -> None:
        """Stop the consumer thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        print("[QueueConsumer] Stopped")

    def set_callbacks(
        self,
        on_complete: Callable[[QueueTask], None] = None,
        on_error: Callable[[QueueTask, Exception], None] = None
    ) -> None:
        """Set callback functions for task events."""
        self._on_task_complete = on_complete
        self._on_task_error = on_error

    def _run_loop(self) -> None:
        """Main consumer loop."""
        while self._running:
            try:
                task = self.queue.get_next_pending()

                if task:
                    self._process_task(task)
                else:
                    time.sleep(self._poll_interval)

            except Exception as e:
                print(f"[QueueConsumer] Error in loop: {e}")
                time.sleep(self._poll_interval)

    def _process_task(self, task: QueueTask) -> None:
        """Process a single task."""
        print(f"[QueueConsumer] Processing task {task.id} ({task.task_type})")

        self.queue.update_task_status(
            task.id,
            TaskStatus.PROCESSING,
            progress=0.0
        )

        try:
            if task.task_type == TaskType.SYNTHESIS.value:
                self._process_synthesis_task(task)
            elif task.task_type == TaskType.BATCH_SYNTHESIS.value:
                self._process_batch_synthesis_task(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")

            if self._on_task_complete:
                updated_task = self.queue.get_task(task.id)
                self._on_task_complete(updated_task)

        except Exception as e:
            print(f"[QueueConsumer] Task {task.id} failed: {e}")
            self.queue.update_task_status(
                task.id,
                TaskStatus.FAILED,
                error_message=str(e)
            )

            if self._on_task_error:
                self._on_task_error(task, e)

    def _process_synthesis_task(self, task: QueueTask) -> None:
        """Process a synthesis task."""
        payload = task.payload

        dto = TtsDto(
            text=payload.get('text', ''),
            voice=payload.get('voice', 'voice'),
            lang_code=payload.get('lang_code', 'en'),
            temperature=payload.get('temperature', 0.65),
            length_penalty=payload.get('length_penalty', 1.0),
            repetition_penalty=payload.get('repetition_penalty', 12.0),
            top_k=payload.get('top_k', 35),
            top_p=payload.get('top_p', 0.75),
            speed=payload.get('speed', 0.95),
            do_sample=payload.get('do_sample', True),
            enable_text_splitting=payload.get('enable_text_splitting', True)
        )

        self.queue.update_task_status(task.id, TaskStatus.PROCESSING, progress=10.0)

        audio_bytes = self.tts_manager.model.synthesize_audio(dto)

        self.queue.update_task_status(task.id, TaskStatus.PROCESSING, progress=80.0)

        output_format = payload.get('output_format', 'wav')
        if output_format != 'wav':
            audio_bytes = convert_audio(audio_bytes, output_format)

        output_file = self.output_dir / f"{task.id}.{output_format}"
        with open(output_file, 'wb') as f:
            f.write(audio_bytes)

        self.queue.update_task_status(
            task.id,
            TaskStatus.COMPLETED,
            result_file=str(output_file),
            progress=100.0
        )

        print(f"[QueueConsumer] Task {task.id} completed: {output_file}")

    def _process_batch_synthesis_task(self, task: QueueTask) -> None:
        """Process a batch synthesis task."""
        import zipfile
        import io
        import json

        payload = task.payload
        items = payload.get('items', [])
        default_voice = payload.get('default_voice', 'voice')
        default_lang_code = payload.get('default_lang_code', 'en')
        output_format = payload.get('output_format', 'wav')

        total_items = len(items)
        results = []
        audio_files = []

        for idx, item in enumerate(items):
            progress = (idx / total_items) * 90
            self.queue.update_task_status(task.id, TaskStatus.PROCESSING, progress=progress)

            voice = item.get('voice') or default_voice
            lang_code = item.get('lang_code') or default_lang_code
            text = item.get('text', '')

            try:
                dto = TtsDto(
                    text=text,
                    voice=voice,
                    lang_code=lang_code
                )

                audio_bytes = self.tts_manager.model.synthesize_audio(dto)

                if output_format != 'wav':
                    audio_bytes = convert_audio(audio_bytes, output_format)

                filename = f"audio_{idx:03d}.{output_format}"
                audio_files.append((filename, audio_bytes))

                results.append({
                    'index': idx,
                    'success': True,
                    'text': text[:50] + '...' if len(text) > 50 else text
                })

            except Exception as e:
                results.append({
                    'index': idx,
                    'success': False,
                    'text': text[:50] + '...' if len(text) > 50 else text,
                    'error': str(e)
                })

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, audio_data in audio_files:
                zf.writestr(filename, audio_data)

            manifest = {
                'total': total_items,
                'successful': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success')),
                'results': results
            }
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))

        output_file = self.output_dir / f"{task.id}.zip"
        with open(output_file, 'wb') as f:
            f.write(zip_buffer.getvalue())

        self.queue.update_task_status(
            task.id,
            TaskStatus.COMPLETED,
            result_file=str(output_file),
            progress=100.0
        )

        print(f"[QueueConsumer] Batch task {task.id} completed: {output_file}")


_consumer_instance: Optional[QueueConsumer] = None


def get_consumer() -> QueueConsumer:
    """Get or create the global consumer instance."""
    global _consumer_instance
    if _consumer_instance is None:
        _consumer_instance = QueueConsumer()
    return _consumer_instance


def start_consumer() -> bool:
    """Start the global consumer."""
    return get_consumer().start()


def stop_consumer() -> None:
    """Stop the global consumer."""
    get_consumer().stop()
