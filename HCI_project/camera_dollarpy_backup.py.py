
import cv2
import mediapipe as mp
from dollarpy import Recognizer, Template, Point
import math

# =====================================
# 1. MediaPipe Initialization
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
# 2. Camera Initialization
# =====================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Cannot open camera")
    exit()

# =====================================
# 3. Gesture Variables
# =====================================

templates = []
recognizer = None

points = []

recording = False
recording_name = ""

last_gesture = "No gesture tested"
last_score = 0.0

# =====================================
# 4. Start Recording Function
# =====================================

def start_recording(name):
    global recording, recording_name, points

    recording = True
    recording_name = name
    points = []

    print(f"\nRecording started: {name}")
    print("Draw your gesture, then press SPACE to finish.")

# =====================================
# 5. Convert Points for DollarPy
# =====================================

def convert_points(raw_points):
    return [
        Point(float(x), float(y))
        for x, y in raw_points
    ]

# =====================================
# 6. Finish Recording Function
# =====================================

def finish_recording():
    global recording, recognizer
    global last_gesture, last_score

    recording = False

    if len(points) < 10:
        print("Not enough points! Please record again.")
        return

    dollar_points = convert_points(points)

    if recording_name == "TEST":
        if len(templates) < 2:
            print("Record V_SHAPE and ZIGZAG templates first!")
            return

        recognizer = Recognizer(templates)

        result = recognizer.recognize(dollar_points)

        if result:
            last_gesture = result[0]
            last_score = float(result[1])

            print("\nDetected Gesture:", last_gesture)
            print("Recognition Score:", round(last_score, 3))

        else:
            last_gesture = "No Match"
            last_score = 0.0
            print("No gesture recognized.")

    else:
        template = Template(
            recording_name,
            dollar_points
        )

        templates.append(template)

        recognizer = Recognizer(templates)

        print(f"\nTemplate saved: {recording_name}")
        print("Total templates:", len(templates))

    points.clear()

# =====================================
# 7. Main Camera Loop
# =====================================

print("\n=================================")
print("DOLLARPY GESTURE RECOGNITION")
print("=================================")
print("V = Record V Shape")
print("Z = Record Zigzag")
print("T = Record a test gesture")
print("SPACE = Finish recording")
print("Q = Quit")
print("=================================\n")

while True:

    success, frame = cap.read()

    if not success:
        break

    frame = cv2.flip(frame, 1)

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = hands.process(rgb_frame)

    height, width, _ = frame.shape

    # =================================
    # 8. Hand Tracking
    # =================================

    if results.multi_hand_landmarks:

        hand_landmarks = results.multi_hand_landmarks[0]

        mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS
        )

        # Index finger tip
        index_tip = hand_landmarks.landmark[8]

        x = int(index_tip.x * width)
        y = int(index_tip.y * height)

        cv2.circle(
            frame,
            (x, y),
            8,
            (0, 255, 0),
            -1
        )

        # =================================
        # 9. Collect Gesture Points
        # =================================

        if recording:

            # Reduce duplicate points
            if not points:
                points.append((x, y))

            else:
                previous_x, previous_y = points[-1]

                distance = math.hypot(
                    x - previous_x,
                    y - previous_y
                )

                if distance >= 3:
                    points.append((x, y))

        # =================================
        # 10. Draw Gesture Path
        # =================================

        if len(points) > 1:

            for i in range(1, len(points)):

                cv2.line(
                    frame,
                    points[i - 1],
                    points[i],
                    (255, 0, 0),
                    3
                )

    # =================================
    # 11. Display Information
    # =================================

    if recording:
        status = f"RECORDING: {recording_name}"

    else:
        status = "READY"

    cv2.putText(
        frame,
        status,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Points: {len(points)}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Saved Templates: {len(templates)}",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Last Result: {last_gesture}",
        (20, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.imshow(
        "DollarPy - Gesture Recording",
        frame
    )

    # =================================
    # 12. Keyboard Controls
    # =================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord('v') and not recording:
        start_recording("V_SHAPE")

    elif key == ord('z') and not recording:
        start_recording("ZIGZAG")

    elif key == ord('t') and not recording:
        start_recording("TEST")

    elif key == 32 and recording:
        finish_recording()

    elif key == ord('q'):
        break

# =====================================
# 13. Release Resources
# =====================================

cap.release()
hands.close()
cv2.destroyAllWindows()

print("\nProgram stopped successfully!")
