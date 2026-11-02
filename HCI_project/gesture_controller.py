"""Turn normalized palm positions and held poses into menu commands."""

from collections import Counter, deque
import math

from swipe_detector import SwipeDetector


class GestureController:
    HOLD_TIME = 0.45
    SWIPE_WINDOW = 1.2
    MOTION_WINDOW = 0.2
    MOTION_THRESHOLD = 0.035
    COOLDOWN_TIME = 0.7
    MAX_FRAME_GAP = 0.5
    POSE_GRACE_TIME = 0.18
    TRACKING_GRACE_TIME = 0.2
    TARGET_MARGIN = 0.035
    SMOOTHING_TIME = 0.06

    def __init__(self):
        self.swipe_detector = SwipeDetector(
            min_distance=0.07, max_vertical_drift=0.15,
            min_points=3, horizontal_ratio=1.5
        )
        self.positions = deque()
        self.menu_open = False
        self.cooldown_until = 0
        self.last_seen = None
        self.smoothed_position = None
        self.last_swipe = None
        self.swipe_idle_since = None
        self._reset_pose()

    def _reset_pose(self):
        self.pose = None
        self.pose_since = None
        self.pose_sent = False
        self.last_pose_match = None
        self.pose_samples = deque()
        self.target_index = None

    def confirm_menu_state(self, menu_open):
        """Use the state acknowledged by the menu, rather than predicting it."""
        self.menu_open = menu_open

    @staticmethod
    def product_index(finger_x):
        """Match the mirrored camera's three columns to the menu's cards."""
        return max(0, min(2, int(finger_x * 3)))

    def _selection_target(self, finger_x):
        if self.target_index is None:
            self.target_index = self.product_index(finger_x)
        # A small overlap keeps a shaky finger from switching cards repeatedly.
        while (
            self.target_index < 2
            and finger_x > (self.target_index + 1) / 3 + self.TARGET_MARGIN
        ):
            self.target_index += 1
        while (
            self.target_index > 0
            and finger_x < self.target_index / 3 - self.TARGET_MARGIN
        ):
            self.target_index -= 1
        return self.target_index

    def _observe_pose(self, command, now):
        self.pose_samples.append((now, command))
        while self.pose_samples and now - self.pose_samples[0][0] > 0.2:
            self.pose_samples.popleft()
        votes = Counter(sample for _, sample in self.pose_samples)
        winner, count = votes.most_common(1)[0]
        if winner is None or count / len(self.pose_samples) < 0.6:
            if self.last_pose_match is None or now - self.last_pose_match > self.POSE_GRACE_TIME:
                self._reset_pose()
            return
        if winner != self.pose:
            self.pose = winner
            self.pose_since = now
            self.pose_sent = False
        if command == self.pose:
            self.last_pose_match = now

    def hold_progress(self, now):
        if self.pose_since is None or self.pose is None:
            return 0
        if self.pose_sent:
            return 1
        return max(0, min(1, (now - self.pose_since) / self.HOLD_TIME))

    def swipe_progress(self):
        if not self.menu_open or len(self.positions) < 2:
            return None, 0
        dx = self.positions[-1][1] - self.positions[0][1]
        if abs(dx) < 0.02:
            return None, 0
        direction = "RIGHT" if dx > 0 else "LEFT"
        if self.last_swipe == "SWIPE_" + direction:
            return None, 0
        return direction, min(1, abs(dx) / self.swipe_detector.min_distance)

    def update(self, pose, position, now, finger_x=None):
        """Return at most one command; moving hands take priority over poses."""
        if position is None:
            self.positions.clear()
            self.smoothed_position = None
            if self.last_seen is None or now - self.last_seen > self.TRACKING_GRACE_TIME:
                self._reset_pose()
                self.last_swipe = None
            return None

        frame_gap = None if self.last_seen is None else now - self.last_seen
        if frame_gap is not None and frame_gap > self.MAX_FRAME_GAP:
            self.positions.clear()
            self.smoothed_position = None
            self._reset_pose()
            self.last_swipe = None
        self.last_seen = now

        x, y = position
        if self.smoothed_position is not None and frame_gap is not None:
            alpha = 1 - math.exp(-frame_gap / self.SMOOTHING_TIME)
            previous_x, previous_y = self.smoothed_position
            x = previous_x + alpha * (x - previous_x)
            y = previous_y + alpha * (y - previous_y)
        self.smoothed_position = (x, y)
        self.positions.append((now, x, y))
        while self.positions and now - self.positions[0][0] > self.SWIPE_WINDOW:
            self.positions.popleft()

        recent = [sample for sample in self.positions if now - sample[0] <= self.MOTION_WINDOW]
        # Include the previous frame even when inference is slower than 5 FPS.
        if len(self.positions) > 1 and len(recent) == 1:
            recent.insert(0, self.positions[-2])
        motion_extent = max(
            math.hypot(x - previous_x, y - previous_y)
            for _, previous_x, previous_y in recent
        )
        moving = motion_extent > self.MOTION_THRESHOLD

        # One continuous sweep changes one category. Pause to repeat it.
        if motion_extent < 0.012:
            if self.swipe_idle_since is None:
                self.swipe_idle_since = now
            elif self.last_swipe is not None and now - self.swipe_idle_since >= 0.2:
                self.last_swipe = None
                self.positions.clear()
                self.positions.append((now, x, y))
        else:
            self.swipe_idle_since = None

        # Closing is deliberate even if the palm shifts as the fingers curl.
        pose_moving = moving and pose != "CLOSED_FIST"
        if pose_moving:
            self._reset_pose()
            command = None
        else:
            command = pose
            if pose == "SELECT_PRODUCT":
                target_x = position[0] if finger_x is None else finger_x
                command = f"SELECT_PRODUCT:{self._selection_target(target_x)}"
            self._observe_pose(command, now)

        if now < self.cooldown_until and pose != "CLOSED_FIST":
            return None

        if self.menu_open and pose != "CLOSED_FIST":
            swipe = self.swipe_detector.detect_path(
                [(sample_x, sample_y) for _, sample_x, sample_y in self.positions]
            )
            if swipe is not None and swipe != self.last_swipe:
                self.positions.clear()
                self.positions.append((now, x, y))
                self.cooldown_until = now + self.COOLDOWN_TIME
                self.last_swipe = swipe
                self.swipe_idle_since = None
                self._reset_pose()
                return swipe

        if (
            pose_moving
            or command != self.pose
            or self.pose is None
            or self.pose_since is None
            or self.pose_sent
            or now - self.pose_since < self.HOLD_TIME
        ):
            return None

        self.pose_sent = True
        if pose != "OPEN_PALM" and not self.menu_open:
            return None

        self.positions.clear()
        self.positions.append((now, x, y))
        self.last_swipe = None
        return command
