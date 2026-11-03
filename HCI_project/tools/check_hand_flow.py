"""Exercise actual DOM hit testing through the app's hand input API in WebView2."""
import json
from pathlib import Path
import queue
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
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
    def scan(self):
        self.events.put(('devices', [BluetoothDevice('AA', 'Another phone'), BluetoothDevice('BB', 'Hand test guest')]))
    def connect(self, address):
        self.is_connected = True
        self.events.put(('connected', (BluetoothDevice(address, 'Hand test guest', True, 'test-phone'), 'test-link')))
    def disconnect(self): self.is_connected = False


def main():
    report = {'passed':False, 'uses_real_camera':False, 'uses_real_bluetooth':False,
              'transport':'WebView2 DOM hit testing and app hand event handler'}
    with tempfile.TemporaryDirectory() as directory:
        monitor=Monitor()
        bridge=BluetoothBridge(monitor, BluetoothUserStore(Path(directory)/'users.txt'))
        bridge.set_camera(True)

        def check():
            def js(code): return host.window.evaluate_js(code)
            def wait(expression):
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    if js(expression): return
                    time.sleep(.1)
                raise AssertionError(expression)
            def click(selector):
                time.sleep(.6)  # A released pinch, then a new intentional pinch.
                result=js('''(()=>{const button=document.querySelector(SELECTOR);
                    if(!button)return 'Missing button: '+SELECTOR;
                    button.scrollIntoView({block:'center',behavior:'instant'});
                    const r=button.getBoundingClientRect();
                    const e={type:'hand',action:'point',pose:'point',x:(r.x+r.width/2)/innerWidth,y:(r.y+r.height/2)/innerHeight};
                    window.handleGesture(e);
                    if(!button.classList.contains('hand-focus'))return 'Hit test missed: '+SELECTOR;
                    window.handleGesture({...e,action:'click'});return true;})()'''.replace('SELECTOR',json.dumps(selector)))
                assert result is True,result
            def button(action): click('button[onclick='+json.dumps(action)+']')

            try:
                assert host.page_loaded.wait(20)
                wait("window.BluetoothUI && BluetoothUI.cameraEnabled()")
                js("browse();add(ITEMS[0].id)")
                assert js("S.scr==='bluetooth'&&cartCount()===0")
                assert js("document.documentElement.scrollWidth<=innerWidth+1")
                button('BluetoothUI.continueAsGuest()')
                wait("S.scr==='welcome'&&BluetoothUI.isGuest()")
                assert js("!BluetoothUI.isConnected()")
                button("go('gate')")
                button('BluetoothUI.setCamera(true,true)')
                wait("S.scr==='browse'")
                guest_item=js("ITEMS.filter(x=>x.category===S.cat)[1].id")
                button("openItem('"+guest_item+"')")
                button('addFromModal()')
                assert js('cartCount()===1')
                button("go('rewards')")
                assert js("document.body.innerText.includes('Guest visits do not earn or save points')")
                js("window.handleGesture({type:'hand',action:'back'})")
                assert js("S.scr==='browse'")
                button('BluetoothUI.requestEndVisit()')
                button('BluetoothUI.confirmEndVisit()')
                wait("S.scr==='bluetooth'&&cartCount()===0")
                assert not (Path(directory)/'users.txt').exists()
                report['guest_skip_menu_hands_and_no_saved_points']=True
                button('BluetoothUI.showHelp(true)')
                assert js("Boolean(document.querySelector('.bt-help'))")
                js("window.handleGesture({type:'hand',action:'back'})")
                assert js("!document.querySelector('.bt-help')")
                button('BluetoothUI.scan()')
                wait("Boolean(document.querySelector('.bt-device'))")
                button('BluetoothUI.select(1)')
                button('BluetoothUI.connect()')
                wait("S.scr==='welcome'")
                report['phone_gate_by_hand']=True
                button("go('gate')")
                button('BluetoothUI.setCamera(true,true)')
                wait("S.scr==='browse'")
                button("setCategory('Drinks')")
                # Pick the third dish rather than the old first-dish-only path.
                item=js("ITEMS.filter(x=>x.category===S.cat)[2].id")
                button("openItem('"+item+"')")
                button('changeModalQty(1)')
                button('changeModalQty(1)')
                button('changeModalQty(-1)')
                assert js('S.mq===2')
                button('addFromModal()')
                assert js("S.modal===null && cartCount()===2 && !document.querySelector('.modal')")
                report['any_dish_and_modal_quantity']=True
                button('review()')
                button("removeOne('"+item+"')")
                assert js('cartCount()===1')
                button("add('"+item+"')")
                button('confirmOrder()')
                assert js("S.scr==='review'&&S.confirm")
                button('S.confirm=false;render()')
                assert js('!S.confirm&&cartCount()===2')
                button('confirmOrder()')
                button('place()')
                wait("S.scr==='sending'")
                report['edit_cart_and_confirm_order']=True
                button("go('rewards')")
                assert js("document.body.innerText.includes('10 points')")
                button("go('games')")
                js("window.handleGesture({type:'hand',action:'back'})")
                assert js("S.scr==='rewards'")
                button('BluetoothUI.requestEndVisit()')
                button('BluetoothUI.dismissOverlay()')
                assert js('BluetoothUI.isConnected()')
                button('BluetoothUI.requestEndVisit()')
                button('BluetoothUI.confirmEndVisit()')
                wait("S.scr==='bluetooth'&&cartCount()===0")
                report['end_visit_confirmation_by_hand']=True
                # Reconnect a new visit, then test independent radio loss.
                monitor.is_connected=True
                bridge._process_event('connected',(BluetoothDevice('BB','Hand test guest',True,'test-phone'),'second-link'))
                wait("S.scr==='welcome'")
                js("browse();add(ITEMS[1].id)")
                host.window.resize(900,650)
                time.sleep(.2)
                assert js("document.documentElement.scrollWidth<=innerWidth+1")
                js("window.handleGesture({type:'hand',action:'scroll',pose:'scroll',x:.5,y:.5,delta:100})")
                assert js('window.scrollY>0')
                js("window.handleGesture({type:'hand',action:'lost'})")
                assert js("document.getElementById('hand-cursor').hidden")
                report['small_window_scroll_and_tracking_loss']=True
                report['all_navigation_by_hand']=True
                # A real transport loss also locks before its queued UI event.
                monitor.is_connected=False
                wait("S.scr==='bluetooth'&&cartCount()===0")
                assert js("!document.body.innerText.includes('Hand test guest')&&BluetoothUI.cameraEnabled()")
                report['link_loss_clears_user_and_cart']=True
                report['passed']=True
            except Exception as error:
                report['error']=str(error)
            finally:
                path=ROOT/'build'/'hand-flow-check.json'
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps(report,indent=2),encoding='utf-8')
                host.window.destroy()
        host.main(test_callback=check,bridge=bridge)
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
