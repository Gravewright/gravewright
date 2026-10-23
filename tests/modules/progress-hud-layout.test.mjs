import test from 'node:test';
import assert from 'node:assert/strict';
import { clampProgressPosition, mountProgressHudLayout } from '../../gravewright/table/static/gravewright_table/progress-hud-layout.js';

class Element extends EventTarget {
  constructor(document, dataset = {}, box = {}) {
    super(); this.ownerDocument = document; this.dataset = dataset; this.style = {};
    this.box = { left: 20, top: 66, width: 108, height: 180, ...box };
    this.attributes = new Map(); this.children = []; this.textContent = 'Authored title'; this.capture = new Set();
  }
  setAttribute(name, value) { this.attributes.set(name, value); }
  append(child) { child.parent = this; this.children.push(child); }
  contains(child) { return this === child || this.children.some(value => value.contains(child)); }
  querySelectorAll(selector) { return this.children.flatMap(child => [child, ...child.querySelectorAll(selector)]).filter(child => child.matches(selector)); }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
  matches(selector) { return selector === '[data-progress-move-handle]' ? 'progressMoveHandle' in this.dataset
    : selector === '[data-clock-id]' ? 'clockId' in this.dataset : selector === '[data-clue-id]' && 'clueId' in this.dataset; }
  closest(selector) { return this.matches(selector) ? this : this.parent?.closest(selector); }
  focus() { this.focused = true; }
  setPointerCapture(id) { this.capture.add(id); }
  hasPointerCapture(id) { return this.capture.has(id); }
  releasePointerCapture(id) { this.capture.delete(id); }
  getBoundingClientRect() { return { ...this.box,
    left: this.style.left ? parseFloat(this.style.left) : this.box.left,
    top: this.style.top ? parseFloat(this.style.top) : this.box.top,
    width: this.style.width ? parseFloat(this.style.width) : this.box.width };
  }
}
const event = (type, target, values = {}) => {
  const result = new Event(type, { cancelable: true });
  for (const [name, value] of Object.entries({ target, button: 0, isPrimary: true, pointerId: 1, clientX: 40, clientY: 80, ...values }))
    Object.defineProperty(result, name, { value });
  return result;
};
function fixture({ storage = new Map(), profile = 'member-a', campaign = 'campaign-a', kind = 'clock', rawStorage } = {}) {
  const view = new EventTarget(), document = new EventTarget(), writes = [];
  Object.assign(view, { innerWidth: 800, innerHeight: 600, requestAnimationFrame(callback) { view.frame = callback; return 1; },
    cancelAnimationFrame() { view.frame = undefined; }, localStorage: rawStorage || {
      getItem: key => storage.get(key) ?? null, setItem: (key, value) => { writes.push([key, value]); storage.set(key, value); },
    } });
  document.defaultView = view;
  const root = new Element(document, {}, { top: 66, height: 0 });
  const make = (id, x = 20) => {
    const card = new Element(document, { [`${kind}Id`]: id }, { left: x });
    const heading = new Element(document, { progressMoveHandle: '' }); card.append(heading); root.append(card);
    return { card, heading };
  };
  const first = make('one'), second = make('two', 140);
  const controller = new AbortController();
  const layout = mountProgressHudLayout(root, { profileId: profile, campaignId: campaign, kind,
    t: value => 'translated:' + value, signal: controller.signal });
  const down = (entry = first, values) => root.dispatchEvent(event('pointerdown', entry.heading, values));
  const move = (values = {}) => document.dispatchEvent(event('pointermove', first.heading, values));
  const up = (values = {}) => document.dispatchEvent(event('pointerup', first.heading, values));
  const point = entry => ({ x: parseFloat(entry.card.style.left), y: parseFloat(entry.card.style.top) });
  return { view, document, root, first, second, make, controller, layout, storage, writes, down, move, up, point };
}

