
import cv2
import mediapipe as mp
import math
import time

from dollarpy import Recognizer
from gesture_storage import load_templates


# =========================
# 1. LOAD SAVED GESTURES
# =========================

templates = load_templates()

if len(templates) < 2:
    print("Please save at least two gesture templates first.")
    exit()

recognizer = Recognizer(templates)

print("Gestures loaded successfully!")


# =========================
# 2. MEDIAPIPE SETUP
# =========================

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)


# =========================
# 3. CAMERA SETUP
# =========================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera.")
    exit()


# =========================
# 4. GESTURE SETTINGS
# =========================

points = []

recording = False

last_position = None
last_movement_time = 0

IDLE_TIME = 0.8
MOVEMENT_THRESHOLD = 5
MIN_POINTS = 10

last_result = "Waiting..."
last_score = 0.0

cooldown = 0
COOLDOWN_TIME = 1.5


# =========================
# 5. MAIN LOOP
# =========================

print("\nLIVE GESTURE RECOGNITION")
print("Draw a saved gesture in front of the camera.")
print("The program detects it automatically.")
print("Press Q to quit.\n")


while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = hands.process(rgb_frame)

    height, width, _ = frame.shape

    current_time = time.monotonic()

    current_position = None

    # =========================
    # HAND TRACKING
    # =========================

    if results.multi_hand_landmarks:

        hand_landmarks = results.multi_hand_landmarks[0]

        mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS
        )

        index_tip = hand_landmarks.landmark[8]

        x = int(index_tip.x * width)
        y = int(index_tip.y * height)

        current_position = (x, y)

        cv2.circle(
            frame,
            current_position,
            8,
            (0, 255, 0),
            -1
        )

    # =========================
    # MOVEMENT DETECTION
    # =========================

    if current_position is not None:

        if last_position is not None:

            distance = math.hypot(
                current_position[0] - last_position[0],
                current_position[1] - last_position[1]
            )

            if distance >= MOVEMENT_THRESHOLD:

                if not recording and current_time >= cooldown:

                    recording = True
                    points = []

                    print("\nGesture recording started...")

                if recording:

                    points.append(current_position)
                    last_movement_time = current_time

        last_position = current_position

    else:
        last_position = None

    # =========================
    # DRAW RECORDED PATH
    # =========================

    if len(points) > 1:

        for i in range(1, len(points)):

            cv2.line(
                frame,
                points[i - 1],
                points[i],
                (255, 0, 0),
                3
            )

    # =========================
    # GESTURE RECOGNITION
    # =========================

    if recording:

        if current_time - last_movement_time >= IDLE_TIME:

            recording = False

            if len(points) >= MIN_POINTS:

                from dollarpy import Point

                dollar_points = [
                    Point(float(x), float(y))
                    for x, y in points
                ]

                result = recognizer.recognize(dollar_points)

                if result:

                    last_result = result[0]
                    last_score = float(result[1])

                    print("\nDetected Gesture:", last_result)
                    print("Recognition Score:", round(last_score, 3))

                else:

                    last_result = "No Match"
                    last_score = 0.0

                    print("No gesture recognized.")

            else:

                last_result = "Movement too short"
                print("Movement was too short.")

            points.clear()

            cooldown = current_time + COOLDOWN_TIME

    # =========================
    # DISPLAY INFORMATION
    # =========================

    status = "RECORDING..." if recording else "READY"

    cv2.putText(
        frame,
        f"Status: {status}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"Gesture: {last_result}",
        (10, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Score: {last_score:.3f}",
        (10, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Points: {len(points)}",
        (10, 135),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2
    )

    cv2.imshow("Live Gesture Recognition", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break


# =========================
# 6. CLEANUP
# =========================

cap.release()
hands.close()
cv2.destroyAllWindows()

print("\nLive Gesture Recognition stopped.")
