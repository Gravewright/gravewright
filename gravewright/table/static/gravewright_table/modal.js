import { registerEscapeClose } from '/static/gravewright_web/escape.js';

let active;
const origins = new WeakMap();

function connectedPrior(origin) {
  while (origin && (origin.closed || !origin.modal.isConnected)) origin = origin.prior;
  return origin?.modal;
}

export function mountModal(modal, {canClose = () => true, nested = false} = {}) {
  if (modal.localName === 'dialog') throw new TypeError('Use a section for project modals.');
  const document = modal.ownerDocument;
  // Keep immutable ancestry when an already closed element is mounted again.
  const prior = origins.get(active), inherited = prior;
  if (!nested) active?.close();
  const previous = document.activeElement;
  const overlay = document.createElement('div');
  overlay.className = 'ownership-modal-overlay';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.tabIndex = -1;
  const background = [...document.body.children].filter(element => element !== modal).map(element => [element,
    inherited?.background.find(([node]) => node === element)?.[1] ?? element.inert]);
  const overflow = inherited?.overflow ?? document.body.style.overflow;
  const origin = {background, overflow, prior, overlay, modal, closed: false};
  origins.set(modal, origin);
  const focusable = () => [...modal.querySelectorAll('button, input, select, textarea, a[href], [tabindex]')]
    .filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length);
  const keydown = event => {
    if (active !== modal || suspended) return;
    if (event.key === 'Tab') {
      const elements = focusable(), first = elements[0] || modal, last = elements.at(-1) || modal;
      if (event.shiftKey && (document.activeElement === first || !modal.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !modal.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    }
  };
  let closed = false, suspended = false, closing;
  modal.suspend = () => {
    if (closed || suspended) return;
    suspended = true; overlay.hidden = true;
    for (const [element, inert] of background) element.inert = inert;
    document.body.style.overflow = overflow;
    document.removeEventListener('keydown', keydown, true);
  };
  modal.resume = () => {
    if (closed || !suspended) return;
    suspended = false; overlay.hidden = false;
    for (const [element] of background) if (element.isConnected) element.inert = true;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', keydown, true);
    (focusable()[0] || modal).focus();
  };
  const finishClose = () => {
    if (closed) return;
    closed = true; origin.closed = true;
    unregisterEscape();
    document.removeEventListener('keydown', keydown, true);
    overlay.remove();
    if (active === modal) {
      for (const [element, inert] of background) if (element.isConnected) element.inert = inert;
      document.body.style.overflow = overflow;
      active = connectedPrior(prior);
      if (active) {
        origins.get(active).overlay.inert = false;
        for (const [element] of origins.get(active)?.background ?? []) if (element.isConnected) element.inert = true;
        document.body.style.overflow = 'hidden';
      }
      if (previous?.isConnected && (!active || active.contains(previous))) previous.focus();
      else if (active) active.focus();
    }
    modal.dispatchEvent(new document.defaultView.Event('close'));
  };
  modal.close = (force = false) => {
    if (closed) return;
    if (force === true) return finishClose();
    if (closing) return closing;
    const pending = [];
    modal.dispatchEvent(new document.defaultView.CustomEvent('gravewright:sheet-flush', {
      detail: {waitUntil: promise => pending.push(Promise.resolve(promise))},
    }));
    if (!pending.length) return finishClose();
    closing = Promise.all(pending).then(finishClose).catch(error => {
      if (closed) return;
      const alert = modal.querySelector('.gw-module-root [role=status], [role=alert]');
      if (alert) { alert.hidden = false; if (!alert.textContent) alert.textContent = error.message; }
    }).finally(() => { closing = undefined; });
    return closing;
  };
  active = modal;
  overlay.append(modal);
  document.body.append(overlay);
  const unregisterEscape = registerEscapeClose(modal, () => { if (!suspended && canClose()) modal.close(); });
  for (const [element] of background) element.inert = true;
  document.body.style.overflow = 'hidden';
  document.addEventListener('keydown', keydown, true);
  (focusable()[0] || modal).focus();
  return modal;
}
