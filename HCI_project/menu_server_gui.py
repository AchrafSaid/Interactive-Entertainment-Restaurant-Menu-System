"""Desktop HTML host: Bluetooth sessions, gesture dispatch and live camera preview."""

import importlib.util
import json
import queue
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from bluetooth_bridge import BluetoothBridge

HOST = "127.0.0.1"
PORT = 5000
STREAM_HOST = "127.0.0.1"
STREAM_PORT = 8765
HTML_FILE = Path(__file__).with_name("index.html")

gesture_queue = queue.Queue()
window = None
page_loaded = threading.Event()
server_socket = None
stream_server = None
bluetooth = None
camera_controller = None
camera_thread = None
running = False
latest_frame = None
latest_hand_event = None
hand_event_lock = threading.Lock()
frame_condition = threading.Condition()


def camera_active():
    state = bluetooth.get_state() if bluetooth is not None else {}
    return running and state.get("camera_enabled", False)


def publish_camera_frame(frame):
    global latest_frame
    if frame is not None and not camera_active():
        return
    with frame_condition:
        latest_frame = frame
        frame_condition.notify_all()


def submit_gesture(gesture):
    state = bluetooth.get_state() if bluetooth is not None else {}
    if not state.get("access_allowed"):
        return False
    gesture_queue.put((state["session_id"], gesture))
    return True


def submit_hand_event(event):
    """Camera input can choose Bluetooth or a guest visit on the first page."""
    global latest_hand_event
    if not camera_active():
        return False
    state = bluetooth.get_state()
    entry = (state["session_id"], event)
    # Discrete gestures are queued so they are never overwritten by motion samples.
    if event.get("action") in ("click", "back", "select", "swipe", "shortcut"):
        gesture_queue.put(entry)
    else:
        # Replace motion samples rather than allowing a slow UI to build lag.
        with hand_event_lock:
            latest_hand_event = entry
    return True


class CameraStreamHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/frame":
            self.send_error(404)
            return
        if not camera_active():
            self.send_error(403, "Connect Bluetooth and enable hand control first")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if not 0 < length <= 2_000_000:
            self.send_error(400)
            return
        publish_camera_frame(self.rfile.read(length))
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        if self.path in ("/status", "/session"):
            if self.path == "/status":
                body = b"running" if running else b"stopped"
                content_type = "text/plain"
            else:
                state = bluetooth.get_state() if bluetooth is not None else {}
                body = json.dumps({"connected": bool(state.get("connected")),
                                   "camera_enabled": bool(state.get("camera_enabled"))}).encode("utf-8")
                content_type = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path != "/stream":
            self.send_error(404)
            return
        if not camera_active():
            self.send_error(403, "Camera is off")
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Connection", "close")
        self.end_headers()
        last_frame = None
        try:
            while running and camera_active():
                with frame_condition:
                    frame_condition.wait_for(lambda: not running or (
                        latest_frame is not None and latest_frame is not last_frame), timeout=0.5)
                    frame = latest_frame
                if not running or not camera_active():
                    break
                if frame is None or frame is last_frame:
                    continue
                last_frame = frame
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                self.wfile.write(frame + b"\r\n")
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, format, *args):
        return


def handle_client(client_socket, address):
    buffer = ""
    try:
        with client_socket:
            while running:
                data = client_socket.recv(1024)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    gesture = message.strip()
                    if not gesture:
                        continue
                    response = f"Processed: {gesture}" if submit_gesture(gesture) else "Bluetooth connection required"
                    client_socket.sendall((response + "\n").encode("utf-8"))
    except (ConnectionResetError, BrokenPipeError, OSError):
        pass


def start_socket_server():
    while running:
        try:
            client_socket, address = server_socket.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        threading.Thread(target=handle_client, args=(client_socket, address), daemon=True).start()


