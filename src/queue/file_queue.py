"""File-based queue implementation with thread-safe operations."""
import os
import json
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from src.queue.models import QueueTask, TaskStatus


class FileQueue:
    """Thread-safe file-based queue for task persistence.

    Uses a JSON file to store tasks with file locking for concurrent access.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, queue_file: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(FileQueue, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, queue_file: str = None):
        if self._initialized:
            return

        self._file_lock = threading.RLock()

        if queue_file:
            self.queue_file = Path(queue_file)
        else:
            queue_dir = Path(__file__).parent.parent.parent / "data" / "queue"
            queue_dir.mkdir(parents=True, exist_ok=True)
            self.queue_file = queue_dir / "tasks.json"

        self._ensure_file_exists()
        self._initialized = True

    def _ensure_file_exists(self) -> None:
        """Ensure the queue file exists."""
        if not self.queue_file.exists():
            self.queue_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_tasks([])

    def _read_tasks(self) -> List[Dict[str, Any]]:
        """Read all tasks from file."""
        with self._file_lock:
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('tasks', [])
            except (json.JSONDecodeError, FileNotFoundError):
                return []

    def _write_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Write all tasks to file."""
        with self._file_lock:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'tasks': tasks,
                    'updated_at': datetime.utcnow().isoformat()
                }, f, indent=2, ensure_ascii=False)

    def add_task(self, task: QueueTask) -> str:
        """Add a task to the queue. Returns task ID."""
        tasks = self._read_tasks()
        tasks.append(task.to_dict())
        self._write_tasks(tasks)
        return task.id

    def get_task(self, task_id: str) -> Optional[QueueTask]:
        """Get a task by ID."""
        tasks = self._read_tasks()
        for task_data in tasks:
            if task_data.get('id') == task_id:
                return QueueTask.from_dict(task_data)
        return None

    def get_next_pending(self) -> Optional[QueueTask]:
        """Get the next pending task (FIFO)."""
        tasks = self._read_tasks()
        for task_data in tasks:
            if task_data.get('status') == TaskStatus.PENDING.value:
                return QueueTask.from_dict(task_data)
        return None

    def update_task(self, task: QueueTask) -> bool:
        """Update a task in the queue."""
        tasks = self._read_tasks()
        for i, task_data in enumerate(tasks):
            if task_data.get('id') == task.id:
                tasks[i] = task.to_dict()
                self._write_tasks(tasks)
                return True
        return False

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: str = None,
        result_file: str = None,
        progress: float = None
    ) -> bool:
        """Update task status and optional fields."""
        tasks = self._read_tasks()
        for i, task_data in enumerate(tasks):
            if task_data.get('id') == task_id:
                tasks[i]['status'] = status.value

                if status == TaskStatus.PROCESSING and not tasks[i].get('started_at'):
                    tasks[i]['started_at'] = datetime.utcnow().isoformat()

                if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    tasks[i]['completed_at'] = datetime.utcnow().isoformat()

                if error_message is not None:
                    tasks[i]['error_message'] = error_message

                if result_file is not None:
                    tasks[i]['result_file'] = result_file

                if progress is not None:
                    tasks[i]['progress'] = progress

                self._write_tasks(tasks)
                return True
        return False

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the queue."""
        tasks = self._read_tasks()
        original_len = len(tasks)
        tasks = [t for t in tasks if t.get('id') != task_id]

        if len(tasks) < original_len:
            self._write_tasks(tasks)
            return True
        return False

    def get_all_tasks(self, status: TaskStatus = None) -> List[QueueTask]:
        """Get all tasks, optionally filtered by status."""
        tasks = self._read_tasks()
        result = []

        for task_data in tasks:
            if status is None or task_data.get('status') == status.value:
                result.append(QueueTask.from_dict(task_data))

        return result

    def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        return len(self.get_all_tasks(TaskStatus.PENDING))

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        tasks = self._read_tasks()
        stats = {
            'total': len(tasks),
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0
        }

        for task in tasks:
            status = task.get('status', 'pending')
            if status in stats:
                stats[status] += 1

        return stats

    def clear_completed(self, older_than_hours: int = 24) -> int:
        """Remove completed/failed/cancelled tasks older than specified hours."""
        tasks = self._read_tasks()
        cutoff = datetime.utcnow()
        removed = 0

        def should_keep(task: Dict) -> bool:
            nonlocal removed
            status = task.get('status')
            if status not in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
                return True

            completed_at = task.get('completed_at')
            if completed_at:
                try:
                    completed_time = datetime.fromisoformat(completed_at)
                    hours_diff = (cutoff - completed_time).total_seconds() / 3600
                    if hours_diff < older_than_hours:
                        return True
                except ValueError:
                    return True

            removed += 1
            return False

        filtered_tasks = [t for t in tasks if should_keep(t)]

        if removed > 0:
            self._write_tasks(filtered_tasks)

        return removed

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self.get_task(task_id)
        if task and task.status == TaskStatus.PENDING.value:
            return self.update_task_status(task_id, TaskStatus.CANCELLED)
        return False
