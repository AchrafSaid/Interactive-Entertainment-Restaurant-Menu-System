
import math


class SwipeDetector:

    def __init__(
        self,
        min_points=5,
        min_distance=90,
        max_deviation_ratio=0.65
    ):

        self.min_points = min_points
        self.min_distance = min_distance
        self.max_deviation_ratio = max_deviation_ratio

    def detect_path(self, points):

        if not points or len(points) < self.min_points:
            return None

        start_x, start_y = points[0]
        end_x, end_y = points[-1]

        dx = end_x - start_x
        dy = end_y - start_y

        distance = math.hypot(dx, dy)

        # Ignore small movements.
        if distance < self.min_distance:
            return None

        # Detect dominant movement direction.
        if abs(dx) > abs(dy) * 1.2:

            if dx > 0:
                return "SWIPE_RIGHT"

            return "SWIPE_LEFT"

        if abs(dy) > abs(dx) * 1.2:

            if dy > 0:
                return "SWIPE_DOWN"

            return "SWIPE_UP"

        # Diagonal movement is ambiguous.
        return None
