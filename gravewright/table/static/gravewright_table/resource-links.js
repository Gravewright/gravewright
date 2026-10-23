import { mountModal } from './modal.js';

export const resourceLabel = (reference, t = key => key) => reference?.unavailable ? t('Unavailable resource')
  : reference?.labelKey ? t(reference.labelKey) : reference?.label || reference?.name || t('Linked resource');

const ownerSections = {
  actor: 'actors', 'actor-asset': 'actors', 'actor-folder': 'actors', item: 'items', 'item-folder': 'items',
  journal: 'journals', 'journal-page': 'journals', 'journal-asset': 'journals', 'journal-folder': 'journals', 'quest-board-entry': 'quests',
  scene: 'maps', 'scene-folder': 'maps', 'scene-object': 'maps', 'scene-tile': 'maps', 'scene-drawing': 'maps', token: 'maps', encounter: 'combat',
  'map-asset': 'library', 'asset-folder': 'library', clock: 'clocks', clue: 'clues', track: 'audio', playlist: 'audio',
  deck: 'cards', card: 'cards', 'deck-definition': 'cards', 'card-asset': 'cards', compendium: 'compendiums',
  'compendium-entry': 'compendiums', 'compendium-asset': 'compendiums', 'pdf-mapping': 'actors', 'session-plan': 'sessions',
  'campaign-event': 'timeline', 'map-builder-project': 'maps', 'blueprint-template': 'maps', mindmap: 'mindmaps',
};

/** Ignore unrelated directory refreshes while retaining immediate auth invalidation. */
function resourceEventDomain(event) {
  if (event.type === 'gravewright:access-revoked' || event.type === 'gravewright:ownership-changed') return 'ownership';
  let domain;
  if (event.type === 'gravewright:resources') domain = event.detail?.module;
  else if (event.type === 'gravewright:api-event') {
    const type = event.detail?.type;
    if (type === 'resources.state') domain = event.detail?.payload?.module;
    else if (type === 'api.changed') domain = event.detail?.payload?.domain?.split('.')[0];
    else if (type && (type.endsWith('.state') || type === 'maps.layers' || type.startsWith('chat.'))) domain = type.split('.')[0];
    else return type ? false : undefined;
  } else domain = { 'gravewright:journals': 'journals', 'gravewright:actors.state': 'actors', 'gravewright:maps': 'maps', 'gravewright:map-layers': 'maps' }[event.type];
  return domain;
}
export function resourceEventAffects(event, reference) {
  const domain = resourceEventDomain(event);
  if (domain === false) return false;
  if (!domain || ['ownership', 'table', 'campaigns', 'members'].includes(domain)) return true;
  if (reference?.unavailable) return true;
  const expected = { 'quest-board-entry': 'journals', 'actor-asset': 'actors', 'journal-asset': 'journals',
    'compendium-asset': 'compendiums', 'session-plan': 'preparation', 'campaign-event': 'preparation',
    'scene-object': 'maps', 'scene-tile': 'maps', 'scene-drawing': 'maps', token: 'tokens', encounter: 'combat',
    'chat-message': 'chat', 'pdf-mapping': 'actors' }[reference?.kind] || ownerSections[reference?.kind];
  return domain === expected || domain === 'library' && expected === 'library'
    || domain === 'maps' && ['maps', 'tokens', 'combat'].includes(expected)
    || domain === 'tokens' && ['maps', 'tokens', 'combat'].includes(expected)
    || reference?.ownerReference && resourceEventAffects(event, reference.ownerReference);
}

export function repeatedResourceEvent(event, snapshots) {
  if (event.type === 'gravewright:api-event' && event.detail?.type === 'api.changed') return false;
  const domain = resourceEventDomain(event);
  if (!domain || ['ownership', 'table', 'campaigns', 'members'].includes(domain)) return false;
  const detail = event.type === 'gravewright:api-event' ? event.detail?.payload : event.detail;
  if (!detail) return false;
  const key = `${domain}:${detail.sceneId || detail.mapId || ''}:${event.type.includes('layers') || event.detail?.type === 'maps.layers' ? 'layers' : 'state'}`;
  const value = JSON.stringify(detail.state || detail);
  if (snapshots.get(key) === value) return true;
  snapshots.set(key, value); return false;
}

function plain(value, remaining = { size: 12000 }, depth = 0) {
  if (depth > 10 || !value || remaining.size <= 0) return '';
  if (typeof value === 'string') { const result = value.slice(0, remaining.size); remaining.size -= result.length; return result; }
  if (Array.isArray(value)) return value.map(item => plain(item, remaining, depth + 1)).filter(Boolean).join('\n');
  if (typeof value === 'object') return plain(value.text || value.content || value.doc || value.description || '', remaining, depth + 1);
  return '';
}

