const detachedWindows = new WeakMap();

export function openDetachedWindow({url = 'about:blank', width = 420, height = 754, source = window} = {}) {
  const left = Math.round(source.screenX + Math.max(0, (source.innerWidth - width) / 2));
  const top = Math.round(source.screenY + Math.max(0, (source.innerHeight - height) / 2));
  const features = `popup=yes,toolbar=no,location=no,menubar=no,status=no,scrollbars=yes,resizable=yes,width=${width},height=${height},left=${left},top=${top}`;
  return source.open(url, '_blank', features);
}

export function restoreWindow(element) {
  element.classList.remove('game-panel--minimized', 'journal-window--minimized', 'gw-window--minimized');
  element.removeAttribute('data-window-minimized');
  const body = element.querySelector('.gw-window__body');
  if (body) body.hidden = false;
}

export function detachWindow(element, id, title, {width = 420, height = 754} = {}) {
  const existing = detachedWindows.get(element);
  if (existing && !existing.closed) { existing.focus(); return existing; }
  const source = element.ownerDocument;
  if (source !== document) {
    source.defaultView.focus();
    return source.defaultView;
  }
  const child = openDetachedWindow({source:source.defaultView, width, height});
  const error = element.querySelector('[data-window-error]');
  error?.remove();
  if (!child) {
    const message = source.createElement('p');
    message.dataset.windowError = '';
    message.setAttribute('role', 'alert');
    message.textContent = source.documentElement.lang.toLowerCase().startsWith('pt')
      ? 'Não foi possível abrir a janela. Permita pop-ups para este site e tente novamente.'
      : 'The window could not open. Allow pop-ups for this site and try again.';
    element.append(message);
    return;
  }
  detachedWindows.set(element, child);
  child.name = `gravewright-${id}-${crypto.randomUUID()}`;
  const target = child.document;
  target.title = title;
  target.documentElement.lang = source.documentElement.lang;
  target.documentElement.dataset.renderProfile = source.documentElement.dataset.renderProfile || 'performance';
  for (const style of source.querySelectorAll('style,link[rel=stylesheet]'))
    target.head.append(style.cloneNode(true));
  target.body.className = 'game-table game-detached';
  const marker = source.createComment('detached-window');
  restoreWindow(element);
  const detachedClass = element.classList.contains('journal-window') ? 'journal-window--detached' : element.classList.contains('gw-window') ? 'gw-window--detached' : element.classList.contains('dice-tray') ? 'dice-tray--detached' : 'game-panel--detached';
  element.classList.add(detachedClass);
  element.replaceWith(marker);
  target.body.append(element);
  let returned = false;
  const close = event => {
    if (event.target.closest('[data-map-panel=close],[data-actor-panel=close],[data-journal-directory=close],[data-visibility-action=close]'))
      source.defaultView.setTimeout(() => child.close(), 0);
  };
  element.addEventListener('click', close);
  const restore = () => {
    if (returned) return;
    returned = true;
    clearInterval(timer);
    detachedWindows.delete(element);
    element.removeEventListener('click', close);
    element.classList.remove(detachedClass);
    if (marker.isConnected) {
      if (element.parentNode) marker.replaceWith(element);
      else marker.remove();
    }
  };
  const timer = setInterval(() => { if (child.closed) restore(); }, 300);
  child.addEventListener('pagehide', restore, {once: true});
  child.focus();
  return child;
}
