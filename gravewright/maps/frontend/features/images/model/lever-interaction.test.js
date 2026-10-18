import test from 'node:test';
import assert from 'node:assert/strict';
import { leverAt, interactiveImageKind, canInteractWithImage } from './lever-interaction.js';
import { createLeverControls } from '../ui/lever-controls.js';

const image = { id: 'lever', x: 100, y: 200, rotation: 90, natural_width: 80,
    natural_height: 20, scale: 2, layer: 'map', z_index: 1, lever: { state: 'off' } };
const center = { x: 100, y: 200 };
const torch = { ...image, id: 'torch', lever: undefined, torch: { state: 'off', lit: true } };

test('lever hit testing follows centered, scaled and rotated public image geometry', () => {
    assert.equal(leverAt([image], { x: 115, y: 260 }, false), image);
    assert.equal(leverAt([image], { x: 130, y: 200 }, false), undefined);
    assert.equal(leverAt([{ ...image, lever: undefined }], center, false), undefined);
    assert.equal(leverAt([{ ...image, natural_width: NaN }], center, false), undefined);
    assert.equal(leverAt([{ ...image, scale: 0 }], center, false), undefined);
    // Players need only the state projection; no private blueprint is consulted.
    assert.equal(leverAt([{ ...image, lever: { state: 'on' } }], center, false)?.id, 'lever');
});

test('image stacking and GM layers determine which lever is reachable', () => {
    const cover = { ...image, id: 'cover', z_index: 2, lever: undefined };
    assert.equal(leverAt([cover, image], center, false), undefined);
    const hidden = { ...image, id: 'hidden', layer: 'gm-image-layer', z_index: -10 };
    assert.equal(leverAt([image, hidden], center, false), image);
    assert.equal(leverAt([image, hidden], center, true), hidden);
    assert.equal(leverAt([{ ...hidden, layer: 'gm' }], center, false), undefined);
    const top = { ...image, id: 'top' };
    assert.equal(leverAt([image, top], center, false), top);
});

test('image-free Smart Objects retain their authored hit area without loading artwork', () => {
    const empty = { ...image, id: 'empty', empty: true, asset_id: null, src: '' };
    assert.equal(leverAt([empty], center, false), undefined);
    assert.equal(leverAt([empty], center, true), empty);
    assert.equal(leverAt([empty], { x: 121, y: 200 }, false), undefined);
    assert.equal(leverAt([{ ...empty, layer: 'gm' }], center, false), undefined);
    assert.equal(leverAt([{ ...empty, interactionEnabled: false }], center, false), undefined);
    assert.equal(leverAt([{ ...empty, interactionEnabled: false }], center, true)?.id, 'empty');
});

test('torches retain independent mechanism and flame states in the public projection', () => {
    assert.equal(interactiveImageKind(torch), 'torch');
    assert.equal(leverAt([torch], center, false), torch);
    assert.equal(leverAt([{ ...torch, torch: { state: 'on', lit: false } }], center, false)?.id, 'torch');
    assert.equal(leverAt([{ ...torch, torch: { state: 'on' } }], center, false), undefined);
    assert.equal(leverAt([torch, { ...image, z_index: 2, lever: undefined }], center, false), undefined);
});

test('disabled interaction preserves object identity and occlusion while allowing GM manual override', () => {
    const disabled = { ...image, interactionEnabled: false }, behind = { ...image, id: 'behind', z_index: 0 };
    assert.equal(interactiveImageKind(disabled), 'lever');
    assert.equal(canInteractWithImage(disabled), false);
    assert.equal(canInteractWithImage(disabled, true), true);
    assert.equal(leverAt([behind, disabled], center, false), undefined, 'disabled foreground artwork still covers the object behind it');
    assert.equal(leverAt([behind, disabled], center, true), disabled);
    assert.equal(canInteractWithImage({ ...image, interactionEnabled: true }), true);
    assert.equal(canInteractWithImage(image), true, 'omitted flags retain the legacy interaction');
});

