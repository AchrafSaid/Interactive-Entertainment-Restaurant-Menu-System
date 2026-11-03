"""Gesture-only hand controls: hold a pose to act, swipe to move the highlight.

There is no pointer. The UI keeps one highlighted control; swipes move the
highlight and holding up one finger selects it. Every other gesture is a
hold-to-trigger shortcut (see HOLD_POSES).

Static hand SHAPES are classified from the 21 MediaPipe landmarks (classify()).
Hand MOVEMENTS (swipes and two-finger moves) are classified by the DollarPy
recogniser in movement_dollarpy.py: the geometry here only decides that the
hand moved far enough; DollarPy decides which movement it was.
"""

from collections import deque
import math

from movement_dollarpy import MovementClassifier

# Hold-to-trigger poses: pose -> (action, seconds the pose must be held still).
# "shortcut" events carry the pose name in event["shortcut"].
HOLD_POSES = {
    "select": ("select", 0.3),       # one finger       -> select highlighted item
    "back": ("back", 0.65),          # closed fist      -> close dish / go back
    "menu": ("shortcut", 0.9),       # open palm        -> open the menu
    "add": ("shortcut", 0.6),        # thumbs up        -> add product
    "decline": ("shortcut", 0.6),    # thumbs down      -> decline product
    "cart": ("shortcut", 0.6),       # C shape          -> open cart
    "checkout": ("shortcut", 0.7),   # OK sign          -> confirm checkout
    "games": ("shortcut", 0.6),      # rock sign        -> games
    "rewards": ("shortcut", 0.6),    # three fingers    -> rewards
}

SWIPE_WINDOW = 0.35     # seconds of palm movement considered for a swipe
SWIPE_DISTANCE = 0.16   # fraction of the camera frame the hand must travel
SWIPE_COOLDOWN = 1.0    # minimum seconds between two highlight moves
STILL_WINDOW = 0.25     # holds restart while the hand moves more than this...
STILL_DISTANCE = 0.05   # ...fraction of the frame within STILL_WINDOW seconds
# Raising a finger moves the hand a little, so selecting tolerates more motion.
STILL_DISTANCE_BY_POSE = {"select": 0.12}
# Two fingers up: moving the hand moves the highlight one step (up, down, left or
# right) per this fraction of the camera frame.
SCROLL_STEP = 0.08
SCROLL_STEP_COOLDOWN = 0.7  # minimum seconds between two-finger steps
SCROLL_WINDOW = 0.7         # seconds of two-finger travel considered for a step
# A pose may flicker for a frame or two (tracking noise) without restarting its hold.
HOLD_GRACE = 0.2
# After DollarPy rejects a movement, wait this long before trying again (each
# recognition costs ~10 ms, so it is not repeated on every camera frame).
DOLLARPY_RETRY = 0.15

_default_classifier = None


def default_classifier():
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = MovementClassifier()
    return _default_classifier


