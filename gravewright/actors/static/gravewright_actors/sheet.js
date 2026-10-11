import { detachWindow } from '/static/gravewright_table/window-controls.js';

/** The host owns window controls; the selected system owns the whole body. */
export function openSheet(campaign, actor, token, gm, onClose = () => {}) {
  const el = document.getElementById('actor-sheet-window').content.firstElementChild.cloneNode(true);
  const actorId = typeof actor === 'string' ? actor : actor.id;
  const metadata = typeof actor === 'string' ? token : actor;
  el.dataset.actorId = actorId;
  el.dataset.actorType = metadata?.actorType || '';
  el.dataset.systemId = metadata?.systemId || document.querySelector('#table-workspace').dataset.systemId;
  el.dataset.canEdit = String(metadata?.canEdit ?? token?.canControl ?? gm);
  if (token) {
    el.classList.replace('actor-directory__sheet', 'token-sheet');
    el.dataset.tokenId = token.id;
    el.dataset.sceneId = token.mapId;
  }
  const content = el.querySelector('.actor-sheet__content'), root = el.querySelector('.actor-sheet__native');
  const heading = el.querySelector('.actor-directory__sheet-heading strong');
  const error = el.querySelector('.actor-sheet__error');
  const setTitle = name => { heading.textContent = name; el.setAttribute('aria-label', name); };
  setTitle(metadata?.name || 'Character sheet');
  el.querySelector('.actor-directory__sheet-heading small').textContent = token
    ? token.linkMode === 'snapshot' ? 'Independent copy' : 'Linked to actor'
    : metadata?.actorType || '';
  let provider, popup, closed = false, closing = false, generation = 0;
  async function lifecycle(name) {
    const tasks = [];
    el.dispatchEvent(new CustomEvent(name, { detail: { waitUntil: task => tasks.push(task) } }));
    await Promise.all(tasks);
  }
  const report = failure => { error.textContent = failure.message; error.hidden = false; };
  // Called by the surface resolver after it has chosen a complete sheet.
  content.setDefaultVisible = async visible => {
    const current = ++generation;
    if (closed) return;
    root.hidden = !visible;
    if (!visible) {
      const previous = provider;
      try { if (previous?.dirty) await previous.flush(); }
      catch (failure) { root.hidden = false; report(failure); throw failure; }
      if (closed || current !== generation) return;
      provider = undefined;
      previous?.destroy();
      root.replaceChildren();
      return;
    }
    if (provider) return;
    if (!el.dataset.sheetProvider) {
      root.textContent = 'Character sheet unavailable.';
      return;
    }
    try {
      const implementation = await import(el.dataset.sheetProvider);
      if (closed || current !== generation) return;
      provider = implementation.mountSheet({ root, window: el, campaign, actorId, token, gm, setTitle, lifecycle });
    } catch (failure) { if (!closed && current === generation) report(failure); }
  };
  async function close(force = false) {
    if (closed || closing && !force) return false;
    closing = true;
    try {
      if (!force) { await lifecycle('gravewright:sheet-flush'); await provider?.flush(); }
      if (closed) return true;
      closed = true;
      ++generation;
      provider?.destroy();
      popup?.close();
      el.remove();
      window.removeEventListener('gravewright:access-revoked', revoke);
      onClose();
      return true;
    } catch (failure) { report(failure); return false; }
    finally { closing = false; }
  }
  const revoke = () => void close(true);
  window.addEventListener('gravewright:access-revoked', revoke);
  el.querySelector('.gw-window__controls').onclick = event => {
    const action = event.target.closest('[data-window]')?.dataset.window;
    if (action === 'close') void close();
    if (action === 'detach') popup = detachWindow(el, `actor-${actorId}${token ? '-' + token.id : ''}`, heading.textContent, { width: 1000, height: 800 });
    if (action === 'minimize') {
      el.classList.toggle('gw-window--minimized');
      el.querySelector('.gw-window__body').hidden = el.classList.contains('gw-window--minimized');
    }
  };
  document.body.append(el);
  // Bundled sheets can open immediately without waiting for unrelated content
  // and marketplace discovery. External systems never have this provider.
  if (el.dataset.sheetProvider) void content.setDefaultVisible(true);
  return { element: el, close, get dirty() { return !!provider?.dirty; } };
}
