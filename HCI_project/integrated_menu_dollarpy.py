import sys
if __name__ == "__main__":
    from run_menu import ensure_runtime, check_gesture_runtime
    ensure_runtime()
    if "--check" in sys.argv:
        raise SystemExit(check_gesture_runtime())


import cv2
import mediapipe as mp
import math
import time
import socket
import urllib.request
import threading
import queue

from dollarpy import Recognizer, Template, Point
from swipe_detector import SwipeDetector


# =====================================
# 1. SERVER CONNECTION
# =====================================

HOST = "127.0.0.1"
PORT = 5000

FRAME_URL = "http://127.0.0.1:8765/frame"

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.settimeout(5)

try:
    client.connect((HOST, PORT))
    print("Connected to Restaurant Menu Server!")

except (ConnectionRefusedError, OSError) as error:
    print("Cannot connect to Menu Server:", error)
    print("Please run menu_server_gui.py first.")
    client.close()
    raise SystemExit


def send_gesture(gesture):
    try:
        client.sendall((gesture + "\n").encode("utf-8"))

        response = client.recv(1024).decode("utf-8")

        if not response:
            raise ConnectionResetError("Server disconnected.")

        print("Server Response:", response.strip())

    except (ConnectionResetError, BrokenPipeError, OSError) as error:
        print("Error sending gesture:", error)
        raise


# =====================================
# 2. CAMERA FRAME PUBLISHER
# =====================================

frame_queue = queue.Queue(maxsize=1)
publisher_stop = threading.Event()


def publish_camera_frames():
    """
    Sends the latest JPEG frame to the Olive / Table
    HTTP camera server without blocking gesture recognition.
    """

    last_error_time = 0

    while not publisher_stop.is_set():

        try:
            frame_data = frame_queue.get(timeout=0.5)

        except queue.Empty:
            continue

        if frame_data is None:
            break

        try:
            request = urllib.request.Request(
                FRAME_URL,
                data=frame_data,
                headers={
                    "Content-Type": "image/jpeg"
                },
                method="POST"
            )

            with urllib.request.urlopen(
                request,
                timeout=2
            ) as response:

                response.read()

        except Exception as error:

            now = time.monotonic()

            # Avoid printing the same error every frame.
            if now - last_error_time >= 3:
                print("Camera preview stream error:", error)
                last_error_time = now

            time.sleep(0.2)


def send_frame_to_menu(frame):
    """
    Encodes the frame and keeps only the newest frame
    in the queue to avoid building up a delay.
    """

    success, buffer = cv2.imencode(
        ".jpg",
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, 65]
    )

    if not success:
        return

    frame_data = buffer.tobytes()

    try:
        frame_queue.put_nowait(frame_data)

    except queue.Full:
        try:
            frame_queue.get_nowait()
        except queue.Empty:
            pass

        try:
            frame_queue.put_nowait(frame_data)
        except queue.Full:
            pass


# =====================================
# 3. SWIPE + DOLLARPY
# =====================================

swipe_detector = SwipeDetector()


def make_points(coords):
    return [
        Point(float(x), float(y))
        for x, y in coords
    ]


DOLLAR_TEMPLATES = [

    Template("HORIZONTAL", make_points([
        (0, 50), (15, 49), (30, 51), (45, 50),
        (60, 49), (75, 50), (90, 51), (100, 50)
    ])),

    Template("CIRCLE", make_points([
        (50, 0), (70, 5), (88, 20), (98, 40),
        (95, 62), (82, 82), (62, 96), (40, 98),
        (20, 87), (5, 68), (0, 47), (7, 26),
        (25, 8), (50, 0)
    ]))
]

dollar_recognizer = Recognizer(DOLLAR_TEMPLATES)

print("Swipe Detector Ready!")
print("DollarPy Recognizer Ready! Templates: HORIZONTAL, CIRCLE")


