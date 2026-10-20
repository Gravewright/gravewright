/** Layer list, active paint layer and object-selection controls. */
import { objectKinds } from './model.js';
import { layerContents, layerSummaries, mergeLayerDown, moveSelectionToLayer, reorderLayer, duplicateLayer } from './layer-model.js';

export function createLayerController({ root, state, t, signal, selection, library, isBusy,
    cancelDrawing, commit, rememberDraft, renderCanvas, renderProperties, renderSelection,
    applyPreviewControls, setSidebarTab, setTool, notify }) {
    const $ = selector => root.querySelector(selector);
    const { assetById } = library;
    const roleForKind = kind => kind === 'decorations' ? 'decoration' : kind.slice(0, -1);
    let layerEvents, draggedLayer;
    function dispose() { layerEvents?.abort(); draggedLayer = null; }
    signal.addEventListener('abort', dispose, { once: true });
    function node(tag, attrs = {}, text) {
        const element = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'class') element.className = value;
            else element.setAttribute(key, value);
        }
        if (text !== undefined) element.textContent = text;
        return element;
    }
    function svg(tag, attrs = {}) {
        const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [key, value] of Object.entries(attrs)) if (value !== undefined) element.setAttribute(key, value);
        return element;
    }
    function activeLayer(id) {
        if (isBusy() || state.preview || !state.document.layers.some(layer => layer.id === id)) return;
        cancelDrawing(); state.activeLayer = id;
        if (state.soloLayer) state.soloLayer = id;
        selection.set(state.selections); rememberDraft();
        renderCanvas(); renderLayers(); renderProperties();
    }
    function requestFirstLayer() {
        if (isBusy() || state.preview) return;
        setSidebarTab('layers', true);
        $('[data-builder-layer-name]').focus({ preventScroll: true });
    }
    function updateLayerControls() {
        if (!state.document.layers.some(layer => layer.id === state.activeLayer)) state.activeLayer = state.document.layers[0]?.id || null;
        if (state.soloLayer && !state.document.layers.some(layer => layer.id === state.soloLayer)) state.soloLayer = null;
        const summaries = layerSummaries(state.document), current = summaries.find(layer => layer.id === state.activeLayer);
        const select = $('[data-builder-active-layer-select]');
        select.value = state.activeLayer || '';
        select.disabled = isBusy() || state.preview || !current;
        $('[data-builder-active-layer-status]').textContent = current
            ? t(!current.visible ? 'Hidden layer' : current.locked ? 'Locked layer' : '{count} objects', { count: current.count }) : t('No active layer');
        $('[data-builder-layer-total]').textContent = String(summaries.length);
        $('[data-builder-layer-summary]').textContent = current ? t('Painting on: {name}', { name: current.name }) : t('Create a layer to start building your map.');
        $('[data-builder-layers-empty]').hidden = Boolean(summaries.length);
        $('[data-builder-create-first-layer]').hidden = Boolean(summaries.length) || state.preview;
        $('[data-builder-layer-add]').disabled = isBusy() || state.preview || summaries.length >= 32 || !$('[data-builder-layer-name]').value.trim();
        for (const control of root.querySelectorAll('[data-builder-layers-show-all], [data-builder-layers-unlock-all]')) control.disabled = isBusy() || state.preview || !summaries.length;
        const count = objectKinds.reduce((total, kind) => total + (state.document[kind]?.length || 0), 0);
        for (const layer of summaries) {
            const row = [...$('[data-builder-layer-list]').children].find(element => element.dataset.builderProjectLayer === layer.id);
            if (!row) continue;
            row.dataset.active = String(layer.id === state.activeLayer);
            row.dataset.locked = String(layer.locked); row.dataset.visible = String(layer.visible);
            const active = row.querySelector('[data-builder-layer-active]');
            active.setAttribute('aria-pressed', String(layer.id === state.activeLayer));
            active.textContent = layer.id === state.activeLayer ? '\u25cf' : '\u25cb';
            row.querySelector('[data-builder-layer-active-badge]').hidden = layer.id !== state.activeLayer;
            row.querySelector('[data-builder-layer-count-for]').textContent = t('{count} objects', { count: layer.count });
            const transfer = row.querySelector('[data-builder-layer-transfer]');
            transfer.disabled = isBusy() || state.preview || !layer.visible || layer.locked || !state.selections.some(ref => selection.item(ref)?.layerId !== layer.id);
            row.querySelector('[data-builder-layer-select]').disabled = isBusy() || state.preview || !layer.visible || layer.locked || !layer.count;
            row.querySelector('[data-builder-layer-merge]').disabled = isBusy() || state.preview || !layer.canMergeDown;
            row.querySelector('[data-builder-layer-remove]').disabled = isBusy() || state.preview || layer.count > 0 || layer.locked;
            row.querySelector('[data-builder-layer-copy]').disabled = isBusy() || state.preview || layer.locked || summaries.length >= 32 || count + layer.count > (state.limits.maxObjects || 2000);
            row.querySelector('[data-builder-layer-drag]').draggable = !isBusy() && !state.preview;
            for (const button of row.querySelectorAll('[data-builder-layer-object]')) {
                const ref = { kind: button.dataset.builderLayerObjectKind, id: button.dataset.builderLayerObject };
                button.disabled = isBusy() || state.preview || !layer.visible || layer.locked || Boolean(state.soloLayer && state.soloLayer !== layer.id);
                button.setAttribute('aria-pressed', String(state.selections.some(value => value.kind === ref.kind && value.id === ref.id)));
            }
        }
    }
    function renderLayers() {
        const target = $('[data-builder-layer-list]'); if (!target) return;
        layerEvents?.abort(); layerEvents = new AbortController();
        const listen = { signal: layerEvents.signal };
        target.replaceChildren();
        if (!state.document.layers.some(layer => layer.id === state.activeLayer)) state.activeLayer = state.document.layers[0]?.id || null;
        const activeSelect = $('[data-builder-active-layer-select]');
        activeSelect.replaceChildren(...state.document.layers.slice().reverse().map(layer => new Option(layer.name, layer.id)));
        if (!state.document.layers.length) activeSelect.append(new Option(t('No active layer'), ''));
        const refresh = (id, attribute) => {
            renderCanvas(); renderLayers(); renderProperties();
            if (id && attribute) root.querySelector(`[${attribute}="${id}"]`)?.focus({ preventScroll: true });
        };
        for (const layer of layerSummaries(state.document).reverse()) {
            const row = node('div', { class: 'map-builder__project-layer', 'data-builder-project-layer': layer.id, role: 'listitem' });
            const main = node('div', { class: 'map-builder__layer-main' });
            const drag = node('button', { type: 'button', class: 'map-builder__layer-drag',
                'data-builder-layer-drag': layer.id, draggable: 'true', title: t('Drag to reorder layer'), 'aria-label': t('Drag to reorder layer') }, '\u283f');
            drag.addEventListener('dragstart', event => {
                if (isBusy() || state.preview) { event.preventDefault(); return; }
                cancelDrawing(); draggedLayer = layer.id;
                event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('text/plain', layer.id);
                row.dataset.dragging = 'true';
            }, listen);
            const clearDrop = () => {
                for (const element of target.children) { delete element.dataset.dropTarget; delete element.dataset.dragging; }
                draggedLayer = null;
            };
            drag.addEventListener('dragend', clearDrop, listen);
            row.addEventListener('dragover', event => {
                if (!draggedLayer || isBusy() || state.preview || draggedLayer === layer.id) return;
                event.preventDefault(); event.dataTransfer.dropEffect = 'move';
                for (const element of target.children) delete element.dataset.dropTarget;
                row.dataset.dropTarget = event.clientY < row.getBoundingClientRect().top + row.offsetHeight / 2 ? 'before' : 'after';
            }, listen);
            row.addEventListener('dragleave', event => { if (!row.contains(event.relatedTarget)) delete row.dataset.dropTarget; }, listen);
            row.addEventListener('drop', event => {
                if (!draggedLayer || isBusy() || state.preview) return;
                event.preventDefault();
                const sourceId = draggedLayer, side = row.dataset.dropTarget;
                const remaining = state.document.layers.filter(value => value.id !== sourceId);
                const index = remaining.findIndex(value => value.id === layer.id);
                clearDrop();
                if (index < 0 || !side) return;
                cancelDrawing();
                if (!reorderLayer(state.document, sourceId, index + (side === 'before' ? 1 : 0))) return;
                commit(); refresh(sourceId, 'data-builder-layer-drag');
            }, listen);
            const active = node('button', { type: 'button', 'data-builder-layer-active': layer.id, 'aria-pressed': String(state.activeLayer === layer.id),
                'aria-label': t('Use this layer'), title: t('Use this layer') }, state.activeLayer === layer.id ? '\u25cf' : '\u25cb');
            active.addEventListener('click', () => { activeLayer(layer.id); root.querySelector(`[data-builder-layer-active="${layer.id}"]`)?.focus({ preventScroll: true }); }, listen);
            const name = node('input', { type: 'text', maxlength: 80, value: layer.name, 'data-builder-layer-title': layer.id,
                'aria-label': t('Layer name'), translate: 'no' });
            name.addEventListener('change', () => {
                if (isBusy() || state.preview || !name.value.trim()) { name.value = layer.name; return; }
                const current = state.document.layers.find(item => item.id === layer.id);
                if (!current || current.name === name.value.trim()) return;
                cancelDrawing(); current.name = name.value.trim(); commit(); refresh(layer.id, 'data-builder-layer-title');
            }, listen);
            main.append(drag, active, name); row.append(main);
            const meta = node('div', { class: 'map-builder__layer-meta' });
            meta.append(node('span', { 'data-builder-layer-count-for': layer.id }, t('{count} objects', { count: layer.count })));
            const badge = node('span', { class: 'map-builder__layer-badge', 'data-builder-layer-active-badge': layer.id }, t('Active layer'));
            badge.hidden = state.activeLayer !== layer.id; meta.append(badge);
            if (layer.locked) meta.append(node('span', {}, t('Locked layer')));
            if (!layer.visible) meta.append(node('span', {}, t('Hidden layer')));
            if (state.soloLayer === layer.id) meta.append(node('span', { class: 'map-builder__layer-badge' }, t('Isolated')));
            row.append(meta);
            const actions = node('div', { class: 'map-builder__layer-actions' });
            for (const [key, label] of [['visible', 'Show layer'], ['locked', 'Lock layer']]) {
                const wrapper = node('label', { title: t(label) });
                const input = node('input', { type: 'checkbox', ['data-builder-layer-' + key]: layer.id, 'aria-label': t(label) });
                input.checked = layer[key]; wrapper.append(input, node('span', {}, t(key === 'visible' ? 'Visible' : 'Lock layer')));
                input.addEventListener('change', () => {
                    if (isBusy() || state.preview) return;
                    const value = input.checked; cancelDrawing();
                    const current = state.document.layers.find(item => item.id === layer.id); if (!current) return;
                    current[key] = value;
                    if (key === 'visible' && !value && state.soloLayer === layer.id) state.soloLayer = null;
                    selection.set(state.selections); commit(); refresh(layer.id, 'data-builder-layer-' + key);
                }, listen); actions.append(wrapper);
            }
            const action = (attribute, label, callback, glyph = label) => {
                const button = node('button', { type: 'button', [attribute]: layer.id, 'aria-label': t(label), title: t(label) }, t(glyph));
                button.addEventListener('click', () => { if (!isBusy() && !state.preview) callback(); }, listen);
                actions.append(button); return button;
            };
            const isolate = action('data-builder-layer-solo', 'Isolate layer', () => {
                cancelDrawing(); state.soloLayer = state.soloLayer === layer.id ? null : layer.id;
                state.activeLayer = layer.id; selection.set(state.selections); rememberDraft(); refresh(layer.id, 'data-builder-layer-solo');
            }, 'Solo');
            isolate.setAttribute('aria-pressed', String(state.soloLayer === layer.id)); isolate.disabled = !layer.visible;
            action('data-builder-layer-select', 'Select layer objects', () => {
                cancelDrawing(); selection.set(layerContents(state.document, layer.id, { editable: true }));
                renderSelection(); renderProperties(); updateLayerControls();
            }, 'Select');
            action('data-builder-layer-transfer', 'Move selection to layer', () => {
                cancelDrawing(); const refs = [...selection.refs()];
                if (!moveSelectionToLayer(state.document, refs, layer.id)) return;
                state.activeLayer = layer.id; if (state.soloLayer) state.soloLayer = layer.id;
                selection.set(refs); commit(); refresh(layer.id, 'data-builder-layer-transfer');
            }, 'Move here');
            for (const [delta, label, glyph] of [[1, 'Move layer up', '\u2191'], [-1, 'Move layer down', '\u2193']]) {
                const button = action('data-builder-layer-order', label, () => {
                    cancelDrawing(); const index = state.document.layers.findIndex(item => item.id === layer.id);
                    if (!reorderLayer(state.document, layer.id, index + delta)) return;
                    commit(); refresh(layer.id, 'data-builder-layer-active');
                }, glyph);
                button.dataset.builderLayerMove = String(delta);
                button.disabled = layer.index + delta < 0 || layer.index + delta >= state.document.layers.length;
            }
            action('data-builder-layer-merge', 'Merge with layer below', () => {
                cancelDrawing(); const merged = mergeLayerDown(state.document, layer.id); if (!merged) return;
                state.activeLayer = merged.layerId;
                if (state.soloLayer) state.soloLayer = merged.layerId;
                selection.set(merged.moved); commit(); refresh(merged.layerId, 'data-builder-layer-active');
            }, 'Merge down');
            action('data-builder-layer-copy', 'Duplicate layer', () => {
                cancelDrawing();
                const copied = duplicateLayer(state.document, layer.id, t('{name} copy', { name: layer.name }).slice(0, 80));
                if (!copied) { notify(t('The layer cannot be duplicated here. Keep its contents inside the map and avoid overlapping doors.'), [], 'error'); return; }
                state.activeLayer = copied.layerId; if (state.soloLayer) state.soloLayer = copied.layerId;
                state.expandedLayers.push(copied.layerId);
                selection.set(copied.refs); commit(); refresh(copied.layerId, 'data-builder-layer-active');
            }, 'Duplicate');
            action('data-builder-layer-remove', 'Delete empty layer', () => {
                cancelDrawing(); const index = state.document.layers.findIndex(item => item.id === layer.id);
                if (index < 0 || layerContents(state.document, layer.id).length || layer.locked) return;
                state.document.layers.splice(index, 1); state.expandedLayers = state.expandedLayers.filter(id => id !== layer.id);
                commit(); refresh();
            }, '\u00d7');
            row.append(actions);
            const details = node('details', { class: 'map-builder__layer-contents', 'data-builder-layer-contents': layer.id });
            const summary = node('summary'), caret = svg('svg', { viewBox: '0 0 16 16', 'aria-hidden': 'true' });
            caret.append(svg('path', { d: 'M6 3.5 10.5 8 6 12.5', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5 }));
            summary.append(caret, node('span', {}, t('Layer contents'))); details.append(summary);
            const contents = node('div', { class: 'map-builder__layer-objects' }); details.append(contents);
            let rendered = false;
            const renderContents = () => {
                if (rendered || !details.open) return; rendered = true;
                const refs = layerContents(state.document, layer.id);
                if (!refs.length) { contents.append(node('p', { class: 'map-builder__hint' }, t('Layer is empty.'))); return; }
                const icons = new Map();
                for (const ref of refs.slice().reverse()) {
                    const item = selection.item(ref); if (!item) continue;
                    const asset = assetById(item.assetId);
                    const label = selection.label(ref.kind, item);
                    const button = node('button', { type: 'button', class: 'map-builder__layer-object',
                        'data-builder-layer-object': ref.id, 'data-builder-layer-object-kind': ref.kind,
                        title: label, 'aria-label': t('Select {name}', { name: label }), 'aria-pressed': 'false' });
                    if (asset) button.append(node('img', { src: asset.url, alt: '', loading: 'lazy', draggable: 'false' }));
                    else {
                        if (!icons.has(ref.kind)) icons.set(ref.kind, $(`[data-builder-tool=${roleForKind(ref.kind)}] svg`));
                        const icon = icons.get(ref.kind)?.cloneNode(true); if (icon) { icon.setAttribute('aria-hidden', 'true'); button.append(icon); }
                    }
                    button.append(node('span', { translate: item.name || asset || item.empty || ref.kind === 'regions' ? 'no' : 'yes' }, label));
                    button.addEventListener('click', event => {
                        if (isBusy() || state.preview || !selection.editable(ref)) return;
                        cancelDrawing(); state.activeLayer = layer.id; setTool('select');
                        const previous = selection.refs(), included = previous.some(value => value.kind === ref.kind && value.id === ref.id);
                        selection.set(event.shiftKey ? included ? previous.filter(value => value.kind !== ref.kind || value.id !== ref.id) : [...previous, ref] : [ref]);
                        renderSelection(); renderProperties(); updateLayerControls(); rememberDraft();
                    }, listen); contents.append(button);
                }
            };
            details.open = state.expandedLayers.includes(layer.id); renderContents();
            details.addEventListener('toggle', () => {
                state.expandedLayers = state.expandedLayers.filter(id => id !== layer.id);
                if (details.open) state.expandedLayers.push(layer.id);
                renderContents(); updateLayerControls(); rememberDraft();
            }, listen);
            row.append(details); target.append(row);
        }
        updateLayerControls(); applyPreviewControls();
    }
    return { activeLayer, requestFirstLayer, updateLayerControls, renderLayers, dispose };
}
