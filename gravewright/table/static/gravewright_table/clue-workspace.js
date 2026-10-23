import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { afterContentReady } from './content-state.js';
import { mountModal } from './modal.js';
import { mountClues } from './clues.js';
import { mountProgressHudLayout } from './progress-hud-layout.js';

const workspace = document.querySelector('#table-workspace');
const toggle = workspace?.querySelector('[data-clues-open]');
if (toggle && workspace.dataset.management !== 'true') {
  const scope = new AbortController(), { signal } = scope;
  const api = gravewright.forTable(workspace.dataset.tableId);
  const translator = createTranslator(), t = key => translator.t(key);
  const sceneId = () => window.gravewrightMaps?.current?.id || null;
  const scenes = () => window.gravewrightMaps?.current ? [window.gravewrightMaps.current] : [];
  let panel, editor, latest, reading, again = false, feedEpoch = 0;
  const hud = document.createElement('aside');
  hud.className = 'clue-hud'; hud.dataset.clueHud = ''; hud.hidden = true;
  hud.setAttribute('aria-label', t('Pinned clues'));
  workspace.append(hud);

  function receive(state) {
    if (signal.aborted || !state || (state.sceneId ?? null) !== sceneId() || !Array.isArray(state.clues)) return;
    feedEpoch += 1;
    latest = state;
    toggle.hidden = !state.is_gm && !state.clues.length;
    hud.hidden = !state.clues.some(clue => clue.pinned);
    pinned.update(state); editor?.update(state);
  }
  const layout = mountProgressHudLayout(hud, { profileId: workspace.dataset.profileId,
    campaignId: workspace.dataset.tableId, kind: 'clue', t, signal });
  const pinned = mountClues(hud, { api, sceneId, scenes, pinnedOnly: true, t, signal,
    onChange: receive, onRender: () => layout.refresh() });
  function clear() {
    feedEpoch += 1;
    latest = undefined; hud.hidden = true;
    toggle.hidden = workspace.dataset.role !== 'gm';
    const empty = { clues: [], is_gm: workspace.dataset.role === 'gm', sceneId: sceneId() };
    pinned.update(empty); editor?.update(empty);
  }
  function refresh() {
    if (signal.aborted) return Promise.resolve();
    if (reading) { again = true; return reading; }
    let pendingEpoch = feedEpoch;
    reading = (async () => {
      do {
        again = false;
        const requested = sceneId(), epoch = feedEpoch;
        pendingEpoch = epoch;
        const value = await api.clues.state({ sceneId: requested }, { signal });
        if (signal.aborted) return;
        if (requested !== sceneId()) { again = true; continue; }
        if (epoch === feedEpoch) receive(value);
      } while (again);
    })().catch(error => {
      if (signal.aborted || pendingEpoch !== feedEpoch) return;
      clear();
      if (panel) { const alert = panel.querySelector('[data-clue-error]'); alert.textContent = t(error.message); alert.hidden = false; }
    }).finally(() => { reading = undefined; });
    return reading;
  }
  function subscribe() { window.gravewrightRealtime?.subscribeModule('clues', sceneId()); }
  function open() {
    if (signal.aborted) return;
    if (panel?.isConnected) { panel.focus(); return; }
    const modal = document.createElement('section');
    modal.className = 'table-modal-window clue-panel'; modal.dataset.cluePanel = '';
    modal.dataset.windowKey = 'campaign-clues'; modal.dataset.movable = '';
    const header = document.createElement('header'), title = document.createElement('strong'), close = document.createElement('button');
    header.dataset.moveHandle = ''; title.id = 'campaign-clue-title'; title.textContent = t('Clues');
    modal.setAttribute('aria-labelledby', title.id); close.type = 'button'; close.textContent = '×';
    close.setAttribute('aria-label', t('Close')); close.onclick = () => modal.close();
    const body = document.createElement('div'), error = document.createElement('p');
    body.className = 'clue-panel__body'; body.dataset.cluesRoot = '';
    error.dataset.clueError = ''; error.setAttribute('role', 'alert'); error.hidden = true;
    header.append(title, close); modal.append(header, error, body);
    panel = modal;
    editor = mountClues(body, { api, sceneId, scenes, t, signal, onChange: receive });
    if (latest) editor.update(latest);
    modal.addEventListener('close', () => { editor?.destroy(); editor = undefined; panel = undefined; toggle.setAttribute('aria-expanded', 'false'); }, { once: true });
    mountModal(modal);
    toggle.setAttribute('aria-expanded', 'true');
    subscribe(); void refresh();
  }
  toggle.addEventListener('click', open, { signal });
  window.addEventListener('gravewright:resources', ({ detail }) => {
    if (detail.module !== 'clues' || (detail.sceneId ?? null) !== sceneId()) return;
    if (detail.unavailable) { clear(); panel?.close(true); } else receive(detail.state);
  }, { signal });
  window.addEventListener('gravewright:module-scene', () => { clear(); subscribe(); void refresh(); }, { signal });
  window.addEventListener('gravewright:connected', () => { subscribe(); void refresh(); }, { signal });
  function dispose() {
    if (signal.aborted) return;
    scope.abort(); editor?.destroy(); panel?.close(true); pinned.destroy(); layout.destroy(); offLocale(); hud.remove(); latest = undefined;
    toggle.hidden = true;
  }
  const offLocale = translator.onChange(() => {
    hud.setAttribute('aria-label', t('Pinned clues'));
    const title = panel?.querySelector('#campaign-clue-title'); if (title) title.textContent = t('Clues');
    panel?.querySelector('header button')?.setAttribute('aria-label', t('Close'));
  });
  window.addEventListener('gravewright:access-revoked', dispose, { signal });
  window.addEventListener('pagehide', dispose, { once: true });
  afterContentReady(() => { if (!signal.aborted) { subscribe(); void refresh(); } });
}