test('clamping keeps full indicators within the viewport and below the HUD origin', () => {
  assert.deepEqual(clampProgressPosition({ x: 9999, y: -100 }, { width: 108, height: 180 }, { width: 320, height: 568, top: 66 }), { x: 204, y: 66 });
  assert.deepEqual(clampProgressPosition({ x: -100, y: 9999 }, { width: 600, height: 900 }, { width: 320, height: 568, top: 66 }), { x: 8, y: 8 });
});

test('dragging one card persists only its final position, independently from the other card', () => {
  const f = fixture();
  assert.equal(f.writes.length, 0); assert.match(f.first.heading.title, /^translated:Drag/);
  assert.equal(f.first.heading.attributes.get('aria-label'), 'translated:Move indicator: Authored title');
  f.down(); f.move({ clientX: 43, clientY: 80 }); assert.deepEqual(f.point(f.first), { x: 20, y: 66 });
  f.move({ clientX: 200, clientY: 220 });
  assert.deepEqual(f.point(f.first), { x: 180, y: 206 }); assert.deepEqual(f.point(f.second), { x: 140, y: 66 });
  assert.equal(f.writes.length, 0); assert.equal(f.first.card.dataset.progressMoving, '');
  f.up();
  assert.deepEqual(f.writes, [['gravewright.progress-hud.v1.member-a.campaign-a.clock.one', '{"x":180,"y":206}']]);
  assert.equal(f.first.card.dataset.progressMoving, undefined);
  f.layout.destroy();
});

test('tap, right click, other pointers, cancellation and Escape do not store movement', () => {
  const f = fixture();
  f.down(undefined, { button: 2 }); f.move({ clientX: 300 }); assert.deepEqual(f.point(f.first), { x: 20, y: 66 });
  f.down(); f.move({ pointerId: 7, clientX: 300 }); f.up(); assert.equal(f.writes.length, 0);
  for (const cancel of ['pointercancel', 'Escape', 'blur', 'lostpointercapture']) {
    f.down(); f.move({ clientX: 220, clientY: 180 });
    if (cancel === 'Escape') f.document.dispatchEvent(event('keydown', f.first.heading, { key: 'Escape' }));
    else if (cancel === 'blur') f.view.dispatchEvent(new Event('blur'));
    else if (cancel === 'lostpointercapture') f.first.heading.dispatchEvent(new Event(cancel));
    else f.document.dispatchEvent(event(cancel, f.first.heading));
    assert.deepEqual(f.point(f.first), { x: 20, y: 66 }); assert.equal(f.writes.length, 0);
  }
  f.layout.destroy();
});

test('arrow keys move only a focused title and save the translated, member-specific preference', () => {
  const f = fixture({ kind: 'clue' });
  f.root.dispatchEvent(event('keydown', f.first.heading, { key: 'ArrowRight', shiftKey: true }));
  f.root.dispatchEvent(event('keydown', f.first.heading, { key: 'ArrowDown' }));
  assert.deepEqual(f.point(f.first), { x: 30, y: 67 }); assert.equal(f.writes.length, 2);
  f.root.dispatchEvent(event('keydown', f.first.card, { key: 'ArrowRight' }));
  f.root.dispatchEvent(event('keydown', f.first.heading, { key: 'ArrowRight', ctrlKey: true }));
  assert.deepEqual(f.point(f.first), { x: 30, y: 67 }); assert.match(f.writes[0][0], /\.clue\.one$/);
  f.layout.destroy();
});

test('position survives DOM rebuilds and reloads while member, campaign and kind remain isolated', () => {
  const storage = new Map(), f = fixture({ storage });
  f.down(); f.move({ clientX: 240, clientY: 180 }); f.up();
  f.root.children = []; const replacement = f.make('one'); f.layout.refresh();
  assert.deepEqual(f.point(replacement), { x: 220, y: 166 }); f.layout.destroy();
  for (const options of [{}, { profile: 'other-member' }, { campaign: 'other-campaign' }, { kind: 'clue' }]) {
    const next = fixture({ storage, ...options });
    assert.deepEqual(next.point(next.first), Object.keys(options).length ? { x: 20, y: 66 } : { x: 220, y: 166 });
    next.layout.destroy();
  }
});

