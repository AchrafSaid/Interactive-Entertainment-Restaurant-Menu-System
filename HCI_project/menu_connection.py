"""A newline-delimited connection to the menu's confirmed state."""

import json
import socket


class MenuConnection:
    def __init__(self, host="127.0.0.1", port=5000, timeout=3):
        self.socket = socket.create_connection((host, port), timeout=timeout)
        self.reader = self.socket.makefile("rb")

    def request(self, gesture):
        self.socket.sendall((gesture + "\n").encode("utf-8"))
        line = self.reader.readline(8192)
        if not line:
            raise ConnectionResetError("Menu server disconnected.")
        if not line.endswith(b"\n"):
            raise RuntimeError("Incomplete response from the menu server.")
        try:
            response = json.loads(line)
        except (ValueError, UnicodeDecodeError) as error:
            raise RuntimeError(
                "Restart both the menu server and camera to use the updated code."
            ) from error
        if isinstance(response, dict) and response.get("ok") is False and response.get("state") is None:
            raise RuntimeError(response.get("error", "Menu server did not confirm its state."))
        if (
            not isinstance(response, dict)
            or not isinstance(response.get("ok"), bool)
            or not isinstance(response.get("state"), dict)
            or not isinstance(response["state"].get("menu_open"), bool)
        ):
            raise RuntimeError("Menu server returned an invalid state.")
        return response

    def close(self):
        self.reader.close()
        self.socket.close()
