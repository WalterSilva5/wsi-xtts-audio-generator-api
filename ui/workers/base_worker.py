"""
Base worker class for background operations.
"""
from PySide6.QtCore import QThread, Signal, QMutex


class BaseWorker(QThread):
    """
    Base class for all worker threads.
    Provides common functionality for progress reporting and cancellation.
    """

    # Common signals
    started_signal = Signal()
    progress = Signal(int, str)  # percent, message
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel_requested = False
        self._mutex = QMutex()

    def cancel(self) -> None:
        """Request cancellation of the operation."""
        self._mutex.lock()
        self._cancel_requested = True
        self._mutex.unlock()

    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        self._mutex.lock()
        cancelled = self._cancel_requested
        self._mutex.unlock()
        return cancelled

    def reset(self) -> None:
        """Reset the worker state for reuse."""
        self._mutex.lock()
        self._cancel_requested = False
        self._mutex.unlock()

    def report_progress(self, percent: int, message: str) -> None:
        """Emit progress signal."""
        self.progress.emit(percent, message)
