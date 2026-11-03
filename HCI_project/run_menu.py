"""Desktop entry point, with optional diagnostics for the packaged BLE runtime."""

import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import queue
import sys
import subprocess
import time


def ensure_runtime():
    if getattr(sys, "frozen", False):
        return
    required = ("webview", "bleak", "mediapipe", "cv2")
    if sys.version_info[:2] <= (3, 12) and all(importlib.util.find_spec(name) for name in required):
        return
    interpreter = Path(__file__).resolve().parent / ".venv-gestures" / "Scripts" / "python.exe"
    if interpreter.is_file() and interpreter.resolve() != Path(sys.executable).resolve():
        print("Using the prepared Olive / Table Python environment...", flush=True)
        raise SystemExit(subprocess.call([str(interpreter), str(Path(sys.argv[0]).resolve()), *sys.argv[1:]]))
    raise SystemExit("Run Setup Gestures.cmd to prepare Python 3.10 and the app dependencies.")


def check_gesture_runtime():
    import cv2
    import mediapipe as mp
    import numpy as np
    if not hasattr(mp, "solutions"):
        raise SystemExit("Run Setup Gestures.cmd. This app requires MediaPipe 0.10.21.")
    with mp.solutions.hands.Hands(static_image_mode=True, max_num_hands=1, model_complexity=0) as hands:
        hands.process(np.zeros((128, 128, 3), dtype=np.uint8))
    print(f"Gesture check passed: Python {sys.version.split()[0]}, MediaPipe {mp.__version__}, OpenCV {cv2.__version__}")
    return 0


def diagnostics(output):
    from bluetooth_connection import BluetoothMonitor
    from bluetooth_users import DEFAULT_USERS_FILE
    report = {
        "packaged": bool(getattr(sys, "frozen", False)),
        "bleak_version": importlib.metadata.version("bleak"),
        "interface": "html",
        "pywebview_version": importlib.metadata.version("pywebview"),
        "dataset": str(DEFAULT_USERS_FILE),
        "scan_completed": False,
    }
    monitor = BluetoothMonitor()
    monitor.start()
    monitor.scan()
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            try:
                kind, payload = monitor.events.get(timeout=0.25)
            except queue.Empty:
                continue
            if kind == "devices":
                report.update(scan_completed=True, nearby_ble_devices_found=len(payload))
                break
            if kind in ("error", "unavailable"):
                report["error"] = payload
                break
        else:
            report["error"] = "Bluetooth scan did not complete within 20 seconds."
    finally:
        monitor.close()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["scan_completed"] else 1


def main():
    ensure_runtime()
    parser = argparse.ArgumentParser(description="Olive / Table Bluetooth restaurant menu")
    parser.add_argument("--diagnostics", metavar="REPORT_JSON", help="Check Bluetooth scanning and write a diagnostic report")
    parser.add_argument("--camera", action="store_true", help="Start with hand control (default)")
    parser.add_argument("--touch", action="store_true", help="Start with camera off; enable hand control using its button")
    parser.add_argument("--check", action="store_true", help="Check the camera recognition runtime without opening the camera")
    args = parser.parse_args()
    if args.diagnostics:
        return diagnostics(args.diagnostics)
    if args.check:
        return check_gesture_runtime()
    from menu_server_gui import main as start_menu
    return start_menu(camera_requested=not args.touch)


if __name__ == "__main__":
    raise SystemExit(main())
