
import socket
import threading
import queue
import tkinter as tk
import json
import traceback
from concurrent.futures import Future, TimeoutError
from dataclasses import dataclass, field

from menu_ui import RestaurantMenuUI


HOST = "127.0.0.1"
PORT = 5000

# Queue transfers gestures safely to the Tkinter main thread
gesture_queue = queue.Queue()


@dataclass
class GestureRequest:
    gesture: str
    reply: Future = field(default_factory=Future)


RESPONSE_TIMEOUT = 2


def handle_client(client_socket, address):
    print(f"Gesture Client connected: {address}")

    buffer = ""

    try:
        with client_socket:
            while True:
                data = client_socket.recv(1024)

                if not data:
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    gesture = message.strip()

                    if not gesture:
                        continue

                    print("Received Gesture:", gesture)

                    request = GestureRequest(gesture)
                    gesture_queue.put(request)
                    # Acknowledge only after Tkinter applies the action.
                    try:
                        result = request.reply.result(timeout=RESPONSE_TIMEOUT)
                    except TimeoutError:
                        request.reply.cancel()
                        result = {
                            "ok": False,
                            "gesture": gesture,
                            "error": "The menu did not respond. Restart the menu server.",
                            "state": None,
                        }
                    response = json.dumps(result) + "\n"
                    client_socket.sendall(
                        response.encode("utf-8")
                    )

    except (ConnectionResetError, OSError) as error:
        print("Client connection ended:", error)

    print("Gesture Client disconnected.")


def start_server(server_socket):
    print(f"Server running on {HOST}:{PORT}")
    print("Waiting for Gesture Client...")

    while True:
        try:
            client_socket, address = server_socket.accept()

            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True
            )

            client_thread.start()

        except OSError:
            break


def process_gestures(root, app):
    """Process gestures in the Tkinter main thread."""

    try:
        while True:
            request = gesture_queue.get_nowait()
            if not request.reply.set_running_or_notify_cancel():
                continue

            try:
                print("Updating GUI:", request.gesture)
                applied = request.gesture == "STATUS" or app.handle_gesture(request.gesture)
                root.update_idletasks()
                result = {
                    "ok": bool(applied),
                    "gesture": request.gesture,
                    "state": app.get_state(),
                }
                if not applied:
                    result["error"] = "Gesture is not available in the current menu."
            except Exception as error:
                traceback.print_exc()
                result = {
                    "ok": False,
                    "gesture": request.gesture,
                    "error": str(error),
                    "state": app.get_state(),
                }
            request.reply.set_result(result)

    except queue.Empty:
        pass

    finally:
        # Keep processing future gestures even if one GUI action fails.
        root.after(30, process_gestures, root, app)


def close_application(root, server_socket):
    print("Closing Restaurant Menu...")

    try:
        server_socket.close()
    except OSError:
        pass

    root.destroy()


if __name__ == "__main__":

    # Create TCP server
    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    try:
        server.bind((HOST, PORT))
    except OSError as error:
        server.close()
        raise SystemExit(
            f"Cannot start the menu server: {error}. "
            "Close any older menu server before restarting."
        ) from error
    server.listen(5)

    # Bind first so an older server cannot leave a second, disconnected window.
    root = tk.Tk()
    app = RestaurantMenuUI(root)

    # Start server in a background thread
    server_thread = threading.Thread(
        target=start_server,
        args=(server,),
        daemon=True
    )

    server_thread.start()

    # Start checking for incoming gestures
    root.after(50, process_gestures, root, app)

    # Handle window closing
    root.protocol(
        "WM_DELETE_WINDOW",
        lambda: close_application(root, server)
    )

    print("Restaurant GUI is ready!")

    root.mainloop()
