import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../../gravewright/table/static/gravewright_table/combat-panel.js', import.meta.url), 'utf8');

class Events {
  listeners = new Map();
  addEventListener(type, handler, options) {
    const entries = this.listeners.get(type) || [];
    entries.push({handler, capture: options === true || options?.capture === true});
    this.listeners.set(type, entries);
  }
  removeEventListener(type, handler, options) {
    const capture = options === true || options?.capture === true;
    this.listeners.set(type, (this.listeners.get(type) || []).filter(entry => entry.handler !== handler || entry.capture !== capture));
  }
  deliver(type, event, capture = false) {
    for (const entry of [...(this.listeners.get(type) || [])]) if (entry.capture === capture) entry.handler(event);
  }
  get listenerCount() {return [...this.listeners.values()].reduce((count, entries) => count + entries.length, 0);}
}

const kebab = value => value.replace(/[A-Z]/g, char => '-' + char.toLowerCase());
function matches(node, selector) {
  if (selector.startsWith('.')) return node.className.split(' ').includes(selector.slice(1));
  if (selector.startsWith('#')) return node.id === selector.slice(1);
  if (selector.startsWith('[')) {
    const attr = selector.slice(1, -1);
    return node.hasAttribute(attr);
  }
  return node.tagName === selector;
}
class Element extends Events {
  constructor(doc, tag) {
    super();this.ownerDocument = doc;this.tagName = tag;this.children = [];this.attributes = {};
    this.dataset = {};this.style = {};this.className = '';this.disabled = false;this.hidden = false;this.open = false;this._text = '';
    this.scrollTop = 0;this.scrollLeft = 0;
    this.classList = {add: (...names) => {this.className = [...new Set([...this.className.split(' ').filter(Boolean), ...names])].join(' ');},
      toggle: (name, on) => {const names = new Set(this.className.split(' ').filter(Boolean));if (on) names.add(name);else names.delete(name);this.className = [...names].join(' ');}};
  }
  get isConnected() {return this === this.ownerDocument.body || !!this.parentElement?.isConnected;}
  get textContent() {return this._text + this.children.map(child => child.textContent).join('');}
  set textContent(value) {this._text = String(value);this.clear();}
  set innerHTML(value) {assert.equal(value, '');this.clear();this._text = '';}
  clear() {for (const child of this.children) child.parentElement = null;this.children = [];}
  append(...children) {for (const child of children) this.appendChild(child);}
  appendChild(child) {child.parentElement = this;this.children.push(child);return child;}
  remove() {if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(child => child !== this);this.parentElement = null;}
  setAttribute(name, value) {this.attributes[name] = String(value);}
  getAttribute(name) {return this.attributes[name] ?? null;}
  removeAttribute(name) {delete this.attributes[name];}
  hasAttribute(name) {return name in this.attributes || Object.keys(this.dataset).some(key => 'data-' + kebab(key) === name);}
  querySelectorAll(selector) {return this.children.flatMap(child => [...(matches(child, selector) ? [child] : []), ...child.querySelectorAll(selector)]);}
  querySelector(selector) {return this.querySelectorAll(selector)[0] || null;}
  closest(selector) {return matches(this, selector) ? this : this.parentElement?.closest(selector) || null;}
  contains(node) {return node === this || this.children.some(child => child.contains(node));}
  focus() {this.ownerDocument.activeElement = this;}
  cloneNode(deep = false) {
    const node = new Element(this.ownerDocument, this.tagName);
    Object.assign(node, {className: this.className, disabled: this.disabled, hidden: this.hidden, _text: this._text,
      attributes: {...this.attributes}, dataset: {...this.dataset}, style: {...this.style}});
    if (deep) for (const child of this.children) node.appendChild(child.cloneNode(true));
    return node;
  }
  getBoundingClientRect() {
    if (this.tagName === 'summary') return {left: 280, right: 304, top: 190, bottom: 214, width: 24, height: 24};
    const width = Math.min(180, Number.parseFloat(this.style.maxWidth) || 180);
    const height = Math.min(this.children.length * 26 + 8, Number.parseFloat(this.style.maxHeight) || Infinity);
    const left = Number.parseFloat(this.style.left) || 0, top = Number.parseFloat(this.style.top) || 0;
    return {left, top, right: left + width, bottom: top + height, width, height};
  }
  dispatch(type, fields = {}) {
    const doc = this.ownerDocument;
    const event = {type, target: this, defaultPrevented: false, stopped: false, ...fields,
      preventDefault() {this.defaultPrevented = true;}, stopPropagation() {this.stopped = true;}};
    doc.deliver(type, event, true);
    const path = [];for (let node = this;node;node = node.parentElement) path.push(node);
    if (!event.stopped) for (const node of path.toReversed()) {node.deliver(type, event, true);if (event.stopped) break;}
    if (!event.stopped) for (const node of path) {node.deliver(type, event);if (event.stopped) break;}
    if (!event.stopped) doc.deliver(type, event);
    return event;
  }
  click() {if (!this.disabled) this.dispatch('click');}
}

