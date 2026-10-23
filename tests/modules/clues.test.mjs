import test from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';

globalThis.window = new EventTarget();
const hook = registerHooks({ resolve(specifier, context, next) {
  if (specifier === '/static/gravewright_modules/i18n.js') return {
    url: new URL('../../gravewright/modules/static/gravewright_modules/i18n.js', import.meta.url).href, shortCircuit: true,
  };
  return next(specifier, context);
} });
const { mountClues, clueConfigPayload, createClueCommands } = await import('../../gravewright/table/static/gravewright_table/clues.js');
hook.deregister();

class Element extends EventTarget {
  constructor(tag, document) {
    super(); this.localName = tag; this.ownerDocument = document; this.children = [];
    this.dataset = {}; this.attributes = new Map(); this.value = ''; this.checked = false;
    this.style = { setProperty() {} }; this.isConnected = true;
    const classes = new Set();
    this.classList = { add: name => classes.add(name), toggle: (name, value) => value ? classes.add(name) : classes.delete(name) };
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  removeAttribute(name) { this.attributes.delete(name); }
  focus() { this.focused = true; }
  reportValidity() { return true; }
}
const all = root => [root, ...root.children.flatMap(all)];
const find = (root, predicate) => all(root).find(predicate);
const tick = () => new Promise(setImmediate);
async function click(button) { assert.ok(button, 'The requested control must exist'); button.dispatchEvent(new Event('click')); await tick(); }

function fixture({ pinnedOnly = false, data, loadHook } = {}) {
  const document = { createElement: tag => new Element(tag, document), createElementNS: (_ns, tag) => new Element(tag, document) };
  const root = document.createElement('div'), calls = [], modals = [], changes = [];
  let selected = null;
  const clue = { id: 'clue', name: '<img src=x onerror=alert(1)>', segments: 6, value: 2, color: '#c9a44c',
    content: '<b>Authored content</b>\nSecond line', gmNotes: 'PRIVATE GM note', discovered: false, visibility: 'players', pinned: true, version: 3, sceneId: null, canEdit: true, canConfigure: true };
  const state = data || { clues: [clue], sceneId: null, is_gm: true };
  const api = { clues: {
    async state(payload, options) { calls.push(['state', payload, options]); return state; },
    async create(payload, options) { calls.push(['create', structuredClone(payload), options]); return { id: 'created' }; },
    async update(payload, options) { calls.push(['update', structuredClone(payload), options]); return { id: payload.id }; },
    async advance(payload, options) { calls.push(['advance', structuredClone(payload), options]); return { id: payload.id }; },
    async reset(payload, options) { calls.push(['reset', structuredClone(payload), options]); return { id: payload.id }; },
    async reveal(payload, options) { calls.push(['reveal', structuredClone(payload), options]); return { id: payload.id }; },
    async hide(payload, options) { calls.push(['hide', structuredClone(payload), options]); return { id: payload.id }; },
    async delete(payload, options) { calls.push(['delete', structuredClone(payload), options]); return { id: payload.id }; },
  } };
  const load = async path => {
    assert.equal(path, '/static/gravewright_table/modal.js'); await loadHook?.();
    return { mountModal(modal, options) {
      modals.push({ modal, options });
      modal.close = force => {
        modal.isConnected = false; modal.dispatchEvent(new Event('close'));
      };
      return modal;
    } };
  };
  const component = mountClues(root, { api, pinnedOnly, t: key => key, sceneId: () => selected,
    scenes: () => [{ id: 'scene-a', name: 'Authored scene A' }], onChange: value => changes.push(value), load });
  const action = (name, delta) => find(root, node => node.dataset.clueAction === name && (delta === undefined || node.dataset.clueDelta === String(delta)));
  const controls = modal => Object.fromEntries(all(modal).filter(node => node.name).map(node => [node.name, node]));
  return { root, clue, state, component, api, calls, changes, modals, action, controls,
    set selected(value) { selected = value; }, get selected() { return selected; } };
}

test('clue configuration preserves authored content and separates saved scope from read context', () => {
  const values = { name: '  A clue  ', content: ' <b>plain</b>\n  content ', gmNotes: '  private notes  ',
    segments: '1', value: '1', color: '#112233', visibility: 'players', sceneId: '', pinned: true };
  assert.deepEqual(clueConfigPayload({ id: 'clue', version: 7 }, values, 'scene-a'), {
    id: 'clue', version: 7, name: 'A clue', content: values.content, gmNotes: values.gmNotes,
    segments: 1, value: 1, color: '#112233', visibility: 'players', pinned: true,
    scopeSceneId: null, sceneId: 'scene-a', mapId: 'scene-a',
  });
  assert.equal(clueConfigPayload(null, { ...values, sceneId: 'scene-b' }, null).scopeSceneId, 'scene-b');
});

test('GM cards use plain authored text, collapsed private notes and progress including a single step', () => {
  const f = fixture(); f.component.update(f.state);
  assert.equal(f.calls.length, 0);
  assert.equal(find(f.root, node => node.dataset.clueName !== undefined).textContent, f.clue.name);
  assert.equal(find(f.root, node => node.dataset.clueContent !== undefined).textContent, f.clue.content);
  const notes = find(f.root, node => node.dataset.clueGmNotes !== undefined);
  assert.equal(notes.localName, 'details'); assert.notEqual(notes.open, true);
  assert.equal(notes.children[1].textContent, f.clue.gmNotes);
  assert.equal(all(f.root).some(node => node.localName === 'img' || node.localName === 'b'), false);
  for (const action of ['create', 'edit', 'delete', 'advance', 'reset', 'reveal', 'hide']) assert.ok(f.action(action));
  f.component.update({ ...f.state, clues: [{ ...f.clue, segments: 1, value: 0 }] });
  const meter = find(f.root, node => node.dataset.clueProgress !== undefined);
  assert.equal(meter.attributes.get('aria-valuemax'), '1'); assert.equal(meter.children.length, 1);
  f.component.destroy();
});

test('public projections render only discovered public clues and never show GM notes or write controls', () => {
  const f = fixture();
  const discovered = { ...f.clue, id: 'known', name: 'Known clue', content: 'Known content', value: 6, discovered: true };
  f.component.update({ ...f.state, is_gm: false, clues: [f.clue, discovered,
    { ...discovered, id: 'private', name: 'Hidden title', visibility: 'gm' },
    { ...discovered, id: 'incomplete', name: 'Another secret', value: 5 }] });
  assert.deepEqual(all(f.root).filter(node => node.dataset.clueId).map(node => node.dataset.clueId), ['known']);
  assert.equal(find(f.root, node => node.dataset.clueGmNotes !== undefined), undefined);
  assert.equal(all(f.root).some(node => node.textContent === f.clue.gmNotes || node.textContent === f.clue.name || node.textContent === 'Hidden title'), false);
  for (const action of ['create', 'edit', 'delete', 'advance', 'reset', 'reveal', 'hide']) assert.equal(f.action(action), undefined);
  f.component.destroy();
});

test('a pinned public clue opens a read-only native modal and hiding it removes its open content', async () => {
  const f = fixture({ pinnedOnly: true });
  const known = { ...f.clue, value: 6, discovered: true, canEdit: false, canConfigure: false };
  f.component.update({ ...f.state, is_gm: false, clues: [known, { ...known, id: 'other', pinned: false }] });
  assert.equal(all(f.root).filter(node => node.dataset.clueId).length, 1);
  assert.ok(f.action('open')); assert.equal(f.action('create'), undefined);
  await click(f.action('open'));
  const { modal, options } = f.modals[0];
  assert.equal(options.nested, true); assert.equal(modal.dataset.clueView, 'clue');
  assert.equal(find(modal, node => node.dataset.clueContent !== undefined).textContent, known.content);
  assert.deepEqual(f.controls(modal), {});
  assert.equal(all(modal).some(node => node.textContent === f.clue.gmNotes), false);
  assert.equal(find(modal, node => node.type === 'submit').hidden, true);
  f.component.update({ clues: [], is_gm: false, sceneId: null });
  assert.equal(modal.isConnected, false); assert.equal(f.root.hidden, true); assert.equal(f.calls.length, 0);
  f.component.destroy();
});

test('new clue editors support one to twenty-four steps, private text and explicit persisted scope', async () => {
  const f = fixture(); f.component.update(f.state);
  await click(f.action('create'));
  const { modal, options } = f.modals[0], fields = f.controls(modal);
  assert.equal(options.nested, true); assert.equal(fields.visibility.value, 'players');
  assert.equal(fields.segments.min, '1'); assert.equal(fields.segments.max, '24');
  assert.equal(fields.content.localName, 'textarea'); assert.equal(fields.gmNotes.maxLength, 4000);
  assert.equal(fields.playersCanEdit, undefined);
  fields.name.value = 'Synthetic clue'; fields.content.value = '<script>plain</script>\nSecond line';
  fields.gmNotes.value = 'Private solution'; fields.value.value = '3'; fields.segments.value = '1';
  fields.segments.dispatchEvent(new Event('input'));
  assert.equal(fields.value.max, '1'); assert.equal(fields.value.value, '1');
  fields.sceneId.value = ''; fields.pinned.checked = true;
  find(modal, node => node.localName === 'form').dispatchEvent(new Event('submit', { cancelable: true })); await tick();
  const payload = f.calls.find(call => call[0] === 'create')[1];
  assert.equal(payload.content, fields.content.value); assert.equal(payload.gmNotes, 'Private solution');
  assert.equal(payload.segments, 1); assert.equal(payload.value, 1); assert.equal(payload.pinned, true);
  assert.equal(payload.scopeSceneId, null); assert.equal(payload.sceneId, null); assert.equal(payload.mapId, null);
  assert.equal(modal.isConnected, false); assert.equal(f.changes.length, 1);
  f.component.destroy();
});

test('uncertain replies keep one operation UUID while a changed candidate gets a new UUID', async () => {
  const abort = new AbortController(), calls = [], changes = [];
  let attempt = 0;
  const commands = createClueCommands({ signal: abort.signal, api: { clues: {
    async update(payload, options) { calls.push([payload, options]); if (++attempt === 1) throw new Error('Lost response'); return { id: payload.id }; },
  } }, refresh: async options => { assert.equal(options.fresh, true); return { clues: [], sceneId: null, is_gm: true }; }, onChange: state => changes.push(state) });
  const payload = { id: 'clue', version: 3, content: 'Authored candidate' };
  await assert.rejects(commands.run('update', payload), /Lost response/); await commands.run('update', payload);
  assert.equal(calls[0][1].requestId, calls[1][1].requestId); assert.equal(changes.length, 1);
  await commands.run('update', { ...payload, content: 'Changed candidate' });
  assert.notEqual(calls[1][1].requestId, calls[2][1].requestId);
  commands.destroy(); abort.abort();
});

test('conflicting drafts keep their opening revision, authored values and read context across selection changes', async () => {
  const f = fixture(); f.selected = 'scene-a'; f.component.update({ ...f.state, sceneId: 'scene-a' });
  await click(f.action('edit'));
  const modal = f.modals[0].modal, fields = f.controls(modal), form = find(modal, node => node.localName === 'form');
  fields.name.value = 'Keep my draft'; fields.content.value = 'New text'; fields.gmNotes.value = 'Private draft';
  f.selected = 'scene-b';
  f.api.clues.update = async (payload, options) => { f.calls.push(['update', payload, options]); throw Object.assign(new Error('Stale'), { code: 'conflict' }); };
  f.api.clues.state = async payload => ({ ...f.state, sceneId: payload.sceneId, clues: [{ ...f.clue, version: 9 }] });
  form.dispatchEvent(new Event('submit', { cancelable: true })); await tick();
  assert.equal(modal.isConnected, true); assert.equal(fields.name.value, 'Keep my draft'); assert.equal(fields.gmNotes.value, 'Private draft');
  assert.match(find(modal, node => node.attributes.get('role') === 'alert').textContent, /Your draft is preserved/);
  form.dispatchEvent(new Event('submit', { cancelable: true })); await tick();
  const attempts = f.calls.filter(call => call[0] === 'update');
  assert.deepEqual(attempts.map(call => [call[1].version, call[1].sceneId]), [[3, 'scene-a'], [3, 'scene-a']]);
  assert.notEqual(attempts[0][2].requestId, attempts[1][2].requestId); assert.equal(f.changes.length, 0);
  f.component.destroy();
});

test('GM progress and reveal/hide controls send revisioned commands without local secret mutations', async () => {
  const f = fixture(); f.component.update(f.state);
  for (const name of ['reveal', 'hide', 'reset']) await click(f.action(name));
  await click(f.action('advance', 1)); await click(f.action('advance', -1));
  const writes = f.calls.filter(call => call[0] !== 'state');
  assert.deepEqual(writes.map(call => call[0]), ['reveal', 'hide', 'reset', 'advance', 'advance']);
  for (const [, payload, options] of writes) {
    assert.equal(payload.id, 'clue'); assert.equal(payload.version, 3); assert.equal(payload.sceneId, null);
    assert.equal(Object.hasOwn(payload, 'content'), false); assert.equal(Object.hasOwn(payload, 'gmNotes'), false);
    assert.match(options.requestId, /^[\da-f-]{36}$/);
  }
  assert.deepEqual(writes.slice(3).map(call => call[1].delta), [1, -1]);
  assert.equal(f.clue.value, 2); assert.equal(f.clue.visibility, 'players'); assert.equal(f.changes.length, 5);
  f.component.destroy();
});

test('a feed supersedes stale reads and stays canonical if it aborts a post-commit refresh', async () => {
  const f = fixture(); f.component.update(f.state);
  let finish, requestSignal;
  f.api.clues.state = (_payload, options) => { requestSignal = options.signal; return new Promise(resolve => { finish = resolve; }); };
  const pending = f.component.refresh(), newer = { ...f.state, clues: [{ ...f.clue, version: 4, value: 3 }] };
  f.component.update(newer); assert.equal(requestSignal.aborted, true); finish(f.state);
  assert.equal(await pending, newer); assert.equal(find(f.root, node => node.dataset.clueValue !== undefined).textContent, '3/6');
  f.api.clues.state = (_payload, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  });
  await click(f.action('advance', 1));
  const canonical = { ...f.state, clues: [{ ...f.clue, version: 5, value: 4 }] };
  f.component.update(canonical); await tick();
  assert.deepEqual(f.changes, [canonical]); assert.equal(find(f.root, node => node.dataset.cluesError !== undefined), undefined);
  f.component.destroy();
});

