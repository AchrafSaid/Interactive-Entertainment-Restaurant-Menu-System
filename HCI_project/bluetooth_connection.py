"""A real BLE link and range checks on a worker, independent of the desktop UI."""

import asyncio
from dataclasses import dataclass
import queue
import sys
import threading
import time
import uuid

from link_health import SignalGuard

try:
    from asyncio import timeout
except ImportError:  # Python 3.10 is required by the legacy MediaPipe Hands API.
    from async_timeout import timeout


# An app-provided ID preserves points when iOS changes its BLE address.
RESTAURANT_SERVICE_UUID = "7b183224-9168-443e-a927-7aeea07e8101"
USER_ID_CHARACTERISTIC_UUID = "7b183224-9168-443e-a927-7aeea07e8102"
LINK_CHECK_INTERVAL = 1.5
LINK_READ_TIMEOUT = 3


@dataclass(frozen=True)
class BluetoothDevice:
    address: str
    name: str
    connected: bool = False
    user_id: str = ""


class BluetoothMonitor:
    """One event loop owns scanning and the live client for its whole lifetime.

    Events are (kind, payload). No worker code accesses Tk or the dataset.
    Factories can be injected to test connections without radio hardware.
    Users reconnect explicitly after a lost connection.
    """

    def __init__(self, scanner=None, client_factory=None):
        self.events = queue.Queue()
        self._commands = queue.Queue()
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._scanner = scanner
        self._client_factory = client_factory
        self._devices = {}
        self._names = {}
        self._client = None
        self._loop = None
        self._task = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def scan(self):
        self._commands.put(("scan", None))

    def connect(self, address):
        self._commands.put(("connect", address))

    def disconnect(self):
        self._connected.clear()
        self._commands.put(("disconnect", None))

    @property
    def is_connected(self):
        return self._connected.is_set()

    def close(self):
        self._connected.clear()
        self._stop.set()
        if self._loop is not None and self._task is not None and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._task.cancel)
            except RuntimeError:
                pass  # The worker finished while the window was closing.
        if self._thread.is_alive():
            self._thread.join(timeout=6)

    def _run(self):
        try:
            asyncio.run(self._main())
        except asyncio.CancelledError:
            pass

    async def _main(self):
        self._loop = asyncio.get_running_loop()
        self._task = asyncio.current_task()
        try:
            if self._scanner is None or self._client_factory is None:
                try:
                    from bleak import BleakClient, BleakScanner
                except ImportError:
                    self.events.put(("unavailable", "Bluetooth support is missing. Install requirements-bluetooth.txt, then restart the menu."))
                    return
                self._scanner = BleakScanner
                self._client_factory = BleakClient

            while not self._stop.is_set():
                try:
                    kind, address = self._commands.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.1)
                    continue
                try:
                    if kind == "scan" and self._client is None:
                        await self._scan()
                    elif kind == "connect" and self._client is None:
                        await self._connect(address)
                except (TimeoutError, asyncio.TimeoutError):
                    self.events.put(("error", "The Bluetooth request timed out. Keep your phone nearby, "
                                     "check that LightBlue is advertising, then scan again."))
                except Exception as error:
                    reason = getattr(getattr(error, "reason", None), "name", None)
                    messages = {
                        "POWERED_OFF": "Bluetooth is switched off on this computer. Turn on Bluetooth in Windows Settings, then scan again.",
                        "NO_BLUETOOTH": "No Bluetooth adapter was found. Connect a BLE-capable adapter, then try again.",
                        "NO_BLE_CENTRAL_ROLE": "This Bluetooth adapter does not support BLE connections. Use a BLE-capable adapter.",
                        "DENIED_BY_USER": "Bluetooth access was denied. Allow Bluetooth access for the app, then try again.",
                        "DENIED_BY_SYSTEM": "Windows has blocked Bluetooth access. Check this computer's Bluetooth access settings.",
                    }
                    if getattr(error, "char_specifier", None) == USER_ID_CHARACTERISTIC_UUID:
                        message = "Your phone is missing its readable restaurant Phone ID. Open 'How to connect your iPhone' and check the setup."
                    else:
                        message = messages.get(reason, str(error) or type(error).__name__)
                    self.events.put(("error", message))
        finally:
            if self._client is not None:
                try:
                    await asyncio.wait_for(self._client.disconnect(), timeout=5)
                except Exception:
                    pass

    async def _scan(self):
        self._devices = {}
        self._names = {}
        self.events.put(("scanning", None))
        advertisements = await asyncio.wait_for(
            self._scanner.discover(
                # iPhone virtual peripherals can omit service UUIDs from their
                # advertisements even though the services are readable over
                # GATT. Check the required Phone ID after connecting instead.
                timeout=6, return_adv=True,
            ), timeout=12,
        )
        self._devices = {address: device for address, (device, _) in advertisements.items()}
        devices = [
            BluetoothDevice(device.address, advertisement.local_name or device.name or "Bluetooth guest")
            for device, advertisement in advertisements.values()
        ]
        devices.sort(key=lambda device: (device.name.casefold(), device.address))
        self._names = {device.address: device.name for device in devices}
        self.events.put(("devices", devices))

    async def _connect(self, address):
        device = self._devices.get(address)
        if device is None:
            raise ValueError("Device is no longer in the list. Scan again.")
        self.events.put(("connecting", None))
        disconnected = asyncio.Event()

        def on_disconnect(_):
            self._connected.clear()
            disconnected.set()

        client_options = {"winrt": {"use_cached_services": False}} if sys.platform == "win32" else {}
        client = self._client_factory(
            device, disconnected_callback=on_disconnect, **client_options,
        )
        self._client = client
        connection_id = uuid.uuid4().hex
        admitted = False
        reason = None
        watcher = None
        heartbeat = None
        health = SignalGuard()

        def advertisement(found, data):
            nonlocal reason
            if found.address.casefold() == address.casefold():
                if health.observe(data.rssi, time.monotonic()):
                    reason = "Phone signal stayed weak. Move closer and connect Bluetooth again."
                    self._connected.clear()
                    disconnected.set()

        async def check_link():
            nonlocal reason
            failures = 0
            while not disconnected.is_set():
                await asyncio.sleep(LINK_CHECK_INTERVAL)
                try:
                    value = await asyncio.wait_for(
                        client.read_gatt_char(USER_ID_CHARACTERISTIC_UUID, use_cached=False), timeout=LINK_READ_TIMEOUT)
                    if bytes(value).decode("utf-8").strip() != user_id:
                        reason = "The phone identity changed. Connect Bluetooth again."
                        break
                    failures = 0
                except Exception:
                    failures += 1
                    if failures >= 2:
                        reason = "Your phone is no longer responding. Move closer and connect Bluetooth again."
                        break
            if reason:
                self._connected.clear()
                disconnected.set()
        try:
            async with timeout(30):
                await client.connect()
                if not client.is_connected:
                    raise ConnectionError("The Bluetooth connection was lost. Please try again.")
                identity = await client.read_gatt_char(USER_ID_CHARACTERISTIC_UUID, use_cached=False)
                try:
                    user_id = bytes(identity).decode("utf-8").strip()
                except UnicodeDecodeError as error:
                    raise ValueError("Set the phone ID value to UTF-8 text in LightBlue, then try again.") from error
                if not user_id or len(user_id) > 128 or not user_id.isprintable():
                    raise ValueError("The phone's restaurant identity is missing or invalid. Check its setup.")
                if not client.is_connected or disconnected.is_set():
                    raise ConnectionError("The Bluetooth connection was lost. Please try again.")
                connected_device = BluetoothDevice(
                    address, self._names.get(address) or client.name or device.name or "Bluetooth guest", True, user_id,
                )
                self._connected.set()
                admitted = True
                self.events.put(("connected", (connected_device, connection_id)))

            # A connected iPhone may stop advertising. Missing advertisements
            # must never be treated as distance; uncached GATT reads still
            # check the real link when RSSI is unavailable.
            try:
                watcher = self._scanner(detection_callback=advertisement)
                await asyncio.wait_for(watcher.start(), timeout=3)
            except Exception:
                if watcher is not None:
                    try:
                        await asyncio.wait_for(watcher.stop(), timeout=2)
                    except Exception:
                        pass
                watcher = None
            heartbeat = asyncio.create_task(check_link())
            last_status = 0

            while not self._stop.is_set() and client.is_connected and not disconnected.is_set():
                # A failed dataset save can release the link from the UI thread.
                try:
                    kind, _ = self._commands.get_nowait()
                except queue.Empty:
                    kind = None
                if kind == "disconnect":
                    break
                now = time.monotonic()
                if now - last_status >= 1:
                    self.events.put(("signal", (connection_id, health.snapshot(now))))
                    last_status = now
                await asyncio.sleep(0.1)
        finally:
            self._connected.clear()
            # Lock the UI as soon as loss is observed, before OS cleanup.
            if admitted:
                self.events.put(("disconnected", {"session_id": connection_id, "message": reason} if reason else connection_id))
            if heartbeat is not None:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass
            if watcher is not None:
                try:
                    await asyncio.wait_for(watcher.stop(), timeout=2)
                except Exception:
                    pass
            try:
                await asyncio.wait_for(client.disconnect(), timeout=5)
            except Exception:
                pass  # The OS may have already removed an out-of-range device.
            finally:
                self._client = None
