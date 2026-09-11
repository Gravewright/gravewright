// UI behavior ported from DiceTray.vue and DicePresets.vue; formulas use the server engine.
import { mergePatch, getPath } from '/static/gravewright_web/vendor/datastar-1.0.3.js';
import { dicePresets, buildPreset } from './presets.js';
const tray = document.getElementById('dice-tray'), workspace = document.getElementById('table-workspace');
const $ = s => tray.querySelector(s), field = n => $(`[name="${n}"]`);
const templates = Object.fromEntries(['term', 'history-entry', 'preset-choice', 'preset-field', 'saved-entry'].map(k => [k, document.getElementById('dice-' + k)]));
const clone = k => templates[k].content.firstElementChild.cloneNode(true);
const show = (el, yes) => { el.hidden = !yes; el.style.display = yes ? '' : 'none'; };
const storageKey = kind => `gravewright:dice-${kind}:${workspace.dataset.profileId}:${workspace.dataset.tableId}`;
function load(kind) { try {
    const v = JSON.parse(localStorage.getItem(storageKey(kind)) || '[]');
    return Array.isArray(v) ? v : [];
}
catch {
    return [];
} }
let terms = [], selected = 0, tab = 'manual', minimized = false, historyOpen = false, busy = false, popup;
let recent = load('history').filter(p => typeof p.expression === 'string' && typeof p.label === 'string').slice(0, 30);
let saved = load('presets').filter(p => typeof p.id === 'string' && typeof p.name === 'string' && typeof p.expression === 'string' && p.expression.length <= 512 && Number.isInteger(p.repeat) && p.repeat >= 1 && p.repeat <= 12).slice(0, 24);
let preset = dicePresets[0], values = { attributes: 6 }, prepared;
function error(text = '') { const el = $('.dice-tray__error'); el.textContent = text; show(el, !!text); }
function persist(kind, entries) { try {
    localStorage.setItem(storageKey(kind), JSON.stringify(entries));
    show($('[data-storage-error]'), false);
}
catch {
    if (kind === 'presets') {
        const el = $('[data-storage-error]');
        el.textContent = 'The browser could not save these presets.';
        show(el, true);
    }
} }
function formula() { field('expression').value = terms.map(t => `${t.count}d${t.faces}${t.explode ? '!' : ''}${t.selection ? t.selection + t.selectedCount : ''}`).join(' + ') + (Number($('#dice-modifier').value) ? ` ${Number($('#dice-modifier').value) > 0 ? '+' : '-'} ${Math.abs(Number($('#dice-modifier').value))}` : ''); refresh(); }
function refresh() {
    const expression = field('expression').value.trim(), repeat = Number(field('repeat').value);
    for (const b of $('.dice-tray__actions').querySelectorAll('button'))
        b.disabled = !expression;
    const hint = $('[data-dice-repeat-hint]');
    hint.textContent = `${repeat} separate results in chat, without adding them together.`;
    show(hint, repeat > 1);
    field('customName').placeholder = field('label').value || 'My roll';
    $('[data-dice-action="save"]').disabled = !expression || !(field('customName').value.trim() || field('label').value.trim());
}
function pool() {
    const container = $('.dice-tray__pool');
    container.replaceChildren();
    show(container, terms.length > 0);
    terms.forEach((t, i) => { const el = clone('term'); const select = el.querySelector('[data-term-select]'); select.textContent = `${t.count}d${t.faces}`; select.classList.toggle('dice-tray__term--active', selected === i); select.dataset.termSelect = i; el.querySelector('[data-term-remove]').dataset.termRemove = i; container.append(el); });
    const active = terms[selected];
    show($('.dice-tray__options'), !!active);
    for (const n of ['count', 'selection', 'selectedCount', 'explode'])
        field(n).disabled = !active;
    if (active) {
        for (const n of ['count', 'selection', 'selectedCount'])
            field(n).value = active[n];
        field('explode').checked = active.explode;
        field('selectedCount').max = active.count;
        field('selectedCount').disabled = !active.selection;
        show($('[data-selected-count]'), !!active.selection);
    }
}
function add(faces) { if (faces !== 'F' && (!Number.isInteger(Number(faces)) || Number(faces) < 1 || Number(faces) > 1000)) {
    error('Choose between 1 and 1,000 faces.');
    return;
} const index = terms.findIndex(t => t.faces === faces); if (index >= 0) {
    selected = index;
    terms[index].count = Math.min(99, terms[index].count + 1);
}
else if (terms.length < 8) {
    terms.push({ faces, count: 1, selection: '', selectedCount: 1, explode: false });
    selected = terms.length - 1;
} error(); pool(); formula(); }
function chooseTab(next) { const fresh = next === 'presets' && tab !== 'presets'; tab = next;
    tray.classList.toggle('dice-tray--presets', tab === 'presets');
    tray.style.width = '';
    tray.style.height = '';
    const bounds = tray.getBoundingClientRect(), view = tray.ownerDocument.defaultView;
    if (bounds.right > view.innerWidth - 8) tray.style.left = `${Math.max(8, view.innerWidth - bounds.width - 8)}px`;
    if (fresh) {
    choosePreset(dicePresets[0].id);
    field('customName').value = '';
    $('.dice-presets__saved').open = false;
} show($('.dice-presets'), tab === 'presets'); show($('[data-dice-manual]'), tab === 'manual'); if (tab === 'manual')
    $('[data-dice-manual]').style.display = 'contents'; for (const b of $('.dice-tray__tabs').children)
    b.setAttribute('aria-pressed', String(b.dataset.diceTab === tab)); for (const el of $('.dice-presets__fields').querySelectorAll('input'))
    el.disabled = tab !== 'presets'; pool(); if (tab === 'presets')
    for (const el of $('[data-dice-manual]').querySelectorAll('input,select'))
        el.disabled = true;
else {
    $('#dice-faces').disabled = false;
    $('#dice-modifier').disabled = false;
} }
function apply(p) { terms = []; selected = 0; $('#dice-modifier').value = 0; field('expression').value = p.expression; field('label').value = p.label; field('repeat').value = p.repeat ?? 1; error(); chooseTab(tab); refresh(); }
function history() { const list = $('.dice-tray__history'); list.replaceChildren(); show(list, historyOpen); $('[data-history-count]').textContent = recent.length; $('[data-dice-action="history"]').setAttribute('aria-expanded', String(historyOpen)); recent.forEach((p, i) => { const el = clone('history-entry'); el.querySelector('strong').textContent = p.label || p.expression; const small = el.querySelector('small'); small.textContent = `${p.repeat > 1 ? p.repeat + ' × ' : ''}${p.expression}`; show(small, !!p.label); el.querySelector('[data-history-use]').dataset.historyUse = i; el.querySelector('[data-history-remove]').dataset.historyRemove = i; list.append(el); }); if (!recent.length) {
    const li = document.createElement('li');
    li.setAttribute('data-v-gwdice', '');
    li.textContent = 'Your rolls will appear here.';
    list.append(li);
} }
function preview() { try {
    prepared = buildPreset(preset, values);
    show($('.dice-presets__preview'), true);
    $('.dice-presets__preview code').textContent = prepared.expression;
    $('.dice-presets__preview small').textContent = prepared.repeat > 1 ? `${prepared.repeat} resultados separados` : 'One roll';
    show($('.dice-presets__error'), false);
}
catch (e) {
    prepared = null;
    show($('.dice-presets__preview'), false);
    $('.dice-presets__error').textContent = e.message;
    show($('.dice-presets__error'), true);
} $('[data-dice-action="apply"]').disabled = !prepared; }
function choosePreset(id) { preset = dicePresets.find(p => p.id === id); values = Object.fromEntries(preset.fields.map(f => [f.key, f.initial])); for (const b of $('.dice-presets__choices').children)
    b.setAttribute('aria-pressed', String(b.dataset.preset === id)); $('.dice-presets__hint').textContent = preset.hint; const fields = $('.dice-presets__fields'); fields.replaceChildren(); for (const f of preset.fields) {
    const el = clone('preset-field');
    el.querySelector('span').textContent = f.label;
    const input = el.querySelector('input');
    Object.assign(input, { min: f.min, max: f.max, value: values[f.key], disabled: tab !== 'presets' });
    input.dataset.presetField = f.key;
    fields.append(el);
} preview(); }
function savedList() { const list = $('[data-saved-list]'); list.replaceChildren(); $('[data-saved-count]').textContent = saved.length; saved.forEach((p, i) => { const el = clone('saved-entry'); el.querySelector('strong').textContent = p.name; el.querySelector('small').textContent = `${p.repeat > 1 ? p.repeat + ' × ' : ''}${p.expression}`; const [use, remove] = el.querySelectorAll('button'); use.dataset.savedUse = i; remove.dataset.savedRemove = i; remove.setAttribute('aria-label', `Delete preset ${p.name}`); list.append(el); }); }
function save() { const name = field('customName').value.trim() || field('label').value.trim(), expression = field('expression').value.trim(), repeat = Number(field('repeat').value); if (!name || !expression || !Number.isInteger(repeat) || repeat < 1 || repeat > 12)
    return; const item = { id: saved.find(p => p.name === name)?.id || crypto.randomUUID(), name, expression, repeat }; saved = [item, ...saved.filter(p => p.id !== item.id)].slice(0, 24); persist('presets', saved); field('customName').value = ''; savedList(); refresh(); }
