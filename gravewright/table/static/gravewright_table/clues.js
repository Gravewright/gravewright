import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { createProgressDetails, bindProgressDetailsName } from './progress-details.js';

const sameScene = (a, b) => (a ?? null) === (b ?? null);
const conflict = error => error?.code === 'conflict' || error?.status === 409;
const refused = error => ['conflict', 'permission_denied', 'invalid_data', 'not_found'].includes(error?.code)
  || error?.status >= 400 && error.status < 500 && ![408, 429].includes(error.status);

/** Read context and persisted scope are distinct; an editor retains its opening revision. */
export function clueConfigPayload(clue, values, sceneId) {
  return { ...(clue ? { id: clue.id, version: clue.version } : {}),
    name: values.name.trim(), segments: Number(values.segments), value: Number(values.value),
    color: values.color, visibility: values.visibility,
    content: values.content, gmNotes: values.gmNotes, pinned: values.pinned === true,
    scopeSceneId: values.sceneId || null, sceneId: sceneId || null, mapId: sceneId || null,
  };
}

/** Retain operation UUIDs only for retries of the same candidate after uncertain replies. */
export function createClueCommands({ api, signal, refresh, onChange = () => {} }) {
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
      const result = await api.clues[method](payload, { requestId: attempt.requestId, signal: requestSignal });
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
 * Shared table/management clue panel. Mounting performs no request; the owner
 * supplies feed projections with update(), or explicitly calls refresh().
 * No socket, board or timer is started. onChange receives one canonical current
 * projection after a successful mutation, allowing another panel/HUD to update.
 */
export function mountClues(root, { api, sceneId = () => null, scenes = () => [],
  t, pinnedOnly = false, onChange, onRender, signal: external, load = path => import(path) } = {}) {
  const document = root.ownerDocument, own = new AbortController();
  const signal = external ? AbortSignal.any([own.signal, external]) : own.signal;
  const translator = createTranslator(), text = t || (key => translator.t(key));
  const modals = new Set(), pendingProgress = new Set(), progressControls = new Map(), focusTargets = new Map();
  let rows = new AbortController(), read, sequence = 0, manualScene;
  let state = { clues: [], is_gm: false, sceneId: null }, editorOpening = false, errorText = '';
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
    errorText = text(conflict(error) ? 'This clue changed. Refresh and try again.' : error?.message || 'Could not save the clue.');
    render();
  };
  const accepts = next => alive() && next && Array.isArray(next.clues) && sameScene(next.sceneId, currentScene());
  function apply(next) {
    if (state.is_gm === true && next.is_gm !== true) for (const modal of modals) modal.close?.(true);
    state = next.is_gm === true ? next : { ...next, clues: next.clues
      .filter(clue => clue.discovered === true && clue.visibility === 'players' && clue.value === clue.segments)
      .map(({ gmNotes: _private, ...clue }) => ({ ...clue, canEdit: false, canConfigure: false })) };
    errorText = ''; render(); details.update(); return true;
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
    const promise = api.clues.state({ sceneId: context, mapId: context }, { signal: requestSignal }).then(value => {
      if (!alive() || token !== sequence || !sameScene(context, currentScene())) return replacement();
      if (!accepts(value)) return;
      apply(value); return state;
    }).catch(error => {
      if (requestSignal.aborted) return replacement();
      throw error;
    }).finally(() => { if (read?.token === token) read = undefined; });
    task.promise = promise; read = task; return promise;
  }
  const commands = createClueCommands({ api, signal, refresh, onChange });
  const details = createProgressDetails({ root, kind: 'clue', signal, text, load, refresh, state: () => state, sceneId: currentScene });
  async function openName(id) {
    const context = currentScene(); await refresh({ fresh: true });
    if (!alive() || context !== currentScene()) return;
    const clue = state.clues.find(row => row.id === id); if (!clue) return;
    return state.is_gm === true && clue.canConfigure === true ? openEditor(clue) : details.open(id, { fresh: false });
  }
  const contextPayload = clue => ({ id: clue.id, version: clue.version, sceneId: currentScene(), mapId: currentScene() });
  async function advance(clue, delta) {
    if (!alive() || state.is_gm !== true || clue.canEdit !== true || pendingProgress.has(clue.id)
      || clue.value + delta < 0 || clue.value + delta > clue.segments) return;
    pendingProgress.add(clue.id); progressControls.get(clue.id)?.();
    try { await commands.run('advance', { ...contextPayload(clue), delta }); }
    finally { pendingProgress.delete(clue.id); progressControls.get(clue.id)?.(); }
  }
  function action(label, name, work, { symbol, disabled = false, delta } = {}) {
    const button = node('button', 'clues__button', symbol || text(label));
    button.type = 'button'; button.dataset.clueAction = name; button.disabled = disabled;
    if (symbol) { button.setAttribute('aria-label', text(label)); button.title = text(label); }
    if (delta !== undefined) button.dataset.clueDelta = String(delta);
    button.addEventListener('click', async () => {
      if (!alive() || button.disabled) return;
      button.disabled = true; button.setAttribute('aria-busy', 'true');
      try { await work(); }
      catch (error) { report(error); }
      finally { if (alive()) { button.disabled = disabled; button.removeAttribute('aria-busy'); } }
    }, { signal: rows.signal });
    return button;
  }
  function progress(clue) {
    const meter = node('div', 'clues__progress');
    meter.setAttribute('role', 'progressbar');
    meter.setAttribute('aria-label', text('Discovery progress'));
    meter.setAttribute('aria-valuemin', '0'); meter.setAttribute('aria-valuemax', String(clue.segments));
    meter.setAttribute('aria-valuenow', String(clue.value)); meter.dataset.clueProgress = '';
    const color = /^#[a-f0-9]{6}$/i.test(clue.color) ? clue.color : '#c9a44c';
    meter.style.setProperty('--clue-color', color);
    for (let index = 0; index < clue.segments; index++) {
      const step = node('span', `clues__step${index < clue.value ? ' clues__step--filled' : ''}`);
      step.setAttribute('aria-hidden', 'true'); meter.append(step);
    }
    return meter;
  }
  function bindProgress(element, clue, buttons) {
    if (state.is_gm !== true || clue.canEdit !== true) return;
    element.setAttribute('role', 'slider'); element.setAttribute('tabindex', '0');
    const hint = text('Left-click to advance; right-click to reduce. Use the arrow keys to adjust progress.');
    element.setAttribute('aria-description', hint); element.setAttribute('title', hint);
    const adjust = delta => advance(clue, delta).catch(report);
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
      const pending = pendingProgress.has(clue.id);
      element.setAttribute('aria-disabled', String(pending));
      if (pending) element.setAttribute('aria-busy', 'true'); else element.removeAttribute('aria-busy');
      for (const button of buttons) button.disabled = pending
        || clue.value + Number(button.dataset.clueDelta) < 0
        || clue.value + Number(button.dataset.clueDelta) > clue.segments;
    };
    progressControls.set(clue.id, busy); focusTargets.set(`progress:${clue.id}`, element); busy();
  }
  function render() {
    if (!alive()) return;
    const focused = [...focusTargets].find(([, element]) => element === document.activeElement)?.[0];
    rows.abort(); rows = new AbortController(); progressControls.clear(); focusTargets.clear();
    root.classList.add('clues'); root.classList.toggle('clues--pinned', pinnedOnly);
    root.replaceChildren();
    const visible = pinnedOnly ? state.clues.filter(clue => clue.pinned) : state.clues;
    root.hidden = pinnedOnly && !visible.length;
    if (!pinnedOnly && state.is_gm === true) {
      const header = node('div', 'clues__toolbar');
      header.append(action('New clue', 'create', () => openEditor())); root.append(header);
    }
    if (errorText) { const error = node('p', 'clues__error', errorText); error.dataset.cluesError = ''; error.setAttribute('role', 'alert'); root.append(error); }
    if (!visible.length && !pinnedOnly) {
      const empty = node('p', 'clues__empty', text(state.is_gm ? 'No clues yet. Create one to begin.' : 'No clues visible.'));
      empty.dataset.cluesEmpty = ''; root.append(empty);
    }
    const list = node('div', 'clues__list');
    for (const clue of visible) {
      const card = node('article', 'clues__clue'); card.dataset.clueId = clue.id;
      const heading = node('strong', 'clues__name', clue.name); heading.dataset.clueName = ''; heading.setAttribute('translate', 'no');
      bindProgressDetailsName(heading, { id: clue.id, kind: 'clue', text, open: openName, report, signal: rows.signal });
      if (pinnedOnly) { heading.dataset.progressMoveHandle = ''; focusTargets.set(`move:${clue.id}`, heading); }
      else focusTargets.set(`details:${clue.id}`, heading);
      const value = node('output', 'clues__value', `${clue.value}/${clue.segments}`); value.dataset.clueValue = '';
      const meter = progress(clue); card.append(heading, meter); if (!pinnedOnly) card.append(value);
      if (!pinnedOnly) {
        const content = node('p', 'clues__content', clue.content); content.dataset.clueContent = ''; content.setAttribute('translate', 'no');
        card.append(content);
        if (state.is_gm === true && clue.gmNotes) {
          const notes = node('details', 'clues__notes'); notes.dataset.clueGmNotes = '';
          const body = node('p', 'clues__content', clue.gmNotes); body.setAttribute('translate', 'no');
          notes.append(node('summary', '', text('GM notes')), body); card.append(notes);
        }
      }
      const controls = node('div', 'clues__controls'); controls.setAttribute('role', 'group'); controls.setAttribute('aria-label', text('Clue controls'));
      const progressButtons = !pinnedOnly && state.is_gm === true && clue.canEdit === true ? [
        action('Reduce clue', 'advance', () => advance(clue, -1), { symbol: '−', delta: -1, disabled: clue.value <= 0 }),
        action('Advance clue', 'advance', () => advance(clue, 1), { symbol: '+', delta: 1, disabled: clue.value >= clue.segments }),
      ] : [];
      controls.append(...progressButtons); bindProgress(meter, clue, progressButtons);
      if (!pinnedOnly && state.is_gm === true && clue.canConfigure === true) controls.append(
        action('Reveal clue', 'reveal', () => commands.run('reveal', contextPayload(clue)), { disabled: clue.discovered && clue.visibility === 'players' }),
        action('Hide clue', 'hide', () => commands.run('hide', contextPayload(clue)), { disabled: clue.visibility === 'gm' }),
        action('Reset clue', 'reset', () => commands.run('reset', contextPayload(clue)), { disabled: clue.value === 0 }),
        action('Edit clue', 'edit', () => openEditor(clue)),
        action('Delete clue', 'delete', () => remove(clue)),
      );
      if (controls.children.length) card.append(controls);
      if (!pinnedOnly) card.append(node('small', 'clues__audience', text(clue.visibility === 'gm' ? 'GM only'
        : clue.discovered ? 'Discovered' : 'Hidden until discovered')));
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
      const modal = node('section', 'table-form-modal clues-editor'); modal.dataset.clueEditor = '';
      const abort = new AbortController(), modalSignal = AbortSignal.any([signal, abort.signal]);
      const form = node('form'), header = node('header'), titleNode = node('strong', '', text(title));
      titleNode.id = `clue-editor-${crypto.randomUUID()}`; modal.setAttribute('aria-labelledby', titleNode.id);
      const close = node('button', '', '×'); close.type = 'button'; close.dataset.close = '';
      close.setAttribute('aria-label', text('Close'));
      const body = node('div', 'table-form-modal__body'), fields = node('div', 'clues-editor__fields');
      const alert = node('p', 'clues__error'); alert.setAttribute('role', 'alert'); alert.hidden = true;
      const footer = node('footer'), cancel = node('button', '', text(save ? 'Cancel' : 'Close')), submit = node('button', '', save ? text(submitLabel) : '');
      cancel.type = 'button'; cancel.dataset.cancel = ''; submit.type = 'submit';
      submit.hidden = !save;
      header.append(titleNode, close); body.append(alert, fields); footer.append(cancel, submit); form.append(header, body, footer); modal.append(form);
      const controls = build(fields, modalSignal);
      let busy = false;
      close.addEventListener('click', () => { if (!busy) modal.close(); }, { signal: modalSignal });
      cancel.addEventListener('click', () => { if (!busy) modal.close(); }, { signal: modalSignal });
      form.addEventListener('submit', async event => {
        event.preventDefault(); if (!save || busy || !alive() || !form.reportValidity()) return;
        busy = true; alert.hidden = true;
        const locked = [close, cancel, submit, ...controls];
        locked.forEach(control => { control.disabled = true; }); modal.setAttribute('aria-busy', 'true');
        try { await save(controls, modalSignal); if (alive() && !modalSignal.aborted) modal.close(); }
        catch (error) {
          if (alive() && !modalSignal.aborted) {
            alert.textContent = text(conflict(error)
              ? 'This clue changed. Your draft is preserved. Close and reopen the editor to review the current version.'
              : error?.message || 'Could not save the clue.'); alert.hidden = false;
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
  function openEditor(clue) {
    const snapshot = clue ? { ...clue } : null;
    const editingContext = currentScene();
    const draft = { name: '', content: '', gmNotes: '', segments: 4, value: 0, color: '#c9a44c', visibility: 'players',
      pinned: false, sceneId: currentScene(), ...snapshot };
    const attemptKey = snapshot?.id || `create:${crypto.randomUUID()}`;
    return mountEditor(snapshot ? 'Edit clue' : 'New clue', async (controls, modalSignal) => {
      const values = Object.fromEntries(controls.map(control => [control.name, control.type === 'checkbox' ? control.checked : control.value]));
      await commands.run(snapshot ? 'update' : 'create', clueConfigPayload(snapshot, values, editingContext), attemptKey, modalSignal);
    }, (fields, modalSignal) => {
      const controls = [], field = (key, label, { type = 'text', options, value = draft[key] } = {}) => {
        const wrapper = node('label', type === 'checkbox' ? 'clues-editor__checkbox' : '');
        const input = node(options ? 'select' : type === 'textarea' ? 'textarea' : 'input'); input.name = key;
        if (options) for (const option of options) { const item = node('option', '', option.label); item.value = String(option.value); input.append(item); }
        else if (type !== 'textarea') input.type = type;
        if (type === 'checkbox') input.checked = Boolean(value); else input.value = String(value ?? '');
        wrapper.append(node('span', '', text(label)), input); fields.append(wrapper); controls.push(input); return input;
      };
      const name = field('name', 'Clue name'); name.required = true; name.maxLength = 120; name.setAttribute('translate', 'no');
      for (const [key, label] of [['content', 'Clue content'], ['gmNotes', 'GM notes']]) {
        const content = field(key, label, { type: 'textarea' }); content.maxLength = 4000; content.rows = 4; content.setAttribute('translate', 'no');
      }
      const segments = field('segments', 'Discovery steps', { type: 'number' }); segments.required = true; segments.min = '1'; segments.max = '24'; segments.step = '1';
      const value = field('value', 'Completed steps', { type: 'number' }); value.required = true; value.min = '0'; value.max = String(draft.segments); value.step = '1';
      const synchronize = () => { value.max = segments.value; if (Number(value.value) > Number(segments.value)) value.value = segments.value; };
      segments.addEventListener('input', synchronize, { signal: modalSignal });
      field('color', 'Clue color', { type: 'color' });
      field('visibility', 'Visibility', { options: [{ value: 'gm', label: text('GM only') }, { value: 'players', label: text('Reveal when discovered') }] });
      const available = (typeof scenes === 'function' ? scenes() : scenes) || [];
      const choices = [{ value: '', label: text('Campaign') }, ...available.map(scene => ({ value: scene.id, label: scene.name }))];
      if (draft.sceneId && !available.some(scene => scene.id === draft.sceneId)) choices.push({ value: draft.sceneId, label: text('Selected scene') });
      const scope = field('sceneId', 'Clue scope', { value: draft.sceneId || '', options: choices }); scope.setAttribute('translate', 'no');
      field('pinned', 'Pin on the table', { type: 'checkbox' });
      fields.append(node('p', 'clues-editor__hint', text('Players see the clue only when every step is complete and its visibility allows players. GM notes always stay private.')));
      return controls;
    }, 'Save changes', () => state.is_gm === true && (!snapshot || state.clues.some(row => row.id === snapshot.id && row.canConfigure === true)));
  }
  function remove(clue) {
    const snapshot = { ...clue };
    const payload = contextPayload(snapshot);
    return mountEditor('Delete clue', (_controls, modalSignal) => commands.run('delete', payload, snapshot.id, modalSignal), fields => {
      const name = node('strong', '', snapshot.name); name.setAttribute('translate', 'no');
      fields.append(name, node('p', '', text('Delete this clue?'))); return [];
    }, 'Delete clue');
  }
  const offLocale = translator.onChange(() => render());
  function destroy() {
    if (own.signal.aborted) return;
    own.abort(); rows.abort(); read?.controller.abort(); commands.destroy(); details.destroy(); offLocale();
    for (const modal of modals) modal.close?.(true);
    modals.clear(); pendingProgress.clear(); progressControls.clear(); focusTargets.clear(); root.replaceChildren();
  }
  if (signal.aborted) destroy();
  else signal.addEventListener('abort', () => { if (!own.signal.aborted) destroy(); }, { once: true });
  render();
  return { refresh, update, setScene(value) {
    manualScene = arguments.length ? value || null : undefined;
    read?.controller.abort(); read = undefined; ++sequence;
    state = { clues: [], is_gm: state.is_gm, sceneId: currentScene() }; details.update(); render(); return refresh();
  }, destroy };
}
