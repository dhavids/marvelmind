import time

from src.position_tracker import PositionTracker
from utils.plotter import PositionPlotter

tracker = PositionTracker(use_ema=True)
plotter = PositionPlotter(
    decay_seconds=20.0,
    trail_seconds=12.0,
    velocity_scale=0.5,
    show_pos=True,
)

last_printed = {}

while True:
    tracker.update()
    current = {}

    for bid, pos in tracker.get_mobile_positions().items():
        key = ("MOBILE", bid)
        value = (pos.x, pos.y, pos.z)
        current[key] = value

        if last_printed.get(key) != value:
            print(f"MOBILE {bid}: x={pos.x:.3f}, y={pos.y:.3f}, z={pos.z:.3f}")

        plotter.update("MOBILE", bid, pos.x, pos.y, pos.z)

    for bid, pos in tracker.get_stationary_map().items():
        key = ("STAT", bid)
        value = (pos.x, pos.y, pos.z)
        current[key] = value

        if last_printed.get(key) != value:
            print(f"STAT   {bid}: x={pos.x:.3f}, y={pos.y:.3f}, z={pos.z:.3f}")

        plotter.update("STAT", bid, pos.x, pos.y, pos.z)

    last_printed = current
    time.sleep(0.1)
