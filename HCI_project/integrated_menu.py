
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
    exit()


def send_gesture(gesture):

    message = gesture + "\n"
    client.sendall(message.encode("utf-8"))

    response = client.recv(1024).decode("utf-8")
    print("Server Response:", response.strip())


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

    """Detect static hand gestures."""

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

    # Open Palm: Four fingers extended
    if extended_fingers == 4:
        return "OPEN_PALM"

    # Closed Fist: All four fingers folded
    elif extended_fingers == 0:
        return "CLOSED_FIST"

    # One Finger: Index finger only
    elif (
        fingers[0] is True
        and fingers[1] is False
        and fingers[2] is False
        and fingers[3] is False
    ):
        return "SELECT_PRODUCT"

    return None


    """Detect OPEN_PALM and CLOSED_FIST."""

    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]

    extended_fingers = 0

    for tip, pip in zip(finger_tips, finger_pips):

        if hand.landmark[tip].y < hand.landmark[pip].y:
            extended_fingers += 1

    if extended_fingers >= 3:
        return "OPEN_PALM"

    elif extended_fingers <= 1:
        return "CLOSED_FIST"

    return None


# =====================================
# 5. CAMERA
# =====================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("Cannot open camera")

    hands.close()
    client.close()

    exit()


# =====================================
# 6. GESTURE SETTINGS
# =====================================

points = []

recording = False

last_position = None
last_movement_time = 0

IDLE_TIME = 0.8
MOVEMENT_THRESHOLD = 5
MIN_POINTS = 10
COOLDOWN_TIME = 1.5

cooldown = 0


# Static gesture stability

candidate_pose = None
stable_frames = 0

STABLE_FRAMES_REQUIRED = 8

last_sent_pose = None

last_result = "Waiting..."


# =====================================
# 7. START SYSTEM
# =====================================

print("\n================================")
print("RESTAURANT MENU GESTURE CONTROL")
print("================================")

print("OPEN PALM: Open Menu")
print("CLOSED FIST: Close Menu")
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
        # HAND DETECTION + LANDMARKS
        # ---------------------------------

        if results.multi_hand_landmarks:

            hand = results.multi_hand_landmarks[0]

            # Draw 21 hand landmarks and connections

            mp_drawing.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            # Detect static hand gesture

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
                and static_gesture != last_sent_pose
            ):

                last_result = static_gesture

                print("\nDetected:", static_gesture)

                send_gesture(static_gesture)

                last_sent_pose = static_gesture

                # Reset movement recording

                recording = False
                points.clear()

                last_position = current_position

                cooldown = current_time + 0.6

        else:

            candidate_pose = None
            stable_frames = 0


        # ---------------------------------
        # SWIPE MOVEMENT RECORDING
        # ---------------------------------

        # Record movement only when no static gesture is detected

        
       
        # ---------------------------------
        # SWIPE MOVEMENT RECORDING
        # ---------------------------------

        if current_position is not None:

            if last_position is not None:

                distance = math.hypot(
                    current_position[0] - last_position[0],
                    current_position[1] - last_position[1]
                )

                # Start recording when meaningful movement begins
                if (
                    not recording
                    and distance >= MOVEMENT_THRESHOLD
                    and current_time >= cooldown
                ):
                    recording = True
                    points = []
                    print("\nRecording Swipe...")

                # Once recording starts, save EVERY tracked position
                if recording:

                    points.append(current_position)

                    # Update movement time only when the hand moves
                    if distance >= MOVEMENT_THRESHOLD:
                        last_movement_time = current_time

            last_position = current_position

        else:

            # Hand temporarily lost
            last_position = None


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

                    print(
                        "Movement was not recognized as a swipe."
                    )

            else:

                last_result = "Movement Too Short"

                print("Movement too short.")


            # Clear recorded points

            points.clear()

            # Apply cooldown

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

        cv2.imshow(
            "Restaurant Menu Control",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break


# =====================================
# 9. CLEANUP
# =====================================

except (
    ConnectionResetError,
    BrokenPipeError,
    OSError
) as error:

    print("Socket connection error:", error)


finally:

    cap.release()

    hands.close()

    cv2.destroyAllWindows()

    client.close()

    print("\nRestaurant Menu Client Stopped.")
