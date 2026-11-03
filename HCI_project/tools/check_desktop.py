"""Check the real WebView2 interface using a temporary, simulated BLE session."""

import json
from pathlib import Path
import queue
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import menu_server_gui as host
from bluetooth_bridge import BluetoothBridge
from bluetooth_connection import BluetoothDevice
from bluetooth_users import BluetoothUserStore


class Monitor:
    def __init__(self):
        self.events = queue.Queue()
        self.is_connected = False
    def start(self): pass
    def close(self): pass
    def disconnect(self): self.is_connected = False


def main():
    report = {"passed":False,"transport":"WebView2 and Python API","uses_real_bluetooth":False}
    monitor = Monitor()
    with tempfile.TemporaryDirectory() as directory:
        bridge = BluetoothBridge(monitor, BluetoothUserStore(Path(directory)/"users.txt"), camera_available=False)

        def check():
            def wait_for(expression):
                deadline = time.monotonic()+15
                while time.monotonic()<deadline:
                    if host.window.evaluate_js(expression):
                        return
                    time.sleep(0.1)
                raise AssertionError(expression)

            try:
                if not host.page_loaded.wait(20):
                    raise AssertionError("The HTML interface did not load")
                wait_for("Boolean(window.pywebview && window.pywebview.api && window.BluetoothUI)")
                host.window.evaluate_js("browse();window.handleGesture('OPEN_PALM')")
                assert host.window.evaluate_js("S.scr==='bluetooth' && Boolean(document.querySelector('.gesture-sidebar'))")
                assert host.window.evaluate_js("document.documentElement.scrollWidth<=window.innerWidth+1")
                report["initial_gate"] = True
                monitor.is_connected = True
                bridge._process_event("connected",(BluetoothDevice("AA","Test guest",True,"test-phone"),"test-link-1"))
                wait_for("S.scr==='welcome' && document.body.innerText.includes('10 points')")
                host.window.evaluate_js("browse();openItem(ITEMS[0].id);addFromModal();go('rewards')")
                assert host.window.evaluate_js("cartCount()===1 && document.body.innerText.includes('10 points')")
                report["menu_rewards_and_cart"] = True
                monitor.is_connected = False
                bridge._process_event("disconnected","test-link-1")
                wait_for("S.scr==='bluetooth' && cartCount()===0 && Boolean(document.querySelector('.gesture-sidebar'))")
                report["disconnect_locks_and_clears_order"] = True
                monitor.is_connected = True
                bridge._process_event("connected",(BluetoothDevice("BB","Test guest",True,"test-phone"),"test-link-2"))
                wait_for("S.scr==='welcome' && document.body.innerText.includes('20 points')")
                report["reconnect_points"] = True
                host.window.evaluate_js("BluetoothUI.endVisit()")
                wait_for("S.scr==='bluetooth'")
                report["passed"] = True
            except Exception as error:
                report["error"] = str(error)
            finally:
                target = ROOT/"build"/"desktop-flow-check.json"
                target.parent.mkdir(exist_ok=True)
                target.write_text(json.dumps(report,indent=2),encoding="utf-8")
                host.window.destroy()

        host.main(test_callback=check,bridge=bridge)
    print(json.dumps(report,indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
