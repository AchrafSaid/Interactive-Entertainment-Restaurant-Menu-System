"""Built-in hand controller for every Olive / Table screen."""
import sys

if __name__ == "__main__":
    from run_menu import ensure_runtime
    ensure_runtime()

import time
import cv2
import mediapipe as mp
from hand_input import HandInput

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480


class OliveTableApp:
    def __init__(self):
        self.window = None
        self.running = False
        self.cap = None
        self.hands = None
        self.camera_allowed = lambda: False
        self.publish_frame = lambda frame: None
        self.gesture_sink = None
        self.hand_sink = lambda event: None
        self.report_camera_error = print
        self.input = HandInput()
        self.status = "Swipe to move, hold one finger to select"

    def release_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.hands is not None:
            self.hands.close()
            self.hands = None
        self.publish_frame(None)
        self.input.lost()

    def camera_loop(self):
        last_preview = last_input = 0
        was_visible = False
        try:
            while self.running:
                if not self.camera_allowed():
                    if self.cap is not None or self.hands is not None:
                        self.release_camera()
                    time.sleep(0.05)
                    continue
                if self.cap is None:
                    self.cap = cv2.VideoCapture(CAMERA_INDEX)
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not self.cap.isOpened():
                        self.report_camera_error("Camera unavailable. Close other camera apps or use touch.")
                        self.release_camera()
                        continue
                    self.hands = mp.solutions.hands.Hands(
                        max_num_hands=1, model_complexity=0,
                        min_detection_confidence=0.65, min_tracking_confidence=0.65)
                ok, frame = self.cap.read()
                if not ok:
                    self.report_camera_error("The camera stopped responding. Restart hand control or use touch.")
                    self.release_camera()
                    continue
                frame = cv2.flip(frame, 1)
                result = self.hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                now = time.monotonic()
                if result.multi_hand_landmarks:
                    hand = result.multi_hand_landmarks[0]
                    event = self.input.from_landmarks(hand, now)
                    if event["action"] not in ("pose", "scroll") or now - last_input >= 0.04:
                        self.hand_sink(event)
                        last_input = now
                    was_visible = True
                    self.status = {"select":"One finger: hold to select", "scroll":"Two fingers: scroll",
                                   "back":"Fist: close / go back", "pause":"Swipe to move the highlight",
                                   "menu":"Open palm: open menu", "add":"Thumbs up: add product",
                                   "decline":"Thumbs down: decline product", "cart":"C shape: open cart",
                                   "checkout":"OK sign: confirm checkout", "games":"Rock sign: games",
                                   "rewards":"Three fingers: rewards"}.get(event.get("pose"), "Move your hand closer")
                    mp.solutions.drawing_utils.draw_landmarks(frame, hand, mp.solutions.hands.HAND_CONNECTIONS)
                elif was_visible:
                    self.hand_sink(self.input.lost())
                    was_visible = False
                    self.status = "Show one hand to the camera"
                if now - last_preview >= 0.09:
                    cv2.putText(frame, self.status, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (190, 255, 200), 1)
                    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
                    if ok:
                        self.publish_frame(encoded.tobytes())
                    last_preview = now
        except Exception as error:
            self.report_camera_error(f"Hand control stopped: {error}. Touch controls are available.")
        finally:
            self.release_camera()

    def start(self):
        import menu_server_gui
        return menu_server_gui.main(camera_controller_instance=self, camera_requested=True)


if __name__ == "__main__":
    if "--check" in sys.argv:
        from run_menu import check_gesture_runtime
        raise SystemExit(check_gesture_runtime())
    raise SystemExit(OliveTableApp().start())
