import { mountModal } from '/static/gravewright_table/modal.js';
import { openFormModal, modalText } from '/static/gravewright_table/form-modal.js';
import { mergePatch, getPath } from '/static/gravewright_web/vendor/datastar-1.0.3.js';
import { detachWindow, restoreWindow } from '/static/gravewright_table/window-controls.js';
import { richText, emptyDoc } from './editor.js';
import { writeReference, readReference } from '/static/gravewright_table/references.js';
import { pdfView } from './pdf.js';
import { renderType, typeLabels, typeIcons } from './types.js';
import { openPresentation, presentationLabel } from './presentation.js';
import { openPermissions } from '/static/gravewright_table/permissions.js';
import { initialContent, restoreContent } from '/static/gravewright_table/content-state.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { registerEscapeClose } from '/static/gravewright_web/escape.js';
import { MAX_CHAPTERS, chapterRows, chapterPath, selectedChapter, canParentChapter, saveChapter, reorderChapter, deleteChapter, movePageToChapter } from './journal-structure.js';
const translator = createTranslator(), t = (key, params) => translator.t(key, params);
const structureResult = action => { try { return action(); } catch (error) { throw Error(t(error.message)); } };
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
let state = { journals: [], folders: [], members: [], is_gm: false }, waitingOpen = new Map(), windows = new Map(), menu, dialog, popup;
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
    const el = openFormModal(modalText('Confirm deletion', 'Confirmar exclusão'), [], action, {key:'journal-confirm',submitLabel:modalText('Delete','Excluir')});
    const message = document.createElement('p'); message.textContent = text;
    el.querySelector('[data-fields]').append(message);
}
function prompt(label, value, action) {
    return openFormModal(label, [{name:'value',label,value,required:true}], form => action(form.elements.value.value), {key:'journal-prompt'});
}
function form(name, submit) {
    dialog?.close();
    const el = clone(name);
    dialog = el;
    const footer = document.createElement('footer');
    let cancel = el.querySelector('[data-cancel]');
    if (!cancel) {
        cancel = document.createElement('button'); cancel.type = 'button'; cancel.dataset.cancel = '';
        cancel.textContent = modalText('Cancel','Cancelar');
    }
    footer.append(cancel, el.querySelector('[type=submit]')); el.append(footer);
    const close = () => { if (!el.querySelector('fieldset').disabled) el.close(); };
    el.querySelector('.directory-dialog__close').addEventListener('click', close);
    cancel.addEventListener('click', close);
    el.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fieldset = el.querySelector('fieldset');
        fieldset.disabled = true;
        for (const button of el.querySelectorAll('button')) button.disabled = true;
        try {
            await submit(el);
            el.close();
        }
        catch (e) {
            const p = el.querySelector('[role=alert]');
            p.textContent = e.message;
            p.hidden = false;
        }
        finally {
            fieldset.disabled = false;
            for (const button of el.querySelectorAll('button')) button.disabled = false;
        }
    });
    mountModal(el, {canClose: () => !el.querySelector('fieldset').disabled});
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
                toggle.addEventListener('contextmenu', e => context(e, [['Create journal', () => create(f.id)], ['Create subfolder', () => folderForm(f.id)], ['Edit folder', () => folderForm('', f)], ['Permissions', () => openPermissions('journal-folders', f.id)], ['Delete folder', () => confirm('Delete this folder? Journals and subfolders will move to the parent folder.', () => commands('folder-delete', { folder_id: f.id }))]], 'gw-folder-menu'));
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
            el.addEventListener('contextmenu', e => context(e, [['Open document', () => open(j.id)], ...(state.is_gm ? [[presentationLabel(), () => windows.has(j.id) ? windows.get(j.id).present() : present(j)], ['Permissions', () => windows.has(j.id) ? windows.get(j.id).permissions() : openPermissions('journals', j.id)], ['Delete journal', () => confirm('Delete this journal?', () => commands('delete', { journal_id: j.id }))]] : [])], 'gw-folder-menu'));
            if (state.is_gm) {
                el.draggable = true;
                el.addEventListener('dragstart', e => {
                    e.dataTransfer.setData('application/x-gravewright-journal', JSON.stringify({ kind: 'journal', id: j.id }));
                    writeReference(e.dataTransfer, {type: 'journal', id: j.id, title: j.title});
                });
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
    return detachWindow(el, id, title, {width:987});
}
function open(id, pageId) {
    const existing = windows.get(id);
    if (existing) {
        if (pageId && existing.pages.some(page => page.id === pageId)) {
            existing.selected = pageId; existing.renderIndex(); existing.renderPage();
        }
        existing.el.classList.remove('journal-window--minimized');
        existing.el.dispatchEvent(new Event('focusin', { bubbles: true }));
        existing.el.ownerDocument.defaultView.focus();
        return;
    }
    const journal = state.journals.find(j => j.id === id);
    if (journal?.can_open === false) return;
    if (!journal) {
        waitingOpen.set(id, pageId);
        window.gravewrightRealtime.journalsSubscribe();
        return;
    }
    const win = new JournalWindow(journal);
    windows.set(id, win);
    if (pageId && win.pages.some(page => page.id === pageId)) {
        win.selected = pageId; win.renderIndex(); win.renderPage();
    }
}
function present(journal, page) {
    return openPresentation(journal, {members: state.members, targeted: state.targeted_handouts_enabled, page, send: payload => commands('present', payload)});
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
    get chapters() { return this.draft.chapters || []; }
    get currentChapter() { return selectedChapter(this.chapters, this.pages, this.selected); }
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
        const payload = { journal_id: d.id, title: d.title, visibility: d.visibility, version: d.version, data: d.type === 'quest' ? d.quest : d.type === 'roll_table' ? d.roll_table : d.type === 'quest_board' ? {} : { content: d.content_doc, cover: d.cover_image, chapters: this.chapters, sections: this.pages, gm: d.diary?.gm } };
        this.$('.journal-window__save').textContent = 'Saving…';
        this.pending = commands('update', structuredClone(payload)).then(result => { this.draft.version = result.version; this.dirty = this.revision !== revision; if (!this.dirty)
            for (const editor of this.typeEditors || [])
                if (!editor.isDestroyed && !editor.getJSON().content?.length)
                    editor.commands.setContent(emptyDoc().doc, false); this.$('.journal-window__save').textContent = this.dirty ? 'Pending changes' : 'Saved'; show(this.$('.journal-window__error'), false); return true; }).catch(e => { this.conflicted = e.code === 'conflict'; this.error(e.message); return false; }).finally(() => { this.pending = null; });
        const ok = await this.pending;
        return ok && this.dirty ? this.flush() : ok;
    }
    error(text) { this.$('.journal-window__error span').textContent = t(text); show(this.$('.journal-window__error'), true); this.$('.journal-window__save').textContent = t(text); }
    update(view) {
        this.remote = view;
        const pagesRestricted = !this.isGM && (this.draft.sections || []).some(old => {
            const page = (view.sections || []).find(p => p.id === old.id);
            return !page || old.can_edit && !page.can_edit;
        });
        if (pagesRestricted || !view.can_edit && this.draft.can_edit) {
            for (const modal of this.structureModals || []) modal.close(true);
            this.dirty = false;
            clearTimeout(this.timer);
            this.draft = structuredClone(view);
            this.editing = false;
            this.render();
        }
        else if (!this.dirty && !this.pending && !this.cancelPageTitleEdit && (view.version !== this.draft.version || view.type === 'quest_board')) {
            this.draft = structuredClone(view);
            this.render();
        }
    }
    async perform(action, data = {}) {
        if (!await this.flush())
            return false;
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
            return reply;
        }
        catch (error) {
            this.error(error.message);
            return false;
        }
    }
    async close(force = false) {
        if (!force && !await this.flush())
            return;
        clearTimeout(this.timer);
        for (const modal of this.structureModals || []) modal.close(true);
        this.destroyEditors();
        this.popup?.close();
        this.el.remove();
        if (windows.get(this.draft.id) === this) windows.delete(this.draft.id);
    }
    destroyEditors() {
        this.cancelPageTitleEdit?.();
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
        edit.querySelector('span').textContent = this.editing ? modalText('Read', 'Ler') : modalText('Edit', 'Editar');
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
    }
    renderIndex() {
        const nav = this.$('.diary-workspace__index');
        nav.replaceChildren(); nav.dataset.journalChapters = '';
        const search = this.$('[data-journal-search]').value.toLowerCase();
        const rows = chapterRows(this.chapters), matches = (page, chapterMatch = false) => (chapterMatch || page.title.toLowerCase().includes(search))
            && (this.filter === 'all' || page.kind === this.filter) && (!this.gmFilter || page.audience === 'gm');
        let count = 0;
        const appendPages = (list, pages) => {
            count += pages.length;
            for (const p of pages) {
                const el = clone('page-link');
                el.querySelector('[data-page-icon]').replaceWith(icon({ text: 'FileText', image: 'Image', pdf: 'FilePdf' }[p.kind]));
                el.querySelector('[data-page-title]').textContent = p.title;
                el.querySelector('[data-page-title]').setAttribute('translate', 'no');
                show(el.querySelector('.page-lock'), p.audience === 'gm');
                if (this.selected === p.id)
                    el.setAttribute('aria-current', 'page');
                el.addEventListener('click', () => { this.selected = p.id; this.renderIndex(); this.renderPage(); });
                el.addEventListener('contextmenu', e => {
                    if (this.isGM || this.editing && p.can_edit !== false)
                        this.pageMenu(e, p);
                });
                el.draggable = true;
                el.dataset.pageId = p.id;
                el.addEventListener('dragstart', e => {
                    e.dataTransfer.setData('application/x-gravewright-page', p.id);
                    writeReference(e.dataTransfer, {type: 'journal', id: this.draft.id, pageId: p.id, title: p.title});
                });
                list.append(el);
            }
        };
        const unassigned = this.pages.filter(page => !page.chapterId && matches(page));
        if (unassigned.length || this.editing && this.chapters.length && !search) {
            const section = document.createElement('section'); section.className = 'diary-workspace__chapter'; section.dataset.chapterId = '';
            const title = document.createElement('strong'); title.className = 'diary-workspace__ungrouped'; title.textContent = t('No chapter');
            section.append(title); appendPages(section, unassigned); nav.append(section);
        }
        const build = chapter => {
            const chapterMatch = !!search && chapterPath(this.chapters, chapter.id).toLowerCase().includes(search);
            const pages = this.pages.filter(page => page.chapterId === chapter.id && matches(page, chapterMatch));
            const children = rows.filter(row => row.parentId === chapter.id).map(build).filter(Boolean);
            if (search && !chapterMatch && !pages.length && !children.length) return null;
            const section = document.createElement('section'); section.className = 'diary-workspace__chapter'; section.dataset.chapterId = chapter.id;
            section.style.setProperty('--chapter-depth', String(chapter.depth));
            const header = document.createElement('div'); header.className = 'diary-workspace__chapter-heading';
            const title = document.createElement('button'); title.type = 'button'; title.className = 'diary-workspace__chapter-title'; title.dataset.chapterToggle = '';
            title.setAttribute('aria-expanded', String(!this.closedChapters.has(chapter.id) || !!search)); title.title = chapterPath(this.chapters, chapter.id);
            title.append(icon('CaretRight'));
            const name = document.createElement('strong'); name.textContent = chapter.name; name.setAttribute('translate', 'no');
            const small = document.createElement('small'); small.textContent = pages.length; title.append(name, small);
            title.addEventListener('click', () => { this.closedChapters.has(chapter.id) ? this.closedChapters.delete(chapter.id) : this.closedChapters.add(chapter.id);
                const focused = title.ownerDocument.activeElement === title;
                this.selected = { chapterId: chapter.id }; this.renderIndex(); this.renderPage();
                if (focused) this.el.querySelector(`[data-chapter-id="${CSS.escape(chapter.id)}"] [data-chapter-toggle]`)?.focus(); });
            title.addEventListener('contextmenu', event => this.chapterMenu(event, chapter));
            if (this.editing && this.draft.can_edit) {
                title.draggable = true; title.addEventListener('dragstart', event => event.dataTransfer.setData('application/x-gravewright-chapter', JSON.stringify({ journalId: this.draft.id, id: chapter.id })));
                const actions = document.createElement('button'); actions.type = 'button'; actions.className = 'journal-button diary-workspace__chapter-actions'; actions.textContent = '⋮';
                actions.dataset.chapterActions = ''; actions.setAttribute('aria-label', t('Chapter actions: {name}', { name: chapter.name }));
                actions.addEventListener('click', event => this.chapterMenu(event, chapter)); header.append(title, actions);
            } else header.append(title);
            section.append(header);
            const list = document.createElement('div'); list.className = 'diary-workspace__chapter-children'; show(list, !this.closedChapters.has(chapter.id) || !!search);
            appendPages(list, pages);
            if (!pages.length && !children.length) { const empty = document.createElement('p'); empty.className = 'diary-workspace__chapter-empty'; empty.textContent = t('No pages in this chapter.'); list.append(empty); }
            list.append(...children); section.append(list); return section;
        };
        const roots = rows.filter(row => row.parentId === null).map(build).filter(Boolean); nav.append(...roots);
        if (!count && !roots.length) {
            const p = document.createElement('p');
            p.className = 'diary-workspace__empty';
            p.textContent = search || this.filter !== 'all' ? modalText('No pages match the search.', 'Nenhuma página corresponde à pesquisa.') : modalText('This journal has no pages yet.', 'Este diário ainda não tem páginas.');
            nav.append(p);
        }
        for (const b of this.el.querySelectorAll('[data-add]'))
            b.disabled = this.pages.length >= 64;
        this.$('[data-action=chapter]').disabled = this.chapters.length >= MAX_CHAPTERS;
    }
    renderPageTitle() {
        this.cancelPageTitleEdit?.();
        const page = this.current, chapter = this.currentChapter;
        const title = this.$('.diary-workspace__identity strong');
        title.setAttribute('translate', 'no');
        title.textContent = this.selected === 'gm' ? t('GM area') : page?.title || chapter?.name || this.draft.title;
        if (!page || !this.editing || !this.draft.can_edit || page.can_edit === false) return;
        const button = title.ownerDocument.createElement('button');
        button.type = 'button'; button.dataset.journalPageTitle = '';
        button.className = 'diary-workspace__page-title'; button.textContent = page.title;
        button.title = t('Rename page'); button.setAttribute('aria-label', t('Rename page'));
        button.addEventListener('click', () => this.editPageTitle()); title.replaceChildren(button);
    }
    editPageTitle() {
        const page = this.current;
        if (!page || !this.editing || !this.draft.can_edit || page.can_edit === false || this.cancelPageTitleEdit) return;
        const title = this.$('.diary-workspace__identity strong'), input = title.ownerDocument.createElement('input');
        input.type = 'text'; input.value = page.title; input.maxLength = 120; input.required = true;
        input.className = 'diary-workspace__page-title-input'; input.dataset.journalPageTitleInput = '';
        input.setAttribute('aria-label', t('Page title')); input.setAttribute('translate', 'no');
        const lifetime = new AbortController(), doc = input.ownerDocument;
        let active = true, finishing = false, pointerDown = false, redraw, redrawTimer, releaseEscape;
        this.cancelPageTitleEdit = () => { active = false; lifetime.abort(); clearTimeout(redrawTimer); releaseEscape?.(); this.cancelPageTitleEdit = null; };
        const finish = (save, focus = false) => {
            if (!active || finishing) return;
            finishing = true;
            const value = input.value.trim();
            if (save && value && value !== page.title && this.current === page && this.editing
                && this.draft.can_edit && page.can_edit !== false && this.el.isConnected) {
                page.title = value; this.touch();
            }
            redraw = () => {
                if (!active) return;
                this.cancelPageTitleEdit();
                const label = this.$(`[data-page-id="${CSS.escape(page.id)}"] [data-page-title]`);
                if (label) label.textContent = page.title;
                if (focus) this.renderIndex();
                this.$('.diary-workspace__image')?.setAttribute('alt', page.title);
                this.renderPageTitle();
                if (!this.dirty && !this.pending && this.remote?.version !== undefined && this.remote.version !== this.draft.version)
                    this.update(this.remote);
                if (focus) this.$('[data-journal-page-title]')?.focus();
            };
            // A blur precedes pointerup/click. Even changing a label's height
            // can move the clicked page or arrow, so defer layout until release.
            if (!focus && pointerDown) input.readOnly = true;
            else redraw();
        };
        doc.addEventListener('pointerdown', () => { pointerDown = true; }, { capture: true, signal: lifetime.signal });
        const releasePointer = () => { pointerDown = false; if (redraw) { clearTimeout(redrawTimer); redrawTimer = setTimeout(redraw, 0); } };
        for (const type of ['pointerup', 'pointercancel', 'dragend'])
            doc.addEventListener(type, releasePointer, { capture: true, signal: lifetime.signal });
        input.addEventListener('blur', () => finish(true), { signal: lifetime.signal });
        input.addEventListener('keydown', event => {
            if (event.isComposing || !['Enter', 'Escape'].includes(event.key)) return;
            event.preventDefault(); event.stopPropagation(); finish(event.key === 'Enter', true);
        }, { signal: lifetime.signal });
        releaseEscape = registerEscapeClose(input, () => finish(false, true));
        title.replaceChildren(input); input.focus(); input.select();
    }
    renderPage() {
        this.destroyEditors();
        const host = this.$('.diary-workspace__page');
        host.replaceChildren();
        const p = this.current;
        const chapter = this.currentChapter;
        this.$('.diary-workspace__identity small').textContent = chapter ? chapterPath(this.chapters, chapter.id) : t('Journal');
        this.$('.diary-workspace__identity small').title = chapter ? chapterPath(this.chapters, chapter.id) : '';
        this.$('.diary-workspace__identity small').setAttribute('translate', 'no');
        this.renderPageTitle();
        this.$('[data-page-count]').textContent = p ? `${this.pages.indexOf(p) + 1} / ${this.pages.length}` : '';
        const persisted = this.remote || state.journals.find(row => row.id === this.draft.id) || this.draft;
        const pagePersisted = !p || [...(persisted.sections || []), ...(persisted.editable_sections || [])].some(row => row.id === p.id);
        const editor = (value, label, save) => { const el = document.createElement('div'); host.append(el); const instance = richText(el, value, !this.editing || p?.can_edit === false, file => upload(this.draft.id, file), label, next => { save(next); this.touch(); }, { journalId: this.draft.id, pageId: p?.id, pagePersisted, presentationTicket: this.draft.presentation_ticket }); this.cleanups.push(() => instance.destroy()); };
        if (chapter && this.selected?.chapterId) {
            const overview = document.createElement('div'); overview.className = 'diary-workspace__chapter-overview'; overview.dataset.chapterOverview = chapter.id;
            const summary = document.createElement('p'); summary.textContent = t('This chapter contains {pages} pages and {chapters} subchapters.', {
                pages: this.pages.filter(page => page.chapterId === chapter.id).length,
                chapters: this.chapters.filter(row => row.parentId === chapter.id).length }); overview.append(summary);
            if (this.editing && this.draft.can_edit) for (const [label, action] of [
                ['New page in this chapter', () => this.add('text', chapter.id)], ['New subchapter', () => this.chapterForm(null, chapter.id)],
            ]) { const button = document.createElement('button'); button.type = 'button'; button.className = 'journal-button'; button.textContent = t(label);
                button.disabled = label === 'New subchapter' ? !canParentChapter(this.chapters, null, chapter.id) : this.pages.length >= 64;
                button.addEventListener('click', action); overview.append(button); }
            host.append(overview); return;
        }
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
        if (this.editing && p.can_edit !== false) {
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
    structureModal(modal) {
        this.structureModals ||= new Set(); this.structureModals.add(modal);
        modal.addEventListener('close', () => this.structureModals.delete(modal), { once: true }); return modal;
    }
    expandChapter(id) {
        const seen = new Set(); let current = this.chapters.find(chapter => chapter.id === id);
        while (current && !seen.has(current.id)) { seen.add(current.id); this.closedChapters.delete(current.id); current = this.chapters.find(chapter => chapter.id === current.parentId); }
    }
    chapterForm(existing = null, parentId = null) {
        if (!this.editing || !this.draft.can_edit || !this.el.isConnected) return;
        const id = existing?.id || `chapter_${crypto.randomUUID().replaceAll('-', '').slice(0, 24)}`;
        const choices = [{ value: '', label: t('No parent chapter') }, ...chapterRows(this.chapters)
            .filter(row => canParentChapter(this.chapters, id, row.id)).map(row => ({ value: row.id, label: chapterPath(this.chapters, row.id) }))];
        const modal = openFormModal(t(existing ? 'Edit chapter' : parentId ? 'New subchapter' : 'New chapter'), [
            { name: 'name', label: t('Chapter name'), value: existing?.name || '', required: true },
            { name: 'parentId', label: t('Parent chapter'), value: existing?.parentId || parentId || '', options: choices },
        ], form => {
            if (!this.editing || !this.draft.can_edit || !this.el.isConnected) throw Error(t('You cannot edit this journal.'));
            this.draft.chapters = structureResult(() => saveChapter(this.chapters, { id, name: form.elements.name.value, parentId: form.elements.parentId.value || null }));
            this.draft.editable_sections = this.pages.map(page => page.chapterId === id ? movePageToChapter(page, this.chapters, id) : page);
            this.expandChapter(id); this.selected = { chapterId: id }; this.touch(); this.renderIndex(); this.renderPage();
        }, { key: 'journal-chapter' });
        modal.dataset.journalChapterEditor = existing?.id || 'new'; modal.querySelector('[name=name]').maxLength = 80;
        for (const option of modal.querySelectorAll('option')) if (option.value) option.setAttribute('translate', 'no');
        return this.structureModal(modal);
    }
    chapterMenu(event, chapter) {
        if (!this.editing || !this.draft.can_edit) return;
        const siblings = chapterRows(this.chapters).filter(row => row.parentId === chapter.parentId), index = siblings.findIndex(row => row.id === chapter.id);
        const move = direction => { this.draft.chapters = reorderChapter(this.chapters, chapter.id, direction); this.touch(); this.renderIndex(); };
        context(event, [
            ...(this.pages.length < 64 ? [[t('New page in this chapter'), () => this.add('text', chapter.id)]] : []),
            ...(canParentChapter(this.chapters, null, chapter.id) ? [[t('New subchapter'), () => this.chapterForm(null, chapter.id)]] : []),
            [t('Edit chapter'), () => this.chapterForm(chapter)],
            ...(index > 0 ? [[t('Move chapter up'), () => move(-1)]] : []),
            ...(index < siblings.length - 1 ? [[t('Move chapter down'), () => move(1)]] : []),
            ...(!this.pages.some(page => page.chapterId === chapter.id && page.can_edit === false) ? [[t('Delete chapter'), () => {
                const modal = openFormModal(t('Delete chapter'), [], () => {
                    if (!this.editing || !this.draft.can_edit || !this.el.isConnected) throw Error(t('You cannot edit this journal.'));
                    const next = structureResult(() => deleteChapter(this.chapters, this.pages, chapter.id)); this.draft.chapters = next.chapters; this.draft.editable_sections = next.pages;
                    if (this.selected?.chapterId === chapter.id) this.selected = chapter.parentId ? { chapterId: chapter.parentId } : 'opening';
                    this.closedChapters.delete(chapter.id); this.touch(); this.renderIndex(); this.renderPage();
                }, { key: 'journal-chapter-delete', submitLabel: t('Delete chapter') });
                modal.dataset.journalChapterDelete = chapter.id;
                const note = document.createElement('p'); note.textContent = t('Pages will remain without a chapter. Subchapters will move to the parent chapter.'); modal.querySelector('[data-fields]').append(note); this.structureModal(modal);
            }]] : []),
        ]);
        menu?.querySelector('button')?.focus();
    }
    movePageForm(page) {
        if (!this.editing || !this.draft.can_edit || page.can_edit === false) return;
        const modal = openFormModal(t('Move to chapter'), [{ name: 'chapterId', label: t('Chapter'), value: page.chapterId || '', options: [
            { value: '', label: t('No chapter') }, ...chapterRows(this.chapters).map(chapter => ({ value: chapter.id, label: chapterPath(this.chapters, chapter.id) })),
        ] }], form => {
            const current = this.pages.find(row => row.id === page.id);
            if (!this.editing || !this.draft.can_edit || !this.el.isConnected || !current || current.can_edit === false) throw Error(t('You cannot edit this journal.'));
            this.draft.editable_sections = structureResult(() => this.pages.map(row => row.id === page.id ? movePageToChapter(row, this.chapters, form.elements.chapterId.value || null) : row));
            this.expandChapter(form.elements.chapterId.value);
            this.touch(); this.renderIndex(); this.renderPage();
        }, { key: 'journal-page-chapter' }); modal.dataset.journalPageChapter = page.id;
        for (const option of modal.querySelectorAll('option')) if (option.value) option.setAttribute('translate', 'no');
        return this.structureModal(modal);
    }
    add(kind, chapterId = this.currentChapter?.id || null) {
        if (!this.editing || this.pages.length >= 64)
            return;
        const p = movePageToChapter({ id: 'section_' + crypto.randomUUID().replaceAll('-', '').slice(0, 12), title: t('New page'), kind, audience: 'public', level: 1, sortOrder: (this.pages.length + 1) * 10, content: emptyDoc(), src: '', assetId: '' }, this.chapters, chapterId);
        this.draft.editable_sections = [...this.pages, p];
        this.selected = p.id;
        this.expandChapter(chapterId);
        this.touch();
        this.renderIndex();
        this.renderPage();
    }
    pageMenu(e, p) {
        context(e, [...(this.isGM ? [...(p.audience !== 'gm' ? [[presentationLabel(), () => this.present(p)]] : []), ['Permissions', () => this.permissions(p)]] : []), ['Rename page', () => prompt('Name', p.title, value => { p.title = value; this.touch(); this.renderIndex(); this.renderPage(); })], [t('Move to chapter'), () => this.movePageForm(p)], ...(this.isGM ? [[p.audience === 'gm' ? 'Make public' : 'GM only', () => { p.audience = p.audience === 'gm' ? 'public' : 'gm'; this.touch(); this.renderIndex(); }]] : []), ['Remove page', () => {
                    this.draft.editable_sections = this.pages.filter(row => row.id !== p.id);
                    if (this.selected === p.id)
                        this.selected = this.pages[0]?.id || 'opening';
                    this.touch();
                    this.renderIndex();
                    this.renderPage();
                }]]);
    }
    async present(page) {
        if (!await this.flush()) return;
        return present(this.draft, page);
    }
    async permissions(page) {
        if (!await this.flush()) return;
        return openPermissions(page ? 'pages' : 'journals', page ? `${this.draft.id}:${page.id}` : this.draft.id);
    }
    bind() {
        this.$('.journal-window__title').addEventListener('input', e => { this.draft.title = e.target.value; this.touch(); });
        this.$('[data-journal-search]').addEventListener('input', () => this.renderIndex());

        this.$('.diary-workspace__index').addEventListener('dragover', e => {
            if (this.editing)
                e.preventDefault();
        });
        this.$('.diary-workspace__index').addEventListener('drop', e => {
            if (!this.editing)
                return;
            e.preventDefault();
            const chapterId = e.target.closest('[data-chapter-id]')?.dataset.chapterId || null;
            const draggedChapter = e.dataTransfer.getData('application/x-gravewright-chapter');
            if (draggedChapter) {
                try {
                    const value = JSON.parse(draggedChapter);
                    if (value.journalId !== this.draft.id || !this.draft.can_edit) return;
                    const chapter = this.chapters.find(row => row.id === value.id);
                    if (!chapter || !canParentChapter(this.chapters, chapter.id, chapterId)) return;
                    this.draft.chapters = saveChapter(this.chapters, { ...chapter, parentId: chapterId }); this.touch(); this.renderIndex(); this.renderPage();
                } catch { /* Invalid or cross-document drags do not modify this journal. */ }
                return;
            }
            const reference = readReference(e.dataTransfer);
            if (reference && reference.id !== this.draft.id) return;
            const id = e.dataTransfer.getData('application/x-gravewright-page'), oldPage = this.pages.find(p => p.id === id);
            const page = oldPage && movePageToChapter(oldPage, this.chapters, chapterId);
            if (!page || page.can_edit === false)
                return;
            const target = e.target.closest('[data-page-id]')?.dataset.pageId;
            const next = this.pages.filter(p => p.id !== id);
            const index = target ? next.findIndex(p => p.id === target) : next.length;
            next.splice(Math.max(0, index), 0, page);
            next.forEach((p, i) => p.sortOrder = (i + 1) * 10);
            this.draft.editable_sections = next;
            this.touch();
            this.renderIndex();
            this.renderPage();
        });
        this.$('[data-action=present]').title = presentationLabel();
        this.el.addEventListener('click', async (e) => {
            if (e.target.closest('[data-action=present]')) { await this.present(); return; }

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
            if (action === 'chapter') this.chapterForm();
            if (action === 'prev' || action === 'next') {
                const index = this.pages.findIndex(p => p.id === this.selected);
                this.selected = this.pages[index + (action === 'prev' ? -1 : 1)]?.id || 'opening';
                this.renderIndex();
                this.renderPage();
            }
        });
    }
}
window.gravewrightJournals = { toggle() { if (popup && !popup.closed) { popup.focus(); return; } if (panel.classList.contains('game-panel--minimized')) { restoreWindow(panel); mergePatch({_journalsOpen:true}); return; } mergePatch({ _journalsOpen: !getPath('_journalsOpen') }); requestAnimationFrame(() => panel.dispatchEvent(new Event('focusin', { bubbles: true }))); window.gravewrightRealtime.journalsSubscribe(); }, open };
window.gravewrightJournals.flush = id => windows.get(id)?.flush() ?? Promise.resolve(true);
window.addEventListener('gravewright:connected', () => window.gravewrightRealtime.journalsSubscribe());
function receiveState(next) {
    restoreContent('journals', () => {
        state = next;
        tree();
        for (const [id, win] of windows) {
            const view = state.journals.find(j => j.id === id);
            if (view && view.can_open !== false)
                win.update(view);
            else
                void win.close(true);
        }
        for (const [id, pageId] of waitingOpen)
            if (state.journals.some(j => j.id === id)) {
                waitingOpen.delete(id);
                open(id, pageId);
            }
    });
}
window.addEventListener('gravewright:journals', event => receiveState(event.detail));
const initial = initialContent('journals');
if(initial)receiveState(initial);
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
