// QuestSheet, QuestBoard and RollTable behavior ported from the original UI.
import { richText, emptyDoc } from './editor.js';
export const typeLabels = { diary: 'Journal', quest: 'Quest', quest_board: 'Quest board', roll_table: 'Roll table' };
export const typeIcons = { diary: 'BookOpenText', quest: 'FlagBanner', quest_board: 'Kanban', roll_table: 'DiceFive' };
const statuses = ['draft', 'available', 'active', 'completed', 'failed', 'archived'];
const clone = name => document.getElementById('journal-' + name).content.firstElementChild.cloneNode(true);
const icon = name => document.getElementById('journal-icons').content.querySelector(`[data-icon="${name}"]`).firstElementChild.cloneNode(true);
const show = (el, on) => el.toggleAttribute('hidden', !on);
function seal(status, compact = true) { const el = document.getElementById('journal-seals').content.querySelector(`[data-status="${status}"]`).cloneNode(true); el.classList.toggle('quest-seal--compact', compact); return el; }
const text = (host, selector, value) => host.querySelector(selector).textContent = value;
function image(el, src, alt = '') { show(el, !!src); if (src)
    el.src = src;
else
    el.removeAttribute('src'); el.alt = alt; }
function editor(w, host, value, label, save, upload) { const instance = richText(host, value, !w.editing, file => upload(w.draft.id, file), label, next => { save(next); w.touch(); }); w.cleanups.push(() => instance.destroy()); w.typeEditors.push(instance.editor); }
export function renderType(w, state, upload, open) {
    w.destroyEditors();
    w.typeEditors = [];
    w.$('[data-typed-document]')?.remove();
    const host = clone(w.draft.type.replaceAll('_', '-'));
    host.dataset.typedDocument = '';
    w.$('.journal-window__body').append(host);
    if (w.draft.type === 'quest')
        quest(w, host, state, upload);
    if (w.draft.type === 'quest_board')
        board(w, host, state, open);
    if (w.draft.type === 'roll_table')
        table(w, host, state);
}
function quest(w, host, state, upload) {
    const q = w.draft.quest, editing = w.editing, tab = w.questTab || 'content';
    host.classList.toggle('quest-sheet--editing', editing);
    show(host.querySelector('nav'), editing);
    for (const b of host.querySelectorAll('[data-quest-tab]')) {
        show(b, state.is_gm || b.dataset.questTab !== 'gm');
        b.setAttribute('aria-pressed', String(b.dataset.questTab === tab));
        b.onclick = () => { w.questTab = b.dataset.questTab; w.render(); };
    }
    const content = host.querySelector('[data-quest-content]');
    if (!editing || tab === 'content') {
        const el = clone(editing ? 'quest-edit' : 'quest-read');
        content.append(el);
        if (editing) {
            for (const field of el.querySelectorAll('[data-q]')) {
                const key = field.dataset.q;
                field.value = key === 'title' ? w.draft.title : key === 'tags' ? q.tags.join(', ') : q.public[key];
                field.addEventListener(key === 'tags' ? 'change' : 'input', () => { if (key === 'title') {
                    w.draft.title = field.value;
                    w.$('.journal-window__title').value = field.value;
                }
                else if (key === 'tags')
                    q.tags = field.value.split(',').map(t => t.trim()).filter(Boolean);
                else
                    q.public[key] = field.value; w.touch(); });
            }
            for (const radio of el.querySelectorAll('input[type=radio]')) {
                radio.name = 'quest-status-' + w.draft.id;
                radio.checked = radio.value === q.status;
                radio.onchange = () => { q.status = radio.value; w.touch(); };
            }
            const portrait = el.querySelector('.quest-sheet__image-drop'), file = el.querySelector('input[type=file]');
            const refresh = () => { image(portrait.querySelector('img'), q.public.image.src); show(portrait.querySelector(':scope > svg'), !q.public.image.src); show(portrait.querySelector('[data-portrait=remove]'), !!q.public.image.src); };
            refresh();
            el.querySelector('[data-portrait=upload]').onclick = () => file.click();
            el.querySelector('[data-portrait=remove]').onclick = () => { q.public.image = { src: '', assetId: '' }; w.touch(); refresh(); };
            file.onchange = async () => { if (!file.files[0])
                return; try {
                const asset = await upload(w.draft.id, file.files[0]);
                q.public.image = { src: asset.src, assetId: asset.asset_id };
                w.touch();
                refresh();
            }
            catch (error) {
                w.error(error.message);
            } };
        }
        else {
            text(el, 'h2', w.draft.title);
            el.querySelector('[data-seal]').replaceWith(seal(q.status, false));
            image(el.querySelector('img'), q.public.image.src, w.draft.title);
            for (const fact of el.querySelectorAll('[data-fact]')) {
                const value = q.public[fact.dataset.fact];
                show(fact, !!value);
                text(fact, 'dd', value);
            }
            show(el.querySelector('dl'), !!(q.public.location || q.public.giver));
            const tags = el.querySelector('.quest-sheet__tags');
            show(tags, q.tags.length > 0);
            for (const tag of q.tags) {
                const li = document.createElement('li');
                li.append(icon('Tag'), document.createTextNode(tag));
                tags.append(li);
            }
        }
        editor(w, el.querySelector('[data-rich=description]'), q.public.description, 'Quest description', value => q.public.description = value, upload);
    }
    const grid = host.querySelector('.quest-sheet__outcome-grid');
    grid.classList.toggle('quest-sheet__outcome-grid--editing', editing);
    for (const key of ['objectives', 'rewards']) {
        const objective = key === 'objectives', rows = editing ? q[key] : q[key].filter(row => row.visibleToPlayers);
        if (editing ? tab !== key : !rows.length)
            continue;
        const el = clone('quest-outcomes');
        grid.append(el);
        el.querySelector('[data-icon-slot]').replaceWith(icon(objective ? 'ListChecks' : 'Coins'));
        text(el, '[data-label]', objective ? 'Objectives' : 'Rewards');
        const small = el.querySelector('small');
        show(small, objective);
        small.textContent = `${rows.filter(r => r.completed).length}/${rows.length}`;
        const add = el.querySelector('button');
        show(add, editing);
        add.disabled = rows.length >= 64;
        add.onclick = () => { q[key].push({ id: crypto.randomUUID(), text: '', visibleToPlayers: true, ...(objective ? { completed: false, optional: false, sortOrder: (rows.length + 1) * 10 } : {}) }); w.touch(); w.render(); };
        for (const row of rows) {
            let item;
            if (editing) {
                item = clone(objective ? 'objective-edit' : 'reward-edit');
                const input = item.querySelector('.journal-input');
                input.value = row.text;
                input.oninput = () => { row.text = input.value; w.touch(); };
                for (const box of item.querySelectorAll('[data-check]')) {
                    box.checked = row[box.dataset.check];
                    box.onchange = () => { row[box.dataset.check] = box.checked; w.touch(); if (objective)
                        small.textContent = `${rows.filter(r => r.completed).length}/${rows.length}`; };
                }
                item.querySelector('button').onclick = () => { q[key] = q[key].filter(r => r.id !== row.id); w.touch(); w.render(); };
            }
            else {
                item = document.createElement('article');
                item.className = 'quest-sheet__objective';
                if (objective)
                    item.append(icon(row.completed ? 'CheckCircle' : 'Circle'));
                const span = document.createElement('span');
                span.textContent = row.text;
                item.append(span);
                if (objective && row.optional) {
                    const small = document.createElement('small');
                    small.textContent = 'Optional';
                    item.append(small);
                }
            }
            if (objective)
                item.classList.toggle('quest-sheet__objective--done', row.completed);
            el.querySelector('[data-rows]').append(item);
        }
    }
    const gm = host.querySelector('[data-quest-gm]');
    show(gm, editing && state.is_gm && tab === 'gm');
    if (editing && state.is_gm && tab === 'gm') {
        q.gm ??= { notes: emptyDoc(), secrets: emptyDoc() };
        for (const key of ['notes', 'secrets'])
            editor(w, gm.querySelector(`[data-rich=${key}]`), q.gm[key], key === 'notes' ? 'GM notes' : 'Secrets', value => q.gm[key] = value, upload);
    }
}
function board(w, host, state, open) {
    const editing = w.editing, entries = (editing ? w.draft.board_entries : w.draft.board_display_entries) || [];
    w.boardFilters ??= new Set(statuses);
    host.classList.toggle('quest-board--editing', editing);
    show(host.querySelector('[data-board-editor]'), editing && state.is_gm);
    for (const b of host.querySelectorAll('[data-status-filter]')) {
        b.setAttribute('aria-pressed', String(w.boardFilters.has(b.dataset.statusFilter)));
        b.onclick = () => { w.boardFilters.has(b.dataset.statusFilter) ? w.boardFilters.delete(b.dataset.statusFilter) : w.boardFilters.add(b.dataset.statusFilter); w.render(); };
    }
    const form = host.querySelector('form'), select = form.querySelector('select');
    for (const q of state.journals.filter(j => j.type === 'quest' && !entries.some(e => e.quest_id === j.id))) {
        const option = document.createElement('option');
        option.value = q.id;
        option.textContent = q.title;
        select.append(option);
    }
    select.onchange = () => form.querySelector('button').disabled = !select.value;
    form.onsubmit = e => { e.preventDefault(); void w.perform('board-add', { quest_id: select.value }); };
    const list = host.querySelector('[data-board-entries]');
    list.className = editing ? 'quest-board__list' : 'quest-board__wall';
    for (const [index, entry] of entries.entries()) {
        if (editing && !w.boardFilters.has(entry.card.status))
            continue;
        const card = entry.card, el = clone(editing ? 'board-edit-card' : 'board-read-card');
        el.dataset.status = card.status;
        el.classList.toggle('quest-board__card--pinned', entry.pinned);
        list.append(el);
        if (editing) {
            const mark = icon(entry.pinned ? 'PushPin' : 'Scroll');
            mark.classList.add('quest-board__mark');
            el.querySelector('[data-mark]').replaceWith(mark);
            text(el, '.quest-board__title', card.title);
            el.querySelector('.quest-board__title').onclick = () => open(entry.quest_id);
            el.querySelector('select').value = card.status;
            el.querySelector('select').onchange = e => void w.perform('status', { journal_id: entry.quest_id, status: e.target.value });
            for (const b of el.querySelectorAll('[data-board-action]')) {
                const action = b.dataset.boardAction;
                b.disabled = action === 'up' ? index === 0 : action === 'down' ? index === entries.length - 1 : false;
                if (action === 'pin')
                    b.setAttribute('aria-pressed', String(entry.pinned));
                b.onclick = () => { if (action === 'pin')
                    void w.perform('board-pin', { quest_id: entry.quest_id, pinned: !entry.pinned }); if (action === 'remove')
                    void w.perform('board-remove', { quest_id: entry.quest_id }); if (action === 'up' || action === 'down') {
                    const ids = entries.map(e => e.quest_id), target = index + (action === 'up' ? -1 : 1);
                    [ids[index], ids[target]] = [ids[target], ids[index]];
                    void w.perform('board-reorder', { ordered_quest_ids: ids });
                } };
            }
        }
        else {
            el.querySelector('button').onclick = () => open(entry.quest_id);
            image(el.querySelector('img'), card.image.src);
            el.querySelector('[data-seal]').replaceWith(seal(card.status));
            show(el.querySelector('.quest-board__pinned'), entry.pinned);
            text(el, 'h3', card.title);
            text(el, '.quest-board__summary', card.summary);
            show(el.querySelector('.quest-board__summary'), !!card.summary);
            show(el.querySelector('.quest-board__facts'), !!(card.location || card.giver));
            for (const fact of el.querySelectorAll('[data-fact]')) {
                show(fact, !!card[fact.dataset.fact]);
                text(fact, 'span', card[fact.dataset.fact]);
            }
            show(el.querySelector('[data-objectives]'), card.objectives.length > 0);
            text(el, 'h4 small', `${card.objectives.filter(o => o.completed).length}/${card.objectives.length}`);
            const objectives = el.querySelector('.quest-board__objectives');
            for (const objective of card.objectives.slice(0, 2)) {
                const li = document.createElement('li');
                li.classList.toggle('quest-board__objective--done', objective.completed);
                const span = document.createElement('span');
                span.textContent = objective.text;
                li.append(icon(objective.completed ? 'CheckCircle' : 'Circle'), span);
                objectives.append(li);
            }
            if (card.objectives.length > 2) {
                const li = document.createElement('li');
                li.textContent = '+' + (card.objectives.length - 2);
                objectives.append(li);
            }
            show(el.querySelector('.quest-board__section--rewards'), card.rewards.length > 0);
            text(el, '.quest-board__section--rewards p', card.rewards.map(r => r.text).join(' · '));
        }
    }
    show(host.querySelector('.quest-board__empty'), !entries.length);
    text(host, '.quest-board__empty p', editing ? 'Add a quest to the board to publish it here.' : 'No published quests on this board.');
    show(host.querySelector('.quest-board__filtered'), entries.length > 0 && !list.children.length);
}
function table(w, host, state) {
    const t = w.draft.roll_table, editing = w.editing;
    for (const el of host.querySelectorAll('[data-table-edit]'))
        show(el, editing);
    show(host.querySelector('[data-replacement-label]'), !editing);
    text(host, '[data-replacement-label]', t.withReplacement ? '∞ With replacement' : '1× Without replacement');
    const replacement = host.querySelector('[data-replacement]');
    replacement.checked = t.withReplacement;
    replacement.onchange = () => { t.withReplacement = replacement.checked; w.touch(); w.render(); };
    const visibility = host.querySelector('[data-result-visibility]');
    visibility.value = t.resultVisibility;
    visibility.disabled = !state.is_gm;
    visibility.onchange = () => { t.resultVisibility = visibility.value; w.touch(); };
    const roll = host.querySelector('[data-table-roll]');
    show(roll, state.is_gm);
    roll.onclick = () => void w.perform('roll');
    const reset = host.querySelector('[data-table-reset]');
    show(reset, state.is_gm && !t.withReplacement);
    reset.onclick = () => void w.perform('reset');
    const add = host.querySelector('[data-table-add]');
    show(add, editing);
    add.disabled = t.entries.length >= 256;
    add.onclick = () => { t.entries.push({ id: crypto.randomUUID(), name: '', weight: 1, result: '', active: true, drawn: false, sortOrder: (t.entries.length + 1) * 10 }); w.touch(); w.render(); };
    show(host.querySelector('.roll-table__scroll'), editing);
    show(host.querySelector('.roll-table__results'), !editing);
    show(host.querySelector('[data-table-empty]'), !t.entries.length);
    const eligible = e => e.active && (t.withReplacement || !e.drawn), total = () => t.entries.filter(eligible).reduce((n, e) => n + Number(e.weight), 0), chance = e => (total() && eligible(e) ? Number(e.weight) / total() * 100 : 0).toFixed(1) + '%';
    const refresh = () => { text(host, '[data-entry-count]', t.entries.length); text(host, '[data-total-weight]', total()); roll.disabled = total() <= 0; for (const row of host.querySelectorAll('[data-entry-id]')) {
        const entry = t.entries.find(e => e.id === row.dataset.entryId);
        row.querySelector('[data-chance]').textContent = chance(entry);
    } };
    for (const entry of t.entries) {
        const el = clone(editing ? 'table-row' : 'table-result');
        el.classList.toggle('roll-table__entry--drawn', entry.drawn && !t.withReplacement);
        if (editing) {
            el.dataset.entryId = entry.id;
            for (const input of el.querySelectorAll('[data-entry]')) {
                const key = input.dataset.entry;
                if (key === 'active')
                    input.checked = entry.active;
                else
                    input.value = entry[key];
                input.oninput = () => { entry[key] = key === 'active' ? input.checked : key === 'weight' ? Math.max(1, Math.min(1000000, Number(input.value) || 1)) : input.value; w.touch(); refresh(); };
            }
            el.querySelector('button').onclick = () => { t.entries = t.entries.filter(e => e.id !== entry.id); w.touch(); w.render(); };
            el.ondragstart = e => e.dataTransfer.setData('application/x-gravewright-table-entry', entry.id);
            el.ondragover = e => e.preventDefault();
            el.ondrop = e => { e.preventDefault(); const from = t.entries.findIndex(r => r.id === e.dataTransfer.getData('application/x-gravewright-table-entry')), to = t.entries.indexOf(entry); if (from < 0)
                return; t.entries.splice(to, 0, t.entries.splice(from, 1)[0]); t.entries.forEach((r, i) => r.sortOrder = (i + 1) * 10); w.touch(); w.render(); };
            host.querySelector('tbody').append(el);
        }
        else {
            el.classList.toggle('roll-table__entry--inactive', !entry.active);
            text(el, 'strong', entry.name);
            text(el, 'p', entry.result);
            show(el.querySelector('p'), !!entry.result);
            text(el, 'small', `${entry.weight} · ${chance(entry)}${entry.drawn && !t.withReplacement ? ' · Sorteada' : !entry.active ? ' · Inativa' : ''}`);
            host.querySelector('.roll-table__results').append(el);
        }
    }
    refresh();
}
