
import cv2
import mediapipe as mp
import time
import numpy as np

from gesture_controller import GestureController
from hand_pose import detect_static_gesture
from menu_connection import MenuConnection
from camera_control import read_camera_frame


# =====================================
# 1. SOCKET CLIENT
# =====================================

HOST = "127.0.0.1"
PORT = 5000
camera_enabled = True
hand_control_enabled = True

try:
    client = MenuConnection(HOST, PORT)
    print("Connected to Restaurant Menu Server!")

except OSError as error:
    print("Cannot connect to Menu Server:", error)
    print("Please run menu_server_gui.py first.")
    raise SystemExit


def send_gesture(gesture):
    global camera_enabled, hand_control_enabled
    response = client.request(gesture)
    gesture_controller.confirm_menu_state(response["state"]["menu_open"])
    camera_enabled = response["state"].get("camera_enabled", True)
    hand_control_enabled = response["state"].get("hand_control_enabled", True)
    if gesture != "STATUS":
        print("Server Response:", response)
    return response


# =====================================
# 2. GESTURE CONTROLLER
# =====================================

gesture_controller = GestureController()

print("Gesture Controller Ready!")

try:
    send_gesture("STATUS")
except (OSError, RuntimeError) as error:
    print("Cannot confirm menu state:", error)
    client.close()
    raise SystemExit


# =====================================
# 3. MEDIAPIPE HAND TRACKING
# =====================================

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.5
)


# =====================================
# 5. CAMERA
# =====================================

cap = cv2.VideoCapture()


# =====================================
# 6. GESTURE SETTINGS
# =====================================

last_result = "Waiting..."
next_state_sync = 0


# =====================================
# 7. START SYSTEM
# =====================================

print("\n================================")
print("RESTAURANT MENU GESTURE CONTROL")
print("================================")

print("OPEN PALM: Open Menu / Back to Menu")
print("CLOSED FIST: Close Menu")
print("ONE FINGER: Hold left / center / right to select that product")
print("SWIPE RIGHT: Next Category")
print("SWIPE LEFT: Previous Category")
print("Press Q to quit.")


# =====================================
# 8. MAIN LOOP
# =====================================

try:

    while True:

        current_time = time.monotonic()
        if current_time >= next_state_sync:
            send_gesture("STATUS")
            next_state_sync = current_time + 1

        success, frame = read_camera_frame(cap, camera_enabled)

        if not success:
            print("Failed to read camera frame.")
            break

        if frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            results = None
        else:
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb) if hand_control_enabled else None

        current_time = time.monotonic()

        current_position = None
        static_gesture = None
        finger_x = None

        # ---------------------------------
        # HAND DETECTION
        # ---------------------------------

        if results is not None and results.multi_hand_landmarks:

            hand = results.multi_hand_landmarks[0]

            mp_drawing.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            world_hands = results.multi_hand_world_landmarks
            pose_hand = world_hands[0] if world_hands else hand
            static_gesture = detect_static_gesture(pose_hand)

            # Average the wrist and knuckles so finger curling does not move
            # the tracking point as much as a single finger landmark would.
            palm_points = [hand.landmark[index] for index in (0, 5, 9, 13, 17)]
            current_position = (
                sum(point.x for point in palm_points) / len(palm_points),
                sum(point.y for point in palm_points) / len(palm_points),
            )
            finger_x = hand.landmark[8].x

        # ---------------------------------
        # MOVEMENT AND HELD POSES
        # ---------------------------------

        gesture = gesture_controller.update(
            static_gesture, current_position, current_time, finger_x
        )
        if gesture is not None:
            print("\nDetected:", gesture)
            response = send_gesture(gesture)
            last_result = gesture if response["ok"] else "Menu did not apply gesture"
            next_state_sync = current_time + 1

        # ---------------------------------
        # CAMERA DISPLAY
        # ---------------------------------

        height, width = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (width, 135), (32, 32, 32), -1)

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
            "Menu: " + ("OPEN" if gesture_controller.menu_open else "CLOSED"),
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        progress = gesture_controller.hold_progress(current_time)
        swipe_direction, swipe_progress = gesture_controller.swipe_progress()
        if not camera_enabled:
            hint = "Camera off - enable it in the menu"
            progress = 0
        elif not hand_control_enabled:
            hint = "Touch control active - use the menu buttons"
            progress = 0
        elif current_position is None:
            hint = "No hand detected - show your full hand"
            progress = 0
        elif static_gesture == "SELECT_PRODUCT" and not gesture_controller.menu_open:
            hint = "Hold an open palm to open the menu first"
            progress = 0
        elif static_gesture == "SELECT_PRODUCT":
            target = gesture_controller.target_index
            if target is None:
                target = gesture_controller.product_index(finger_x)
            hint = f"Item {target + 1}: hold still ({int(progress * 100)}%)"
            for column in (1, 2):
                cv2.line(frame, (width * column // 3, 140),
                         (width * column // 3, height), (150, 150, 150), 1)
            for column in range(3):
                cv2.putText(frame, str(column + 1),
                            (width * (2 * column + 1) // 6, height - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        elif swipe_direction is not None and static_gesture != "CLOSED_FIST":
            hint = f"Swipe {swipe_direction}: keep moving horizontally"
            progress = swipe_progress
        elif static_gesture is not None:
            pose_name = static_gesture.replace("_", " ").title()
            hint = f"{pose_name}: hold still ({int(progress * 100)}%)"
        else:
            hint = "Show an open palm, a fist, or one index finger"

        cv2.putText(frame, hint, (10, 100), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 2)
        cv2.rectangle(frame, (10, 115), (width - 10, 125), (80, 80, 80), -1)
        if progress > 0:
            cv2.rectangle(frame, (10, 115),
                          (10 + int((width - 20) * progress), 125), (0, 200, 0), -1)

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

except (ConnectionResetError, BrokenPipeError, OSError, RuntimeError) as error:

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
