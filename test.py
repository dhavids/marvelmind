import time
from pathlib import Path
from typing import Dict, Tuple

from utils.logging_setup import setup_logging, get_logger

# Logging setup (must be first)
setup_logging(Path("logs"))
logger = get_logger("test")

from src.position_tracker import PositionTracker
from utils.plotter import PositionPlotter
from utils.csv_writer import PositionCSVWriter
from utils.broadcaster import PositionBroadcaster
from utils.sink import PositionSink

# Helpers for console printing (only on change)
EPS = 1e-4


def _pos_tuple(p) -> Tuple[float, float, float]:
    return (round(p.x, 4), round(p.y, 4), round(p.z, 4))


def _snapshot(tracker: PositionTracker) -> Dict[Tuple[str, int], Tuple[float, float, float]]:
    snap = {}

    for bid, pos in tracker.get_mobile_positions().items():
        snap[("MOBILE", bid)] = _pos_tuple(pos)

    for bid, pos in tracker.get_stationary_map().items():
        snap[("STAT", bid)] = _pos_tuple(pos)

    return snap


def _print_snapshot(snap: Dict[Tuple[str, int], Tuple[float, float, float]]) -> None:
    for (label, bid), (x, y, z) in sorted(snap.items()):
        print(f"{label:<6} {bid}: x={x:.3f}, y={y:.3f}, z={z:.3f}")


# Component setup
tracker = PositionTracker(use_ema=True)

csv_writer = PositionCSVWriter(Path("positions_out.csv"))
broadcaster = PositionBroadcaster(port=5555, rate_hz=20)
broadcaster.start()

sink = PositionSink(
    csv_writer=csv_writer,
    broadcaster=broadcaster,
)

plotter = PositionPlotter(
    trail_seconds=50.0,
    decay_seconds=30.0,
    refresh_interval=0.2,
    show_pos=True,
)

logger.info("Test loop started")

last_snapshot: Dict[Tuple[str, int], Tuple[float, float, float]] = {}

# Main loop
try:
    while True:
        tracker.update()

        # Publish to CSV + broadcaster
        sink.publish(tracker)

        # Update plotter (always)
        for bid, pos in tracker.get_mobile_positions().items():
            plotter.update("MOBILE", bid, pos.x, pos.y, pos.z)

        for bid, pos in tracker.get_stationary_map().items():
            plotter.update("STATIONARY", bid, pos.x, pos.y, pos.z)

        # Console printing only when data changes
        current_snapshot = _snapshot(tracker)
        if current_snapshot != last_snapshot:
            _print_snapshot(current_snapshot)
            last_snapshot = current_snapshot

        time.sleep(0.02)

except KeyboardInterrupt:
    logger.info("Shutting down test loop")

finally:
    broadcaster.stop()
    csv_writer.close()
    plotter.close()
    logger.info("Shutdown complete")
