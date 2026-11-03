    print(f"Gesture client connected: {address}")
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

                    print("Received gesture:", gesture)
                    gesture_queue.put(gesture)
                    client_socket.sendall(
                        f"Processed: {gesture}\n".encode("utf-8")
                    )
    except (ConnectionResetError, BrokenPipeError, OSError) as error:
        if running:
            print("Gesture client connection ended:", error)

    print("Gesture client disconnected.")


def start_socket_server():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        server_socket.settimeout(1.0)
        print(f"Gesture server running on {HOST}:{PORT}")

        while running:
            try:
                client_socket, address = server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True
            ).start()
    except OSError as error:
        print("Could not start gesture server:", error)
        print("Make sure port", PORT, "is available and menu_server.py is not running.")


def dispatch_gestures():
    while running:
        try:
            gesture = gesture_queue.get(timeout=0.2)
        except queue.Empty:
            continue

        if not page_loaded.wait(timeout=15):
            print("HTML page did not load; skipped gesture:", gesture)
            continue
        if window is None:
            continue

        try:
            safe_gesture = json.dumps(gesture)
            window.evaluate_js(
                f"if (window.handleGesture) window.handleGesture({safe_gesture});"
            )
            print("Forwarded to menu:", gesture)
        except Exception as error:
            print("Could not update menu interface:", error)


def on_loaded():
    page_loaded.set()
    print("Olive / Table interface loaded.")


def on_closing():
    global running
    running = False
    with frame_condition:
        frame_condition.notify_all()

    if server_socket is not None:
        try:
            server_socket.close()
        except OSError:
            pass

    if stream_server is not None:
        try:
            stream_server.shutdown()
            stream_server.server_close()
        except Exception:
            pass

    print("Closing Olive / Table...")


if __name__ == "__main__":
    print("Starting Olive / Table...")
    if not HTML_FILE.exists():
        raise FileNotFoundError(
            f"{HTML_FILE.name} must be in the same folder as this Python file."
        )

    threading.Thread(target=start_socket_server, daemon=True).start()
    threading.Thread(target=start_camera_stream_server, daemon=True).start()
    threading.Thread(target=dispatch_gestures, daemon=True).start()

    window = webview.create_window(
        "Olive / Table",
        str(HTML_FILE),
        width=1200,
        height=800,
        min_size=(900, 650),
        background_color="#f5f2ea"
    )
    window.events.loaded += on_loaded
 print(f"Gesture client connected: {address}")
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

                    print("Received gesture:", gesture)
                    gesture_queue.put(gesture)
                    client_socket.sendall(
                        f"Processed: {gesture}\n".encode("utf-8")
                    )
    except (ConnectionResetError, BrokenPipeError, OSError) as error:
        if running:
            print("Gesture client connection ended:", error)

    print("Gesture client disconnected.")


def start_socket_server():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        server_socket.settimeout(1.0)
        print(f"Gesture server running on {HOST}:{PORT}")

        while running:
            try:
                client_socket, address = server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True
            ).start()
    except OSError as error:
        print("Could not start gesture server:", import json
import queue
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import webview


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
running = True
latest_frame = None
frame_condition = threading.Condition()


class CameraStreamHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global latest_frame

        if self.path != "/frame":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return

        if length <= 0 or length > 2_000_000:
            self.send_error(400)
            return

        frame = self.rfile.read(length)
        with frame_condition:
            latest_frame = frame
            frame_condition.notify_all()

        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        if self.path == "/status":
            body = b"running" if running else b"stopped"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path != "/stream":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "multipart/x-mixed-replace; boundary=frame"
        )
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        last_frame = None
        try:
            while running:
                with frame_condition:
                    frame_condition.wait_for(
                        lambda: not running or (
                            latest_frame is not None and latest_frame is not last_frame
                        ),
                        timeout=1.0
                    )
                    frame = latest_frame

                if not running:
                    break
                if frame is None or frame is last_frame:
                    continue

                last_frame = frame
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(
                    f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                )
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, format, *args):
        return


def start_camera_stream_server():
    global stream_server
    try:
        stream_server = ThreadingHTTPServer(
            (STREAM_HOST, STREAM_PORT),
            CameraStreamHandler
        )
        stream_server.daemon_threads = True
        print(f"Camera preview server: http://{STREAM_HOST}:{STREAM_PORT}/stream")
        stream_server.serve_forever(poll_interval=0.3)
    except OSError as error:
        print("Could not start camera preview server:", error)
        print("Make sure port", STREAM_PORT, "is available.")


