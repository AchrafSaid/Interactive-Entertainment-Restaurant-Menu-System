
class SwipeDetector:

    def detect_path(self, points):

        # Minimum number of tracking points
        if len(points) < 8:
            return None

        xs = [point[0] for point in points]
        ys = [point[1] for point in points]

        # Start-to-end movement
        dx = xs[-1] - xs[0]
        dy = ys[-1] - ys[0]

        # Total horizontal and vertical movement
        horizontal_distance = sum(
            abs(xs[i] - xs[i - 1])
            for i in range(1, len(xs))
        )

        vertical_distance = sum(
            abs(ys[i] - ys[i - 1])
            for i in range(1, len(ys))
        )

        # Total vertical variation
        vertical_range = max(ys) - min(ys)

        # Avoid detecting very small movements
        if abs(dx) < 100:
            return None

        if horizontal_distance < 110:
            return None

        # Check horizontal movement dominance
        if vertical_distance > horizontal_distance * 0.65:
            return None

        # Check vertical deviation
        if vertical_range > 100:
            return None

        # Direction consistency
        consistency = abs(dx) / horizontal_distance

        if consistency < 0.65:
            return None

        # Detect swipe direction
        if dx > 0:
            return "SWIPE_RIGHT"

        else:
            return "SWIPE_LEFT"

        return None