/** Native reads provide useful content without broadening the link's authorization. */
export async function loadResourcePreview(reference, { api, signal, campaigns, campaignId } = {}) {
  const { kind, id, sceneId } = reference, options = { signal }, scope = sceneId ? { sceneId } : {};
  if (reference.ownerReference) return loadResourcePreview(reference.ownerReference, { api, signal, campaigns, campaignId });
  let projection, rows, value;
  if (kind === 'compendium-entry') {
    const [packId, entryId] = id.split('/'); value = await api.compendiums.read({ packId, id: entryId }, options);
  } else if (kind === 'map-builder-project') { const result = await api.mapBuilder.read({ projectId: id }, options); value = result.project || result; }
  else if (kind === 'blueprint-template') { const result = await api.blueprints.readTemplate({ templateId: id }, options); value = result.template || result; }
  else if (kind === 'pdf-mapping') {
    const response = await fetch(`/api/containers/${encodeURIComponent(campaignId)}/pdf-mappings/${encodeURIComponent(id)}/export`, { signal, credentials: 'same-origin', cache: 'no-store' });
    const result = await response.json(); if (!response.ok) throw Error(result.message || 'Could not load campaign resources.');
    value = result; rows = result.manualFields || result.fields || [];
    return { entries: Array.isArray(rows) ? rows.map(row => row.label || row.name).filter(Boolean) : Object.values(rows).map(row => row.label || row.name).filter(Boolean) };
  }
  else if (kind === 'session-plan' || kind === 'campaign-event') {
    projection = await campaigns.preparation(campaignId, options); rows = kind === 'session-plan' ? projection.sessions : projection.events;
  } else if (kind === 'chat-message') { rows = await api.chat.history(scope, options); }
  else if (['scene-object', 'scene-drawing', 'token', 'encounter'].includes(kind)) {
    projection = kind === 'encounter' ? await api.combat.state(scope, options) : kind === 'token' ? await api.tokens.state(scope, options) : await api.maps.layers(scope, options);
    rows = kind === 'scene-drawing' ? projection.drawings?.rows : Object.values(projection).flatMap(item => Array.isArray(item) ? item : []);
    if (kind === 'encounter') value = projection;
  } else {
    const domains = { actor: 'actors', 'actor-folder': 'actors', item: 'items', 'item-folder': 'items', journal: 'journals',
      'journal-page': 'journals', 'journal-folder': 'journals', 'quest-board-entry': 'journals', scene: 'maps', 'scene-folder': 'maps',
      'map-asset': 'library', 'asset-folder': 'library', clock: 'clocks', clue: 'clues', track: 'audio', playlist: 'audio',
      deck: 'cards', card: 'cards', 'deck-definition': 'cards', 'card-asset': 'cards', compendium: 'compendiums', mindmap: 'mindmaps' };
    const domain = domains[kind];
    if (domain) { projection = await api[domain].state(scope, options); rows = Object.values(projection).flatMap(item => Array.isArray(item) ? item : []); }
  }
  signal?.throwIfAborted();
  value ||= (rows || []).find(row => String(row.id) === id || kind === 'scene-drawing' && String(row.id) === id.split('/')[1]);
  if (value && kind === 'journal-page') value = (value.sections || []).find(page => page.id === reference.pageId) || value;
  if (kind.endsWith('-folder')) {
    const children = (rows || []).filter(row => String(row.folderId ?? row.folder_id ?? row.folder ?? row.groupId) === id);
    return { text: children.map(row => row.name || row.title).filter(Boolean).join('\n'), empty: !children.length };
  }
  if (!value) return {};
  const content = value.data?.data || value.data || value;
  const text = [content.description, content.bio, content.notes, content.summary, content.content, content.content_markdown, content.text,
    content.sections, content.checklist, content.nodes?.map(node => ({ content: `${node.label}\n${node.notes || ''}` }))]
    .map(item => plain(item)).filter(Boolean).join('\n\n').slice(0, 12000);
  const progress = Number.isFinite(value.value) && Number.isFinite(value.segments) ? `${value.value}/${value.segments}` : null;
  const audio = kind === 'track' ? value.src || value.url : null;
  const image = kind === 'track' ? null : value.frontUrl || value.backUrl || value.imageUrl || value.portraitUrl || value.src || value.image || value.front || value.face;
  const facts = [];
  if (Number.isFinite(content.x) && Number.isFinite(content.y)) facts.push({ label: 'Position', value: `${content.x}, ${content.y}` });
  if (Number.isFinite(value.gridX) && Number.isFinite(value.gridY)) facts.push({ label: 'Position', value: `${value.gridX}, ${value.gridY}` });
  if (Number.isFinite(content.width) && Number.isFinite(content.height)) facts.push({ label: 'Size', value: `${content.width} × ${content.height}` });
  if (Number.isFinite(value.draw_count)) facts.push({ label: 'Draw pile', value: String(value.draw_count) });
  if (Number.isFinite(value.discard_count)) facts.push({ label: 'Discard pile', value: String(value.discard_count) });
  if (Number.isFinite(value.duration)) facts.push({ label: 'Duration', value: `${value.duration} s` });
  const playlistNames = kind === 'playlist' ? (value.tracks || []).map(track => (projection.tracks || []).find(item => item.id === track.soundId)?.name).filter(Boolean) : [];
  return { text, progress, image: typeof image === 'string' ? image : null,
    audio, facts, entries: [...playlistNames, ...(value.entries || value.cards || value.combatants || []).map(row => row.name || row.label).filter(Boolean)], value };
}

