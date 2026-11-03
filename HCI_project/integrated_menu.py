
from pathlib import Path
import threading
import time
import math

import cv2
import mediapipe as mp
import webview


# ==========================================
# CONFIGURATION
# ==========================================

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

STABLE_FRAMES = 8
GESTURE_COOLDOWN = 1.0

MIN_SWIPE_DISTANCE = 100
MAX_SWIPE_DURATION = 0.9
MIN_SWIPE_DURATION = 0.12
SWIPE_COOLDOWN = 0.8
SWIPE_STOP_TIME = 0.12

SELECT_HOLD_TIME = 0.7

# ==========================================
# APPLICATION
# ==========================================

class OliveTableApp:

    def __init__(self):

        self.window = None
        self.running = False

        self.cap = None
        self.hands = None

        self.last_pose = None
        self.pose_frames = 0
        self.last_gesture_time = 0
        self.sent_pose = None

        self.last_swipe_time = 0

        self.swipe_active = False
        self.swipe_start = None
        self.swipe_previous = None
        self.swipe_started_at = 0
        self.swipe_last_motion = 0

        self.index_started_at = None
        self.index_start_point = None
        self.select_sent = False

        self.status = "Show your hand"

    # ======================================
    # SEND TO HTML
    # ======================================

    def send_gesture(self, gesture):

        if not self.window:
            return

        now = time.monotonic()

        if gesture.startswith("SWIPE_"):

            if now - self.last_swipe_time < SWIPE_COOLDOWN:
                return

            self.last_swipe_time = now

        print("Gesture:", gesture)
        self.status = gesture

        try:

            self.window.evaluate_js(
                "window.handleGesture("
                + repr(gesture)
                + ")"
            )

        except Exception as error:

            print("JavaScript error:", error)

    # ======================================
    # DISTANCE
    # ======================================

    @staticmethod
    def distance(a, b):

        return math.hypot(
            a[0] - b[0],
            a[1] - b[1]
        )

    # ======================================
    # FINGER DETECTION
    # ======================================

    @staticmethod
    def fingers_up(hand):

        lm = hand.landmark

        # Finger tips compared with middle joints.
        fingers = [
            lm[8].y < lm[6].y,
            lm[12].y < lm[10].y,
            lm[16].y < lm[14].y,
            lm[20].y < lm[18].y
        ]

        # Thumb direction is evaluated using x position.
        # This is a basic camera-facing heuristic.
        thumb_extended = abs(lm[4].x - lm[2].x) > 0.055

        return thumb_extended, fingers

    # ======================================
    # POSE DETECTION
    # ======================================

    @staticmethod
    def detect_pose(hand):

        lm = hand.landmark

        thumb, fingers = OliveTableApp.fingers_up(hand)

        thumb_index = math.hypot(
            lm[4].x - lm[8].x,
            lm[4].y - lm[8].y
        )

        # OPEN PALM
        if all(fingers):
            return "OPEN_PALM"

        # CLOSED FIST
        if not any(fingers) and not thumb:
            return "CLOSED_FIST"

        # THUMBS UP / DOWN
        if thumb and not any(fingers):

            if lm[4].y < lm[3].y - 0.04:
                return "THUMBS_UP"

            if lm[4].y > lm[3].y + 0.04:
                return "THUMBS_DOWN"

        # OK SIGN
        if (
            thumb_index < 0.055
            and fingers[1]
            and fingers[2]
            and fingers[3]
        ):
            return "OK_SIGN"

        # INDEX FINGER ONLY
        if fingers == [True, False, False, False]:
            return "SELECT_PRODUCT"

        return None

    # ======================================
    # RESET TRACKING
    # ======================================

    def reset_tracking(self):

        self.swipe_active = False
        self.swipe_start = None
        self.swipe_previous = None
        self.swipe_started_at = 0
        self.swipe_last_motion = 0

        self.index_started_at = None
        self.index_start_point = None
        self.select_sent = False

    # ======================================
    # SWIPE DETECTION
    # ======================================

    def detect_swipe(self, point, now):

        if self.swipe_start is None:

            self.swipe_start = point
            self.swipe_previous = point
            self.swipe_started_at = now
            self.swipe_last_motion = now
            self.swipe_active = False

            return None

        movement = self.distance(
            point,
            self.swipe_previous
        )

        # Compare current position with previous frame.
        if movement >= 3:
            self.swipe_last_motion = now

        self.swipe_previous = point

        dx = point[0] - self.swipe_start[0]
        dy = point[1] - self.swipe_start[1]

        total_distance = math.hypot(dx, dy)

        duration = now - self.swipe_started_at

        stopped = (
            now - self.swipe_last_motion >= SWIPE_STOP_TIME
        )

        if (
            total_distance >= MIN_SWIPE_DISTANCE
            and MIN_SWIPE_DURATION <= duration <= MAX_SWIPE_DURATION
            and stopped
        ):

            if abs(dx) > abs(dy) * 1.2:

                gesture = (
                    "SWIPE_RIGHT" if dx > 0
                    else "SWIPE_LEFT"
                )

            else:

                gesture = (
                    "SWIPE_DOWN" if dy > 0
                    else "SWIPE_UP"
                )

            self.swipe_active = True

            return gesture

        if duration > MAX_SWIPE_DURATION:

            self.swipe_start = point
            self.swipe_previous = point
            self.swipe_started_at = now
            self.swipe_last_motion = now

        return None

    # ======================================
    # SELECT PRODUCT
    # ======================================

    def detect_select(self, point, now):

        if self.index_started_at is None:

            self.index_started_at = now
            self.index_start_point = point
            self.select_sent = False

            return None

        movement = self.distance(
            point,
            self.index_start_point
        )

        if (
            movement < 30
            and now - self.index_started_at >= SELECT_HOLD_TIME
            and not self.select_sent
        ):

            self.select_sent = True

            return "SELECT_PRODUCT"

        if movement >= 30:

            self.index_started_at = now
            self.index_start_point = point
            self.select_sent = False

        return None

    # ======================================
    # STATIC GESTURES
    # ======================================

    def process_static_pose(self, pose, now):

        if pose is None:

            self.last_pose = None
            self.pose_frames = 0
            self.sent_pose = None

            return

        if pose != self.last_pose:

            self.last_pose = pose
            self.pose_frames = 1
            self.sent_pose = None

            return

        self.pose_frames += 1

        if (
            self.pose_frames >= STABLE_FRAMES
            and self.sent_pose != pose
            and now - self.last_gesture_time >= GESTURE_COOLDOWN
        ):

            self.send_gesture(pose)

            self.last_gesture_time = now
            self.sent_pose = pose

    # ======================================
    # CAMERA LOOP
    # ======================================

    def camera_loop(self):

        self.cap = cv2.VideoCapture(CAMERA_INDEX)

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            FRAME_WIDTH
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            FRAME_HEIGHT
        )

        if not self.cap.isOpened():

            print("ERROR: Camera could not open.")
            self.running = False
            return

        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils

        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

        print("Camera started.")

        try:

            while self.running:

                success, frame = self.cap.read()

                if not success:
                    continue

                frame = cv2.flip(frame, 1)

                rgb = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                results = self.hands.process(rgb)

                now = time.monotonic()

                hand = None

                if results.multi_hand_landmarks:
                    hand = results.multi_hand_landmarks[0]

                if hand is None:

                    self.process_static_pose(None, now)
                    self.reset_tracking()

                    self.status = "Show your hand"

                else:

                    mp_draw.draw_landmarks(
                        frame,
                        hand,
                        mp_hands.HAND_CONNECTIONS
                    )

                    lm = hand.landmark

                    point = (
                        int(lm[8].x * frame.shape[1]),
                        int(lm[8].y * frame.shape[0])
                    )

                    thumb, fingers = self.fingers_up(hand)

                    index_only = (
                        fingers == [True, False, False, False]
                    )

                    if index_only:

                        # Detect swipe first.
                        swipe = self.detect_swipe(
                            point,
                            now
                        )

                        if swipe:

                            self.send_gesture(swipe)

                            self.reset_tracking()

                        else:

                            # Select only when index finger stays still.
                            select = self.detect_select(
                                point,
                                now
                            )

                            if select:
                                self.send_gesture(select)

                    else:

                        self.reset_tracking()

                        pose = self.detect_pose(hand)

                        self.process_static_pose(
                            pose,
                            now
                        )

                    cv2.circle(
                        frame,
                        point,
                        8,
                        (0, 255, 0),
                        -1
                    )

                cv2.putText(
                    frame,
                    "OLIVE / TABLE",
                    (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    "Gesture: " + self.status,
                    (15, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2
                )

                cv2.imshow(
                    "Olive / Table - Camera",
                    frame
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):

                    self.running = False
                    break

        finally:

            if self.cap:
                self.cap.release()

            if self.hands:
                self.hands.close()

            cv2.destroyAllWindows()

            print("Camera stopped.")

    # ======================================
    # START APP
    # ======================================

    def start(self):

        html_file = Path(__file__).with_name(
            "olive_table_with_gesture_sidebar.html"
        )

        if not html_file.exists():

            raise FileNotFoundError(
                f"HTML file not found: {html_file}"
            )

        self.running = True

        self.window = webview.create_window(
            "Olive / Table",
            html_file.resolve().as_uri(),
            width=1200,
            height=800,
            min_size=(800, 600),
            background_color="#f5f2ea"
        )

        self.window.events.loaded += self.on_loaded

        try:

            webview.start(debug=False)

        finally:

            self.running = False

    def on_loaded(self):

        threading.Thread(
            target=self.camera_loop,
            daemon=True
        ).start()


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    app = OliveTableApp()
    app.start()
