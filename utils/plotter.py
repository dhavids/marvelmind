import time
import math
from collections import deque
from typing import Dict, Tuple

import matplotlib
matplotlib.use("TkAgg")

import matplotlib.pyplot as plt


class PositionPlotter:
    def __init__(
        self,
        decay_seconds: float = 15.0,
        trail_seconds: float = 10.0,
        refresh_interval: float = 0.2,
        velocity_scale: float = 1.0,
        show_pos: bool = False,
    ):
        self.decay_seconds = decay_seconds
        self.trail_seconds = trail_seconds
        self.refresh_interval = refresh_interval
        self.velocity_scale = velocity_scale
        self.show_pos = show_pos

        self._points: Dict[Tuple[str, int], deque] = {}
        self._last_draw = 0.0
        self._running = True

        plt.ion()
        self.fig, self.ax = plt.subplots()
        self._setup_axes()
        plt.show(block=False)

        self.fig.canvas.mpl_connect("key_press_event", self._on_key)

    def _on_key(self, event):
        if event.key == "p":
            self.show_pos = not self.show_pos

    def _setup_axes(self):
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.grid(True)

    def update(self, label: str, beacon_id: int, x: float, y: float, z: float):
        if not self._running:
            return

        now = time.monotonic()
        key = (label, beacon_id)

        if key not in self._points:
            self._points[key] = deque()

        self._points[key].append((x, y, z, now))

        while self._points[key] and now - self._points[key][0][3] > self.trail_seconds:
            self._points[key].popleft()

        if now - self._last_draw >= self.refresh_interval:
            self._redraw(now)

    def _label_alignment(self, x: float, y: float):
        xmin, xmax = self.ax.get_xlim()
        ymin, ymax = self.ax.get_ylim()

        x_mid = (xmin + xmax) * 0.5
        y_mid = (ymin + ymax) * 0.5

        ha = "left" if x < x_mid else "right"
        va = "bottom" if y < y_mid else "top"

        dx = 5 if ha == "left" else -5
        dy = 5 if va == "bottom" else -5

        return ha, va, dx, dy

    def _redraw(self, now: float):
        try:
            self.ax.clear()
            self._setup_axes()

            expired = []

            for (label, bid), samples in self._points.items():
                if not samples:
                    expired.append((label, bid))
                    continue

                last_x, last_y, last_z, last_ts = samples[-1]

                if now - last_ts > self.decay_seconds:
                    expired.append((label, bid))
                    continue

                xs = [p[0] for p in samples]
                ys = [p[1] for p in samples]

                is_mobile = label == "MOBILE"
                color = "red" if is_mobile else "blue"
                marker = "o" if is_mobile else "s"

                if len(xs) > 1:
                    self.ax.plot(xs, ys, color=color, alpha=0.5)

                self.ax.scatter(last_x, last_y, c=color, marker=marker)

                # Label rendering
                if self.show_pos:
                    ha, va, dx, dy = self._label_alignment(last_x, last_y)
                    text = f"{label[0]}{bid} ({last_x:.2f}, {last_y:.2f})"
                    self.ax.annotate(
                        text,
                        (last_x, last_y),
                        xytext=(dx, dy),
                        textcoords="offset points",
                        ha=ha,
                        va=va,
                        fontsize=8,
                        color=color,
                        alpha=0.9,
                    )
                else:
                    self.ax.text(
                        last_x,
                        last_y,
                        f"{label[0]}{bid}",
                        fontsize=9,
                        color=color,
                    )

                # Velocity vector
                if len(samples) >= 2:
                    x0, y0, _, t0 = samples[-2]
                    dt = last_ts - t0
                    if dt > 0:
                        vx = (last_x - x0) / dt
                        vy = (last_y - y0) / dt
                        if math.hypot(vx, vy) > 1e-4:
                            self.ax.arrow(
                                last_x,
                                last_y,
                                vx * self.velocity_scale,
                                vy * self.velocity_scale,
                                head_width=0.05,
                                head_length=0.08,
                                fc=color,
                                ec=color,
                                alpha=0.8,
                            )

            for key in expired:
                del self._points[key]

            self.fig.canvas.draw_idle()
            plt.pause(0.001)
            self._last_draw = now

        except KeyboardInterrupt:
            self.close()

    def close(self):
        self._running = False
        try:
            plt.close(self.fig)
        except Exception:
            pass
