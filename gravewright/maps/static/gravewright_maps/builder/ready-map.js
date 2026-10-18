import { mountModal } from '/static/gravewright_table/modal.js';
import { clone, objectKinds, readyMapGeometry, setBackgroundImage } from './model.js';

/** Import one map image through the campaign library and the normal project history. */
export function openReadyMapImport({ template, document, assets, limits, t, upload, apply, onClose }) {
    const modal = template.content.firstElementChild.cloneNode(true), form = modal.querySelector('form');
    const file = modal.querySelector('[data-builder-map-upload]'), existing = modal.querySelector('[data-builder-map-asset]');
    const preview = modal.querySelector('[data-builder-map-preview]'), issue = modal.querySelector('[role=alert]');
    const local = new AbortController(), { signal } = local;
    const empty = !objectKinds.some(kind => document[kind]?.length) && !document.backgroundImage;
    let working = false, closed = false, previewUrl, generation = 0, uploaded, geometryEdited = false;
    for (const key of ['columns', 'rows', 'cellSize']) {
        form.elements[key].value = document[key];
        form.elements[key].addEventListener('input', () => { geometryEdited = true; }, { signal });
    }
    for (const asset of assets) {
        const option = new Option(asset.name, asset.id); option.setAttribute('translate', 'no'); existing.add(option);
    }
    existing.value = document.backgroundImage?.assetId || '';
    function clearPreview() {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = undefined; preview.removeAttribute('src'); preview.hidden = true;
    }
    function suggest(asset) {
        if (!empty || geometryEdited || ['columns', 'rows', 'cellSize'].some(key => form.elements[key] === globalThis.document.activeElement)) return;
        const geometry = readyMapGeometry(asset, Number(form.elements.cellSize.value) || document.cellSize, limits);
        for (const key of ['columns', 'rows', 'cellSize']) form.elements[key].value = geometry[key];
    }
    function showExisting() {
        clearPreview();
        const asset = assets.find(row => row.id === existing.value);
        if (asset) { preview.src = asset.url; preview.hidden = false; suggest(asset); }
    }
    existing.addEventListener('change', () => {
        generation++; file.value = ''; uploaded = undefined; issue.hidden = true; showExisting();
    }, { signal });
    file.addEventListener('change', async () => {
        const current = ++generation;
        uploaded = undefined; existing.value = ''; issue.hidden = true; clearPreview();
        const image = file.files[0];
        if (!image) return;
        if (image.size > 25 * 1024 * 1024) {
            issue.textContent = t('Choose an image up to 25 MB.'); issue.hidden = false; return;
        }
        previewUrl = URL.createObjectURL(image); preview.src = previewUrl; preview.hidden = false;
        try {
            const bitmap = await createImageBitmap(image);
            try { if (!closed && current === generation) suggest(bitmap); }
            finally { bitmap.close(); }
        } catch {
            // The server also accepts TIFF, which some browsers cannot preview.
            if (!closed && current === generation) preview.hidden = true;
        }
    }, { signal });
    for (const selector of ['[data-builder-map-import-close]', '[data-builder-map-import-cancel]']) {
        modal.querySelector(selector).addEventListener('click', () => { if (!working) modal.close(); }, { signal });
    }
    modal.addEventListener('close', () => {
        closed = true; generation++; local.abort(); clearPreview(); onClose?.();
    }, { once: true });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (working || !form.reportValidity()) return;
        const image = file.files[0], geometry = Object.fromEntries(['columns', 'rows', 'cellSize'].map(key => [key, Number(form.elements[key].value)]));
        issue.hidden = true;
        try {
            if (!image && !existing.value) throw new Error('Choose a map image.');
            if (image?.size > 25 * 1024 * 1024) throw new Error('Choose an image up to 25 MB.');
            // Check dimensions and existing geometry before creating a library asset.
            setBackgroundImage(clone(document), existing.value || crypto.randomUUID(), geometry, limits);
        } catch (error) { issue.textContent = t(error.message); issue.hidden = false; return; }
        working = true;
        for (const control of modal.querySelectorAll('button,input,select')) control.disabled = true;
        try {
            if (image && !uploaded) uploaded = await upload(image);
            if (closed) return;
            await apply(uploaded || existing.value, geometry);
            if (!closed) { working = false; modal.close(); }
        } catch (error) {
            if (!closed && error.name !== 'AbortError') { issue.textContent = t(error.message); issue.hidden = false; }
        } finally {
            working = false;
            if (!closed) for (const control of modal.querySelectorAll('button,input,select')) control.disabled = false;
        }
    }, { signal });
    showExisting();
    return mountModal(modal, { canClose: () => !working });
}
