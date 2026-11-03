"""Conservative BLE proximity estimates; RSSI is not a distance measurement."""


class SignalGuard:
    def __init__(self, threshold=-78, grace=4.0, recovery=-70):
        self.threshold = threshold
        self.grace = grace
        self.recovery = recovery
        self.rssi = None
        self.last_sample = None
        self.weak_since = None
        self.samples = 0

    def observe(self, rssi, now):
        # -127 is Windows' "not received" sentinel, not a measured signal.
        if not isinstance(rssi, (int, float)) or not -126 <= rssi <= 0:
            return False
        if self.last_sample is None or now - self.last_sample > 2.5:
            self.rssi = rssi
            self.weak_since = None
            self.samples = 0
        else:
            self.rssi = self.rssi * 0.65 + rssi * 0.35
        self.last_sample = now
        if self.rssi <= self.threshold:
            if self.weak_since is None:
                self.weak_since = now
            self.samples += 1
        elif self.rssi >= self.recovery:
            self.weak_since = None
            self.samples = 0
        return self.samples >= 3 and self.weak_since is not None and now - self.weak_since >= self.grace

    def snapshot(self, now):
        fresh = self.last_sample is not None and now - self.last_sample <= 3
        return {"rssi": round(self.rssi) if fresh else None,
                "mode": "weak" if fresh and self.weak_since is not None else "signal" if fresh else "link"}
