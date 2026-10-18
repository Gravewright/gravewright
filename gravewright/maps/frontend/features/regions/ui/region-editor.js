import { openFormModal } from '/static/gravewright_table/form-modal.js';
import { text as t } from '../../../shared/config/i18n/text.js';
import { normalizeRegionFilters, regionFilterDispositions } from '../model/regions.js';

/** The server derives presence; the editor only saves authored region settings. */
export function openRegionEditor(zone, { save, tokens = [], campaignId, sceneId } = {}) {
    const filters = normalizeRegionFilters(zone.region.filters);
    const selected = { actorIds: new Set(filters.actorIds), tokenIds: new Set(filters.tokenIds), dispositions: new Set(filters.dispositions) };
    const fields = [
        { name: 'name', label: t('Region name'), value: zone.region.name, required: true },
        { name: 'enabled', label: t('Enabled'), type: 'checkbox', value: zone.enabled !== false },
    ];
    const geometry = zone.geometry;
    const dimensions = geometry.shape === 'rect' ? ['x', 'y', 'width', 'height'] : geometry.shape === 'circle' ? ['x', 'y', 'radius'] : [];
    const captions = { x: 'X', y: 'Y', width: 'Width', height: 'Height', radius: 'Radius' };
    for (const key of dimensions) fields.push({ name: key, label: t(captions[key]), type: 'number', value: geometry[key], required: true });
    const modal = openFormModal(t('Configure region'), fields, async form => {
        const patch = { region: { name: form.elements.name.value.trim() }, enabled: form.elements.enabled.checked };
        const currentFilters = {
            actorIds: [...selected.actorIds], tokenIds: [...selected.tokenIds], dispositions: [...selected.dispositions],
            visibility: form.elements.regionVisibility.value,
        };
        const changed = currentFilters.visibility !== filters.visibility || ['actorIds', 'tokenIds', 'dispositions'].some(key =>
            currentFilters[key].length !== filters[key].length || currentFilters[key].some(id => !filters[key].includes(id)));
        if (zone.region.filters !== undefined || changed) patch.region.filters = changed ? currentFilters : filters;
        if (dimensions.length) patch.geometry = { ...geometry, ...Object.fromEntries(dimensions.map(key => [key, Number(form.elements[key].value)])) };
        await save?.(patch);
    }, { key: 'scene-region-editor' });
    modal.dataset.regionEditor = zone.id;
    const name = modal.querySelector('[name=name]'); name.maxLength = 120;
    for (const key of dimensions) {
        const control = modal.querySelector(`[name=${key}]`); control.step = 'any';
        if (['width', 'height', 'radius'].includes(key)) control.min = '0.000001';
    }
    const status = document.createElement('p'); status.dataset.regionStatus = '';
    status.textContent = `${t(zone.region.state === 'occupied' ? 'Occupied' : 'Empty')} · ${t('Tokens inside: {0}', zone.region.count ?? 0)}`;
    const note = document.createElement('p'); note.textContent = t('Region occupancy is computed from token positions.');
    modal.querySelector('[data-fields]').prepend(status, note);
    const controller = new AbortController();
    modal.addEventListener('close', () => controller.abort(), { once: true });
    const details = document.createElement('details');
    details.className = 'region-editor__filters'; details.dataset.regionFilters = '';
    details.open = zone.region.filters !== undefined;
    const summary = document.createElement('summary'); summary.textContent = t('Presence filters');
    const hint = document.createElement('p'); hint.textContent = t('All selected criteria must match. Empty lists accept any token.');
    const visibilityLabel = document.createElement('label'), visibilityCaption = document.createElement('span');
    visibilityCaption.textContent = t('Visibility');
    const visibility = document.createElement('select'); visibility.name = 'regionVisibility'; visibility.dataset.regionFilterVisibility = '';
    for (const [value, label] of [['any', 'Any token'], ['visible', 'Visible tokens'], ['hidden', 'Hidden tokens']])
        visibility.add(new Option(t(label), value));
    visibility.value = filters.visibility;
    visibilityLabel.append(visibilityCaption, visibility);
    details.append(summary, hint, visibilityLabel);

    function choices(key, caption, rows, empty) {
        const field = document.createElement('fieldset'); field.dataset.regionFilter = key;
        const legend = document.createElement('legend'); legend.textContent = t(caption);
        const list = document.createElement('div'); list.className = 'region-editor__choices';
        field.append(legend, list); details.append(field);
        const render = values => {
            list.replaceChildren();
            const catalog = new Map(values.map(row => [row.id, row.name || row.id]));
            for (const id of selected[key]) if (!catalog.has(id)) catalog.set(id, t('Unavailable: {0}', id));
            if (!catalog.size) {
                const message = document.createElement('p'); message.textContent = t(empty); list.append(message);
            }
            const updateLimit = () => {
                if (key === 'dispositions') return;
                for (const input of list.querySelectorAll('input')) input.disabled = selected[key].size >= 64 && !input.checked;
            };
            for (const [id, name] of catalog) {
                const label = document.createElement('label'), input = document.createElement('input'), text = document.createElement('span');
                input.type = 'checkbox'; input.value = id; input.checked = selected[key].has(id);
                input.dataset.regionFilterValue = id;
                text.textContent = name; if (key !== 'dispositions') text.translate = false;
                input.addEventListener('change', () => {
                    input.checked ? selected[key].add(id) : selected[key].delete(id);
                    updateLimit();
                });
                label.append(input, text); list.append(label);
            }
            updateLimit();
        };
        render(rows);
        return { field, render };
    }
    const dispositions = { friendly: 'Friendly', neutral: 'Neutral', hostile: 'Hostile', unknown: 'Unknown' };
    choices('dispositions', 'Dispositions', regionFilterDispositions.map(id => ({ id, name: t(dispositions[id]) })), '');
    const actors = choices('actorIds', 'Actors', [], 'No actors available.');
    const tokenChoices = choices('tokenIds', 'Tokens', tokens, 'No tokens in this scene.');
    function loadCatalog(target, url, key, loadingText, errorText) {
        const loading = document.createElement('p'); loading.setAttribute('role', 'status'); loading.className = 'region-editor__catalog-status';
        const retry = document.createElement('button'); retry.type = 'button'; retry.textContent = t('Retry'); retry.hidden = true;
        target.field.append(loading, retry);
        const load = async () => {
            retry.disabled = true; loading.textContent = t(loadingText);
            try {
                const response = await fetch(url, { credentials: 'same-origin', signal: controller.signal });
                if (!response.ok) throw Error(errorText);
                const catalog = await response.json();
                if (!modal.isConnected || controller.signal.aborted) return;
                if (!Array.isArray(catalog[key])) throw Error(errorText);
                target.render(catalog[key]); loading.textContent = ''; retry.hidden = true;
            } catch {
                if (!modal.isConnected || controller.signal.aborted) return;
                loading.textContent = t(errorText); retry.hidden = false;
            } finally { if (!controller.signal.aborted) retry.disabled = false; }
        };
        retry.addEventListener('click', load);
        void load();
    }
    if (campaignId) {
        const base = `/api/containers/${encodeURIComponent(campaignId)}`;
        loadCatalog(actors, `${base}/actors`, 'actors', 'Loading actors...', 'Could not load actors.');
        if (sceneId) loadCatalog(tokenChoices, `${base}/maps/${encodeURIComponent(sceneId)}/tokens`, 'tokens', 'Loading tokens...', 'Could not load tokens.');
    }
    modal.querySelector('[data-fields]').append(details);
    return modal;
}
