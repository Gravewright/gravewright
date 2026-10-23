import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { createProgressDetails, bindProgressDetailsName } from './progress-details.js';

const SVG = 'http://www.w3.org/2000/svg';
const PRESETS = [4, 6, 8, 10, 12];
const sameScene = (a, b) => (a ?? null) === (b ?? null);
const conflict = error => error?.code === 'conflict' || error?.status === 409;
const refused = error => ['conflict', 'permission_denied', 'invalid_data', 'not_found'].includes(error?.code)
  || error?.status >= 400 && error.status < 500 && ![408, 429].includes(error.status);

/** Original annular SVG sectors, clockwise from twelve o'clock, bounded to 2–24. */
export function clockSectors(segments) {
  if (!Number.isInteger(segments) || segments < 2 || segments > 24) return [];
  const point = (radius, angle) => [64 + radius * Math.cos(angle), 64 + radius * Math.sin(angle)]
    .map(number => Number(number.toFixed(4))).join(' ');
  return Array.from({ length: segments }, (_, index) => {
    const size = Math.PI * 2 / segments, gap = Math.min(.035, size * .12);
    const start = index * size - Math.PI / 2 + gap, end = (index + 1) * size - Math.PI / 2 - gap;
    return `M ${point(55, start)} A 55 55 0 0 1 ${point(55, end)} L ${point(32, end)} A 32 32 0 0 0 ${point(32, start)} Z`;
  });
}

/** Read context and persisted scope are distinct; an editor retains its opening revision. */
export function clockConfigPayload(clock, values, sceneId) {
  return { ...(clock ? { id: clock.id, version: clock.version } : {}),
    name: values.name.trim(), description: values.description ?? '', segments: Number(values.segments), value: Number(values.value),
    color: values.color, visibility: values.visibility,
    playersCanEdit: values.playersCanEdit === true, pinned: values.pinned === true,
    scopeSceneId: values.sceneId || null, sceneId: sceneId || null, mapId: sceneId || null,
  };
}

/** Retain operation UUIDs only for retries of the same candidate after uncertain replies. */
export function createClockCommands({ api, signal, refresh, onChange = () => {} }) {
  const attempts = new Map();
  return { async run(method, payload, key = payload.id || 'create', ownerSignal) {
    const requestSignal = ownerSignal ? AbortSignal.any([signal, ownerSignal]) : signal;
    if (requestSignal.aborted) return;
    const fingerprint = JSON.stringify([method, payload]);
    let attempt = attempts.get(key);
    if (attempt?.fingerprint !== fingerprint) {
      attempt = { fingerprint, requestId: crypto.randomUUID() }; attempts.set(key, attempt);
    }
    try {
      const result = await api.clocks[method](payload, { requestId: attempt.requestId, signal: requestSignal });
      if (requestSignal.aborted) return;
      const state = await refresh({ fresh: true });
      if (requestSignal.aborted) return;
      if (state) await onChange(state);
      if (attempts.get(key) === attempt) attempts.delete(key);
      return result;
    } catch (error) {
      if (refused(error) && attempts.get(key) === attempt) attempts.delete(key);
      if (conflict(error) && !requestSignal.aborted) await refresh({ fresh: true }).catch(() => {});
      throw error;
    }
  }, destroy() { attempts.clear(); } };
}

/**
 * Shared table/management clock panel. Mounting performs no request; the owner
 * supplies feed projections with update(), or explicitly calls refresh().
 * No socket, board or timer is started. onChange receives one canonical current
 * projection after a successful mutation, allowing another panel/HUD to update.
 */
