import csv
import time
from pathlib import Path
from typing import Iterable, Tuple

from utils.logging_setup import get_logger
logger = get_logger(__name__)

from src.position_tracker import PositionSample, BeaconType


class PositionCSVWriter:
    def __init__(self, output_path: Path, rate_hz: float = 5.0):
        self._file = output_path.open("w", newline="")
        self._writer = csv.writer(self._file)

        self._period = 1.0 / rate_hz
        self._last_write_ts = 0.0

        self._writer.writerow([
            "ts_pub",
            "ts_mm",
            "ts_read",
            "beacon_type",
            "beacon_id",
            "x",
            "y",
            "z",
        ])
        self._file.flush()

        logger.info(
            "CSV writer opened at %s (rate %.1f Hz)",
            output_path,
            rate_hz,
        )

    def write_snapshot(
        self,
        ts_pub: float,
        beacons: Iterable[Tuple[BeaconType, int, PositionSample]],
    ) -> None:
        now = time.monotonic()

        if now - self._last_write_ts < self._period:
            logger.debug("CSV write throttled")
            return

        rows = []
        for beacon_type, beacon_id, pos in beacons:
            rows.append([
                f"{ts_pub:.6f}",
                f"{pos.ts_mm:.6f}" if pos.ts_mm is not None else "",
                f"{pos.ts_read:.6f}",
                beacon_type.value,
                beacon_id,
                f"{pos.x:.6f}",
                f"{pos.y:.6f}",
                f"{pos.z:.6f}",
            ])

        if not rows:
            logger.debug("CSV snapshot empty, skipping")
            return

        self._writer.writerows(rows)
        self._file.flush()

        self._last_write_ts = now

        logger.debug(
            "CSV snapshot written: %d beacons at ts_pub=%.6f",
            len(rows),
            ts_pub,
        )

    def close(self) -> None:
        logger.info("Closing CSV writer")
        self._file.close()
