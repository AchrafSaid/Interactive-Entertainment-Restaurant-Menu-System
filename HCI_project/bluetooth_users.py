"""Persistent Bluetooth identities and rewards, stored as readable JSON text."""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


APP_DIRECTORY = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
)
DEFAULT_USERS_FILE = APP_DIRECTORY / "data" / "bluetooth_users.txt"
# A previous packaged build may already hold the customer's points. Reuse it
# when running the updated source if the source dataset has no records yet.
if not getattr(sys, "frozen", False):
    legacy_users_file = APP_DIRECTORY / "release" / "OliveTable" / "data" / "bluetooth_users.txt"
    try:
        source_users = json.loads(DEFAULT_USERS_FILE.read_text(encoding="utf-8"))["users"] if DEFAULT_USERS_FILE.exists() else {}
        legacy_users = json.loads(legacy_users_file.read_text(encoding="utf-8"))["users"] if legacy_users_file.exists() else {}
        if not source_users and isinstance(legacy_users, dict) and legacy_users:
            DEFAULT_USERS_FILE = legacy_users_file
    except (OSError, ValueError, KeyError, TypeError):
        pass  # Dataset validation reports errors without overwriting either file.
POINTS_PER_CONNECTION = 10


class UserDataError(ValueError):
    """The existing dataset cannot safely be read or updated."""


class BluetoothUserStore:
    def __init__(self, path=DEFAULT_USERS_FILE):
        self.path = Path(path)

    def _read(self):
        if not self.path.exists():
            return {"version": 1, "users": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError("Unsupported dataset format")
            users = data["users"]
            if not isinstance(users, dict):
                raise ValueError("Users must be an object")
            for device_id, user in users.items():
                if not isinstance(device_id, str) or not isinstance(user, dict):
                    raise ValueError("Invalid user record")
                if not isinstance(user.get("username"), str):
                    raise ValueError("Invalid username")
                for key in ("points", "connections"):
                    if type(user.get(key)) is not int or user[key] < 0:
                        raise ValueError(f"Invalid {key}")
                for key in ("first_connected", "last_connected", "last_connection_id"):
                    if not isinstance(user.get(key), str):
                        raise ValueError(f"Invalid {key}")
            return data
        except (ValueError, KeyError, TypeError) as error:
            raise UserDataError(
                f"Cannot read {self.path.name}. Repair or restore the dataset; "
                "the existing file has been kept."
            ) from error

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Replace only after a complete write, so an interrupted save keeps the
        # previous dataset. The temporary file is on the same filesystem.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent,
                prefix=self.path.name + ".", suffix=".tmp", delete=False,
            ) as file:
                temporary = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def record_connection(self, device_id, name, connection_id):
        """Credit a successful BLE connection once, even if its event repeats."""
        if not device_id or not connection_id:
            raise ValueError("A stable device identity and connection ID are required")
        name = name.strip() or "Bluetooth guest"
        data = self._read()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        user = data["users"].get(device_id)
        if user is None:
            user = {
                "username": name, "points": 0, "connections": 0,
                "first_connected": now, "last_connected": now,
                "last_connection_id": "",
            }
            data["users"][device_id] = user
        awarded = user["last_connection_id"] != connection_id
        changed = user["username"] != name or awarded
        user["username"] = name
        if awarded:
            user["points"] += POINTS_PER_CONNECTION
            user["connections"] += 1
            user["last_connected"] = now
            user["last_connection_id"] = connection_id
        if changed:
            self._write(data)
        return dict(user), POINTS_PER_CONNECTION if awarded else 0


class BluetoothSession:
    """Only a device with a verified live link can unlock the menu."""

    def __init__(self, store):
        self.store = store
        self.address = None
        self.user = None
        self.connection_id = None

    def clear(self):
        self.address = None
        self.user = None
        self.connection_id = None

    def connect(self, device, connection_id):
        if not device.connected:
            raise ValueError("The Bluetooth device is not connected")
        if not device.user_id:
            raise ValueError("The device has no restaurant identity")
        if self.address is not None and self.address != device.address:
            raise ValueError("Another user is already connected")
        user, awarded = self.store.record_connection(device.user_id, device.name, connection_id)
        self.address = device.address
        self.user = user
        self.connection_id = connection_id
        return awarded