test('narrow screens keep independent positions and restore desktop positions when expanding back', () => {
  const f = fixture();
  f.down(); f.move({ clientX: 600, clientY: 350 }); f.up();
  const original = f.storage.values().next().value;
  f.view.innerWidth = 320; f.view.innerHeight = 400;
  f.view.dispatchEvent(new Event('resize')); f.view.frame();
  assert.deepEqual(f.point(f.first), { x: 20, y: 140 });
  assert.equal(f.writes.length, 1); assert.equal(f.storage.values().next().value, original);
  f.root.dispatchEvent(event('keydown', f.first.heading, { key: 'ArrowRight', shiftKey: true }));
  assert.equal(f.writes.length, 2); assert.match(f.writes[1][0], /\.clock\.one\.compact$/);
  f.view.innerWidth = 800; f.view.innerHeight = 600; f.layout.refresh();
  assert.deepEqual(f.point(f.first), { x: 580, y: 336 });
  f.view.innerWidth = 320; f.view.innerHeight = 400; f.layout.refresh();
  assert.deepEqual(f.point(f.first), { x: 30, y: 140 }); f.layout.destroy();
});

test('stored positions are clamped when resizing within a single viewport layout', () => {
  const f = fixture();
  f.down(); f.move({ clientX: 600, clientY: 350 }); f.up();
  const before = f.storage.values().next().value;
  f.view.innerWidth = 600; f.view.innerHeight = 400; f.layout.refresh();
  assert.deepEqual(f.point(f.first), { x: 484, y: 212 });
  assert.equal(f.writes.length, 1); assert.equal(f.storage.values().next().value, before);
  f.layout.destroy();
});

test('compact default clocks stack without overlap when authored titles have different heights', () => {
  const f = fixture();
  f.view.innerWidth = 320; f.view.innerHeight = 740;
  f.first.card.box.height = 168; f.second.card.box.height = 114;
  f.layout.refresh();
  assert.deepEqual(f.point(f.first), { x: 20, y: 492 });
  assert.deepEqual(f.point(f.second), { x: 140, y: 370 });
  assert.equal(f.point(f.second).y + f.second.card.box.height + 8, f.point(f.first).y);
  assert.equal(f.writes.length, 0);
  f.layout.destroy();
});

test('compact clock defaults clear the visible dock while retaining individually saved positions', () => {
  const f = fixture();
  f.view.innerWidth = 320; f.view.innerHeight = 740;
  f.first.card.box.height = 168; f.second.card.box.height = 114;
  f.document.querySelector = selector => selector === '.game-dock'
    ? { getBoundingClientRect: () => ({ top: 645, width: 300, height: 87 }) } : undefined;
  f.layout.refresh();
  assert.deepEqual(f.point(f.first), { x: 20, y: 469 });
  assert.deepEqual(f.point(f.second), { x: 140, y: 347 });
  assert.equal(f.point(f.first).y + f.first.card.box.height, 645 - 8);
  assert.equal(f.writes.length, 0);
  f.storage.set('gravewright.progress-hud.v1.member-a.campaign-a.clock.one.compact', '{"x":30,"y":500}');
  f.layout.refresh();
  assert.deepEqual(f.point(f.first), { x: 30, y: 500 });
  assert.equal(f.writes.length, 0); f.layout.destroy();
});

