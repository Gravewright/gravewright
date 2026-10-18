/** Shared wall/door window. The caller owns persistence and window placement. */
import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { wallPresets, wallPreset, wallPayload } from './walls/model/walls.js';

export function createWallEditor(wall, { onSave, onClose, transactional = false, t = createTranslator().t } = {}) {
    const editor = document.getElementById('map-wall-editor').content.firstElementChild.cloneNode(true);
    const form = editor.querySelector('form'), fields = form.elements, abort = new AbortController();
    const { signal } = abort, data = wallPayload(wall), close = editor.querySelector('header button');
    const title = t(wall.kind === 'door' ? 'Configure door' : 'Configure wall');
    editor.dataset.id = wall.id; editor.setAttribute('aria-label', title); editor.querySelector('strong').textContent = title;
    for (const control of form.querySelectorAll('[aria-label]')) control.setAttribute('aria-label', t(control.getAttribute('aria-label')));
    for (const preset of wallPresets) fields.preset.append(new Option(t(preset.name), preset.id));
    fields.preset.value = wall.presentation && wall.presentation !== 'normal' ? wall.presentation : wallPreset(wall).id;
    for (const [key, value] of Object.entries(data.behavior)) fields[key].value = value;
    fields.finite.checked = data.vertical.bottom != null;
    fields.bottom.value = data.vertical.bottom ?? 0; fields.top.value = data.vertical.top ?? 3;
    fields.discovered.checked = Boolean(wall.discovered);
    fields.interactionEnabled.checked = wall.interactionEnabled !== false;
    for (const control of form.querySelectorAll('[data-player-interaction]')) control.hidden = wall.kind !== 'door';
    const cancel = editor.querySelector('[data-native-editor-cancel]'); cancel.hidden = !transactional;
    const preset = () => wallPresets.find(value => value.id === fields.preset.value) || wallPresets[0];
    function sync() {
        const finite = fields.finite.checked;
        for (const element of form.querySelectorAll('[data-finite]')) element.hidden = !finite;
        fields.bottom.disabled = fields.top.disabled = !finite;
        form.querySelector('[data-secret]').hidden = preset().presentation !== 'secret';
        fields.top.setCustomValidity(!finite || Number(fields.top.value) > Number(fields.bottom.value)
            ? '' : t('Upper height must be greater than lower height.'));
    }
    function setState({ busy = false, error = '' } = {}) {
        editor.querySelector('fieldset').disabled = busy;
        if (transactional) close.disabled = busy;
        const alert = editor.querySelector('[role=alert]'); alert.hidden = !error; alert.textContent = error;
    }
    fields.preset.addEventListener('change', () => {
        const value = preset();
        for (const [key, behavior] of Object.entries(value.behavior)) fields[key].value = behavior;
        fields.finite.checked = Boolean(value.vertical);
        fields.bottom.value = value.vertical?.bottom ?? 0; fields.top.value = value.vertical?.top ?? 3;
        sync();
    }, { signal });
    form.addEventListener('input', sync, { signal });
    form.addEventListener('change', sync, { signal });
    form.addEventListener('submit', event => {
        event.preventDefault(); sync();
        if (!form.reportValidity() || editor.querySelector('fieldset').disabled) return;
        const patch = { behavior: Object.fromEntries(['movement', 'vision', 'light', 'sound'].map(key => [key, fields[key].value])),
            presentation: preset().presentation, vertical: { bottom: fields.finite.checked ? Number(fields.bottom.value) : null,
                top: fields.finite.checked ? Number(fields.top.value) : null }, discovered: fields.discovered.checked };
        if (wall.kind === 'door' && ('interactionEnabled' in wall || !fields.interactionEnabled.checked)) patch.interactionEnabled = fields.interactionEnabled.checked;
        if (transactional) setState({ busy: true });
        try {
            Promise.resolve(onSave?.(patch)).catch(error => setState({ error: error.message || t('Could not save the change.') }))
                .finally(() => { if (transactional && editor.isConnected && !editor.querySelector('[role=alert]').textContent) setState(); });
        } catch (error) { setState({ error: error.message || t('Could not save the change.') }); }
    }, { signal });
    for (const button of [close, cancel]) button.addEventListener('click', () => onClose?.(), { signal });
    editor.addEventListener('keydown', event => {
        if (event.key === 'Escape') { event.stopPropagation(); onClose?.(); }
    }, { signal });
    editor.setState = setState;
    editor.dispose = () => abort.abort();
    sync(); return editor;
}
