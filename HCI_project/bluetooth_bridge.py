"""Desktop visits: verified Bluetooth users or explicitly selected guests."""

import queue
import threading
import uuid

from bluetooth_connection import BluetoothMonitor, RESTAURANT_SERVICE_UUID, USER_ID_CHARACTERISTIC_UUID
from bluetooth_users import BluetoothSession, BluetoothUserStore


class BluetoothBridge:
    def __init__(self, monitor=None, store=None, camera_control=None, camera_available=True, auto_camera=False):
        self._monitor = monitor or BluetoothMonitor()
        self._session = BluetoothSession(store or BluetoothUserStore())
        self._guest_id = None
        self._reject_pending_connections = False
        self._camera_control = camera_control
        self._camera_available = camera_available
        self._auto_camera = auto_camera
        self._camera_enabled = False
        self._camera_error = ""
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._devices = []
        self._busy = False
        self._available = True
        self._message = "Connect your phone for rewards, or continue as a guest."
        self._revision = 0
        self._signal = {"rssi": None, "mode": "link"}
        self._phone_id = "phone-" + uuid.uuid4().hex[:12]
        self._thread = threading.Thread(target=self._process_events, daemon=True)

    def _start(self):
        self._monitor.start()
        self._thread.start()
        if self._auto_camera:
            self.set_camera(True)

    def _connected(self):
        return self._session.user is not None and self._monitor.is_connected

    def _snapshot(self):
        connected = self._connected()
        guest = self._guest_id is not None
        user = {"username": "Guest", "points": 0, "connections": 0} if guest else self._session.user if connected else None
        return {
            "revision": self._revision,
            "connected": connected,
            "guest": guest,
            "access_allowed": connected or guest,
            "session_id": self._guest_id if guest else self._session.connection_id if connected else None,
            "user": {key: user[key] for key in ("username", "points", "connections")} if user else None,
            "busy": self._busy,
            "available": self._available,
            "message": self._message,
            "devices": [{"address": device.address, "name": device.name} for device in self._devices],
            "camera_enabled": self._camera_enabled,
            "camera_available": self._camera_available,
            "camera_error": self._camera_error,
            "signal": self._signal if connected else {"rssi": None, "mode": "link"},
            "setup": {"service": RESTAURANT_SERVICE_UUID, "characteristic": USER_ID_CHARACTERISTIC_UUID,
                      "phone_id": self._phone_id},
        }

    def get_state(self):
        with self._lock:
            return self._snapshot()

    def scan_bluetooth(self):
        with self._lock:
            if self._busy or self._connected() or self._guest_id or not self._available:
                return self._snapshot()
            self._busy = True
            self._devices = []
            self._message = "Looking for nearby Bluetooth devices…"
            self._revision += 1
            self._monitor.scan()
            return self._snapshot()

    def connect_bluetooth(self, address):
        with self._lock:
            if self._busy or self._connected() or self._guest_id or not self._available:
                return self._snapshot()
            device = next((device for device in self._devices if device.address == address), None)
            if device is None:
                self._message = "Scan for phones and select your device first."
            else:
                self._busy = True
                self._reject_pending_connections = False
                self._message = f"Connecting to {device.name}…"
                self._monitor.connect(device.address)
            self._revision += 1
            return self._snapshot()

    def _clear_session(self, message):
        self._session.clear()
        self._guest_id = None
        self._signal = {"rssi": None, "mode": "link"}
        self._devices = []
        self._busy = False
        self._message = message
        self._revision += 1

    def continue_as_guest(self):
        with self._lock:
            if self._guest_id or self._connected():
                return self._snapshot()
            # Ignore an in-flight scan/connect result after the guest choice.
            self._reject_pending_connections = True
            self._monitor.disconnect()
            self._session.clear()
            self._guest_id = "guest-" + uuid.uuid4().hex
            self._devices = []
            self._busy = False
            self._signal = {"rssi": None, "mode": "link"}
            self._message = "Welcome, Guest. Explore the menu without Bluetooth."
            self._revision += 1
            return self._snapshot()

    def end_visit(self):
        with self._lock:
            guest = self._guest_id is not None
            self._monitor.disconnect()
            self._clear_session("Guest visit ended. Choose how to enter again." if guest else
                                "Visit ended. Your points are saved. Connect your phone or continue as a guest.")
            return self._snapshot()

    def set_camera(self, enabled):
        with self._lock:
            if type(enabled) is not bool:
                return self._snapshot()
            if enabled and not self._camera_available:
                self._camera_error = "Run Setup Gestures.cmd to install camera support. Touch controls are available."
            else:
                try:
                    if self._camera_control is not None:
                        self._camera_control(enabled)
                    self._camera_enabled = enabled
                    self._camera_error = ""
                except Exception as error:
                    self._camera_enabled = False
                    self._camera_error = f"Camera could not start: {error}. You can use touch controls."
            self._revision += 1
            return self._snapshot()

    def _report_camera_error(self, message):
        with self._lock:
            self._camera_enabled = False
            self._camera_error = message
            self._revision += 1

    def _process_event(self, kind, payload):
        with self._lock:
            if kind == "connected" and self._reject_pending_connections:
                self._monitor.disconnect()
                return
            if self._guest_id:
                if kind == "unavailable":
                    self._available = False
                    self._revision += 1
                return
            if kind == "devices":
                self._devices = payload
                self._busy = False
                self._message = (
                    "Select the name you set in LightBlue, then connect. Other nearby devices may also appear."
                    if payload else "No devices found. Select your virtual device in LightBlue and keep the iPhone unlocked."
                )
            elif kind == "connected":
                device, connection_id = payload
                if not self._monitor.is_connected:
                    self._clear_session("Connection lost. Connect Bluetooth to continue.")
                    return
                try:
                    awarded = self._session.connect(device, connection_id)
                except (OSError, ValueError) as error:
                    self._monitor.disconnect()
                    self._clear_session(f"Could not save your points: {error}")
                    return
                self._busy = False
                self._devices = []
                self._message = f"Connected. +{awarded} points saved." if awarded else "Bluetooth connected."
                if self._auto_camera:
                    self.set_camera(True)
            elif kind == "disconnected":
                connection_id = payload.get("session_id") if isinstance(payload, dict) else payload
                if connection_id != self._session.connection_id:
                    return
                self._clear_session(payload.get("message") if isinstance(payload, dict) else
                                    "Connection lost. Move closer and connect Bluetooth again to continue.")
                return
            elif kind == "signal":
                connection_id, signal = payload
                if connection_id != self._session.connection_id or self._signal == signal:
                    return
                self._signal = signal
            elif kind in ("error", "unavailable"):
                self._available = kind != "unavailable"
                self._clear_session(f"Bluetooth could not continue: {payload}")
                return
            else:
                return
            self._revision += 1

    def _process_events(self):
        while not self._stop.is_set():
            try:
                kind, payload = self._monitor.events.get(timeout=0.2)
            except queue.Empty:
                continue
            self._process_event(kind, payload)

    def _close(self):
        self._stop.set()
        self._monitor.close()
        if self._thread.is_alive():
            self._thread.join(timeout=2)
