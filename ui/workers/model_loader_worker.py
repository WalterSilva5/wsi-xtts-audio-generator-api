"""
Worker for loading the TTS model in background.
"""
from PySide6.QtCore import Signal

from ui.workers.base_worker import BaseWorker
from src.core.services.tts_service import TTSService


class ModelLoaderWorker(BaseWorker):
    """
    Worker thread for loading the TTS model.
    Model loading is a heavy operation that should not block the UI.
    """

    # Signals
    finished = Signal(bool)  # success

    def __init__(self, tts_service: TTSService, parent=None):
        super().__init__(parent)
        self._tts_service = tts_service

    def run(self) -> None:
        """Execute model loading in background thread."""
        self.started_signal.emit()
        self.reset()

        try:
            # Set progress callback
            self._tts_service.set_progress_callback(
                lambda p, m: self.report_progress(p, m)
            )

            # Load the model
            success = self._tts_service.load_model()

            # Check for cancellation
            if self.is_cancelled():
                self._tts_service.unload_model()
                self.finished.emit(False)
                return

            self.finished.emit(success)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False)


class ModelUnloaderWorker(BaseWorker):
    """
    Worker thread for unloading the TTS model.
    """

    finished = Signal()

    def __init__(self, tts_service: TTSService, parent=None):
        super().__init__(parent)
        self._tts_service = tts_service

    def run(self) -> None:
        """Execute model unloading in background thread."""
        self.started_signal.emit()

        try:
            self.report_progress(0, "Unloading model...")
            self._tts_service.unload_model()
            self.report_progress(100, "Model unloaded")
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()
