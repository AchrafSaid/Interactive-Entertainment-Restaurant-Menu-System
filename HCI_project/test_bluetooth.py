"""Run with python -m unittest test_bluetooth -v; no radio or phone is needed."""

import asyncio
import json
from pathlib import Path
import queue
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bluetooth_connection import (
    BluetoothDevice, BluetoothMonitor, RESTAURANT_SERVICE_UUID,
    USER_ID_CHARACTERISTIC_UUID,
    timeout,
)
from bluetooth_users import BluetoothSession, BluetoothUserStore, UserDataError


class UserStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "data" / "users.txt"
        self.store = BluetoothUserStore(self.path)

    def test_rewards_persist_and_duplicate_connection_is_not_credited(self):
        first, awarded = self.store.record_connection("phone-01", "Nadeen's iPhone", "link-1")
        self.assertEqual((first["points"], awarded), (10, 10))
        store_after_restart = BluetoothUserStore(self.path)
        repeated, awarded = store_after_restart.record_connection("phone-01", "Nadeen's iPhone", "link-1")
        self.assertEqual((repeated["points"], awarded), (10, 0))
        reconnected, awarded = store_after_restart.record_connection("phone-01", "Nadeen's iPhone", "link-2")
        self.assertEqual((reconnected["points"], reconnected["connections"], awarded), (20, 2, 10))

    def test_name_changes_and_identical_names_do_not_merge_identities(self):
        self.store.record_connection("phone-01", "iPhone", "link-1")
        self.store.record_connection("phone-02", "iPhone", "link-2")
        renamed, _ = self.store.record_connection("phone-01", "هاتف نادين", "link-3")
        saved = json.loads(self.path.read_text(encoding="utf-8"))["users"]
        self.assertEqual(renamed["points"], 20)
        self.assertEqual(saved["phone-01"]["username"], "هاتف نادين")
        self.assertEqual(saved["phone-02"]["points"], 10)

    def test_corrupt_dataset_is_preserved(self):
        self.path.parent.mkdir()
        self.path.write_text("broken dataset", encoding="utf-8")
        with self.assertRaises(UserDataError):
            self.store.record_connection("phone", "Name", "link")
        self.assertEqual(self.path.read_text(encoding="utf-8"), "broken dataset")

    def test_failed_atomic_replace_keeps_previous_total(self):
        self.store.record_connection("phone", "Name", "link-1")
        original = self.path.read_bytes()
        with patch("bluetooth_users.os.replace", side_effect=OSError("Disk unavailable")):
            with self.assertRaises(OSError):
                self.store.record_connection("phone", "Name", "link-2")
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_unconnected_or_unidentified_device_cannot_unlock_session(self):
        session = BluetoothSession(self.store)
        for device in (BluetoothDevice("AA", "Phone"), BluetoothDevice("AA", "Phone", True)):
            with self.assertRaises(ValueError):
                session.connect(device, "link")
        self.assertIsNone(session.user)
        self.assertFalse(self.path.exists())

    def test_rotated_bluetooth_address_preserves_points(self):
        session = BluetoothSession(self.store)
        session.connect(BluetoothDevice("AA", "Phone", True, "stable-id"), "link-1")
        session.clear()
        session.connect(BluetoothDevice("BB", "Phone", True, "stable-id"), "link-2")
        self.assertEqual(session.user["points"], 20)
        self.assertEqual(len(json.loads(self.path.read_text())["users"]), 1)


class FakeScanner:
    @staticmethod
    async def discover(**kwargs):
        assert "service_uuids" not in kwargs
        assert kwargs["return_adv"]
        return {"AA": (SimpleNamespace(address="AA", name="Cached name"),
                       SimpleNamespace(local_name="Nadeen's iPhone", service_uuids=[]))}


