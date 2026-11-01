import socket

HOST = "127.0.0.1"
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

print("Connected to Restaurant Menu Server!")

gestures = [
    "ZIGZAG",
    "ZIGZAG"
]

for gesture in gestures:
    client.sendall((gesture + "\n").encode("utf-8"))

    response = client.recv(1024).decode("utf-8")
    print("Server Response:", response.strip())

client.close()

print("Client disconnected.")