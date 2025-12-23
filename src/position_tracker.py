import time
import csv
import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from utils.log_watcher import LogTracker


class BeaconType(Enum):
    STATIONARY = "stationary"
    MOBILE = "mobile"
    UNKNOWN = "unknown"


@dataclass
class PositionSample:
    timestamp: float
    x: float
    y: float
    z: float


@dataclass
class BeaconState:
    beacon_id: int
    beacon_type: BeaconType
    history: deque = field(default_factory=lambda: deque(maxlen=50))
    last_seen: float = 0.0
    ema_x: Optional[float] = None
    ema_y: Optional[float] = None
    ema_z: Optional[float] = None


class PositionTrackerException(Exception):
    pass


class PositionTracker:
    MIN_MOBILE_MOVEMENT = 0.01  # meters
    EMA_ALPHA = 0.3

    WARN_INTERVAL = 5.0
    RESTART_TIMEOUT = 60.0
    EXCEPTION_TIMEOUT = 120.0

    def __init__(self, use_ema: bool = True):
        self.use_ema = use_ema

        self.log_tracker = LogTracker()
        self.current_log: Optional[Path] = None
        self.file_offset = 0

        self.beacons: Dict[int, BeaconState] = {}
        self.beacon_types: Dict[int, BeaconType] = {}

        self.last_data_time = time.monotonic()
        self.last_warn_time = 0.0

    def update(self):
        self._check_log_switch()
        self._read_new_data()
        self._check_timeouts()

    def get_mobile_positions(self) -> Dict[int, PositionSample]:
        return {
            bid: b.history[-1]
            for bid, b in self.beacons.items()
            if b.beacon_type == BeaconType.MOBILE and b.history
        }

    def get_stationary_map(self) -> Dict[int, PositionSample]:
        return {
            bid: b.history[-1]
            for bid, b in self.beacons.items()
            if b.beacon_type == BeaconType.STATIONARY and b.history
        }

    def _check_log_switch(self):
        new_log = self.log_tracker.update()
        if new_log and new_log != self.current_log:
            print(f"[INFO] Switching to new log: {new_log.name}")
            self.current_log = new_log
            self.file_offset = 0
            self.beacons.clear()
            self.beacon_types = self._parse_beacon_types(new_log)
            self.last_data_time = time.monotonic()

    def _parse_beacon_types(self, log_path: Path) -> Dict[int, BeaconType]:
        beacon_types: Dict[int, BeaconType] = {}
        current_beacon_id = None

        with log_path.open("r", encoding="latin-1", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                if line[0].isdigit():
                    break

                if line.startswith("[beacon"):
                    try:
                        current_beacon_id = int(line.split()[1].strip("]"))
                    except Exception:
                        current_beacon_id = None
                    continue

                if current_beacon_id is not None and line.startswith("Hedgehog_mode"):
                    value = line.split("=")[1].strip()
                    beacon_types[current_beacon_id] = (
                        BeaconType.MOBILE if value == "1" else BeaconType.STATIONARY
                    )
                    current_beacon_id = None

        return beacon_types

    def _read_new_data(self):
        if not self.current_log:
            return

        data_seen = False

        with self.current_log.open("r", encoding="latin-1", errors="ignore") as f:
            f.seek(self.file_offset)
            reader = csv.reader(f)

            for row in reader:
                if len(row) >= 5:
                    data_seen = True

                self._process_row(row)

            self.file_offset = f.tell()

        if data_seen:
            self.last_data_time = time.monotonic()

    def _process_row(self, row: list[str]) -> None:
        if len(row) < 8:
            return

        try:
            line_type = int(row[2])
            data_code = int(row[3])
            beacon_id = int(row[4])
        except ValueError:
            return

        if line_type != 41:
            return

        beacon_type = self.beacon_types.get(beacon_id, BeaconType.UNKNOWN)

        if data_code in (17, 129):
            self._handle_position_row(row, beacon_type)
        elif data_code == 18:
            self._handle_position_row(row, BeaconType.STATIONARY)

    def _handle_position_row(self, row: list[str], beacon_type: BeaconType) -> None:
        try:
            beacon_id = int(row[4])
            raw_x = float(row[5])
            raw_y = float(row[6])
            raw_z = float(row[7])
        except (ValueError, IndexError):
            return

        now = time.monotonic()

        beacon = self.beacons.get(beacon_id)
        if beacon is None:
            beacon = BeaconState(beacon_id, beacon_type)
            self.beacons[beacon_id] = beacon

        beacon.last_seen = now

        if beacon.beacon_type == BeaconType.MOBILE and self.use_ema:
            if beacon.ema_x is None:
                beacon.ema_x = raw_x
                beacon.ema_y = raw_y
                beacon.ema_z = raw_z
            else:
                a = self.EMA_ALPHA
                beacon.ema_x = a * raw_x + (1 - a) * beacon.ema_x
                beacon.ema_y = a * raw_y + (1 - a) * beacon.ema_y
                beacon.ema_z = a * raw_z + (1 - a) * beacon.ema_z

            x, y, z = beacon.ema_x, beacon.ema_y, beacon.ema_z
        else:
            x, y, z = raw_x, raw_y, raw_z

        sample = PositionSample(now, x, y, z)
        history = beacon.history

        if history:
            last = history[-1]

            if beacon.beacon_type == BeaconType.MOBILE:
                if self._distance(last, sample) < self.MIN_MOBILE_MOVEMENT:
                    history[-1] = PositionSample(now, last.x, last.y, last.z)
                    return
            else:
                history[-1] = PositionSample(now, last.x, last.y, last.z)
                return

        history.append(sample)

    def _distance(self, a: PositionSample, b: PositionSample) -> float:
        return math.sqrt(
            (a.x - b.x) ** 2 +
            (a.y - b.y) ** 2 +
            (a.z - b.z) ** 2
        )

    def _check_timeouts(self):
        now = time.monotonic()
        since_data = now - self.last_data_time

        if since_data >= self.WARN_INTERVAL:
            if now - self.last_warn_time >= self.WARN_INTERVAL:
                print(f"[WARN] No new Marvelmind data for {since_data:.1f}s")
                self.last_warn_time = now

        if since_data >= self.RESTART_TIMEOUT:
            print("[INFO] Restarting tracker due to Marvelmind silence")
            self.file_offset = 0
            self.beacons.clear()
            self.last_data_time = now

        if since_data >= self.EXCEPTION_TIMEOUT:
            raise PositionTrackerException(
                "No Marvelmind data received for 120 seconds"
            )
