import { normalizeRegionFilters, regionFilterDispositions, regionFilterVisibility } from '../region-filters.js';

/** Edit an authored filter draft; the owner supplies catalogs and persistence. */
export function createRegionFilterControls({ filters, t, signal, linked, loadCatalog, onChange, onReady }) {
    let current = normalizeRegionFilters(filters);
    const make = (tag, attributes = {}, text) => {
        const element = document.createElement(tag);
        for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
        if (text !== undefined) element.textContent = text;
        return element;
    };
    const listen = (element, event, callback) => element.addEventListener(event, callback, { signal });
    const details = make('details', { class: 'map-builder__region-filters', 'data-builder-region-filters': '' });
    details.open = filters !== undefined;
    details.append(make('summary', {}, t('Presence filters')),
        make('p', { class: 'map-builder__hint' }, t('All selected criteria must match. Empty lists accept any token.')));
    const visibilityLabel = make('label', {}, t('Visibility'));
    const visibility = make('select', { 'data-builder-region-filter': 'visibility' });
    const visibilityNames = { any: 'Any token', visible: 'Visible tokens', hidden: 'Hidden tokens' };
    for (const value of regionFilterVisibility) visibility.append(new Option(t(visibilityNames[value]), value));
    visibility.value = current.visibility; visibilityLabel.append(visibility); details.append(visibilityLabel);
    const publish = (key, value) => {
        const next = normalizeRegionFilters({ ...current, [key]: value });
        onChange(next); current = next;
    };
    listen(visibility, 'change', () => publish('visibility', visibility.value));
    const dispositionLabel = make('label', {}, t('Dispositions'));
    const dispositions = make('select', { multiple: '', size: '4', 'data-builder-region-filter': 'dispositions', 'aria-label': t('Dispositions') });
    const dispositionNames = { friendly: 'Friendly', neutral: 'Neutral', hostile: 'Hostile', unknown: 'Unknown' };
    for (const value of regionFilterDispositions) {
        const option = new Option(t(dispositionNames[value]), value); option.selected = current.dispositions.includes(value); dispositions.append(option);
    }
    listen(dispositions, 'change', () => publish('dispositions', [...dispositions.selectedOptions].map(option => option.value)));
    dispositionLabel.append(dispositions); details.append(dispositionLabel);
    const choices = make('div', { class: 'map-builder__filter-choices' });
    const status = make('p', { class: 'map-builder__hint', role: 'status' }, t('Loading actors...'));
    const retry = make('button', { type: 'button', 'data-builder-filter-retry': '', hidden: '' }, t('Retry'));
    details.append(choices, status, retry);
    if (!linked) details.append(make('p', { class: 'map-builder__hint' }, t('Generate a scene to choose individual tokens. Actor filters are available now.')));
    const renderList = (key, rows, label) => {
        const wrapper = make('label', {}, t(label));
        const select = make('select', { multiple: '', size: '4', translate: 'no', 'data-builder-region-filter': key, 'aria-label': t(label) });
        const byId = new Map(rows.map(row => [row.id, row]));
        for (const id of current[key]) if (!byId.has(id)) byId.set(id, { id, name: t('Unavailable: {0}', { 0: id }) });
        for (const row of byId.values()) {
            const option = new Option(row.name || row.id, row.id); option.selected = current[key].includes(row.id); select.append(option);
        }
        if (!byId.size) select.dataset.builderFilterDisabled = 'true';
        select.disabled = !byId.size;
        listen(select, 'change', () => {
            const ids = [...select.selectedOptions].map(option => option.value);
            select.setCustomValidity(ids.length <= 64 ? '' : t('Select no more than 64 actors or tokens.'));
            if (select.reportValidity()) publish(key, ids);
        });
        wrapper.append(select);
        if (!byId.size) wrapper.append(make('span', { class: 'map-builder__hint' }, t(key === 'actorIds' ? 'No actors available.' : 'No tokens in this scene.')));
        return wrapper;
    };
    async function load(refresh = false) {
        status.hidden = false; status.textContent = t('Loading actors...'); retry.hidden = true;
        try {
            const catalog = await loadCatalog(refresh);
            if (!details.isConnected || signal.aborted) return;
            choices.replaceChildren(renderList('actorIds', catalog.actors, 'Actors'), renderList('tokenIds', catalog.tokens, 'Tokens'));
            status.hidden = true; onReady?.();
        } catch (error) {
            if (signal.aborted || !details.isConnected) return;
            status.textContent = `${t('Could not load region filter choices.')}: ${error.message}`; retry.hidden = false; onReady?.();
        }
    }
    listen(retry, 'click', () => void load(true));
    queueMicrotask(() => void load());
    return details;
}
