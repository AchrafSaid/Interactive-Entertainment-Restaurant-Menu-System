const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

function createUI(filename='index.html') {
  const app = {innerHTML:'', appendChild() {}};
  const timers = [];
  const context = {
    console,
    setInterval() {return 1;},
    setTimeout(callback) {timers.push(callback); return timers.length;},
    clearTimeout() {},
    addEventListener() {},
    prompt() {},
    navigator:{clipboard:{writeText:async()=>{}}},
    document:{body:{classList:{toggle(){}}}, getElementById(id){return id==='app'?app:null;}, createElement(){return {};}}
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'bluetooth_ui.js'),'utf8'),context);
  const html = fs.readFileSync(path.join(__dirname,filename),'utf8');
  for (const script of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) vm.runInContext(script[1],context);
  const evaluate = code => vm.runInContext(code,context);
  const snapshot = (changes={}) => ({revision:1,connected:true,session_id:'first',user:{username:'Nadeem',points:10,connections:1},
    devices:[],busy:false,available:true,message:'Connected',camera_enabled:false,camera_available:true,camera_error:'',setup:{},...changes});
  return {app,context,evaluate,timers,snapshot};
}

for (const filename of ['index.html','olive_table_with_gesture_sidebar.html']) {
  test(`${filename}: Bluetooth is the first and only unconnected page`,()=>{
    const ui=createUI(filename);
    assert.match(ui.app.innerHTML,/Connect Bluetooth/);
    assert.doesNotMatch(ui.app.innerHTML,/Gesture Guide|Start your experience|http:\/\/127.0.0.1:8765\/stream/);
    ui.evaluate(`go('browse');browse();review();openItem(ITEMS[0].id);add(ITEMS[0].id);place();window.handleGesture('OPEN_PALM')`);
    assert.equal(ui.evaluate('S.scr'),'bluetooth');
    assert.equal(ui.evaluate('cartCount()'),0);
    assert.equal(ui.evaluate('S.modal'),null);
  });
}

