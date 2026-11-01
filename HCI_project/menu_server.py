
import socket
from menu_controller import MenuController

HOST = "127.0.0.1"
PORT = 5000

# Initialize restaurant menu
menu = MenuController()

# Create TCP server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind((HOST, PORT))
server.listen(1)

print("\n================================")
print("RESTAURANT MENU SERVER")
print("================================")
print(f"Server running on {HOST}:{PORT}")
print("Waiting for Gesture Client...")
print("================================\n")

try:
    while True:
        client_socket, client_address = server.accept()

        print(f"Client connected: {client_address}")

        with client_socket:
            buffer = ""

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

                    print("\nReceived from Client:", gesture)

                    if gesture == "ZIGZAG":

                        if menu.game_open:
                            response = "Game is already open!"
                            print(response)

                        else:
                            menu.handle_gesture(gesture)
                            response = "Game opened successfully!"

                    else:
                        menu.handle_gesture(gesture)
                        response = f"Processed: {gesture}"

                    client_socket.sendall(
                        f"{response}\n".encode("utf-8")
                    )

        print("Client disconnected.")

except KeyboardInterrupt:
    print("\nServer stopped by user.")

finally:
    server.close()
    print("Server closed.")