class FakeClient:
    def __init__(self, device, disconnected_callback, **options):
        self.callback = disconnected_callback
        self.is_connected = False
        self.name = device.name
        self.identity = b"phone-01"
        self.failure = None
        self.disconnect_calls = 0
        self.options = options

    async def connect(self):
        if self.failure:
            raise self.failure
        self.is_connected = True

    async def read_gatt_char(self, characteristic, **kwargs):
        assert characteristic == USER_ID_CHARACTERISTIC_UUID
        assert kwargs["use_cached"] is False
        return bytearray(self.identity)

    async def disconnect(self):
        self.disconnect_calls += 1
        self.drop_link()

    def drop_link(self):
        self.is_connected = False
        self.callback(self)


class BluetoothWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clients = []
        self.failure = None
        self.identity = b"phone-01"

        def factory(*args, **kwargs):
            client = FakeClient(*args, **kwargs)
            client.failure = self.failure
            client.identity = self.identity
            self.clients.append(client)
            return client

        self.monitor = BluetoothMonitor(FakeScanner, factory)
        self.task = asyncio.create_task(self.monitor._main())

    async def asyncTearDown(self):
        self.monitor._stop.set()
        await asyncio.wait_for(self.task, timeout=2)

    async def next_event(self, desired):
        async with timeout(2):
            while True:
                try:
                    kind, payload = self.monitor.events.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                if kind == desired:
                    return payload
                if kind == "error":
                    self.fail(f"Unexpected Bluetooth failure: {payload}")

    async def scan(self):
        self.monitor.scan()
        devices = await self.next_event("devices")
        self.assertEqual(devices[0].name, "Nadeen's iPhone")

    async def test_actual_connect_disconnect_and_reconnect(self):
        await self.scan()
        self.monitor.connect("AA")
        device, connection_id = await self.next_event("connected")
        self.assertTrue(device.connected)
        self.assertTrue(self.monitor.is_connected)
        if sys.platform == "win32":
            self.assertIs(self.clients[-1].options["winrt"]["use_cached_services"], False)
        self.assertEqual((device.name, device.user_id), ("Nadeen's iPhone", "phone-01"))
        self.clients[-1].drop_link()
        self.assertFalse(self.monitor.is_connected)
        self.assertEqual(await self.next_event("disconnected"), connection_id)
        self.monitor.connect("AA")
        _, second_id = await self.next_event("connected")
        self.assertNotEqual(connection_id, second_id)

    async def test_phone_without_advertised_service_still_requires_valid_identity(self):
        # Reproduces an iPhone observed by Windows with an empty advertised
        # service list. Discovery must show it; admission still reads its ID.
        await self.scan()
        self.identity = b""
        self.monitor.connect("AA")
        self.assertIn("identity", await self.next_event("error"))
        self.assertFalse(self.monitor.is_connected)

    async def test_failed_connection_emits_no_connected_event(self):
        await self.scan()
        self.failure = ConnectionError("Out of range")
        self.monitor.connect("AA")
        error = await self.next_event("error")
        self.assertIn("Out of range", error)
        self.assertIsNone(self.monitor._client)
        self.assertGreater(self.clients[0].disconnect_calls, 0)

    async def test_invalid_identity_is_rejected_and_link_closed(self):
        await self.scan()
        self.identity = b""
        self.monitor.connect("AA")
        self.assertIn("identity", await self.next_event("error"))
        self.assertFalse(self.clients[0].is_connected)

    async def test_radio_off_has_actionable_message(self):
        class RadioOffError(Exception):
            reason = SimpleNamespace(name="POWERED_OFF")

        with patch.object(FakeScanner, "discover", side_effect=RadioOffError("Radio off")):
            self.monitor.scan()
            message = await self.next_event("error")
        self.assertIn("Turn on Bluetooth", message)
        self.assertFalse(self.monitor.is_connected)

    async def test_connection_timeout_has_actionable_message(self):
        await self.scan()
        self.failure = TimeoutError()
        self.monitor.connect("AA")
        self.assertIn("timed out", await self.next_event("error"))
        self.assertFalse(self.monitor.is_connected)

    async def test_main_thread_can_release_rejected_connection(self):
        await self.scan()
        self.monitor.connect("AA")
        _, connection_id = await self.next_event("connected")
        self.monitor.disconnect()
        self.assertEqual(await self.next_event("disconnected"), connection_id)
        async with timeout(2):
            while self.monitor._client is not None:
                await asyncio.sleep(0.01)
        self.assertFalse(self.clients[-1].is_connected)