class HandInput:
    def __init__(self, classifier=None):
        self.classifier = classifier or default_classifier()
        self.lost()

    def lost(self):
        self.hold_pose = None
        self.hold_since = None
        self.hold_sent = False
        self.hold_seen = None
        self.scroll_y = None
        self.trail = deque()
        self.scroll_trail = deque()
        self.last_swipe = -10
        self.retry_at = -10
        return {"type": "hand", "action": "lost"}

    def recognise_movement(self, trail, now):
        """Ask DollarPy which movement the trail is. Returns a direction or None."""
        if now < self.retry_at:
            return None, None
        direction, name, score = self.classifier.classify(list(trail))
        info = {"classifier": "dollarpy", "gesture": name, "score": round(score, 3)}
        if direction is None:
            self.retry_at = now + DOLLARPY_RETRY
        return direction, info

    @staticmethod
    def distance(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    @staticmethod
    def bend(lm, mcp, pip, dip, tip):
        """Degrees between a finger's first and last segment: 0 straight, ~180 folded."""
        u = [getattr(lm[pip], k, 0) - getattr(lm[mcp], k, 0) for k in "xyz"]
        v = [getattr(lm[tip], k, 0) - getattr(lm[dip], k, 0) for k in "xyz"]
        norm = math.hypot(*u) * math.hypot(*v)
        if norm == 0:
            return 0
        return math.degrees(math.acos(max(-1, min(1, sum(a * b for a, b in zip(u, v)) / norm))))

    def classify(self, lm):
        width = self.distance(lm[5], lm[17])
        fingers = [self.distance(lm[t], lm[0]) > self.distance(lm[p], lm[0]) * 1.12
                   for t, p in ((8, 6), (12, 10), (16, 14), (20, 18))]
        ratio = self.distance(lm[4], lm[8]) / width
        # Thumb is "out" when its tip is well away from the middle knuckle
        # (in a fist it is tucked across the fingers).
        thumb_out = self.distance(lm[4], lm[9]) > width * 1.15
        thumb_up = thumb_out and lm[4].y < min(lm[5].y, lm[6].y) - width * 0.45
        thumb_down = thumb_out and lm[4].y > max(lm[5].y, lm[6].y) + width * 0.45
        bends = [self.bend(lm, *joints) for joints in
                 ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16))]
        c_curve = all(40 < angle < 135 for angle in bends) and 0.45 < ratio < 1.8
        if ratio < 0.33 and fingers[1] and fingers[2] and fingers[3]:
            return "checkout"          # OK sign: thumb + index circle, others up
        if c_curve:
            return "cart"
        # One finger: the index is up (straight, even if the wrist is tilted) and
        # the other three are folded. The thumb is ignored.
        index_up = fingers[0] or bends[0] < 30
        if index_up and not any(fingers[1:]):
            return "select"
        if not any(fingers):
            if thumb_up:
                return "add"
            if thumb_down:
                return "decline"
            return "back"
        if fingers == [True, False, False, True]:
            return "games"
        if fingers == [True, True, True, False]:
            return "rewards"
        if fingers == [True, True, False, False]:
            return "scroll"
        if all(fingers):
            return "menu"
        return "pause"

    def from_landmarks(self, landmarks, now):
        lm = landmarks.landmark
        if self.distance(lm[5], lm[17]) < 0.045:
            return self.lost()
        return self.step(self.classify(lm), lm[9].x, lm[9].y, now)

    def step(self, pose, x, y, now):
        """Advance one camera frame. (x, y) is the palm centre in 0..1 frame units."""
        event = {"type": "hand", "action": "pose", "pose": pose, "progress": 0}
        self.trail.append((now, x, y))
        while self.trail and now - self.trail[0][0] > SWIPE_WINDOW:
            self.trail.popleft()

        # Swipes: a fast palm movement (not while scrolling). The hand must travel
        # SWIPE_DISTANCE within SWIPE_WINDOW; DollarPy classifies the movement.
        if pose != "scroll" and now - self.last_swipe >= SWIPE_COOLDOWN:
            t0, x0, y0 = self.trail[0]
            if max(abs(x - x0), abs(y - y0)) > SWIPE_DISTANCE:
                direction, info = self.recognise_movement(self.trail, now)
                if direction:
                    self.last_swipe = now
                    self.trail.clear()
                    self.hold_pose = None
                    event.update(action="swipe", direction=direction, **info)
                    return event

        # Bridge brief tracking flicker: keep the held pose for a moment.
        if (self.hold_pose and pose != self.hold_pose and self.hold_seen is not None
                and now - self.hold_seen <= HOLD_GRACE):
            pose = self.hold_pose
            event["pose"] = pose
        elif pose == self.hold_pose:
            self.hold_seen = now

        # Holds only count while the hand is (nearly) still.
        recent = [(px, py) for t, px, py in self.trail if now - t <= STILL_WINDOW]
        limit = STILL_DISTANCE_BY_POSE.get(pose, STILL_DISTANCE)
        moving = math.hypot(recent[-1][0] - recent[0][0], recent[-1][1] - recent[0][1]) > limit
        if pose in HOLD_POSES:
            action, seconds = HOLD_POSES[pose]
            if self.hold_pose != pose or (moving and not self.hold_sent):
                self.hold_pose, self.hold_since, self.hold_sent = pose, now, False
                self.hold_seen = now
            event["progress"] = min(1, (now - self.hold_since) / seconds)
            if event["progress"] >= 1 and not self.hold_sent:
                event["action"] = action
                if action == "shortcut":
                    event["shortcut"] = pose
                self.hold_sent = True
        else:
            self.hold_pose = None
            self.hold_since = None
            self.hold_sent = False
            self.hold_seen = None

        if pose == "scroll":
            # Two fingers: hand travel over the last SWIPE_WINDOW seconds steps the
            # highlight in its main direction (the page follows the highlight).
            # "delta" lets the UI scroll when there is nothing further to highlight.
            if self.scroll_y is not None:
                event["action"] = "scroll"
                event["delta"] = (y - self.scroll_y) * 1800
            self.scroll_y = y
            self.scroll_trail.append((now, x, y))
            while now - self.scroll_trail[0][0] > SCROLL_WINDOW:
                self.scroll_trail.popleft()
            t0, x0, y0 = self.scroll_trail[0]
            if (now - self.last_swipe >= SCROLL_STEP_COOLDOWN
                    and max(abs(x - x0), abs(y - y0)) >= SCROLL_STEP):
                direction, info = self.recognise_movement(self.scroll_trail, now)
                if direction:
                    self.last_swipe = now
                    self.scroll_trail.clear()
                    event.update(action="swipe", direction=direction, delta=0, source="scroll", **info)
        else:
            self.scroll_y = None
            self.scroll_trail.clear()
        return event
