
from dollarpy import Recognizer, Template, Point

# Template 1: V Shape
v_shape = Template("V_SHAPE", [
    Point(0, 0),
    Point(50, 50),
    Point(100, 0)
])

# Template 2: Zigzag
zigzag = Template("ZIGZAG", [
    Point(0, 0),
    Point(30, 50),
    Point(60, 0),
    Point(90, 50),
    Point(120, 0)
])

# Create recognizer
recognizer = Recognizer([v_shape, zigzag])

# Test a V-shaped gesture
test_points = [
    Point(10, 0),
    Point(55, 50),
    Point(100, 0)
]

result = recognizer.recognize(test_points)

print("Detected Gesture:", result[0])
print("Recognition Score:", result[1])
