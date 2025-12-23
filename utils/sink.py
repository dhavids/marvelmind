import time

from src.position_tracker import BeaconType


class PositionSink:
    def __init__(self, csv_writer=None, broadcaster=None):
        self.csv_writer = csv_writer
        self.broadcaster = broadcaster

    def publish(self, tracker):
        ts_pub = time.time()

        beacons = []

        for bid, pos in tracker.get_mobile_positions().items():
            beacons.append((BeaconType.MOBILE, bid, pos))

        for bid, pos in tracker.get_stationary_map().items():
            beacons.append((BeaconType.STATIONARY, bid, pos))

        if self.csv_writer:
            self.csv_writer.write_snapshot(ts_pub, beacons)

        if self.broadcaster:
            payload = {
                "ts_pub": ts_pub,
                "beacons": [
                    {
                        "type": btype.value,
                        "id": bid,
                        "pos": {
                            "x": pos.x,
                            "y": pos.y,
                            "z": pos.z,
                        },
                        "ts_mm": pos.ts_mm,
                        "ts_read": pos.ts_read,
                    }
                    for btype, bid, pos in beacons
                ],
            }
            self.broadcaster.update(payload)
