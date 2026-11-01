
import cv2
import mediapipe as mp
from collections import deque
import time

# Initialize MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Open camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    exit()

# Store recent hand positions
positions = deque(maxlen=15)

last_gesture = "Waiting..."
last_detection_time = 0

print("Swipe Recognition Started!")
print("Move your hand LEFT or RIGHT.")
print("Press Q to quit.")

while True:
    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = hands.process(rgb_frame)

    gesture = "No Hand Detected"

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]

        mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS
        )

        # Track the center of the palm (landmark 9)
        palm = hand_landmarks.landmark[9]

        x = palm.x
        y = palm.y

        positions.append((x, y))

        # Detect movement after collecting 15 positions
        if len(positions) == 15:
            start_x, start_y = positions[0]
            end_x, end_y = positions[-1]

            delta_x = end_x - start_x
            delta_y = end_y - start_y

            current_time = time.time()

            # Prevent repeated detections
            if current_time - last_detection_time > 1.0:

                if abs(delta_x) > 0.18 and abs(delta_x) > abs(delta_y) * 1.5:

                    if delta_x > 0:
                        gesture = "SWIPE RIGHT"
                    else:
                        gesture = "SWIPE LEFT"

                    last_gesture = gesture
                    last_detection_time = current_time

                    # Clear old positions
                    positions.clear()

                else:
                    gesture = "Move your hand horizontally"

        # Draw tracking point
        height, width, _ = frame.shape
        point_x = int(x * width)
        point_y = int(y * height)

        cv2.circle(
            frame,
            (point_x, point_y),
            10,
            (0, 255, 0),
            -1
        )

    else:
        positions.clear()

    # Display current gesture
    cv2.putText(
        frame,
        gesture if gesture != "No Hand Detected" else last_gesture,
        (30, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        3
    )

    cv2.imshow("Restaurant Menu - Swipe Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
hands.close()
cv2.destroyAllWindows()

print("Swipe Recognition Stopped!")
