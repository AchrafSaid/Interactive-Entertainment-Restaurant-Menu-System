import json
import socket
import threading
import time
import unittest
from unittest.mock import patch

from menu_connection import MenuConnection


class MenuConnectionTests(unittest.TestCase):
    def response(self, data, split=False):
        server, client = socket.socketpair()
        client.settimeout(2)
        with patch("menu_connection.socket.create_connection", return_value=client):
            connection = MenuConnection()

        def reply():
            with server:
                request = b""
                while not request.endswith(b"\n"):
                    request += server.recv(1024)
                if split:
                    for part in [data[:7], data[7:19], data[19:]]:
                        server.sendall(part)
                        time.sleep(0.005)
                else:
                    server.sendall(data)

        worker = threading.Thread(target=reply, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 2)
        self.addCleanup(connection.close)
        return connection

    def test_fragmented_reply_preserves_confirmed_state(self):
        state = {"menu_open": True, "category": "Drinks", "selected_item": None}
        data = (json.dumps({"ok": True, "gesture": "OPEN_PALM", "state": state}) + "\n").encode()
        response = self.response(data, split=True).request("OPEN_PALM")
        self.assertEqual(response["state"], state)

    def test_old_server_gets_a_clear_restart_message(self):
        with self.assertRaisesRegex(RuntimeError, "Restart both"):
            self.response(b"Processed: OPEN_PALM\n").request("OPEN_PALM")

    def test_unresponsive_gui_error_is_reported(self):
        data = json.dumps({"ok": False, "state": None, "error": "Restart the menu server."}) + "\n"
        with self.assertRaisesRegex(RuntimeError, "Restart the menu server"):
            self.response(data.encode()).request("OPEN_PALM")

    def test_invalid_state_cannot_be_shown_as_confirmed(self):
        data = b'{"ok":true,"state":{"menu_open":"false"}}\n'
        with self.assertRaisesRegex(RuntimeError, "invalid state"):
            self.response(data).request("STATUS")


if __name__ == "__main__":
    unittest.main()
