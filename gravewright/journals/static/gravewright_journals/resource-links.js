import { resourceLabel, resourceEventAffects, repeatedResourceEvent, pickResourceLink, openResourceLink } from '/static/gravewright_table/resource-links.js';

export const resourceNodeName = 'gwResourceLink';
const signature = ref => ref && !ref.unavailable ? JSON.stringify([ref.kind, ref.id, ref.pageId || null]) : null;
const identity = ref => ref?.key ? `key:${ref.key}` : signature(ref);

/** Old directory drags retain their campaign boundary while gaining typed atoms. */
export function journalResourceNode(reference) {
  const kind = reference?.kind || reference?.type;
  if (typeof kind !== 'string' || typeof reference?.id !== 'string' || !reference.id || reference.id.length > 256) return null;
  const ref = { kind, id: reference.id, ...(reference.pageId ? { pageId: reference.pageId } : {}),
    ...(reference.label || reference.title ? { label: (reference.label || reference.title).slice(0, 240) } : {}),
    ...(reference.labelKey ? { labelKey: reference.labelKey } : {}) };
  return { type: resourceNodeName, attrs: { reference: ref } };
}

export function resourceHtml(reference, text) {
  const ref = reference?.unavailable ? { unavailable: true, ...(reference.key ? { key: reference.key } : {}) }
    : reference?.kind && reference?.id ? { kind: reference.kind, id: reference.id, ...(reference.pageId ? { pageId: reference.pageId } : {}) } : { unavailable: true };
  return ['span', { 'data-gw-resource-link': '', 'data-resource-state': ref.unavailable ? 'unavailable' : 'available',
    'data-gw-resource-reference': JSON.stringify(ref), class: 'journal-resource-link', translate: 'no' }, resourceLabel(reference || { unavailable: true }, text)];
}

function projectedReferences(value, references = new Map(), depth = 0) {
  if (depth > 40 || !value || typeof value !== 'object') return references;
  if (value.type === resourceNodeName) {
    const ref = value.attrs?.reference;
    if (ref?.key) references.set(ref.key, ref);
    if (signature(ref)) references.set(signature(ref), ref);
  }
  for (const child of Array.isArray(value) ? value : Object.values(value)) if (child && typeof child === 'object') projectedReferences(child, references, depth + 1);
  return references;
}

