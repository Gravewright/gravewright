import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../../gravewright/web/static/gravewright_web/windows.js', import.meta.url), 'utf8');
const translatorUrl = new URL('../../gravewright/modules/static/gravewright_modules/i18n.js', import.meta.url).href;
// Run the actual browser controller, adapting only its static URL and exposing
// its startup promise. Placement, persistence and event handlers are unchanged.
const executable = source.replace("'/static/gravewright_modules/i18n.js'", JSON.stringify(translatorUrl))
  .replace('(async () => {', 'export default (async () => {');
let sequence = 0;

class Classes extends Set {
  contains(name) { return this.has(name); }
  remove(...names) { for (const name of names) this.delete(name); }
  toggle(name, force = !this.has(name)) { force ? this.add(name) : this.delete(name); return force; }
}
class Target extends EventTarget {
  listeners = new Map();
  addEventListener(name, callback, options) { super.addEventListener(name, callback, options); this.listeners.set(callback, name); }
  removeEventListener(name, callback, options) { super.removeEventListener(name, callback, options); this.listeners.delete(callback); }
}
const datasetKey = name => name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
class Element extends Target {
  constructor(document, tag = 'aside', classes = '', box = {}) {
    super(); this.ownerDocument = document; this.tagName = tag.toUpperCase(); this.className = classes;
    this.dataset = {}; this.attributes = new Map(); this.children = []; this.isConnected = true; this.hidden = false;
    this.style = Object.fromEntries(['position','width','height','left','top','right','bottom','transform','zIndex'].map(name => [name, '']));
    this.box = { left: 20, top: 47, width: 420, height: 500, ...box };
  }
  set className(value) { this.classList = new Classes(value.split(' ').filter(Boolean)); }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return name.startsWith('data-') ? this.dataset[datasetKey(name)] ?? this.attributes.get(name) : this.attributes.get(name); }
  hasAttribute(name) { return this.getAttribute(name) !== undefined; }
  toggleAttribute(name) { const on = !this.hasAttribute(name); on ? this.setAttribute(name, '') : this.attributes.delete(name); return on; }
  matches(selector) {
    if (selector.startsWith('.')) return this.classList.has(selector.slice(1));
    const attribute = selector.match(/^\[([^=\]]+)(?:=([^\]]+))?\]$/);
    return attribute ? this.hasAttribute(attribute[1]) && (attribute[2] === undefined || this.getAttribute(attribute[1]) === attribute[2])
      : this.tagName.toLowerCase() === selector;
  }
  closest(selector) { return selector.split(',').some(value => this.matches(value)) ? this : this.parent?.closest(selector); }
  querySelectorAll(selector) { return this.children.flatMap(child => [child, ...child.querySelectorAll('*')])
    .filter(child => selector === '*' || selector.split(',').some(value => child.matches(value))); }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
  append(child) { this.children.push(child); child.parent = this; }
  insertBefore(child, before) { this.children = this.children.filter(value => value !== child); this.children.splice(this.children.indexOf(before), 0, child); child.parent = this; }
  remove() { this.isConnected = false; if (this.parent) this.parent.children = this.parent.children.filter(value => value !== this); }
  getClientRects() { return this.isConnected && !this.hidden ? [this.getBoundingClientRect()] : []; }
  getBoundingClientRect() {
    const number = (key, fallback) => this.style[key] ? Number.parseFloat(this.style[key]) : fallback;
    const left = number('left', this.box.left), top = number('top', this.box.top), width = number('width', this.box.width), height = number('height', this.box.height);
    return { x: left, y: top, left, top, width, height, right: left + width, bottom: top + height };
  }
  get offsetWidth() { return this.getBoundingClientRect().width; }
}
const pointer = (type, target, values = {}) => {
  const event = new Event(type, { cancelable: true });
  for (const [name, value] of Object.entries({ target, button: 0, pointerId: 1, clientX: 40, clientY: 80, ...values }))
    Object.defineProperty(event, name, { value });
  return event;
};

async function fixture({ bounded = true, saved, width = 1200, height = 900, menubar = 58, box } = {}) {
  const doc = new Target(), view = new Target(), mutations = [], resizes = [], writes = [];
  Object.assign(view, { innerWidth: width, innerHeight: height, getComputedStyle: () => ({ zIndex: '7' }), gravewrightLocale: { id: 'en', messages: {} } });
  doc.defaultView = view;
  doc.documentElement = new Element(doc, 'html');
  const table = new Element(doc, 'main'); table.dataset = { profileId: 'member', tableId: 'campaign' };
  const bar = new Element(doc, 'header', 'game-menubar', { top: 0, height: menubar });
  const panel = new Element(doc, 'aside', 'game-panel game-panel--visibility', box);
  panel.dataset.movable = ''; panel.dataset.windowKey = 'visibility';
  if (bounded) panel.dataset.windowTopBoundary = '.game-menubar';
  const header = new Element(doc, 'header'), controls = new Element(doc, 'div'), nativeMinimize = new Element(doc, 'button');
  nativeMinimize.dataset.visibilityAction = 'minimize'; controls.append(nativeMinimize); header.append(controls); panel.append(header);
  const panels = [panel];
  doc.createElement = tag => new Element(doc, tag);
  doc.getElementById = () => null;
  doc.querySelector = selector => selector === '#table-workspace' ? table : selector === '.game-menubar' ? bar : null;
  doc.querySelectorAll = selector => selector === '[data-movable]' ? panels.filter(value => value.isConnected && value.ownerDocument === doc) : [];
  const storage = new Map(saved ? [['gravewright.windows.v1.member.campaign', JSON.stringify([['visibility', saved]])]] : []);
  Object.assign(globalThis, { document: doc, window: view, localStorage: {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => { storage.set(key, value); writes.push({ key, value: JSON.parse(value) }); },
  }, MutationObserver: class {
    constructor(callback) { this.callback = callback; mutations.push(this); }
    observe(target) { this.target = target; }
    disconnect() { this.disconnected = true; }
  }, ResizeObserver: class {
    constructor(callback) { this.callback = callback; resizes.push(this); }
    observe(target) { this.target = target; }
    disconnect() { this.disconnected = true; }
  } });
  const module = await import('data:text/javascript;base64,' + Buffer.from(executable).toString('base64') + '#fixture=' + ++sequence);
  await module.default;
  const sync = () => mutations.find(observer => observer.target === doc.documentElement).callback();
  return { doc, view, bar, panel, header, storage, writes, mutations, resizes, sync,
    resize(nextWidth, nextHeight, nextMenubar) { view.innerWidth = nextWidth; view.innerHeight = nextHeight; if (nextMenubar !== undefined) bar.box.height = nextMenubar; view.dispatchEvent(new Event('resize')); },
    drag(y) { const bounds = panel.getBoundingClientRect(); header.dispatchEvent(pointer('pointerdown', header, { clientX: bounds.left + 20, clientY: bounds.top + 15 })); doc.dispatchEvent(pointer('pointermove', header, { clientY: y + 15 })); },
    stop() { doc.dispatchEvent(pointer('pointerup', header)); },
    destroy() { for (const value of panels) value.isConnected = false; sync(); },
  };
}

