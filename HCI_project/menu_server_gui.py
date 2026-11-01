
import socket
import threading
import queue
import tkinter as tk

from menu_ui import RestaurantMenuUI


HOST = "127.0.0.1"
PORT = 5000

# Queue transfers gestures safely to the Tkinter main thread
gesture_queue = queue.Queue()


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

                    # Send gesture to the GUI queue
                    gesture_queue.put(gesture)

                    # Reply to the gesture client
                    response = f"Processed: {gesture}\n"
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
            gesture = gesture_queue.get_nowait()

            print("Updating GUI:", gesture)
            app.handle_gesture(gesture)

    except queue.Empty:
        pass

    # Check the queue again after 50 milliseconds
    root.after(50, process_gestures, root, app)


def close_application(root, server_socket):
    print("Closing Restaurant Menu...")

    try:
        server_socket.close()
    except OSError:
        pass

    root.destroy()


if __name__ == "__main__":

    # Create the GUI
    root = tk.Tk()
    app = RestaurantMenuUI(root)

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

    server.bind((HOST, PORT))
    server.listen(5)

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
