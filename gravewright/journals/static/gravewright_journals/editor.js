// The original Tiptap editor, adapted from JournalRichText.vue without Vue.
import { Editor, Node, Extension, mergeAttributes, StarterKit, Link, Placeholder, Suggestion } from './vendor/editor.js';
import { readReference, referenceMime, followReference } from '/static/gravewright_table/references.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { createJournalResourceLinks, resourceNodeName, resourceHtml } from './resource-links.js';
import { referenceTextInput } from './reference-trigger.js';
import { registerEscapeClose } from '/static/gravewright_web/escape.js';
export const emptyDoc = () => ({ format: 'gw-journal-doc-v1', version: 1, doc: { type: 'doc', content: [{ type: 'paragraph' }] } });
const Image = Node.create({ name: 'gwImage', group: 'block', atom: true, draggable: true,
    addAttributes: () => ({ visibility: { default: 'public' }, assetId: { default: '' }, src: { default: '' }, alt: { default: '' }, caption: { default: '' }, align: { default: 'center' }, width: { default: null } }),
    parseHTML: () => [{ tag: 'figure[data-gw-image]' }], renderHTML: ({ node }) => ['figure', { 'data-gw-image': '', class: `journal-rich-text__image journal-rich-text__image--${node.attrs.align}` }, ['img', { src: node.attrs.src, alt: node.attrs.alt, width: node.attrs.width }], ['figcaption', {}, node.attrs.caption]] });
const Callout = Node.create({ name: 'gwCallout', group: 'block', content: 'block+', defining: true,
    addAttributes: () => ({ kind: { default: 'gm_note' }, visibility: { default: 'gm' }, title: { default: '' } }), parseHTML: () => [{ tag: 'aside[data-gw-callout]' }],
    renderHTML: ({ node, HTMLAttributes }) => ['aside', mergeAttributes(HTMLAttributes, { 'data-gw-callout': node.attrs.kind, class: 'journal-rich-text__callout' }), ['strong', { contenteditable: 'false' }, node.attrs.title || createTranslator().t(node.attrs.kind === 'secret' ? 'Secret' : 'GM note')], ['div', {}, 0]] });
const Visibility = Extension.create({ name: 'journalVisibility', addGlobalAttributes() { return [{ types: ['paragraph', 'heading', 'blockquote', 'bulletList', 'orderedList', 'listItem', 'horizontalRule'], attributes: { visibility: { default: 'public', renderHTML: () => ({}) } } }]; } });
const commands = [{ id: 'text', label: 'Text', node: { type: 'paragraph' } }, ...[1, 2, 3].map(level => ({ id: `h${level}`, label: `Heading ${level}`, node: { type: 'heading', attrs: { level } } })),
    { id: 'bullet', label: 'Bulleted list', node: { type: 'bulletList', content: [{ type: 'listItem', content: [{ type: 'paragraph' }] }] } },
    { id: 'ordered', label: 'Numbered list', node: { type: 'orderedList', content: [{ type: 'listItem', content: [{ type: 'paragraph' }] }] } },
    { id: 'quote', label: 'Quote', node: { type: 'blockquote', content: [{ type: 'paragraph' }] } }, { id: 'divider', label: 'Divider', node: { type: 'horizontalRule' } }, { id: 'image', label: 'Image', node: { type: 'gwImage' } }, { id: 'resource', label: 'Campaign resource' }];
