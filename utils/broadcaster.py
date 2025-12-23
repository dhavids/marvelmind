import json
import socket
import threading
import time

from utils.logging_setup import get_logger

logger = get_logger(__name__)


class PositionBroadcaster:
    def __init__(self, host="0.0.0.0", port=5555, rate_hz=20):
        self.host = host
        self.port = port
        self.period = 1.0 / rate_hz

        self._clients = []
        self._lock = threading.Lock()
        self._running = False
        self._latest_payload = None

        self._last_broadcast_log = 0.0

    def start(self):
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        logger.info(
            "Broadcaster started on %s:%d at %.1f Hz",
            self.host,
            self.port,
            1.0 / self.period,
        )

    def stop(self):
        self._running = False
        with self._lock:
            for c in self._clients:
                c.close()
            self._clients.clear()
        logger.info("Broadcaster stopped")

    def update(self, payload: dict):
        self._latest_payload = payload

    def _accept_loop(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()

        logger.info("Broadcaster listening for clients")

        while self._running:
            try:
                conn, addr = server.accept()
                conn.setblocking(False)
                with self._lock:
                    self._clients.append(conn)
                logger.info("Client connected from %s:%d", addr[0], addr[1])
            except Exception:
                time.sleep(0.1)

    def _broadcast_loop(self):
        while self._running:
            if self._latest_payload is not None:
                msg = json.dumps(self._latest_payload).encode() + b"\n"

                with self._lock:
                    dead = []
                    for c in self._clients:
                        try:
                            c.sendall(msg)
                        except Exception:
                            dead.append(c)

                    for c in dead:
                        c.close()
                        self._clients.remove(c)
                        logger.warning("Client disconnected due to send failure")

                    client_count = len(self._clients)

                # Throttled broadcast logging (once per second) if we have clients
                now = time.monotonic()
                if now - self._last_broadcast_log >= 1.0 and client_count > 0:
                    beacon_count = len(self._latest_payload.get("beacons", []))
                    logger.info(
                        "Broadcasted %d beacons to %d clients",
                        beacon_count,
                        client_count,
                    )
                    self._last_broadcast_log = now

            time.sleep(self.period)
