import { openFormModal as nativeFormModal } from '/static/gravewright_table/form-modal.js';
import { pickReference as nativeReferencePicker } from '/static/gravewright_table/references.js';
import { lineDiff } from './line-diff.js';

/**
 * GM preparation views for the campaign manager: dashboard, session planner,
 * timeline, quest columns, connections, player preview and journal history.
 * Every mutation goes through native journal commands or the preparation API;
 * this module keeps no separate copy of campaign documents.
 */
const STATUSES = { draft: 'Draft', available: 'Available', active: 'Active', completed: 'Completed', failed: 'Failed', archived: 'Archived' };
const WIDGETS = { pins: 'Pinned documents', session: 'Next session', pending: 'Pending work', diagnostics: 'Sheet diagnostics', events: 'Upcoming events' };
const KINDS = { actor: 'Character', item: 'Item', journal: 'Journal', scene: 'Scene', encounter: 'Encounter', track: 'Track', playlist: 'Playlist',
  note: 'Note', session: 'Session plan', event: 'Timeline event', quest: 'Quest', quest_board: 'Quest board', diary: 'Journal', roll_table: 'Roll table' };
const VIA = { link: 'Linked in text', assigned: 'Assigned character', prerequisite: 'Quest prerequisite', board: 'On quest board',
  pin: 'Pinned on scene', token: 'Token on scene', session: 'Session step', timeline: 'Timeline link' };

