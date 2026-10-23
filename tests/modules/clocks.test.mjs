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
const { mountClocks, clockSectors, clockConfigPayload, createClockCommands } = await import('../../gravewright/table/static/gravewright_table/clocks.js');
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
  const clock = { id: 'clock', name: '<img src=x onerror=alert(1)>', segments: 6, value: 2, color: '#c9a44c',
    visibility: 'gm', playersCanEdit: false, pinned: true, version: 3, sceneId: null, canEdit: true, canConfigure: true };
  const state = data || { clocks: [clock], sceneId: null, is_gm: true };
  const api = { clocks: {
    async state(payload, options) { calls.push(['state', payload, options]); return state; },
    async create(payload, options) { calls.push(['create', structuredClone(payload), options]); return { id: 'created' }; },
    async update(payload, options) { calls.push(['update', structuredClone(payload), options]); return { id: payload.id }; },
    async advance(payload, options) { calls.push(['advance', structuredClone(payload), options]); return { id: payload.id }; },
    async reset(payload, options) { calls.push(['reset', structuredClone(payload), options]); return { id: payload.id }; },
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
  const component = mountClocks(root, { api, pinnedOnly, t: key => key, sceneId: () => selected,
    scenes: () => [{ id: 'scene-a', name: 'Authored scene A' }], onChange: value => changes.push(value), load });
  const action = (name, delta) => find(root, node => node.dataset.clockAction === name && (delta === undefined || node.dataset.clockDelta === String(delta)));
  const controls = modal => Object.fromEntries(all(modal).filter(node => node.name).map(node => [node.name, node]));
  return { root, clock, state, component, api, calls, changes, modals, action, controls,
    set selected(value) { selected = value; }, get selected() { return selected; } };
}

test('every supported sector count produces bounded, closed original SVG geometry', () => {
  for (let count = 2; count <= 24; count++) {
    const paths = clockSectors(count);
    assert.equal(paths.length, count);
    for (const path of paths) {
      assert.match(path, /^M /); assert.match(path, / Z$/);
      assert.equal(path.includes('NaN'), false); assert.equal(path.includes('Infinity'), false);
      const points = [...path.matchAll(/(?:M|L) ([\d.]+) ([\d.]+)/g)];
      assert.ok(points.every(match => Number(match[1]) >= 9 && Number(match[1]) <= 119 && Number(match[2]) >= 9 && Number(match[2]) <= 119));
    }
  }
  for (const count of [0, 1, 25, 2.5, Infinity, '6']) assert.deepEqual(clockSectors(count), []);
});

test('config payload separates persisted scope from context and retains the opening revision', () => {
  const values = { name: ' Campaign clock ', segments: '8', value: '2', color: '#112233', visibility: 'players',
    playersCanEdit: true, pinned: false, sceneId: '' };
  const payload = clockConfigPayload({ id: 'clock', version: 8 }, values, 'scene-a');
  assert.deepEqual(payload, { id: 'clock', version: 8, name: 'Campaign clock', segments: 8, value: 2,
    color: '#112233', visibility: 'players', playersCanEdit: true, pinned: false,
    scopeSceneId: null, sceneId: 'scene-a', mapId: 'scene-a' });
  assert.equal(clockConfigPayload(null, { ...values, sceneId: 'scene-b' }, null).scopeSceneId, 'scene-b');
  assert.equal(values.sceneId, '');
});

test('uncertain retries retain UUIDs, successful commands notify once after a fresh read', async () => {
  const abort = new AbortController(), calls = [], reads = [], changes = [];
  let attempt = 0;
  const commands = createClockCommands({ signal: abort.signal, api: { clocks: {
    async advance(payload, options) { calls.push([payload, options]); if (++attempt < 2) throw new Error('Lost response'); return { id: 'clock' }; },
  } }, refresh: async options => { reads.push(options); return { clocks: [], sceneId: null, is_gm: true }; }, onChange: state => changes.push(state) });
  const payload = { id: 'clock', version: 3, delta: 1, sceneId: null, mapId: null };
  await assert.rejects(commands.run('advance', payload), /Lost response/);
  await commands.run('advance', payload);
  assert.equal(calls[0][1].requestId, calls[1][1].requestId);
  assert.deepEqual(reads, [{ fresh: true }]); assert.equal(changes.length, 1);
  await commands.run('advance', { ...payload, version: 4 });
  assert.notEqual(calls[1][1].requestId, calls[2][1].requestId);
  commands.destroy(); abort.abort();
});

test('conflicts reload state without changing the candidate revision or notifying a successful mutation', async () => {
  const abort = new AbortController(), calls = [], changes = [];
  let reads = 0;
  const commands = createClockCommands({ signal: abort.signal, api: { clocks: {
    async update(payload, options) { calls.push([payload, options]); throw Object.assign(new Error('Stale'), { code: 'conflict' }); },
  } }, refresh: async () => { reads++; return { clocks: [] }; }, onChange: state => changes.push(state) });
  const payload = { id: 'clock', version: 3, name: 'Preserved draft' };
  await assert.rejects(commands.run('update', payload), { code: 'conflict' });
  await assert.rejects(commands.run('update', payload), { code: 'conflict' });
  assert.equal(payload.version, 3); assert.equal(calls.length, 2); assert.equal(reads, 2);
  assert.notEqual(calls[0][1].requestId, calls[1][1].requestId); assert.equal(changes.length, 0);
  abort.abort();
});

test('mount and feed updates perform no HTTP; permission flags govern every control', async () => {
  const f = fixture();
  assert.deepEqual(f.calls, []);
  f.component.update(f.state);
  assert.equal(find(f.root, node => node.dataset.clockName !== undefined).textContent, f.clock.name);
  assert.equal(all(f.root).filter(node => node.localName === 'path').length, 6);
  assert.equal(all(f.root).filter(node => node.attributes.get('class') === 'clocks__sector clocks__sector--filled').length, 2);
  assert.ok(f.action('create') && f.action('edit') && f.action('reset') && f.action('delete'));
  f.component.update({ ...f.state, is_gm: false, clocks: [{ ...f.clock, visibility: 'players', playersCanEdit: true, canEdit: false, canConfigure: false }] });
  assert.equal(f.action('advance'), undefined); assert.equal(f.action('create'), undefined);
  assert.equal(f.action('edit'), undefined); assert.equal(f.action('reset'), undefined); assert.equal(f.action('delete'), undefined);
  f.component.update({ ...f.state, is_gm: false, clocks: [{ ...f.clock, canEdit: true, canConfigure: false }] });
  assert.ok(f.action('advance', 1) && f.action('advance', -1));
  await click(f.action('advance', 1));
  const command = f.calls.find(call => call[0] === 'advance');
  assert.deepEqual(command[1], { id: 'clock', version: 3, sceneId: null, mapId: null, delta: 1 });
  assert.equal(f.changes.length, 1);
  f.component.destroy();
});

test('pinned HUD filters the feed and exposes only permitted progress controls', () => {
  const f = fixture({ pinnedOnly: true });
  f.component.update({ ...f.state, clocks: [f.clock, { ...f.clock, id: 'other', pinned: false }] });
  assert.equal(all(f.root).filter(node => node.dataset.clockId).length, 1);
  assert.ok(f.action('advance')); assert.equal(f.action('edit'), undefined); assert.equal(f.action('create'), undefined);
  f.component.update({ ...f.state, clocks: [] }); assert.equal(f.root.hidden, true);
  f.component.destroy();
});

test('new clock modal uses native nesting, presets, explicit scope and typed form values', async () => {
  const f = fixture(); f.component.update(f.state);
  await click(f.action('create'));
  const { modal, options } = f.modals[0], fields = f.controls(modal);
  assert.equal(options.nested, true); assert.equal(modal.dataset.clockEditor, '');
  fields.name.value = 'Synthetic progress'; fields.preset.value = '12';
  fields.preset.dispatchEvent(new Event('change'));
  assert.equal(fields.segments.value, '12'); assert.equal(fields.value.max, '12');
  fields.value.value = '3'; fields.sceneId.value = ''; fields.visibility.value = 'players';
  fields.playersCanEdit.checked = true; fields.pinned.checked = true;
  find(modal, node => node.localName === 'form').dispatchEvent(new Event('submit', { cancelable: true }));
  await tick();
  const created = f.calls.find(call => call[0] === 'create')[1];
  assert.equal(created.name, 'Synthetic progress'); assert.equal(created.segments, 12); assert.equal(created.value, 3);
  assert.equal(created.scopeSceneId, null); assert.equal(created.sceneId, null); assert.equal(created.mapId, null);
  assert.equal(created.playersCanEdit, true); assert.equal(created.pinned, true);
  assert.equal(modal.isConnected, false); assert.equal(f.changes.length, 1);
  f.component.destroy();
});

test('conflicting editor saves preserve form values and never replace its opening revision', async () => {
  const f = fixture(); f.component.update(f.state);
  await click(f.action('edit'));
  const modal = f.modals[0].modal, fields = f.controls(modal), form = find(modal, node => node.localName === 'form');
  fields.name.value = 'Keep this local draft';
  f.api.clocks.update = async (payload, options) => {
    f.calls.push(['update', payload, options]); f.state.clocks[0].version = 9;
    throw Object.assign(new Error('Stale'), { code: 'conflict' });
  };
  form.dispatchEvent(new Event('submit', { cancelable: true })); await tick();
  assert.equal(fields.name.value, 'Keep this local draft'); assert.equal(modal.isConnected, true);
  assert.match(find(modal, node => node.attributes.get('role') === 'alert').textContent, /Your draft is preserved/);
  form.dispatchEvent(new Event('submit', { cancelable: true })); await tick();
  assert.deepEqual(f.calls.filter(call => call[0] === 'update').map(call => call[1].version), [3, 3]);
  f.component.destroy();
});

test('scene changes and mutation refreshes cannot apply an older in-flight projection', async () => {
  const f = fixture(); f.component.update(f.state);
  let finish;
  f.api.clocks.state = async payload => payload.sceneId === null ? new Promise(resolve => { finish = resolve; })
    : { ...f.state, sceneId: payload.sceneId, clocks: [] };
  const old = f.component.refresh();
  await f.component.setScene('scene-b');
  finish(f.state); await old;
  assert.equal(find(f.root, node => node.dataset.clockId), undefined);
  assert.equal(f.component.update(f.state), false);
  f.component.destroy();
});

test('a newer feed projection supersedes a pending read even when the transport ignores abort', async () => {
  const f = fixture(); f.component.update(f.state);
  let finish, requestSignal;
  f.api.clocks.state = (_payload, options) => {
    requestSignal = options.signal;
    return new Promise(resolve => { finish = resolve; });
  };
  const pending = f.component.refresh();
  const newer = { ...f.state, clocks: [{ ...f.clock, version: 9, value: 5 }] };
  f.component.update(newer);
  assert.equal(requestSignal.aborted, true);
  finish(f.state);
  assert.equal(await pending, newer);
  assert.equal(find(f.root, node => node.dataset.clockValue !== undefined).textContent, '5/6');
  f.component.destroy();
});

test('a feed arriving during the post-commit read remains the canonical successful result', async () => {
  const f = fixture(); f.component.update(f.state);
  let requestSignal;
  f.api.clocks.state = (_payload, options) => new Promise((_resolve, reject) => {
    requestSignal = options.signal;
    options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  });
  await click(f.action('advance', 1));
  assert.ok(requestSignal, 'The committed command must start its canonical read');
  const newer = { ...f.state, clocks: [{ ...f.clock, version: 4, value: 3 }] };
  f.component.update(newer); await tick();
  assert.equal(requestSignal.aborted, true);
  assert.deepEqual(f.changes, [newer]);
  assert.equal(find(f.root, node => node.dataset.clockValue !== undefined).textContent, '3/6');
  assert.equal(find(f.root, node => node.dataset.clocksError !== undefined), undefined);
  f.component.destroy();
});

test('an open editor keeps its read context when scene selection changes', async () => {
  const f = fixture(); f.selected = 'scene-a';
  f.component.update({ ...f.state, sceneId: 'scene-a' });
  await click(f.action('edit'));
  const modal = f.modals[0].modal, fields = f.controls(modal);
  fields.name.value = 'Campaign progress'; fields.sceneId.value = '';
  f.selected = 'scene-b';
  f.api.clocks.state = async payload => ({ ...f.state, sceneId: payload.sceneId });
  find(modal, node => node.localName === 'form').dispatchEvent(new Event('submit', { cancelable: true }));
  await tick();
  const payload = f.calls.find(call => call[0] === 'update')[1];
  assert.equal(payload.sceneId, 'scene-a'); assert.equal(payload.mapId, 'scene-a');
  assert.equal(payload.scopeSceneId, null); assert.equal(payload.version, 3);
  assert.equal(f.changes[0].sceneId, 'scene-b'); assert.equal(modal.isConnected, false);
  f.component.destroy();
});

test('destroy aborts pending modal requests, clears DOM and prevents late modal creation', async () => {
  const f = fixture(); f.component.update(f.state);
  await click(f.action('create'));
  const modal = f.modals[0].modal, form = find(modal, node => node.localName === 'form');
  let finish, requestSignal;
  f.api.clocks.create = async (_payload, options) => { requestSignal = options.signal; return new Promise(resolve => { finish = resolve; }); };
  form.dispatchEvent(new Event('submit', { cancelable: true })); await tick();
  assert.equal(f.modals[0].options.canClose(), false);
  f.component.destroy();
  assert.equal(requestSignal.aborted, true); assert.equal(modal.isConnected, false); assert.equal(f.root.children.length, 0);
  finish({ id: 'late' }); await tick(); assert.equal(f.changes.length, 0);

  let complete;
  const loading = fixture({ loadHook: () => new Promise(resolve => { complete = resolve; }) }); loading.component.update(loading.state);
  await click(loading.action('create')); loading.component.destroy(); complete(); await tick();
  assert.equal(loading.modals.length, 0);
});