def classify_with_dollarpy(path_points):

    try:
        dollar_points = [
            Point(float(x), float(y))
            for x, y in path_points
        ]

        result = dollar_recognizer.recognize(dollar_points)

        if isinstance(result, tuple):
            name = result[0]
            score = result[1] if len(result) > 1 else None
        else:
            name = result
            score = None

        return name, score

    except Exception as error:
        print("DollarPy classification error:", error)
        return None, None


# =====================================
# 4. MEDIAPIPE HAND TRACKING
# =====================================

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)


# =====================================
# 5. STATIC GESTURE DETECTION
# =====================================

def point_distance(a, b):
    return math.hypot(
        a.x - b.x,
        a.y - b.y
    )


def detect_static_gesture(hand):

    lm = hand.landmark

    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]

    fingers_extended = []

    for tip, pip in zip(finger_tips, finger_pips):

        fingers_extended.append(
            lm[tip].y < lm[pip].y - 0.015
        )

    extended_count = sum(fingers_extended)

    other_fingers_folded = extended_count == 0
    other_fingers_extended = extended_count == 4

    thumb_tip = lm[4]
    thumb_ip = lm[3]
    thumb_mcp = lm[2]

    thumb_index_gap = point_distance(
        thumb_tip,
        lm[8]
    )

    # OK SIGN
    if (
        thumb_index_gap < 0.045
        and all(fingers_extended[1:])
    ):
        return "OK_SIGN"

    # THUMBS UP / DOWN
    if other_fingers_folded:

        if (
            thumb_tip.y < thumb_ip.y - 0.035
            and thumb_tip.y < thumb_mcp.y - 0.045
        ):
            return "THUMBS_UP"

        if (
            thumb_tip.y > thumb_ip.y + 0.035
            and thumb_tip.y > thumb_mcp.y + 0.045
        ):
            return "THUMBS_DOWN"

    # C SHAPE
    if (
        0.065 < thumb_index_gap < 0.17
        and 0 < extended_count < 4
    ):
        return "C_SHAPE"

    # OPEN PALM
    if other_fingers_extended:
        return "OPEN_PALM"

    # CLOSED FIST
    if other_fingers_folded:
        return "CLOSED_FIST"

    # ONE FINGER
    if (
        fingers_extended[0]
        and not fingers_extended[1]
        and not fingers_extended[2]
        and not fingers_extended[3]
    ):
        return "SELECT_PRODUCT"

    return None


# =====================================
# 6. CAMERA INITIALIZATION
# =====================================

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():

    print("Could not open camera!")

    hands.close()
    client.close()

    raise SystemExit


print("Camera opened successfully!")


# =====================================
# 7. GESTURE SETTINGS
# =====================================

points = []

recording = False

last_position = None
last_movement_time = 0

IDLE_TIME = 0.4
MOVEMENT_THRESHOLD = 8
MIN_POINTS = 5
COOLDOWN_TIME = 1.0

candidate_pose = None
stable_frames = 0

STABLE_FRAMES_REQUIRED = 8

last_sent_pose = None

menu_open = False

last_result = "Waiting..."

cooldown = 0


# =====================================
# 8. START CAMERA PUBLISHER
# =====================================

publisher_thread = threading.Thread(
    target=publish_camera_frames,
    daemon=True
)

publisher_thread.start()


# =====================================
# 9. START SYSTEM
# =====================================

print("\n================================")
print("RESTAURANT MENU GESTURE CONTROL")
print("================================")

print("OPEN PALM: Open Menu")
print("CLOSED FIST: Close Menu")
print("ONE FINGER: Select Product")
print("THUMBS UP: Add Product")
print("THUMBS DOWN: Decline Product")
print("C SHAPE: Open Cart")
print("OK SIGN: Checkout")
print("SWIPE RIGHT: Next Category")
print("SWIPE LEFT: Previous Category")

print("Camera preview appears inside Olive / Table.")
print("Press Ctrl+C here to stop the camera client.")


# =====================================
# 10. MAIN LOOP
# =====================================