function nativeResourceAction(reference) {
  const { kind, id, pageId } = reference;
  if (['journal', 'journal-page', 'quest', 'quest-board', 'roll-table'].includes(kind) && window.gravewrightJournals?.open)
    return () => window.gravewrightJournals.open(id, pageId);
  if (kind === 'actor' && window.gravewrightActors?.open) return () => window.gravewrightActors.open(id);
  if (kind === 'item' && window.gravewrightItems?.open) return () => window.gravewrightItems.open(id);
  if (kind === 'scene' && window.gravewrightMaps?.view) return () => window.gravewrightMaps.view(id);
  if (kind === 'mindmap' && window.gravewrightMindMaps?.open) return () => window.gravewrightMindMaps.open(id);
  if (kind === 'clock' || kind === 'clue') {
    const toggle = document.querySelector(`[data-${kind === 'clock' ? 'clocks' : 'clues'}-open]`);
    if (toggle && !toggle.hidden) return () => toggle.click();
  }
  if (['track', 'playlist'].includes(kind) && window.gravewrightTableMedia?.showAudio) return () => window.gravewrightTableMedia.showAudio();
  if (reference.ownerReference) return nativeResourceAction(reference.ownerReference);
}

/** Resolve again on opening; stored display metadata never grants access. */
export async function openResourceLink(reference, { api, resourceApi = api?.mindmaps, preferNative = false, sourceEvents, t = key => key, signal } = {}) {
  const own = new AbortController(); signal = signal ? AbortSignal.any([own.signal, signal]) : own.signal;
  signal?.throwIfAborted();
  if (!reference || reference.unavailable) return;
  let modal, body, permissionEpoch = 0;
  const snapshots = new Map(sourceEvents);
  function invalidated(event) {
    if (!resourceEventAffects(event, reference)) return;
    if (repeatedResourceEvent(event, snapshots)) return;
    ++permissionEpoch; body?.replaceChildren(); modal?.close?.(true); own.abort();
  }
  for (const event of ['gravewright:resources', 'gravewright:api-event', 'gravewright:journals', 'gravewright:maps', 'gravewright:map-layers', 'gravewright:actors.state', 'gravewright:ownership-changed', 'gravewright:access-revoked']) window.addEventListener(event, invalidated, { signal });
  let result;
  try {
    result = await resourceApi.resolve({ reference: { kind: reference.kind, id: reference.id,
      ...(reference.pageId ? { pageId: reference.pageId } : {}) } }, { signal });
  } catch (error) { const aborted = signal.aborted; own.abort(); if (aborted || error.name === 'AbortError' || error.code === 'cancelled') return; throw error; }
  if (signal.aborted) return;
  const row = result && Object.hasOwn(result, 'resource') ? result.resource : result;
  if (preferNative && row?.id && ['actor', 'item', 'journal', 'journal-page', 'scene', 'mindmap'].includes(row.ownerReference?.kind || reference.kind)) {
    const action = nativeResourceAction({ ...reference, ...row });
    if (action) { own.abort(); return action(); }
  }
  modal = document.createElement('section'); modal.className = 'table-form-modal mindmap-resource';
  modal.dataset.resourcePreview = '';
  const header = document.createElement('header'), heading = document.createElement('strong'), close = document.createElement('button');
  heading.textContent = row ? resourceLabel(row, t) : t('Unavailable resource'); heading.setAttribute('translate', 'no');
  heading.id = `mindmap-resource-${crypto.randomUUID()}`; modal.setAttribute('aria-labelledby', heading.id);
  close.type = 'button'; close.textContent = '×'; close.setAttribute('aria-label', t('Close')); close.onclick = () => modal.close();
  body = document.createElement('div'); body.className = 'table-form-modal__body';
  const detail = document.createElement('p'); detail.setAttribute('translate', 'no');
  detail.textContent = row?.descriptionKey ? t(row.descriptionKey) : row?.description || (row ? t('Loading resource...') : t('You no longer have access to this resource.'));
  body.append(detail); header.append(heading, close); modal.append(header, body);
  const work = row && nativeResourceAction({ ...reference, ...row });
  if (work) {
    const open = document.createElement('button'); open.type = 'button'; open.textContent = t('Open linked resource');
    open.onclick = () => { modal.close(); void work(); }; body.append(open);
  }
  const campaign = document.getElementById('table-workspace');
  if (row && campaign?.dataset.role === 'gm' && ownerSections[reference.kind]) {
    const link = document.createElement('a'); link.textContent = t('Open owning directory'); link.target = '_blank'; link.rel = 'noopener';
    link.href = `/campaigns/${encodeURIComponent(campaign.dataset.tableId)}/manage?section=${encodeURIComponent(ownerSections[reference.kind])}`; body.append(link);
  }
  if (row && reference.kind === 'map-builder-project' && campaign?.dataset.role === 'gm') {
    const link = document.createElement('a'); link.textContent = t('Open Map Builder'); link.target = '_blank'; link.rel = 'noopener';
    link.href = `/game/${encodeURIComponent(campaign.dataset.tableId)}/map-builder?project=${encodeURIComponent(reference.id)}`; body.append(link);
  }
  if (row && ['actor-asset', 'journal-asset', 'map-asset'].includes(reference.kind)) {
    const download = document.createElement('button'); download.type = 'button'; download.textContent = t('Download linked file');
    download.onclick = async () => {
      download.disabled = true;
      try {
        const file = reference.kind === 'actor-asset' ? await api.actors.downloadAsset({ id: reference.id }, { signal })
          : reference.kind === 'journal-asset' ? await api.journals.downloadAsset({ id: reference.id }, { signal }) : await api.library.download({ id: reference.id }, { signal });
        signal?.throwIfAborted(); const url = URL.createObjectURL(file.blob), anchor = document.createElement('a');
        anchor.href = url; anchor.download = file.name; anchor.click(); URL.revokeObjectURL(url);
      } catch (error) { detail.textContent = t(error.message); detail.setAttribute('role', 'alert'); }
      finally { download.disabled = false; }
    }; body.append(download);
  }
  const dispose = () => modal.close?.(true);
  signal?.addEventListener('abort', dispose, { once: true });
  modal.addEventListener('close', () => { signal.removeEventListener('abort', dispose); own.abort(); }, { once: true });
  mountModal(modal, { nested: true });
  const previewEpoch = permissionEpoch;
  if (row) void loadResourcePreview({ ...reference, ...row }, { api, signal, campaigns: window.gravewright?.campaigns, campaignId: campaign?.dataset.tableId })
    .then(preview => {
      if (!modal.isConnected || signal?.aborted || previewEpoch !== permissionEpoch) return;
      detail.textContent = [preview.progress, preview.text, ...(preview.facts || []).map(fact => `${t(fact.label)}: ${fact.value}`), ...(preview.entries || [])].filter(Boolean).join('\n\n')
        || t(preview.empty ? 'This folder is empty.' : 'Use the native resource controls or open its owning directory.');
      if (preview.image) { try {
        const url = new URL(preview.image, location.href);
        if (url.origin === location.origin && ['http:', 'https:'].includes(url.protocol)) { const image = document.createElement('img'); image.src = url.href; image.alt = resourceLabel(row, t); image.style.maxWidth = '100%'; body.prepend(image); }
      } catch { /* Malformed image URLs are not displayed. */ } }
      if (preview.audio) { try {
        const url = new URL(preview.audio, location.href);
        if (url.origin === location.origin && ['http:', 'https:'].includes(url.protocol)) { const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'none'; audio.src = url.href; body.append(audio); }
      } catch { /* Malformed audio URLs are not displayed. */ } }
    }).catch(error => { if (modal.isConnected && !signal?.aborted) { detail.textContent = t(error.message); detail.setAttribute('role', 'alert'); } });
  return modal;
}

