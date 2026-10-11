let active;

export function mountModal(modal, {canClose = () => true} = {}) {
  active?.close();
  const previous = document.activeElement;
  const overlay = document.createElement('div');
  overlay.className = 'ownership-modal-overlay';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.tabIndex = -1;
  const background = [...document.body.children].map(element => [element, element.inert]);
  const overflow = document.body.style.overflow;
  const focusable = () => [...modal.querySelectorAll('button, input, select, textarea, a[href], [tabindex]')]
    .filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length);
  const keydown = event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (canClose()) modal.close();
    } else if (event.key === 'Tab') {
      const elements = focusable(), first = elements[0] || modal, last = elements.at(-1) || modal;
      if (event.shiftKey && (document.activeElement === first || !modal.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !modal.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    }
  };
  let closed = false, suspended = false;
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
  modal.close = () => {
    if (closed) return;
    closed = true;
    document.removeEventListener('keydown', keydown, true);
    overlay.remove();
    for (const [element, inert] of background) element.inert = inert;
    document.body.style.overflow = overflow;
    if (active === modal) { active = undefined; if (previous?.isConnected) previous.focus(); }
    modal.dispatchEvent(new Event('close'));
  };
  active = modal;
  overlay.append(modal);
  document.body.append(overlay);
  for (const [element] of background) element.inert = true;
  document.body.style.overflow = 'hidden';
  document.addEventListener('keydown', keydown, true);
  (focusable()[0] || modal).focus();
  return modal;
}
