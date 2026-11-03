/* Shared entry screen: Bluetooth rewards or an explicit guest visit. */
"use strict";
window.BluetoothUI = (() => {
  let state = {revision:-1, connected:false, user:null, session_id:null, devices:[], busy:false, available:true,
    message:"Starting Bluetooth…", camera_enabled:false, camera_available:true, camera_error:"", setup:{}};
  let selected = "", helpOpen = false, fetching = false;
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const native = () => window.pywebview && window.pywebview.api;
  const isConnected = () => Boolean(state.connected && state.user);
  const isGuest = () => Boolean(state.guest && state.user && state.session_id);
  const hasAccess = () => isConnected() || isGuest();

  function resetPage() {
    if (typeof S === "undefined") return;
    clearTimeout(S.toastTimer); clearTimeout(S.orderTimer);
    Object.assign(S, {scr:"bluetooth", cat:"Main courses", cart:{}, modal:null, mq:1, toast:"", sent:false, confirm:false, page:0, history:[]});
  }
  function update(next) {
    if (!next || typeof next.connected !== "boolean") return;
    if (next.revision < state.revision || (next.revision === state.revision && !hasAccess() && (next.connected || next.guest))) return;
    const oldSession = state.session_id;
    const oldAccess = hasAccess();
    const changed = JSON.stringify(next) !== JSON.stringify(state);
    state = next;
    if (!hasAccess()) {
      endConfirm=false;
      if (oldAccess || (typeof S !== "undefined" && S.scr !== "bluetooth")) resetPage();
    } else if (!oldAccess || oldSession !== state.session_id) {
      resetPage(); S.scr = "welcome"; helpOpen = false;
    }
    if (!state.devices.some(device => device.address === selected)) selected = state.devices[0]?.address || "";
    if (changed && typeof render === "function") render();
  }
  async function call(method, ...args) {
    if (!native()) {
      state.message = "Open this interface using Start Menu.cmd or OliveTable.exe to connect Bluetooth.";
      render(); return;
    }
    try {
      const next = await native()[method](...args);
      update(next);
      return next;
    } catch (error) {
      state = {...state, revision:-1, connected:false, guest:false, access_allowed:false, user:null, session_id:null, busy:false,
        message:"The Bluetooth connection could not be checked. Restart the desktop app and try again."};
      resetPage(); render();
    }
  }
  async function refresh() {
    if (fetching || !native()) return;
    fetching = true;
    try { await call("get_state"); } finally { fetching = false; }
  }
  function requireAccess() {
    if (hasAccess()) return true;
    resetPage(); if (typeof render === "function") render(); return false;
  }
  function select(index) { selected = state.devices[Number(index)]?.address || ""; render(); }
  async function scan() {
    if (state.busy) return;
    state = {...state, busy:true, message:"Looking for nearby Bluetooth devices…"}; render();
    await call("scan_bluetooth");
  }
  async function connect() {
    if (state.busy || !selected) return;
    state = {...state, busy:true, message:"Connecting and checking your phone…"}; render();
    await call("connect_bluetooth", selected);
  }
  async function setCamera(enabled, enterMenu=false) {
    const next = await call("set_camera", enabled);
    if (next?.camera_error) tip(next.camera_error);
    else if (next && enterMenu) browse();
  }
  async function copy(value) {
    try { await navigator.clipboard.writeText(value); }
    catch (_) {
      const input=document.createElement('textarea');
      input.value=value;input.readOnly=true;input.style.position='fixed';input.style.opacity='0';
      document.body.appendChild(input);input.select();
      let copied=false;
      try {copied=document.execCommand('copy');} finally {input.remove();}
      if(!copied)tip('Copy is unavailable. Use the value shown in the setup guide.');
    }
  }
  function help() {
    const setup = state.setup || {};
    return `<div class="scrim" role="presentation"><section class="bt-help card" role="dialog" aria-modal="true" aria-labelledby="bt-help-title">
      <h2 id="bt-help-title">Set up your iPhone once</h2>
      <ol><li>Install <b>LightBlue by Punch Through</b> on your iPhone and allow Bluetooth.</li>
      <li>Open <b>Virtual</b>, press <b>+</b>, create a blank device and give it your phone’s name.</li>
      <li>Add the service below, then add its characteristic. Enable <b>Read</b>.</li></ol>
      ${[["Service UUID","service"],["Characteristic UUID","characteristic"],["Phone ID — use UTF-8 / text format","phone_id"]].map(([label,key])=>`
      <label class="bt-copy"><b>${label}</b><span class="bt-copy-row"><input readonly aria-label="${label}" value="${escape(setup[key])}" onclick="this.select()"><button class="btn" onclick="BluetoothUI.copySetup('${key}')">Copy</button></span></label>`).join("")}
      <p class="small">If LightBlue is in Hex mode, the suggested Phone ID is: <code>${Array.from(setup.phone_id || "").map(c=>c.charCodeAt(0).toString(16).padStart(2,"0")).join("").toUpperCase()}</code></p>
      <p class="small">Every phone needs its own permanent Phone ID. If you already configured your phone, keep its saved ID to keep your points.</p>
      <ol start="4"><li>Save your device. Go back to the <b>Virtual Devices list</b> and select the circle beside your device to start advertising.</li>
      <li>Keep LightBlue open and the iPhone unlocked. Close this help, scan for phones, select yours and connect.</li></ol>
      <p class="small">The advertised device name becomes your username. Turning on Bluetooth in Settings alone is not enough.</p>
      <button class="btn p" onclick="BluetoothUI.showHelp(false)">Back to Bluetooth connection</button>
    </section></div>`;
  }
  function page() {
    return `<main class="bt-page"><div class="bt-intro"><span class="logo">OLIVE / TABLE</span>
      <span class="pill">YOUR TABLE AWAITS</span><h1>Connect your phone<br> or join as a guest.</h1>
      <p>Make yourself at home. Connect your phone to collect rewards, or skip Bluetooth and explore as a guest.</p>
      <div class="bt-points"><b>+10</b><span>points each time you successfully connect.<br>Your points are saved for your next visit.</span></div>
      <p class="small">If your Bluetooth connection drops, you’ll return to this page automatically.</p></div>
      <section class="card stack bt-connect"><span class="pill">YOUR PHONE · YOUR TABLE</span>
      <h2>Keep your phone nearby.</h2><p>In LightBlue, select your saved virtual device and keep the app open.</p>
      <b>Nearby Bluetooth devices</b>
      <div class="bt-device-list" role="group" aria-label="Choose your phone">
      ${state.devices.length ? state.devices.map((device,index)=>`<button class="bt-device ${device.address===selected?'on':''}" aria-pressed="${device.address===selected}" onclick="BluetoothUI.select(${index})" ${state.busy?'disabled':''}><span>${escape(device.name)}<small>${escape(device.address)}</small></span><i>${device.address===selected?'✓':'○'}</i></button>`).join("") : '<p class="small">Scan to find your phone</p>'}</div>
      <p class="bt-message" role="status" aria-live="polite">${state.busy?'<span class="spin" aria-hidden="true"></span> ':""}${escape(state.message)}</p>
      <div class="bt-actions"><button class="btn" onclick="BluetoothUI.scan()" ${state.busy||!state.available?"disabled":""}>Scan for phones</button>
      <button class="btn p" onclick="BluetoothUI.connect()" ${state.busy||!selected||!state.available?"disabled":""}>Connect Bluetooth</button></div>
      <button class="btn" onclick="BluetoothUI.continueAsGuest()">Skip · Continue as guest →</button>
      <p class="small">Guest visits include the menu and hand controls. Points are only saved for Bluetooth visits.</p>
      <button class="tab bt-help-link" onclick="BluetoothUI.showHelp(true)">How to connect your iPhone</button>
      <p class="small">Swipe to highlight Bluetooth or guest, then hold up one finger to select. Touch and mouse work too.</p></section></main>${helpOpen?help():""}`;
  }
  function sessionBar() {
    if (!hasAccess()) return "";
    if (isGuest()) return `<div class="bt-user-bar"><span>Welcome, <b>Guest</b><br>Guest visit · Points are not saved</span><button class="tab" onclick="BluetoothUI.requestEndVisit()">End visit</button></div>`;
    const signal=state.signal || {};
    return `<div class="bt-user-bar"><span>Welcome, <b>${escape(state.user.username)}</b> · <b>${state.user.points} points</b><br><span class="${signal.mode==='weak'?'signal-weak':''}">${signal.mode==='weak'?'Weak phone signal · move closer':signal.rssi!=null?`Bluetooth connected · ${signal.rssi} dBm`:'Bluetooth connected · live link checks'}</span></span>
      <button class="tab" onclick="BluetoothUI.requestEndVisit()">End visit</button></div>`;
  }
  window.addEventListener("pywebviewready", refresh);
  window.addEventListener("keydown", event => {
    if (event.key === "Escape" && helpOpen) { helpOpen = false; render(); }
    if (event.key.toLowerCase() === "q" && state.camera_enabled && !["INPUT","TEXTAREA"].includes(event.target?.tagName)) setCamera(false);
  });
  setInterval(refresh, 750);
  let endConfirm=false;
  return {page, update, refresh, requireAccess, isConnected, isGuest, hasAccess, resetPage, select, scan, connect, setCamera, copy,
    continueAsGuest(){return call('continue_as_guest');},
    showHelp(value){helpOpen=value;render();}, copySetup(key){return copy(state.setup[key] || "");}, sessionBar, escape,
    endVisit(){return call("end_visit");},
    requestEndVisit(){endConfirm=true;render();},
    overlay(){if(!endConfirm||!hasAccess())return '';return `<div class="scrim"><section class="confirm-card" role="dialog" aria-modal="true" aria-labelledby="end-title"><h2 id="end-title">End your visit?</h2><p>${isGuest()?'Your guest visit will end.':'Your points are saved.'} Your current order selection will be cleared.</p><button class="btn p" onclick="BluetoothUI.dismissOverlay()">Keep exploring</button><button class="btn" onclick="BluetoothUI.confirmEndVisit()">${isGuest()?'End guest visit':'End visit and disconnect'}</button></section></div>`;},
    confirmEndVisit(){endConfirm=false;return call('end_visit');},
    dismissOverlay(){if(!helpOpen&&!endConfirm)return false;helpOpen=false;endConfirm=false;render();return true;},
    user(){return state.user;}, sessionId(){return state.session_id;},
    cameraEnabled(){return Boolean(state.camera_enabled);},
    cameraAvailable(){return state.camera_available;}, cameraError(){return state.camera_error || "";}};
})();
