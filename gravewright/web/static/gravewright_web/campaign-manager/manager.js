import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { executeNative } from '/static/gravewright_modules/domain-api.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { mergePatch } from '/static/gravewright_web/vendor/datastar-1.0.3.js';
import { sceneRestored, clearContent } from '/static/gravewright_table/content-state.js';
import { openFormModal } from '/static/gravewright_table/form-modal.js';
import { managementTransport } from './transport.js';
import { mountManagedScenes } from './scenes.js';
import { mountPreparation } from './preparation.js';

const root = document.querySelector('#table-workspace[data-management]');
const campaignId = root.dataset.tableId;
const language = createTranslator(), t = key => language.t(key);
const api = gravewright.forTable(campaignId);
const http = new HttpClient();
const $ = selector => root.querySelector(selector);
const errorBox = $('[data-manager-error]');
let overview = JSON.parse(document.getElementById('campaign-management-overview').textContent);
let section = 'overview', selectedScene = null, library, decks, timer, searching, audioSignature, clocksWidget, cluesWidget, mindmapsWidget;
const mounted = new Set();
const labels = { overview: 'Overview', journals: 'Journals', quests: 'Quests', clocks: 'Clocks', clues: 'Clues', mindmaps: 'Mind maps', actors: 'Characters', items: 'Items',
  maps: 'Scenes', library: 'File library', audio: 'Audio', cards: 'Cards', compendiums: 'Compendiums', combat: 'Encounters', members: 'Participants',
  sessions: 'Session planner', timeline: 'Timeline', connections: 'Connections', 'player-view': 'View as player', history: 'History and trash' };
const statuses = { draft: 'Draft', available: 'Available', active: 'Active', completed: 'Completed', failed: 'Failed', archived: 'Archived' };
function node(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined) element.textContent = value;
  return element;
}
function authored(tag, value) {
  const element = node(tag, '', value); element.setAttribute('translate', 'no'); return element;
}
function stopPreviews() {
  for (const audio of root.querySelectorAll('audio')) { audio.pause(); audio.removeAttribute('src'); audio.load(); }
}
function report(error) {
  if (transport.signal.aborted || error?.name === 'AbortError') return;
  errorBox.textContent = t(error?.message || 'Could not load campaign management.'); errorBox.hidden = false;
}
function run(action, button) {
  if (transport.signal.aborted) return;
  if (button?.disabled) return;
  if (button) button.disabled = true;
  errorBox.hidden = true;
  return Promise.resolve().then(action).catch(report).finally(() => { if (button) button.disabled = false; });
}
function button(label, action) {
  const element = node('button', '', t(label)); element.type = 'button';
  element.addEventListener('click', () => run(action, element));
  return element;
}
function empty(host, key = 'Nothing here yet. Prepare your first document.') {
  host.replaceChildren(node('p', 'campaign-manager__empty', t(key)));
}
function revoke() {
  clearInterval(timer); clearTimeout(searching);
  clearContent();
  stopPreviews();
  library?.destroy(); decks?.destroy();
  clocksWidget?.destroy();
  cluesWidget?.destroy();
  mindmapsWidget?.destroy();
  preparation?.destroy();
  window.dispatchEvent(new Event('gravewright:access-revoked'));
  for (const panel of root.querySelectorAll('[data-native-directory]')) panel._content?.dispose();
  for (const modal of document.querySelectorAll('[role="dialog"]')) modal.close?.(true);
  root.classList.add('campaign-manager--revoked');
  errorBox.textContent = t('GM access to this campaign is no longer available.'); errorBox.hidden = false;
  root.append(errorBox);
  document.getElementById('table-initial-content')?.remove();
  document.getElementById('campaign-management-overview')?.remove();
}
const transport = managementTransport({ api, execute: executeNative, report, revoked: revoke,
  authorize: async signal => {
    const next = await gravewright.campaigns.management(campaignId, { signal });
    overview = next; renderOverview(); renderMembers(); return next;
  },
  publish(domain, value, context) {
    const event = domain === 'journals' ? 'journals' : domain === 'actors' ? 'actors.state' : null;
    if (event) window.dispatchEvent(new CustomEvent('gravewright:' + event, { detail: value }));
    else window.dispatchEvent(new CustomEvent('gravewright:resources', { detail: { module: domain, state: value, sceneId: context.sceneId ?? null } }));
    window.dispatchEvent(new CustomEvent('gravewright:manager-state', { detail: { domain, state: value } }));
    if (domain === 'journals') {
      overview.counts.journals = value.journals.length;
      const quests = value.journals.filter(doc => doc.type === 'quest');
      overview.counts.quests = quests.length;
      overview.quests = { total: quests.length, byStatus: Object.fromEntries(Object.keys(statuses).map(status => [status, quests.filter(doc => (doc.quest?.status ?? doc.status) === status).length])) };
      renderDocuments(); renderOverview(); preparation?.journalsChanged(section);
    }
    if (domain === 'actors') { overview.counts.actors = value.actors.length; renderOverview(); preparation?.renderQuests(); }
    if (domain === 'maps') { overview.counts.scenes = value.maps.length; scenes.render(value); renderSceneChoices(); renderOverview(); }
    if (domain === 'audio') renderAudio(value);
    if (domain === 'clocks' && (context.sceneId ?? null) === selectedScene) clocksWidget?.update(value);
    if (domain === 'clues' && (context.sceneId ?? null) === selectedScene) cluesWidget?.update(value);
    if (domain === 'mindmaps') mindmapsWidget?.update(value);
    else if (mindmapsWidget) void transport.read('mindmaps').catch(report);
  },
});
window.gravewrightRealtime = transport;
// This is a local editing context. Selecting it never changes navigation or broadcast.
window.gravewrightMaps = {
  get current() { return transport.states.get('maps')?.maps.find(scene => scene.id === selectedScene) || null; },
  view(id) { selectSection('maps'); selectScene(id); },
};
window.gravewrightMindMaps = window.gravewrightMindmaps = {
  async open(id, nodeId) { await selectSection('mindmaps'); return mindmapsWidget?.open(id, nodeId); },
  showDirectory() { return selectSection('mindmaps'); },
};
const scenes = mountManagedScenes({ root, api, transport, http, t, report,
  selectedScene: () => selectedScene, onSelect: id => selectScene(id) });
