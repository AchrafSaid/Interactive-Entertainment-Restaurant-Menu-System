
from swipe_detector import SwipeDetector

detector = SwipeDetector()


def test_gesture(name, points):

    result = detector.detect_path(points)

    print(f"{name}: {result}")


# Straight horizontal movement
right = [(100 + i * 15, 200) for i in range(15)]

left = [(350 - i * 15, 200) for i in range(15)]


# V-shaped movement
v_shape = (
    [(100 + i * 10, 100 + i * 10) for i in range(10)]
    +
    [(200 + i * 10, 190 - i * 10) for i in range(10)]
)


# Zigzag movement
zigzag = [
    (100, 100),
    (120, 150),
    (140, 100),
    (160, 150),
    (180, 100),
    (200, 150),
    (220, 100),
    (240, 150),
    (260, 100),
    (280, 150),
    (300, 100)
]


print("Testing Swipe and Drawing Gestures...\n")

test_gesture("Swipe Right", right)
test_gesture("Swipe Left", left)
test_gesture("V Shape", v_shape)
test_gesture("Zigzag", zigzag)
