import test from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';
import { newMindmapDocument } from '../../gravewright/table/static/gravewright_table/mindmap-model.js';

globalThis.window = new EventTarget();
const hooks = registerHooks({ resolve(specifier, context, next) {
  if (specifier === '/static/gravewright_modules/i18n.js') return { url: new URL('../../gravewright/modules/static/gravewright_modules/i18n.js', import.meta.url).href, shortCircuit: true };
  return next(specifier, context);
}, load(url, context, next) {
  if (url.endsWith('/gravewright_table/modal.js')) return { format: 'module', shortCircuit: true, source: `export function mountModal(modal, options = {}) {
    modal.options = options; document.body.append(modal); modal.isConnected = true;
    modal.close = () => { if (!modal.isConnected) return; modal.isConnected = false; modal.dispatchEvent(new Event('close')); };
    return modal;
  }` };
  return next(url, context);
} });
const { mountMindmaps } = await import('../../gravewright/table/static/gravewright_table/mindmaps.js');
const { resourceLabel, loadResourcePreview, openResourceLink } = await import('../../gravewright/table/static/gravewright_table/resource-links.js');
hooks.deregister();

class Element extends EventTarget {
  constructor(tag, document) {
    super(); Object.assign(this, { localName: tag, ownerDocument: document, children: [], dataset: {}, style: { setProperty() {} }, attributes: new Map(), value: '', isConnected: true, clientWidth: 800, clientHeight: 500 });
    const classes = new Set(); this.classList = { add: name => classes.add(name), toggle: (name, value) => value ? classes.add(name) : classes.delete(name) };
  }
  append(...children) { children.forEach(child => { child.parent = this; this.children.push(child); }); }
  prepend(child) { child.parent = this; this.children.unshift(child); }
  contains(element) { return element === this || this.children.some(child => child.contains(element)); }
  replaceChildren(...children) { if (this.children.some(child => child.contains(this.ownerDocument.activeElement))) this.ownerDocument.activeElement = this.ownerDocument.body; this.children = []; this.append(...children); }
  matches(selector) {
    if (selector === '[contenteditable]') return false;
    const attribute = selector.match(/^\[([^=\]]+)(?:="?([^\]"]+)"?)?\]$/);
    if (attribute) {
      const [, key, value] = attribute;
      const actual = key.startsWith('data-') ? this.dataset[key.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] : this[key] ?? this.attributes.get(key);
      return value === undefined ? actual !== undefined : String(actual) === value;
    }
    return selector === this.localName;
  }
  closest(selector) { return selector.split(',').some(value => this.matches(value)) ? this : this.parent?.closest(selector); }
  querySelectorAll(selector) { return all(this).slice(1).filter(element => selector.split(',').some(value => element.matches(value))); }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
  setAttribute(key, value) { this.attributes.set(key, String(value)); }
  removeAttribute(key) { this.attributes.delete(key); }
  focus() { this.ownerDocument.activeElement = this; }
  reportValidity() { return true; }
  getBoundingClientRect() { return { left: 0, top: 0, width: this.clientWidth, height: this.clientHeight }; }
}
const all = root => [root, ...root.children.flatMap(all)], find = (root, predicate) => all(root).find(predicate);
const tick = () => new Promise(setImmediate);
async function click(element) { assert.ok(element); element.dispatchEvent(new Event('click')); await tick(); }
function fixture({ editable = true } = {}) {
  const doc = { createElement: tag => new Element(tag, doc), createElementNS: (_ns, tag) => new Element(tag, doc) };
  doc.body = doc.createElement('body'); doc.activeElement = doc.body; globalThis.document = doc;
  globalThis.Option = class extends Element { constructor(label, value) { super('option', doc); this.textContent = label; this.value = value; } };
  const root = doc.createElement('div'), calls = [], scope = new AbortController();
  let row = { id: 'map', name: 'Authored map', visibility: 'gm', version: 3, canEdit: editable, canConfigure: false,
    document: newMindmapDocument('Root topic', 'root') };
  const state = () => ({ mindmaps: [structuredClone(row)], canManage: false, editors: [] });
  const api = { mindmaps: {
    async state() { calls.push(['state']); return state(); },
    async read(payload) { calls.push(['read', payload]); return structuredClone(row); },
    async update(payload, options) { calls.push(['update', structuredClone(payload), options]); row = { ...row, name: payload.name, document: structuredClone(payload.document), version: row.version + 1 }; return { id: row.id }; },
    async resolve({ reference }) { return { ...reference, label: 'Verified resource' }; },
  } };
  const component = mountMindmaps(root, { api, t: key => key, signal: scope.signal }); component.update(state());
  const editor = () => find(doc.body, element => element.dataset.mindmapEditor === 'map' && element.isConnected);
  const action = label => find(editor(), element => element.localName === 'button' && element.textContent === label);
  return { doc, root, api, component, calls, scope, editor, action, state, get row() { return row; }, set row(value) { row = value; } };
}