function setBusy(value) { busy = value; $('fieldset').disabled = value; tray.setAttribute('aria-busy', String(value)); $('[data-roll-label]').textContent = value ? 'Rolling…' : 'Roll'; }
// Only the submitted roll fields participate; preset drafts have their own validation.
function roll(visibility) { if (busy || !['expression', 'repeat', 'label'].every(name => field(name).reportValidity()))
    return; const entry = { expression: field('expression').value.trim(), label: field('label').value.trim(), repeat: Number(field('repeat').value) }; error(); setBusy(true); window.gravewrightRealtime.roll({ ...entry, visibility }).then(() => { recent = [entry, ...recent.filter(p => p.expression !== entry.expression || p.label !== entry.label || (p.repeat ?? 1) !== entry.repeat)].slice(0, 30); persist('history', recent); history(); window.gravewrightDice.close(); }).catch(e => error(e.message)).finally(() => setBusy(false)); }
tray.addEventListener('submit', e => { e.preventDefault(); roll('public'); });
tray.addEventListener('input', e => { const el = e.target; if (el.dataset.presetField) {
    values[el.dataset.presetField] = el.valueAsNumber;
    preview();
    return;
} if (['count', 'selection', 'selectedCount', 'explode'].includes(el.name) && terms[selected]) {
    terms[selected][el.name] = el.name === 'explode' ? el.checked : el.name === 'selection' ? el.value : Number(el.value);
    if (el.name === 'selection')
        pool();
    formula();
}
else if (el.id === 'dice-modifier')
    formula();
else
    refresh(); });