const deferred = () => {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    return { promise, resolve, reject };
};
const settle = () => new Promise(resolve => setImmediate(resolve));
class ElementStub extends EventTarget {
    constructor(tag) { super(); this.tag = tag; this.children = []; this.attributes = new Map(); this.dataset = {};
        this.classes = new Set(); this.classList = { add: name => this.classes.add(name) };
        this.namespaceURI = 'http://www.w3.org/2000/svg'; }
    setAttribute(key, value) { this.attributes.set(key, String(value)); if (key.startsWith('data-'))
        this.dataset[key.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = String(value); }
    getAttribute(key) { return this.attributes.get(key); }
    toggleAttribute(key, enabled) { if (enabled) this.setAttribute(key, ''); else this.attributes.delete(key); }
    append(...nodes) { for (const node of nodes) { node.parentElement = this; this.children.push(node); } }
    remove() { if (this.parentElement) this.parentElement.children = this.parentElement.children.filter(node => node !== this); }
    closest(selector) {
        if (selector === '[data-smart-image-action]' && this.dataset.smartImageAction) return this;
        if (selector === '.smart-image-controls' && this.classes.has('smart-image-controls')) return this;
        return this.parentElement?.closest(selector) ?? null;
    }
    focus() {}
}
function fixture(t, gm = false, initial = image) {
    const previous = { document: globalThis.document, window: globalThis.window };
    const context = { tool: 'select', layer: 'game', role: gm ? 'gm' : 'player', calibration: false, ignored: false };
    globalThis.document = { createElementNS: (_, tag) => new ElementStub(tag),
        querySelector: selector => selector === '#table-workspace'
            ? { dataset: { role: context.role } } : context.calibration ? {} : null };
    globalThis.window = new EventTarget();
    const surface = new ElementStub('surface');
    surface.getBoundingClientRect = () => ({ left: 10, top: 20, width: 1440, height: 900 });
    surface.closest = selector => context.ignored && selector.includes('button,') ? {} : null;
    const command = deferred(), read = deferred(), calls = [], errors = [];
    window.addEventListener('gravewright:tool-error', event => errors.push(event.detail.message));
    const api = { state: { images: [initial] }, command(...args) { calls.push(args); return command.promise; },
        read() { calls.push('read'); return read.promise; } };
    const control = createLeverControls(surface, { viewport: () => ({ x: 30, y: -40, scale: 2 }) }, gm,
        api, { getPath: key => context[key.slice(1)] });
    const double = (changes = {}) => {
        const event = new Event('dblclick', { cancelable: true });
        Object.assign(event, { button: 0, clientX: 240, clientY: 380 }, changes);
        surface.dispatchEvent(event);
        return event;
    };
    const key = (action, key = 'Enter', changes = {}) => {
        const target = surface.children[0].children[0].children.find(node => node.dataset.smartImageAction === action);
        const event = new Event('keydown', { cancelable: true });
        Object.defineProperty(event, 'target', { value: target });
        Object.assign(event, { key }, changes);
        surface.dispatchEvent(event);
        return event;
    };
    t.after(() => { control.destroy(); Object.assign(globalThis, previous); });
    return { context, surface, control, double, key, calls, command, read, errors };
}

test('players receive no mechanism or torch-flame controls for disabled images', t => {
    const f = fixture(t, false, { ...torch, interactionEnabled: false });
    assert.equal(f.surface.children[0].children.length, 0);
    assert.equal(f.double().defaultPrevented, false);
    assert.deepEqual(f.calls, []);
});

test('empty Smart Objects expose a named control only in the GM workspace', async t => {
    const empty = { ...image, id: 'empty', empty: true, src: '', asset_id: null };
    const f = fixture(t, true, empty);
    assert.equal(f.surface.children[0].children.length, 0);
    assert.equal(f.double().defaultPrevented, false);
    f.context.layer = 'gm';
    f.control.update({ images: [empty] });
    const main = f.surface.children[0].children[0].children[0];
    assert.equal(main.getAttribute('aria-label'), 'Empty Object: Deactivated.');
    assert.equal(main.getAttribute('fill'), 'transparent');
    assert.equal(f.double().defaultPrevented, true);
    assert.deepEqual(f.calls, [['images', 'interact', { image_id: 'empty' }]]);
    f.command.resolve(); f.read.resolve(); await settle();
});

test('a stale keyboard control cannot bypass an authoritative interaction disable', t => {
    const f = fixture(t, false, torch), stale = f.surface.children[0].children[0].children[1];
    f.control.update({ images: [{ ...torch, interactionEnabled: false }] });
    const event = new Event('keydown', { cancelable: true });
    Object.defineProperty(event, 'target', { value: stale }); Object.assign(event, { key: 'Enter' });
    f.surface.dispatchEvent(event);
    assert.deepEqual(f.calls, []);
});

test('a keyboard control from the GM workspace cannot operate after switching to Game', t => {
    const empty = { ...image, id: 'empty', empty: true, src: '', asset_id: null };
    const f = fixture(t, true, empty);
    f.context.layer = 'gm';
    f.control.update({ images: [empty] });
    const stale = f.surface.children[0].children[0].children[0];
    f.context.layer = 'game';
    const event = new Event('keydown', { cancelable: true });
    Object.defineProperty(event, 'target', { value: stale }); Object.assign(event, { key: 'Enter' });
    f.surface.dispatchEvent(event);
    assert.deepEqual(f.calls, []);
});

test('the GM can manually override a disabled torch flame without changing its interaction setting', async t => {
    const gm = fixture(t, true, { ...torch, interactionEnabled: false });
    assert.equal(gm.key('torch-light').defaultPrevented, true);
    assert.deepEqual(gm.calls, [['images', 'torch-light', { image_id: 'torch', lit: false }]]);
    gm.command.resolve(); gm.read.resolve(); await settle();
});

test('double-click sends one logical command until acknowledgement and refresh finish', async t => {
    const f = fixture(t);
    let otherDoubleClicks = 0;
    f.surface.addEventListener('dblclick', () => { otherDoubleClicks++; });
    assert.equal(f.double().defaultPrevented, true);
    f.double();
    assert.deepEqual(f.calls, [['images', 'interact', { image_id: 'lever' }]]);
    assert.equal(otherDoubleClicks, 0, 'lever activation must not reach mixed selection editing');
    f.command.resolve({ image: { lever: { state: 'on' } } });
    await settle();
    f.double();
    assert.deepEqual(f.calls.at(-1), 'read');
    assert.equal(f.calls.length, 2, 'the pending guard includes the authoritative refresh');
    f.control.update({ images: [{ ...image, x: 500 }] });
    f.read.resolve();
    await settle();
    assert.equal(f.double().defaultPrevented, false, 'subsequent hits use current projected geometry');
    assert.equal(otherDoubleClicks, 1);
});

test('streamers, editing tools and native overlay targets do not activate levers', t => {
    const f = fixture(t, true);
    for (const overrides of [{ role: 'streamer' }, { layer: 'composition' }, { layer: 'walls' },
        { layer: 'effects' }, { tool: 'measure' }, { tool: 'wall' }, { calibration: true }, { ignored: true }]) {
        const before = { ...f.context };
        Object.assign(f.context, overrides);
        assert.equal(f.double().defaultPrevented, false);
        Object.assign(f.context, before);
    }
    assert.equal(f.double({ button: 2 }).defaultPrevented, false);
    assert.equal(f.calls.length, 0);
    assert.equal(f.double().defaultPrevented, true, 'GMs can operate in normal selection mode');
});

test('destroy removes the gesture and stops late command completion from refreshing a new scene', async t => {
    const f = fixture(t);
    f.double();
    f.control.destroy();
    assert.equal(f.double().defaultPrevented, false);
    f.command.resolve();
    await settle();
    assert.equal(f.calls.length, 1);
});

test('an uncertain command failure reports the error and refreshes without retrying the toggle', async t => {
    const f = fixture(t);
    f.double();
    f.command.reject(new Error('Connection lost.'));
    await settle();
    assert.deepEqual(f.errors, ['Connection lost.']);
    assert.equal(f.calls.length, 2);
    assert.equal(f.calls[1], 'read');
    f.read.resolve();
    await settle();
});

test('torch keyboard activation turns the mechanism without changing flame state', async t => {
    const f = fixture(t, false, torch);
    assert.equal(f.key('interact').defaultPrevented, true);
    f.key('torch-light');
    assert.deepEqual(f.calls, [['images', 'interact', { image_id: 'torch' }]], 'one pending operation per object');
    f.command.resolve(); f.read.resolve();
    await settle();
    assert.equal(f.surface.children[0].children[0].children[0].getAttribute('aria-label'),
        'Torch: Normal. Lit. Turn torch.');
});

test('torch flame keyboard action sends an explicit value without a mechanism command', async t => {
    const f = fixture(t, false, { ...torch, torch: { state: 'on', lit: false } });
    assert.equal(f.key('torch-light', ' ', { repeat: true }).defaultPrevented, true);
    assert.equal(f.calls.length, 0);
    assert.equal(f.key('torch-light', ' ').defaultPrevented, true);
    assert.deepEqual(f.calls, [['images', 'torch-light', { image_id: 'torch', lit: true }]]);
    assert.equal(f.key('interact', 'ArrowRight').defaultPrevented, false);
    f.command.resolve(); f.read.resolve();
    await settle();
});
