// The original Tiptap editor, adapted from JournalRichText.vue without Vue.
import { Editor, Node, Extension, mergeAttributes, StarterKit, Link, Placeholder, Suggestion } from './vendor/editor.js';
export const emptyDoc = () => ({ format: 'gw-journal-doc-v1', version: 1, doc: { type: 'doc', content: [{ type: 'paragraph' }] } });
const Image = Node.create({ name: 'gwImage', group: 'block', atom: true, draggable: true,
    addAttributes: () => ({ visibility: { default: 'public' }, assetId: { default: '' }, src: { default: '' }, alt: { default: '' }, caption: { default: '' }, align: { default: 'center' }, width: { default: null } }),
    parseHTML: () => [{ tag: 'figure[data-gw-image]' }], renderHTML: ({ node }) => ['figure', { 'data-gw-image': '', class: `journal-rich-text__image journal-rich-text__image--${node.attrs.align}` }, ['img', { src: node.attrs.src, alt: node.attrs.alt, width: node.attrs.width }], ['figcaption', {}, node.attrs.caption]] });
const Callout = Node.create({ name: 'gwCallout', group: 'block', content: 'block+', defining: true,
    addAttributes: () => ({ kind: { default: 'gm_note' }, visibility: { default: 'gm' }, title: { default: '' } }), parseHTML: () => [{ tag: 'aside[data-gw-callout]' }],
    renderHTML: ({ node, HTMLAttributes }) => ['aside', mergeAttributes(HTMLAttributes, { 'data-gw-callout': node.attrs.kind, class: 'journal-rich-text__callout' }), ['strong', { contenteditable: 'false' }, node.attrs.title || (node.attrs.kind === 'secret' ? 'Secret' : 'GM note')], ['div', {}, 0]] });
const Visibility = Extension.create({ name: 'journalVisibility', addGlobalAttributes() { return [{ types: ['paragraph', 'heading', 'blockquote', 'bulletList', 'orderedList', 'listItem', 'horizontalRule'], attributes: { visibility: { default: 'public', renderHTML: () => ({}) } } }]; } });
const commands = [{ id: 'text', label: 'Text', node: { type: 'paragraph' } }, ...[1, 2, 3].map(level => ({ id: `h${level}`, label: `Heading ${level}`, node: { type: 'heading', attrs: { level } } })),
    { id: 'bullet', label: 'Bulleted list', node: { type: 'bulletList', content: [{ type: 'listItem', content: [{ type: 'paragraph' }] }] } },
    { id: 'ordered', label: 'Numbered list', node: { type: 'orderedList', content: [{ type: 'listItem', content: [{ type: 'paragraph' }] }] } },
    { id: 'quote', label: 'Quote', node: { type: 'blockquote', content: [{ type: 'paragraph' }] } }, { id: 'divider', label: 'Divider', node: { type: 'horizontalRule' } }, { id: 'image', label: 'Image', node: { type: 'gwImage' } }];
export function richText(host, value, readonly, upload, label, onChange) {
    const doc = host.ownerDocument;
    host.className = 'journal-rich-text' + (readonly ? ' journal-rich-text--read' : '');
    const surface = doc.createElement('div');
    surface.className = 'journal-rich-text__surface';
    host.append(surface);
    const input = doc.createElement('input');
    input.type = 'file';
    input.accept = 'image/png,image/jpeg,image/webp';
    input.className = 'journal-rich-text__file';
    host.append(input);
    let menu, selected = 0, items = [], choose, editor, closed = false;
    const hide = () => { menu?.remove(); menu = undefined; };
    const error = () => { let p = host.querySelector('[role=alert]'); if (!p) {
        p = doc.createElement('p');
        p.setAttribute('role', 'alert');
        host.prepend(p);
    } p.textContent = 'Could not upload the image.'; };
    async function files(list) { if (!upload || !list)
        return; for (const file of [...list].filter(f => f.type.startsWith('image/'))) {
        try {
            const asset = await upload(file);
            if (!closed)
                editor.chain().focus().insertContent({ type: 'gwImage', attrs: { src: asset.src, assetId: asset.asset_id } }).run();
        }
        catch {
            if (!closed)
                error();
        }
    } }
    input.addEventListener('change', () => files(input.files));
    function pick(command, range) { const chain = editor.chain().focus().deleteRange(range); if (command.id === 'image') {
        chain.run();
        input.click();
    }
    else if (command.id === 'text')
        chain.setParagraph().run();
    else if (command.id.startsWith('h'))
        chain.setHeading({ level: Number(command.id.slice(1)) }).run();
    else
        chain.insertContent(command.node).run(); hide(); }
    function paint() { if (!menu)
        return; menu.replaceChildren(); items.forEach((item, index) => { const b = doc.createElement('button'); b.type = 'button'; b.className = 'journal-rich-text__command'; b.setAttribute('role', 'option'); b.setAttribute('aria-selected', String(index === selected)); b.textContent = item.label; b.addEventListener('mousedown', e => { e.preventDefault(); choose(item); }); menu.append(b); }); }
    editor = new Editor({ element: surface, editable: !readonly, content: value?.doc || emptyDoc().doc,
        extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), Link.configure({ openOnClick: readonly, HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' } }), Placeholder.configure({ placeholder: 'Type / to insert blocks' }), Image, Callout, Visibility,
            Extension.create({ name: 'journalSlash', addProseMirrorPlugins() { return [Suggestion({ editor: this.editor, char: '/', allowSpaces: false, items: ({ query }) => commands.filter(c => (c.id !== 'image' || upload) && `${c.label} ${c.id}`.toLowerCase().includes(query.toLowerCase())), command: ({ range, props }) => pick(props, range), render: () => ({ onStart: p => { const rect = p.clientRect?.(); if (!rect)
                                return; hide(); items = p.items; choose = p.command; selected = 0; menu = doc.createElement('div'); menu.className = 'journal-rich-text__commands'; menu.setAttribute('role', 'listbox'); menu.setAttribute('aria-label', 'Insert block'); Object.assign(menu.style, { left: rect.left + 'px', top: Math.min(rect.bottom, doc.defaultView.innerHeight - 377) + 'px' }); doc.body.append(menu); paint(); }, onUpdate: p => { items = p.items; choose = p.command; selected = 0; paint(); }, onKeyDown: ({ event }) => { if (!menu)
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
        editorProps: { attributes: { role: 'textbox', 'aria-label': label || 'Page content', 'aria-multiline': 'true' }, handlePaste: (_, event) => { if (!readonly && event.clipboardData?.files.length) {
                void files(event.clipboardData.files);
                return true;
            } return false; }, handleDrop: (_, event) => { if (!readonly && event.dataTransfer?.files.length) {
                void files(event.dataTransfer.files);
                return true;
            } return false; } },
        onUpdate: ({ editor }) => onChange({ format: 'gw-journal-doc-v1', version: 1, doc: editor.getJSON() }), onBlur: hide });
    return { destroy() { closed = true; hide(); editor.destroy(); }, editor };
}