function fixture() {
  const doc = new Events(), view = new Events(), observers = [];
  doc.documentElement = {lang: 'en'};doc.defaultView = view;doc.activeElement = null;
  doc.createElement = tag => new Element(doc, tag);doc.body = doc.createElement('body');
  doc.querySelector = selector => doc.body.querySelector(selector);
  view.innerWidth = 320;view.innerHeight = 220;view.scrollX = 0;view.scrollY = 0;view.getComputedStyle = () => ({zIndex: '1100'});
  view.MutationObserver = class {
    constructor(callback) {this.callback = callback;this.connected = true;observers.push(this);}
    observe() {}
    disconnect() {this.connected = false;}
  };
  const panel = doc.createElement('aside');panel.dataset.nativeDirectory = 'combat';panel.dataset.isGm = 'true';
  const target = doc.createElement('div');target.dataset.combatState = '';panel.append(target);doc.body.append(panel);
  const state = {sceneId: 'scene', active: true, round: 1, config: {input: 'roll'},
    combatants: Array.from({length: 4}, (_, index) => ({id: 't' + index, token_id: 't' + index, name: 'b',
      position: index + 1, initiative: 20 - index, can_move_up: index > 0, can_move_down: index < 3, bars: []}))};
  runInNewContext(source, {document: doc, window: view});
  const render = () => view.GravewrightCombatPanel.renderPanel(panel, state);
  render();
  const trigger = () => panel.querySelectorAll('summary').at(-1);
  const popup = () => doc.body.children.find(node => node.className.includes('directory-context-menu'));
  const emit = (type, fields = {}) => view.deliver(type, {type, target: view, ...fields}, type === 'scroll');
  const flush = records => {for (const observer of observers.filter(observer => observer.connected)) observer.callback(records || []);};
  return {doc, view, panel, state, trigger, popup, render, emit, flush, observers};
}

test('native combat actions escape the scrolling list and remain inside a small viewport', () => {
  const f = fixture(), trigger = f.trigger();trigger.click();
  const popup = f.popup(), box = popup.getBoundingClientRect();
  assert.equal(popup.parentElement, f.doc.body);assert.equal(popup.getAttribute('role'), 'menu');
  assert.equal(popup.style.position, 'fixed');assert.equal(popup.style.overflowY, 'auto');
  assert.ok(box.left >= 8 && box.right <= f.view.innerWidth - 8);
  assert.ok(box.top >= 8 && box.bottom <= f.view.innerHeight - 8);
  assert.equal(trigger.getAttribute('aria-expanded'), 'true');
  assert.equal(f.doc.activeElement, popup.querySelector('button'));
  f.doc.activeElement.dispatch('keydown', {key: 'Escape'});
  assert.equal(f.popup(), undefined);assert.equal(f.doc.activeElement, trigger);
  assert.equal(trigger.getAttribute('aria-expanded'), 'false');
  assert.equal(f.doc.listenerCount + f.view.listenerCount, 0);
});

test('portal actions dispatch once through their original combatant button and keyboard skips disabled actions', () => {
  const f = fixture(), trigger = f.trigger(), originalButtons = trigger.parentElement.querySelectorAll('button'), delivered = [];
  originalButtons[1].disabled = true;
  f.panel.addEventListener('click', event => {if (event.target.dataset.combatAction) delivered.push(event.target);});
  trigger.dispatch('keydown', {key: 'ArrowDown'});
  const choices = f.popup().querySelectorAll('button');
  choices[0].dispatch('keydown', {key: 'ArrowDown'});assert.equal(f.doc.activeElement, choices[2]);
  choices[2].dispatch('keydown', {key: 'End'});assert.equal(f.doc.activeElement, choices.at(-1));
  choices.at(-1).dispatch('keydown', {key: 'Home'});assert.equal(f.doc.activeElement, choices[0]);
  choices.at(-1).click();
  assert.deepEqual(delivered, [originalButtons.at(-1)]);
  assert.equal(delivered[0].dataset.combatAction, 'combatants/remove');
  assert.equal(delivered[0].dataset.combatantId, 't3');
  assert.equal(f.popup(), undefined);assert.equal(f.doc.activeElement, trigger);
});

test('native combat menu closes on outside action, scroll, resize, scene change, rerender and panel teardown', () => {
  for (const reason of ['outside', 'scroll', 'resize', 'scene', 'rerender', 'hidden', 'removed', 'pagehide']) {
    const f = fixture();f.trigger().click();const popup = f.popup();
    if (reason === 'outside') f.doc.body.click();
    if (reason === 'scroll') {f.emit('scroll', {target: popup});assert.equal(f.popup(), popup);f.panel.scrollTop += 10;f.emit('scroll', {target: f.panel});}
    if (reason === 'resize') f.emit('resize');
    if (reason === 'scene') f.emit('gravewright:module-scene');
    if (reason === 'rerender') f.render();
    if (reason === 'hidden') {f.panel.hidden = true;f.flush([{target: f.panel, type: 'attributes'}]);}
    if (reason === 'removed') {f.panel.remove();f.flush([{target: f.doc.body, type: 'childList'}]);}
    if (reason === 'pagehide') f.emit('pagehide');
    assert.equal(f.popup(), undefined, reason);
    assert.equal(f.doc.listenerCount + f.view.listenerCount, 0, reason);
    assert.ok(f.observers.every(observer => !observer.connected), reason);
  }
});

test('queued scroll-into-view events keep the menu open until an ancestor or viewport really moves', () => {
  for (const viewport of [false, true]) {
    const f = fixture(), scroller = viewport ? f.view : f.panel.querySelector('.gw-combat-list');
    if (viewport) f.view.scrollY = 50;else scroller.scrollTop = 200;
    f.trigger().click();const popup = f.popup();
    f.emit('scroll', {target: scroller});
    assert.equal(f.popup(), popup, 'A delayed event for the already captured position must not close the menu.');
    f.emit('scroll', {target: f.doc});
    assert.equal(f.popup(), popup);
    if (viewport) f.view.scrollY += 10;else scroller.scrollTop += 10;
    f.emit('scroll', {target: scroller});
    assert.equal(f.popup(), undefined);
    assert.equal(f.doc.listenerCount + f.view.listenerCount, 0);
  }
});