/** One lifecycle and one coalesced journal read own all inline reference views. */
export function createJournalResourceLinks({ host, api, editor, text, readonly, signal: external,
  journalId = host.closest?.('[data-journal-id]')?.dataset.journalId,
  pageId, pagePersisted = true, readJournal, onReadonly = () => {},
  pick = pickResourceLink, open = openResourceLink, report = () => {} }) {
  const own = new AbortController(), signal = external ? AbortSignal.any([own.signal, external]) : own.signal;
  const document = host.ownerDocument, views = new Set(), live = new Map(), sourceEvents = new Map();
  let closed = false, epoch = 0, timer, reading, picker, projectionQueued = false;
  const alive = () => !closed && !signal.aborted;
  const resourceApi = api.journals;
  function resolveDisplay(reference) {
    if (!reference || !alive()) return { unavailable: true, ...(reference?.key ? { key: reference.key } : {}) };
    return live.has(identity(reference)) ? live.get(identity(reference)) || { unavailable: true, ...(reference.key ? { key: reference.key } : {}) } : reference;
  }
  function paintAll() { for (const view of views) view.paint(); }
  function storedReference(reference) {
    const projected = resolveDisplay(reference);
    // An unsaved link has no opaque key yet. Keep its canonical address for
    // server validation while removing every stale display field locally.
    return projected.unavailable && !projected.key && reference?.kind && reference?.id
      ? { kind: reference.kind, id: reference.id, ...(reference.pageId ? { pageId: reference.pageId } : {}) } : projected;
  }
  function serialize(value, depth = 0) {
    if (!value || typeof value !== 'object' || depth > 40) return value;
    if (value.type === resourceNodeName) return { ...value, attrs: { ...value.attrs, reference: storedReference(value.attrs?.reference) } };
    if (Array.isArray(value)) return value.map(item => serialize(item, depth + 1));
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, serialize(item, depth + 1)]));
  }
  function queueProjection() {
    if (projectionQueued) return; projectionQueued = true;
    queueMicrotask(() => { projectionQueued = false; persistProjection(); });
  }
  function persistProjection() {
    const current = editor(); if (!alive() || !current?.state?.doc?.descendants) return;
    let transaction = current.state.tr, changed = false;
    current.state.doc.descendants((node, position) => {
      if (node.type.name !== resourceNodeName) return;
      const reference = storedReference(node.attrs.reference);
      if (JSON.stringify(reference) !== JSON.stringify(node.attrs.reference)) {
        transaction = transaction.setNodeMarkup(position, undefined, { ...node.attrs, reference }); changed = true;
      }
    });
    if (changed) current.view.dispatch(transaction.setMeta('preventUpdate', true).setMeta('addToHistory', false));
  }
  async function refresh({ neutralize = true } = {}) {
    if (!alive() || !views.size) return;
    reading?.abort(); const request = reading = new AbortController(), token = ++epoch;
    const requestSignal = AbortSignal.any([signal, request.signal]);
    const rows = [...views].map(view => view.reference).filter(ref => identity(ref));
    const unique = new Map(rows.map(ref => [identity(ref), ref]));
    // Explicit full refreshes redact all links. A scheduled resource refresh
    // already redacted only affected links in invalidate(), preserving the rest.
    if (neutralize) { for (const key of unique.keys()) live.set(key, null); paintAll(); }
    try {
      let projected = new Map();
      if (journalId) {
        const state = readJournal ? { journals: [await readJournal(requestSignal)].filter(Boolean) } : await resourceApi.state({}, { signal: requestSignal });
        if (!alive() || requestSignal.aborted || token !== epoch) return;
        const journal = state.journals.find(row => row.id === journalId && row.can_open !== false);
        if (!journal) { host.hidden = true; editor()?.setEditable?.(false, false); destroy(); return; }
        const page = pageId && (journal.editable_sections || journal.sections || []).find(row => row.id === pageId);
        if (page) pagePersisted = true;
        if (pageId && !page && (pagePersisted || readonly || journal.can_edit === false)) { host.hidden = true; editor()?.setEditable?.(false, false); destroy(); return; }
        if (!readonly && (pageId && page ? page.can_edit === false : journal.can_edit === false)) { editor()?.setEditable?.(false, false); picker?.close?.(true); onReadonly(); }
        projected = projectedReferences(journal);
      }
      const missing = [];
      for (const [key, reference] of unique) {
        const current = reference.key ? projected.get(reference.key) : projected.get(key);
        if (current) live.set(key, current.unavailable ? { unavailable: true, key: current.key } : current);
        else if (!reference.unavailable) missing.push([key, reference]);
      }
      // Newly inserted, unsaved links are absent from the saved journal projection.
      await Promise.all(missing.map(async ([key, reference]) => {
        const result = await resourceApi.resolve({ reference: { kind: reference.kind, id: reference.id,
          ...(reference.pageId ? { pageId: reference.pageId } : {}) } }, { signal: requestSignal });
        if (!alive() || requestSignal.aborted || token !== epoch) return;
        const row = result && Object.hasOwn(result, 'resource') ? result.resource : result; live.set(key, row?.id ? row : null);
      }));
      if (alive() && !requestSignal.aborted && token === epoch) { paintAll(); persistProjection(); }
    } catch (error) {
      if (alive() && !requestSignal.aborted && token === epoch) { paintAll(); persistProjection(); report(error); }
    } finally { if (reading === request) reading = undefined; }
  }
  function invalidate(event) {
    if (!alive() || !views.size) return;
    const sourceChanged = resourceEventAffects(event, { kind: 'journal' });
    const affected = [...views].filter(view => sourceChanged || resourceEventAffects(event, view.reference));
    if (!affected.length) return;
    if (repeatedResourceEvent(event, sourceEvents)) return;
    ++epoch; reading?.abort();
    for (const entry of affected) live.set(identity(entry.reference), null);
    paintAll(); queueProjection();
    clearTimeout(timer); timer = setTimeout(() => void refresh({ neutralize: false }), 120);
  }
  const view = ({ node }) => {
    const controller = new AbortController(), nodeSignal = AbortSignal.any([signal, controller.signal]);
    const dom = document.createElement('span'); dom.className = 'journal-resource-link'; dom.dataset.gwResourceLink = '';
    dom.contentEditable = 'false'; dom.setAttribute('translate', 'no');
    const entry = { reference: node.attrs.reference, dom, paint() {
      const reference = resolveDisplay(entry.reference), unavailable = !reference || reference.unavailable === true;
      dom.textContent = resourceLabel(reference || { unavailable: true }, text);
      dom.dataset.resourceState = unavailable ? 'unavailable' : 'available';
      dom.setAttribute('aria-disabled', String(unavailable));
      if (unavailable) { dom.tabIndex = -1; dom.removeAttribute('role'); dom.removeAttribute('aria-keyshortcuts'); }
      else { dom.tabIndex = 0; dom.setAttribute('role', 'link'); dom.setAttribute('aria-keyshortcuts', 'Enter Space'); }
    } };
    views.add(entry); entry.paint();
    const activate = async () => {
      if (!alive()) return;
      const reference = resolveDisplay(entry.reference); if (!reference || reference.unavailable) return;
      try { await open(reference, { api, resourceApi, preferNative: true, sourceEvents, t: text, signal: nodeSignal }); }
      catch (error) { if (alive() && !nodeSignal.aborted && error.name !== 'AbortError' && error.code !== 'cancelled') report(error); }
    };
    dom.addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); void activate(); }, { signal: nodeSignal });
    dom.addEventListener('keydown', event => {
      if (!['Enter', ' '].includes(event.key) || event.repeat || event.ctrlKey || event.metaKey || event.altKey) return;
      event.preventDefault(); event.stopPropagation(); void activate();
    }, { signal: nodeSignal });
    return { dom, ignoreMutation: () => true,
      stopEvent: event => ['click', 'keydown'].includes(event.type),
      update(next) { if (next.type.name !== resourceNodeName) return false; entry.reference = next.attrs.reference; entry.paint(); queueProjection(); return true; },
      destroy() { controller.abort(); views.delete(entry); },
    };
  };
  function insert(reference, position) {
    if (!alive() || readonly || !editor()?.isEditable) return false;
    const node = journalResourceNode(reference); if (!node) return false;
    if (position && typeof position === 'object') {
      const { from, to, text } = position, doc = editor().state.doc;
      // A delayed picker must replace only its original trigger, never text
      // at an insertion point that another edit has invalidated.
      if (!Number.isInteger(from) || !Number.isInteger(to) || from < 0 || to <= from
        || to > doc.content.size || typeof text !== 'string' || !text.length || to - from !== text.length
        || doc.textBetween(from, to) !== text) throw Error('The reference insertion point changed. Type @ again.');
      position = { from, to };
    }
    live.delete(signature(node.attrs.reference));
    const chain = editor().chain().focus();
    if (position !== undefined) chain.setTextSelection(position);
    chain.insertContent([node, { type: 'text', text: ' ' }]).run(); return true;
  }
  function choose(position) {
    if (!alive() || readonly || !editor()?.isEditable) return;
    if (picker?.isConnected) { picker.focus(); return picker; }
    picker = pick(reference => { if (!insert(reference, position)) throw Error('You cannot edit this journal.'); }, { api, resourceApi, t: text, signal }); return picker;
  }
  function destroy() {
    if (closed) return;
    closed = true; ++epoch; clearTimeout(timer); reading?.abort(); own.abort(); picker?.close?.(true);
    for (const entry of views) { entry.dom.textContent = text('Unavailable resource'); entry.dom.dataset.resourceState = 'unavailable'; entry.dom.removeAttribute('role'); entry.dom.removeAttribute('aria-keyshortcuts'); entry.dom.setAttribute('aria-disabled', 'true'); entry.dom.tabIndex = -1; }
    views.clear(); live.clear(); sourceEvents.clear();
  }
  const window = document.defaultView || globalThis.window;
  for (const event of ['gravewright:resources', 'gravewright:api-event', 'gravewright:journals', 'gravewright:actors.state', 'gravewright:maps', 'gravewright:map-layers', 'gravewright:ownership-changed']) window.addEventListener(event, invalidate, { signal });
  window.addEventListener('gravewright:access-revoked', destroy, { signal });
  if (signal.aborted) destroy(); else signal.addEventListener('abort', destroy, { once: true });
  return { view, insert, choose, refresh, destroy, signal, serialize, project: resolveDisplay };
}
