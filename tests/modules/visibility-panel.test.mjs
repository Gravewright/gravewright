import test from 'node:test';
import assert from 'node:assert/strict';
import { createTranslator } from '../../gravewright/modules/static/gravewright_modules/i18n.js';
import { mountVisibilityPanelText } from '../../gravewright/maps/static/gravewright_maps/visibility-panel.js';

class Element extends EventTarget {
  constructor(attributes = {}, text = '') { super(); this.attributes = new Map(Object.entries(attributes)); this.children = []; this.value = text; }
  append(...elements) { this.children.push(...elements); }
  get textContent() { return this.value + this.children.map(element => element.textContent).join(''); }
  set textContent(value) { this.value = value; this.children = []; }
  setAttribute(name, value) { this.attributes.set(name, value); }
  getAttribute(name) { return this.attributes.get(name); }
  get dataset() { return Object.fromEntries([...this.attributes].filter(([name]) => name.startsWith('data-'))
    .map(([name, value]) => [name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase()), value])); }
  matches(selector) {
    const [, name, value] = selector.match(/^\[([^=\]]+)(?:=([^\]]+))?\]$/) || [];
    return this.attributes.has(name) && (value === undefined || this.attributes.get(name) === value);
  }
  querySelectorAll(selector) { return this.children.flatMap(element => [...(element.matches(selector) ? [element] : []), ...element.querySelectorAll(selector)]); }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
}
class View extends EventTarget {
  listeners = new Map();
  addEventListener(name, callback, options) { this.listeners.set(callback, name); super.addEventListener(name, callback, options); }
  removeEventListener(name, callback, options) { this.listeners.delete(callback); super.removeEventListener(name, callback, options); }
}
const fullHint = 'The whole map is visible to everyone. Nothing is hidden.';
const catalogs = {
  'pt-BR': { Visibility: 'Visibilidade', 'Full vision': 'Visão completa', Mode: 'Modo', Close: 'Fechar', Detach: 'Desacoplar', Minimize: 'Minimizar',
    [fullHint]: 'Todo o mapa está visível.', 'Manual lighting is active.': 'Iluminação manual ativa.',
    'Click to add points. Click the first point to close.': 'Clique para adicionar pontos.', 'Could not save the change.': 'Não foi possível salvar.' },
  es: { Visibility: 'Visibilidad', 'Full vision': 'Visión completa', Mode: 'Modo', Close: 'Cerrar', Detach: 'Desacoplar', Minimize: 'Minimizar',
    [fullHint]: 'Todo el mapa es visible.' },
};
function fixture(locale = 'en') {
  const view = globalThis.window = new View();
  globalThis.document = { getElementById: () => null };
  view.gravewrightLocale = { id: locale, messages: catalogs[locale] || {} };
  const panel = new Element(), icon = new Element(), heading = new Element(), title = new Element({ 'data-visibility-text': 'Visibility' }, 'Visibility');
  heading.append(icon, title); panel.append(heading);
  const full = new Element({ 'data-visibility-text': 'Full vision' }, 'Full vision'), group = new Element({ 'data-visibility-aria': 'Mode' });
  const modeHint = new Element({ 'data-mode-hint': '' }), status = new Element({ 'data-fog-status': '' }), brush = new Element({ 'data-brush-hint': '' });
  const alert = new Element({ role: 'alert' }), input = new Element({ name: 'darkness' }), output = new Element();
  input.value = '0.65'; input.disabled = true; output.value = '0.65';
  const close = new Element({ 'data-visibility-action': 'close' }), detach = new Element({ 'data-visibility-action': 'detach' }), minimize = new Element({ 'data-visibility-action': 'minimize' });
  panel.append(full, group, modeHint, status, brush, alert, input, output, close, detach, minimize);
  document.activeElement = input;
  let popup;
  const labels = mountVisibilityPanelText(panel, { translator: createTranslator(), getPopup: () => popup });
  const state = { mode: 'none', fogEnabled: false, shape: 'circle', error: '' };
  labels.update(state);
  const language = id => {
    view.gravewrightLocale = { id, messages: catalogs[id] || {} };
    view.dispatchEvent(new CustomEvent('gravewright:locale', { detail: view.gravewrightLocale }));
  };
  return { panel, heading, icon, title, full, group, modeHint, status, brush, alert, input, output, close, detach, minimize, view, labels, state, language,
    detachWindow() { return popup = { closed: false, document: { title: 'Visibility', documentElement: { lang: 'en' } } }; } };
}