test('first opening clears the menubar while preserving automatic dimensions as mode content grows', async () => {
  const f = await fixture({ box: { height: 139 } });
  assert.equal(f.panel.getBoundingClientRect().top, 66);
  assert.equal(f.panel.getBoundingClientRect().height, 139);
  assert.equal(f.panel.style.width, '');
  assert.equal(f.panel.style.height, '');
  f.panel.box.height = 500;
  f.resizes.find(observer => !observer.disconnected).callback();
  assert.equal(f.panel.getBoundingClientRect().height, 500);
  assert.equal(f.panel.getBoundingClientRect().top, 66);
  assert.equal(f.panel.style.width, '');
  assert.equal(f.panel.style.height, '');
  assert.equal(f.writes.length, 0);
  f.destroy();
});

test('restoring a desktop layout on mobile keeps the complete panel below the taller menubar', async () => {
  const f = await fixture({ width: 320, height: 600, menubar: 96, saved: { x: 800, y: 47, width: 420, height: 700 } });
  assert.deepEqual(f.panel.getBoundingClientRect(), { x: 8, y: 104, left: 8, top: 104, width: 304, height: 488, right: 312, bottom: 592 });
  assert.equal(f.writes.length, 0, 'Restoring a layout must not silently replace the saved preference');
  f.destroy();
});

test('viewport resize and reset use the current boundary instead of retaining an inline desktop top', async () => {
  const f = await fixture({ saved: { x: 600, y: 200, width: 420, height: 700 } });
  f.resize(320, 568, 96);
  assert.equal(f.panel.getBoundingClientRect().top, 104);
  assert.equal(f.panel.getBoundingClientRect().height, 456);
  assert.equal(f.panel.getBoundingClientRect().width, 304);
  f.panel.querySelector('[data-window-action=reset]').onclick();
  assert.equal(f.panel.getBoundingClientRect().top, 104);
  assert.equal(f.panel.getBoundingClientRect().bottom, 560);
  assert.deepEqual(f.writes.at(-1).value, []);
  f.destroy();
});

test('dragging an opted-in panel clamps the title below the menubar and saves only on release', async () => {
  const f = await fixture();
  f.drag(-200);
  assert.equal(f.panel.getBoundingClientRect().top, 66);
  assert.equal(f.writes.length, 0);
  f.stop();
  assert.equal(f.writes.length, 1);
  assert.equal(f.writes[0].value[0][1].y, 66);
  assert.equal(f.header.classList.has('gw-move-handle--active'), false);
  assert.equal([...f.doc.listeners.values()].includes('pointermove'), false);
  f.destroy();
});

test('returning from a detached document reapplies the current boundary without restoring an obsolete preference', async () => {
  const f = await fixture({ saved: { x: 100, y: 47, width: 420, height: 500 } });
  f.panel.ownerDocument = { defaultView: new Target() }; f.sync();
  assert.equal([...f.view.listeners.values()].includes('resize'), false);
  f.panel.style.top = '47px'; f.bar.box.height = 96;
  f.panel.ownerDocument = f.doc; f.sync();
  assert.equal(f.panel.getBoundingClientRect().top, 104);
  assert.equal([...f.view.listeners.values()].filter(name => name === 'resize').length, 1);
  f.destroy();
  assert.equal([...f.view.listeners.values()].includes('resize'), false);
  assert(f.resizes.every(observer => observer.disconnected));
});

test('windows without the opt-in retain their saved position and existing zero-top drag boundary', async () => {
  const f = await fixture({ bounded: false, menubar: 96, saved: { x: 100, y: 47, width: 420, height: 300 } });
  assert.equal(f.panel.getBoundingClientRect().top, 47);
  f.drag(-200); f.stop();
  assert.equal(f.panel.getBoundingClientRect().top, 0);
  f.resize(320, 568, 120);
  assert.equal(f.panel.getBoundingClientRect().top, 8);
  assert.equal(f.panel.getBoundingClientRect().height, 300);
  f.destroy();
});