test('a verified connection restores the menu and selected dish quantity is added immediately',()=>{
  const ui=createUI(); ui.context.BluetoothUI.update(ui.snapshot());
  assert.equal(ui.evaluate('S.scr'),'welcome');
  assert.match(ui.app.innerHTML,/Nadeem/);
  assert.match(ui.app.innerHTML,/10 points/);
  assert.ok(ui.evaluate('ITEMS.length')>20);
  ui.evaluate(`go('gate');browse()`);
  assert.equal(ui.evaluate('S.scr'),'categories');
  assert.match(ui.app.innerHTML,/class="cat-card/);
  assert.doesNotMatch(ui.app.innerHTML,/onclick="openItem/);
  ui.evaluate(`setCategory(ITEMS[3].category);openItem(ITEMS[3].id);changeModalQty(2);addFromModal()`);
  assert.equal(ui.evaluate('S.scr'),'browse');
  assert.equal(ui.evaluate('cartCount()'),3);
  assert.equal(ui.evaluate('S.modal'),null);
  assert.doesNotMatch(ui.app.innerHTML,/class="modal"/);
});

test('categories show first, choosing one shows its dishes, and back returns to the list',()=>{
  const ui=createUI(); ui.context.BluetoothUI.update(ui.snapshot());
  ui.evaluate(`browse();setCategory('Drinks')`);
  assert.equal(ui.evaluate('S.scr'),'browse');
  assert.equal(ui.evaluate('S.cat'),'Drinks');
  assert.match(ui.app.innerHTML,/All categories/);
  ui.evaluate('allCategories()');  // also used by the fist gesture on the dishes screen
  assert.equal(ui.evaluate('S.scr'),'categories');
  ui.evaluate(`setCategory('Desserts')`);
  assert.equal(ui.evaluate('S.cat'),'Desserts');
  ui.evaluate('allCategories()');
  assert.equal(ui.evaluate('S.scr'),'categories');
  assert.ok(!ui.evaluate('S.history').includes('browse'));
});

test('checkout requires an explicit confirmation and can be cancelled',()=>{
  const ui=createUI();ui.context.BluetoothUI.update(ui.snapshot());
  ui.evaluate('browse();add(ITEMS[1].id);review();confirmOrder()');
  assert.equal(ui.evaluate('S.scr'),'review');
  assert.match(ui.app.innerHTML,/Confirm demo order/);
  ui.evaluate('S.confirm=false;render()');
  assert.doesNotMatch(ui.app.innerHTML,/Confirm demo order/);
  assert.equal(ui.evaluate('cartCount()'),1);
});

test('the Bluetooth gate supports hand control without admitting an unverified user',()=>{
  const ui=createUI();ui.context.BluetoothUI.update(ui.snapshot({connected:false,user:null,session_id:null,camera_enabled:true}));
  assert.match(ui.app.innerHTML,/src="http:\/\/127.0.0.1:8765\/stream"/);
  assert.equal(ui.context.BluetoothUI.cameraEnabled(),true);
  ui.evaluate('browse();add(ITEMS[0].id)');
  assert.equal(ui.evaluate('cartCount()'),0);
  assert.equal(ui.evaluate('S.scr'),'bluetooth');
});

test('disconnect clears the order, modal and private username and blocks every route',()=>{
  const ui=createUI(); ui.context.BluetoothUI.update(ui.snapshot());
  ui.evaluate('browse();openItem(ITEMS[0].id);add(ITEMS[0].id)');
  ui.context.BluetoothUI.update(ui.snapshot({revision:2,connected:false,user:null,session_id:null,message:'Connection lost'}));
  assert.equal(ui.evaluate('S.scr'),'bluetooth');
  assert.equal(ui.evaluate('cartCount()'),0);
  assert.equal(ui.evaluate('S.modal'),null);
  assert.doesNotMatch(ui.app.innerHTML,/Welcome, <b>Nadeem/);
  ui.evaluate(`go('games');go('rewards');review();window.handleGesture('OK_SIGN')`);
  assert.equal(ui.evaluate('S.scr'),'bluetooth');
});

test('camera preview appears only after Bluetooth and camera permission',()=>{
  const ui=createUI(); ui.context.BluetoothUI.update(ui.snapshot());
  assert.doesNotMatch(ui.app.innerHTML,/src="http:\/\/127.0.0.1:8765\/stream"/);
  ui.context.BluetoothUI.update(ui.snapshot({revision:2,camera_enabled:true}));
  assert.match(ui.app.innerHTML,/src="http:\/\/127.0.0.1:8765\/stream"/);
  ui.context.BluetoothUI.update(ui.snapshot({revision:3,connected:false,user:null,session_id:null,camera_enabled:false}));
  assert.doesNotMatch(ui.app.innerHTML,/src="http:\/\/127.0.0.1:8765\/stream"/);
});

test('Bluetooth names are escaped in the welcome and rewards UI',()=>{
  const ui=createUI(); ui.context.BluetoothUI.update(ui.snapshot({user:{username:'<img src=x onerror=alert(1)>',points:20,connections:2}}));
  ui.evaluate(`go('rewards')`);
  assert.doesNotMatch(ui.app.innerHTML,/<img src=x/);
  assert.match(ui.app.innerHTML,/&lt;img/);
  assert.match(ui.app.innerHTML,/20 points/);
});

test('late state replies cannot reopen an ended session',()=>{
  const ui=createUI(); ui.context.BluetoothUI.update(ui.snapshot());
  ui.context.BluetoothUI.update(ui.snapshot({revision:2,connected:false,user:null,session_id:null}));
  ui.context.BluetoothUI.update(ui.snapshot());
  ui.context.BluetoothUI.update(ui.snapshot({revision:2}));
  assert.equal(ui.evaluate('S.scr'),'bluetooth');
  assert.equal(ui.context.BluetoothUI.isConnected(),false);
});

test('an old order completion callback cannot change a new user session',()=>{
  const ui=createUI(); ui.context.BluetoothUI.update(ui.snapshot());
  ui.evaluate('browse();add(ITEMS[0].id);place()');
  const oldCallback = ui.timers.at(-1);
  ui.context.BluetoothUI.update(ui.snapshot({revision:2,connected:false,user:null,session_id:null}));
  ui.context.BluetoothUI.update(ui.snapshot({revision:3,session_id:'second',user:{username:'Second guest',points:10,connections:1}}));
  oldCallback();
  assert.equal(ui.evaluate('S.sent'),false);
  assert.equal(ui.evaluate('cartCount()'),0);
});

for(const filename of ['index.html','olive_table_with_gesture_sidebar.html']) {
  test(`${filename}: skip starts a guest visit with menu and demo checkout`,async()=>{
    const ui=createUI(filename);
    assert.match(ui.app.innerHTML,/Skip · Continue as guest/);
    const guest=ui.snapshot({guest:true,access_allowed:true,connected:false,session_id:'guest-one',user:{username:'Guest',points:0,connections:0}});
    ui.context.pywebview={api:{continue_as_guest:async()=>guest}};
    await ui.context.BluetoothUI.continueAsGuest();
    assert.equal(ui.evaluate('S.scr'),'welcome');
    assert.equal(ui.context.BluetoothUI.isConnected(),false);
    assert.equal(ui.context.BluetoothUI.isGuest(),true);
    ui.evaluate('browse();openItem(ITEMS[2].id);addFromModal();review();place()');
    assert.equal(ui.evaluate('S.scr'),'sending');
    ui.timers.at(-1)();
    assert.equal(ui.evaluate('S.sent'),true);
    ui.evaluate("go('rewards')");
    assert.match(ui.app.innerHTML,/Guest visits do not earn or save points/);
    assert.doesNotMatch(ui.app.innerHTML,/Bluetooth connected|\b0 points|connected 0 time/);
    ui.context.BluetoothUI.update(ui.snapshot({revision:2,connected:false,guest:false,user:null,session_id:null}));
    assert.equal(ui.evaluate('S.scr'),'bluetooth');
    assert.equal(ui.evaluate('cartCount()'),0);
    ui.context.BluetoothUI.update(guest);
    assert.equal(ui.context.BluetoothUI.hasAccess(),false);
  });
}