class FakeMonitor:
    def __init__(self):
        self.events = queue.Queue()
        self.is_connected = False
        self.disconnected = False
        self.operations = []

    def start(self):
        pass

    def close(self):
        pass

    def scan(self):
        self.operations.append(("scan",))

    def connect(self, address):
        self.operations.append(("connect", address))

    def disconnect(self):
        self.disconnected = True
        self.is_connected = False


class BluetoothBridgeTests(unittest.TestCase):
    def setUp(self):
        from bluetooth_bridge import BluetoothBridge
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = BluetoothUserStore(Path(self.directory.name) / "users.txt")
        self.monitor = FakeMonitor()
        self.camera_calls = []
        self.bridge = BluetoothBridge(self.monitor, self.store, camera_control=self.camera_calls.append)

    def connect_phone(self, address="AA", name="Nadeem", identity="phone-01", connection_id="link-1"):
        self.monitor.is_connected = True
        self.bridge._process_event("connected", (BluetoothDevice(address,name,True,identity),connection_id))

    def test_initial_state_is_locked_without_private_user_data(self):
        state = self.bridge.get_state()
        self.assertFalse(state["connected"])
        self.assertFalse(state["camera_enabled"])
        self.assertIsNone(state["user"])
        self.assertIsNone(state["session_id"])
        self.assertFalse(self.store.path.exists())

    def test_only_a_scanned_device_can_be_selected(self):
        state = self.bridge.connect_bluetooth("unknown")
        self.assertFalse(state["connected"])
        self.assertEqual(self.monitor.operations, [])
        self.bridge.scan_bluetooth()
        self.bridge._process_event("devices", [BluetoothDevice("AA","Nadeem")])
        self.bridge.connect_bluetooth("AA")
        self.assertEqual(self.monitor.operations, [("scan",),("connect","AA")])
        self.assertFalse(self.bridge.get_state()["connected"])

    def test_successful_connection_persists_ten_points_and_user(self):
        self.connect_phone()
        state = self.bridge.get_state()
        self.assertTrue(state["connected"])
        self.assertEqual(state["user"], {"username":"Nadeem", "points":10, "connections":1})
        self.assertNotIn("last_connection_id", state["user"])
        self.bridge._process_event("connected", (BluetoothDevice("AA","Nadeem",True,"phone-01"),"link-1"))
        self.assertEqual(self.bridge.get_state()["user"]["points"],10)

    def test_lost_link_locks_immediately_before_event_is_processed(self):
        self.connect_phone()
        self.bridge.set_camera(True)
        self.monitor.is_connected = False
        state = self.bridge.get_state()
        self.assertFalse(state["connected"])
        self.assertTrue(state["camera_enabled"])  # Hands can reconnect on the locked gate.
        self.assertIsNone(state["user"])
        self.assertIsNone(state["session_id"])

    def test_disconnect_clears_user_and_next_connection_adds_ten(self):
        self.connect_phone()
        self.monitor.is_connected = False
        self.bridge._process_event("disconnected","link-1")
        self.assertIsNone(self.bridge.get_state()["user"])
        self.connect_phone(connection_id="link-2")
        self.assertEqual(self.bridge.get_state()["user"]["points"],20)

    def test_save_failure_does_not_unlock_menu(self):
        with patch.object(self.store,"record_connection",side_effect=OSError("Disk full")):
            self.connect_phone()
        state = self.bridge.get_state()
        self.assertFalse(state["connected"])
        self.assertTrue(self.monitor.disconnected)
        self.assertIn("Disk full",state["message"])

    def test_camera_can_control_locked_gate_and_end_visit_preserves_points(self):
        self.bridge.set_camera(True)
        self.assertEqual(self.camera_calls, [True])
        self.assertTrue(self.bridge.get_state()["camera_enabled"])
        self.assertFalse(self.bridge.get_state()["connected"])
        self.connect_phone()
        self.assertEqual(self.camera_calls,[True])
        self.assertTrue(self.bridge.get_state()["camera_enabled"])
        self.bridge.end_visit()
        self.assertTrue(self.bridge.get_state()["camera_enabled"])
        self.assertFalse(self.bridge.get_state()["connected"])
        self.assertEqual(json.loads(self.store.path.read_text())["users"]["phone-01"]["points"],10)

    def test_stale_disconnect_cannot_clear_new_user(self):
        self.connect_phone()
        self.bridge._process_event("disconnected","old-link")
        self.assertTrue(self.bridge.get_state()["connected"])

    def test_expired_connected_event_does_not_award_points(self):
        self.bridge._process_event("connected",(BluetoothDevice("AA","Nadeem",True,"phone-01"),"expired"))
        self.assertFalse(self.bridge.get_state()["connected"])
        self.assertFalse(self.store.path.exists())

    def test_missing_runtime_stays_locked_and_disables_scan(self):
        self.bridge._process_event("unavailable","Install Bluetooth support")
        self.bridge.scan_bluetooth()
        self.assertEqual(self.monitor.operations,[])
        self.assertFalse(self.bridge.get_state()["available"])

    def test_guest_has_access_without_a_bluetooth_link_or_saved_record(self):
        self.bridge._process_event("unavailable", "No Bluetooth adapter")
        state = self.bridge.continue_as_guest()
        self.assertTrue(state["guest"])
        self.assertTrue(state["access_allowed"])
        self.assertFalse(state["connected"])
        self.assertEqual(state["user"]["username"], "Guest")
        self.assertFalse(self.store.path.exists())
        self.assertEqual(self.bridge.continue_as_guest()["session_id"], state["session_id"])
        self.bridge._process_event("error", "A late scan failed")
        self.assertTrue(self.bridge.get_state()["guest"])
        self.bridge.end_visit()
        self.assertFalse(self.bridge.get_state()["access_allowed"])
        self.assertNotEqual(self.bridge.continue_as_guest()["session_id"], state["session_id"])

    def test_late_phone_connection_cannot_replace_guest_or_award_points(self):
        state = self.bridge.continue_as_guest()
        self.connect_phone()
        self.assertEqual(self.bridge.get_state()["session_id"], state["session_id"])
        self.assertFalse(self.store.path.exists())
        self.bridge.end_visit()
        self.connect_phone(connection_id="late-after-guest")
        self.assertFalse(self.bridge.get_state()["access_allowed"])
        self.assertFalse(self.store.path.exists())

    def test_guest_leaves_existing_points_untouched_and_can_later_connect(self):
        self.connect_phone()
        saved = self.store.path.read_bytes()
        self.bridge.end_visit()
        self.bridge.continue_as_guest()
        self.bridge._process_event("disconnected", "link-1")
        self.assertTrue(self.bridge.get_state()["guest"])
        self.assertEqual(self.store.path.read_bytes(), saved)
        self.bridge.end_visit()
        self.bridge._process_event("devices", [BluetoothDevice("AA", "Nadeem")])
        self.bridge.connect_bluetooth("AA")
        self.connect_phone(connection_id="link-2")
        state = self.bridge.get_state()
        self.assertFalse(state["guest"])
        self.assertTrue(state["connected"])
        self.assertEqual(state["user"]["points"], 20)


if __name__ == "__main__":
    unittest.main()
