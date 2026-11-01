class SwipeDetector:

    def detect_path(self, points):

        if len(points) < 5:
            return None

        start_x = points[0][0]
        end_x = points[-1][0]

        start_y = points[0][1]
        end_y = points[-1][1]

        dx = end_x - start_x
        dy = abs(end_y - start_y)

        # Ignore small movements
        if abs(dx) < 80:
            return None

        # Keep the movement mostly horizontal
        if dy > 80:
            return None

        if dx > 0:
            return "SWIPE_RIGHT"

        return "SWIPE_LEFT"