// Opens a referenced document in its native manager editor.
async function openDocument(ref) {
  if (ref.type === 'journal') return window.gravewrightJournals.open(ref.id);
  if (ref.type === 'actor') { await selectSection('actors'); return window.gravewrightActors.open(ref.id); }
  if (ref.type === 'item') { await selectSection('items'); return window.gravewrightItems?.open(ref.id); }
  if (ref.type === 'scene' || ref.type === 'encounter') { await selectSection('maps'); return selectScene(ref.id); }
  if (ref.type === 'track' || ref.type === 'playlist') return selectSection('audio');
}
const preparation = mountPreparation({ root, campaignId, campaigns: gravewright.campaigns, transport, signal: transport.signal,
  t: (key, params) => language.t(key, params), run, open: openDocument, select: next => selectSection(next), overview: () => overview,
  audio: async () => { await transport.subscribeModule('audio', selectedScene); return transport.states.get('audio'); } });

function selectScene(id) {
  selectedScene = transport.states.get('maps')?.maps.some(scene => scene.id === id) ? id : null;
  $('[data-manager-scene]').value = selectedScene || '';
  $('[data-manager-clock-scene]').value = selectedScene || '';
  $('[data-manager-clue-scene]').value = selectedScene || '';
  scenes.render(transport.states.get('maps'));
  window.dispatchEvent(new Event('gravewright:module-scene'));
  if (clocksWidget) {
    clocksWidget.update({ clocks: [], is_gm: true, sceneId: selectedScene });
    void transport.subscribeModule('clocks', selectedScene);
  }
  if (cluesWidget) {
    cluesWidget.update({ clues: [], is_gm: true, sceneId: selectedScene });
    void transport.subscribeModule('clues', selectedScene);
  }
}
function renderSceneChoices() {
  for (const select of [$('[data-manager-scene]'), $('[data-manager-clock-scene]'), $('[data-manager-clue-scene]')]) {
    select.replaceChildren(new Option(t('No scene selected'), ''));
    for (const scene of transport.states.get('maps')?.maps || []) {
      const option = new Option(scene.name, scene.id); option.setAttribute('translate', 'no'); select.append(option);
    }
    if (selectedScene && !transport.states.get('maps')?.maps.some(scene => scene.id === selectedScene)) selectScene(null);
    select.value = selectedScene || '';
  }
}
function renderOverview() {
  const host = $('[data-manager-stats]'); if (!host || transport?.signal.aborted) return;
  host.replaceChildren();
  for (const [key, name, view] of [['journals','Journals','journals'],['quests','Quests','quests'],['actors','Characters','actors'],['scenes','Scenes','maps']]) {
    const stat = button(name, () => selectSection(view)); stat.className = 'campaign-manager__stat';
    stat.prepend(node('strong', '', String(overview.counts?.[key] || 0))); host.append(stat);
  }
  const progress = $('[data-manager-progress]'); progress.replaceChildren();
  const total = overview.quests?.total || 0;
  if (!total) { empty(progress, 'No quests yet. Create a quest to begin planning.'); return; }
  for (const [status, label] of Object.entries(statuses)) {
    const count = overview.quests.byStatus?.[status] || 0;
    const row = node('div', 'campaign-manager__progress-row');
    const bar = node('progress'); bar.max = total; bar.value = count; bar.setAttribute('aria-label', t(label));
    row.append(node('span', '', t(label)), node('strong', '', String(count)), bar); progress.append(row);
  }
}
function documents() { return transport.states.get('journals')?.journals || []; }
function renderDocuments() {
  const host = $('[data-manager-documents]'); host.replaceChildren();
  const rows = documents().slice(0, 8);
  if (!rows.length) { empty(host); return; }
  for (const doc of rows) {
    const row = button('', () => window.gravewrightJournals.open(doc.id)); row.className = 'campaign-manager__document';
    row.append(authored('span', doc.title), node('small', '', t(doc.type === 'quest' ? 'Quest' : doc.type === 'quest_board' ? 'Quest board' : doc.type === 'roll_table' ? 'Roll table' : 'Journal'))); host.append(row);
  }
}
function renderQuests() { preparation.renderQuests(); }
function createDocument(kind) {
  const note = kind === 'gm-note';
  const titles = { diary: 'New journal', quest: 'New quest', quest_board: 'New quest board', 'gm-note': 'GM notebook' };
  let attempt;
  const modal = openFormModal(t(titles[kind]), [{ name: 'title', label: t('Title'), required: true,
    ...(note ? { value: t('GM notebook') } : {}) }], async form => {
    const payload = { title: form.elements.title.value, journal_type: note ? 'diary' : kind };
    const fingerprint = JSON.stringify(payload);
    if (attempt?.fingerprint !== fingerprint) attempt = { fingerprint, requestId: crypto.randomUUID() };
    const result = await transport.journalCommand('create', payload, { requestId: attempt.requestId });
    // The native creation service defaults every journal to private.
    window.gravewrightJournals.open(result.journal_id);
    await transport.check();
  }, { key: 'manager-create-' + kind, submitLabel: t('Create') });
  modal.querySelector('[name=title]').maxLength = 120;
  return modal;
}
function renderMembers() {
  const host = $('[data-manager-members]'); if (!host) return;
  host.replaceChildren();
  for (const member of overview.members || []) {
    const row = node('article', 'campaign-manager__row'), info = node('div', 'campaign-manager__row-info');
    info.append(node('strong', '', member.name), node('small', '', t(member.role === 'gm' ? 'Game master' : member.role === 'streamer' ? 'Streamer' : 'Player')));
    row.append(info);
    if (member.role !== 'gm') row.append(button('Remove participant', () => {
      const modal = openFormModal(t('Remove participant'), [], async () => {
        await transport.check();
        await gravewright.campaigns.banMember(campaignId, { user_id: member.id }, { signal: transport.signal });
        await transport.check();
      }, { key: 'manager-remove-member', submitLabel: t('Remove participant') });
      modal.querySelector('[data-fields]').append(authored('p', member.name), node('p', '', t('Remove this participant from the campaign?')));
    }));
    host.append(row);
  }
  if (!host.children.length) empty(host, 'No participants found.');
}
function renderAudio(state) {
  const signature = JSON.stringify((state.tracks || []).map(({ id, name, kind, src }) => ({ id, name, kind, src })));
  if (signature === audioSignature) return;
  audioSignature = signature;
  const host = $('[data-manager-audio]'), rows = [];
  const existing = new Map([...host.querySelectorAll('[data-track-id]')].map(row => [row.dataset.trackId, row]));
  for (const track of state.tracks || []) {
    const row = existing.get(track.id) || node('article', 'campaign-manager__row');
    existing.delete(track.id); row.dataset.trackId = track.id;
    let info = row.querySelector('.campaign-manager__row-info'), preview = row.querySelector('audio');
    if (!info) { info = node('div', 'campaign-manager__row-info'); row.append(info); }
    info.replaceChildren(authored('strong', track.name), node('small', '', t(track.kind === 'effect' ? 'Sound effect' : 'Ambient audio')));
    if (!preview) { preview = document.createElement('audio'); preview.controls = true; preview.preload = 'none'; preview.style.maxWidth = '100%'; row.append(preview); }
    if (preview.getAttribute('src') !== track.src) preview.src = track.src;
    preview.setAttribute('aria-label', t('Preview audio')); rows.push(row);
  }
  for (const row of existing.values()) { const audio = row.querySelector('audio'); audio.pause(); audio.removeAttribute('src'); audio.load(); }
  host.replaceChildren(...rows);
  if (!host.children.length) empty(host, 'No audio in this campaign.');
}
async function ensureMedia() {
  if (!mounted.has('media')) {
    await import('/static/gravewright_table/media-workspace.js'); mounted.add('media');
    if (transport.signal.aborted) return;
    window.dispatchEvent(new Event('gravewright:module-scene'));
    await Promise.all([transport.subscribeModule('audio', selectedScene), transport.subscribeModule('cards', selectedScene)]);
  }
}
async function selectSection(next, { history = true } = {}) {
  if (!labels[next] || !$(`[data-manager-section="${next}"]`) || transport.signal.aborted) return;
  section = next;
  for (const tab of root.querySelectorAll('[data-manager-section]')) tab.setAttribute('aria-current', tab.dataset.managerSection === next ? 'page' : 'false');
  const directory = ['items','compendiums','combat'].includes(next);
  for (const view of root.querySelectorAll('[data-manager-view]')) view.hidden = view.dataset.managerView !== (directory ? 'directories' : next);
  for (const panel of root.querySelectorAll('[data-native-directory]')) panel.hidden = panel.dataset.nativeDirectory !== next;
  mergePatch({ _journalsOpen: next === 'journals', _actorsOpen: next === 'actors' });
  $('[data-manager-heading]').textContent = t(labels[next]);
  if (history) { const url = new URL(location.href); url.searchParams.set('section', next); window.history.replaceState(null, '', url); }
  if (directory) await transport.subscribeModule(next, selectedScene);
  if (next === 'audio' || next === 'cards') await ensureMedia();
  if (transport.signal.aborted) return;
  if (next === 'clocks') {
    if (!clocksWidget) {
      const { mountClocks } = await import('/static/gravewright_table/clocks.js');
      if (transport.signal.aborted) return;
      clocksWidget = mountClocks($('[data-manager-view="clocks"] [data-clocks-root]'), { api,
        sceneId: () => selectedScene, scenes: () => transport.states.get('maps')?.maps || [], t,
        onChange: state => {
          if ((state.sceneId ?? null) !== selectedScene || transport.signal.aborted) return;
          transport.invalidate('clocks'); transport.states.set('clocks', state); clocksWidget?.update(state);
        },
      });
    }
    await transport.subscribeModule('clocks', selectedScene);
  }
  if (next === 'clues') {
    if (!cluesWidget) {
      const { mountClues } = await import('/static/gravewright_table/clues.js');
      if (transport.signal.aborted) return;
      cluesWidget = mountClues($('[data-manager-view="clues"] [data-clues-root]'), { api,
        sceneId: () => selectedScene, scenes: () => transport.states.get('maps')?.maps || [], t,
        onChange: state => {
          if ((state.sceneId ?? null) !== selectedScene || transport.signal.aborted) return;
          transport.invalidate('clues'); transport.states.set('clues', state); cluesWidget?.update(state);
        },
      });
    }
    await transport.subscribeModule('clues', selectedScene);
  }
  if (next === 'mindmaps') {
    if (!mindmapsWidget) {
      const { mountMindmaps } = await import('/static/gravewright_table/mindmaps.js');
      if (transport.signal.aborted) return;
      mindmapsWidget = mountMindmaps($('[data-manager-view="mindmaps"] [data-mindmaps-root]'), { api,
        sceneId: () => selectedScene, scenes: () => transport.states.get('maps')?.maps || [], t, signal: transport.signal,
        onChange: state => { transport.invalidate('mindmaps'); transport.states.set('mindmaps', state); mindmapsWidget?.update(state); },
      });
    }
    await transport.subscribeModule('mindmaps');
  }
  if (next === 'audio') await transport.subscribeModule('audio', selectedScene);
  if (next === 'cards' && !decks) decks = window.gravewrightTableMedia.mountDecks($('[data-manager-decks]'));
  if (next === 'library' && !library) {
    const { mountAssetLibrary } = await import('./library.js');
    if (transport.signal.aborted) return;
    library = mountAssetLibrary($('[data-manager-library]'), { props: { containerId: campaignId, gm: true, revision: 0 }, HttpClient });
  }
  await preparation.enter(next);
}
async function search() {
  const query = $('#campaign-search').value.trim(), host = $('[data-manager-search-results]');
  if (!query) { host.hidden = true; host.replaceChildren(); return; }
  host.hidden = false; host.replaceChildren(node('p', '', t('Searching campaign...')));
  const result = await api.table.search(query, { signal: transport.signal });
  if ($('#campaign-search').value.trim() !== query || transport.signal.aborted) return;
  host.replaceChildren();
  for (const entry of (Array.isArray(result) ? result : result.results || result.entries || []).slice(0, 50)) {
    const row = button('', async () => {
      if (entry.type === 'journal' || entry.type === 'quest') window.gravewrightJournals.open(entry.id);
      else if (entry.type === 'actor') { await selectSection('actors'); window.gravewrightActors.open(entry.id); }
      else if (entry.type === 'item') { await selectSection('items'); window.gravewrightItems.open(entry.id); }
      else if (entry.type === 'scene') { await selectSection('maps'); selectScene(entry.id); }
      else if (entry.type === 'compendium') await selectSection('compendiums');
    });
    row.className = 'campaign-manager__document';
    row.append(authored('span', entry.name || entry.title), node('small', '', t({ actor: 'Character', scene: 'Scene', item: 'Item', journal: 'Journal', quest: 'Quest' }[entry.type] || 'Document')));
    host.append(row);
  }
  if (!host.children.length) empty(host, 'No results found.');
}
root.addEventListener('click', event => {
  const tab = event.target.closest('[data-manager-section]');
  if (tab) void run(() => selectSection(tab.dataset.managerSection));
  const create = event.target.closest('[data-manager-create]');
  if (create) void run(() => createDocument(create.dataset.managerCreate));
}, { signal: transport.signal });
$('[data-manager-quest-status]').addEventListener('change', renderQuests, { signal: transport.signal });
$('[data-manager-invite]').addEventListener('click', event => void run(async () => {
  await transport.check();
  const value = await gravewright.campaigns.invite(campaignId, { expires_in_hours: 24, max_uses: 10 }, { signal: transport.signal });
  const modal = openFormModal(t('Invitation code'), [{ name: 'code', label: t('Invitation code'), value: value.code }], async form => {
    await navigator.clipboard.writeText(form.elements.code.value);
  }, { key: 'manager-invitation', submitLabel: t('Copy code') });
  const input = modal.querySelector('[name=code]'); input.readOnly = true; input.select();
  modal.querySelector('[data-fields]').append(node('p', '', t('This invitation expires in 24 hours and allows up to 10 uses.')));
}, event.currentTarget), { signal: transport.signal });
$('[data-manager-scene]').addEventListener('change', event => selectScene(event.target.value), { signal: transport.signal });
$('[data-manager-clock-scene]').addEventListener('change', event => selectScene(event.target.value), { signal: transport.signal });
$('[data-manager-clue-scene]').addEventListener('change', event => selectScene(event.target.value), { signal: transport.signal });
$('[data-manager-refresh]').addEventListener('click', event => run(() => Promise.all([transport.refresh(), preparation.enter(section)]), event.currentTarget), { signal: transport.signal });
$('#campaign-search').addEventListener('input', () => { clearTimeout(searching); searching = setTimeout(() => void run(search), 250); }, { signal: transport.signal });
$('[data-manager-audio-upload]').addEventListener('click', () => $('[data-manager-audio-file]').click(), { signal: transport.signal });
$('[data-manager-audio-file]').addEventListener('change', event => void run(async () => {
  const file = event.target.files[0]; event.target.value = ''; if (!file) return;
  await transport.check(); await api.audio.upload({ file, name: file.name }, { signal: transport.signal });
  await transport.read('audio');
}), { signal: transport.signal });
$('[data-manager-audio-workspace]').addEventListener('click', () => void run(async () => {
  if (!selectedScene) throw Error(t('Choose a scene first.'));
  await ensureMedia(); window.gravewrightTableMedia.showAudio();
}), { signal: transport.signal });
window.addEventListener('focus', () => { if (!document.hidden) void run(() => transport.refresh()); }, { signal: transport.signal });
document.addEventListener('visibilitychange', () => { if (!document.hidden) void run(() => transport.refresh()); }, { signal: transport.signal });
window.addEventListener('pagehide', () => {
  clearInterval(timer); clearTimeout(searching); clearContent(); stopPreviews(); library?.destroy(); decks?.destroy(); clocksWidget?.destroy(); cluesWidget?.destroy(); mindmapsWidget?.destroy(); preparation.destroy(); scenes.destroy(); transport.close();
}, { once: true });
window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); }, { once: true });
language.onChange(() => { renderOverview(); renderDocuments(); renderMembers(); renderSceneChoices(); preparation.refreshLabels(section); $('[data-manager-heading]').textContent = t(labels[section]); });

try {
  await transport.check();
  sceneRestored();
  await Promise.all([import('/static/gravewright_actors/workspace.js'), import('/static/gravewright_journals/workspace.js'), import('/static/gravewright_table/directories.js')]);
  await import('/static/gravewright_modules/workspace.js');
  // Native directories share the seeded HTTP state, without a table connection.
  await Promise.all([transport.actorsSubscribe(), transport.journalsSubscribe(), transport.subscribeModule('maps')]);
  window.dispatchEvent(new Event('gravewright:connected'));
  renderOverview(); renderDocuments(); renderQuests(); renderMembers();
  await selectSection(new URL(location.href).searchParams.get('section') || 'overview', { history: false });
  timer = setInterval(() => {
    if (document.hidden) return;
    void run(() => transport.refresh());
    // Preparation records are GM-only and resynchronize by polling, like the native states.
    if (['overview', 'sessions', 'timeline'].includes(section)) void run(() => preparation.load());
  }, 15000);
  root.dataset.managerReady = 'true';
} catch (error) { report(error); }
