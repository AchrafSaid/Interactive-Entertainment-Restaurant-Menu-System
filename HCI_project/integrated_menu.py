
import cv2
import mediapipe as mp
import math
import time
import socket

from swipe_detector import SwipeDetector


# =====================================
# 1. SOCKET CLIENT
# =====================================

HOST = "127.0.0.1"
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((HOST, PORT))
    print("Connected to Restaurant Menu Server!")

except ConnectionRefusedError:
    print("Cannot connect to Menu Server!")
    print("Please run menu_server_gui.py first.")
    client.close()
    raise SystemExit


def send_gesture(gesture):
    try:
        message = gesture + "\n"
        client.sendall(message.encode("utf-8"))

        response = client.recv(1024).decode("utf-8")

        if not response:
            raise ConnectionResetError("Server disconnected.")

        print("Server Response:", response.strip())

    except (ConnectionResetError, BrokenPipeError, OSError) as error:
        print("Error sending gesture:", error)
        raise


# =====================================
# 2. SWIPE DETECTOR
# =====================================

swipe_detector = SwipeDetector()

print("Swipe Detector Ready!")


# =====================================
# 3. MEDIAPIPE HAND TRACKING
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
# 4. STATIC GESTURE DETECTION
# =====================================

def detect_static_gesture(hand):

    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]

    fingers = []

    for tip, pip in zip(finger_tips, finger_pips):

        extended = (
            hand.landmark[tip].y <
            hand.landmark[pip].y
        )

        fingers.append(extended)

    extended_fingers = sum(fingers)

    # OPEN PALM
    if extended_fingers == 4:
        return "OPEN_PALM"

    # CLOSED FIST
    elif extended_fingers == 0:
        return "CLOSED_FIST"

    # SELECT PRODUCT
    elif (
        fingers[0]
        and not fingers[1]
        and not fingers[2]
        and not fingers[3]
    ):
        return "SELECT_PRODUCT"

    return None


# =====================================
# 5. CAMERA
# =====================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("Cannot open camera")

    hands.close()
    client.close()

    raise SystemExit


# =====================================
# 6. GESTURE SETTINGS
# =====================================

points = []

recording = False

last_position = None
last_movement_time = 0

IDLE_TIME = 0.4
MOVEMENT_THRESHOLD = 8
MIN_POINTS = 5
COOLDOWN_TIME = 1.0

# Static gesture stability
candidate_pose = None
stable_frames = 0

STABLE_FRAMES_REQUIRED = 8

last_sent_pose = None

# Menu state
menu_open = False

last_result = "Waiting..."

cooldown = 0


# =====================================
# 7. START SYSTEM
# =====================================

print("\n================================")
print("RESTAURANT MENU GESTURE CONTROL")
print("================================")

print("OPEN PALM: Open Menu")
print("CLOSED FIST: Close Menu")
print("ONE FINGER: Select Product")
print("SWIPE RIGHT: Next Category")
print("SWIPE LEFT: Previous Category")
print("Press Q to quit.")


# =====================================
# 8. MAIN LOOP
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

            # Track index fingertip
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
            ):

                # OPEN MENU only if closed
                if (
                    static_gesture == "OPEN_PALM"
                    and not menu_open
                ):

                    print("\nDetected: OPEN_PALM")
                    send_gesture("OPEN_PALM")

                    menu_open = True
                    last_result = "OPEN_PALM"

                    recording = False
                    points.clear()

                    cooldown = current_time + 0.6

                # CLOSE MENU only if open
                elif (
                    static_gesture == "CLOSED_FIST"
                    and menu_open
                ):

                    print("\nDetected: CLOSED_FIST")
                    send_gesture("CLOSED_FIST")

                    menu_open = False
                    last_result = "CLOSED_FIST"

                    recording = False
                    points.clear()

                    cooldown = current_time + 0.6

                # SELECT PRODUCT
                elif (
                    static_gesture == "SELECT_PRODUCT"
                    and last_sent_pose != "SELECT_PRODUCT"
                ):

                    print("\nDetected: SELECT_PRODUCT")
                    send_gesture("SELECT_PRODUCT")

                    last_sent_pose = "SELECT_PRODUCT"
                    last_result = "SELECT_PRODUCT"

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

                # Start recording movement
                if (
                    not recording
                    and distance >= MOVEMENT_THRESHOLD
                    and current_time >= cooldown
                ):

                    recording = True
                    points = [last_position]

                    last_movement_time = current_time

                    print("\nRecording Swipe...")

                # Save movement positions
                if recording:

                    points.append(current_position)

                    if distance >= MOVEMENT_THRESHOLD:
                        last_movement_time = current_time

            last_position = current_position

        else:

            last_position = current_position

        # ---------------------------------
        # RECOGNIZE SWIPE
        # ---------------------------------

        if (
            recording
            and current_time - last_movement_time >= IDLE_TIME
        ):

            recording = False

            if len(points) >= MIN_POINTS:

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
        # CAMERA DISPLAY
        # ---------------------------------

        cv2.putText(
            frame,
            "Gesture: " + last_result,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
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

        cv2.imshow(
            "Restaurant Menu Control",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break


# =====================================
# 9. ERROR HANDLING
# =====================================

except (ConnectionResetError, BrokenPipeError, OSError) as error:

    print("Connection error:", error)

except Exception as error:

    print("Unexpected error:", error)


# =====================================
# 10. CLEANUP
# =====================================

finally:

    cap.release()
    hands.close()
    cv2.destroyAllWindows()
    client.close()

    print("\nRestaurant Menu Client Stopped.")
