
import socket

HOST = "127.0.0.1"
PORT = 5000

def send_gesture(gesture):

    try:

        with socket.create_connection(
            (HOST, PORT),
            timeout=5
        ) as client:

            client.settimeout(5)

            print("Connected to Restaurant Menu Server!")

            client.sendall(
                (gesture + "\n").encode("utf-8")
            )

            response = client.recv(1024).decode("utf-8")

            print("Server Response:", response.strip())

    except ConnectionRefusedError:

        print("ERROR: Server is not running.")

    except socket.timeout:

        print("ERROR: Server response timed out.")

    except OSError as error:

        print("Socket error:", error)


if __name__ == "__main__":

    test_gestures = [
        "SWIPE_RIGHT",
        "SWIPE_LEFT",
        "OPEN_PALM",
        "CLOSED_FIST"
    ]

    for gesture in test_gestures:

        print("\nSending:", gesture)

        send_gesture(gesture)
