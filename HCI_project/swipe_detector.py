class SwipeDetector:

    def __init__(self, min_distance=80, max_vertical_drift=80,
                 min_points=5, horizontal_ratio=None):
        self.min_distance = min_distance
        self.max_vertical_drift = max_vertical_drift
        self.min_points = min_points
        self.horizontal_ratio = horizontal_ratio

    def detect_path(self, points):

        if len(points) < self.min_points:
            return None

        start_x = points[0][0]
        end_x = points[-1][0]

        start_y = points[0][1]
        end_y = points[-1][1]

        dx = end_x - start_x
        dy = abs(end_y - start_y)

        # Ignore small movements
        if abs(dx) < self.min_distance:
            return None

        # Keep the movement mostly horizontal
        if dy > self.max_vertical_drift:
            return None

        if self.horizontal_ratio is not None:
            vertical_span = max(point[1] for point in points) - min(point[1] for point in points)
            if abs(dx) < vertical_span * self.horizontal_ratio:
                return None

        if dx > 0:
            return "SWIPE_RIGHT"

        return "SWIPE_LEFT"
