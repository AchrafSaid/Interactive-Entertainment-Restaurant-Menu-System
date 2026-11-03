
import cv2
import mediapipe as mp
import socket
import time
import math

from dollarpy import Recognizer, Point
from gesture_storage import load_templates


# =====================================
# 1. CONFIGURATION
# =====================================

HOST = "127.0.0.1"
PORT = 5000

CAMERA_INDEX = 0

MIN_POINTS = 10
MOVEMENT_THRESHOLD = 3

GESTURE_PAUSE = 0.8
GESTURE_COOLDOWN = 1.0

MIN_SCORE = 0.60


# =====================================
# 2. LOAD DOLLARPY TEMPLATES
# =====================================

templates = load_templates()

if not templates:
    print("No gesture templates found!")
    raise SystemExit

recognizer = Recognizer(templates)

print("DollarPy Recognizer Ready!")


# =====================================
# 3. TCP SOCKET CLIENT
# =====================================

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.settimeout(3)

try:
    client.connect((HOST, PORT))
    client.settimeout(None)
    print("Connected to Olive / Table Server!")

except OSError as error:
    print("Could not connect to server:", error)
    print("Start menu_server.py first.")
    client.close()
    raise SystemExit


def send_gesture(gesture):
    try:
        client.sendall((gesture + "\n").encode("utf-8"))
        response = client.recv(1024).decode("utf-8").strip()
        print("Server:", response)

    except OSError as error:
        print("Socket communication error:", error)
        raise SystemExit


# =====================================
# 4. MEDIAPIPE HAND TRACKING
# =====================================

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

camera = cv2.VideoCapture(CAMERA_INDEX)

if not camera.isOpened():
    print("Could not open camera!")
    hands.close()
    client.close()
    raise SystemExit


# =====================================
# 5. GESTURE VARIABLES
# =====================================

gesture_points = []

previous_point = None

last_movement_time = time.time()
last_gesture_time = 0


# =====================================
# 6. DOLLARPY RECOGNITION
# =====================================

def recognize_gesture(points):
    global last_gesture_time

    if len(points) < MIN_POINTS:
        print("Not enough points:", len(points))
        return

    dollar_points = [
        Point(float(x), float(y))
        for x, y in points
    ]

    try:
        scores = []

        for template in templates:
            test_recognizer = Recognizer([template])
            name, score = test_recognizer.recognize(dollar_points)

            scores.append((template.name, score))

        scores.sort(key=lambda item: item[1], reverse=True)

        print("\nTop 5 Template Matches:")

        for name, score in scores[:5]:
            print(f"{name}: {score:.3f}")

        gesture_name, score = recognizer.recognize(dollar_points)

        if gesture_name is None or score < MIN_SCORE:
            print(f"No Match | Score: {score:.3f}")
            return

        print(
            f"Recognized: {gesture_name} | "
            f"Score: {score:.3f}"
        )

        now = time.time()

        if (
            gesture_name.startswith("C_SHAPE")
            and now - last_gesture_time >= GESTURE_COOLDOWN
        ):
            send_gesture("C_SHAPE")
            last_gesture_time = now

    except Exception as error:
        print("Recognition error:", error)


# =====================================
# 7. MAIN CAMERA LOOP
# =====================================

print("\nCamera started!")
print("Draw letter C using your index finger.")
print("Press Q to quit.\n")


try:

    while camera.isOpened():

        success, frame = camera.read()

        if not success:
            continue

        frame = cv2.flip(frame, 1)

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = hands.process(rgb_frame)

        current_time = time.time()

        # =================================
        # 8. HAND DETECTION
        # =================================

        if results.multi_hand_landmarks:

            hand_landmarks = results.multi_hand_landmarks[0]

            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            # Index finger tip
            index_tip = hand_landmarks.landmark[8]

            x = int(index_tip.x * frame.shape[1])
            y = int(index_tip.y * frame.shape[0])

            cv2.circle(
                frame,
                (x, y),
                8,
                (0, 255, 0),
                -1
            )

            current_point = (x, y)

            # =================================
            # 9. COLLECT GESTURE POINTS
            # =================================

            if previous_point is None:
                previous_point = current_point

            if not gesture_points:

                gesture_points.append(current_point)
                last_movement_time = current_time

            else:

                distance = math.hypot(
                    current_point[0] - previous_point[0],
                    current_point[1] - previous_point[1]
                )

                if distance >= MOVEMENT_THRESHOLD:

                    gesture_points.append(current_point)
                    last_movement_time = current_time

            previous_point = current_point

        else:
            previous_point = None

        # =================================
        # 10. FINISH GESTURE
        # =================================

        if (
            gesture_points
            and current_time - last_movement_time >= GESTURE_PAUSE
        ):

            print(
                "Captured points:",
                len(gesture_points)
            )

            recognize_gesture(gesture_points)

            gesture_points.clear()
            previous_point = None

        # =================================
        # 11. DISPLAY INFORMATION
        # =================================

        cv2.putText(
            frame,
            f"Points: {len(gesture_points)}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow(
            "Olive / Table - DollarPy",
            frame
        )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


# =====================================
# 12. CLEANUP
# =====================================

finally:

    camera.release()
    hands.close()
    cv2.destroyAllWindows()
    client.close()

    print("Camera and Socket closed.")