/** Native bounded catalog picker; failures retain the selection and draft. */
export function pickResourceLink(insert, { api, resourceApi = api?.mindmaps, t = key => key, signal: external } = {}) {
  const own = new AbortController(), signal = external ? AbortSignal.any([own.signal, external]) : own.signal;
  signal.throwIfAborted();
  const modal = document.createElement('section'); modal.className = 'table-form-modal mindmap-resource-picker';
  modal.dataset.mindmapResourcePicker = '';
  modal.dataset.resourcePicker = '';
  const form = document.createElement('form'), header = document.createElement('header'), heading = document.createElement('strong');
  heading.textContent = t('Link campaign resource'); heading.id = `mindmap-picker-${crypto.randomUUID()}`;
  modal.setAttribute('aria-labelledby', heading.id);
  const close = document.createElement('button'); close.type = 'button'; close.textContent = '×'; close.setAttribute('aria-label', t('Close'));
  const body = document.createElement('div'); body.className = 'table-form-modal__body';
  const alert = document.createElement('p'); alert.setAttribute('role', 'alert'); alert.hidden = true;
  const query = document.createElement('input'); query.type = 'search'; query.maxLength = 120;
  query.setAttribute('aria-label', t('Search campaign resources')); query.placeholder = t('Search campaign resources');
  const kind = document.createElement('select'); kind.setAttribute('aria-label', t('Resource type'));
  kind.append(new Option(t('All resource types'), ''));
  const results = document.createElement('select'); results.size = 10; results.required = true;
  results.setAttribute('aria-label', t('Campaign resources'));
  const hint = document.createElement('p'); hint.textContent = t('Choose a resource from this campaign. Its own permissions always apply.');
  const footer = document.createElement('footer'), submit = document.createElement('button'); submit.type = 'submit'; submit.textContent = t('Add link');
  header.append(heading, close); body.append(alert, query, kind, results, hint); footer.append(submit); form.append(header, body, footer); modal.append(form);
  let rows = [], reading, epoch = 0, timer, busy = false;
  async function search() {
    reading?.abort(); const request = reading = new AbortController(), token = ++epoch;
    alert.hidden = true; results.setAttribute('aria-busy', 'true');
    try {
      const value = await resourceApi.resources({ query: query.value, ...(kind.value ? { kinds: [kind.value] } : {}), limit: 80 },
        { signal: AbortSignal.any([signal, request.signal]) });
      if (signal.aborted || request.signal.aborted || token !== epoch) return;
      const previous = rows[Number(results.value)]; rows = value.resources || [];
      results.replaceChildren();
      rows.forEach((row, index) => { const option = new Option(resourceLabel(row, t), String(index)); option.setAttribute('translate', 'no'); results.append(option); });
      if (previous) { const index = rows.findIndex(row => row.kind === previous.kind && row.id === previous.id && row.pageId === previous.pageId); if (index >= 0) results.value = String(index); }
      if (kind.options.length === 1) for (const item of value.kinds || []) kind.append(new Option(t(item.label), item.id));
      hint.textContent = t(value.truncated ? 'More resources match. Refine your search.' : rows.length ? 'Choose a resource from this campaign. Its own permissions always apply.' : 'No resources found.');
    } catch (error) {
      if (!signal.aborted && !request.signal.aborted) { alert.textContent = t(error.message || 'Could not load campaign resources.'); alert.hidden = false; }
    } finally { if (token === epoch) results.removeAttribute('aria-busy'); }
  }
  close.addEventListener('click', () => { if (!busy) modal.close(); }, { signal });
  query.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => void search(), 200); }, { signal });
  kind.addEventListener('change', () => void search(), { signal });
  form.addEventListener('submit', async event => {
    event.preventDefault(); const row = rows[Number(results.value)]; if (busy || !row) return;
    busy = true; [close, query, kind, results, submit].forEach(control => { control.disabled = true; });
    try { await insert({ kind: row.kind, id: row.id, ...(row.pageId ? { pageId: row.pageId } : {}), label: row.label, ...(row.labelKey ? { labelKey: row.labelKey } : {}) }); if (!signal.aborted) modal.close(); }
    catch (error) { if (!signal.aborted) { alert.textContent = t(error.message); alert.hidden = false; } }
    finally { busy = false; [close, query, kind, results, submit].forEach(control => { control.disabled = false; }); }
  }, { signal });
  modal.addEventListener('close', () => { own.abort(); reading?.abort(); clearTimeout(timer); }, { once: true });
  signal.addEventListener('abort', () => modal.close?.(true), { once: true });
  mountModal(modal, { nested: true, canClose: () => !busy }); void search(); return modal;
}
