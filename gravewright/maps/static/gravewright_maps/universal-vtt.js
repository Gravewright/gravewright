import { mountModal } from '/static/gravewright_table/modal.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';

/** Interchange the visible map and native geometry; never imply a flattened image is an editable project. */
export function openUniversalVtt({ campaignId, sceneId, folderId, t, onImported }) {
    if (!document.querySelector('link[data-uvtt-css]')) {
        const link = document.createElement('link'); link.rel = 'stylesheet'; link.dataset.uvttCss = '';
        link.href = new URL('./universal-vtt.css', import.meta.url).href; document.head.append(link);
    }
    const abort = new AbortController(), { signal } = abort, http = new HttpClient(undefined, () => signal);
    const make = (tag, attrs = {}, text) => {
        const node = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const exporting = Boolean(sceneId);
    const modal = make('section', { class: 'table-form-modal universal-vtt', 'data-universal-vtt': '', 'aria-label': t(exporting ? 'Export Universal VTT' : 'Import Universal VTT') });
    const header = make('header'), title = make('strong', {}, t(exporting ? 'Export Universal VTT' : 'Import Universal VTT'));
    const close = make('button', { type: 'button', 'data-uvtt-close': '' }, t('Close'));
    close.addEventListener('click', () => { if (!busy || exporting) modal.close(); }, { signal }); header.append(title, close);
    const body = make('form', { class: 'universal-vtt__body' });
    body.append(make('p', {}, t('Universal VTT transfers a flattened map image, grid, walls, portals and lights. Builder layers, behaviors, effects, actors and audio are not transferred.')));
    const status = make('p', { role: 'status', 'data-uvtt-status': '' }), notes = make('ul', { 'data-uvtt-warnings': '' });
    const footer = make('footer'), action = make('button', { type: 'button', 'data-uvtt-submit': '' }, t(exporting ? 'Prepare export' : 'Import scene'));
    const name = make('input', { type: 'text', maxlength: '120', required: '', 'data-uvtt-name': '', translate: 'no' });
    const file = make('input', { type: 'file', accept: '.uvtt,.dd2vtt,.df2vtt,application/json', required: '', 'data-uvtt-file': '' });
    if (!exporting) {
        const fileLabel = make('label'), nameLabel = make('label');
        fileLabel.append(make('span', {}, t('Universal VTT file')), file); nameLabel.append(make('span', {}, t('Scene name')), name);
        body.append(fileLabel, nameLabel, make('p', { class: 'universal-vtt__hint' }, t('Import creates a new GM-only scene. The background image cannot be split back into Builder tiles or layers.')));
    }
    const download = make('a', { class: 'universal-vtt__download', 'data-uvtt-download': '', hidden: '' }, t('Download Universal VTT'));
    footer.append(action, download); body.append(status, notes); modal.append(header, body, footer);
    let busy = false, disposed = false, requestId = crypto.randomUUID(), url;
    const changed = () => { requestId = crypto.randomUUID(); status.textContent = ''; notes.replaceChildren(); };
    file.addEventListener('change', () => { changed(); if (!name.value && file.files[0]) name.value = file.files[0].name.replace(/\.[^.]+$/, '').slice(0, 120); }, { signal });
    name.addEventListener('input', changed, { signal });
    async function perform() {
        if (busy || !exporting && !body.reportValidity()) return;
        if (!exporting && file.files[0].size > 64 * 1024 * 1024) { status.textContent = t('The Universal VTT file exceeds the interchange size limit.'); return; }
        busy = true; action.disabled = true; close.disabled = !exporting; file.disabled = true; name.disabled = true; notes.replaceChildren();
        modal.setAttribute('aria-busy', 'true'); status.textContent = t(exporting ? 'Preparing Universal VTT export...' : 'Importing Universal VTT scene...');
        try {
            let result;
            if (exporting) result = await http.get(`/api/maps/${encodeURIComponent(sceneId)}/universal-vtt`, { signal, timeoutMs: null });
            else {
                const form = new FormData(); form.append('file', file.files[0]); form.append('name', name.value.trim()); form.append('request_id', requestId);
                if (folderId) form.append('folderId', folderId);
                result = await http.upload(`/api/containers/${encodeURIComponent(campaignId)}/universal-vtt/import`, form);
            }
            if (disposed) return;
            for (const warning of result.warnings || []) notes.append(make('li', {}, t(warning)));
            if (exporting) {
                if (url) URL.revokeObjectURL(url);
                url = URL.createObjectURL(new Blob([JSON.stringify(result.document)], { type: 'application/json' }));
                download.href = url; download.download = result.filename; download.hidden = false; action.hidden = true;
                status.textContent = t('Export ready. Review the format limitations before downloading.');
            } else {
                status.textContent = t('Scene imported. It is available in Scenes and has not been activated for players.');
                action.hidden = true; file.disabled = true; name.disabled = true; onImported?.(result);
            }
        } catch (error) {
            if (!disposed && error.name !== 'AbortError') status.textContent = t(error.message || 'Universal VTT interchange failed.');
        } finally {
            if (!disposed) { busy = false; action.disabled = false; close.disabled = false; modal.setAttribute('aria-busy', 'false'); if (!action.hidden) { file.disabled = false; name.disabled = false; } }
        }
    }
    action.addEventListener('click', () => void perform(), { signal });
    body.addEventListener('submit', event => { event.preventDefault(); void perform(); }, { signal });
    modal.addEventListener('close', () => { disposed = true; abort.abort(); if (url) URL.revokeObjectURL(url); }, { once: true });
    return mountModal(modal, { canClose: () => !busy || exporting, nested: true });
}
