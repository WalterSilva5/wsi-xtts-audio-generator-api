"""
Worker for TTS synthesis operations.
"""
from PySide6.QtCore import Signal

from ui.workers.base_worker import BaseWorker
from src.core.services.tts_service import TTSService
from src.core.models.tts_request import SynthesisRequest, SynthesisResult, SynthesisStatus


class SynthesisWorker(BaseWorker):
    """
    Worker thread for TTS synthesis operations.
    Synthesis can take several seconds and should not block the UI.
    """

    # Signals
    finished = Signal(object)  # SynthesisResult

    def __init__(self, tts_service: TTSService, parent=None):
        super().__init__(parent)
        self._tts_service = tts_service
        self._request: SynthesisRequest = None

    def set_request(self, request: SynthesisRequest) -> None:
        """Set the synthesis request before starting."""
        self._request = request

    def cancel(self) -> None:
        """Request cancellation of synthesis."""
        super().cancel()
        self._tts_service.cancel_synthesis()

    def run(self) -> None:
        """Execute synthesis in background thread."""
        self.started_signal.emit()
        self.reset()

        if self._request is None:
            self.error.emit("No synthesis request set")
            self.finished.emit(SynthesisResult(
                status=SynthesisStatus.ERROR,
                error_message="No synthesis request set"
            ))
            return

        try:
            # Set progress callback
            self._tts_service.set_progress_callback(
                lambda p, m: self.report_progress(p, m)
            )

            # Perform synthesis
            result = self._tts_service.synthesize(self._request)

            # Check for cancellation
            if self.is_cancelled():
                result = SynthesisResult(status=SynthesisStatus.CANCELLED)

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(SynthesisResult(
                status=SynthesisStatus.ERROR,
                error_message=str(e)
            ))