test('full vision uses English defaults and an English brush hint without a language pack', () => {
  const f = fixture();
  assert.equal(f.title.textContent, 'Visibility');
  assert.equal(f.full.textContent, 'Full vision');
  assert.equal(f.modeHint.textContent, fullHint);
  assert.equal(f.brush.textContent, 'Alt+scroll on the map to adjust quickly.');
  assert.equal(f.panel.getAttribute('aria-label'), 'Visibility');
  f.labels.destroy();
});

test('installed catalogs translate the icon title immediately and language changes preserve controls and focus', () => {
  const f = fixture('pt-BR'); let closes = 0;
  f.close.addEventListener('click', () => closes++);
  assert.equal(f.title.textContent, 'Visibilidade');
  assert.equal(f.full.textContent, 'Visão completa');
  assert.equal(f.modeHint.textContent, 'Todo o mapa está visível.');
  assert.equal(f.close.getAttribute('title'), 'Fechar');
  f.language('es');
  assert.equal(f.title.textContent, 'Visibilidad');
  assert.equal(f.full.textContent, 'Visión completa');
  assert.equal(f.modeHint.textContent, 'Todo el mapa es visible.');
  assert.equal(f.group.getAttribute('aria-label'), 'Modo');
  assert.equal(f.close.getAttribute('aria-label'), 'Cerrar');
  assert.equal(f.heading.children[0], f.icon);
  assert.equal(document.activeElement, f.input);
  assert.equal(f.input.value, '0.65'); assert.equal(f.output.value, '0.65'); assert.equal(f.input.disabled, true);
  f.close.dispatchEvent(new Event('click')); assert.equal(closes, 1);
  f.language('en'); assert.equal(f.title.textContent, 'Visibility'); assert.equal(f.modeHint.textContent, fullHint);
  f.labels.destroy();
});

test('state changes translate the current fog, polygon and error messages instead of restoring raw source text', () => {
  const f = fixture('pt-BR');
  f.labels.update({ mode: 'manual', fogEnabled: true, shape: 'polygon', error: 'Could not save the change.' });
  assert.equal(f.status.textContent, 'Iluminação manual ativa.');
  assert.equal(f.brush.textContent, 'Clique para adicionar pontos.');
  assert.equal(f.alert.textContent, 'Não foi possível salvar.');
  f.language('en');
  assert.equal(f.modeHint.textContent, 'Paint revealed areas by hand, independently of tokens and lights.');
  assert.equal(f.status.textContent, 'Manual lighting is active.');
  assert.equal(f.alert.textContent, 'Could not save the change.');
  f.labels.update({ mode: 'dynamic', fogEnabled: false, shape: 'square', error: '' });
  assert.equal(f.modeHint.textContent, 'Players only see what their tokens and lights reach. Walls block vision.');
  assert.equal(f.status.textContent, 'Manual lighting is off. Choose an initial state to enable it.');
  assert.equal(f.alert.textContent, '');
  f.labels.destroy();
});

test('detached titles follow the locale and closing disposes translations before stale updates or reopening', () => {
  const f = fixture(), popup = f.detachWindow();
  f.language('pt-BR');
  assert.equal(popup.document.title, 'Visibilidade');
  assert.equal(popup.document.documentElement.lang, 'pt-BR');
  assert.equal(f.view.listeners.size, 2);
  f.labels.destroy(); f.labels.destroy();
  assert.equal(f.view.listeners.size, 0);
  f.language('es'); f.labels.update({ ...f.state, mode: 'manual' });
  assert.equal(popup.document.title, 'Visibilidade');
  assert.equal(f.modeHint.textContent, 'Todo o mapa está visível.');
  const reopened = mountVisibilityPanelText(f.panel, { translator: createTranslator() });
  reopened.update(f.state);
  assert.equal(f.title.textContent, 'Visibilidad');
  assert.equal(f.modeHint.textContent, 'Todo el mapa es visible.');
  reopened.destroy(); assert.equal(f.view.listeners.size, 0);
});
