"""
Worker for adding a new speaker in background.
"""
from PySide6.QtCore import Signal

from ui.workers.base_worker import BaseWorker
from src.core.services.tts_service import TTSService


class AddSpeakerWorker(BaseWorker):
    """
    Worker thread for adding a new speaker.
    Handles file copying and embedding generation in background.
    """

    # Signals
    progress = Signal(int, str)  # percent, message
    finished = Signal(bool, str)  # success, speaker_name or error message

    def __init__(self, tts_service: TTSService, parent=None):
        super().__init__(parent)
        self._tts_service = tts_service
        self._speaker_name: str = ""
        self._audio_file_path: str = ""

    def set_speaker_data(self, name: str, audio_file_path: str) -> None:
        """Set the speaker data to add."""
        self._speaker_name = name
        self._audio_file_path = audio_file_path

    def run(self) -> None:
        """Execute the speaker addition process."""
        try:
            self.progress.emit(0, "Starting...")

            if self._cancelled:
                self.finished.emit(False, "Cancelled")
                return

            success = self._tts_service.add_speaker(
                name=self._speaker_name,
                audio_file_path=self._audio_file_path,
                progress_callback=self._on_progress
            )

            if success:
                self.finished.emit(True, self._speaker_name)
            else:
                self.finished.emit(False, "Failed to add speaker")

        except Exception as e:
            self.finished.emit(False, str(e))

    def _on_progress(self, percent: int, message: str) -> None:
        """Handle progress updates from the service."""
        if not self._cancelled:
            self.progress.emit(percent, message)
