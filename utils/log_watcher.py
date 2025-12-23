from pathlib import Path
from typing import Optional
from .paths import LOGS_DIR


def list_log_files() -> list[Path]:
    """
    Return all Marvelmind log files sorted chronologically.
    """
    if not LOGS_DIR.exists():
        raise FileNotFoundError(f"Logs directory does not exist: {LOGS_DIR}")

    logs = [
        p for p in LOGS_DIR.iterdir()
        if p.is_file() and p.name.endswith("__Marvelmind_log.csv")
    ]

    return sorted(logs)


def latest_log_file() -> Optional[Path]:
    """
    Return the most recent Marvelmind log file, or None if none exist.
    """
    logs = list_log_files()
    return logs[-1] if logs else None


class LogTracker:
    """
    Tracks the currently active Marvelmind log and detects when it changes.
    """

    def __init__(self):
        self._current_log: Optional[Path] = None

    def update(self) -> Optional[Path]:
        """
        Check for a new log file.
        Returns the new log path if changed, otherwise None.
        """
        latest = latest_log_file()

        if latest is None:
            return None

        if self._current_log is None or latest != self._current_log:
            self._current_log = latest
            return latest

        return None

    @property
    def current_log(self) -> Optional[Path]:
        return self._current_log