test('native player editor sends only name/document and preserves keyboard topic selection during child creation', async () => {
  const f = fixture(); assert.equal(f.calls.length, 0); await f.component.open('map');
  await click(f.action('Add child topic'));
  const selected = find(f.editor(), element => element.dataset.mindmapNodeId && element.dataset.mindmapNodeId !== 'root');
  assert.equal(f.doc.activeElement, selected);
  const label = f.editor().querySelector('[name="label"]'); label.value = '<img src=x>Authored child'; label.focus(); label.dispatchEvent(new Event('change'));
  assert.equal(f.doc.activeElement.name, 'label');
  await click(f.action('Save mind map')); await tick();
  const payload = f.calls.find(call => call[0] === 'update')[1];
  assert.deepEqual(Object.keys(payload).sort(), ['document', 'id', 'name', 'version']); assert.equal(payload.version, 3);
  assert.equal(payload.document.nodes[1].label, '<img src=x>Authored child'); assert.equal(f.row.version, 4);
  assert.equal(all(f.editor()).some(element => element.localName === 'img'), false); f.component.destroy();
});

test('read-only maps allow viewing while all editing controls remain locked and issue no command', async () => {
  const f = fixture({ editable: false }); await f.component.open('map');
  assert.equal(f.action('Add root topic').disabled, true); assert.equal(f.action('Save mind map').disabled, true);
  assert.equal(f.editor().querySelector('[name="notes"]').disabled, true);
  await click(f.action('Add root topic')); assert.equal(f.calls.some(call => call[0] === 'update'), false);
  assert.equal(all(f.editor()).filter(element => element.dataset.mindmapNodeId).length, 1); f.component.destroy();
});

test('concurrent map versions preserve the local draft, disable saving and offer explicit reload', async () => {
  const f = fixture(); await f.component.open('map');
  const notes = f.editor().querySelector('[name="notes"]'); notes.value = 'Local draft'; notes.dispatchEvent(new Event('change'));
  f.row = { ...f.row, version: 4 }; f.component.update(f.state());
  assert.equal(f.editor().querySelector('[name="notes"]').value, 'Local draft');
  assert.equal(f.action('Save mind map').disabled, true); assert.equal(f.action('Reload saved map').hidden, false);
  assert.equal(f.calls.some(call => call[0] === 'update'), false); f.component.destroy();
});

test('a same-version realtime feed cannot discard text entered before blur or change', async () => {
  const f = fixture(); await f.component.open('map');
  const original = f.editor().querySelector('[name="notes"]'); original.focus(); original.value = 'Typing before blur'; original.dispatchEvent(new Event('input'));
  assert.equal(f.action('Save mind map').disabled, false);
  f.component.update(f.state());
  const replacement = f.editor().querySelector('[name="notes"]');
  assert.equal(replacement.value, 'Typing before blur'); assert.equal(f.doc.activeElement, replacement);
  original.dispatchEvent(new Event('change')); await click(f.action('Save mind map')); await tick();
  assert.equal(f.calls.find(call => call[0] === 'update')[1].document.nodes[0].notes, 'Typing before blur');
  f.component.destroy();
});

test('a redundant change after input does not replace the topic that just received keyboard focus', async () => {
  const f = fixture(); await f.component.open('map');
  const notes = f.editor().querySelector('[name="notes"]'); notes.focus(); notes.value = 'Draft'; notes.dispatchEvent(new Event('input'));
  const topic = find(f.editor(), element => element.dataset.mindmapNodeId === 'root'); topic.focus();
  notes.dispatchEvent(new Event('change'));
  assert.equal(f.doc.activeElement, topic); assert.equal(find(f.editor(), element => element.dataset.mindmapNodeId === 'root'), topic);
  f.component.destroy();
});

