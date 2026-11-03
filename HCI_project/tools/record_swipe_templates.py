"""Record real swipe templates from the camera for the DollarPy recogniser.

    python tools/record_swipe_templates.py

Press L, R, U or D, then swipe your open hand in that direction within about
one second. The palm path (MediaPipe landmark 9) is encoded with the same
time-band encoding as the app and saved to swipe_templates.json as
SWIPE_<DIR>_REC_<n>. Press T to test the current templates on your next swipe,
and Q to quit. Close the menu app first: only one program can use the camera.
"""
import json
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from movement_dollarpy import TEMPLATES_FILE, MovementClassifier, encode  # noqa: E402

KEYS = {ord("l"): "LEFT", ord("r"): "RIGHT", ord("u"): "UP", ord("d"): "DOWN", ord("t"): "TEST"}
RECORD_SECONDS = 1.0
MIN_TRAVEL = 0.12   # ignore recordings where the hand barely moved


def trim(trail):
    """Keep the part of the recording where the hand actually moved."""
    if len(trail) < 3:
        return trail
    speeds = [((b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2) ** .5 / max(1e-3, b[0] - a[0]) for a, b in zip(trail, trail[1:])]
    moving = [i for i, s in enumerate(speeds) if s > 0.25]
    return trail[moving[0]:moving[-1] + 2] if moving else trail


def main():
    templates = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8")) if TEMPLATES_FILE.exists() else {}
    classifier = MovementClassifier(templates)
    cap = cv2.VideoCapture(0)
    hands = mp.solutions.hands.Hands(max_num_hands=1, model_complexity=0, min_detection_confidence=0.6)
    label, started, trail, message = None, 0.0, [], "Press L/R/U/D to record, T to test, Q to quit"
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera unavailable."); break
            frame = cv2.flip(frame, 1)
            result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            now = time.monotonic()
            if result.multi_hand_landmarks:
                palm = result.multi_hand_landmarks[0].landmark[9]
                mp.solutions.drawing_utils.draw_landmarks(frame, result.multi_hand_landmarks[0], mp.solutions.hands.HAND_CONNECTIONS)
                if label:
                    trail.append((now, palm.x, palm.y))
            if label and now - started >= RECORD_SECONDS:
                path = trim(trail)
                travel = max((max(abs(x - path[0][1]), abs(y - path[0][2])) for _, x, y in path), default=0)
                if travel < MIN_TRAVEL or encode(path) is None:
                    message = "Not enough movement - try again"
                elif label == "TEST":
                    direction, name, score = classifier.classify(path)
                    message = f"DollarPy: {name} score {score:.2f} -> {direction or 'rejected'}"
                else:
                    count = sum(k.startswith(f"SWIPE_{label}_REC_") for k in templates) + 1
                    templates[f"SWIPE_{label}_REC_{count}"] = [[round(x, 4), round(y, 4)] for x, y in encode(path)]
                    TEMPLATES_FILE.write_text(json.dumps(templates, indent=1) + "\n", encoding="utf-8")
                    classifier = MovementClassifier(templates)
                    message = f"Saved SWIPE_{label}_REC_{count}"
                print(message)
                label, trail = None, []
            status = f"Recording {label}... swipe now" if label else message
            cv2.putText(frame, status, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 120), 2)
            cv2.imshow("Record swipe templates", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key in KEYS and not label:
                label, started, trail = KEYS[key], time.monotonic(), []
    finally:
        cap.release()
        hands.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
