import logging
from pathlib import Path
from datetime import datetime

_LOGGER_INITIALIZED = False


def setup_logging(
    log_dir: Path,
    prefix: str = "marvelmind",
    keep_last: int = 3,
):
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = log_dir / f"{prefix}_{ts}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.FileHandler(log_path)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    _prune_old_logs(log_dir, prefix, keep_last)

    _LOGGER_INITIALIZED = True


def _prune_old_logs(log_dir: Path, prefix: str, keep_last: int):
    logs = sorted(
        log_dir.glob(f"{prefix}_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for old in logs[keep_last:]:
        try:
            old.unlink()
        except Exception:
            pass


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