export function mountPreparation(ctx) {
  const { root, campaignId, campaigns, t, run, open, select } = ctx;
  const $ = selector => root.querySelector(selector);
  const scope = new AbortController();
  const signal = ctx.signal ? AbortSignal.any([scope.signal, ctx.signal]) : scope.signal;
  const alive = () => !signal.aborted;
  const check = () => signal.throwIfAborted();
  const loadModule = ctx.loadModule || (path => import(path));
  let prep = null, loading, selectedSession = null, draft = null, dirty = false, timelineFilter = 'all', timelineMode = 'list';
  let month = new Date(), connection = null, preview = null, historyJournal = '';
  let readEpoch = 0, historyEpoch = 0, previewEpoch = 0, comparisonEpoch = 0, connectionEpoch = 0, sessionSaving = false;
  const attempts = new Map(), modals = new Set();
  function trackModal(modal) {
    modals.add(modal);
    modal.addEventListener('close', () => { modals.delete(modal); if (alive()) render({ refreshEditor: true }); }, { once: true });
    return modal;
  }
  function openFormModal(title, fields, save, options) {
    check();
    return trackModal(nativeFormModal(title, fields, async form => { check(); const value = await save(form); check(); return value; }, options));
  }
  function pickReference(insert) {
    check();
    return trackModal(nativeReferencePicker(async row => { check(); const value = await insert(row); check(); return value; }, { signal }));
  }
  function displayError(error) {
    if (error?.name === 'AbortError') return error;
    return Object.assign(new Error(t(error?.message || 'Could not load campaign management.')), { code: error?.code, status: error?.status });
  }
  const refused = error => error?.code === 'conflict' || ['invalid_data', 'invalid_input', 'permission_denied', 'not_found'].includes(error?.code)
    || error?.status >= 400 && error.status < 500 && ![408, 429].includes(error.status);
  function attemptFor(key, fingerprint) {
    let attempt = attempts.get(key);
    if (!attempt || attempt.fingerprint !== fingerprint) { attempt = { fingerprint, id: crypto.randomUUID() }; attempts.set(key, attempt); }
    return attempt;
  }

  function node(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = value;
    return element;
  }
  function authored(tag, value, className) { const element = node(tag, className, value); element.setAttribute('translate', 'no'); return element; }
  function button(label, action, className) {
    const element = node('button', className, t(label)); element.type = 'button';
    element.addEventListener('click', () => { if (alive()) return run(action, element); }, { signal });
    return element;
  }
  function icon(label, glyph, action) {
    const element = button('', action, 'campaign-prep__icon'); element.textContent = glyph;
    element.setAttribute('aria-label', t(label)); element.title = t(label); return element;
  }
  function empty(host, key) { host.replaceChildren(node('p', 'campaign-manager__empty', t(key))); }
  function kind(value) { return t(KINDS[value] || 'Document'); }
  function docs() { return ctx.transport.states.get('journals')?.journals || []; }
  function actors() { return ctx.transport.states.get('actors')?.actors || []; }
  function scenes() { return ctx.transport.states.get('maps')?.maps || []; }
  function questOf(doc) { return doc.quest || doc; }
  function ref(type, id) { return { type, id }; }
  function formatDate(value) {
    if (!value) return '';
    const [year, monthIndex, day] = value.split('-').map(Number);
    return new Date(year, monthIndex - 1, day).toLocaleDateString(document.documentElement.lang || undefined, { dateStyle: 'medium' });
  }
  function chip(entry, { remove } = {}) {
    const row = node('span', 'campaign-prep__chip' + (entry.missing ? ' campaign-prep__chip--missing' : ''));
    const label = button('', () => open(entry), 'campaign-prep__chip-open');
    label.append(authored('span', entry.title || t('Missing document')), node('small', '', kind(entry.kind || entry.type)));
    label.disabled = !!entry.missing;
    row.append(label);
    if (remove) row.append(icon('Remove link', '×', remove));
    return row;
  }

  // One request UUID per logical change; a retry of the same change reuses it.
  async function prepare(action, payload, key) {
    check();
    const fingerprint = JSON.stringify([action, payload]);
    key ||= 'prepare:' + fingerprint;
    const attempt = attemptFor(key, fingerprint);
    await ctx.transport.check();
    check();
    let result;
    try {
      result = await campaigns.prepare(campaignId, action, payload, attempt.id, { signal });
    } catch (error) {
      if (refused(error) && attempts.get(key) === attempt) attempts.delete(key);
      if (alive()) await load({ fresh: true }).catch(() => {});
      throw displayError(error);
    }
    check();
    await load({ fresh: true });
    check();
    if (attempts.get(key) === attempt) attempts.delete(key);
    return result;
  }
  async function journalCommand(action, payload) {
    check();
    const fingerprint = JSON.stringify([action, payload]), key = 'journal:' + fingerprint;
    const attempt = attemptFor(key, fingerprint);
    try {
      const result = await ctx.transport.journalCommand(action, payload, { requestId: attempt.id });
      check(); if (attempts.get(key) === attempt) attempts.delete(key); return result;
    } catch (error) {
      if (refused(error) && attempts.get(key) === attempt) attempts.delete(key);
      if (error.code === 'conflict' && alive()) await ctx.transport.read('journals').catch(() => {});
      throw displayError(error);
    }
  }
  function load({ fresh = false } = {}) {
    check();
    if (!fresh && loading) return loading.promise;
    loading?.controller.abort();
    const controller = new AbortController(), epoch = ++readEpoch;
    const task = { controller, epoch };
    const replacement = () => { check(); return loading && loading !== task ? loading.promise : prep; };
    const requestSignal = AbortSignal.any([signal, controller.signal]);
    task.promise = campaigns.preparation(campaignId, { signal: requestSignal }).then(value => {
      check();
      if (epoch !== readEpoch) return replacement();
      prep = value; render(); return value;
    }).catch(error => {
      if (controller.signal.aborted && alive()) return replacement();
      throw displayError(error);
    }).finally(() => { if (loading === task) loading = undefined; });
    loading = task; return task.promise;
  }

  /* Dashboard */
  function renderDashboard() {
    const host = $('[data-manager-dashboard]'); if (!host || !prep) return;
    host.replaceChildren();
    const header = node('div', 'campaign-prep__heading');
    header.append(node('h2', '', t('Preparation')), button('Customize dashboard', customize));
    host.append(header);
    const grid = node('div', 'campaign-prep__widgets');
    for (const widget of prep.board.widgets) {
      if (widget === 'diagnostics' && !prep.diagnostics.supported) continue;
      const card = node('section', 'campaign-manager__card campaign-prep__widget'); card.dataset.widget = widget;
      card.append(node('h3', '', t(WIDGETS[widget])));
      const body = node('div'); card.append(body); grid.append(card);
      ({ pins: renderPins, session: renderNextSession, pending: renderPending, diagnostics: renderDiagnostics, events: renderUpcoming })[widget](body, card);
    }
    if (!grid.children.length) empty(grid, 'All dashboard panels are hidden. Use Customize dashboard to show them.');
    host.append(grid);
  }
  function renderPins(body, card) {
    card.querySelector('h3').after(button('Pin document', () => {
      let pending;
      return pickReference(row => {
        const identity = JSON.stringify(ref(row.type, row.id));
        if (!pending || pending.identity !== identity) pending = { identity, payload: { revision: prep.board.revision,
          pins: [...prep.board.pins.map(({ type, id }) => ({ type, id })), ref(row.type, row.id)] } };
        return prepare('board-update', pending.payload);
      });
    }, 'campaign-prep__widget-action'));
    if (!prep.board.pins.length) { empty(body, 'Pin the documents you use most while preparing.'); return; }
    const list = node('div', 'campaign-prep__chips');
    for (const pin of prep.board.pins) list.append(chip(pin, { remove: () => prepare('board-update', {
      revision: prep.board.revision, pins: prep.board.pins.filter(row => row !== pin).map(({ type, id }) => ({ type, id })) }) }));
    body.append(list);
  }
  function renderNextSession(body) {
    const next = prep.pending.session;
    if (!next) { body.append(node('p', 'campaign-prep__muted', t('No planned session.'))); body.append(button('Plan a session', () => select('sessions'))); return; }
    body.append(authored('strong', next.title), node('p', 'campaign-prep__muted', next.scheduledFor ? formatDate(next.scheduledFor) : t('No date')));
    const list = node('ul', 'campaign-prep__list');
    for (const step of next.steps.slice(0, 6)) {
      const item = node('li'); item.append(authored('span', step.title), node('small', '', ' · ' + kind(step.kind))); list.append(item);
    }
    for (const row of next.checklist.slice(0, 6)) list.append(authored('li', '☐ ' + row.text));
    if (!list.children.length) list.append(node('li', '', t('Every material is ready.')));
    body.append(list, button('Open session plan', () => chooseSession(next.id, true)));
  }
  function renderPending(body) {
    const { unassigned, blocked, carried } = prep.pending;
    const list = node('ul', 'campaign-prep__list');
    for (const quest of unassigned) {
      const item = node('li'); item.append(button('', () => open(ref('journal', quest.id)), 'campaign-prep__link'));
      item.firstChild.append(authored('span', quest.title), node('small', '', ' · ' + t('No assigned characters'))); list.append(item);
    }
    for (const quest of blocked) {
      const item = node('li'); item.append(button('', () => open(ref('journal', quest.id)), 'campaign-prep__link'));
      item.firstChild.append(authored('span', quest.title), node('small', '', ' · ' + t('Active before its prerequisites'))); list.append(item);
    }
    for (const row of carried) {
      const item = node('li'); item.append(authored('span', row.text), node('small', '', ' · ' + t('From') + ' '), authored('small', row.sessionTitle)); list.append(item);
    }
    if (!list.children.length) empty(body, 'No pending work.'); else body.append(list);
  }
  function renderDiagnostics(body) {
    const { issues, error } = prep.diagnostics;
    if (error) { body.append(node('p', 'campaign-prep__muted', t(error))); return; }
    if (!issues.length) { empty(body, 'No sheet problems found.'); return; }
    const list = node('ul', 'campaign-prep__list');
    for (const issue of issues.slice(0, 20)) {
      const item = node('li'), link = button('', () => open(ref('actor', issue.actorId)), 'campaign-prep__link');
      link.append(authored('strong', issue.actorName));
      item.append(link, node('span', '', ' ' + t(issue.message, issue.params))); list.append(item);
    }
    if (issues.length > 20) list.append(node('li', 'campaign-prep__muted', t('{0} more problems', [issues.length - 20])));
    body.append(list);
  }
  function renderUpcoming(body) {
    const events = prep.events.filter(event => event.upcoming).slice(0, 6);
    if (!events.length) { empty(body, 'No upcoming events.'); return; }
    const list = node('ul', 'campaign-prep__list');
    for (const event of events) {
      const item = node('li'); item.append(authored('strong', event.title));
      const when = [event.worldDate, formatDate(event.date)].filter(Boolean).join(' · ');
      if (when) item.append(authored('small', ' · ' + when));
      list.append(item);
    }
    body.append(list, button('Open timeline', () => select('timeline')));
  }
  function customize() {
    const revision = prep.board.revision;
    let order = [...prep.board.widgets, ...Object.keys(WIDGETS).filter(key => !prep.board.widgets.includes(key))];
    const shown = new Set(prep.board.widgets);
    const modal = openFormModal(t('Customize dashboard'), [], () => prepare('board-update', {
      revision, widgets: order.filter(key => shown.has(key)) }, 'dashboard'), { key: 'manager-dashboard', submitLabel: t('Save') });
    const list = node('div', 'campaign-prep__order'); modal.querySelector('[data-fields]').append(list);
    const paint = () => {
      list.replaceChildren();
      order.forEach((key, index) => {
        const row = node('div', 'campaign-prep__order-row'), label = node('label'), box = node('input');
        box.type = 'checkbox'; box.checked = shown.has(key);
        box.addEventListener('change', () => { if (box.checked) shown.add(key); else shown.delete(key); });
        label.append(box, node('span', '', t(WIDGETS[key])));
        const up = node('button', 'campaign-prep__icon', '↑'), down = node('button', 'campaign-prep__icon', '↓');
        for (const [control, offset, name] of [[up, -1, 'Move up'], [down, 1, 'Move down']]) {
          control.type = 'button'; control.setAttribute('aria-label', t(name) + ': ' + t(WIDGETS[key]));
          control.disabled = index + offset < 0 || index + offset >= order.length;
          control.addEventListener('click', () => {
            [order[index], order[index + offset]] = [order[index + offset], order[index]]; paint();
            list.querySelectorAll('.campaign-prep__order-row')[index + offset]?.querySelectorAll('button')[offset < 0 ? 0 : 1]?.focus();
          });
        }
        row.append(label, up, down); list.append(row);
      });
    };
    paint();
  }

  /* Session planner */
  function sessionList() { return prep?.sessions || []; }
  function current() { return sessionList().find(row => row.id === selectedSession) || null; }
  function chooseSession(id, navigate = false) {
    check();
    if (sessionSaving) return;
    if (id !== selectedSession) {
      if (dirty) throw Error(t('Save or discard the current session plan first.'));
      selectedSession = id; draft = null;
    }
    return navigate ? select('sessions') : renderSessions();
  }
  function edit() {
    const saved = current();
    if (!saved) { if (dirty && draft?.id === selectedSession) return draft; draft = null; dirty = false; return null; }
    if (!draft || draft.id !== saved.id || (!dirty && draft.revision !== saved.revision)) {
      draft = structuredClone(saved); dirty = false;
    }
    return draft;
  }
  function touch() { dirty = true; renderSessionEditor(); }
  function renderSessions({ keepEditor = false } = {}) {
    const host = $('[data-manager-sessions]'); if (!host || !prep) return;
    const list = host.querySelector('[data-session-list]');
    list.replaceChildren();
    if (!sessionList().length) empty(list, 'No session plans yet.');
    for (const status of ['planned', 'completed']) {
      const rows = sessionList().filter(row => row.status === status);
      if (!rows.length) continue;
      list.append(node('h3', 'campaign-prep__group', t(status === 'planned' ? 'Planned' : 'Completed')));
      for (const row of rows) {
        const item = button('', () => chooseSession(row.id), 'campaign-prep__session');
        item.setAttribute('aria-current', String(row.id === selectedSession));
        const done = row.steps.filter(step => step.done).length + row.checklist.filter(entry => entry.done).length;
        const total = row.steps.length + row.checklist.length;
        item.append(authored('strong', row.title), node('small', '', [row.scheduledFor ? formatDate(row.scheduledFor) : t('No date'), `${done}/${total}`].join(' · ')));
        list.append(item);
      }
    }
    if (!keepEditor) renderSessionEditor();
  }
  function renderSessionEditor() {
    const host = $('[data-session-editor]'); if (!host) return;
    const plan = edit();
    host.replaceChildren();
    if (!plan) { empty(host, 'Choose a session plan or create a new one.'); return; }
    const completed = plan.status === 'completed';
    const form = node('div', 'campaign-prep__editor');
    const top = node('div', 'campaign-prep__fields');
    const title = field('Title', 'input', plan.title, value => { plan.title = value; });
    title.querySelector('input').maxLength = 120; title.querySelector('input').required = true;
    const when = field('Session date', 'input', plan.scheduledFor || '', value => { plan.scheduledFor = value || null; });
    when.querySelector('input').type = 'date';
    top.append(title, when); form.append(top);

    const steps = node('section', 'campaign-prep__block');
    steps.append(node('h3', '', t('Sequence')));
    const stepList = node('ol', 'campaign-prep__steps');
    plan.steps.forEach((step, index) => {
      const item = node('li', 'campaign-prep__step' + (step.done ? ' campaign-prep__step--done' : ''));
      const label = node('label'), box = node('input'); box.type = 'checkbox'; box.checked = step.done;
      box.addEventListener('change', () => { step.done = box.checked; touch(); });
      label.append(box, authored('span', step.title || step.label));
      const meta = node('small', '', kind(step.kind) + (step.missing ? ' · ' + t('Missing document') : ''));
      const actions = node('span', 'campaign-prep__row-actions');
      if (step.refId && !step.missing) actions.append(button('Open', () => open(ref(step.kind, step.refId))));
      actions.append(icon('Move up', '↑', () => { move(plan.steps, index, -1); touch(); }), icon('Move down', '↓', () => { move(plan.steps, index, 1); touch(); }),
        icon('Remove step', '×', () => { plan.steps.splice(index, 1); touch(); }));
      item.append(label, meta, actions); stepList.append(item);
    });
    if (!plan.steps.length) stepList.append(node('li', 'campaign-prep__muted', t('Add scenes, encounters, quests, documents and audio in the order you plan to use them.')));
    const add = node('div', 'campaign-prep__add');
    add.append(button('Add document', () => pickReference(row => {
      plan.steps.push({ id: crypto.randomUUID().slice(0, 12), kind: row.type, refId: row.id, label: '', title: row.title, done: false }); touch();
    })), button('Add encounter', () => chooseFrom('Add encounter', scenes(), 'encounter', plan)),
    button('Add audio', async () => {
      const audio = await ctx.audio();
      chooseFrom('Add audio', [...(audio?.playlists || []).map(row => ({ ...row, kind: 'playlist' })), ...(audio?.tracks || []).map(row => ({ ...row, kind: 'track' }))], null, plan);
    }), button('Add note', () => openFormModal(t('Add note'), [{ name: 'label', label: t('Note'), required: true }], form => {
      plan.steps.push({ id: crypto.randomUUID().slice(0, 12), kind: 'note', refId: null, label: form.elements.label.value, title: form.elements.label.value, done: false }); touch();
    }, { key: 'manager-session-note', submitLabel: t('Add') })));
    steps.append(stepList, add); form.append(steps);

    const checklist = node('section', 'campaign-prep__block');
    checklist.append(node('h3', '', t('Checklist')));
    const checks = node('ul', 'campaign-prep__checks');
    plan.checklist.forEach((entry, index) => {
      const item = node('li'), label = node('label'), box = node('input'); box.type = 'checkbox'; box.checked = entry.done;
      box.addEventListener('change', () => { entry.done = box.checked; touch(); });
      label.append(box, authored('span', entry.text)); item.append(label, icon('Remove entry', '×', () => { plan.checklist.splice(index, 1); touch(); }));
      checks.append(item);
    });
    const entry = node('form', 'campaign-prep__inline'), input = node('input');
    input.maxLength = 240; input.placeholder = t('New checklist entry'); input.setAttribute('aria-label', t('New checklist entry'));
    const addEntry = node('button', '', t('Add')); addEntry.type = 'submit';
    entry.append(input, addEntry);
    entry.addEventListener('submit', event => {
      event.preventDefault(); if (!input.value.trim()) return;
      plan.checklist.push({ id: crypto.randomUUID().slice(0, 12), text: input.value.trim(), done: false }); touch();
      $('[data-session-editor] .campaign-prep__inline input')?.focus();
    });
    checklist.append(checks, entry); form.append(checklist);

    const notes = field('Private notes', 'textarea', plan.notes, value => { plan.notes = value; });
    notes.querySelector('textarea').maxLength = 8000; notes.querySelector('textarea').rows = 5;
    notes.append(node('small', 'campaign-prep__muted', t('Only campaign game masters can read these notes.')));
    form.append(notes);

    if (completed) {
      const wrap = node('section', 'campaign-prep__block');
      wrap.append(node('h3', '', t('Session summary')), authored('p', plan.summary || '—', 'campaign-prep__summary'));
      if (plan.pending.length) {
        wrap.append(node('h3', '', t('Pending')));
        const list = node('ul', 'campaign-prep__list'); for (const row of plan.pending) list.append(authored('li', row.text)); wrap.append(list);
      }
      form.append(wrap);
    }
    const footer = node('div', 'campaign-prep__footer');
    footer.dataset.sessionFooter = ''; renderSessionFooter(footer, plan);
    form.append(footer);
    host.append(form);
  }
  function renderSessionFooter(footer, plan) {
    footer.replaceChildren();
    const completed = plan.status === 'completed';
    const save = button(dirty ? 'Save changes' : 'Saved', saveSession); save.disabled = !dirty || sessionSaving; save.classList.add('campaign-prep__primary');
    footer.append(save);
    if (dirty) footer.append(button('Discard changes', () => { draft = null; dirty = false; renderSessionEditor(); }));
    footer.append(completed ? button('Reopen session', () => prepare('session-reopen', { id: plan.id, revision: plan.revision }))
      : button('Finish session', finishSession), button('Delete', () => confirm('Delete session plan', plan.title,
      () => prepare('session-delete', { id: plan.id, revision: plan.revision }).then(() => { check(); selectedSession = null; draft = null; dirty = false; renderSessions(); }))));
  }
  function field(label, tag, value, change) {
    const wrap = node('label', 'campaign-prep__field'); wrap.append(node('span', '', t(label)));
    const input = node(tag); input.value = value ?? ''; input.setAttribute('translate', 'no');
    input.addEventListener('input', () => { if (!alive() || sessionSaving) return; change(input.value); if (!dirty) { dirty = true; refreshFooter(); } }, { signal });
    wrap.append(input); return wrap;
  }
  function refreshFooter() {
    const footer = $('[data-session-footer]');
    if (footer && draft) renderSessionFooter(footer, draft);
  }
  function move(list, index, offset) {
    const target = index + offset; if (target < 0 || target >= list.length) return;
    [list[index], list[target]] = [list[target], list[index]];
  }
  function chooseFrom(title, rows, forced, plan) {
    if (!rows.length) throw Error(t('Nothing is available to add.'));
    openFormModal(t(title), [{ name: 'choice', label: t('Choose'), options: rows.map((row, index) => ({ value: String(index), label: row.name })) }], form => {
      const row = rows[Number(form.elements.choice.value)];
      plan.steps.push({ id: crypto.randomUUID().slice(0, 12), kind: forced || row.kind, refId: row.id, label: '', title: row.name, done: false }); touch();
    }, { key: 'manager-session-choice', submitLabel: t('Add') });
  }
  function payloadOf(plan) {
    return { id: plan.id, revision: plan.revision, title: plan.title, scheduledFor: plan.scheduledFor || null, notes: plan.notes,
      steps: plan.steps.map(({ id, kind: stepKind, refId, label, done }) => ({ id, kind: stepKind, refId, label: stepKind === 'note' ? label : '', done })),
      checklist: plan.checklist.map(({ id, text, done }) => ({ id, text, done })) };
  }
  async function saveSession() {
    if (!draft || !dirty || sessionSaving) return;
    if (!draft.title.trim()) throw Error(t('Enter a title.'));
    const candidate = payloadOf(draft), opening = draft, fingerprint = JSON.stringify(candidate);
    const editor = $('[data-session-editor]');
    const locked = [...editor.querySelectorAll('input,textarea,select,button')].map(control => [control, control.disabled]);
    sessionSaving = true; editor.setAttribute('aria-busy', 'true');
    for (const [control] of locked) control.disabled = true;
    try {
      const result = await prepare('session-update', candidate, 'session-' + draft.id);
      check();
      if (draft === opening && JSON.stringify(payloadOf(draft)) === fingerprint) { draft = null; dirty = false; }
      else if (draft === opening && Number.isInteger(result.revision)) {
        // Only this confirmed write may advance a retained draft's revision.
        draft.revision = result.revision; dirty = true;
      }
    } catch (error) {
      if (error.code === 'conflict') throw Object.assign(new Error(t('This session plan changed. Your draft is preserved. Discard it to review the current version before saving again.')), { code: error.code });
      throw error;
    } finally {
      sessionSaving = false;
      for (const [control, disabled] of locked) if (control.isConnected) control.disabled = disabled;
      editor.removeAttribute('aria-busy');
      if (alive()) renderSessions();
    }
  }
  function newSession() {
    if (dirty) throw Error(t('Save or discard the current session plan first.'));
    openFormModal(t('New session plan'), [{ name: 'title', label: t('Title'), required: true },
      { name: 'date', label: t('Session date'), type: 'date' }], async form => {
      const result = await prepare('session-create', { title: form.elements.title.value, scheduledFor: form.elements.date.value || null }, 'session-create');
      selectedSession = result.id; draft = null; renderSessions();
    }, { key: 'manager-session-create', submitLabel: t('Create') }).querySelector('[name=title]').maxLength = 120;
  }
  async function finishSession() {
    if (dirty) await saveSession();
    check();
    if (dirty || sessionSaving) throw Error(t('Save or discard the current session plan first.'));
    const plan = current(); if (!plan) return;
    const remaining = [...plan.steps.filter(step => !step.done).map(step => step.title || step.label), ...plan.checklist.filter(row => !row.done).map(row => row.text)];
    const modal = openFormModal(t('Finish session'), [
      { name: 'summary', label: t('Session summary'), multiline: true },
      { name: 'pending', label: t('Pending (one per line)'), multiline: true, value: remaining.join('\n') },
    ], form => prepare('session-finish', { id: plan.id, revision: plan.revision, summary: form.elements.summary.value,
      pending: form.elements.pending.value.split('\n').map(text => text.trim()).filter(Boolean).slice(0, 32).map(text => ({ text: text.slice(0, 240), done: false })) },
    'session-finish-' + plan.id), { key: 'manager-session-finish', submitLabel: t('Finish session') });
    modal.querySelector('[name=summary]').maxLength = 8000;
  }
  function confirm(title, name, action) {
    const modal = openFormModal(t(title), [], action, { key: 'manager-confirm', submitLabel: t('Delete') });
    modal.querySelector('[data-fields]').append(authored('p', name), node('p', '', t('This cannot be undone.')));
  }

  /* Timeline and calendar */
  function renderTimeline() {
    const host = $('[data-manager-timeline]'); if (!host || !prep) return;
    host.querySelector('[data-timeline-filter]').value = timelineFilter;
    for (const toggle of host.querySelectorAll('[data-timeline-mode]')) toggle.setAttribute('aria-pressed', String(toggle.dataset.timelineMode === timelineMode));
    const body = host.querySelector('[data-timeline-body]'); body.replaceChildren();
    const events = prep.events.filter(event => timelineFilter === 'all' || (timelineFilter === 'upcoming') === event.upcoming);
    if (timelineMode === 'calendar') { renderCalendar(body, events); return; }
    if (!events.length) { empty(body, 'No timeline events yet.'); return; }
    const list = node('ol', 'campaign-prep__timeline');
    events.forEach((event, index) => {
      const item = node('li', 'campaign-prep__event' + (event.upcoming ? ' campaign-prep__event--upcoming' : ''));
      const head = node('div', 'campaign-prep__event-head');
      const when = node('div', 'campaign-prep__event-when');
      if (event.worldDate) when.append(authored('strong', event.worldDate));
      if (event.date) when.append(node('small', '', formatDate(event.date)));
      if (event.upcoming) when.append(node('span', 'campaign-prep__badge', t('Upcoming')));
      head.append(when, authored('h3', event.title));
      item.append(head);
      if (event.description) item.append(authored('p', event.description, 'campaign-prep__summary'));
      const links = node('div', 'campaign-prep__chips');
      for (const link of event.links) links.append(chip(link, { remove: () => prepare('event-update', { id: event.id, revision: event.revision,
        links: event.links.filter(row => row !== link).map(({ type, id }) => ({ type, id })) }) }));
      item.append(links);
      const actions = node('div', 'campaign-prep__row-actions');
      actions.append(button('Link document', () => pickReference(row => prepare('event-update', { id: event.id, revision: event.revision,
        links: [...event.links.map(({ type, id }) => ({ type, id })), ref(row.type, row.id)] }))),
      button('Edit', () => eventForm(event)),
      icon('Move earlier', '↑', () => swap(events, index, -1)), icon('Move later', '↓', () => swap(events, index, 1)),
      button('Delete', () => confirm('Delete event', event.title, () => prepare('event-delete', { id: event.id, revision: event.revision }))));
      item.append(actions); list.append(item);
    });
    body.append(list);
  }
  async function swap(events, index, offset) {
    const first = events[index], second = events[index + offset];
    if (!second) return;
    let a = first.position, b = second.position;
    if (a === b) b = a + offset;
    await prepare('event-update', { id: first.id, revision: first.revision, position: b });
    const fresh = prep.events.find(row => row.id === second.id);
    if (fresh) await prepare('event-update', { id: fresh.id, revision: fresh.revision, position: a });
  }
  function eventForm(event) {
    const modal = openFormModal(t(event ? 'Edit event' : 'New event'), [
      { name: 'title', label: t('Title'), required: true, value: event?.title },
      { name: 'worldDate', label: t('In-world date'), value: event?.worldDate },
      { name: 'date', label: t('Calendar date'), type: 'date', value: event?.date || '' },
      { name: 'upcoming', label: t('Upcoming event'), type: 'checkbox', value: event?.upcoming },
      { name: 'description', label: t('Description'), multiline: true, value: event?.description },
    ], form => {
      const payload = { title: form.elements.title.value, worldDate: form.elements.worldDate.value, date: form.elements.date.value || null,
        upcoming: form.elements.upcoming.checked, description: form.elements.description.value };
      return event ? prepare('event-update', { id: event.id, revision: event.revision, ...payload }, 'event-' + event.id)
        : prepare('event-create', payload, 'event-create');
    }, { key: 'manager-event', submitLabel: t(event ? 'Save' : 'Create') });
    modal.querySelector('[name=title]').maxLength = 120; modal.querySelector('[name=worldDate]').maxLength = 80;
    modal.querySelector('[name=description]').maxLength = 4000;
  }
  function renderCalendar(body, events) {
    const year = month.getFullYear(), index = month.getMonth();
    const bar = node('div', 'campaign-prep__calendar-bar');
    const label = node('strong', '', new Date(year, index, 1).toLocaleDateString(document.documentElement.lang || undefined, { month: 'long', year: 'numeric' }));
    bar.append(icon('Previous month', '‹', () => { month = new Date(year, index - 1, 1); renderTimeline(); }), label,
      icon('Next month', '›', () => { month = new Date(year, index + 1, 1); renderTimeline(); }), button('Today', () => { month = new Date(); renderTimeline(); }));
    body.append(bar);
    const byDay = new Map();
    const key = day => `${year}-${String(index + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    for (const event of events) if (event.date) byDay.set(event.date, [...(byDay.get(event.date) || []), { title: event.title, kind: 'event', upcoming: event.upcoming }]);
    for (const plan of sessionList()) if (plan.scheduledFor) byDay.set(plan.scheduledFor, [...(byDay.get(plan.scheduledFor) || []), { title: plan.title, kind: 'session', id: plan.id }]);
    const grid = node('div', 'campaign-prep__calendar'); grid.setAttribute('role', 'grid'); grid.setAttribute('aria-label', label.textContent);
    const first = new Date(year, index, 1), offset = (first.getDay() + 6) % 7, days = new Date(year, index + 1, 0).getDate();
    for (let weekday = 0; weekday < 7; weekday++) {
      grid.append(node('span', 'campaign-prep__weekday', new Date(2024, 0, 1 + weekday).toLocaleDateString(document.documentElement.lang || undefined, { weekday: 'short' })));
    }
    for (let blank = 0; blank < offset; blank++) grid.append(node('span', 'campaign-prep__day campaign-prep__day--blank'));
    const today = new Date(), todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    let undated = 0;
    for (let day = 1; day <= days; day++) {
      const cell = node('div', 'campaign-prep__day' + (key(day) === todayKey ? ' campaign-prep__day--today' : '')); cell.setAttribute('role', 'gridcell');
      cell.append(node('span', 'campaign-prep__day-number', String(day)));
      for (const entry of byDay.get(key(day)) || []) {
        const tag = entry.kind === 'session' ? button('', () => chooseSession(entry.id, true), 'campaign-prep__day-entry campaign-prep__day-entry--session')
          : node('span', 'campaign-prep__day-entry');
        tag.append(authored('span', entry.title)); tag.title = t(entry.kind === 'session' ? 'Session plan' : 'Timeline event');
        cell.append(tag);
      }
      grid.append(cell);
    }
    undated = events.filter(event => !event.date).length;
    body.append(grid);
    if (undated) body.append(node('p', 'campaign-prep__muted', t('{0} events have only an in-world date and appear in the timeline view.', [undated])));
  }

  /* Quest columns */
  function renderQuests() {
    const host = $('[data-manager-quests]'); if (!host) return;
    const filter = $('[data-manager-quest-status]')?.value || '';
    const quests = docs().filter(doc => doc.type === 'quest');
    const byId = new Map(quests.map(doc => [doc.id, doc]));
    const names = new Map(actors().map(actor => [actor.id, actor.name]));
    host.replaceChildren();
    host.classList.add('campaign-prep__board');
    for (const [status, label] of Object.entries(STATUSES)) {
      if (filter && filter !== status) continue;
      const column = node('section', 'campaign-prep__column'); column.dataset.status = status;
      const rows = quests.filter(doc => (questOf(doc).status || 'draft') === status);
      const heading = node('h3'); heading.append(node('span', '', t(label)), node('small', '', String(rows.length)));
      column.append(heading);
      column.addEventListener('dragover', event => { if (event.dataTransfer.types.includes('application/x-gravewright-quest')) { event.preventDefault(); column.classList.add('campaign-prep__column--over'); } });
      column.addEventListener('dragleave', () => column.classList.remove('campaign-prep__column--over'));
      column.addEventListener('drop', event => {
        column.classList.remove('campaign-prep__column--over');
        const id = event.dataTransfer.getData('application/x-gravewright-quest'), doc = byId.get(id);
        if (!doc) return; event.preventDefault();
        if ((questOf(doc).status || 'draft') !== status) void run(() => setStatus(doc, status));
      });
      const list = node('div', 'campaign-prep__cards');
      for (const doc of rows) list.append(questCard(doc, byId, names));
      if (!rows.length) list.append(node('p', 'campaign-prep__muted', t('No quests')));
      column.append(list); host.append(column);
    }
  }
  function questCard(doc, byId, names) {
    const quest = questOf(doc), goals = quest.objectives || [], prereqs = quest.prerequisites || [];
    const card = node('article', 'campaign-prep__card'); card.dataset.managerQuestId = doc.id;
    card.draggable = !!doc.can_edit;
    card.addEventListener('dragstart', event => { event.dataTransfer.setData('application/x-gravewright-quest', doc.id); event.dataTransfer.effectAllowed = 'move'; });
    card.append(authored('strong', doc.title));
    const waiting = prereqs.filter(id => (questOf(byId.get(id) || {}).status) !== 'completed');
    if (waiting.length) card.append(node('span', 'campaign-prep__badge campaign-prep__badge--warn', t('Waiting for {0} prerequisites', [waiting.length])));
    const people = (quest.assignees || []).map(id => names.get(id)).filter(Boolean);
    card.append(node('small', 'campaign-prep__muted', people.length ? '' : t('No assigned characters')));
    if (people.length) card.lastChild.append(...people.map((name, index) => authored('span', (index ? ', ' : '') + name)));
    if (goals.length) {
      const progress = node('progress'); progress.max = goals.length; progress.value = goals.filter(goal => goal.completed).length;
      progress.setAttribute('aria-label', t('Objectives'));
      const details = node('details'), summary = node('summary', '', `${progress.value}/${goals.length} ${t('Objectives')}`);
      details.append(summary);
      for (const goal of goals) {
        const label = node('label', 'campaign-prep__objective'), box = node('input'); box.type = 'checkbox'; box.checked = goal.completed;
        box.disabled = !doc.can_edit;
        box.addEventListener('change', () => void run(() => journalCommand('objective', { journal_id: doc.id, version: doc.version, objective_id: goal.id, completed: box.checked })));
        label.append(box, authored('span', goal.text)); details.append(label);
      }
      card.append(progress, details);
    }
    if (prereqs.length) {
      const list = node('div', 'campaign-prep__chips');
      for (const id of prereqs) {
        const target = byId.get(id);
        list.append(chip({ type: 'journal', id, kind: 'quest', title: target?.title, missing: !target }));
      }
      card.append(list);
    }
    const actions = node('div', 'campaign-prep__row-actions');
    const moveTo = node('select'); moveTo.setAttribute('aria-label', t('Move quest to'));
    for (const [status, label] of Object.entries(STATUSES)) moveTo.add(new Option(t(label), status));
    moveTo.value = quest.status || 'draft'; moveTo.disabled = !doc.can_edit;
    moveTo.addEventListener('change', () => void run(() => setStatus(doc, moveTo.value)));
    actions.append(moveTo, button('Open', () => open(ref('journal', doc.id))), button('Assign', () => assign(doc)),
      button('Prerequisites', () => prerequisites(doc, byId)), button('Where used', () => showConnections(ref('journal', doc.id))));
    card.append(actions);
    return card;
  }
  function setStatus(doc, status) { return journalCommand('status', { journal_id: doc.id, version: doc.version, status }); }
  function checkboxes(title, rows, chosen, save, key) {
    if (!rows.length) throw Error(t('Nothing is available to choose.'));
    const modal = openFormModal(t(title), [], form => save([...form.querySelectorAll('[data-choice]:checked')].map(box => box.value)), { key, submitLabel: t('Save') });
    const list = node('div', 'campaign-prep__choices');
    for (const row of rows) {
      const label = node('label'), box = node('input'); box.type = 'checkbox'; box.value = row.id; box.dataset.choice = ''; box.checked = chosen.includes(row.id);
      label.append(box, authored('span', row.name)); list.append(label);
    }
    modal.querySelector('[data-fields]').append(list);
  }
  function assign(doc) {
    checkboxes('Assign characters', actors().map(actor => ({ id: actor.id, name: actor.name })), questOf(doc).assignees || [],
      values => journalCommand('assign', { journal_id: doc.id, version: doc.version, assignees: values }), 'manager-quest-assign');
  }
  function prerequisites(doc, byId) {
    checkboxes('Prerequisites', [...byId.values()].filter(row => row.id !== doc.id).map(row => ({ id: row.id, name: row.title })),
      questOf(doc).prerequisites || [], values => journalCommand('prerequisites', { journal_id: doc.id, version: doc.version, prerequisites: values }),
      'manager-quest-prerequisites');
  }

  /* Connections */
  async function showConnections(target) {
    connection = { target, value: null };
    await select('connections');
  }
  async function renderConnections() {
    const host = $('[data-manager-connections]'); if (!host || !alive()) return;
    const body = host.querySelector('[data-connections-body]');
    if (!connection) { empty(body, 'Choose a document to see its links and where it is used.'); return; }
    if (!connection.value) {
      body.replaceChildren(node('p', 'campaign-prep__muted', t('Loading...')));
      const wanted = connection;
      const epoch = ++connectionEpoch;
      const value = await campaigns.references(campaignId, wanted.target.type, wanted.target.id, { signal });
      if (!alive() || connection !== wanted || epoch !== connectionEpoch) return;
      connection.value = value;
    }
    const { target, links, usedBy } = connection.value;
    body.replaceChildren();
    const head = node('div', 'campaign-prep__heading');
    const title = node('h2'); title.append(authored('span', target.title), node('small', '', ' · ' + kind(target.type)));
    head.append(title, button('Open', () => open(target)));
    body.append(head);
    const columns = node('div', 'campaign-manager__columns');
    for (const [label, rows, hint] of [['Links to', links, 'This document does not link to other content.'], ['Used by', usedBy, 'Nothing uses this document yet.']]) {
      const card = node('section', 'campaign-manager__card'); card.append(node('h3', '', t(label)));
      if (!rows.length) card.append(node('p', 'campaign-prep__muted', t(hint)));
      for (const row of rows) {
        const item = node('div', 'campaign-prep__usage');
        const opener = button('', () => openUsage(row), 'campaign-prep__link'); opener.disabled = !!row.missing;
        opener.append(authored('span', row.title || t('Missing document')));
        item.append(opener, node('small', '', [kind(row.kind || row.type), t(VIA[row.via] || 'Linked in text')].join(' · ')));
        if (['actor', 'item', 'journal', 'scene'].includes(row.type) && !row.missing) item.append(icon('Where used', '⇄', () => showConnections(ref(row.type, row.id))));
        card.append(item);
      }
      columns.append(card);
    }
    body.append(columns);
  }
  function openUsage(row) {
    if (row.type === 'session') return chooseSession(row.id, true);
    if (row.type === 'event') return select('timeline');
    return open(row);
  }

  /* Player preview */
  function renderPlayerView() {
    const host = $('[data-manager-player-view]'); if (!host) return;
    const chooser = host.querySelector('[data-player-choice]'), players = (ctx.overview().members || []).filter(member => member.role === 'player');
    const chosen = chooser.value;
    chooser.replaceChildren(new Option(t('Choose a player'), ''));
    for (const member of players) { const option = new Option(member.name, member.id); option.setAttribute('translate', 'no'); chooser.append(option); }
    chooser.value = players.some(member => member.id === chosen) ? chosen : '';
    const body = host.querySelector('[data-player-body]');
    if (!players.length) { empty(body, 'This campaign has no players yet.'); return; }
    if (!preview || preview.member.id !== chooser.value) { empty(body, 'Choose a player to see exactly what they can open.'); return; }
    body.replaceChildren();
    const intro = node('p', 'campaign-manager__hint'); intro.append(node('span', '', t('Showing what this player receives from the server:') + ' '), authored('strong', preview.member.name));
    body.append(intro);
    const grid = node('div', 'campaign-prep__preview');
    const journalsCard = section('Journals and quests');
    const openable = preview.journals.filter(doc => doc.can_open), listed = preview.journals.filter(doc => !doc.can_open);
    for (const doc of openable) {
      const row = node('div', 'campaign-prep__usage');
      const opener = button('', () => previewJournal(doc), 'campaign-prep__link'); opener.append(authored('span', doc.title));
      const pages = doc.sections ? ' · ' + t('{0} pages', [doc.sections.length]) : '';
      row.append(opener, node('small', '', kind(doc.type) + pages + (doc.can_edit ? ' · ' + t('Can edit') : '')));
      journalsCard.append(row);
    }
    for (const doc of listed) {
      const row = node('div', 'campaign-prep__usage'); row.append(authored('span', doc.title), node('small', '', t('Title only'))); journalsCard.append(row);
    }
    if (!preview.journals.length) journalsCard.append(node('p', 'campaign-prep__muted', t('No journals are visible to this player.')));
    grid.append(journalsCard);
    for (const [label, rows, emptyKey] of [['Characters', preview.actors, 'No characters are visible to this player.'],
      ['Items', preview.items, 'No items are visible to this player.'], ['Scenes', preview.scenes, 'No scene is currently visible to this player.']]) {
      const card = section(label);
      for (const row of rows) {
        const line = node('div', 'campaign-prep__usage'); line.append(authored('span', row.name));
        if ('canOpen' in row) line.append(node('small', '', t(row.canEdit ? 'Can edit' : row.canOpen ? 'Can view' : 'Title only')));
        card.append(line);
      }
      if (!rows.length) card.append(node('p', 'campaign-prep__muted', t(emptyKey)));
      grid.append(card);
    }
    body.append(grid);
  }
  function section(label) { const card = node('section', 'campaign-manager__card'); card.append(node('h3', '', t(label))); return card; }
  async function loadPreview(memberId) {
    check();
    const epoch = ++previewEpoch;
    for (const modal of modals) if (modal.dataset.preparationPreview !== undefined) modal.close(true);
    preview = null; renderPlayerView();
    if (!memberId) return;
    const value = await campaigns.viewAs(campaignId, memberId, { signal });
    if (alive() && epoch === previewEpoch && $('[data-player-choice]').value === memberId) { preview = value; renderPlayerView(); }
  }
  async function previewJournal(doc) {
    const requested = preview;
    const { richText } = await loadModule('/static/gravewright_journals/editor.js');
    if (!alive() || preview !== requested || !preview?.journals.includes(doc) || $('[data-manager-player-view]')?.hidden) return;
    const modal = openFormModal(doc.title, [], () => {}, { key: 'manager-player-preview', submitLabel: t('Close') });
    modal.dataset.preparationPreview = '';
    modal.querySelector('header strong')?.setAttribute('translate', 'no');
    modal.classList.add('campaign-prep__preview-modal');
    const fields = modal.querySelector('[data-fields]');
    fields.append(node('p', 'campaign-manager__hint', t('Read-only preview of this player\'s version.')));
    const editors = [];
    const rich = value => { const host = node('div'); fields.append(host); editors.push(richText(host, value, true, null, doc.title)); };
    if (doc.type === 'diary') {
      rich(doc.content_doc);
      for (const page of doc.sections || []) { fields.append(authored('h3', page.title)); rich(page.content); }
    } else if (doc.quest) {
      const quest = doc.quest;
      fields.append(node('p', '', t(STATUSES[quest.status] || 'Draft')));
      if (quest.public?.summary) fields.append(authored('p', quest.public.summary));
      if (quest.public?.description) rich(quest.public.description);
      const list = node('ul', 'campaign-prep__list');
      for (const goal of quest.objectives || []) list.append(authored('li', (goal.completed ? '☑ ' : '☐ ') + goal.text));
      fields.append(list);
    } else if (doc.type === 'quest_board') {
      const entries = doc.board_display_entries || [];
      if (!entries.length) fields.append(node('p', 'campaign-prep__muted', t('No quests are visible on this board.')));
      for (const entry of entries) {
        const card = entry.card, block = node('section', 'campaign-manager__card');
        block.append(authored('h3', card.title), node('p', '', t(STATUSES[card.status] || 'Draft')));
        if (card.image?.src) {
          const image = node('img'); image.src = card.image.src; image.alt = ''; image.loading = 'lazy';
          image.style.maxWidth = '100%'; image.style.height = 'auto'; block.append(image);
        }
        if (card.summary) block.append(authored('p', card.summary, 'campaign-prep__summary'));
        if (card.location || card.giver) block.append(authored('p', [card.location, card.giver].filter(Boolean).join(' · ')));
        for (const [label, rows] of [['Objectives', card.objectives], ['Rewards', card.rewards]]) if (rows?.length) {
          block.append(node('h4', '', t(label)));
          const list = node('ul', 'campaign-prep__list');
          for (const row of rows) list.append(authored('li', (label === 'Objectives' ? row.completed ? '☑ ' : '☐ ' : '') + row.text));
          block.append(list);
        }
        if (card.assignees?.length) block.append(authored('p', card.assignees.map(actor => actor.name).join(', ')));
        fields.append(block);
      }
    } else if (doc.roll_table) {
      const list = node('ul', 'campaign-prep__list');
      for (const entry of doc.roll_table.entries || []) list.append(authored('li', entry.name + (entry.result ? ': ' + entry.result : '')));
      fields.append(list);
    }
    modal.addEventListener('close', () => { for (const editor of editors) editor?.destroy?.(); }, { once: true });
  }

  /* History and trash */
  async function renderHistory() {
    const host = $('[data-manager-history]'); if (!host || !alive()) return;
    const epoch = ++historyEpoch;
    const chooser = host.querySelector('[data-history-journal]');
    chooser.replaceChildren(new Option(t('Choose a document'), ''));
    for (const doc of docs()) { const option = new Option(doc.title, doc.id); option.setAttribute('translate', 'no'); chooser.append(option); }
    chooser.value = docs().some(doc => doc.id === historyJournal) ? historyJournal : '';
    const requested = chooser.value;
    const versions = host.querySelector('[data-history-versions]'), trash = host.querySelector('[data-history-trash]');
    empty(versions, requested ? 'Loading...' : 'Choose a document to see its earlier versions.');
    const [history, deleted] = await Promise.all([
      requested ? campaigns.journalHistory(campaignId, requested, { signal }) : null,
      campaigns.journalTrash(campaignId, { signal }),
    ]);
    if (!alive() || epoch !== historyEpoch || chooser.value !== requested) return;
    if (!requested) empty(versions, 'Choose a document to see its earlier versions.');
    else if (!history.revisions.length) empty(versions, 'No earlier versions yet. A version is kept each time the document changes.');
    else {
      versions.replaceChildren();
      for (const revision of history.revisions) {
        const row = node('article', 'campaign-manager__row'), info = node('div', 'campaign-manager__row-info');
        info.append(authored('strong', revision.title), node('small', '', [new Date(revision.createdAt).toLocaleString(), revision.author, t('Version {0}', [revision.version])].filter(Boolean).join(' · ')));
        row.append(info, button('Compare', () => compare(revision)));
        versions.append(row);
      }
    }
    trash.replaceChildren();
    for (const entry of deleted.journals) {
      const row = node('article', 'campaign-manager__row'), info = node('div', 'campaign-manager__row-info');
      info.append(authored('strong', entry.title), node('small', '', [kind(entry.type), new Date(entry.createdAt).toLocaleString(), entry.author].filter(Boolean).join(' · ')));
      row.append(info, button('Restore', async () => {
        const result = await journalCommand('restore-deleted', { revision_id: entry.id });
        await renderHistory(); window.gravewrightJournals?.open(result.journal_id);
      }), button('Delete permanently', () => confirm('Delete permanently', entry.title, async () => {
        await journalCommand('trash-purge', { revision_id: entry.id }); await renderHistory();
      })));
      trash.append(row);
    }
    if (!trash.children.length) empty(trash, 'The trash is empty.');
  }
  async function compare(revision) {
    check();
    const epoch = ++comparisonEpoch;
    const value = await campaigns.journalRevision(campaignId, revision.id, { signal });
    if (!alive() || epoch !== comparisonEpoch || $('[data-manager-history]')?.hidden) return;
    const doc = docs().find(row => row.id === revision.journalId);
    const expectedVersion = value.current?.version;
    let stale = false;
    const modal = openFormModal(t('Compare versions'), [], async () => {
      if (stale) throw Error(t('This document changed. Close this comparison and compare again before restoring.'));
      if (!docs().some(row => row.id === revision.journalId) || !Number.isInteger(expectedVersion)) throw Error(t('This document is no longer available.'));
      try {
        await journalCommand('restore-revision', { journal_id: revision.journalId, version: expectedVersion, revision_id: revision.id });
      } catch (error) {
        if (error.code === 'conflict') {
          stale = true; modal.querySelector('[type=submit]').hidden = true;
          throw Error(t('This document changed. Close this comparison and compare again before restoring.'));
        }
        throw error;
      }
      await renderHistory();
    }, { key: 'manager-compare', submitLabel: t('Restore this version') });
    modal.classList.add('campaign-prep__compare-modal');
    if (!doc?.can_edit || !Number.isInteger(expectedVersion)) modal.querySelector('[type=submit]').hidden = true;
    const legend = node('p', 'campaign-manager__hint', t('Lines marked − exist only in the earlier version; lines marked + exist only in the current document.'));
    const diff = node('ol', 'campaign-prep__diff');
    for (const [mark, line] of lineDiff(value.revision.lines, value.current?.lines || [])) {
      const item = authored('li', line, mark === '-' ? 'campaign-prep__diff--old' : mark === '+' ? 'campaign-prep__diff--new' : '');
      item.dataset.mark = mark === ' ' ? '' : mark === '-' ? '−' : '+';
      diff.append(item);
    }
    modal.querySelector('[data-fields]').append(legend, diff);
  }

  /* Event wiring for static controls in the page template. */
  function wire() {
    const on = (selector, type, handler) => $(selector)?.addEventListener(type, handler, { signal });
    on('[data-session-create]', 'click', event => void run(newSession, event.currentTarget));
    on('[data-event-create]', 'click', event => void run(() => eventForm(null), event.currentTarget));
    on('[data-timeline-filter]', 'change', event => { timelineFilter = event.target.value; renderTimeline(); });
    for (const toggle of root.querySelectorAll('[data-timeline-mode]')) toggle.addEventListener('click', () => { timelineMode = toggle.dataset.timelineMode; renderTimeline(); }, { signal });
    on('[data-connections-pick]', 'click', () => pickReference(row => showConnections(ref(row.type, row.id))));
    on('[data-player-choice]', 'change', event => void run(() => loadPreview(event.target.value)));
    on('[data-history-journal]', 'change', event => { historyJournal = event.target.value; void run(renderHistory); });
    on('[data-history-refresh]', 'click', event => void run(renderHistory, event.currentTarget));
    window.addEventListener('beforeunload', event => { if (dirty) event.preventDefault(); }, { signal });
  }

  function render({ refreshEditor = false } = {}) {
    if (!alive()) return;
    // Background refreshes never rebuild an editor that holds unsaved input or focus.
    const editor = $('[data-session-editor]');
    renderDashboard(); renderSessions({ keepEditor: dirty || sessionSaving || modals.size > 0 || !refreshEditor && !!editor?.contains(document.activeElement) }); renderTimeline();
  }
  function destroy() {
    if (scope.signal.aborted) return;
    scope.abort(); readEpoch++; historyEpoch++; previewEpoch++; comparisonEpoch++; connectionEpoch++;
    loading?.controller.abort(); attempts.clear();
    for (const modal of modals) modal.close?.(true);
    modals.clear(); prep = preview = connection = draft = null; dirty = false;
    for (const selector of ['[data-manager-dashboard]', '[data-session-list]', '[data-session-editor]', '[data-timeline-body]',
      '[data-manager-quests]', '[data-connections-body]', '[data-player-body]', '[data-history-versions]', '[data-history-trash]']) $(selector)?.replaceChildren();
  }
  wire();
  if (signal.aborted) destroy();
  else signal.addEventListener('abort', () => { if (!scope.signal.aborted) destroy(); }, { once: true });
  return {
    load, render, renderQuests, showConnections,
    async enter(section) {
      if (!alive()) return;
      if (['overview', 'sessions', 'timeline'].includes(section)) await load();
      if (section === 'connections') await renderConnections();
      if (section === 'player-view') renderPlayerView();
      if (section === 'history') await renderHistory();
      if (section === 'quests') renderQuests();
    },
    journalsChanged(section) {
      if (!alive()) return;
      renderQuests();
      if (section === 'history') void run(renderHistory);
      if (section === 'connections' && connection) { connection.value = null; void run(renderConnections); }
    },
    refreshLabels(section) { if (!alive()) return; render(); renderQuests(); if (section === 'player-view') renderPlayerView(); },
    destroy,
  };
}
