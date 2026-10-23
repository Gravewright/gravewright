import test from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';

const hooks = registerHooks({ resolve(specifier, context, next) {
  if (specifier === '/static/gravewright_table/resource-links.js') return { url: new URL('../../gravewright/table/static/gravewright_table/resource-links.js', import.meta.url).href, shortCircuit: true };
  return next(specifier, context);
}, load(url, context, next) {
  if (url.endsWith('/gravewright_table/modal.js')) return { format: 'module', shortCircuit: true, source: `export function mountModal(modal) {
    document.body.append(modal); modal.close = () => { modal.isConnected=false; modal.dispatchEvent(new Event('close')); }; return modal;
  }` };
  return next(url, context);
} });
const { createJournalResourceLinks, journalResourceNode, resourceHtml } = await import('../../gravewright/journals/static/gravewright_journals/resource-links.js');
const { openResourceLink, repeatedResourceEvent } = await import('../../gravewright/table/static/gravewright_table/resource-links.js');
hooks.deregister();

class Element extends EventTarget {
  constructor(tag, doc) { super(); Object.assign(this, { localName: tag, ownerDocument: doc, children: [], dataset: {}, attributes: new Map(), isConnected: true, style: {} }); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(key, value) { this.attributes.set(key, String(value)); }
  removeAttribute(key) { this.attributes.delete(key); }
  closest() { return null; }
}
const tick = () => new Promise(setImmediate);
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const key = (element, name) => { const event = new Event('keydown', { cancelable: true }); Object.defineProperty(event, 'key', { value: name }); element.dispatchEvent(event); return event; };
function fixture({ readonly = false, journalId = 'journal', pageId, pagePersisted, readJournal } = {}) {
  const window = new EventTarget(), doc = { defaultView: window, createElement: tag => new Element(tag, doc), getElementById: () => null, querySelector: () => null };
  doc.body = doc.createElement('body'); globalThis.window = window; globalThis.document = doc;
  const host = doc.createElement('div'), calls = [], errors = [], nodes = [], scope = new AbortController();
  let projection = [], callback, picker;
  const editor = { isEditable: !readonly, state: { doc: { descendants(fn) { nodes.forEach((node, index) => fn(node, index)); } }, get tr() {
    const patches = [], meta = {};
    return { patches, meta, setNodeMarkup(pos, _, attrs) { patches.push([pos, attrs]); return this; }, setMeta(key, value) { meta[key] = value; return this; } };
  } }, view: { dispatch(transaction) { calls.push(['projection', transaction.meta]); for (const [pos, attrs] of transaction.patches) { nodes[pos].attrs = attrs; nodes[pos].view.update(nodes[pos]); } } },
  setEditable(value) { this.isEditable = value; }, chain() { const chain = { focus() { return this; }, setTextSelection(pos) { calls.push(['position', pos]); return this; }, insertContent(content) { calls.push(['insert', content]); return this; }, run() { return true; } }; return chain; } };
  const api = { mindmaps: { resolve() { throw Error('Wrong domain'); } }, journals: {
    async state() { calls.push(['state']); return { journals: projection }; },
    async resolve(payload) { calls.push(['resolve', payload]); return { resource: { ...payload.reference, label: 'Fresh resource' } }; },
  } };
  const resources = createJournalResourceLinks({ host, api, editor: () => editor, text: key => key, readonly, journalId, pageId, pagePersisted, readJournal, signal: scope.signal,
    open: async (reference, options) => calls.push(['open', reference, options]), report: error => errors.push(error),
    pick: (insert, options) => { callback = insert; calls.push(['pick', options]); picker = { isConnected: true, close() { this.isConnected = false; } }; return picker; } });
  function add(reference) { const node = { type: { name: 'gwResourceLink' }, attrs: { reference } }; node.view = resources.view({ node }); nodes.push(node); return node; }
  return { window, doc, host, calls, errors, nodes, scope, editor, api, resources, add, get callback() { return callback; }, get picker() { return picker; }, set projection(value) { projection = value; } };
}

test('legacy directory references become typed atoms; hidden HTML contains only the opaque reference', () => {
  assert.deepEqual(journalResourceNode({ type: 'journal', id: 'target', pageId: 'section', title: 'Authored title' }), { type: 'gwResourceLink', attrs: { reference: { kind: 'journal', id: 'target', pageId: 'section', label: 'Authored title' } } });
  assert.equal(journalResourceNode({ type: 'actor', id: 12 }), null);
  const html = resourceHtml({ unavailable: true, key: 'opaque', id: 'secret-id', label: 'Private title' }, key => key);
  assert.equal(JSON.stringify(html).includes('secret-id'), false); assert.equal(JSON.stringify(html).includes('Private title'), false);
  assert.equal(html[2], 'Unavailable resource');
});

test('inline atoms open by click, Enter and Space using journal authorization and readonly never inserts', async () => {
  const f = fixture({ readonly: true }), node = f.add({ kind: 'actor', id: 'target', label: 'Character' }), dom = node.view.dom;
  assert.equal(dom.attributes.get('role'), 'link'); assert.equal(dom.attributes.get('translate'), 'no');
  dom.dispatchEvent(new Event('click')); assert.equal(key(dom, 'Enter').defaultPrevented, true); key(dom, ' '); await tick();
  assert.equal(f.calls.filter(call => call[0] === 'open').length, 3);
  assert.equal(f.calls[0][2].resourceApi, f.api.journals); assert.equal(f.calls[0][2].preferNative, true);
  assert.equal(f.resources.insert({ kind: 'actor', id: 'target' }), false); f.resources.choose();
  assert.equal(f.calls.some(call => call[0] === 'pick' || call[0] === 'insert'), false); f.resources.destroy();
});

test('picker insertion uses the full journals catalog and stale selections cannot mutate a destroyed editor', () => {
  const f = fixture(); f.resources.choose(7); assert.equal(f.calls[0][1].resourceApi, f.api.journals);
  f.callback({ kind: 'session-plan', id: 'session', label: 'Session' });
  assert.deepEqual(f.calls.find(call => call[0] === 'insert')[1][0], journalResourceNode({ kind: 'session-plan', id: 'session', label: 'Session' }));
  f.resources.destroy(); assert.equal(f.picker.isConnected, false); assert.throws(() => f.callback({ kind: 'actor', id: 'other' }), /cannot edit/);
});

test('confirming an @ picker replaces only its trigger range and cancellation makes no edit', () => {
  const f = fixture(), range = { from: 8, to: 9, text: '@' };
  f.editor.state.doc.content = { size: 40 };
  f.editor.state.doc.textBetween = (from, to) => from === 8 && to === 9 ? '@' : 'Other text';
  f.resources.choose(range);
  assert.equal(f.calls.some(call => call[0] === 'position' || call[0] === 'insert'), false);
  f.picker.close();
  assert.equal(f.calls.some(call => call[0] === 'position' || call[0] === 'insert'), false);
  f.resources.choose(range); f.callback({ kind: 'actor', id: 'target', label: 'Actor' });
  assert.deepEqual(f.calls.find(call => call[0] === 'position')[1], { from: 8, to: 9 });
  assert.equal(f.calls.filter(call => call[0] === 'insert').length, 1);
  f.resources.destroy();
});

test('a changed trigger or revoked editing cannot replace unrelated text through a delayed picker', () => {
  const f = fixture(), range = { from: 8, to: 9, text: '@' };
  f.editor.state.doc.content = { size: 40 }; f.editor.state.doc.textBetween = () => '@';
  f.resources.choose(range); f.editor.state.doc.textBetween = () => 'x';
  assert.throws(() => f.callback({ kind: 'actor', id: 'target' }), /insertion point changed/);
  assert.equal(f.calls.some(call => call[0] === 'position' || call[0] === 'insert'), false);
  f.editor.state.doc.textBetween = () => '@'; f.editor.isEditable = false;
  assert.throws(() => f.callback({ kind: 'actor', id: 'target' }), /cannot edit/);
  f.resources.destroy();
});

test('live projection redacts revoked labels, preserves opaque links and authored text through Undo without autosave transactions', async () => {
  const f = fixture(), original = { kind: 'clock', id: 'private', label: 'Private clock', key: 'opaque' }, node = f.add(original);
  f.projection = [{ id: 'journal', content_doc: { type: 'doc', content: [{ type: 'gwResourceLink', attrs: { reference: { unavailable: true, key: 'opaque' } } }] } }];
  await f.resources.refresh(); assert.equal(node.view.dom.textContent, 'Unavailable resource');
  assert.deepEqual(node.attrs.reference, { unavailable: true, key: 'opaque' });
  assert.deepEqual(f.calls.find(call => call[0] === 'projection')[1], { preventUpdate: true, addToHistory: false });
  node.attrs.reference = original; node.view.update(node);
  const draft = { type: 'doc', content: [{ type: 'text', text: 'Keep typing' }, { type: 'gwResourceLink', attrs: { reference: original } }] };
  assert.equal(JSON.stringify(f.resources.serialize(draft)).includes('Private clock'), false);
  assert.equal(f.resources.serialize(draft).content[0].text, 'Keep typing'); assert.equal(node.view.dom.textContent, 'Unavailable resource');
  await tick(); assert.deepEqual(node.attrs.reference, { unavailable: true, key: 'opaque' }); f.resources.destroy();
});

test('a renewed grant restores an opaque atom by stable key without exposing the target while denied', async () => {
  const f = fixture(), node = f.add({ unavailable: true, key: 'opaque' });
  node.view.dom.dispatchEvent(new Event('click')); assert.equal(f.calls.length, 0);
  f.projection = [{ id: 'journal', sections: [{ content: { type: 'gwResourceLink', attrs: { reference: { kind: 'actor', id: 'visible', label: 'Now permitted', key: 'opaque' } } } }] }];
  await f.resources.refresh(); assert.equal(node.view.dom.textContent, 'Now permitted'); assert.equal(node.view.dom.tabIndex, 0);
  f.resources.destroy();
});

test('source revocation disables and disposes the editor; late target resolution cannot resurrect its labels', async () => {
  const f = fixture(), pending = deferred(), node = f.add({ kind: 'item', id: 'new', label: 'Unsaved item' });
  f.projection = [{ id: 'journal' }]; f.api.journals.resolve = () => pending.promise;
  const refresh = f.resources.refresh(); await tick(); f.scope.abort(); pending.resolve({ resource: { kind: 'item', id: 'new', label: 'Late private label' } }); await refresh;
  assert.equal(node.view.dom.textContent, 'Unavailable resource'); assert.equal(node.view.dom.tabIndex, -1);
  assert.equal(resourceHtml(f.resources.project({ kind: 'item', id: 'new', label: 'Old private label' }), key => key)[2], 'Unavailable resource');
  node.view.dom.dispatchEvent(new Event('click')); assert.equal(f.calls.some(call => call[0] === 'open'), false);
  const revoked = fixture(); revoked.add({ kind: 'actor', id: 'old', key: 'opaque' }); await revoked.resources.refresh();
  assert.equal(revoked.host.hidden, true); assert.equal(revoked.editor.isEditable, false);
});

test('destroying one node disposes its activation listeners without closing the whole editor', async () => {
  const f = fixture(), first = f.add({ kind: 'actor', id: 'a' }), second = f.add({ kind: 'item', id: 'b' });
  first.view.destroy(); first.view.dom.dispatchEvent(new Event('click')); second.view.dom.dispatchEvent(new Event('click')); await tick();
  assert.equal(f.calls.filter(call => call[0] === 'open').length, 1); assert.equal(f.calls[0][1].id, 'b'); f.resources.destroy();
});

test('page-owner editing survives journal-level readonly and stops when that exact page grant is revoked', async () => {
  const f = fixture({ pageId: 'owned-page' }); f.add({ kind: 'actor', id: 'actor', key: 'opaque' });
  f.projection = [{ id: 'journal', can_edit: false, sections: [{ id: 'owned-page', can_edit: true }] }];
  await f.resources.refresh(); assert.equal(f.editor.isEditable, true); f.resources.choose();
  f.projection = [{ id: 'journal', can_edit: false, sections: [{ id: 'owned-page', can_edit: false }, { id: 'other-page', can_edit: true }] }];
  await f.resources.refresh(); assert.equal(f.editor.isEditable, false); assert.equal(f.picker.isConnected, false);
  assert.equal(f.resources.insert({ kind: 'item', id: 'other' }), false); f.resources.destroy();
});

test('temporary presentations refresh through their authorized ticket reader without requiring directory visibility', async () => {
  let current = { id: 'journal', can_open: true, content_doc: { type: 'gwResourceLink', attrs: { reference: { kind: 'actor', id: 'actor', key: 'opaque', label: 'Presented reference' } } } };
  const f = fixture({ readonly: true, readJournal: async () => current }), node = f.add({ unavailable: true, key: 'opaque' });
  f.api.journals.state = () => { throw Error('Temporary grants do not appear in the directory'); };
  await f.resources.refresh(); assert.equal(node.view.dom.textContent, 'Presented reference'); assert.notEqual(f.host.hidden, true);
  current = null; await f.resources.refresh(); assert.equal(f.host.hidden, true); assert.equal(node.view.dom.textContent, 'Unavailable resource');
});

test('a local new page survives feeds before its first autosave and becomes revocable after persistence', async () => {
  const f = fixture({ pageId: 'new-page', pagePersisted: false }), node = f.add({ kind: 'clock', id: 'clock', label: 'New link' });
  f.projection = [{ id: 'journal', can_edit: true, sections: [] }]; await f.resources.refresh();
  assert.notEqual(f.host.hidden, true); assert.equal(f.editor.isEditable, true); assert.equal(node.view.dom.textContent, 'Fresh resource');
  f.projection = [{ id: 'journal', can_edit: true, sections: [{ id: 'new-page', can_edit: true }] }]; await f.resources.refresh();
  f.projection = [{ id: 'journal', can_edit: true, sections: [] }]; await f.resources.refresh(); assert.equal(f.host.hidden, true);
});

test('a readonly page that leaves the authorized projection is hidden and its link listeners are disposed', async () => {
  const f = fixture({ readonly: true, pageId: 'old-page' }), node = f.add({ kind: 'actor', id: 'actor', key: 'opaque' });
  f.projection = [{ id: 'journal', can_edit: false, sections: [] }]; await f.resources.refresh();
  assert.equal(f.host.hidden, true); node.view.dom.dispatchEvent(new Event('click')); assert.equal(f.calls.some(call => call[0] === 'open'), false);
});

test('an unsaved atom retains its canonical address during invalidation so fresh resolution can restore its label', async () => {
  const f = fixture(), node = f.add({ kind: 'clock', id: 'new', label: 'Old label' }); f.projection = [{ id: 'journal' }];
  f.window.dispatchEvent(new Event('gravewright:resources')); await tick();
  assert.equal(node.view.dom.textContent, 'Unavailable resource'); assert.deepEqual(node.attrs.reference, { kind: 'clock', id: 'new' });
  await f.resources.refresh(); assert.equal(node.view.dom.textContent, 'Fresh resource'); assert.equal(node.attrs.reference.id, 'new'); f.resources.destroy();
});

test('invalidation immediately supersedes an older read even when it resolves before the coalesced refresh starts', async () => {
  const f = fixture(), node = f.add({ kind: 'clock', id: 'clock', label: 'Previously authorized', key: 'opaque' }), pending = deferred();
  let requestedSignal;
  f.api.journals.state = (_, options) => { requestedSignal = options.signal; return pending.promise; };
  const oldRead = f.resources.refresh(); f.window.dispatchEvent(new Event('gravewright:resources'));
  assert.equal(requestedSignal.aborted, true);
  pending.resolve({ journals: [{ id: 'journal', content_doc: { type: 'gwResourceLink', attrs: { reference: { kind: 'clock', id: 'clock', label: 'Stale private label', key: 'opaque' } } } }] });
  await oldRead; assert.equal(node.view.dom.textContent, 'Unavailable resource');
  assert.equal(JSON.stringify(f.resources.serialize({ type: 'gwResourceLink', attrs: { reference: node.attrs.reference } })).includes('Stale private label'), false);
  f.resources.destroy();
});

test('shared native opener uses journals.resolve, rejects a null wrapper and invalidates reads before their response arrives', async () => {
  const f = fixture(), opened = []; f.window.gravewrightActors = { open: id => opened.push(id) };
  const ref = { kind: 'actor', id: 'target' };
  await openResourceLink(ref, { api: f.api, resourceApi: f.api.journals, preferNative: true }); assert.deepEqual(opened, ['target']);
  f.api.journals.resolve = async () => ({ resource: null });
  const modal = await openResourceLink(ref, { api: f.api, resourceApi: f.api.journals, preferNative: true });
  assert.equal(modal.children[0].children[0].textContent, 'Unavailable resource'); assert.deepEqual(opened, ['target']); modal.close();
  const pending = deferred(); f.api.journals.resolve = () => pending.promise;
  const opening = openResourceLink(ref, { api: f.api, resourceApi: f.api.journals, preferNative: true });
  f.window.dispatchEvent(new Event('gravewright:resources')); pending.resolve({ resource: { ...ref, label: 'Private actor' } });
  assert.equal(await opening, undefined); assert.deepEqual(opened, ['target']); f.resources.destroy();
});

test('unrelated resource refreshes cannot cancel a normal clock preview opening', async () => {
  const f = fixture(), pending = deferred(); f.api.journals.resolve = () => pending.promise;
  f.api.clocks = { async state() { return { clocks: [{ id: 'clock', value: 1, segments: 4 }] }; } };
  const opening = openResourceLink({ kind: 'clock', id: 'clock' }, { api: f.api, resourceApi: f.api.journals });
  const unrelated = new Event('gravewright:journals'); Object.defineProperty(unrelated, 'detail', { value: { journals: [{ id: 'journal', version: 2 }] } }); f.window.dispatchEvent(unrelated);
  pending.resolve({ resource: { kind: 'clock', id: 'clock', label: 'Clock' } }); const modal = await opening;
  assert.ok(modal?.isConnected); modal.close(); f.resources.destroy();
});

test('identical known resource snapshots leave pending reads and the preview intact; a changed snapshot closes it', async () => {
  const f = fixture(), pending = deferred(), snapshots = new Map(); f.api.journals.resolve = () => pending.promise;
  f.api.clocks = { async state() { return { clocks: [{ id: 'clock', value: 1, segments: 4 }] }; } };
  function feed(value) { const event = new Event('gravewright:resources'); Object.defineProperty(event, 'detail', { value: { module: 'clocks', state: { clocks: [{ id: 'clock', value }] } } }); return event; }
  repeatedResourceEvent(feed(1), snapshots);
  const opening = openResourceLink({ kind: 'clock', id: 'clock' }, { api: f.api, resourceApi: f.api.journals, sourceEvents: snapshots });
  f.window.dispatchEvent(feed(1)); pending.resolve({ resource: { kind: 'clock', id: 'clock', label: 'Clock' } });
  const modal = await opening; assert.ok(modal?.isConnected);
  f.window.dispatchEvent(feed(1)); assert.equal(modal.isConnected, true);
  f.window.dispatchEvent(feed(2)); assert.equal(modal.isConnected, false); f.resources.destroy();
});

test('an api.changed notification invalidates a target even without an active native directory subscription', async () => {
  const f = fixture(), pending = deferred(); f.api.journals.resolve = () => pending.promise;
  const opening = openResourceLink({ kind: 'deck', id: 'deck' }, { api: f.api, resourceApi: f.api.journals });
  const event = new Event('gravewright:api-event'); Object.defineProperty(event, 'detail', { value: { type: 'api.changed', payload: { domain: 'cards' } } }); f.window.dispatchEvent(event);
  pending.resolve({ resource: { kind: 'deck', id: 'deck', label: 'Old private deck' } }); assert.equal(await opening, undefined); f.resources.destroy();
});

test('opaque links react to source-resource grant changes although their original kind is correctly hidden', async () => {
  const f = fixture(), node = f.add({ unavailable: true, key: 'opaque' }), pending = deferred();
  let requestSignal; f.api.journals.state = (_, options) => { requestSignal = options.signal; return pending.promise; };
  const reading = f.resources.refresh(); const event = new Event('gravewright:resources'); Object.defineProperty(event, 'detail', { value: { module: 'clocks', state: { clocks: [{ id: 'clock', visibility: 'players' }] } } });
  f.window.dispatchEvent(event); assert.equal(requestSignal.aborted, true);
  pending.resolve({ journals: [] }); await reading; assert.notEqual(f.host.hidden, true);
  f.api.journals.state = async () => ({ journals: [{ id: 'journal', content_doc: { type: 'gwResourceLink', attrs: { reference: { kind: 'clock', id: 'clock', label: 'Newly shared clock', key: 'opaque' } } } }] });
  await f.resources.refresh(); assert.equal(node.view.dom.textContent, 'Newly shared clock'); f.resources.destroy();
});

test('an items feed redacts only items and a journal remains clickable throughout the scheduled pending refresh', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const f = fixture(), itemRef = { kind: 'item', id: 'item', label: 'Old item', key: 'item-key' },
    questRef = { kind: 'journal', id: 'quest', label: 'Unaffected quest', key: 'quest-key' },
    item = f.add(itemRef), quest = f.add(questRef), pending = deferred();
  let requested = false;
  f.api.journals.state = () => { requested = true; return pending.promise; };
  const event = new Event('gravewright:resources'); Object.defineProperty(event, 'detail', { value: { module: 'items', state: { items: [] } } });
  f.window.dispatchEvent(event);
  assert.equal(item.view.dom.textContent, 'Unavailable resource'); assert.equal(quest.view.dom.textContent, 'Unaffected quest');
  t.mock.timers.tick(120); await tick(); assert.equal(requested, true);
  assert.equal(item.view.dom.textContent, 'Unavailable resource'); assert.equal(quest.view.dom.dataset.resourceState, 'available');
  quest.view.dom.dispatchEvent(new Event('click')); await tick();
  assert.equal(f.calls.find(call => call[0] === 'open')[1].id, 'quest');
  pending.resolve({ journals: [{ id: 'journal', content_doc: { type: 'doc', content: [
    { type: 'gwResourceLink', attrs: { reference: { unavailable: true, key: 'item-key' } } },
    { type: 'gwResourceLink', attrs: { reference: questRef } },
  ] } }] }); await tick();
  assert.equal(item.view.dom.textContent, 'Unavailable resource'); assert.equal(quest.view.dom.textContent, 'Unaffected quest');
  item.attrs.reference = itemRef; item.view.update(item); assert.equal(item.view.dom.textContent, 'Unavailable resource'); f.resources.destroy();
});

test('coalesced resource invalidations retain their union while ownership invalidates every link immediately', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const f = fixture(), item = f.add({ kind: 'item', id: 'item', label: 'Item', key: 'i' }),
    clock = f.add({ kind: 'clock', id: 'clock', label: 'Clock', key: 'c' }),
    journal = f.add({ kind: 'journal', id: 'quest', label: 'Quest', key: 'j' });
  function feed(module) { const event = new Event('gravewright:resources'); Object.defineProperty(event, 'detail', { value: { module, state: {} } }); f.window.dispatchEvent(event); }
  feed('items'); feed('clocks');
  assert.equal(item.view.dom.dataset.resourceState, 'unavailable'); assert.equal(clock.view.dom.dataset.resourceState, 'unavailable');
  assert.equal(journal.view.dom.dataset.resourceState, 'available');
  f.window.dispatchEvent(new Event('gravewright:ownership-changed'));
  assert.equal(journal.view.dom.dataset.resourceState, 'unavailable'); assert.equal(f.calls.some(call => call[0] === 'state'), false); f.resources.destroy();
});
