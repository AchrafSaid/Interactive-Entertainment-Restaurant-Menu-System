"""Exercise the real local transport and camera lifecycle without a webcam."""

import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import queue
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

import menu_server_gui as host
from bluetooth_bridge import BluetoothBridge
from bluetooth_users import BluetoothUserStore
from bluetooth_connection import BluetoothDevice
from test_bluetooth import FakeMonitor


class DesktopTransportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.monitor = FakeMonitor()
        self.bridge = BluetoothBridge(self.monitor, BluetoothUserStore(Path(self.directory.name)/"users.txt"))
        host.bluetooth = self.bridge
        host.running = True
        host.latest_frame = None
        host.latest_hand_event = None
        host.gesture_queue = queue.Queue()
        self.http = ThreadingHTTPServer(("127.0.0.1",0),host.CameraStreamHandler)
        self.http.daemon_threads = True
        self.thread = threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        host.running = False
        with host.frame_condition:
            host.frame_condition.notify_all()
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=1)

    def connect_phone(self):
        self.monitor.is_connected = True
        self.bridge._process_event("connected",(BluetoothDevice("AA","Guest",True,"phone-01"),"link-1"))

    def request(self, method, path, body=None):
        client = HTTPConnection("127.0.0.1",self.http.server_port,timeout=2)
        try:
            client.request(method,path,body=body)
            response = client.getresponse()
            return response.status,response.read()
        finally:
            client.close()

    def test_camera_stream_and_upload_are_blocked_before_bluetooth(self):
        self.assertEqual(self.request("GET","/stream")[0],403)
        self.assertEqual(self.request("POST","/frame",b"jpeg")[0],403)
        self.assertIsNone(host.latest_frame)

    def test_camera_choice_survives_disconnect_to_operate_locked_gate(self):
        self.connect_phone()
        self.assertEqual(self.request("POST","/frame",b"jpeg")[0],403)
        self.bridge.set_camera(True)
        self.assertEqual(self.request("POST","/frame",b"jpeg")[0],200)
        self.assertEqual(host.latest_frame,b"jpeg")
        self.monitor.is_connected = False
        status,payload = self.request("GET","/session")
        self.assertEqual(status,200)
        self.assertEqual(json.loads(payload),{"connected":False,"camera_enabled":True})
        self.assertTrue(host.submit_hand_event({"type":"hand","action":"click","x":.5,"y":.5}))
        self.assertFalse(host.submit_gesture("OPEN_PALM"))
        self.bridge.set_camera(False)
        self.assertEqual(self.request("GET","/stream")[0],403)

    def test_camera_must_be_enabled_for_hand_events_before_bluetooth(self):
        self.assertFalse(host.submit_hand_event({"type":"hand","action":"click"}))
        self.bridge.set_camera(True)
        self.assertTrue(host.submit_hand_event({"type":"hand","action":"point","x":.2,"y":.2}))
        self.assertIsNone(self.bridge.get_state()["user"])

    def test_motion_samples_do_not_build_a_cursor_backlog(self):
        self.bridge.set_camera(True)
        for x in range(500):
            host.submit_hand_event({"type":"hand","action":"point","x":x})
        self.assertTrue(host.gesture_queue.empty())
        self.assertEqual(host.latest_hand_event[1]["x"],499)
        host.submit_hand_event({"type":"hand","action":"click","x":.5,"y":.5})
        self.assertEqual(host.gesture_queue.qsize(),1)

    def test_guest_can_use_gestures_without_a_bluetooth_connection(self):
        state = self.bridge.continue_as_guest()
        self.assertTrue(host.submit_gesture("SELECT_PRODUCT"))
        self.assertEqual(host.gesture_queue.get_nowait(), (state["session_id"], "SELECT_PRODUCT"))
        self.assertFalse(state["connected"])
        self.assertFalse((Path(self.directory.name)/"users.txt").exists())

    def test_socket_client_cannot_bypass_the_bluetooth_gate(self):
        server,client = socket.socketpair()
        client.settimeout(2)
        thread = threading.Thread(target=host.handle_client,args=(server,("test",0)),daemon=True)
        thread.start()
        try:
            client.sendall(b"OPEN_PALM\n")
            self.assertEqual(client.recv(1024).decode().strip(),"Bluetooth connection required")
            self.assertTrue(host.gesture_queue.empty())
            self.connect_phone()
            client.sendall(b"OPEN_PALM\n")
            self.assertEqual(client.recv(1024).decode().strip(),"Processed: OPEN_PALM")
            self.assertEqual(host.gesture_queue.get_nowait(),("link-1","OPEN_PALM"))
        finally:
            client.close()
            thread.join(timeout=1)


class CameraLifecycleTests(unittest.TestCase):
    def test_camera_does_not_open_before_bluetooth_and_user_choice(self):
        from integrated_menu import OliveTableApp
        controller = OliveTableApp()
        controller.running = True
        with patch("integrated_menu.cv2.VideoCapture") as capture:
            thread = threading.Thread(target=controller.camera_loop)
            thread.start()
            threading.Event().wait(0.15)
            controller.running = False
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
