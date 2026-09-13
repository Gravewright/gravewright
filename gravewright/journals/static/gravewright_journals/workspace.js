import { mergePatch, getPath } from '/static/gravewright_web/vendor/datastar-1.0.3.js';
import { richText, emptyDoc } from './editor.js';
import { pdfView } from './pdf.js';
import { renderType, typeLabels, typeIcons } from './types.js';
const panel = document.getElementById('journals-panel'), tableId = document.getElementById('table-workspace').dataset.tableId;
const clone = name => document.getElementById('journal-' + name).content.firstElementChild.cloneNode(true);
const icons = document.getElementById('journal-icons').content;
const icon = name => icons.querySelector(`[data-icon="${name}"]`).firstElementChild.cloneNode(true);
const show = (el, on) => {
    if (on)
        el.removeAttribute('hidden');
    else
        el.setAttribute('hidden', '');
};
let state = { journals: [], folders: [], members: [], is_gm: false }, waitingOpen = new Set(), windows = new Map(), menu, dialog, popup;
const commands = (action, data) => window.gravewrightRealtime.journalCommand(action, data);
const storedKey = `gravewright.directory.${tableId}.journals`;
let closedFolders = new Set();
try {
    closedFolders = new Set(JSON.parse(localStorage.getItem(storedKey) || '[]'));
}
catch { }
function directoryError(text = '') { const el = panel.querySelector('[data-journal-error]'); el.textContent = text; show(el, !!text); }
function dismiss() { menu?.remove(); menu = undefined; }
function context(event, items, cls = 'journal-context') {
    event.preventDefault();
    event.stopPropagation();
    dismiss();
    const doc = event.target.ownerDocument;
    menu = doc.createElement('menu');
    menu.className = cls;
    Object.assign(menu.style, { left: Math.min(event.clientX, doc.defaultView.innerWidth - 233) + 'px', top: Math.min(event.clientY, doc.defaultView.innerHeight - items.length * 38) + 'px' });
    for (const [label, fn] of items) {
        const b = doc.createElement('button');
        b.type = 'button';
        b.textContent = label;
        b.addEventListener('click', () => { dismiss(); void fn(); });
        menu.append(b);
    }
    doc.body.append(menu);
}
document.addEventListener('click', dismiss);
function confirm(text, action) {
    const el = clone('confirm');
    el.querySelector('p').textContent = text;
    const [yes, no] = el.querySelectorAll('button');
    yes.addEventListener('click', async () => {
        try {
            yes.disabled = true;
            await action();
            el.remove();
        }
        catch (e) {
            el.querySelector('p').textContent = e.message;
            yes.disabled = false;
        }
    });
    no.addEventListener('click', () => el.remove());
    document.body.append(el);
}
function prompt(label, value, action) { const el = clone('prompt'); el.querySelector('label span').textContent = label; el.querySelector('input').value = value; el.addEventListener('submit', e => { e.preventDefault(); action(el.querySelector('input').value); el.remove(); }); el.querySelector('button[type=button]').addEventListener('click', () => el.remove()); document.body.append(el); el.querySelector('input').focus(); }
function form(name, submit) {
    dialog?.remove();
    const el = clone(name);
    dialog = el;
    el.querySelector('.directory-dialog__close').addEventListener('click', () => el.remove());
    el.querySelector('[data-cancel]')?.addEventListener('click', () => el.remove());
    el.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            e.stopPropagation();
            el.remove();
        }
    });
    el.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fieldset = el.querySelector('fieldset');
        fieldset.disabled = true;
        try {
            await submit(el);
            el.remove();
        }
        catch (e) {
            const p = el.querySelector('[role=alert]');
            p.textContent = e.message;
            p.hidden = false;
        }
        finally {
            fieldset.disabled = false;
        }
    });
    document.body.append(el);
    el.querySelector('input')?.focus();
    return el;
}
function create(folderId = '') { const dialog = form('create', async (el) => { const result = await commands('create', { title: el.querySelector('[name=title]').value, folder_id: folderId, journal_type: el.querySelector('[name=type]').value }); open(result.journal_id); }); dialog.querySelector('select').onchange = e => dialog.querySelector('button[type=submit]').textContent = 'Create ' + typeLabels[e.target.value].toLocaleLowerCase(); }
function folderForm(parent = '', existing) {
    const el = form('folder-form', async (form) => { await commands(existing ? 'folder-update' : 'folder-create', { folder_id: existing?.id, parent_id: parent, name: form.querySelector('[name=name]').value, color: form.querySelector('[name=color]').value }); });
    el.querySelector('[name=colorPicker]').addEventListener('input', e => el.querySelector('[name=color]').value = e.target.value);
    el.querySelector('[name=color]').addEventListener('input', e => el.querySelector('[name=colorPicker]').value = e.target.value);
    if (existing) {
        el.querySelector('[name=colorPicker]').value = existing.color;
        el.querySelector('[name=name]').value = existing.name;
        el.querySelector('[name=color]').value = existing.color;
    }
}
function tree() {
    const root = panel.querySelector('[data-directory-tree]');
    root.replaceChildren();
    const query = panel.querySelector('input[type=search]').value.trim().toLowerCase();
    const entries = state.journals.filter(j => j.listed !== false && j.title.toLowerCase().includes(query));
    const visible = new Set(entries.map(j => j.folder_id));
    if (query) {
        let change = true;
        while (change) {
            change = false;
            for (const f of state.folders)
                if (visible.has(f.id) && f.parent_id && !visible.has(f.parent_id)) {
                    visible.add(f.parent_id);
                    change = true;
                }
        }
    }
    function draw(host, parent = '') {
        host.dataset.folder = parent;
        for (const f of state.folders.filter(f => (f.parent_id || '') === parent && (!query || visible.has(f.id)))) {
            const el = clone('folder');
            el.dataset.folder = f.id;
            el.style.setProperty('--folder-color', f.color);
            el.querySelector('.gw-folder__label').textContent = f.name;
            el.querySelector('.gw-folder__count').textContent = entries.filter(j => j.folder_id === f.id).length;
            const content = el.querySelector('.gw-folder__content'), toggle = el.querySelector('.gw-folder__toggle');
            const expanded = !!query || !closedFolders.has(f.id);
            show(content, expanded);
            toggle.setAttribute('aria-expanded', String(expanded));
            el.classList.toggle('gw-folder--open', expanded);
            toggle.addEventListener('click', () => {
                closedFolders.has(f.id) ? closedFolders.delete(f.id) : closedFolders.add(f.id);
                try {
                    localStorage.setItem(storedKey, JSON.stringify([...closedFolders]));
                }
                catch { }
                tree();
            });
            show(el.querySelector('.gw-folder__actions'), state.is_gm);
            show(el.querySelector('.gw-folder__grip'), state.is_gm);
            el.classList.toggle('gw-folder--movable', state.is_gm);
            el.querySelector('[data-subfolder]').addEventListener('click', () => folderForm(f.id));
            el.querySelector('.gw-folder__actions button').addEventListener('click', () => create(f.id));
            if (state.is_gm) {
                toggle.draggable = true;
                toggle.addEventListener('dragstart', e => e.dataTransfer.setData('application/x-gravewright-journal', JSON.stringify({ kind: 'folder', id: f.id })));
                toggle.addEventListener('contextmenu', e => context(e, [['Create journal', () => create(f.id)], ['Create subfolder', () => folderForm(f.id)], ['Edit folder', () => folderForm('', f)], ['Delete folder', () => confirm('Delete this folder? Journals and subfolders will move to the parent folder.', () => commands('folder-delete', { folder_id: f.id }))]], 'gw-folder-menu'));
            }
            draw(el.querySelector('.directory-tree'), f.id);
            host.append(el);
        }
        for (const j of entries.filter(j => (j.folder_id || '') === parent)) {
            const el = clone('entry');
            el.querySelector('strong').textContent = j.title;
            el.title = typeLabels[j.type];
            el.querySelector(':scope > svg').replaceWith(icon(typeIcons[j.type]));
            show(el.querySelector('.directory-entry__grip'), state.is_gm);
            el.addEventListener('click', () => open(j.id));
            el.addEventListener('contextmenu', e => context(e, [['Open document', () => open(j.id)], ...(state.is_gm ? [['Permissions', () => { open(j.id); windows.get(j.id)?.permissions(); }], ['Delete journal', () => confirm('Delete this journal?', () => commands('delete', { journal_id: j.id }))]] : [])], 'gw-folder-menu'));
            if (state.is_gm) {
                el.draggable = true;
                el.addEventListener('dragstart', e => e.dataTransfer.setData('application/x-gravewright-journal', JSON.stringify({ kind: 'journal', id: j.id })));
            }
            host.append(el);
        }
    }
    draw(root);
    show(panel.querySelector('.journal-directory__empty'), !state.journals.length);
}
panel.querySelector('[data-directory-tree]').addEventListener('dragover', e => {
    if (state.is_gm)
        e.preventDefault();
});
panel.querySelector('[data-directory-tree]').addEventListener('drop', async (e) => {
    if (!state.is_gm)
        return;
    e.preventDefault();
    e.stopPropagation();
    try {
        const item = JSON.parse(e.dataTransfer.getData('application/x-gravewright-journal'));
        const target = e.target.closest('[data-folder]')?.dataset.folder || '';
        await commands(item.kind === 'folder' ? 'folder-move' : 'move', item.kind === 'folder' ? { folder_id: item.id, target_parent_id: target } : { journal_id: item.id, target_folder_id: target });
    }
    catch (e) {
        directoryError(e.message);
    }
});
panel.querySelector('input[type=search]').addEventListener('input', tree);
panel.addEventListener('click', e => {
    const action = e.target.closest('[data-journal-directory]')?.dataset.journalDirectory;
    if (action === 'create')
        create();
    if (action === 'folder')
        folderForm();
    if (action === 'close')
        mergePatch({ _journalsOpen: false });
    if (action === 'minimize')
        panel.classList.toggle('game-panel--minimized');
    if (action === 'detach')
        popup = detach(panel, 'journals-directory', 'Journals');
});
function detach(el, id, title) {
    const doc = el.ownerDocument;
    if (doc !== document) {
        doc.defaultView.focus();
        return;
    }
    const child = window.open('', id, 'popup,width=987,height=754');
    if (!child)
        return;
    child.document.title = title;
    for (const style of document.querySelectorAll('style,link[rel=stylesheet]'))
        child.document.head.append(style.cloneNode(true));
    const marker = document.createComment('detached-journal');
    el.replaceWith(marker);
    child.document.body.append(el);
    el.classList.add(el === panel ? 'game-panel--detached' : 'journal-window--detached');
    child.addEventListener('pagehide', () => {
        if (marker.isConnected)
            marker.replaceWith(el);
        el.classList.remove('journal-window--detached', 'game-panel--detached');
    });
    return child;
}
function open(id) {
    const existing = windows.get(id);
    if (existing) {
        existing.el.classList.remove('journal-window--minimized');
        existing.el.dispatchEvent(new Event('focusin', { bubbles: true }));
        existing.el.ownerDocument.defaultView.focus();
        return;
    }
    const journal = state.journals.find(j => j.id === id);
    if (!journal) {
        waitingOpen.add(id);
        return;
    }
    windows.set(id, new JournalWindow(journal));
}
async function upload(journalId, file) {
    const data = new FormData();
    data.append('campaign_id', tableId);
    data.append('journal_id', journalId);
    data.append('file', file);
    const token = document.cookie.split('; ').find(p => p.startsWith('gravewright-csrf='))?.split('=').slice(1).join('=');
    const response = await fetch('/game/journal/asset', { method: 'POST', body: data, headers: { 'X-CSRF-Token': decodeURIComponent(token || '') } });
    const result = await response.json();
    if (!response.ok)
        throw new Error(result.error || 'Could not upload the file.');
    return result;
}
class JournalWindow {
    constructor(journal) { this.draft = structuredClone(journal); this.editing = journal.type === 'diary' && journal.can_edit; this.selected = (journal.sections || [])[0]?.id || 'opening'; this.filter = 'all'; this.gmFilter = false; this.closedChapters = new Set(); this.cleanups = []; this.dirty = false; this.revision = 0; this.el = clone('window'); this.el.dataset.journalId = journal.id; this.el.dataset.journalType = journal.type; this.el.setAttribute('aria-label', journal.title); document.body.append(this.el); this.bind(); this.render(); }
    get isGM() { return state.is_gm && !this.draft.presentation_ticket; }
    $(selector) { return this.el.querySelector(selector); }
    get pages() { return this.draft.editable_sections || this.draft.sections || []; }
    get current() { return this.pages.find(p => p.id === this.selected); }
    touch() {
        if (!this.editing || !this.draft.can_edit)
            return;
        this.dirty = true;
        this.revision++;
        this.$('.journal-window__save').textContent = 'Pending changes';
        clearTimeout(this.timer);
        this.timer = setTimeout(() => void this.flush(), 700);
    }
    async flush() {
        clearTimeout(this.timer);
        if (this.pending) {
            if (!await this.pending)
                return false;
            return this.dirty ? this.flush() : true;
        }
        if (!this.dirty)
            return true;
        const revision = this.revision;
        const d = this.draft;
        const payload = { journal_id: d.id, title: d.title, visibility: d.visibility, version: d.version, data: d.type === 'quest' ? d.quest : d.type === 'roll_table' ? d.roll_table : d.type === 'quest_board' ? {} : { content: d.content_doc, cover: d.cover_image, sections: this.pages, gm: d.diary?.gm } };
        this.$('.journal-window__save').textContent = 'Saving…';
        this.pending = commands('update', structuredClone(payload)).then(result => { this.draft.version = result.version; this.dirty = this.revision !== revision; if (!this.dirty)
            for (const editor of this.typeEditors || [])
                if (!editor.isDestroyed && !editor.getJSON().content?.length)
                    editor.commands.setContent(emptyDoc().doc, false); this.$('.journal-window__save').textContent = this.dirty ? 'Pending changes' : 'Saved'; show(this.$('.journal-window__error'), false); return true; }).catch(e => { this.conflicted = e.code === 'conflict'; this.error(e.message); return false; }).finally(() => { this.pending = null; });
        const ok = await this.pending;
        return ok && this.dirty ? this.flush() : ok;
    }
    error(text) { this.$('.journal-window__error span').textContent = text; show(this.$('.journal-window__error'), true); this.$('.journal-window__save').textContent = text; }
    update(view) {
        this.remote = view;
        if (!view.can_edit && this.draft.can_edit) {
            this.dirty = false;
            clearTimeout(this.timer);
            this.draft = structuredClone(view);
            this.editing = false;
            this.render();
        }
        else if (!this.dirty && !this.pending && (view.version !== this.draft.version || view.type === 'quest_board')) {
            this.draft = structuredClone(view);
            this.render();
        }
    }
    async perform(action, data = {}) {
        if (!await this.flush())
            return;
        try {
            const reply = await commands(action, { journal_id: this.draft.id, ...data });
            if (reply.entry) {
                let output = this.$('.journal-window__result');
                if (!output) {
                    output = document.createElement('output');
                    output.className = 'journal-window__result';
                    this.el.append(output);
                }
                output.textContent = `${reply.entry.name}: ${reply.entry.result}`;
            }
        }
        catch (error) {
            this.error(error.message);
        }
    }
    async close(force = false) {
        if (!force && !await this.flush())
            return;
        clearTimeout(this.timer);
        this.destroyEditors();
        this.popup?.close();
        this.el.remove();
        if (windows.get(this.draft.id) === this) windows.delete(this.draft.id);
    }
    destroyEditors() {
        for (const cleanup of this.cleanups)
            cleanup();
        this.cleanups = [];
    }
    render() {
        const d = this.draft;
        this.$('.journal-window__title').value = d.title;
        this.$('[data-title]').textContent = d.title;
        show(this.$('.journal-window__title'), this.editing);
        show(this.$('[data-title]'), !this.editing);
        show(this.$('[data-action=edit]'), d.can_edit);
        const edit = this.$('[data-action=edit]');
        edit.querySelector('svg').replaceWith(icon(this.editing ? 'Eye' : 'PencilSimple'));
        edit.querySelector('span').textContent = this.editing ? 'Read' : 'Edit';
        show(this.$('[data-action=permissions]'), this.isGM && !d.presentation_ticket);
        show(this.$('[data-action=present]'), this.isGM && !d.presentation_ticket);
        show(this.$('[data-action=gm]'), this.isGM && this.editing);
        show(this.$('[data-filter=gm]'), this.isGM);
        show(this.$('.diary-workspace__create'), this.editing);
        show(this.$('.diary-workspace'), d.type === 'diary');
        this.$('.journal-window__identity small').textContent = typeLabels[d.type];
        if (d.type === 'diary') {
            this.renderIndex();
            this.renderPage();
        }
        else {
            renderType(this, {...state,is_gm:this.isGM}, upload, open);
        }
        if (!this.$('.journal-window__permissions').hidden)
            this.renderPermissions();
    }
    renderIndex() {
        const nav = this.$('.diary-workspace__index');
        nav.replaceChildren();
        const search = this.$('[data-journal-search]').value.toLowerCase();
        const groups = [...new Set(this.pages.map(p => p.category))];
        let count = 0;
        for (const category of groups) {
            const pages = this.pages.filter(p => p.category === category && p.title.toLowerCase().includes(search) && (this.filter === 'all' || p.kind === this.filter) && (!this.gmFilter || p.audience === 'gm'));
            if (!pages.length)
                continue;
            count += pages.length;
            const section = document.createElement('section');
            section.className = 'diary-workspace__chapter';
            section.dataset.chapter = category;
            if (category) {
                const title = document.createElement('button');
                title.type = 'button';
                title.className = 'diary-workspace__chapter-title';
                title.append(icon('CaretRight'));
                const strong = document.createElement('strong');
                strong.textContent = category;
                const small = document.createElement('small');
                small.textContent = pages.length;
                title.append(strong, small);
                title.addEventListener('click', () => { this.closedChapters.has(category) ? this.closedChapters.delete(category) : this.closedChapters.add(category); this.renderIndex(); });
                title.addEventListener('contextmenu', e => {
                    if (this.editing)
                        context(e, [['New page in this chapter', () => this.add('text', category)], ['Rename chapter', () => prompt('Name', category, value => {
                                    for (const p of this.pages)
                                        if (p.category === category)
                                            p.category = value;
                                    this.touch();
                                    this.renderIndex();
                                })], ['Ungroup chapter', () => {
                                    for (const p of this.pages)
                                        if (p.category === category)
                                            p.category = '';
                                    this.touch();
                                    this.renderIndex();
                                }]]);
                });
                section.append(title);
            }
            const list = document.createElement('div');
            show(list, !this.closedChapters.has(category) || !!search);
            for (const p of pages) {
                const el = clone('page-link');
                el.querySelector('[data-page-icon]').replaceWith(icon({ text: 'FileText', image: 'Image', pdf: 'FilePdf' }[p.kind]));
                el.querySelector('[data-page-title]').textContent = p.title;
                show(el.querySelector('.page-lock'), p.audience === 'gm');
                if (this.selected === p.id)
                    el.setAttribute('aria-current', 'page');
                el.addEventListener('click', () => { this.selected = p.id; this.renderIndex(); this.renderPage(); });
                el.addEventListener('contextmenu', e => {
                    if (this.editing)
                        this.pageMenu(e, p);
                });
                el.draggable = this.editing;
                el.dataset.pageId = p.id;
                el.addEventListener('dragstart', e => e.dataTransfer.setData('application/x-gravewright-page', p.id));
                list.append(el);
            }
            section.append(list);
            nav.append(section);
        }
        if (!count) {
            const p = document.createElement('p');
            p.className = 'diary-workspace__empty';
            p.textContent = search || this.filter !== 'all' ? 'No pages match the search.' : 'This journal has no pages yet.';
            nav.append(p);
        }
        for (const b of this.el.querySelectorAll('[data-add]'))
            b.disabled = this.pages.length >= 64;
    }
    renderPage() {
        this.destroyEditors();
        const host = this.$('.diary-workspace__page');
        host.replaceChildren();
        const p = this.current;
        this.$('.diary-workspace__identity small').textContent = p?.category || 'Journal';
        this.$('.diary-workspace__identity strong').textContent = this.selected === 'gm' ? 'GM area' : p?.title || this.draft.title;
        this.$('[data-page-count]').textContent = p ? `${this.pages.indexOf(p) + 1} / ${this.pages.length}` : '';
        const editor = (value, label, save) => { const el = document.createElement('div'); host.append(el); const instance = richText(el, value, !this.editing, file => upload(this.draft.id, file), label, next => { save(next); this.touch(); }); this.cleanups.push(() => instance.destroy()); };
        if (this.selected === 'gm' && this.isGM) {
            const gm = this.draft.diary?.gm;
            if (!gm)
                return;
            for (const [key, title, label] of [['notes', 'GM notes', 'GM notes'], ['secrets', 'Secrets', 'GM secrets']]) {
                const h = document.createElement('h3');
                h.textContent = title;
                host.append(h);
                editor(gm[key], label, value => gm[key] = value);
            }
            return;
        }
        if (!p) {
            const content = this.draft.content_doc?.doc?.content || [];
            const blank = content.every(node => node.type === 'paragraph' && !node.content?.length);
            if (!this.pages.length && blank && !this.writingIntroduction) {
                const empty = clone('empty');
                show(empty.querySelector('.journal-empty__actions'), !!this.draft.can_edit);
                empty.querySelector('[data-empty-page]').addEventListener('click', () => {
                    this.editing = true;
                    this.render();
                    this.add('text');
                });
                empty.querySelector('[data-empty-cover]').addEventListener('click', () => {
                    this.writingIntroduction = true;
                    this.editing = true;
                    this.render();
                });
                host.append(empty);
                return;
            }
            editor(this.draft.content_doc, 'Journal cover', value => this.draft.content_doc = value);
            return;
        }
        if (p.kind === 'text') {
            editor(p.content, 'Page content', value => p.content = value);
            return;
        }
        if (this.editing) {
            const el = clone('upload');
            el.querySelector('span').textContent = p.src ? 'Replace file' : 'Upload file';
            const input = el.querySelector('input');
            input.accept = p.kind === 'pdf' ? 'application/pdf' : 'image/png,image/jpeg,image/webp';
            input.addEventListener('change', async () => {
                if (!input.files[0])
                    return;
                try {
                    const asset = await upload(this.draft.id, input.files[0]);
                    p.assetId = asset.asset_id;
                    p.src = asset.src;
                    this.touch();
                    if (this.current === p)
                        this.renderPage();
                }
                catch (e) {
                    const error = this.$('[data-upload-error]');
                    error.textContent = e.message;
                    show(error, true);
                }
            });
            host.append(el);
        }
        if (p.src && p.kind === 'image') {
            const image = document.createElement('img');
            image.className = 'diary-workspace__image';
            image.src = p.src;
            image.alt = p.title;
            host.append(image);
        }
        else if (p.assetId && p.kind === 'pdf') {
            let active = true;
            pdfView(host, p.assetId, p.title, clone, this.draft.presentation_ticket).then(cleanup => {
                if (active)
                    this.cleanups.push(cleanup);
                else
                    cleanup();
            });
            this.cleanups.push(() => active = false);
        }
        else {
            const text = document.createElement('p');
            text.className = 'diary-workspace__empty';
            text.textContent = 'This page has no file yet.';
            host.append(text);
        }
    }
    add(kind, category = this.current?.category || '') {
        if (!this.editing || this.pages.length >= 64)
            return;
        const p = { id: 'section_' + crypto.randomUUID().replaceAll('-', '').slice(0, 12), title: 'New page', category, kind, audience: 'public', level: 1, sortOrder: (this.pages.length + 1) * 10, content: emptyDoc(), src: '', assetId: '' };
        this.draft.editable_sections = [...this.pages, p];
        this.selected = p.id;
        this.touch();
        this.renderIndex();
        this.renderPage();
    }
    pageMenu(e, p) {
        context(e, [['Rename page', () => prompt('Name', p.title, value => { p.title = value; this.touch(); this.renderIndex(); this.renderPage(); })], ['Move to chapter', () => prompt('Chapter', p.category, value => { p.category = value; this.touch(); this.renderIndex(); this.renderPage(); })], ...(this.isGM ? [[p.audience === 'gm' ? 'Make public' : 'GM only', () => { p.audience = p.audience === 'gm' ? 'public' : 'gm'; this.touch(); this.renderIndex(); }]] : []), ['Remove page', () => {
                    this.draft.editable_sections = this.pages.filter(row => row.id !== p.id);
                    if (this.selected === p.id)
                        this.selected = this.pages[0]?.id || 'opening';
                    this.touch();
                    this.renderIndex();
                    this.renderPage();
                }]]);
    }
    permissions() {
        const el = this.$('.journal-window__permissions');
        show(el, el.hidden);
        if (!el.hidden)
            this.renderPermissions();
    }
    renderPermissions() {
        this.$('[name=visibility]').value = this.draft.visibility;
        const host = this.$('[data-member-permissions]');
        host.replaceChildren();
        for (const member of state.members.filter(m => m.role !== 'gm')) {
            const el = clone('permission');
            el.querySelector('span').textContent = member.name;
            el.querySelector('select').value = this.draft.permissions?.[member.id] || 'none';
            el.querySelector('select').addEventListener('change', async (e) => {
                if (!await this.flush())
                    return;
                try {
                    const result = await commands('access', { journal_id: this.draft.id, target_user_id: member.id, access_level: e.target.value });
                    this.draft.version = result.version;
                }
                catch (error) {
                    this.error(error.message);
                }
            });
            host.append(el);
        }
    }
    bind() {
        this.$('.journal-window__title').addEventListener('input', e => { this.draft.title = e.target.value; this.touch(); });
        this.$('[data-journal-search]').addEventListener('input', () => this.renderIndex());
        this.$('[name=visibility]').addEventListener('change', e => { this.editing = true; this.draft.visibility = e.target.value; this.touch(); this.render(); });
        this.$('.diary-workspace__composer').addEventListener('submit', e => { e.preventDefault(); const input = e.target.querySelector('input'); this.add('text', input.value.trim()); input.value = ''; show(e.target, false); });
        this.$('.diary-workspace__index').addEventListener('dragover', e => {
            if (this.editing)
                e.preventDefault();
        });
        this.$('.diary-workspace__index').addEventListener('drop', e => {
            if (!this.editing)
                return;
            e.preventDefault();
            const id = e.dataTransfer.getData('application/x-gravewright-page'), page = this.pages.find(p => p.id === id);
            if (!page)
                return;
            const target = e.target.closest('[data-page-id]')?.dataset.pageId;
            page.category = e.target.closest('[data-chapter]')?.dataset.chapter || '';
            const next = this.pages.filter(p => p.id !== id);
            const index = target ? next.findIndex(p => p.id === target) : next.length;
            next.splice(Math.max(0, index), 0, page);
            next.forEach((p, i) => p.sortOrder = (i + 1) * 10);
            this.draft.editable_sections = next;
            this.touch();
            this.renderIndex();
        });
        const presentation = this.$('[data-presentation]');
        for (const member of state.targeted_handouts_enabled ? state.members : []) {
            const option = document.createElement('option'); option.value = member.id; option.textContent = member.name;
            presentation.querySelector('select').append(option);
        }
        presentation.onsubmit = async e => {
            e.preventDefault(); if (!await this.flush()) return;
            try { await commands('present', {journal_id:this.draft.id, target:presentation.querySelector('select').value}); presentation.hidden = true; }
            catch(error) {this.error('Could not present the journal.');}
        };
        this.el.addEventListener('click', async (e) => {
            if (e.target.closest('[data-action=present]')) { presentation.hidden = !presentation.hidden; return; }

            const b = e.target.closest('button');
            if (!b)
                return;
            if (b.dataset.add) {
                this.add(b.dataset.add);
                return;
            }
            if (b.dataset.filter) {
                if (b.dataset.filter === 'gm')
                    this.gmFilter = !this.gmFilter;
                else
                    this.filter = b.dataset.filter;
                for (const button of this.el.querySelectorAll('[data-filter]'))
                    button.setAttribute('aria-pressed', String(button.dataset.filter === 'gm' ? this.gmFilter : button.dataset.filter === this.filter));
                this.renderIndex();
                return;
            }
            const action = b.dataset.action;
            if (action === 'edit') {
                if (this.editing && !await this.flush())
                    return;
                this.editing = !this.editing;
                this.render();
            }
            if (action === 'save') {
                if (this.conflicted && this.remote) {
                    this.draft.version = this.remote.version;
                    this.conflicted = false;
                }
                void this.flush();
            }
            if (action === 'close')
                void this.close();
            if (action === 'minimize')
                this.el.classList.toggle('journal-window--minimized');
            if (action === 'detach')
                this.popup = detach(this.el, 'journal-' + this.draft.id, this.draft.title);
            if (action === 'permissions')
                this.permissions();
            if (action === 'cover' || action === 'gm') {
                this.selected = action === 'gm' ? 'gm' : 'opening';
                this.renderIndex();
                this.renderPage();
            }
            if (action === 'collapse' || action === 'expand') {
                this.$('.diary-workspace').classList.toggle('diary-workspace--collapsed', action === 'collapse');
                show(this.$('[data-action=expand]'), action === 'collapse');
            }
            if (action === 'filters') {
                const filters = this.$('.diary-workspace__filters');
                show(filters, filters.hidden);
                b.setAttribute('aria-expanded', String(!filters.hidden));
            }
            if (action === 'chapter') {
                const form = this.$('.diary-workspace__composer');
                show(form, form.hidden);
                if (!form.hidden)
                    form.querySelector('input').focus();
            }
            if (action === 'prev' || action === 'next') {
                const index = this.pages.findIndex(p => p.id === this.selected);
                this.selected = this.pages[index + (action === 'prev' ? -1 : 1)]?.id || 'opening';
                this.renderIndex();
                this.renderPage();
            }
        });
    }
}
window.gravewrightJournals = { toggle() { mergePatch({ _journalsOpen: !getPath('_journalsOpen') }); requestAnimationFrame(() => panel.dispatchEvent(new Event('focusin', { bubbles: true }))); window.gravewrightRealtime.journalsSubscribe(); }, open };
window.addEventListener('gravewright:connected', () => window.gravewrightRealtime.journalsSubscribe());
window.addEventListener('gravewright:journals', event => {
    state = event.detail;
    tree();
    for (const [id, win] of windows) {
        const view = state.journals.find(j => j.id === id);
        if (view)
            win.update(view);
        else
            void win.close(true);
    }
    for (const id of waitingOpen)
        if (state.journals.some(j => j.id === id)) {
            waitingOpen.delete(id);
            open(id);
        }
});
window.addEventListener('gravewright:access-revoked', () => {
    state = { journals: [], folders: [], members: [], is_gm: false };
    tree();
    for (const win of windows.values())
        void win.close(true);
});
window.addEventListener('beforeunload', e => {
    if ([...windows.values()].some(w => w.dirty)) {
        e.preventDefault();
        e.returnValue = '';
    }
});
window.addEventListener('pagehide', () => {
    popup?.close();
    for (const win of windows.values())
        win.popup?.close();
});
if (window.gravewrightRealtime)
    window.gravewrightRealtime.journalsSubscribe();

let presented;
const presentationsSeen = new Set();
window.addEventListener('gravewright:handout.presented', async ({detail}) => {
    if (presentationsSeen.has(detail.requestId)) return;
    presentationsSeen.add(detail.requestId);
    if (presentationsSeen.size > 100) presentationsSeen.delete(presentationsSeen.values().next().value);
    try {
        const response = await fetch(`/api/containers/${tableId}/journal-presentation/${encodeURIComponent(detail.ticket)}`);
        if (!response.ok) throw Error();
        const value = await response.json();
        await presented?.close(true);
        presented = new JournalWindow(value);
        const current = presented;
        setTimeout(() => {if (presented === current) void current.close(true);}, 90000);
    } catch {directoryError('The presentation expired or is unavailable.');}
});
window.addEventListener('gravewright:access-revoked', () => void presented?.close(true));