tray.addEventListener('click', e => { const b = e.target.closest('button'); if (!b || b.disabled || busy && b.closest('fieldset'))
    return; const d = b.dataset; if (d.diceFaces)
    add(d.diceFaces);
else if (d.diceTab)
    chooseTab(d.diceTab);
else if (d.termSelect !== undefined) {
    selected = Number(d.termSelect);
    pool();
}
else if (d.termRemove !== undefined) {
    terms.splice(Number(d.termRemove), 1);
    selected = 0;
    pool();
    formula();
}
else if (d.preset)
    choosePreset(d.preset);
else if (d.historyUse !== undefined)
    apply(recent[Number(d.historyUse)]);
else if (d.historyRemove !== undefined) {
    recent.splice(Number(d.historyRemove), 1);
    persist('history', recent);
    history();
}
else if (d.savedUse !== undefined) {
    const p = saved[Number(d.savedUse)];
    apply({ ...p, label: p.name });
}
else if (d.savedRemove !== undefined) {
    saved.splice(Number(d.savedRemove), 1);
    persist('presets', saved);
    savedList();
}
else {
    const actions = { custom: () => add($('#dice-faces').value), clear: () => { terms = []; selected = 0; $('#dice-modifier').value = 0; field('repeat').value = 1; pool(); formula(); error(); }, minimize: () => { minimized = !minimized; show($('form'), !minimized); }, close: () => window.gravewrightDice.close(), detach: () => window.gravewrightDice.detach(), history: () => { historyOpen = !historyOpen; history(); }, apply: () => prepared && apply(prepared), save, gm: () => roll('gm') };
    actions[d.diceAction]?.();
} });
window.gravewrightDice = {
    toggle() { if (popup && !popup.closed) {
        popup.focus();
        return;
    } if (!getPath('_diceOpen')) {
        terms = [];
        selected = 0;
        minimized = false;
        historyOpen = false;
        $('#dice-faces').value = 24;
        $('#dice-modifier').value = 0;
        field('expression').value = '';
        field('label').value = '';
        field('repeat').value = 1;
        show($('form'), true);
        chooseTab('manual');
        refresh();
        history();
        error();
        tray.scrollTop = 0;
    } mergePatch({ _diceOpen: !getPath('_diceOpen') });
        requestAnimationFrame(() => tray.dispatchEvent(new Event('focusin', { bubbles: true })));
    },
    close() { mergePatch({ _diceOpen: false }); popup?.close(); },
    detach() { if (popup && !popup.closed) {
        popup.focus();
        return;
    } popup = window.open('', `dice-${workspace.dataset.tableId}`, 'popup,width=420,height=700'); if (!popup)
        return; popup.document.title = 'Dice tray'; for (const style of document.querySelectorAll('style,link[rel="stylesheet"]'))
        popup.document.head.append(style.cloneNode(true)); const marker = document.createComment('dice-tray'); tray.replaceWith(marker); popup.document.body.append(tray); tray.classList.add('dice-tray--detached'); popup.addEventListener('pagehide', () => { marker.replaceWith(tray); tray.classList.remove('dice-tray--detached'); popup = null; }); }
};
window.addEventListener('pagehide', () => popup?.close());
for (const p of dicePresets) {
    const el = clone('preset-choice');
    el.dataset.preset = p.id;
    el.querySelector('span').textContent = p.name;
    $('.dice-presets__choices').append(el);
}
choosePreset(preset.id);
chooseTab('manual');
refresh();
history();
savedList();