def handle_client(client_socket, address):
    print(f"Gesture client connected: {address}")
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

                    print("Received gesture:", gesture)
                    gesture_queue.put(gesture)
                    client_socket.sendall(
                        f"Processed: {gesture}\n".encode("utf-8")
                    )
    except (ConnectionResetError, BrokenPipeError, OSError) as error:
        if running:
            print("Gesture client connection ended:", error)

    print("Gesture client disconnected.")


def start_socket_server():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        server_socket.settimeout(1.0)
        print(f"Gesture server running on {HOST}:{PORT}")

        while running:
            try:
                client_socket, address = server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True
            ).start()
    except OSError as error:
        print("Could not start gesture server:", error)
        print("Make sure port", PORT, "is available and menu_server.py is not running.")


def dispatch_gestures():
    while running:
        try:
            gesture = gesture_queue.get(timeout=0.2)
        except queue.Empty:
            continue

        if not page_loaded.wait(timeout=15):
            print("HTML page did not load; skipped gesture:", gesture)
            continue
        if window is None:
            continue

        try:
            safe_gesture = json.dumps(gesture)
            window.evaluate_js(
                f"if (window.handleGesture) window.handleGesture({safe_gesture});"
            )
            print("Forwarded to menu:", gesture)
        except Exception as error:
            print("Could not update menu interface:", error)


def on_loaded():
    page_loaded.set()
    print("Olive / Table interface loaded.")


def on_closing():
    global running
    running = False
    with frame_condition:
        frame_condition.notify_all()

    if server_socket is not None:
        try:
            server_socket.close()
        except OSError:
            pass

    if stream_server is not None:
        try:
            stream_server.shutdown()
            stream_server.server_close()
        except Exception:
            pass

    print("Closing Olive / Table...")


if __name__ == "__main__":
    print("Starting Olive / Table...")
    if not HTML_FILE.exists():
        raise FileNotFoundError(
            f"{HTML_FILE.name} must be in the same folder as this Python file."
        )

    threading.Thread(target=start_socket_server, daemon=True).start()
    threading.Thread(target=start_camera_stream_server, daemon=True).start()
    threading.Thread(target=dispatch_gestures, daemon=True).start()

    window = webview.create_window(
        "Olive / Table",
        str(HTML_FILE),
        width=1200,
        height=800,
        min_size=(900, 650),
        background_color="#f5f2ea"
    )
    window.events.loaded += on_loaded
    window.events.closing += on_closing
    webview.start(debug=False)
error)
        print("Make sure port", PORT, "is available and menu_server.py is not running.")


def dispatch_gestures():
    while running:
        try:
            gesture = gesture_queue.get(timeout=0.2)
        except queue.Empty:
            continue

        if not page_loaded.wait(timeout=15):
            print("HTML page did not load; skipped gesture:", gesture)
            continue
        if window is None:
            continue

        try:
            safe_gesture = json.dumps(gesture)
            window.evaluate_js(
                f"if (window.handleGesture) window.handleGesture({safe_gesture});"
            )
            print("Forwarded to menu:", gesture)
        except Exception as error:
            print("Could not update menu interface:", error)


def on_loaded():
    page_loaded.set()
    print("Olive / Table interface loaded.")


def on_closing():
    global running
    running = False
    with frame_condition:
        frame_condition.notify_all()

    if server_socket is not None:
        try:
            server_socket.close()
        except OSError:
            pass

    if stream_server is not None:
        try:
            stream_server.shutdown()
            stream_server.server_close()
        except Exception:
            pass

    print("Closing Olive / Table...")


if __name__ == "__main__":
    print("Starting Olive / Table...")
    if not HTML_FILE.exists():
        raise FileNotFoundError(
            f"{HTML_FILE.name} must be in the same folder as this Python file."
        )

    threading.Thread(target=start_socket_server, daemon=True).start()
    threading.Thread(target=start_camera_stream_server, daemon=True).start()
    threading.Thread(target=dispatch_gestures, daemon=True).start()

    window = webview.create_window(
        "Olive / Table",
        str(HTML_FILE),
        width=1200,
        height=800,
        min_size=(900, 650),
        background_color="#f5f2ea"
    )
    window.events.loaded += on_loaded
