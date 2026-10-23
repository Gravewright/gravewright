import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { afterContentReady } from './content-state.js';
import { mountModal } from './modal.js';
import { mountMindmaps } from './mindmaps.js';

const workspace = document.querySelector('#table-workspace'), toggle = workspace?.querySelector('[data-mindmaps-open]');
if (toggle && workspace.dataset.management !== 'true') {
  const scope = new AbortController(), { signal } = scope, translator = createTranslator(), t = key => translator.t(key);
  const api = gravewright.forTable(workspace.dataset.tableId), host = document.createElement('div');
  host.className = 'mindmap-directory__body'; host.dataset.mindmapsRoot = '';
  let panel, pending, queued = false, timer;
  const sceneId = () => window.gravewrightMaps?.current?.id || null;
  const widget = mountMindmaps(host, { api, t, signal, sceneId,
    scenes: () => window.gravewrightMaps?.current ? [window.gravewrightMaps.current] : [], onChange: receive });
  function receive(value) {
    if (signal.aborted || !value || !Array.isArray(value.mindmaps)) return;
    widget.update(value); toggle.hidden = !value.canManage && !value.mindmaps.length;
  }
  function refresh() {
    if (signal.aborted) return Promise.resolve();
    if (pending) { queued = true; return pending; }
    pending = (async () => {
      do { queued = false; const value = await api.mindmaps.state({}, { signal }); if (!signal.aborted) receive(value); } while (queued && !signal.aborted);
    })().catch(error => {
      if (signal.aborted || error.name === 'AbortError') return;
      if ([401, 403, 404].includes(error.status)) { widget.update({ mindmaps: [], canManage: false, editors: [] }); toggle.hidden = true; }
      const alert = panel?.querySelector('[role=alert]'); if (alert) { alert.textContent = t(error.message); alert.hidden = false; }
    }).finally(() => { pending = undefined; }); return pending;
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(() => void refresh(), 150); }
  function showDirectory() {
    if (signal.aborted) return;
    if (panel?.isConnected) { panel.focus(); return; }
    const modal = document.createElement('section'); modal.className = 'table-modal-window mindmap-directory'; modal.dataset.mindmapDirectory = '';
    const header = document.createElement('header'), title = document.createElement('strong'), close = document.createElement('button');
    title.textContent = t('Mind maps'); title.id = `mindmaps-directory-${crypto.randomUUID()}`; modal.setAttribute('aria-labelledby', title.id);
    close.type = 'button'; close.textContent = '×'; close.setAttribute('aria-label', t('Close')); close.onclick = () => modal.close();
    const alert = document.createElement('p'); alert.className = 'mindmaps__error'; alert.setAttribute('role', 'alert'); alert.hidden = true;
    header.append(title, close); modal.append(header, alert, host); panel = modal;
    modal.addEventListener('close', () => { panel = undefined; toggle.setAttribute('aria-expanded', 'false'); }, { once: true });
    mountModal(modal); toggle.setAttribute('aria-expanded', 'true'); void refresh(); return modal;
  }
  const facade = { open: (id, nodeId) => widget.open(id, nodeId), showDirectory };
  window.gravewrightMindMaps = facade; window.gravewrightMindmaps = facade;
  toggle.addEventListener('click', showDirectory, { signal });
  window.addEventListener('gravewright:resources', ({ detail }) => {
    if (detail.module === 'mindmaps') { if (detail.unavailable) receive({ mindmaps: [], canManage: false }); else receive(detail.state); }
    else schedule();
  }, { signal });
  for (const event of ['gravewright:journals', 'gravewright:actors.state', 'gravewright:ownership-changed']) window.addEventListener(event, schedule, { signal });
  for (const event of ['gravewright:maps', 'gravewright:map-layers', 'gravewright:tokens', 'gravewright:module-scene']) window.addEventListener(event, schedule, { signal });
  window.addEventListener('gravewright:api-event', ({ detail }) => {
    if (!['table.presence', 'table.ping'].includes(detail?.type)) schedule();
  }, { signal });
  window.addEventListener('gravewright:connected', () => { window.gravewrightRealtime?.subscribeModule('mindmaps', null); void refresh(); }, { signal });
  const offLocale = translator.onChange(() => { toggle.setAttribute('aria-label', t('Mind maps')); toggle.title = t('Mind maps'); });
  function destroy() {
    if (signal.aborted) return;
    scope.abort(); clearTimeout(timer); widget.destroy(); panel?.close(true); offLocale(); host.remove();
    if (window.gravewrightMindMaps === facade) { delete window.gravewrightMindMaps; delete window.gravewrightMindmaps; }
  }
  window.addEventListener('gravewright:access-revoked', destroy, { signal });
  window.addEventListener('pagehide', destroy, { once: true });
  afterContentReady(() => { if (!signal.aborted) { window.gravewrightRealtime?.subscribeModule('mindmaps', null); void refresh(); } });
}
