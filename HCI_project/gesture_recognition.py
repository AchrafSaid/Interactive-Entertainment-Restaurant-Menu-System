
import cv2
import mediapipe as mp

# Initialize MediaPipe Hands
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
    print("Error: Cannot open camera")
    exit()

print("Gesture Recognition Started!")
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
        for hand_landmarks in results.multi_hand_landmarks:

            # Draw hand landmarks
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            landmarks = hand_landmarks.landmark

            # Finger tip and PIP landmark IDs
            fingers = [
                (8, 6),    # Index
                (12, 10),  # Middle
                (16, 14),  # Ring
                (20, 18)   # Pinky
            ]

            extended_fingers = 0

            # Check which fingers are extended
            for tip_id, pip_id in fingers:
                if landmarks[tip_id].y < landmarks[pip_id].y:
                    extended_fingers += 1

            # Classify the gesture
            if extended_fingers >= 3:
                gesture = "OPEN PALM"
            elif extended_fingers <= 1:
                gesture = "CLOSED FIST"
            else:
                gesture = "OTHER GESTURE"

    # Display detected gesture
    cv2.putText(
        frame,
        gesture,
        (30, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2,
        (0, 255, 0),
        3
    )

    cv2.imshow("Restaurant Menu - Gesture Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
hands.close()
cv2.destroyAllWindows()

print("Gesture Recognition Stopped!")