test('scene changes cannot accept a projection from the previous context', async () => {
  const f = fixture(); f.component.update(f.state);
  let finish;
  f.api.clues.state = async payload => payload.sceneId === null ? new Promise(resolve => { finish = resolve; }) : { ...f.state, sceneId: payload.sceneId, clues: [] };
  const old = f.component.refresh(); await f.component.setScene('scene-b'); finish(f.state); await old;
  assert.equal(find(f.root, node => node.dataset.clueId), undefined); assert.equal(f.component.update(f.state), false);
  f.component.destroy();
});

test('a lost GM role closes a private editor and strips all private card content', async () => {
  const f = fixture(); f.component.update(f.state); await click(f.action('edit'));
  const modal = f.modals[0].modal;
  f.component.update({ ...f.state, is_gm: false, clues: [] });
  assert.equal(modal.isConnected, false); assert.equal(find(f.root, node => node.dataset.clueId), undefined);
  assert.equal(f.action('create'), undefined); f.component.destroy();
});

test('destroy aborts pending requests and lazy imports without leaving modals, DOM or notifications', async () => {
  const f = fixture(); f.component.update(f.state); await click(f.action('create'));
  const modal = f.modals[0].modal;
  let finish, requestSignal;
  f.api.clues.create = async (_payload, options) => { requestSignal = options.signal; return new Promise(resolve => { finish = resolve; }); };
  find(modal, node => node.localName === 'form').dispatchEvent(new Event('submit', { cancelable: true })); await tick();
  assert.equal(f.modals[0].options.canClose(), false);
  f.component.destroy(); assert.equal(requestSignal.aborted, true); assert.equal(modal.isConnected, false); assert.equal(f.root.children.length, 0);
  finish({ id: 'late' }); await tick(); assert.equal(f.changes.length, 0);
  let complete;
  const loading = fixture({ loadHook: () => new Promise(resolve => { complete = resolve; }) }); loading.component.update(loading.state);
  await click(loading.action('create')); loading.component.destroy(); complete(); await tick();
  assert.equal(loading.modals.length, 0);
});
