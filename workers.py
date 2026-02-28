"""Background worker for running script functions without blocking the UI."""

from PyQt5.QtCore import QThread, pyqtSignal


class ScriptWorker(QThread):
    """Worker thread for running scripts without blocking UI."""

    finished = pyqtSignal(bool)
    log_message = pyqtSignal(str)
    progress_update = pyqtSignal(int, int, str)  # current, total, filename

    def __init__(self, script_func, *args, **kwargs):
        super().__init__()
        self.script_func = script_func
        self.args = args
        self.kwargs = kwargs
        self._stop_requested = False

    def stop(self) -> None:
        """Request the worker to stop."""
        self._stop_requested = True
        self.log_message.emit("⚠ Stop requested - cancelling operation...")

    def is_stop_requested(self) -> bool:
        """Check if stop was requested."""
        return self._stop_requested

    def run(self) -> None:
        """Execute the script function."""
        def log_callback(msg):
            if not self._stop_requested:
                self.log_message.emit(msg)

        def progress_callback(current, total, filename):
            if not self._stop_requested:
                self.progress_update.emit(current, total, filename)

        self.kwargs['log_callback'] = log_callback
        self.kwargs['progress_callback'] = progress_callback
        self.kwargs['is_stopped'] = lambda: self._stop_requested
        try:
            result = self.script_func(*self.args, **self.kwargs)
            if self._stop_requested:
                self.log_message.emit("✗ Operation cancelled by user")
                self.finished.emit(False)
            else:
                self.finished.emit(result)
        except Exception as e:
            if not self._stop_requested:
                self.log_message.emit(f"Error: {e}")
            self.finished.emit(False)
