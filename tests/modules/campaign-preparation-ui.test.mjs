import test from 'node:test';
import assert from 'node:assert/strict';
import { registerHooks } from 'node:module';

globalThis.window = new EventTarget();
const formStub = 'data:text/javascript,' + encodeURIComponent('export const modalText=(key)=>key;export const openFormModal=(...args)=>globalThis.preparationTestForm(...args);');
const hook = registerHooks({ resolve(specifier, context, next) {
  if (specifier === '/static/gravewright_table/form-modal.js' || context.parentURL?.endsWith('/references.js') && specifier === './form-modal.js')
    return { url: formStub, shortCircuit: true };
  if (specifier === '/static/gravewright_table/references.js') return {
    url: new URL('../../gravewright/table/static/gravewright_table/references.js', import.meta.url).href, shortCircuit: true,
  };
  if (context.parentURL?.endsWith('/references.js') && specifier === './content-state.js')
    return { url: 'data:text/javascript,export const afterContentReady=()=>{};', shortCircuit: true };
  return next(specifier, context);
} });
const { mountPreparation } = await import('../../gravewright/web/static/gravewright_web/campaign-manager/preparation.js');
const { pickReference } = await import('../../gravewright/table/static/gravewright_table/references.js');
hook.deregister();

const camel = value => value.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
class Element extends EventTarget {
  constructor(tag, document) {
    super(); this.localName = tag; this.ownerDocument = document; this.children = []; this.parentNode = null;
    this.dataset = {}; this.attributes = new Map(); this.value = ''; this.checked = false; this.disabled = false;
    this.style = { setProperty() {} }; this._text = ''; this.className = '';
    this.classList = { add: (...names) => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), ...names])].join(' '); },
      remove: name => { this.className = this.className.split(/\s+/).filter(value => value !== name).join(' '); },
      contains: name => this.className.split(/\s+/).includes(name),
      toggle: (name, force) => { const add = force ?? !this.classList.contains(name); this.classList[add ? 'add' : 'remove'](name); return add; } };
  }
  get isConnected() { return this === this.ownerDocument.body || !!this.parentNode?.isConnected; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this.replaceChildren(); this._text = String(value); }
  get firstChild() { return this.children[0]; }
  get lastChild() { return this.children.at(-1); }
  get elements() { return Object.fromEntries(this.querySelectorAll('[name]').map(node => [node.name, node])); }
  append(...nodes) { for (const node of nodes) { node.remove(); node.parentNode = this; this.children.push(node); } }
  add(node) { this.append(node); if (!this.value) this.value = node.value; }
  replaceChildren(...nodes) { for (const node of this.children) node.parentNode = null; this.children = []; this._text = ''; this.append(...nodes); }
  remove() { if (this.parentNode) { const index = this.parentNode.children.indexOf(this); this.parentNode.children.splice(index, 1); this.parentNode = null; } }
  after(node) { const parent = this.parentNode, index = parent.children.indexOf(this); node.remove(); node.parentNode = parent; parent.children.splice(index + 1, 0, node); }
  setAttribute(name, value) { if (name.startsWith('data-')) this.dataset[camel(name.slice(5))] = String(value); else this.attributes.set(name, String(value)); }
  getAttribute(name) { return name.startsWith('data-') ? this.dataset[camel(name.slice(5))] ?? null : this.attributes.get(name) ?? this[name] ?? null; }
  removeAttribute(name) { this.attributes.delete(name); }
  contains(node) { for (let item = node; item; item = item.parentNode) if (item === this) return true; return false; }
  focus() { this.ownerDocument.activeElement = this; }
  reportValidity() { return true; }
  matches(token) {
    const tag = token.match(/^[a-z][\w-]*/)?.[0]; if (tag && this.localName !== tag) return false;
    for (const [, name] of token.matchAll(/\.([\w-]+)/g)) if (!this.classList.contains(name)) return false;
    for (const [, name, value] of token.matchAll(/\[([\w-]+)(?:=['"]?([^'"\]]+)['"]?)?\]/g)) {
      const actual = this.getAttribute(name); if (actual === null || value !== undefined && String(actual) !== value) return false;
    }
    return !token.includes(':checked') || this.checked;
  }
  querySelectorAll(selector) {
    return all(this).slice(1).filter(node => selector.split(',').some(part => {
      const tokens = part.trim().split(/\s+/); if (!node.matches(tokens.pop())) return false;
      let parent = node.parentNode;
      for (const token of tokens.reverse()) { while (parent && !parent.matches(token)) parent = parent.parentNode; if (!parent) return false; parent = parent.parentNode; }
      return true;
    }));
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
const all = root => [root, ...root.children.flatMap(all)];
const tick = async () => { await new Promise(setImmediate); await new Promise(setImmediate); };
const defer = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const named = (root, label) => all(root).find(node => node.localName === 'button' && (node.textContent === label || node.firstChild?.textContent === label));
async function click(button) { assert.ok(button, 'Expected a native control'); if (!button.disabled) { button.onclick?.(new Event('click')); button.dispatchEvent(new Event('click')); } await tick(); }
function input(control, value) { assert.ok(control); assert.equal(control.disabled, false); control.value = value; control.dispatchEvent(new Event('input')); }

function fixture(t, { loadModule } = {}) {
  const document = { createElement: tag => new Element(tag, document), documentElement: { lang: 'en' } };
  document.body = document.createElement('body'); document.activeElement = document.body;
  globalThis.document = document;
  globalThis.Option = function (label, value) { const node = document.createElement('option'); node.textContent = label; node.value = value; return node; };
  const make = (tag, key, parent) => { const node = document.createElement(tag); if (key) node.dataset[key] = ''; parent?.append(node); return node; };
  const root = make('main', null, document.body); root.id = 'table-workspace'; root.dataset.tableId = 'campaign';
  document.getElementById = id => all(document.body).find(node => node.id === id);
  make('div', 'managerDashboard', root);
  const sessions = make('section', 'managerSessions', root); make('nav', 'sessionList', sessions); make('div', 'sessionEditor', sessions); make('button', 'sessionCreate', sessions);
  const timeline = make('section', 'managerTimeline', root); make('select', 'timelineFilter', timeline); make('div', 'timelineBody', timeline);
  for (const mode of ['list', 'calendar']) make('button', 'timelineMode', timeline).dataset.timelineMode = mode;
  make('button', 'eventCreate', timeline); make('select', 'managerQuestStatus', root); make('div', 'managerQuests', root);
  const connections = make('section', 'managerConnections', root); make('div', 'connectionsBody', connections); make('button', 'connectionsPick', connections);
  const players = make('section', 'managerPlayerView', root); make('select', 'playerChoice', players); make('div', 'playerBody', players);
  const history = make('section', 'managerHistory', root); make('select', 'historyJournal', history); make('div', 'historyVersions', history); make('div', 'historyTrash', history); make('button', 'historyRefresh', history);
  const date = new Date().toISOString().slice(0, 10);
  const plan = (id, title) => ({ id, title, revision: 1, status: 'planned', scheduledFor: date, notes: 'Saved notes', steps: [], checklist: [], pending: [], summary: '' });
  const server = { board: { revision: 1, widgets: ['session'], pins: [] }, sessions: [plan('a', 'Session A'), plan('b', 'Session B')],
    pending: { session: null, unassigned: [], blocked: [], carried: [] }, events: [], diagnostics: { supported: false, issues: [] } };
  server.pending.session = server.sessions[0];
  const states = new Map([['journals', { journals: [{ id: 'journal', title: 'Journal', type: 'diary', version: 7, can_edit: true }] }], ['actors', { actors: [] }], ['maps', { maps: [] }]]);
  const calls = [], errors = [], modals = [], opened = [], selections = [], scope = new AbortController();
  globalThis.preparationTestForm = (title, fields, save, options) => {
    const priorFocus = document.activeElement;
    const modal = make('section', null, document.body); modal.title = title; modal.key = options?.key;
    const form = make('form', null, modal), header = make('header', null, form); make('strong', null, header).textContent = title;
    const body = make('div', null, form), alert = make('p', null, body); alert.setAttribute('role', 'alert'); alert.hidden = true;
    const inputs = make('div', 'fields', body), submit = make('button', null, form); submit.type = 'submit'; submit.textContent = options?.submitLabel || 'Save';
    for (const field of fields) { const control = make(field.options ? 'select' : field.multiline ? 'textarea' : 'input', null, inputs);
      control.name = field.name; if (!field.multiline) control.type = field.type || 'text';
      for (const option of field.options || []) control.add(new Option(option.label, option.value));
      control.value = field.value ?? ''; control.checked = !!field.value;
    }
    modal.close = () => { if (!modal.isConnected) return; modal.remove(); if (priorFocus?.isConnected) priorFocus.focus(); modal.dispatchEvent(new Event('close')); };
    modal.submit = async () => { try { await save(form); modal.close(); } catch (error) { alert.hidden = false; alert.textContent = error.message; } };
    modals.push(modal); return modal;
  };
  const campaigns = {
    preparation: async () => structuredClone(server),
    prepare: async (_id, action, payload, requestId) => {
      calls.push({ action, payload: structuredClone(payload), requestId });
      if (action === 'session-update') { const row = server.sessions.find(row => row.id === payload.id); Object.assign(row, structuredClone(payload), { revision: row.revision + 1 }); return { id: row.id, revision: row.revision }; }
      return {};
    },
    references: async () => ({ target: { id: 'journal', type: 'journal', title: 'Journal' }, links: [], usedBy: [{ id: 'a', type: 'session', title: 'Session A', via: 'session' }] }),
    viewAs: async () => ({ member: { id: 'player', name: 'Player' }, journals: [], actors: [], items: [], scenes: [] }),
    journalHistory: async () => ({ revisions: [{ id: 'revision', journalId: 'journal', title: 'Earlier revision', version: 6 }] }),
    journalTrash: async () => ({ journals: [] }),
    journalRevision: async () => ({ revision: { lines: ['Old body'] }, current: { version: 7, lines: ['Reviewed body'] } }),
  };
  const transport = { states, signal: scope.signal, check: async () => {}, read: async name => states.get(name),
    journalCommand: async (action, payload, options) => { calls.push({ action, payload: structuredClone(payload), requestId: options.requestId }); return {}; },
    search: async () => [{ type: 'journal', id: '00000000-0000-4000-8000-000000000001', title: 'Synthetic document' }],
  };
  window.gravewrightRealtime = transport;
  let component;
  const ctx = { root, campaignId: 'campaign', campaigns, transport, signal: scope.signal, t: key => key, open: value => opened.push(value),
    run: async (work, button) => { if (button?.disabled) return; if (button) button.disabled = true; try { return await work(); } catch (error) { errors.push(error); } finally { if (button) button.disabled = false; } },
    select: async next => { selections.push(next); return component.enter(next); }, overview: () => ({ members: [{ id: 'player', name: 'Player', role: 'player' }] }),
    audio: async () => ({}), loadModule: loadModule || (async () => ({ richText: host => { host.textContent = 'Projected rich text'; return { destroy() {} }; } })),
  };
  component = mountPreparation(ctx); t.after(() => { component.destroy(); scope.abort(); });
  const editor = () => root.querySelector('[data-session-editor]');
  const choose = async id => click(named(root.querySelector('[data-session-list]'), id === 'a' ? 'Session A' : 'Session B'));
  return { root, document, server, states, campaigns, transport, component, calls, errors, modals, opened, selections, ctx, editor, choose, scope };
}

test('the selected session card and all navigation shortcuts preserve unsaved session input', async t => {
  const f = fixture(t); await f.component.load(); await f.choose('b');
  input(f.editor().querySelector('textarea'), 'Unsaved private draft');
  assert.ok(named(f.editor(), 'Discard changes'));
  await f.choose('b'); assert.equal(f.editor().querySelector('textarea').value, 'Unsaved private draft');
  await f.choose('a'); assert.match(f.errors.at(-1).message, /Save or discard/);
  await click(named(f.root, 'Open session plan')); assert.match(f.errors.at(-1).message, /Save or discard/);
  await click(f.root.querySelector('[data-timeline-mode="calendar"]'));
  await click(named(f.root.querySelector('[data-timeline-body]'), 'Session A')); assert.match(f.errors.at(-1).message, /Save or discard/);
  await f.component.showConnections({ type: 'journal', id: 'journal' });
  await click(named(f.root.querySelector('[data-connections-body]'), 'Session A')); assert.match(f.errors.at(-1).message, /Save or discard/);
  assert.equal(f.editor().querySelector('textarea').value, 'Unsaved private draft'); assert.equal(f.calls.length, 0);
});

test('session saves lock their editor until the confirmed candidate and fresh state are available', async t => {
  const f = fixture(t); await f.component.load(); await f.choose('a');
  input(f.editor().querySelector('textarea'), 'Submitted private notes');
  const pending = defer(), prepare = f.campaigns.prepare;
  f.campaigns.prepare = async (...args) => { await pending.promise; return prepare(...args); };
  await click(named(f.editor(), 'Save changes'));
  assert.equal(f.editor().getAttribute('aria-busy'), 'true');
  assert.ok(f.editor().querySelectorAll('input,textarea,select,button').every(control => control.disabled));
  await f.choose('a'); assert.equal(f.editor().querySelector('textarea').disabled, true);
  pending.resolve(); await tick();
  assert.equal(f.editor().querySelector('textarea').value, 'Submitted private notes');
  assert.equal(f.editor().querySelector('textarea').disabled, false); assert.ok(named(f.editor(), 'Saved'));
  assert.equal(f.calls[0].payload.revision, 1); assert.equal(f.server.sessions[0].revision, 2);
});

test('session conflicts preserve the draft and its opening revision on every attempt', async t => {
  const f = fixture(t); await f.component.load(); await f.choose('a'); input(f.editor().querySelector('textarea'), 'Keep this draft');
  f.server.sessions[0].revision = 2;
  f.campaigns.prepare = async (_id, action, payload, requestId) => { f.calls.push({ action, payload, requestId }); throw Object.assign(Error('Conflict'), { code: 'conflict' }); };
  await click(named(f.editor(), 'Save changes')); await click(named(f.editor(), 'Save changes'));
  assert.equal(f.editor().querySelector('textarea').value, 'Keep this draft'); assert.match(f.errors[0].message, /draft is preserved/);
  assert.deepEqual(f.calls.map(call => call.payload.revision), [1, 1]);
  await click(named(f.editor(), 'Discard changes')); assert.equal(f.editor().querySelector('textarea').value, 'Saved notes');
});

test('finishing a session refreshes its clean editor after the native modal restores focus', async t => {
  const f = fixture(t); await f.component.load(); await f.choose('a');
  const finish = named(f.editor(), 'Finish session'); finish.focus();
  f.campaigns.prepare = async (_id, action, payload) => {
    assert.equal(action, 'session-finish');
    Object.assign(f.server.sessions[0], { status: 'completed', revision: 2, summary: payload.summary, pending: payload.pending });
    return { id: 'a', revision: 2 };
  };
  await click(finish); const modal = f.modals.at(-1);
  modal.querySelector('[name=summary]').value = 'Completed session summary';
  modal.querySelector('[name=pending]').value = 'Carry this forward';
  await modal.submit();
  assert.equal(modal.isConnected, false); assert.ok(named(f.editor(), 'Reopen session'));
  assert.equal(named(f.editor(), 'Finish session'), undefined);
  assert.match(f.editor().textContent, /Completed session summary/); assert.match(f.editor().textContent, /Carry this forward/);
});

test('a pre-commit background read cannot replace the canonical post-commit session state', async t => {
  const f = fixture(t); await f.component.load(); await f.choose('a');
  const old = structuredClone(f.server), pending = defer(); let reads = 0;
  f.campaigns.preparation = async () => ++reads === 1 ? pending.promise : structuredClone(f.server);
  const reading = f.component.load(); input(f.editor().querySelector('textarea'), 'Committed notes');
  await click(named(f.editor(), 'Save changes'));
  assert.equal(reads, 2); assert.equal(f.editor().querySelector('textarea').value, 'Committed notes');
  pending.resolve(old); await reading;
  assert.equal(f.editor().querySelector('textarea').value, 'Committed notes');
});

test('uncertain session retries reuse the request UUID and original candidate after a lost reply', async t => {
  const f = fixture(t); await f.component.load(); await f.choose('a'); input(f.editor().querySelector('textarea'), 'Retry candidate');
  let first = true;
  f.campaigns.prepare = async (_id, action, payload, requestId) => {
    f.calls.push({ action, payload: structuredClone(payload), requestId });
    if (first) { first = false; Object.assign(f.server.sessions[0], structuredClone(payload), { revision: 2 }); throw Error('Lost reply'); }
    return { id: payload.id, revision: 2 };
  };
  await click(named(f.editor(), 'Save changes')); await click(named(f.editor(), 'Save changes'));
  assert.equal(f.calls[0].requestId, f.calls[1].requestId); assert.deepEqual(f.calls[0].payload, f.calls[1].payload);
  assert.equal(f.editor().querySelector('textarea').value, 'Retry candidate'); assert.ok(named(f.editor(), 'Saved'));
});

test('comparison restores the reviewed version and preserves its diff after a conflict until a new comparison', async t => {
  const f = fixture(t); await f.component.enter('history');
  const chooser = f.root.querySelector('[data-history-journal]'); chooser.value = 'journal'; chooser.dispatchEvent(new Event('change')); await tick();
  await click(named(f.root, 'Compare')); const modal = f.modals.at(-1);
  f.states.get('journals').journals[0].version = 8;
  f.transport.journalCommand = async (action, payload) => { f.calls.push({ action, payload }); throw Object.assign(Error('Conflict'), { code: 'conflict' }); };
  await modal.submit();
  assert.equal(f.calls[0].payload.version, 7); assert.equal(modal.isConnected, true);
  assert.equal(modal.querySelector('[type=submit]').hidden, true); assert.match(modal.textContent, /compare again/);
  assert.match(modal.textContent, /Reviewed body/); assert.match(modal.textContent, /Old body/);
  await modal.submit(); assert.equal(f.calls.length, 1);
});

test('out-of-order history reads never place another document revisions under the current selection', async t => {
  const f = fixture(t), first = defer(), second = defer();
  f.states.get('journals').journals.push({ id: 'other', title: 'Other journal', version: 2, can_edit: true });
  f.campaigns.journalHistory = async (_campaign, id) => id === 'journal' ? first.promise : second.promise;
  await f.component.enter('history');
  const chooser = f.root.querySelector('[data-history-journal]');
  chooser.value = 'journal'; chooser.dispatchEvent(new Event('change')); await tick();
  chooser.value = 'other'; chooser.dispatchEvent(new Event('change')); await tick();
  second.resolve({ revisions: [{ id: 'new', journalId: 'other', title: 'Current selection revision', version: 1 }] }); await tick();
  first.resolve({ revisions: [{ id: 'old', journalId: 'journal', title: 'Stale selection revision', version: 6 }] }); await tick();
  const versions = f.root.querySelector('[data-history-versions]');
  assert.match(versions.textContent, /Current selection revision/); assert.equal(versions.textContent.includes('Stale selection revision'), false);
  assert.equal(chooser.value, 'other');
});

test('a native reference picker waits for async insertion and retains its selection after rejection', async t => {
  const f = fixture(t), pending = defer(); let inserts = 0;
  const modal = pickReference(async row => { assert.equal(row.title, 'Synthetic document'); if (++inserts === 1) return pending.promise; }, { signal: f.scope.signal });
  const query = modal.querySelector('input'); query.value = 'Synthetic'; query.oninput();
  await new Promise(resolve => setTimeout(resolve, 220));
  const choice = named(modal, 'Synthetic document'); await click(choice);
  const saving = modal.submit(); await tick();
  assert.equal(modal.isConnected, true); assert.equal(query.disabled, true); assert.equal(choice.disabled, true);
  pending.reject(Error('Pin validation failed')); await saving;
  assert.equal(modal.isConnected, true); assert.match(modal.textContent, /Pin validation failed/);
  assert.equal(choice.getAttribute('aria-pressed'), 'true'); assert.equal(query.disabled, false);
  await modal.submit(); assert.equal(inserts, 2); assert.equal(modal.isConnected, false);
});

test('pin retries retain the same captured candidate and UUID even after an uncertain successful write', async t => {
  const f = fixture(t); f.server.board.widgets = ['pins']; await f.component.load();
  let first = true;
  f.campaigns.prepare = async (_id, action, payload, requestId) => {
    f.calls.push({ action, payload: structuredClone(payload), requestId });
    if (first) {
      first = false; f.server.board.revision = 2; f.server.board.pins = [{ ...payload.pins[0], title: 'Synthetic document' }];
      throw Error('Lost pin reply');
    }
    return {};
  };
  await click(named(f.root, 'Pin document')); const modal = f.modals.at(-1), query = modal.querySelector('input');
  query.value = 'Synthetic'; query.oninput(); await new Promise(resolve => setTimeout(resolve, 220));
  await click(named(modal, 'Synthetic document')); await modal.submit();
  assert.equal(modal.isConnected, true); await modal.submit();
  assert.equal(modal.isConnected, false); assert.equal(f.calls.length, 2);
  assert.equal(f.calls[0].requestId, f.calls[1].requestId); assert.deepEqual(f.calls[0].payload, f.calls[1].payload);
});

test('uncertain journal restoration retries keep their reviewed candidate and operation UUID', async t => {
  const f = fixture(t); await f.component.enter('history');
  const chooser = f.root.querySelector('[data-history-journal]'); chooser.value = 'journal'; chooser.dispatchEvent(new Event('change')); await tick();
  await click(named(f.root, 'Compare')); const modal = f.modals.at(-1); let first = true;
  f.transport.journalCommand = async (action, payload, options) => {
    f.calls.push({ action, payload: structuredClone(payload), requestId: options.requestId });
    if (first) { first = false; f.states.get('journals').journals[0].version = 8; throw Error('Lost restore reply'); }
    return {};
  };
  await modal.submit(); assert.equal(modal.isConnected, true); await modal.submit();
  assert.equal(modal.isConnected, false); assert.deepEqual(f.calls[0].payload, f.calls[1].payload);
  assert.equal(f.calls[0].requestId, f.calls[1].requestId); assert.equal(f.calls[1].payload.version, 7);
});

test('quest-board previews render only the native player display cards without GM data or edit controls', async t => {
  const f = fixture(t);
  const shown = { quest_id: 'visible', card: { title: '<b>Visible quest</b>', status: 'active', summary: 'Public summary',
    objectives: [{ text: 'Public objective', completed: false }], rewards: [{ text: 'Public reward' }], assignees: [{ name: 'Visible actor' }],
    gm: { notes: 'PRIVATE GM NOTES' } } };
  f.campaigns.viewAs = async () => ({ member: { id: 'player', name: 'Player' }, journals: [{ id: 'board', title: 'Board', type: 'quest_board', can_open: true,
    board_display_entries: [shown], board_entries: [{ quest_id: 'hidden', card: { title: 'PRIVATE QUEST' } }] }], actors: [], items: [], scenes: [] });
  await f.component.enter('player-view'); const chooser = f.root.querySelector('[data-player-choice]');
  chooser.value = 'player'; chooser.dispatchEvent(new Event('change')); await tick();
  await click(named(f.root.querySelector('[data-player-body]'), 'Board')); const modal = f.modals.at(-1);
  assert.equal(modal.key, 'manager-player-preview'); assert.match(modal.textContent, /<b>Visible quest<\/b>/);
  for (const label of ['Public summary', 'Public objective', 'Public reward', 'Visible actor']) assert.ok(modal.textContent.includes(label));
  assert.equal(modal.textContent.includes('PRIVATE'), false); assert.equal(modal.querySelector('input'), null);
  assert.equal(modal.querySelector('textarea'), null); assert.equal(f.calls.length, 0);
});

test('pending preview imports cannot create a modal after disposal and mounted pickers close with the owner', async t => {
  const pending = defer(), f = fixture(t, { loadModule: () => pending.promise });
  f.campaigns.viewAs = async () => ({ member: { id: 'player', name: 'Player' }, journals: [{ id: 'journal', title: 'Preview journal', type: 'diary', can_open: true }], actors: [], items: [], scenes: [] });
  await f.component.enter('player-view'); const chooser = f.root.querySelector('[data-player-choice]');
  chooser.value = 'player'; chooser.dispatchEvent(new Event('change')); await tick();
  await click(named(f.root.querySelector('[data-player-body]'), 'Preview journal'));
  f.component.destroy(); pending.resolve({ richText() { throw Error('A discarded preview must not mount an editor'); } }); await tick();
  assert.equal(f.modals.some(modal => modal.isConnected), false);
  const picker = pickReference(() => {}, { signal: f.scope.signal });
  f.scope.abort(); assert.equal(picker.isConnected, false);
});

test('dashboard customization retains its opening revision instead of silently rebasing another tab changes', async t => {
  const f = fixture(t); await f.component.load(); await click(named(f.root, 'Customize dashboard'));
  const modal = f.modals.at(-1); f.server.board.revision = 2; await f.component.load({ fresh: true });
  await modal.submit(); assert.equal(f.calls[0].payload.revision, 1);
});
