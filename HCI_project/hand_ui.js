/* Gesture-only control: one highlighted button, moved by swipes and pressed
   by holding up one finger. It operates the same real buttons as touch. */
"use strict";
window.HandUI = (() => {
  let target = null, lastSeen = 0, active = false;
  const remembered = new Map();  // scope name -> key of its highlighted button
  const now = () => Date.now();
  const keyOf = el => el ? `${el.getAttribute('onclick') || ''}|${el.textContent.trim()}` : null;

  function status(message) {
    const el = document.getElementById("hand-status");
    if (el && el.textContent !== message) el.textContent = message;
  }
  function scope() {
    return Array.from(document.querySelectorAll('.scrim')).at(-1) || document.getElementById('app');
  }
  // Dialogs are re-created on every render, so scopes are named rather than compared.
  function scopeName(root = scope()) {
    if (!root || root.id === 'app') return `app:${S.scr}`;
    return `dialog:${root.firstElementChild?.className || ''}:${S.modal || ''}`;
  }
  function focusables() {
    const root = scope();
    if (!root) return [];
    return Array.from(root.querySelectorAll('button, [data-hand-target]')).filter(el =>
      !el.disabled && el.getAttribute('aria-disabled') !== 'true' &&
      !el.closest('.gesture-sidebar') && el.getClientRects().length);
  }
  function setFocus(el, scroll = true) {
    if (target !== el) {clear();target = el;}
    if (!el) return;
    if (active) el.classList.add('hand-focus');
    remembered.set(scopeName(), keyOf(el));
    if (scroll && active) el.scrollIntoView?.({block:'nearest', inline:'nearest'});
  }
  function clear() {target?.classList.remove('hand-focus');target?.style.removeProperty('--hold');}
  // Choose a sensible starting button: the main action of a dialog or screen,
  // e.g. the first dish's View button or "Add to order".
  function defaultFocus(list) {
    return list.find(el => el.matches('[data-hand-default]')) || list.find(el => el.matches('.btn.p, .cat-card')) || list[0] || null;
  }
  function ensureFocus() {
    const list = focusables();
    if (target && list.includes(target)) return list;
    const key = remembered.get(scopeName());
    const match = key ? list.find(el => keyOf(el) === key) : null;
    setFocus(match || defaultFocus(list), false);
    return list;
  }
  const centre = el => {const r = el.getBoundingClientRect();return {x:r.left + r.width / 2, y:r.top + r.height / 2};};
  // Move the highlight to the nearest button in the swipe direction.
  // dishesOnly: when moving sideways with two fingers, stay on the dish cards.
  function move(direction, dishesOnly = false) {
    let list = ensureFocus();
    if (dishesOnly && dishOf(target) && (direction === 'left' || direction === 'right')) list = list.filter(el => dishOf(el));
    if (!list.length) return 'Nothing to select here';
    if (!target) {setFocus(list[0]);return describe();}
    const from = centre(target);
    const axis = direction === 'left' || direction === 'right' ? 'x' : 'y';
    const other = axis === 'x' ? 'y' : 'x';
    const sign = direction === 'right' || direction === 'down' ? 1 : -1;
    let best = null, bestScore = Infinity;
    for (const el of list) {
      if (el === target) continue;
      const c = centre(el);
      const along = (c[axis] - from[axis]) * sign;
      if (along <= 8) continue;
      const score = along + Math.abs(c[other] - from[other]) * 2.5;
      if (score < bestScore) {bestScore = score;best = el;}
    }
    if (!best && axis === 'x') {
      // Wrap through the buttons in reading order at the end of a row.
      const i = list.indexOf(target);
      best = list[(i + sign + list.length) % list.length];
    }
    if (!best) {
      // Nothing more to highlight that way: scroll the page instead (long text, footers).
      scrollPage(sign * 320);
      return direction === 'down' ? 'Scrolled down' : 'Scrolled up';
    }
    setFocus(best);
    return describe();
  }
  function label(el) {
    const dish = dishOf(el);
    if (dish) return `${$(dish)?.n || 'Dish'} · View`;
    return (el.getAttribute('aria-label') || el.textContent || 'Button').trim().replace(/\s+/g, ' ').slice(0, 48);
  }
  const describe = () => target ? `▶ ${label(target)} · hold one finger to select` : 'Nothing to select here';
  const dishOf = el => el?.getAttribute('onclick')?.match(/openItem\('([^']+)'\)/)?.[1] || null;

  function select() {
    ensureFocus();
    if (!target) return 'Nothing to select here';
    const name = label(target), button = target;
    button.click();
    return `Selected ${name} · relax your finger to select again`;
  }
  // After scrolling, keep the highlight on something the user can see.
  function keepFocusVisible() {
    if (!target) return;
    const r = target.getBoundingClientRect();
    if (r.bottom > 0 && r.top < innerHeight) return;
    const list = focusables().filter(el => {const b = el.getBoundingClientRect();return b.bottom > 0 && b.top < innerHeight;});
    if (!list.length) return;
    const mid = innerHeight / 2, x = r.left + r.width / 2;
    list.sort((a, b) => {
      const ca = centre(a), cb = centre(b);
      return (Math.abs(ca.y - mid) + Math.abs(ca.x - x) * .5) - (Math.abs(cb.y - mid) + Math.abs(cb.x - x) * .5);
    });
    // Prefer a dish if one is on screen.
    setFocus(list.find(el => dishOf(el)) || list[0], false);
  }
  function scrollPage(delta) {
    let el = target || scope();
    while (el && el !== document.body) {
      const style = getComputedStyle(el);
      if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight) {
        el.scrollBy({top:delta, behavior:"instant"}); keepFocusVisible(); return;
      }
      el = el.parentElement;
    }
    window.scrollBy({top:delta, behavior:"instant"});
    keepFocusVisible();
  }
  function back() {
    if (BluetoothUI.dismissOverlay()) return;
    if (!BluetoothUI.hasAccess()) return;
    if (S.confirm) {S.confirm=false;render();return;}
    if (S.modal) {closeModal();return;}
    if (S.scr === 'browse') {allCategories();return;}
    const screen = S.history?.pop() || (S.scr === 'welcome' ? 'welcome' : 'categories');
    S.scr=screen;S.modal=null;render();window.scrollTo?.(0,0);
  }

  // Hold-to-trigger shortcut poses (see hand_input.py HOLD_POSES).
  const inMenu = () => BluetoothUI.hasAccess() && !['bluetooth','welcome','gate'].includes(S.scr);
  function addProduct() {
    if (S.modal) {const name=$(S.modal)?.n;addFromModal();return `${name} added to your order`;}
    const dish = dishOf(target);
    if (dish && $(dish)) {add(dish);return `${$(dish).n} added to your order`;}
    return 'Highlight a dish (or open it) first, then thumbs up';
  }
  function declineProduct() {
    if (S.modal) {const name=$(S.modal)?.n;S.modal=null;S.mq=1;render();return `${name} declined`;}
    if (S.confirm) {S.confirm=false;render();return 'Checkout cancelled · keep editing';}
    return 'Open a dish first, then thumbs down to decline it';
  }
  function checkout() {
    if (!cartCount()) {tip('Your order is empty');return 'Add something before checking out';}
    if (S.confirm) {place();return 'Order confirmed';}
    if (S.scr !== 'review') review();
    confirmOrder();return 'Final review · OK sign again to confirm';
  }
  const SHORTCUTS = {
    menu:     {label:'Open palm · Open menu',         anywhere:true, run:()=>{browse();return 'Menu opened';}},
    add:      {label:'Thumbs up · Add product',       run:addProduct},
    decline:  {label:'Thumbs down · Decline product', run:declineProduct},
    cart:     {label:'C shape · Open cart',           run:()=>{review();return 'Cart opened';}},
    checkout: {label:'OK sign · Confirm checkout',    run:checkout},
    games:    {label:'Rock sign · Games',             run:()=>{go('games');return 'Games opened';}},
    rewards:  {label:'Three fingers · Rewards',       run:()=>{go('rewards');return 'Rewards opened';}},
  };
  function shortcut(name) {
    const entry = SHORTCUTS[name];
    if (!entry) return;
    const allowed = entry.anywhere ? BluetoothUI.hasAccess() && S.scr !== 'bluetooth' : inMenu();
    if (!allowed) {status('Connect or continue as guest first');return;}
    BluetoothUI.dismissOverlay();
    status(entry.run() + ' · relax your hand to repeat');
  }
  const HOLD_LABELS = {select:'One finger · Select', back:'Fist · Close / back'};

  function handle(event) {
    if (!event || event.type !== "hand" || !BluetoothUI.cameraEnabled()) return;
    if (event.action === "lost") {status("Show one hand to the camera");return;}
    lastSeen = now();
    ensureFocus();
    // Grow the highlight's glow while one finger is held, so progress is visible.
    target?.style.setProperty('--hold', event.pose === 'select' && event.action === 'pose' ? (event.progress || 0) : 0);
    switch (event.action) {
      case "back": back();status("Back · relax your hand to repeat");return;
      case "shortcut": shortcut(event.shortcut);return;
      case "select": status(select());return;
      case "swipe":
        {
          const moved = event.source === 'scroll' ? move(event.direction, true) : move(event.direction);
          // Show what the DollarPy recogniser classified, and how confident it was.
          const dollar = event.gesture ? ` · DollarPy: ${event.gesture} ${Math.round((event.score || 0) * 100)}%` : '';
          status(moved + dollar);
        }
        return;
      case "scroll":
        status(`${describe()} · move two fingers up, down, left or right`);return;
    }
    const hold = SHORTCUTS[event.pose]?.label || HOLD_LABELS[event.pose];
    if (hold && event.progress > 0) {
      const what = event.pose === 'select' && target ? ` ${label(target)}` : '';
      status(`${hold}${what} · hold… ${Math.round(event.progress * 100)}%`);return;
    }
    status(describe() + ' · swipe to move');
  }
  function afterRender() {
    active = BluetoothUI.cameraEnabled();
    document.body.classList.toggle('hands-on', active);
    target = null;
    ensureFocus();
    if (!active) clear();
    // All controls use ordinary semantic buttons; quantity controls get names.
    document.querySelectorAll('.qty button').forEach(button=>button.setAttribute('aria-label',button.textContent.trim()==='+'?'Increase quantity':'Decrease quantity'));
  }
  function legacy(gesture) {
    if (typeof gesture !== 'string') return;
    const g = gesture.trim().toUpperCase();
    const swipe = {SWIPE_LEFT:'left', SWIPE_RIGHT:'right', SWIPE_UP:'up', SWIPE_DOWN:'down'}[g];
    if (swipe) {status(move(swipe));return;}
    const named = {CLOSED_FIST:null, THUMBS_UP:'add', THUMBS_DOWN:'decline', OPEN_PALM:'menu',
                   OK_SIGN:'checkout', C_SHAPE:'cart'};
    if (g === 'CLOSED_FIST') {back();return;}
    if (named[g]) {shortcut(named[g]);return;}
    if (['SELECT_PRODUCT','ONE_FINGER','V_SHAPE'].includes(g)) status(select());
  }
  window.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();back();}});
  setInterval(()=>{if (active && lastSeen && now()-lastSeen>650) {status('Show one hand to the camera');lastSeen=0;}},150);
  return {handle,afterRender,back,clear,legacy,move,select};
})();