export function richText(host, value, readonly, upload, label, onChange, options = {}) {
    const doc = host.ownerDocument, translator = createTranslator(), text = key => translator.t(key);
    const own = new AbortController(), signal = options.signal ? AbortSignal.any([own.signal, options.signal]) : own.signal;
    const tableId = options.campaignId || doc.getElementById('table-workspace')?.dataset.tableId || globalThis.document.getElementById('table-workspace')?.dataset.tableId;
    const api = options.api || globalThis.window.gravewright.forTable(tableId);
    let menu, menuEscape, selected = 0, items = [], choose, editor, closed = false;
    const resources = createJournalResourceLinks({ host, api, editor: () => editor, text, readonly, signal,
        ...(options.journalId ? { journalId: options.journalId } : {}), pageId: options.pageId, pagePersisted: options.pagePersisted,
        ...(options.presentationTicket ? { readJournal: async signal => {
            const response = await fetch(`/api/containers/${encodeURIComponent(tableId)}/journal-presentation/${encodeURIComponent(options.presentationTicket)}`, { signal, credentials: 'same-origin', cache: 'no-store' });
            if ([401, 403, 404].includes(response.status)) return null;
            if (!response.ok) throw Error('Could not load campaign resources.'); return response.json();
        } } : {}),
        report: failure => error(failure.message || 'Could not load campaign resources.') });
    const ResourceLink = Node.create({ name: resourceNodeName, inline: true, group: 'inline', atom: true, selectable: true,
        addAttributes: () => ({ reference: { default: null, renderHTML: () => ({}) } }),
        parseHTML: () => [{ tag: 'span[data-gw-resource-link]', getAttrs: element => {
            try { const raw = element.getAttribute('data-gw-resource-reference'); if (!raw || raw.length > 2048) return false;
                const reference = JSON.parse(raw);
                return reference && typeof reference === 'object' && (reference.unavailable === true && typeof reference.key === 'string' || typeof reference.kind === 'string' && typeof reference.id === 'string') ? { reference } : false;
            } catch { return false; }
        } }], renderHTML: ({ node }) => resourceHtml(resources.project(node.attrs.reference), text), addNodeView: () => resources.view });
    host.className = 'journal-rich-text' + (readonly ? ' journal-rich-text--read' : '');
    const surface = doc.createElement('div');
    surface.className = 'journal-rich-text__surface';
    host.append(surface);
    surface.addEventListener('click', followReference, { capture: true, signal });
    const insertReference = (ref, position) => resources.insert(ref, position);
    if (!readonly) {
        surface.addEventListener('dragover', event => {
            if (event.dataTransfer.types.includes(referenceMime)) event.preventDefault();
        }, { signal });
    }
    const input = doc.createElement('input');
    input.type = 'file';
    input.accept = 'image/png,image/jpeg,image/webp';
    input.className = 'journal-rich-text__file';
    host.append(input);
    const hide = () => { menuEscape?.(); menuEscape = undefined; menu?.remove(); menu = undefined; };
    const error = (message = 'Could not upload the image.') => { let p = host.querySelector('[role=alert]'); if (!p) {
        p = doc.createElement('p');
        p.setAttribute('role', 'alert');
        host.prepend(p);
    } p.textContent = text(message); };
    async function files(list) { if (readonly || closed || signal.aborted || !upload || !list)
        return; for (const file of [...list].filter(f => f.type.startsWith('image/'))) {
        try {
            const asset = await upload(file);
            if (!closed && !signal.aborted && editor.isEditable)
                editor.chain().focus().insertContent({ type: 'gwImage', attrs: { src: asset.src, assetId: asset.asset_id } }).run();
        }
        catch {
            if (!closed)
                error();
        }
    } }
    input.addEventListener('change', () => files(input.files), { signal });
    function pick(command, range) { const chain = editor.chain().focus().deleteRange(range); if (command.id === 'image') {
        chain.run();
        input.click();
    }
    else if (command.id === 'resource') { chain.run(); resources.choose(); }
    else if (command.id === 'text')
        chain.setParagraph().run();
    else if (command.id.startsWith('h'))
        chain.setHeading({ level: Number(command.id.slice(1)) }).run();
    else
        chain.insertContent(command.node).run(); hide(); }
    function paint() { if (!menu)
        return; menu.replaceChildren(); items.forEach((item, index) => { const b = doc.createElement('button'); b.type = 'button'; b.className = 'journal-rich-text__command'; b.setAttribute('role', 'option'); b.setAttribute('aria-selected', String(index === selected)); b.textContent = text(item.label); b.addEventListener('mousedown', e => { e.preventDefault(); choose(item); }, { signal }); menu.append(b); }); }
    editor = new Editor({ element: surface, editable: !readonly, content: value?.doc || emptyDoc().doc,
        extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), Link.configure({ openOnClick: readonly, HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' } }), Placeholder.configure({ placeholder: text('Type / to insert blocks or @ to insert references') }), Image, Callout, Visibility, ResourceLink,
            Extension.create({ name: 'journalSlash', addProseMirrorPlugins() { return [Suggestion({ editor: this.editor, char: '/', allowSpaces: false, items: ({ query }) => commands.filter(c => (c.id !== 'image' || upload) && `${text(c.label)} ${c.label} ${c.id}`.toLowerCase().includes(query.toLowerCase())), command: ({ range, props }) => pick(props, range), render: () => ({ onStart: p => { const rect = p.clientRect?.(); if (!rect)
                                return; hide(); items = p.items; choose = p.command; selected = 0; menu = doc.createElement('div'); menu.className = 'journal-rich-text__commands'; menu.setAttribute('role', 'listbox'); menu.setAttribute('aria-label', text('Insert block')); Object.assign(menu.style, { left: rect.left + 'px', top: Math.min(rect.bottom, doc.defaultView.innerHeight - 377) + 'px' }); doc.body.append(menu); menuEscape = registerEscapeClose(menu, hide); paint(); }, onUpdate: p => { items = p.items; choose = p.command; selected = 0; paint(); }, onKeyDown: ({ event }) => { if (!menu)
                                return false; if (event.key === 'Escape') {
                                hide();
                                return true;
                            } if (['ArrowUp', 'ArrowDown'].includes(event.key) && items.length) {
                                selected = (selected + (event.key === 'ArrowUp' ? -1 : 1) + items.length) % items.length;
                                paint();
                                return true;
                            } if (['Enter', 'Tab'].includes(event.key) && items[selected]) {
                                choose(items[selected]);
                                return true;
                            } return false; }, onExit: hide }) })]; } })],
        editorProps: { attributes: { role: 'textbox', 'aria-label': label || text('Page content'), 'aria-multiline': 'true' },
            handleTextInput: (view, from, to, typed) => referenceTextInput(view, from, to, typed, {
                isActive: () => !readonly && !closed && !signal.aborted && editor.isEditable,
                choose: range => resources.choose(range),
            }), handlePaste: (_, event) => { if (!readonly && event.clipboardData?.files.length) {
                void files(event.clipboardData.files);
                return true;
            } return false; }, handleDrop: (_, event) => {
                const ref = !readonly && readReference(event.dataTransfer);
                if (ref) {
                    event.preventDefault();
                    insertReference(ref, editor.view.posAtCoords({left: event.clientX, top: event.clientY})?.pos);
                    return true;
                }
                if (!readonly && event.dataTransfer?.files.length) {
                void files(event.dataTransfer.files);
                return true;
            } return false; } },
        onUpdate: ({ editor }) => onChange({ format: 'gw-journal-doc-v1', version: 1, doc: resources.serialize(editor.getJSON()) }), onBlur: hide });
    function destroy() { if (closed) return; closed = true; hide(); resources.destroy(); own.abort(); editor.destroy(); }
    if (signal.aborted) destroy(); else signal.addEventListener('abort', destroy, { once: true });
    return { destroy, editor };
}