test('resource permission refresh redacts stale labels through dirty drafts and Undo without losing opaque links', async () => {
  const f = fixture(); f.row.document.nodes[0].links = [{ kind: 'clock', id: 'secret', label: 'Secret clock label', key: 'opaque' }];
  f.component.update(f.state()); await f.component.open('map');
  const notes = f.editor().querySelector('[name="notes"]'); notes.value = 'Keep my notes'; notes.dispatchEvent(new Event('change'));
  f.row.document.nodes[0].links = [{ unavailable: true, key: 'opaque' }]; f.component.update(f.state());
  assert.equal(all(f.editor()).some(element => element.textContent === 'Secret clock label'), false);
  assert.equal(f.editor().querySelector('[name="notes"]').value, 'Keep my notes');
  await click(f.action('Undo')); assert.equal(all(f.editor()).some(element => element.textContent === 'Secret clock label'), false);
  await click(f.action('Redo')); await click(f.action('Save mind map')); await tick();
  const payload = f.calls.find(call => call[0] === 'update')[1];
  assert.deepEqual(payload.document.nodes[0].links, [{ unavailable: true, key: 'opaque' }]);
  assert.equal(payload.document.nodes[0].notes, 'Keep my notes'); f.component.destroy();
});

test('revoking map access destroys the editor and aborting a late read cannot reopen private content', async () => {
  const f = fixture(); await f.component.open('map'); const modal = f.editor();
  f.component.update({ mindmaps: [], canManage: false }); assert.equal(modal.isConnected, false);
  let finish; f.api.mindmaps.read = () => new Promise(resolve => { finish = resolve; });
  const pending = f.component.open('map'); f.scope.abort(); finish(f.row); await pending;
  assert.equal(f.editor(), undefined); assert.equal(f.root.children.length, 0);
});

test('a newer authorization feed supersedes an already pending map read', async () => {
  const f = fixture(); let finish;
  f.api.mindmaps.read = () => new Promise(resolve => { finish = resolve; });
  const pending = f.component.open('map'); f.component.update({ mindmaps: [], canManage: false }); finish(f.row); await pending;
  assert.equal(f.editor(), undefined); f.component.destroy();
});

test('resource preview uses native project/template payload names and opaque compendium addresses', async () => {
  const calls = [], api = {
    mapBuilder: { async read(payload) { calls.push(['project', payload]); return { project: { document: { notes: 'Project description' } } }; } },
    blueprints: { async readTemplate(payload) { calls.push(['template', payload]); return { template: { description: 'Template description' } }; } },
    compendiums: { async read(payload) { calls.push(['entry', payload]); return { data: { description: 'Entry body' } }; } },
  };
  await loadResourcePreview({ kind: 'map-builder-project', id: 'project' }, { api });
  assert.equal((await loadResourcePreview({ kind: 'blueprint-template', id: 'template' }, { api })).text, 'Template description');
  assert.equal((await loadResourcePreview({ kind: 'compendium-entry', id: 'native:pack/opaque-entry' }, { api })).text, 'Entry body');
  assert.deepEqual(calls, [['project', { projectId: 'project' }], ['template', { templateId: 'template' }], ['entry', { packId: 'native:pack', id: 'opaque-entry' }]]);
});

