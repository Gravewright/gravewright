import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { mountModal } from './modal.js';
import { newMindmapDocument, visibleMindmapNodes, addMindmapNode, removeMindmapNode, reparentMindmapNode,
  createMindmapHistory, fitMindmap, zoomMindmap, createMindmapCommands } from './mindmap-model.js';
import { pickResourceLink, openResourceLink, resourceLabel } from './resource-links.js';

const SVG = 'http://www.w3.org/2000/svg';
const conflict = error => error?.status === 409 || error?.code === 'conflict';

/** Shared native directory. Its host owns realtime/polling and scene context. */
export function mountMindmaps(root, { api, t, sceneId = () => null, scenes = () => [], onChange,
  signal: external } = {}) {
  const document = root.ownerDocument, own = new AbortController();
  const signal = external ? AbortSignal.any([own.signal, external]) : own.signal;
  const translator = createTranslator(), text = t || (key => translator.t(key));
  const commands = createMindmapCommands({ api, signal }), editors = new Map(), dialogs = new Set();
  let state = { mindmaps: [], canManage: false, editors: [] }, sequence = 0, rowScope = new AbortController();
  let errorText = '', opening = new Map();
  const alive = () => !signal.aborted;
  const node = (tag, className, value) => {
    const element = document.createElement(tag); if (className) element.className = className;
    if (value !== undefined) element.textContent = value; return element;
  };
  const authored = (tag, className, value) => { const element = node(tag, className, value); element.setAttribute('translate', 'no'); return element; };
  const report = error => {
    if (!alive() || error?.name === 'AbortError') return;
    errorText = text(error?.message || 'Could not load mind maps.'); render();
  };
  function button(label, action, hostSignal = signal, className = '') {
    const control = node('button', className, text(label)); control.type = 'button';
    control.addEventListener('click', () => { if (!control.disabled) Promise.resolve().then(action).catch(report); }, { signal: hostSignal }); return control;
  }
  function update(next) {
    if (!alive() || !next || !Array.isArray(next.mindmaps)) return false;
    ++sequence; state = next; errorText = ''; render();
    for (const dialog of dialogs) {
      const id = dialog.dataset.mindmapSettingsId;
      if (id !== undefined && (!state.canManage || id && !state.mindmaps.some(row => row.id === id && row.canConfigure))) dialog.close?.(true);
    }
    for (const [id, editor] of editors) {
      const row = state.mindmaps.find(item => item.id === id);
      if (!row) editor.destroy(); else editor.receive(row);
    }
    return true;
  }
  async function refresh() {
    const token = ++sequence, value = await api.mindmaps.state({}, { signal });
    if (!alive()) return;
    if (token === sequence) { update(value); await onChange?.(value); }
    return state;
  }
  async function mutate(method, payload) {
    const result = await commands.run(method, payload); await refresh(); commands.acknowledge(payload.id); return result;
  }
  function form(title, build, save, submitLabel = 'Save changes', ownerSignal = signal) {
    const abort = new AbortController(), modalSignal = AbortSignal.any([signal, ownerSignal, abort.signal]);
    const modal = node('section', 'table-form-modal mindmap-form'), content = node('form');
    const heading = node('strong', '', text(title)), header = node('header'), close = node('button', '', '×');
    heading.id = `mindmap-form-${crypto.randomUUID()}`; modal.setAttribute('aria-labelledby', heading.id);
    close.type = 'button'; close.setAttribute('aria-label', text('Close'));
    const body = node('div', 'table-form-modal__body'), alert = node('p', 'mindmaps__error'), fields = node('div', 'mindmap-form__fields');
    alert.setAttribute('role', 'alert'); alert.hidden = true;
    const footer = node('footer'), cancel = node('button', '', text('Cancel')), submit = node('button', '', text(submitLabel));
    cancel.type = 'button'; submit.type = 'submit';
    header.append(heading, close); body.append(alert, fields); footer.append(cancel, submit); content.append(header, body, footer); modal.append(content);
    const controls = build(fields, modalSignal) || []; let busy = false;
    close.addEventListener('click', () => { if (!busy) modal.close(); }, { signal: modalSignal });
    cancel.addEventListener('click', () => { if (!busy) modal.close(); }, { signal: modalSignal });
    content.addEventListener('submit', async event => {
      event.preventDefault(); if (busy || !content.reportValidity()) return;
      busy = true; alert.hidden = true;
      [close, cancel, submit, ...controls].forEach(control => { control.disabled = true; });
      try { await save(controls, modalSignal); if (alive() && !modalSignal.aborted) modal.close(); }
      catch (error) { if (alive() && !modalSignal.aborted) { alert.textContent = text(conflict(error)
        ? 'This mind map changed. Your draft is preserved. Close and reopen to review the saved version.' : error.message); alert.hidden = false; } }
      finally { busy = false; [close, cancel, submit, ...controls].forEach(control => { control.disabled = false; }); }
    }, { signal: modalSignal });
    dialogs.add(modal); modal.addEventListener('close', () => { abort.abort(); dialogs.delete(modal); }, { once: true });
    modalSignal.addEventListener('abort', () => modal.close?.(true), { once: true });
    mountModal(modal, { nested: true, canClose: () => !busy }); return modal;
  }
  function settings(row) {
    if (!state.canManage || row && !row.canConfigure) return;
    const draft = row ? structuredClone(row) : { name: text('New mind map'), visibility: 'gm', editorIds: [], scopeSceneId: null };
    let created;
    const modal = form(row ? 'Mind map permissions' : 'New mind map', fields => {
      const controls = [];
      const field = (name, label, type = 'text', options) => {
        const wrapper = node('label'), caption = node('span', '', text(label)), input = node(options ? 'select' : 'input'); input.name = name;
        if (options) for (const item of options) input.append(new Option(item.label, item.value)); else input.type = type;
        input.value = draft[name] ?? ''; wrapper.append(caption, input); fields.append(wrapper); controls.push(input); return input;
      };
      const name = field('name', 'Mind map name'); name.required = true; name.maxLength = 120; name.setAttribute('translate', 'no');
      field('visibility', 'Visibility', 'text', [{ value: 'gm', label: text('GM only') }, { value: 'players', label: text('Visible to players') }]);
      const scopeChoices = [{ value: '', label: text('Campaign') }, ...(typeof scenes === 'function' ? scenes() : scenes).map(item => ({ value: item.id, label: item.name }))];
      if (draft.scopeSceneId && !scopeChoices.some(choice => choice.value === draft.scopeSceneId)) scopeChoices.push({ value: draft.scopeSceneId, label: text('Selected scene') });
      field('scopeSceneId', 'Scene scope', 'text', scopeChoices).setAttribute('translate', 'no');
      const group = node('fieldset'), legend = node('legend', '', text('Players allowed to edit')); group.append(legend);
      for (const member of state.editors || []) {
        const label = node('label', 'mindmap-form__checkbox'), input = node('input'); input.type = 'checkbox'; input.name = 'editor'; input.value = member.id;
        input.checked = (draft.editorIds || []).includes(member.id); label.append(input, authored('span', '', member.name)); group.append(label); controls.push(input);
      }
      group.append(node('p', 'mindmaps__hint', text('Selected players can read and edit this map, including a GM-only map. Streamers remain read-only.'))); fields.append(group);
      return controls;
    }, async controls => {
      const values = Object.fromEntries(controls.filter(control => control.name !== 'editor').map(control => [control.name, control.value]));
      const payload = { ...values, scopeSceneId: values.scopeSceneId || null,
        editorIds: controls.filter(control => control.name === 'editor' && control.checked).map(control => control.value),
        ...(row ? { id: row.id, version: draft.version } : { document: newMindmapDocument(values.name) }) };
      created = await mutate(row ? 'update' : 'create', payload);
    });
    modal.dataset.mindmapSettingsId = row?.id || '';
    if (!row) modal.addEventListener('close', () => { if (created?.id && alive()) void open(created.id).catch(report); }, { once: true });
    return modal;
  }
  function remove(row) {
    const snapshot = { ...row };
    const modal = form('Delete mind map', fields => { fields.append(authored('strong', '', snapshot.name), node('p', '', text('Delete this mind map and all its topics?'))); return []; },
      () => mutate('delete', { id: snapshot.id, version: snapshot.version }), 'Delete mind map');
    modal.dataset.mindmapSettingsId = row.id; return modal;
  }
  function render() {
    if (!alive()) return;
    rowScope.abort(); rowScope = new AbortController(); root.classList.add('mindmaps'); root.replaceChildren();
    const toolbar = node('div', 'mindmaps__toolbar');
    toolbar.append(button('Refresh mind maps', refresh, rowScope.signal));
    if (state.canManage) toolbar.append(button('New mind map', () => settings(), rowScope.signal)); root.append(toolbar);
    if (errorText) { const error = node('p', 'mindmaps__error', errorText); error.setAttribute('role', 'alert'); root.append(error); }
    const list = node('div', 'mindmaps__list');
    for (const row of state.mindmaps) {
      const card = node('article', 'mindmaps__entry'); card.dataset.mindmapId = row.id;
      const openButton = button('', () => open(row.id), rowScope.signal, 'mindmaps__open');
      openButton.append(authored('strong', '', row.name), node('small', '', text(row.canEdit ? 'Editable mind map' : 'Read-only mind map')));
      card.append(openButton);
      if (row.canConfigure) card.append(button('Permissions', () => settings(row), rowScope.signal), button('Delete mind map', () => remove(row), rowScope.signal));
      list.append(card);
    }
    if (!state.mindmaps.length) list.append(node('p', 'mindmaps__hint', text('No mind maps are available.'))); root.append(list);
  }
  async function open(id, nodeId) {
    if (!alive()) return;
    if (editors.has(id)) { editors.get(id).focus(nodeId); return; }
    if (opening.has(id)) return opening.get(id);
    const epoch = sequence;
    const pending = (async () => {
      const value = await api.mindmaps.read({ id }, { signal });
      if (!alive()) return;
      const row = epoch === sequence ? value?.mindmap || value : state.mindmaps.find(item => item.id === id);
      if (!row && epoch !== sequence) return;
      if (!row?.id || !row.document) throw Error(text('Mind map not found or access denied.'));
      const editor = createEditor(row, () => editors.delete(id)); editors.set(id, editor); editor.focus(nodeId);
    })().finally(() => opening.delete(id));
    opening.set(id, pending); return pending;
  }

  function createEditor(initial, onClose) {
    const abort = new AbortController(), editorSignal = AbortSignal.any([signal, abort.signal]);
    const modal = node('section', 'mindmap-editor table-modal-window'); modal.dataset.mindmapEditor = initial.id;
    const header = node('header', 'mindmap-editor__header'), title = node('input', 'mindmap-editor__name');
    title.value = initial.name; title.maxLength = 120; title.setAttribute('aria-label', text('Mind map name')); title.setAttribute('translate', 'no');
    const close = node('button', '', '×'); close.type = 'button'; close.setAttribute('aria-label', text('Close'));
    const heading = node('h2', 'mindmap-editor__heading', text('Mind map')); heading.id = `mindmap-editor-${initial.id}`; modal.setAttribute('aria-labelledby', heading.id);
    const status = node('span', 'mindmap-editor__status'); status.setAttribute('role', 'status');
    header.append(heading, title, status, close);
    const toolbar = node('div', 'mindmap-editor__toolbar'), error = node('p', 'mindmaps__error'); error.setAttribute('role', 'alert'); error.hidden = true;
    const layout = node('div', 'mindmap-editor__layout'), canvas = node('div', 'mindmap-editor__canvas');
    canvas.dataset.mindmapCanvas = ''; canvas.tabIndex = 0; canvas.setAttribute('role', 'group'); canvas.setAttribute('aria-label', text('Mind map canvas'));
    const world = node('div', 'mindmap-editor__world'), inspector = node('aside', 'mindmap-editor__inspector');
    canvas.append(world); layout.append(canvas, inspector); modal.append(header, toolbar, error, layout);
    const history = createMindmapHistory(initial.document);
    let linkProjection = new Map(initial.document.nodes.flatMap(item => item.links || []).filter(link => link.key).map(link => [link.key, link]));
    const freshLinks = new Map(); let linkEpoch = 0;
    let row = structuredClone(initial), selected = initial.document.nodes[0]?.id, saving = false, stale = false,
      view = { x: 80, y: 80, scale: 1 }, gesture, paintScope = new AbortController(), inspectorScope = new AbortController();
    const active = () => alive() && !editorSignal.aborted;
    const editable = () => row.canEdit === true && !saving && !stale && active();
    const dirty = () => history.dirty || title.value !== row.name;
    const fail = issue => { if (active() && issue?.name !== 'AbortError') { error.textContent = text(conflict(issue)
      ? 'This mind map changed. Your draft is preserved. Reload the saved map before editing again.' : issue.message); error.hidden = false; } };
    const run = work => Promise.resolve().then(work).catch(fail);
    const referenceKey = link => JSON.stringify([link.kind, link.id, link.pageId || null]);
    function projectedDocument() {
      const value = history.value;
      for (const item of value.nodes) item.links = (item.links || []).map(link => link.key
        ? structuredClone(linkProjection.get(link.key) || { unavailable: true, key: link.key })
        : freshLinks.has(referenceKey(link)) ? freshLinks.get(referenceKey(link)) || { unavailable: true } : link);
      return value;
    }
    const getSelected = () => projectedDocument().nodes.find(item => item.id === selected);
    const transform = () => { world.style.transform = `translate(${view.x}px, ${view.y}px) scale(${view.scale})`; };
    function stats() {
      status.textContent = text(saving ? 'Saving...' : stale ? 'Saved version changed' : dirty() ? 'Unsaved changes' : 'Saved');
      title.disabled = !editable();
      for (const control of toolbar.querySelectorAll('[data-edit-action]')) control.disabled = !editable();
      undo.disabled = !editable() || !history.canUndo; redo.disabled = !editable() || !history.canRedo;
      save.disabled = !editable() || !dirty(); reload.hidden = !stale;
      for (const input of inspector.querySelectorAll('input,textarea,select,[data-edit-action]')) input.disabled = !editable();
    }
    function change(next, focusId = selected) {
      if (!editable()) return;
      history.change(next); selected = focusId; error.hidden = true; paint(); inspect(); stats();
    }
    function patch(patchValue) {
      const candidate = history.value, item = candidate.nodes.find(item => item.id === selected); if (!item) return;
      Object.assign(item, patchValue); change(candidate);
    }
    function add(parentId, siblingId) {
      if (history.value.nodes.length >= 500) throw Error(text('A mind map can contain at most 500 topics.'));
      const next = addMindmapNode(history.value, parentId, text('New topic'), { siblingId });
      change(next, next.nodes.at(-1).id);
      [...world.querySelectorAll('[data-mindmap-node-id]')].find(element => element.dataset.mindmapNodeId === selected)?.focus({ preventScroll: true });
    }
    const editButton = (label, action) => { const control = button(label, action, editorSignal); control.dataset.editAction = ''; toolbar.append(control); return control; };
    editButton('Add root topic', () => add(null));
    editButton('Add child topic', () => add(selected || null));
    editButton('Add sibling topic', () => add(null, selected));
    editButton('Delete topic', () => { if (selected) { const next = removeMindmapNode(history.value, selected); change(next, next.nodes[0]?.id); } });
    function navigateHistory(direction) {
      history[direction]();
      if (!history.value.nodes.some(item => item.id === selected)) selected = history.value.nodes[0]?.id;
      paint(); inspect(); stats();
    }
    const undo = editButton('Undo', () => navigateHistory('undo'));
    const redo = editButton('Redo', () => navigateHistory('redo'));
    toolbar.append(button('Zoom out', () => zoom(.8), editorSignal), button('Zoom in', () => zoom(1.25), editorSignal), button('Fit map', fit, editorSignal));
    const save = editButton('Save mind map', () => run(saveMap)); save.dataset.mindmapSave = '';
    const reload = button('Reload saved map', () => run(reloadMap), editorSignal); toolbar.append(reload);
    function zoom(factor) { view = zoomMindmap(view, factor, { x: canvas.clientWidth / 2, y: canvas.clientHeight / 2 }); transform(); }
    function fit() { view = fitMindmap(visibleMindmapNodes(history.value), canvas.clientWidth, canvas.clientHeight); transform(); }
    async function saveMap() {
      if (!editable() || !dirty()) return;
      if (!title.value.trim()) throw Error(text('Enter a mind map name.'));
      const candidate = { id: row.id, version: row.version, name: title.value.trim(), document: projectedDocument() };
      saving = true; stats();
      try {
        await commands.run('update', candidate);
        const latest = await api.mindmaps.read({ id: row.id }, { signal: editorSignal });
        if (!active()) return;
        row = structuredClone(latest?.mindmap || latest); title.value = row.name; history.reset(row.document); stale = false;
        linkProjection = new Map(row.document.nodes.flatMap(item => item.links || []).filter(link => link.key).map(link => [link.key, link])); freshLinks.clear();
        commands.acknowledge(row.id); await refresh(); paint(); inspect(); error.hidden = true;
      } catch (issue) {
        if (conflict(issue)) { stale = true; await refresh().catch(() => {}); }
        throw issue;
      } finally { saving = false; if (active()) stats(); }
    }
    async function reloadMap() {
      if (!active() || saving) return;
      return form('Reload saved mind map', fields => { fields.append(node('p', '', text('Discard your unsaved changes and load the current saved map?'))); return []; }, async () => {
        const value = await api.mindmaps.read({ id: row.id }, { signal: editorSignal }); if (!active()) return;
        row = structuredClone(value?.mindmap || value); history.reset(row.document); title.value = row.name; stale = false;
        linkProjection = new Map(row.document.nodes.flatMap(item => item.links || []).filter(link => link.key).map(link => [link.key, link])); freshLinks.clear();
        paint(); inspect(); stats(); error.hidden = true;
      }, 'Reload saved map', editorSignal);
    }
    function paint() {
      const focused = document.activeElement?.dataset?.mindmapNodeId;
      paintScope.abort(); paintScope = new AbortController(); world.replaceChildren();
      const nodes = visibleMindmapNodes(history.value), byId = new Map(nodes.map(item => [item.id, item]));
      const svg = document.createElementNS(SVG, 'svg'); svg.classList.add('mindmap-editor__edges'); svg.setAttribute('aria-hidden', 'true');
      const edges = [...nodes.filter(item => item.parentId).map(item => ({ from: item.parentId, to: item.id })), ...history.value.edges];
      for (const edge of edges) {
        const from = byId.get(edge.from), to = byId.get(edge.to); if (!from || !to) continue;
        const path = document.createElementNS(SVG, 'path'), a = from.x + 210, b = to.x;
        path.setAttribute('d', `M ${a} ${from.y + 38} C ${(a + b) / 2} ${from.y + 38} ${(a + b) / 2} ${to.y + 38} ${b} ${to.y + 38}`);
        if (edge.id) path.classList.add('mindmap-editor__cross-edge'); svg.append(path);
        if (edge.label) { const label = document.createElementNS(SVG, 'text'); label.textContent = edge.label; label.setAttribute('x', String((a + b) / 2)); label.setAttribute('y', String((from.y + to.y) / 2 + 28)); label.setAttribute('translate', 'no'); svg.append(label); }
      }
      world.append(svg);
      for (const item of nodes) {
        const card = node('button', 'mindmap-editor__topic'); card.type = 'button'; card.dataset.mindmapNodeId = item.id;
        card.style.left = `${item.x}px`; card.style.top = `${item.y}px`; card.style.setProperty('--topic-color', /^#[\da-f]{6}$/i.test(item.color) ? item.color : '#c9a44c');
        card.classList.toggle('mindmap-editor__topic--selected', item.id === selected); card.classList.toggle('mindmap-editor__topic--completed', item.completed === true);
        card.setAttribute('aria-pressed', String(item.id === selected));
        card.setAttribute('aria-keyshortcuts', row.canEdit ? 'Enter F2 Tab Shift+Tab' : 'Enter F2');
        card.append(authored('strong', '', item.label));
        const badges = [item.completed ? text('Completed') : '', item.collapsed ? text('Collapsed') : '', item.links?.length ? `${item.links.length} ${text('Links')}` : ''].filter(Boolean);
        if (badges.length) card.append(node('small', '', badges.join(' · ')));
        card.addEventListener('click', () => { selected = item.id; paint(); inspect(); stats(); }, { signal: paintScope.signal });
        card.addEventListener('dblclick', () => inspector.querySelector('[name=label]')?.focus(), { signal: paintScope.signal });
        world.append(card);
      }
      transform();
      if (focused && (!document.activeElement || document.activeElement === document.body)) {
        [...world.querySelectorAll('[data-mindmap-node-id]')].find(element => element.dataset.mindmapNodeId === (selected || focused))?.focus({ preventScroll: true });
      }
    }
    function inspect() {
      const focused = inspector.contains(document.activeElement) ? document.activeElement?.name : null;
      const selection = focused && typeof document.activeElement.selectionStart === 'number'
        ? [document.activeElement.selectionStart, document.activeElement.selectionEnd] : null;
      inspectorScope.abort(); inspectorScope = new AbortController(); inspector.replaceChildren();
      const item = getSelected();
      if (!item) { inspector.append(node('p', 'mindmaps__hint', text('Select a topic to view its notes and links.'))); return; }
      const field = (key, label, type = 'text') => {
        const wrapper = node('label'), caption = node('span', '', text(label)), input = node(type === 'textarea' ? 'textarea' : 'input');
        input.name = key; if (type !== 'textarea') input.type = type; input.disabled = !editable();
        if (type === 'checkbox') input.checked = !!item[key]; else input.value = item[key] || '';
        if (key === 'label') input.maxLength = 200; if (key === 'notes') { input.maxLength = 8000; input.rows = 5; }
        if (['label', 'notes'].includes(key)) input.setAttribute('translate', 'no');
        const retainDraft = () => {
          if (!editable()) return;
          const candidate = history.value, current = candidate.nodes.find(node => node.id === item.id); if (!current) return;
          current[key] = type === 'checkbox' ? input.checked : input.value;
          if (!history.change(candidate)) return;
          error.hidden = true; paint(); stats();
        };
        input.addEventListener('input', retainDraft, { signal: inspectorScope.signal });
        input.addEventListener('change', retainDraft, { signal: inspectorScope.signal });
        wrapper.append(caption, input); inspector.append(wrapper); return input;
      };
      field('label', 'Topic label'); field('notes', 'Topic notes', 'textarea'); field('color', 'Topic color', 'color');
      field('collapsed', 'Collapse child topics', 'checkbox'); field('completed', 'Completed', 'checkbox');
      const parentLabel = node('label'), parentSelect = node('select'); parentSelect.disabled = !editable(); parentSelect.setAttribute('aria-label', text('Parent topic'));
      parentSelect.setAttribute('translate', 'no');
      parentSelect.append(new Option(text('Root topic'), ''));
      for (const candidate of history.value.nodes) if (candidate.id !== item.id) parentSelect.append(new Option(candidate.label, candidate.id));
      parentSelect.value = item.parentId || '';
      parentSelect.addEventListener('change', () => { try { change(reparentMindmapNode(history.value, selected, parentSelect.value || null)); } catch (issue) { parentSelect.value = item.parentId || ''; fail(issue); } }, { signal: inspectorScope.signal });
      parentLabel.append(node('span', '', text('Parent topic')), parentSelect); inspector.append(parentLabel);
      const links = node('section', 'mindmap-editor__links'); links.append(node('h3', '', text('Linked resources')));
      for (const [index, reference] of (item.links || []).entries()) {
        const entry = node('div', 'mindmap-editor__link');
        if (reference.unavailable) entry.append(node('span', '', text('Unavailable resource')));
        else { const open = button('', () => run(() => openResourceLink(reference, { api, t: text, signal: editorSignal })), inspectorScope.signal); open.textContent = resourceLabel(reference, text); open.setAttribute('translate', 'no'); entry.append(open); }
        if (editable()) entry.append(button('Remove link', () => patch({ links: item.links.filter((_, position) => position !== index) }), inspectorScope.signal)); links.append(entry);
      }
      if (editable()) links.append(button('Link campaign resource', () => pickResourceLink(reference => {
        if (!editable() || selected !== item.id) throw Error(text('This mind map changed. Your draft is preserved. Reload the saved map before editing again.'));
        const current = getSelected();
        if (current?.links.length >= 16) throw Error(text('A topic can contain at most 16 resource links.'));
        freshLinks.delete(referenceKey(reference));
        if (current) patch({ links: [...current.links, reference] });
      }, { api, t: text, signal: editorSignal }), inspectorScope.signal)); inspector.append(links);
      const relations = node('section', 'mindmap-editor__links'); relations.append(node('h3', '', text('Topic connections')));
      for (const edge of history.value.edges.filter(edge => edge.from === item.id || edge.to === item.id)) {
        const peer = history.value.nodes.find(candidate => candidate.id === (edge.from === item.id ? edge.to : edge.from));
        const entry = node('div', 'mindmap-editor__link'); entry.append(authored('span', '', `${edge.label ? edge.label + ': ' : ''}${peer?.label || ''}`));
        if (editable()) entry.append(button('Remove connection', () => { const next = history.value; next.edges = next.edges.filter(candidate => candidate.id !== edge.id); change(next); }, inspectorScope.signal)); relations.append(entry);
      }
      if (editable()) relations.append(button('Connect topics', () => form('Connect topics', fields => {
        const target = node('select'), label = node('input'); target.name = 'to'; label.name = 'label'; label.maxLength = 200;
        target.setAttribute('translate', 'no'); label.setAttribute('translate', 'no');
        target.setAttribute('aria-label', text('Target topic')); label.setAttribute('aria-label', text('Connection label')); label.placeholder = text('Connection label');
        for (const other of history.value.nodes) if (other.id !== item.id) target.append(new Option(other.label, other.id)); fields.append(target, label); return [target, label];
      }, controls => {
        if (!editable()) throw Error(text('This mind map changed. Your draft is preserved. Reload the saved map before editing again.'));
        const next = history.value, to = controls[0].value, label = controls[1].value;
        if (!to) throw Error(text('Choose a target topic.'));
        if (next.edges.length >= 1000) throw Error(text('A mind map can contain at most 1000 connections.'));
        if (next.edges.some(edge => edge.from === item.id && edge.to === to && edge.label === label)) throw Error(text('This connection already exists.'));
        next.edges.push({ id: crypto.randomUUID(), from: item.id, to, label }); change(next);
      }, 'Save changes', editorSignal), inspectorScope.signal));
      inspector.append(relations);
      if (focused && (!document.activeElement || document.activeElement === document.body)) {
        const input = inspector.querySelector(`[name="${focused}"]`); input?.focus({ preventScroll: true });
        if (selection && input?.setSelectionRange) input.setSelectionRange(...selection);
      }
    }
    function stopGesture(commit = false) {
      if (!gesture) return;
      const current = gesture; gesture = undefined; current.abort.abort();
      if (commit && current.node && editable() && current.moved) {
        const next = history.value, item = next.nodes.find(item => item.id === current.node.id);
        if (item) { item.x = Math.max(-100000, Math.min(100000, current.node.x + current.dx / view.scale)); item.y = Math.max(-100000, Math.min(100000, current.node.y + current.dy / view.scale)); change(next); }
      } else if (current.node) paint();
      else if (!commit) { view = current.origin; transform(); }
    }
    canvas.addEventListener('pointerdown', event => {
      if (event.button !== 0 && event.button !== 1 || event.isPrimary === false || gesture) return;
      const target = event.target.closest('[data-mindmap-node-id]'), item = target && history.value.nodes.find(item => item.id === target.dataset.mindmapNodeId);
      if (item && !editable() && event.button !== 1) return;
      const panning = !item || event.button === 1 || event.shiftKey;
      const controller = new AbortController(); gesture = { abort: controller, x: event.clientX, y: event.clientY, dx: 0, dy: 0,
        node: panning ? null : item, origin: { ...view }, moved: false };
      const current = gesture, dragSignal = AbortSignal.any([editorSignal, controller.signal]);
      if (item && !panning) { selected = item.id; target.focus({ preventScroll: true }); inspect(); stats(); }
      document.addEventListener('pointermove', move => {
        if (move.pointerId !== event.pointerId || gesture !== current) return;
        current.dx = move.clientX - current.x; current.dy = move.clientY - current.y;
        if (Math.hypot(current.dx, current.dy) < 4 && !current.moved) return;
        current.moved = true;
        if (current.node) { target.style.left = `${item.x + current.dx / view.scale}px`; target.style.top = `${item.y + current.dy / view.scale}px`; }
        else { view = { ...current.origin, x: current.origin.x + current.dx, y: current.origin.y + current.dy }; transform(); }
        move.preventDefault();
      }, { signal: dragSignal });
      document.addEventListener('pointerup', up => { if (up.pointerId === event.pointerId) stopGesture(true); }, { signal: dragSignal });
      document.addEventListener('pointercancel', cancel => { if (cancel.pointerId === event.pointerId) stopGesture(false); }, { signal: dragSignal });
      event.preventDefault();
    }, { signal: editorSignal });
    canvas.addEventListener('wheel', event => {
      event.preventDefault(); const box = canvas.getBoundingClientRect();
      view = zoomMindmap(view, Math.exp(-event.deltaY * .0015), { x: event.clientX - box.left, y: event.clientY - box.top }); transform();
    }, { signal: editorSignal, passive: false });
    modal.addEventListener('keydown', event => {
      if (event.key === 'Escape' && gesture) { event.preventDefault(); event.stopPropagation(); stopGesture(false); return; }
      if (event.target.closest('input,textarea,select,[contenteditable]')) return;
      const topic = event.target.closest('[data-mindmap-node-id]');
      if (topic && ['Enter', 'F2'].includes(event.key)) {
        event.preventDefault(); event.stopPropagation(); selected = topic.dataset.mindmapNodeId; paint(); inspect(); stats();
        const label = inspector.querySelector('[name=label]');
        const target = label && !label.disabled ? label : [...inspector.querySelectorAll('button,a[href]')].find(control => !control.disabled);
        if (target) target.focus({ preventScroll: true }); else { inspector.tabIndex = 0; inspector.focus({ preventScroll: true }); }
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void run(saveMap); }
      if (!editable()) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') { event.preventDefault(); navigateHistory(event.shiftKey ? 'redo' : 'undo'); }
      if (event.key === 'Delete' && selected) { event.preventDefault(); const next = removeMindmapNode(history.value, selected); change(next, next.nodes[0]?.id); }
      if (event.key === 'Tab' && event.target.closest('[data-mindmap-node-id]')) { event.preventDefault(); event.shiftKey ? add(null, selected) : add(selected); }
    }, { signal: editorSignal });
    title.addEventListener('input', stats, { signal: editorSignal });
    function requestClose() {
      if (saving) return;
      if (!dirty()) return modal.close();
      return form('Unsaved mind map', fields => { fields.append(node('p', '', text('Discard your unsaved mind map changes?'))); return []; }, () => modal.close(true), 'Discard changes', editorSignal);
    }
    close.addEventListener('click', requestClose, { signal: editorSignal });
    modal.addEventListener('close', () => { stopGesture(false); abort.abort(); paintScope.abort(); inspectorScope.abort(); onClose(); }, { once: true });
    // Prevent Escape from silently discarding the local draft.
    mountModal(modal, { nested: true, canClose: () => {
      if (gesture) { stopGesture(false); return false; }
      if (dirty()) { requestClose(); return false; } return !saving;
    } });
    paint(); inspect(); stats(); fit();
    return {
      focus(nodeId) { if (!active()) return; if (nodeId) { const item = history.value.nodes.find(item => item.id === nodeId); if (item) { selected = item.id; view = { ...view, x: canvas.clientWidth / 2 - (item.x + 105) * view.scale, y: canvas.clientHeight / 2 - (item.y + 38) * view.scale }; paint(); inspect(); } } modal.focus(); },
      receive(next) {
        if (!active() || saving) return;
        stopGesture(false);
        linkProjection = new Map(next.document.nodes.flatMap(item => item.links || []).filter(link => link.key).map(link => [link.key, link]));
        const unverified = history.value.nodes.flatMap(item => item.links || []).filter(link => !link.key && !link.unavailable), epoch = ++linkEpoch;
        for (const link of unverified) freshLinks.set(referenceKey(link), null);
        for (const link of unverified) void api.mindmaps.resolve({ reference: { kind: link.kind, id: link.id, ...(link.pageId ? { pageId: link.pageId } : {}) } }, { signal: editorSignal })
          .then(value => { if (active() && epoch === linkEpoch) { const resource = value?.resource || value; freshLinks.set(referenceKey(link), resource?.id ? resource : null); inspect(); stats(); } })
          .catch(() => {});
        if (row.canEdit && !next.canEdit) { row = structuredClone(next); history.reset(row.document); title.value = row.name; stale = false; }
        else if (next.version !== row.version && dirty()) stale = true;
        else if (!dirty()) { row = structuredClone(next); history.reset(row.document); title.value = row.name; stale = false; }
        paint(); inspect(); stats();
      },
      destroy() { modal.close?.(true); },
    };
  }
  const offLocale = translator.onChange(render);
  function destroy() {
    if (own.signal.aborted) return;
    own.abort(); rowScope.abort(); commands.destroy(); offLocale();
    for (const editor of editors.values()) editor.destroy(); editors.clear();
    for (const dialog of dialogs) dialog.close?.(true); dialogs.clear(); opening.clear(); root.replaceChildren();
  }
  signal.addEventListener('abort', () => { if (!own.signal.aborted) destroy(); }, { once: true });
  render(); return { update, refresh, open, create: () => settings(), destroy };
}