export function mountClocks(root, { api, sceneId = () => null, scenes = () => [],
  t, pinnedOnly = false, onChange, onRender, signal: external, load = path => import(path) } = {}) {
  const document = root.ownerDocument, own = new AbortController();
  const signal = external ? AbortSignal.any([own.signal, external]) : own.signal;
  const translator = createTranslator(), text = t || (key => translator.t(key));
  const modals = new Set(), pendingProgress = new Set(), progressControls = new Map(), focusTargets = new Map();
  let rows = new AbortController(), read, sequence = 0, manualScene;
  let state = { clocks: [], is_gm: false, sceneId: null }, editorOpening = false, errorText = '';
  const currentScene = () => (manualScene !== undefined ? manualScene : typeof sceneId === 'function' ? sceneId() : sceneId) || null;
  const alive = () => !signal.aborted;
  const node = (tag, className, value) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = value;
    return element;
  };
  const report = error => {
    if (!alive() || error?.name === 'AbortError' || error?.code === 'cancelled') return;
    errorText = text(conflict(error) ? 'This clock changed. Refresh and try again.' : error?.message || 'Could not save the clock.');
    render();
  };
  const accepts = next => alive() && next && Array.isArray(next.clocks) && sameScene(next.sceneId, currentScene());
  function apply(next) {
    if (state.is_gm === true && next.is_gm !== true) for (const modal of modals) modal.close?.(true);
    state = next; errorText = ''; render(); details.update(); return true;
  }
  function update(next) {
    if (!accepts(next)) return false;
    if (read) { read.superseded = true; read.controller.abort(); read = undefined; }
    ++sequence;
    return apply(next);
  }
  function refresh({ fresh = false } = {}) {
    if (!alive()) return Promise.resolve();
    const context = currentScene();
    if (!fresh && read && sameScene(read.sceneId, context)) return read.promise;
    read?.controller.abort();
    const controller = new AbortController(), token = ++sequence;
    const task = { sceneId: context, controller, token, superseded: false };
    const requestSignal = AbortSignal.any([signal, controller.signal]);
    const replacement = () => {
      if (!alive() || !sameScene(context, currentScene())) return;
      if (task.superseded) return state;
      if (read && read.token !== token && sameScene(read.sceneId, context)) return read.promise;
    };
    const promise = api.clocks.state({ sceneId: context, mapId: context }, { signal: requestSignal }).then(value => {
      if (!alive() || token !== sequence || !sameScene(context, currentScene())) return replacement();
      if (!accepts(value)) return;
      apply(value); return value;
    }).catch(error => {
      if (requestSignal.aborted) return replacement();
      throw error;
    }).finally(() => { if (read?.token === token) read = undefined; });
    task.promise = promise; read = task; return promise;
  }
  const commands = createClockCommands({ api, signal, refresh, onChange });
  const details = createProgressDetails({ root, kind: 'clock', signal, text, load, refresh, state: () => state, sceneId: currentScene });
  async function openName(id) {
    const context = currentScene(); await refresh({ fresh: true });
    if (!alive() || context !== currentScene()) return;
    const clock = state.clocks.find(row => row.id === id); if (!clock) return;
    return state.is_gm === true && clock.canConfigure === true ? openEditor(clock) : details.open(id, { fresh: false });
  }
  const contextPayload = clock => ({ id: clock.id, version: clock.version, sceneId: currentScene(), mapId: currentScene() });
  async function advance(clock, delta) {
    if (!alive() || clock.canEdit !== true || pendingProgress.has(clock.id)
      || clock.value + delta < 0 || clock.value + delta > clock.segments) return;
    pendingProgress.add(clock.id); progressControls.get(clock.id)?.();
    try { await commands.run('advance', { ...contextPayload(clock), delta }); }
    finally { pendingProgress.delete(clock.id); progressControls.get(clock.id)?.(); }
  }
  function action(label, name, work, { symbol, disabled = false, delta } = {}) {
    const button = node('button', 'clocks__button', symbol || text(label));
    button.type = 'button'; button.dataset.clockAction = name; button.disabled = disabled;
    if (symbol) { button.setAttribute('aria-label', text(label)); button.title = text(label); }
    if (delta !== undefined) button.dataset.clockDelta = String(delta);
    button.addEventListener('click', async () => {
      if (!alive() || button.disabled) return;
      button.disabled = true; button.setAttribute('aria-busy', 'true');
      try { await work(); }
      catch (error) { report(error); }
      finally { if (alive()) { button.disabled = disabled; button.removeAttribute('aria-busy'); } }
    }, { signal: rows.signal });
    return button;
  }
  function face(clock) {
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('viewBox', '0 0 128 128'); svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `${clock.name}: ${clock.value}/${clock.segments}`);
    svg.dataset.clockFace = '';
    const color = /^#[a-f0-9]{6}$/i.test(clock.color) ? clock.color : '#c9a44c';
    svg.style.setProperty('--clock-color', color);
    for (const [index, path] of clockSectors(clock.segments).entries()) {
      const sector = document.createElementNS(SVG, 'path'); sector.setAttribute('d', path);
      sector.setAttribute('class', `clocks__sector${index < clock.value ? ' clocks__sector--filled' : ''}`);
      svg.append(sector);
    }
    const count = document.createElementNS(SVG, 'text'); count.setAttribute('x', '64'); count.setAttribute('y', '71');
    count.setAttribute('class', 'clocks__number'); count.textContent = String(clock.value); svg.append(count);
    return svg;
  }
  function bindProgress(element, clock, buttons) {
    if (clock.canEdit !== true) return;
    element.setAttribute('role', 'slider'); element.setAttribute('tabindex', '0');
    element.setAttribute('aria-valuemin', '0'); element.setAttribute('aria-valuemax', String(clock.segments));
    element.setAttribute('aria-valuenow', String(clock.value));
    const hint = text('Left-click to advance; right-click to reduce. Use the arrow keys to adjust progress.');
    element.setAttribute('aria-description', hint); element.setAttribute('title', hint);
    const adjust = delta => advance(clock, delta).catch(report);
    element.addEventListener('click', event => {
      if (event.button !== undefined && event.button !== 0) return;
      event.stopPropagation(); adjust(1);
    }, { signal: rows.signal });
    element.addEventListener('contextmenu', event => {
      event.preventDefault(); event.stopPropagation(); adjust(-1);
    }, { signal: rows.signal });
    element.addEventListener('keydown', event => {
      const delta = ['ArrowRight', 'ArrowUp', '+', '=', 'Enter', ' '].includes(event.key) ? 1
        : ['ArrowLeft', 'ArrowDown', '-'].includes(event.key) ? -1 : 0;
      if (!delta || event.ctrlKey || event.metaKey || event.altKey) return;
      event.preventDefault(); event.stopPropagation(); if (!event.repeat) adjust(delta);
    }, { signal: rows.signal });
    const busy = () => {
      const pending = pendingProgress.has(clock.id);
      element.setAttribute('aria-disabled', String(pending));
      if (pending) element.setAttribute('aria-busy', 'true'); else element.removeAttribute('aria-busy');
      for (const button of buttons) button.disabled = pending
        || clock.value + Number(button.dataset.clockDelta) < 0
        || clock.value + Number(button.dataset.clockDelta) > clock.segments;
    };
    progressControls.set(clock.id, busy); focusTargets.set(`progress:${clock.id}`, element); busy();
  }
  function render() {
    if (!alive()) return;
    const focused = [...focusTargets].find(([, element]) => element === document.activeElement)?.[0];
    rows.abort(); rows = new AbortController(); progressControls.clear(); focusTargets.clear();
    root.classList.add('clocks'); root.classList.toggle('clocks--pinned', pinnedOnly);
    root.replaceChildren();
    const visible = pinnedOnly ? state.clocks.filter(clock => clock.pinned) : state.clocks;
    root.hidden = pinnedOnly && !visible.length;
    if (!pinnedOnly && state.is_gm === true) {
      const header = node('div', 'clocks__toolbar');
      header.append(action('New clock', 'create', () => openEditor())); root.append(header);
    }
    if (errorText) { const error = node('p', 'clocks__error', errorText); error.dataset.clocksError = ''; error.setAttribute('role', 'alert'); root.append(error); }
    if (!visible.length && !pinnedOnly) {
      const empty = node('p', 'clocks__empty', text(state.is_gm ? 'No clocks yet. Create one to begin.' : 'No clocks visible.'));
      empty.dataset.clocksEmpty = ''; root.append(empty);
    }
    const list = node('div', 'clocks__list');
    for (const clock of visible) {
      const card = node('article', 'clocks__clock'); card.dataset.clockId = clock.id;
      const heading = node('strong', 'clocks__name', clock.name); heading.dataset.clockName = ''; heading.setAttribute('translate', 'no');
      bindProgressDetailsName(heading, { id: clock.id, kind: 'clock', text, open: openName, report, signal: rows.signal });
      if (pinnedOnly) { heading.dataset.progressMoveHandle = ''; focusTargets.set(`move:${clock.id}`, heading); }
      else focusTargets.set(`details:${clock.id}`, heading);
      const value = node('output', 'clocks__value', `${clock.value}/${clock.segments}`); value.dataset.clockValue = '';
      const progress = face(clock); card.append(heading, progress); if (!pinnedOnly) card.append(value);
      const controls = node('div', 'clocks__controls'); controls.setAttribute('role', 'group'); controls.setAttribute('aria-label', text('Clock controls'));
      const progressButtons = !pinnedOnly && clock.canEdit === true ? [
        action('Reduce clock', 'advance', () => advance(clock, -1), { symbol: '−', delta: -1, disabled: clock.value <= 0 }),
        action('Advance clock', 'advance', () => advance(clock, 1), { symbol: '+', delta: 1, disabled: clock.value >= clock.segments }),
      ] : [];
      controls.append(...progressButtons); bindProgress(progress, clock, progressButtons);
      if (!pinnedOnly && clock.canConfigure === true) controls.append(
        action('Reset clock', 'reset', () => commands.run('reset', contextPayload(clock)), { disabled: clock.value === 0 }),
        action('Edit clock', 'edit', () => openEditor(clock)),
        action('Delete clock', 'delete', () => remove(clock)),
      );
      if (controls.children.length) card.append(controls);
      if (!pinnedOnly) card.append(node('small', 'clocks__audience', text(clock.visibility === 'gm' ? 'GM only' : 'Visible to players')));
      list.append(card);
    }
    root.append(list);
    onRender?.(root);
    if (focused && alive() && (!document.activeElement || document.activeElement === document.body
      || document.activeElement === document.documentElement)) focusTargets.get(focused)?.focus({ preventScroll: true });
  }
  async function mountEditor(title, save, build, submitLabel, authorized = () => state.is_gm === true) {
    if (editorOpening || !alive()) return;
    for (const modal of modals) if (modal.isConnected) { modal.focus(); return; }
    editorOpening = true;
    try {
      const { mountModal } = await load('/static/gravewright_table/modal.js');
      if (!alive() || !authorized()) return;
      const modal = node('section', 'table-form-modal clocks-editor'); modal.dataset.clockEditor = '';
      const abort = new AbortController(), modalSignal = AbortSignal.any([signal, abort.signal]);
      const form = node('form'), header = node('header'), titleNode = node('strong', '', text(title));
      titleNode.id = `clock-editor-${crypto.randomUUID()}`; modal.setAttribute('aria-labelledby', titleNode.id);
      const close = node('button', '', '×'); close.type = 'button'; close.dataset.close = '';
      close.setAttribute('aria-label', text('Close'));
      const body = node('div', 'table-form-modal__body'), fields = node('div', 'clocks-editor__fields');
      const alert = node('p', 'clocks__error'); alert.setAttribute('role', 'alert'); alert.hidden = true;
      const footer = node('footer'), cancel = node('button', '', text('Cancel')), submit = node('button', '', text(submitLabel));
      cancel.type = 'button'; cancel.dataset.cancel = ''; submit.type = 'submit';
      header.append(titleNode, close); body.append(alert, fields); footer.append(cancel, submit); form.append(header, body, footer); modal.append(form);
      const controls = build(fields, modalSignal);
      let busy = false;
      close.addEventListener('click', () => { if (!busy) modal.close(); }, { signal: modalSignal });
      cancel.addEventListener('click', () => { if (!busy) modal.close(); }, { signal: modalSignal });
      form.addEventListener('submit', async event => {
        event.preventDefault(); if (busy || !alive() || !form.reportValidity()) return;
        busy = true; alert.hidden = true;
        const locked = [close, cancel, submit, ...controls];
        locked.forEach(control => { control.disabled = true; }); modal.setAttribute('aria-busy', 'true');
        try { await save(controls, modalSignal); if (alive() && !modalSignal.aborted) modal.close(); }
        catch (error) {
          if (alive() && !modalSignal.aborted) {
            alert.textContent = text(conflict(error)
              ? 'This clock changed. Your draft is preserved. Close and reopen the editor to review the current version.'
              : error?.message || 'Could not save the clock.'); alert.hidden = false;
          }
        } finally {
          busy = false; locked.forEach(control => { control.disabled = false; }); modal.removeAttribute('aria-busy');
        }
      }, { signal: modalSignal });
      modal.addEventListener('close', () => { abort.abort(); modals.delete(modal); }, { once: true });
      modals.add(modal); mountModal(modal, { nested: true, canClose: () => !busy });
      return modal;
    } finally { editorOpening = false; }
  }
  function openEditor(clock) {
    const snapshot = clock ? { ...clock } : null;
    const editingContext = currentScene();
    const draft = { name: '', description: '', segments: 4, value: 0, color: '#c9a44c', visibility: 'gm',
      playersCanEdit: false, pinned: false, sceneId: currentScene(), ...snapshot };
    const attemptKey = snapshot?.id || `create:${crypto.randomUUID()}`;
    return mountEditor(snapshot ? 'Edit clock' : 'New clock', async (controls, modalSignal) => {
      const values = Object.fromEntries(controls.map(control => [control.name, control.type === 'checkbox' ? control.checked : control.value]));
      await commands.run(snapshot ? 'update' : 'create', clockConfigPayload(snapshot, values, editingContext), attemptKey, modalSignal);
    }, (fields, modalSignal) => {
      const controls = [], field = (key, label, { type = 'text', options, value = draft[key] } = {}) => {
        const wrapper = node('label', type === 'checkbox' ? 'clocks-editor__checkbox' : '');
        const input = node(options ? 'select' : type === 'textarea' ? 'textarea' : 'input'); input.name = key;
        if (options) for (const option of options) { const item = node('option', '', option.label); item.value = String(option.value); input.append(item); }
        else if (type !== 'textarea') input.type = type;
        if (type === 'checkbox') input.checked = Boolean(value); else input.value = String(value ?? '');
        wrapper.append(node('span', '', text(label)), input); fields.append(wrapper); controls.push(input); return input;
      };
      const name = field('name', 'Clock name'); name.required = true; name.maxLength = 120; name.setAttribute('translate', 'no');
      const description = field('description', 'Clock description', { type: 'textarea' }); description.rows = 4; description.maxLength = 4000; description.setAttribute('translate', 'no');
      const preset = field('preset', 'Clock preset', { value: PRESETS.includes(draft.segments) ? draft.segments : 'custom',
        options: [...PRESETS.map(value => ({ value, label: String(value) })), { value: 'custom', label: text('Custom') }] });
      const segments = field('segments', 'Segments', { type: 'number' }); segments.required = true; segments.min = '2'; segments.max = '24'; segments.step = '1';
      const value = field('value', 'Filled segments', { type: 'number' }); value.required = true; value.min = '0'; value.max = String(draft.segments); value.step = '1';
      const synchronize = () => { value.max = segments.value; if (Number(value.value) > Number(segments.value)) value.value = segments.value; };
      preset.addEventListener('change', () => { if (preset.value !== 'custom') { segments.value = preset.value; synchronize(); } }, { signal: modalSignal });
      segments.addEventListener('input', () => { preset.value = PRESETS.includes(Number(segments.value)) ? segments.value : 'custom'; synchronize(); }, { signal: modalSignal });
      field('color', 'Clock color', { type: 'color' });
      field('visibility', 'Visibility', { options: [{ value: 'gm', label: text('GM only') }, { value: 'players', label: text('Visible to players') }] });
      const available = (typeof scenes === 'function' ? scenes() : scenes) || [];
      const choices = [{ value: '', label: text('Campaign') }, ...available.map(scene => ({ value: scene.id, label: scene.name }))];
      if (draft.sceneId && !available.some(scene => scene.id === draft.sceneId)) choices.push({ value: draft.sceneId, label: text('Selected scene') });
      const scope = field('sceneId', 'Clock scope', { value: draft.sceneId || '', options: choices }); scope.setAttribute('translate', 'no');
      field('playersCanEdit', 'Players can advance this clock', { type: 'checkbox' });
      field('pinned', 'Pin on the table', { type: 'checkbox' });
      return controls;
    }, 'Save changes', () => state.is_gm === true && (!snapshot || state.clocks.some(row => row.id === snapshot.id && row.canConfigure === true)));
  }
  function remove(clock) {
    const snapshot = { ...clock };
    const payload = contextPayload(snapshot);
    return mountEditor('Delete clock', (_controls, modalSignal) => commands.run('delete', payload, snapshot.id, modalSignal), fields => {
      const name = node('strong', '', snapshot.name); name.setAttribute('translate', 'no');
      fields.append(name, node('p', '', text('Delete this clock?'))); return [];
    }, 'Delete clock');
  }
  const offLocale = translator.onChange(() => render());
  function destroy() {
    if (own.signal.aborted) return;
    own.abort(); rows.abort(); read?.controller.abort(); commands.destroy(); details.destroy(); offLocale();
    for (const modal of modals) modal.close?.(true);
    modals.clear(); pendingProgress.clear(); progressControls.clear(); focusTargets.clear(); root.replaceChildren();
  }
  signal.addEventListener('abort', () => { if (!own.signal.aborted) destroy(); }, { once: true });
  render();
  return { refresh, update, setScene(value) {
    manualScene = arguments.length ? value || null : undefined;
    read?.controller.abort(); read = undefined; ++sequence;
    state = { clocks: [], is_gm: state.is_gm, sceneId: currentScene() }; details.update(); render(); return refresh();
  }, destroy };
}
