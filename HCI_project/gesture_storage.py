
import json
import os
from dollarpy import Template, Point

FILE_NAME = "gesture_templates.json"


def save_templates(templates):
    data = {}

    for template in templates:
        data[template.name] = [
            [point.x, point.y]
            for point in template
        ]

    with open(FILE_NAME, "w") as file:
        json.dump(data, file, indent=4)

    print("Gestures saved successfully!")


def load_templates():
    if not os.path.exists(FILE_NAME):
        print("No saved gestures found.")
        return []

    with open(FILE_NAME, "r") as file:
        data = json.load(file)

    templates = []

    for name, points in data.items():
        converted_points = [
            Point(float(x), float(y))
            for x, y in points
        ]

        templates.append(Template(name, converted_points))

    print("Loaded gestures:", [t.name for t in templates])

    return templates