def dispatch_gestures():
    global latest_hand_event
    while running:
        try:
            session_id, gesture = gesture_queue.get(timeout=0.025)
        except queue.Empty:
            with hand_event_lock:
                pending, latest_hand_event = latest_hand_event, None
            if pending is None:
                continue
            session_id, gesture = pending
        state = bluetooth.get_state()
        camera_event = isinstance(gesture, dict) and gesture.get("type") == "hand"
        if state["session_id"] != session_id or not page_loaded.is_set():
            continue
        if not (state["camera_enabled"] if camera_event else state["access_allowed"]):
            continue
        try:
            window.evaluate_js(f"if (window.handleGesture) window.handleGesture({json.dumps(gesture)});")
        except Exception as error:
            if running:
                print("Could not update menu interface:", error)


def ensure_camera(enabled):
    global camera_controller, camera_thread
    if not enabled:
        publish_camera_frame(None)
        return
    if camera_thread is not None and camera_thread.is_alive():
        return
    if camera_controller is None:
        from integrated_menu import OliveTableApp
        camera_controller = OliveTableApp()
    camera_controller.window = window
    camera_controller.running = True
    camera_controller.camera_allowed = camera_active
    camera_controller.publish_frame = publish_camera_frame
    camera_controller.gesture_sink = submit_gesture
    camera_controller.hand_sink = submit_hand_event
    camera_controller.report_camera_error = bluetooth._report_camera_error
    camera_thread = threading.Thread(target=camera_controller.camera_loop, daemon=True)
    camera_thread.start()


def on_loaded():
    page_loaded.set()
    if bluetooth._auto_camera:
        bluetooth.set_camera(True)


def on_closing():
    global running
    if not running:
        return
    running = False
    if camera_controller is not None:
        camera_controller.running = False
    publish_camera_frame(None)
    if bluetooth is not None:
        bluetooth._close()
    if server_socket is not None:
        server_socket.close()
    if stream_server is not None:
        stream_server.shutdown()
        stream_server.server_close()
    if camera_thread is not None and camera_thread.is_alive():
        camera_thread.join(timeout=2)
    page_loaded.clear()


def main(camera_controller_instance=None, camera_requested=False, test_callback=None, bridge=None):
    global running, window, server_socket, stream_server, bluetooth, camera_controller, camera_thread
    import webview
    if not HTML_FILE.exists():
        raise FileNotFoundError(f"Missing desktop interface: {HTML_FILE}")
    camera_controller = camera_controller_instance
    camera_thread = None
    page_loaded.clear()
    running = True
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        server_socket.settimeout(0.5)
        stream_server = ThreadingHTTPServer((STREAM_HOST, STREAM_PORT), CameraStreamHandler)
        stream_server.daemon_threads = True
    except OSError as error:
        running = False
        server_socket.close()
        print("Cannot start Olive / Table. Close another copy using port 5000 or 8765:", error)
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk(); root.withdraw()
            messagebox.showerror("Olive / Table", "The app may already be running. Close the other copy and try again.\n\nLocal ports 5000 and 8765 must be available.", parent=root)
            root.destroy()
        except Exception:
            pass
        return 1
    camera_available = importlib.util.find_spec("mediapipe") is not None and importlib.util.find_spec("cv2") is not None
    bluetooth = bridge or BluetoothBridge(camera_control=ensure_camera, camera_available=camera_available,
                                          auto_camera=camera_requested)
    bluetooth._start()
    threading.Thread(target=start_socket_server, daemon=True).start()
    threading.Thread(target=stream_server.serve_forever, kwargs={"poll_interval":0.2}, daemon=True).start()
    threading.Thread(target=dispatch_gestures, daemon=True).start()
    try:
        window = webview.create_window("Olive / Table", str(HTML_FILE), js_api=bluetooth,
                                      width=1200, height=800, min_size=(900,650), background_color="#f5f2ea")
        window.events.loaded += on_loaded
        window.events.closing += on_closing
        webview.start(func=test_callback, gui="edgechromium", debug=False)
    finally:
        on_closing()
    return 0


if __name__ == "__main__":
    from run_menu import main as launch
    raise SystemExit(launch())