test('dock growth repositions default clocks without overwriting saved positions and unsubscribes on close', () => {
  const f = fixture();
  f.view.innerWidth = 320; f.view.innerHeight = 740;
  let dockTop = 645;
  f.document.querySelector = selector => selector === '.game-dock'
    ? { getBoundingClientRect: () => ({ top: dockTop, width: 300, height: 740 - dockTop }) } : undefined;
  f.storage.set('gravewright.progress-hud.v1.member-a.campaign-a.clock.two.compact', '{"x":140,"y":300}');
  f.layout.refresh();
  assert.deepEqual(f.point(f.first), { x: 20, y: 457 });
  assert.deepEqual(f.point(f.second), { x: 140, y: 300 });
  dockTop = 603;
  f.view.dispatchEvent(new Event('gravewright:dock-resize'));
  const scheduled = f.view.frame;
  f.view.dispatchEvent(new Event('resize'));
  assert.equal(f.view.frame, scheduled);
  scheduled();
  assert.deepEqual(f.point(f.first), { x: 20, y: 415 });
  assert.deepEqual(f.point(f.second), { x: 140, y: 300 });
  assert.equal(f.writes.length, 0);
  f.view.dispatchEvent(new Event('gravewright:dock-resize'));
  f.layout.destroy();
  assert.equal(f.view.frame, undefined);
  f.view.dispatchEvent(new Event('gravewright:dock-resize'));
  assert.equal(f.view.frame, undefined);
});

test('malformed or blocked local storage leaves dragging functional', () => {
  for (const raw of ['null', '[]', '{"x":"40","y":80}', '{"x":1e30,"y":80}', 'x'.repeat(300)]) {
    const storage = new Map([['gravewright.progress-hud.v1.member-a.campaign-a.clock.one', raw]]), f = fixture({ storage });
    assert.deepEqual(f.point(f.first), { x: 20, y: 66 }); f.layout.destroy();
  }
  const f = fixture({ rawStorage: { getItem() { throw new Error('Blocked'); }, setItem() { throw new Error('Blocked'); } } });
  f.down(); f.move({ clientX: 200, clientY: 200 }); f.up(); assert.deepEqual(f.point(f.first), { x: 180, y: 186 });
  f.layout.refresh(); assert.deepEqual(f.point(f.first), { x: 180, y: 186 }); f.layout.destroy();
});

test('abort during drag or scheduled resize disposes work without persisting or reacting later', () => {
  const f = fixture();
  f.down(); f.move({ clientX: 200, clientY: 200 }); f.view.dispatchEvent(new Event('resize'));
  f.controller.abort(); f.move({ clientX: 400, clientY: 400 }); f.up();
  assert.equal(f.writes.length, 0); assert.equal(f.view.frame, undefined); assert.equal(f.first.card.style.position, '');
});

test('description/edit title semantics survive positioning and a tap stays a native click', () => {
  const f = fixture(), heading = f.first.heading;
  heading.dataset.progressDetailsTrigger = 'clock';
  heading.setAttribute('role', 'button'); heading.setAttribute('aria-label', 'translated:Clock details: Authored title');
  heading.title = 'translated:Double-click for details';
  f.layout.refresh(); f.layout.refresh();
  assert.equal(heading.attributes.get('role'), 'button');
  assert.equal(heading.attributes.get('aria-label'), 'translated:Clock details: Authored title');
  assert.match(heading.attributes.get('aria-keyshortcuts'), /Enter Space.*ArrowLeft/);
  assert.equal(heading.title.split('translated:Drag').length, 2);
  const down = event('pointerdown', heading), up = event('pointerup', heading);
  f.root.dispatchEvent(down); f.document.dispatchEvent(up);
  assert.equal(down.defaultPrevented, false); assert.equal(up.defaultPrevented, false);
  assert.equal(heading.capture.size, 0); assert.equal(f.writes.length, 0);
  f.layout.destroy();
});

test('a completed drag suppresses its accidental double-click but later title activation works', () => {
  const f = fixture();
  f.down(); f.move({ clientX: 120, clientY: 160 });
  const up = event('pointerup', f.first.heading); f.document.dispatchEvent(up);
  const click = event('dblclick', f.first.heading); f.root.dispatchEvent(click);
  assert.equal(click.defaultPrevented, true);
  const later = event('dblclick', f.first.heading);
  Object.defineProperty(later, 'timeStamp', { value: up.timeStamp + 351 });
  f.root.dispatchEvent(later); assert.equal(later.defaultPrevented, false);
  assert.equal(f.writes.length, 1); f.layout.destroy();
});
