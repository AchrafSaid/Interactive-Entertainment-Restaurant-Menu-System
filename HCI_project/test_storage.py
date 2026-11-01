
from dollarpy import Template, Point
from gesture_storage import save_templates, load_templates

# Create sample gestures
v_shape = Template("V_SHAPE", [
    Point(0, 0),
    Point(50, 50),
    Point(100, 0)
])

zigzag = Template("ZIGZAG", [
    Point(0, 0),
    Point(30, 50),
    Point(60, 0),
    Point(90, 50),
    Point(120, 0)
])

# Save gestures
save_templates([v_shape, zigzag])

# Load gestures
loaded_templates = load_templates()

print("Number of loaded templates:", len(loaded_templates))
