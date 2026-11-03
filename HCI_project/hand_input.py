"""Time-based, camera-rate-independent pointing, pinch and scroll controls."""

import math


class HandInput:
    def __init__(self):
        self.position = None
        self.last_time = None
        self.pinch_armed = False
        self.pinch_since = None
        self.pinch_position = None
        self.last_click = -10
        self.fist_since = None
        self.fist_sent = False
        self.scroll_y = None
        self.point_until = -1

    def lost(self):
        self.position = None
        self.last_time = None
        self.pinch_armed = False
        self.pinch_since = None
        self.fist_since = None
        self.fist_sent = False
        self.scroll_y = None
        self.point_until = -1
        return {"type": "hand", "action": "lost"}

    @staticmethod
    def distance(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def from_landmarks(self, landmarks, now):
        lm = landmarks.landmark
        width = self.distance(lm[5], lm[17])
        if width < 0.045:
            return self.lost()
        fingers = [self.distance(lm[t], lm[0]) > self.distance(lm[p], lm[0]) * 1.12
                   for t, p in ((8, 6), (12, 10), (16, 14), (20, 18))]
        ratio = self.distance(lm[4], lm[8]) / width
        # A pinch can fold the index; retain pointer mode while its pinch is held.
        if fingers == [True, True, False, False] and ratio > 0.42:
            pose = "scroll"
        elif all(fingers) and ratio > 0.42:
            pose = "pause"
        elif (fingers[0] or self.pinch_since is not None or
              (now < self.point_until and ratio < .30 and self.distance(lm[8], lm[5]) > width * .65)):
            pose = "point"
        elif not any(fingers):
            pose = "back"
        else:
            pose = "pause"
        if pose == "point":
            self.point_until = now + .4
        x = min(1, max(0, (lm[8].x - 0.14) / 0.72))
        y = min(1, max(0, (lm[8].y - 0.12) / 0.72))
        return self.update(x, y, ratio, pose, now)

    def update(self, x, y, pinch, pose, now):
        dt = max(0.001, min(0.1, now - self.last_time)) if self.last_time is not None else 0.1
        self.last_time = now
        alpha = 1 - math.exp(-dt / 0.065)
        if self.position is None:
            self.position = (x, y)
        else:
            self.position = tuple(old + alpha * (new - old) for old, new in zip(self.position, (x, y)))
        event = {"type": "hand", "action": "point", "x": self.position[0], "y": self.position[1],
                 "pose": pose, "progress": 0}
        if pose != "back":
            self.fist_since = None
            self.fist_sent = False
        if pose == "back":
            if self.fist_since is None:
                self.fist_since = now
            event["progress"] = min(1, (now - self.fist_since) / 0.65)
            if event["progress"] >= 1 and not self.fist_sent:
                event["action"] = "back"
                self.fist_sent = True
        if pose == "point":
            if pinch > 0.45:
                self.pinch_armed = True
                self.pinch_since = None
                self.pinch_position = None
            elif pinch < 0.30 and self.pinch_armed:
                if self.pinch_since is None:
                    self.pinch_since = now
                    self.pinch_position = self.position
                # Freeze the cursor during the pinch so the finger's closing
                # movement cannot select a neighbouring control.
                event["x"], event["y"] = self.pinch_position
                event["progress"] = min(1, (now - self.pinch_since) / 0.12)
                if event["progress"] >= 1 and now - self.last_click >= 0.55:
                    event["action"] = "click"
                    self.last_click = now
                    self.pinch_armed = False
            elif self.pinch_position is not None:
                event["x"], event["y"] = self.pinch_position
        else:
            self.pinch_since = None
            self.pinch_position = None
            self.pinch_armed = False
        if pose == "scroll":
            if self.scroll_y is not None:
                event["action"] = "scroll"
                event["delta"] = (self.scroll_y - y) * 1800
            self.scroll_y = y
        else:
            self.scroll_y = None
        return event