test('folder, progress, card and audio previews read useful native data and owner links read their authorized document', async () => {
  const api = {
    actors: { async state() { return { actors: [{ id: 'actor', folderId: 'folder', name: 'Child character' }], folders: [{ id: 'folder', name: 'Folder' }] }; } },
    clocks: { async state() { return { clocks: [{ id: 'clock', value: 2, segments: 6 }] }; } },
    cards: { async state() { return { cards: [{ id: 'card', name: 'Visible card', frontUrl: '/game/cards/card/card/front' }] }; } },
    audio: { async state() { return { tracks: [{ id: 'audio', src: '/game/audio/track/audio' }] }; } },
    journals: { async state() { return { journals: [{ id: 'journal', sections: [{ id: 'page', content: { text: 'Authorized page body' } }] }] }; } },
  };
  assert.equal((await loadResourcePreview({ kind: 'actor-folder', id: 'folder' }, { api })).text, 'Child character');
  assert.equal((await loadResourcePreview({ kind: 'clock', id: 'clock' }, { api })).progress, '2/6');
  assert.equal((await loadResourcePreview({ kind: 'card', id: 'card' }, { api })).image, '/game/cards/card/card/front');
  const audio = await loadResourcePreview({ kind: 'track', id: 'audio' }, { api });
  assert.equal(audio.image, null); assert.equal(audio.audio, '/game/audio/track/audio');
  assert.equal((await loadResourcePreview({ kind: 'journal-asset', id: 'attachment', ownerReference: { kind: 'journal-page', id: 'journal', pageId: 'page' } }, { api })).text, 'Authorized page body');
  assert.equal(resourceLabel({ label: 'Authored title' }, key => 'translated:' + key), 'Authored title');
  assert.equal(resourceLabel({ label: 'Generic', labelKey: 'Tokens' }, key => 'translated:' + key), 'translated:Tokens');
  assert.equal(resourceLabel({ unavailable: true }, key => 'translated:' + key), 'translated:Unavailable resource');
});

test('a source invalidation closes partial-content previews and a late private read cannot repopulate them', async () => {
  const f = fixture(); f.doc.getElementById = () => ({ dataset: { role: 'player', tableId: 'campaign' } });
  let finish;
  f.api.journals = { state: () => new Promise(resolve => { finish = resolve; }) };
  const modal = await openResourceLink({ kind: 'journal', id: 'journal' }, { api: f.api });
  assert.equal(modal.isConnected, true); assert.ok(finish);
  const event = new Event('gravewright:resources'); event.detail = { module: 'journals' }; window.dispatchEvent(event);
  assert.equal(modal.isConnected, false);
  finish({ journals: [{ id: 'journal', content: 'Earlier private page body' }] }); await tick();
  assert.equal(all(modal).some(element => element.textContent === 'Earlier private page body'), false);
  f.component.destroy();
});

test('native Escape close checks cancel an active node drag before considering unsaved prompts', async () => {
  const f = fixture(); Object.setPrototypeOf(f.doc, new EventTarget()); await f.component.open('map');
  const modal = f.editor(), canvas = find(modal, element => element.dataset.mindmapCanvas !== undefined);
  const topic = find(modal, element => element.dataset.mindmapNodeId === 'root');
  const down = Object.assign(new Event('pointerdown', { cancelable: true }), { button: 0, isPrimary: true, pointerId: 1, clientX: 50, clientY: 50 });
  Object.defineProperty(down, 'target', { value: topic }); canvas.dispatchEvent(down);
  f.doc.dispatchEvent(Object.assign(new Event('pointermove', { cancelable: true }), { pointerId: 1, clientX: 150, clientY: 120 }));
  assert.notEqual(topic.style.left, '0px');
  assert.equal(modal.options.canClose(), false); assert.equal(modal.isConnected, true);
  const restored = find(modal, element => element.dataset.mindmapNodeId === 'root'); assert.equal(restored.style.left, '0px');
  assert.equal(f.action('Save mind map').disabled, true); f.component.destroy();
});

test('Enter and F2 move keyboard focus from topics into editable or readonly details without creating topics', async () => {
  for (const editable of [true, false]) {
    const f = fixture({ editable }); await f.component.open('map');
    for (const key of ['Enter', 'F2']) {
      const topic = find(f.editor(), element => element.dataset.mindmapNodeId === 'root'); topic.focus();
      const event = Object.assign(new Event('keydown', { cancelable: true }), { key });
      Object.defineProperty(event, 'target', { value: topic }); f.editor().dispatchEvent(event);
      assert.equal(event.defaultPrevented, true);
      if (editable) assert.equal(f.doc.activeElement, f.editor().querySelector('[name="label"]'));
      else {
        assert.equal(f.doc.activeElement.className, 'mindmap-editor__inspector');
        assert.equal(f.editor().querySelector('[name="label"]').disabled, true);
      }
      assert.equal(all(f.editor()).filter(element => element.dataset.mindmapNodeId).length, 1);
    }
    f.component.destroy();
  }
});