try:

    while True:

        success, frame = cap.read()

        if not success:
            print("Failed to read camera frame.")
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = hands.process(rgb)

        height, width, _ = frame.shape

        current_time = time.monotonic()

        current_position = None
        static_gesture = None

        # ---------------------------------
        # HAND DETECTION
        # ---------------------------------

        if results.multi_hand_landmarks:

            hand = results.multi_hand_landmarks[0]

            mp_drawing.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            static_gesture = detect_static_gesture(hand)

            tip = hand.landmark[8]

            x = int(tip.x * width)
            y = int(tip.y * height)

            current_position = (x, y)

        # ---------------------------------
        # STATIC GESTURE RECOGNITION
        # ---------------------------------

        if static_gesture is not None:

            if static_gesture == candidate_pose:
                stable_frames += 1

            else:
                candidate_pose = static_gesture
                stable_frames = 1

            if (
                stable_frames >= STABLE_FRAMES_REQUIRED
                and current_time >= cooldown
                and last_sent_pose != static_gesture
            ):

                print("\nDetected:", static_gesture)

                send_gesture(static_gesture)

                last_sent_pose = static_gesture
                last_result = static_gesture

                if static_gesture == "OPEN_PALM":
                    menu_open = True

                elif static_gesture == "CLOSED_FIST":
                    menu_open = False

                recording = False
                points.clear()

                cooldown = current_time + 0.6

        else:

            candidate_pose = None
            stable_frames = 0
            last_sent_pose = None

        # ---------------------------------
        # SWIPE MOVEMENT RECORDING
        # ---------------------------------

        if (
            static_gesture is None
            and current_position is not None
        ):

            if last_position is not None:

                dx = current_position[0] - last_position[0]
                dy = current_position[1] - last_position[1]

                distance = math.hypot(dx, dy)

                if (
                    not recording
                    and distance >= MOVEMENT_THRESHOLD
                    and current_time >= cooldown
                ):

                    recording = True
                    points = [last_position]

                    last_movement_time = current_time

                    print("\nRecording Swipe...")

                if recording:

                    points.append(current_position)

                    if distance >= MOVEMENT_THRESHOLD:
                        last_movement_time = current_time

            last_position = current_position

        else:

            last_position = current_position

        # ---------------------------------
        # RECOGNIZE MOVEMENT
        # ---------------------------------

        if (
            recording
            and current_time - last_movement_time >= IDLE_TIME
        ):

            recording = False

            if len(points) >= MIN_POINTS:

                dollar_name, dollar_score = classify_with_dollarpy(
                    points
                )

                if dollar_name is not None:

                    print(
                        "DollarPy classification:",
                        dollar_name,
                        "Score:",
                        dollar_score
                    )

                swipe = swipe_detector.detect_path(points)

                if swipe in ("SWIPE_RIGHT", "SWIPE_LEFT"):

                    last_result = swipe

                    print("\nDetected:", swipe)

                    send_gesture(swipe)

                else:

                    last_result = "Not a Swipe"

                    print("Movement was not recognized as a swipe.")

            else:

                last_result = "Movement Too Short"

                print("Movement too short.")

            points.clear()

            cooldown = current_time + COOLDOWN_TIME

        # ---------------------------------
        # DRAW CAMERA INFORMATION
        # ---------------------------------

        cv2.putText(
            frame,
            "Hand Tracking",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            "Menu: " + ("OPEN" if menu_open else "CLOSED"),
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        # ---------------------------------
        # SEND FRAME TO OLIVE / TABLE
        # ---------------------------------

        send_frame_to_menu(frame)


# =====================================
# 11. ERROR HANDLING
# =====================================

except KeyboardInterrupt:

    print("\nStopping camera client...")

except (ConnectionResetError, BrokenPipeError, OSError) as error:

    print("Connection error:", error)

except Exception as error:

    print("Unexpected error:", error)


# =====================================
# 12. CLEANUP
# =====================================

finally:

    publisher_stop.set()

    try:
        frame_queue.put_nowait(None)
    except queue.Full:
        pass

    cap.release()
    hands.close()

    cv2.destroyAllWindows()

    try:
        client.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass

    client.close()

    print("\nRestaurant Menu Client Stopped.")
