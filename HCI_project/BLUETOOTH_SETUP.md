# Updated Olive / Table desktop app

The pulled HTML menu and newer hand-recognition code now share a Bluetooth
session backend. The connection page appears before welcome or navigation.
A real BLE connection and the readable permanent Phone ID create a rewards
visit and award 10 points. Alternatively, **Skip · Continue as guest** opens
the menu without Bluetooth. Guests can use the menu and hand controls, but
never create a saved customer record or earn points.

## Launch

- Double-click `Start Menu.cmd` or `release/OliveTable/OliveTable.exe`.
- From source: `python run_menu.py`.
- Hand control starts by default, including on the connection page.
- To start with the camera off: `python run_menu.py --touch`.
- Alternative hand-control launcher: `python integrated_menu.py` or
  `Start Gestures.cmd`. Run one app instance at a time.
- `app.py`, `menu_server_gui.py`, and the `menu_ui.py` script entry point open
  the same Bluetooth-protected HTML app.

The source launchers select `.venv-gestures` (Python 3.10). To prepare a new
computer, install Python 3.10 with its launcher and run `Setup Gestures.cmd`.
The packaged Windows app includes the runtime and needs Windows 11 x64 and
[Microsoft Edge WebView2](https://developer.microsoft.com/microsoft-edge/webview2/).

See **START_HERE.txt** for the full iPhone walkthrough. The LightBlue setup from
before the pull still works. Keep its permanent Phone ID to retain points.

## iPhone values

| Setting | Value |
|---|---|
| Service UUID | `7b183224-9168-443e-a927-7aeea07e8101` |
| Readable characteristic UUID | `7b183224-9168-443e-a927-7aeea07e8102` |
| Existing phone's text ID | `nadeem-iphone-01` |
| Same ID in Hex | `6E616465656D2D6970686F6E652D3031` |

Each phone needs its own permanent ID. Its advertised name becomes its username.
Go back to the **Virtual Devices list** in LightBlue and select the circle beside
the device to start advertising. Keep the iPhone unlocked and LightBlue open.
[LightBlue's official virtual-device guide](https://punchthrough.com/lightblue-virtual-devices/)
describes creating and advertising profiles.

Scanning includes nearby BLE devices even if the service UUID is missing from
advertising data. The app verifies the characteristic after connecting and uses
fresh Windows service discovery to avoid stale LightBlue configurations.

## Stored data and privacy

`bluetooth_users.py` saves readable JSON text atomically to
`data/bluetooth_users.txt` beside the executable. Existing packaged records are
preserved by rebuilds. Source runs reuse that populated packaged dataset if the
source dataset has no records. Both old files were backed up under
`build/reintegration-backup` before integration.

Records retain the username, points, connection count, timestamps in UTC, and
last connection ID. A stable Phone ID preserves points when iOS changes its BLE
address. Failed connections and duplicate events add no points. Corrupt data is
preserved and reported instead of silently overwritten. Run one app instance
against a dataset at a time. Release ZIPs exclude user records.

The camera starts by default for hand control. Stop camera and Q turn it off;
`--touch` starts without it. Live frames appear locally and are not saved.
Camera access is separate from menu access: hands can scan/select/connect or
choose the guest button. The menu and cart require either an explicit guest
visit or a verified Bluetooth session. Guest sessions have unique temporary IDs
and do not report a Bluetooth connection. End visit clears the guest cart and
returns to the first page. Late Bluetooth events cannot replace a guest visit.
Link loss clears the cart, modal and username. Hand control stays available
to reconnect.

## Range monitoring

The worker watches native disconnects and performs uncached identity reads
every 1.5 seconds. Two failed reads, each limited to 3 seconds, close a stuck
link. A changed identity also locks the app. The UI polls every 750 ms.
Heartbeat reads and signal samples never add points.

A concurrent advertisement watcher tracks only the connected phone address.
`link_health.SignalGuard` smooths RSSI, ignores the Windows -127 sentinel,
and disconnects after at least three weak samples sustained for four seconds
(default -78 dBm, recovery -70 dBm). Gaps over 2.5 seconds reset the weak streak.
The session bar shows fresh RSSI or the fallback "live link checks".

An iPhone may stop advertising while connected. Missing advertisements are
not evidence of distance: actual link loss and uncached reads remain active.
A responsive phone can therefore stay connected past an imagined distance
cutoff if RSSI is unavailable. This cannot promise a fixed metre boundary.
Test on the restaurant hardware; tune `SignalGuard` thresholds if needed.
Windows exposes RSSI in advertisement callbacks:
[Microsoft BLE advertisements](https://learn.microsoft.com/en-us/windows/uwp/devices-sensors/ble-beacon),
[Bleak scanner API](https://bleak.readthedocs.io/en/latest/api/scanner.html),
[Bleak uncached Windows reads](https://bleak.readthedocs.io/en/latest/backends/windows.html).

## Hand controls

- One index finger moves the pointer; a gold outline shows the target.
- Pinch thumb and index for 120 ms to select; release to rearm. Holding never
  repeats. The pointer freezes during the pinch to avoid adjacent targets.
- Two fingers move up/down to scroll, including phone choices and dialogs.
- Hold a fist for 650 ms to go back; an open palm pauses selection.
- Every dish, quantities, cart edits, checkout, navigation, setup help and
  phone connection use the same ordinary buttons.

Controls have targets of at least 48 pixels, visible focus and feedback.
Checkout and End visit require confirmation. Touch, keyboard and mouse remain
available. Gesture timing is independent of camera FPS. Motion samples are
replaced rather than queued so a slow renderer cannot build a cursor backlog.
The live preview element survives page updates.

## Main files

- `menu_server_gui.py`: WebView2 window, local gesture socket and MJPEG preview.
- `bluetooth_bridge.py`: Python API for verified sessions and camera permission.
- `bluetooth_connection.py`: BLE worker, disconnect callback and fresh GATT reads.
- `bluetooth_users.py`: stable identities and saved rewards.
- `bluetooth_ui.js` / `.css`: shared connection screen, help, session and route guards.
- `index.html`: pulled menu, cart, games, rewards and gesture sidebar.
- `integrated_menu.py`: camera capture and MediaPipe tracking.
- `hand_input.py`: smoothed pointer, pinch latch, scroll and back intent.
- `hand_ui.js` / `.css`: hit testing, focus, scrolling and larger controls.
- `link_health.py`: signal smoothing and range hysteresis.

Opening HTML directly in a browser keeps it locked because the desktop Python
Bluetooth API is required. The app uses the native bridge documented by
[pywebview](https://pywebview.flowrl.com/guide/interdomain.html).

## Verification

```powershell
.\.venv-gestures\Scripts\python.exe -m unittest test_bluetooth test_desktop_host test_hand_and_range -v
node --test test_bluetooth_ui.cjs
python integrated_menu.py --check
.\.venv-gestures\Scripts\python.exe tools/check_desktop.py
.\.venv-gestures\Scripts\python.exe tools/check_hand_flow.py
```

The desktop flow check uses WebView2 with a temporary simulated Bluetooth
session and dataset. It checks the first page, navigation, points, disconnect,
cart clearing and reconnect totals. It does not award points to real users.
The hand check also drives actual DOM hit testing with synthetic hand events
through phone selection, any dish, quantities, confirmation and navigation.
These tests do not measure real hand accuracy or physical Bluetooth range.
Real iPhone pairing still needs the LightBlue setup and a hardware check.

## Rebuild

```powershell
.\.venv-gestures\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv-gestures\Scripts\python.exe tools/build_release.py
```

Build on Windows using Python 3.10. The portable folder includes the camera
runtime, HTML, local fonts and assets. Rebuilds retain existing saved records.
The ZIP is assembled from fresh build files and never from customer data.
