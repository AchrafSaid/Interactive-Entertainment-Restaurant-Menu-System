/* Point and pinch operates the same real buttons as touch and keyboard. */
"use strict";
window.HandUI = (() => {
  let cursor, target = null, lastSeen = 0, lastClick = 0, active = false;
  const now = () => Date.now();
  function clear() {
    target?.classList.remove("hand-focus"); target = null;
    if (cursor) cursor.hidden = true;
  }
  function status(message) {
    const el = document.getElementById("hand-status");
    if (el && el.textContent !== message) el.textContent = message;
  }
  function hit(x, y) {
    const el = document.elementFromPoint(x, y);
    const button = el?.closest("button, [data-hand-target]");
    const modal = Array.from(document.querySelectorAll('.scrim')).at(-1);
    if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true' || (modal && !modal.contains(button))) return null;
    return button;
  }
  function scrollAt(x, y, delta) {
    let el = document.elementFromPoint(x, y);
    while (el && el !== document.body) {
      const style = getComputedStyle(el);
      if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight) {
        el.scrollBy({top:delta, behavior:"instant"}); return;
      }
      el = el.parentElement;
    }
    window.scrollBy({top:delta, behavior:"instant"});
  }
  function back() {
    if (BluetoothUI.dismissOverlay()) return;
    if (!BluetoothUI.hasAccess()) return;
    if (S.confirm) {S.confirm=false;render();return;}
    if (S.modal) {closeModal();return;}
    const screen = S.history?.pop() || (S.scr === 'welcome' ? 'welcome' : 'browse');
    S.scr=screen;S.modal=null;render();window.scrollTo?.(0,0);
  }
  function handle(event) {
    if (!event || event.type !== "hand" || !BluetoothUI.cameraEnabled()) return;
    if (event.action === "lost") {clear();status("Show one hand to the camera");return;}
    lastSeen=now();
    if (event.action === "back") {clear();back();status("Back · relax your hand to repeat");return;}
    if (!Number.isFinite(event.x) || !Number.isFinite(event.y)) return;
    const x=Math.max(12,Math.min(innerWidth-12,event.x*innerWidth));
    const y=Math.max(12,Math.min(innerHeight-12,event.y*innerHeight));
    if (event.pose === "scroll") {
      clear();scrollAt(x,y,Math.max(-100,Math.min(100,event.delta || 0)));
      status("Scrolling · move two fingers up or down");return;
    }
    if (event.pose !== "point") {
      clear();status(event.pose==='back' ? 'Hold fist to go back…' : 'Paused · point one finger to resume');return;
    }
    if (!cursor) return;
    cursor.hidden=false;cursor.style.transform=`translate(${x}px, ${y}px)`;
    cursor.style.setProperty('--progress',Math.round((event.progress || 0)*360)+'deg');
    const next=hit(x,y);
    if (target !== next) {target?.classList.remove('hand-focus');target=next;target?.classList.add('hand-focus');}
    cursor.classList.toggle('on-target',Boolean(target));
    status(target ? 'Pinch thumb + index to select · release to repeat' : 'Point at a button · two fingers to scroll');
    if (event.action === "click" && target && now()-lastClick>450) {
      lastClick=now();
      const button=target;clear();button.click();status('Selected · open your pinch before selecting again');
    }
  }
  function afterRender() {
    active=BluetoothUI.cameraEnabled();
    document.body.classList.toggle('hands-on',active);
    if (!cursor) {
      cursor=document.createElement('div');cursor.id='hand-cursor';cursor.hidden=true;
      cursor.setAttribute('aria-hidden','true');document.body.appendChild(cursor);
    }
    clear();
    // All controls use ordinary semantic buttons; quantity controls get names.
    document.querySelectorAll('.qty button').forEach(button=>button.setAttribute('aria-label',button.textContent.trim()==='+'?'Increase quantity':'Decrease quantity'));
  }
  let legacyIndex=0;
  function legacy(gesture) {
    if (typeof gesture !== 'string') return;
    const g=gesture.trim().toUpperCase();
    if (g==='CLOSED_FIST'||g==='THUMBS_DOWN') {back();return;}
    if (g==='C_SHAPE') {review();return;}
    if (g==='SWIPE_UP'||g==='SWIPE_DOWN') {window.scrollBy({top:g==='SWIPE_DOWN'?300:-300});return;}
    const modal=Array.from(document.querySelectorAll('.scrim')).at(-1);
    const buttons=Array.from((modal||document.getElementById('app')).querySelectorAll('button'))
      .filter(button=>!button.disabled&&button.getClientRects().length);
    if(!buttons.length)return;
    if(g==='SWIPE_RIGHT')legacyIndex++;
    if(g==='SWIPE_LEFT')legacyIndex--;
    legacyIndex=(legacyIndex+buttons.length)%buttons.length;
    clear();target=buttons[legacyIndex];target.classList.add('hand-focus');target.scrollIntoView({block:'nearest'});
    if(['SELECT_PRODUCT','V_SHAPE','THUMBS_UP','OK_SIGN'].includes(g)){target.click();legacyIndex=0;}
  }
  window.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();back();}});
  setInterval(()=>{if (active && now()-lastSeen>650) {clear();status('Show one hand to the camera');}},150);
  return {handle,afterRender,back,clear,legacy};
})();
