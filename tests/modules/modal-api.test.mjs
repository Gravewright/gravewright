import test from 'node:test';
import assert from 'node:assert/strict';
import { createUiApi, setModalHost } from '../../gravewright/modules/static/gravewright_modules/modal-api.js';
import { Lifetime } from '../../gravewright/modules/static/gravewright_modules/lifetime.js';
import { BrowserBridge } from '../../gravewright/modules/static/gravewright_modules/browser-bridge.js';

class Element extends EventTarget {
  constructor(document, name) {
    super();
    this.ownerDocument = document;
    this.localName = name;
    this.classList = new Set();
  }
}
function fixture(onMount) {
  const document = { defaultView: { Element } }, calls = [];
  const host = { document, mountModal(element, options) {
    const call = { element, options, closed: false, forced: [] };
    calls.push(call);
    element.close = force => {
      if (call.closed) return;
      call.closed = true;
      call.forced.push(force);
      element.dispatchEvent(new Event('close'));
    };
    element.suspend = () => { call.suspended = true; };
    element.resume = () => { call.suspended = false; };
    onMount?.(element);
    return element;
  } };
  return { document, calls, host, element: name => new Element(document, name) };
}

test('module modals use the native component synchronously and preserve registration', async () => {
  const f = fixture(), life = new Lifetime(), register = () => {};
  const ui = createUiApi(life, { register }, f.host), modal = f.element('section');
  assert.equal(ui.register, register);
  assert.ok(Object.isFrozen(ui));
  assert.equal(ui.openModal(modal), modal);
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0].options.nested, true);
  assert.equal(f.calls[0].options.canClose(), true);
  assert.ok(modal.classList.has('table-modal-window'));
  modal.suspend();
  assert.equal(f.calls[0].suspended, true);
  modal.resume();
  assert.equal(f.calls[0].suspended, false);
  await life.close();
  assert.deepEqual(f.calls[0].forced, [true]);
  assert.equal(life.cleanups.length, 0);
  assert.throws(() => ui.openModal(f.element('div')), { code: 'stale_context' });
});

test('normal close releases lifetime ownership and allows reusing a closed modal', async () => {
  const f = fixture(), life = new Lifetime(), ui = createUiApi(life, {}, f.host);
  const modal = ui.openModal(f.element('form'));
  assert.equal(life.cleanups.length, 1);
  assert.throws(() => ui.openModal(modal), { code: 'conflict' });
  modal.close();
  assert.equal(life.cleanups.length, 0);
  assert.equal(ui.openModal(modal), modal);
  modal.close();
  await life.close();
  assert.deepEqual(f.calls.map(call => call.forced), [[undefined], [undefined]]);
});

test('Escape close guard and explicit nesting options reach the host component', async () => {
  const f = fixture(), life = new Lifetime();
  let busy = true;
  createUiApi(life, {}, f.host).openModal(f.element('div'), { nested: false, canClose: () => !busy });
  assert.equal(f.calls[0].options.nested, false);
  assert.equal(f.calls[0].options.canClose(), false);
  busy = false;
  assert.equal(f.calls[0].options.canClose(), true);
  await life.close();
  assert.equal(f.calls[0].options.canClose(), false);
  assert.deepEqual(f.calls[0].forced, [true]);
});

test('native dialogs, foreign documents and invalid options cannot mount', async () => {
  const f = fixture(), life = new Lifetime(), ui = createUiApi(life, {}, f.host);
  for (const element of [null, {}, f.element('dialog'), f.element('button'), fixture().element('section')]) {
    assert.throws(() => ui.openModal(element), { code: 'invalid_data' });
  }
  for (const options of [null, [], 'nested', { nested: 1 }, { canClose: true }]) {
    assert.throws(() => ui.openModal(f.element('section'), options), { code: 'invalid_data' });
  }
  assert.equal(f.calls.length, 0);
  assert.equal(life.cleanups.length, 0);
  await life.close();
});

test('disposal during native mounting immediately removes the modal', async () => {
  const life = new Lifetime(), f = fixture(() => { void life.close(); });
  assert.throws(() => createUiApi(life, {}, f.host).openModal(f.element('section')), { code: 'stale_context' });
  assert.deepEqual(f.calls[0].forced, [true]);
  assert.equal(life.cleanups.length, 0);
  await life.close();
});

test('BrowserBridge APIs obtain the host injected at browser initialization', async () => {
  globalThis.window = new EventTarget();
  setModalHost(undefined, undefined);
  const life = new Lifetime(), bridge = new BrowserBridge('table'), register = () => {};
  const api = bridge.api({ moduleId: 'example.system', tableId: 'table', mountId: 'mount' }, life, { register });
  assert.equal(api.ui.register, register);
  assert.throws(() => api.ui.openModal(null), { code: 'unavailable' });
  const f = fixture();
  setModalHost(f.host.mountModal, f.document);
  assert.equal(api.ui.openModal(f.element('section')), f.calls[0].element);
  await life.close();
  assert.deepEqual(f.calls[0].forced, [true]);
  setModalHost(undefined, undefined);
});
