/** Selection properties, geometry guards and Smart Object configuration controls. */
import { clone, doorFits, fitsBounds, length, removeObject, setDynamicSurface, updateTorchGeometry, documentBounds } from './model.js';
import { attachTorch, torchOwner, torchComponentState, torchSourcePoint } from './torch-model.js';
import { configurePressurePlate, normalizeRegionFilters } from './region-model.js';
import { createRegionFilterControls } from './region-filter-ui.js';
import { isNativeKind, renderNativeProperties } from './native-controls.js';
import { moveSelectionToLayer } from './layer-model.js';
import { sameDocument } from './asset-removal.js';
import { interactiveObjectPresets, openInteractiveObjectCatalog } from './interactive-presets.js';

export function createInspectorController({ root, state, t, signal: parentSignal, toolHints, selection, library,
    isBusy, isDisposed, commit, renderCanvas, renderLayers, renderSelection, applyPreviewControls,
    chooseQuickTool, deleteSelection, openNativeEditor, openBehavior, loadFilterCatalog,
    setSidebarTab, pickOnMap, createTorchComponent, detachTorch, notify, onModal, onOptions }) {
    const $ = selector => root.querySelector(selector);
    const viewport = $('[data-builder-viewport]');
    const { assetById, assetName, renderMaterials } = library;
    const kindName = kind => ({ floors: 'Floor', walls: 'Wall', doors: 'Door', decorations: 'Decorative object',
        lights: 'Light', particles: 'Particles', shaders: 'Shader', regions: 'Region' })[kind];
    const roleForKind = kind => kind === 'decorations' ? 'decoration' : kind.slice(0, -1);
    const isSmartDecoration = item => Boolean(item?.lever || item?.torch);
    const hasNativeEditor = kind => isNativeKind(kind) || kind === 'walls' || kind === 'doors';
    let openingObjectCatalog = false;
    let propertyModal, panelAbort, modalFieldsAbort;
    const sections = { properties: 'Properties', appearance: 'Appearance', behavior: 'Behavior',
        components: 'Torch components', region: 'Region' };
    function fieldSignal() {
        const abort = new AbortController();
        if (parentSignal?.aborted) abort.abort();
        else parentSignal?.addEventListener('abort', () => abort.abort(), { signal: abort.signal, once: true });
        return abort;
    }
    function node(tag, attrs = {}, text) {
        const element = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'class') element.className = value;
            else element.setAttribute(key, value);
        }
        if (text !== undefined) element.textContent = text;
        return element;
    }
    function renderProperties() {
        panelAbort?.abort(); panelAbort = fieldSignal();
        renderPropertyFields($('[data-builder-properties]'), { signal: panelAbort.signal });
        if (!propertyModal) return;
        if (!selection.item(propertyModal.target)) { propertyModal.modal.close(true); return; }
        modalFieldsAbort?.abort(); modalFieldsAbort = fieldSignal();
        renderPropertyFields(propertyModal.body, { target: propertyModal.target, section: propertyModal.section,
            signal: modalFieldsAbort.signal });
    }
    function renderPropertyFields(container, { target, section, signal }) {
        container.replaceChildren();
        const refs = target ? [target] : selection.refs();
        const item = target ? selection.item(target) : selection.current();
        const currentTarget = target || state.selection;
        if (!target) renderMaterials();
        const selectionLabel = $('[data-builder-selection-label]');
        if (!target && selectionLabel) {
            selectionLabel.textContent = refs.length > 1 ? t('{count} selected', { count: refs.length })
                : item ? selection.label(state.selection.kind, item) : t(toolHints[state.tool]);
        }
        const materials = $('[data-builder-materials]'); if (!target && materials) materials.hidden = !item || item.empty || refs.length > 1 || isNativeKind(state.selection.kind) || state.selection.kind === 'regions' || item.brush?.operation === 'erase';
        container.dataset.empty = String(!item);
        if (!item) {
            container.append($('[data-builder-quick-tool=select] svg').cloneNode(true), node('strong', {}, t('Nothing selected')),
                node('p', { class: 'map-builder__hint' }, t(toolHints.select)));
            const choose = node('button', { type: 'button', 'data-builder-select-on-map': '' }, t('Select on map'));
            choose.addEventListener('click', () => chooseQuickTool('select'), { signal }); container.append(choose);
            applyPreviewControls(); return;
        }
        const layerLabel = node('label', {}, t('Layer')), layerSelect = node('select', { 'data-builder-property': 'layerId' });
        const sourceLayers = new Set(refs.map(ref => selection.item(ref).layerId));
        if (sourceLayers.size > 1) layerSelect.append(new Option(t('Multiple layers'), ''));
        for (const layer of state.document.layers) {
            const option = new Option(layer.name, layer.id); option.disabled = !layer.visible || layer.locked; layerSelect.append(option);
        }
        layerSelect.value = sourceLayers.size === 1 ? item.layerId : '';
        layerLabel.append(layerSelect); container.append(layerLabel);
        layerSelect.addEventListener('change', () => {
            if (isBusy() || state.preview || !moveSelectionToLayer(state.document, refs, layerSelect.value)) return;
            if (state.soloLayer) state.soloLayer = layerSelect.value;
            selection.set(refs); commit(); renderCanvas(); renderLayers(); renderProperties();
        }, { signal });
        if (refs.length > 1) {
            container.prepend(node('strong', { 'data-builder-selected-count': String(refs.length) }, t('{count} selected', { count: refs.length })));
            const remove = node('button', { type: 'button', 'data-builder-delete': '' }, t('Delete selected objects'));
            remove.addEventListener('click', deleteSelection, { signal }); container.append(remove); applyPreviewControls(); return;
        }
        const { kind } = currentTarget;
        container.prepend(node('strong', {}, t(item.empty ? 'Empty Object' : item.torch ? 'Torch' : kindName(kind))));
        if (!target && onOptions) {
            const options = node('button', { type: 'button', 'data-builder-object-options': '' }, t('Object options'));
            options.addEventListener('click', () => onOptions({ ...currentTarget }, options), { signal });
            container.insertBefore(options, layerLabel);
        }
        const nameLabel = node('label', {}, t(item.empty ? 'Object name' : kind === 'regions' ? 'Region name' : 'Element name'));
        const nameInput = node('input', { type: 'text', maxlength: '120', autocomplete: 'off',
            'data-builder-property': kind === 'regions' ? 'regionName' : 'name', 'data-builder-selection-name': '', translate: 'no' });
        nameInput.required = item.empty === true || ['regions', 'shaders'].includes(kind);
        const currentName = () => item.name || (item.empty ? t('Empty Object') : '');
        nameInput.value = currentName(); nameInput.placeholder = selection.label(kind, item, false);
        nameLabel.append(nameInput); container.append(nameLabel);
        nameInput.addEventListener('input', () => nameInput.setCustomValidity(''), { signal });
        nameInput.addEventListener('change', () => {
            if (isBusy() || state.preview || nameInput.disabled) return;
            const name = nameInput.value.trim();
            nameInput.setCustomValidity(name.includes('\0') || Array.from(name).length > 120
                || nameInput.required && !name ? t('Use a name with 1 to 120 characters.') : '');
            if (!nameInput.reportValidity()) return;
            nameInput.value = name;
            if ((item.name || '') === name) return;
            if (name) item.name = name; else delete item.name;
            commit(); renderCanvas(); renderLayers();
            if (selectionLabel) selectionLabel.textContent = selection.label(kind, item);
        }, { signal });
        nameInput.addEventListener('keydown', event => {
            if (event.isComposing || !['Enter', 'Escape'].includes(event.key)) return;
            event.preventDefault(); event.stopPropagation();
            if (event.key === 'Escape') { nameInput.value = currentName(); nameInput.setCustomValidity(''); }
            else nameInput.dispatchEvent(new Event('change'));
            if (nameInput.checkValidity()) { nameInput.blur(); if (!target) viewport.focus({ preventScroll: true }); }
        }, { signal });
        if (item.empty) container.append(node('p', { class: 'map-builder__hint' },
            t('An invisible object with states and behaviors. Only the GM can see its marker.')));
        const owner = isNativeKind(kind) && torchOwner(state.document, kind, item.id);
        if (owner) {
            const selectTorch = node('button', { type: 'button', 'data-builder-select-torch': owner.id }, t('Select linked torch'));
            selectTorch.addEventListener('click', () => { selection.set([{ kind: 'decorations', id: owner.id }]); renderSelection(); renderProperties(); }, { signal });
            container.append(selectTorch);
        }
        if (hasNativeEditor(kind)) {
            const edit = node('button', { type: 'button', 'data-builder-edit-native': kind }, t('Open game editor'));
            edit.addEventListener('click', () => { closePropertyModal(); void openNativeEditor({ kind, id: item.id }); }, { signal });
            container.append(edit);
        }
        if (kind === 'walls') container.append(node('p', { class: 'map-builder__hint' },
            t('Drag wall nodes to reshape connected walls. Use + to add a node or extend an endpoint.')));
        const row = node('div', { class: 'map-builder__fields' });
        const addField = (label, key, min, max, step = 'any') => {
            const wrapper = node('label', {}, t(label));
            const input = node('input', { type: 'number', min, max, step, required: '', 'data-builder-property': key });
            input.value = owner && ['x', 'y'].includes(key) ? torchComponentState(state.document, kind, item)[key] : item[key];
            wrapper.append(input); row.append(wrapper);
            input.addEventListener('change', () => {
                if (isBusy() || state.preview || input.disabled || !input.checkValidity() || !Number.isFinite(Number(input.value))) return;
                if (Number(input.value) === (owner && ['x', 'y'].includes(key) ? torchComponentState(state.document, kind, item)[key] : item[key])) return;
                const before = clone(state.document);
                if (kind === 'decorations' && item.torch) {
                    if (!updateTorchGeometry(state.document, item.id, { [key]: Number(input.value) })) {
                        notify(t('Keep objects inside the map.'), [], 'error'); renderProperties(); return;
                    }
                } else if (owner && ['x', 'y'].includes(key)) {
                    const displayed = torchComponentState(state.document, kind, item);
                    Object.assign(item, torchSourcePoint(state.document, kind, item.id, { x: displayed.x, y: displayed.y, [key]: Number(input.value) }));
                } else item[key] = Number(input.value);
                const valid = fitsBounds(state.document) && (kind !== 'doors' || doorFits(state.document, item))
                    && (kind !== 'walls' || length(item) >= .1);
                if (!valid) { state.document = before; notify(t('Keep objects inside the map. Doors must be 0.25 to 20 cells long and cannot overlap another door.'), [], 'error'); renderProperties(); return; }
                commit(); renderCanvas();
            }, { signal });
        };
        const bounds = documentBounds(state.document);
        if (kind === 'floors' || kind === 'decorations' || kind === 'regions') {
            addField('X', 'x', 0, bounds.width); addField('Y', 'y', 0, bounds.height);
            const minimum = kind === 'floors' && item.shape ? .001 : .05;
            addField('Width', 'width', minimum, bounds.width); addField('Height', 'height', minimum, bounds.height);
            if (kind !== 'regions') addField('Rotation', 'rotation', 0, kind === 'floors' ? 270 : 359, kind === 'floors' ? 90 : 1);
        } else if (kind === 'lights') {
            addField('X', 'x', 0, bounds.width); addField('Y', 'y', 0, bounds.height);
            addField('Bright radius (cells)', 'brightRadius', 0, 200); addField('Dim radius (cells)', 'dimRadius', 0, 200);
            addField('Intensity', 'intensity', 0, 1);
        } else if (isNativeKind(kind)) {
            addField('X', 'x', 0, bounds.width); addField('Y', 'y', 0, bounds.height);
        } else {
            addField('Start X', 'x1', 0, bounds.width); addField('Start Y', 'y1', 0, bounds.height);
            addField('End X', 'x2', 0, bounds.width); addField('End Y', 'y2', 0, bounds.height);
            addField('Thickness', 'thickness', .05, 2);
        }
        container.append(row);
        if (kind === 'walls' || kind === 'doors') {
            const label = node('label', { class: 'map-builder__torch-lit', 'data-builder-property-section': 'appearance' });
            const input = node('input', { type: 'checkbox', 'data-builder-property': 'artwork' });
            input.checked = item.artwork !== false;
            label.append(input, node('span', {}, t(kind === 'walls' ? 'Show wall artwork' : 'Show door artwork')));
            container.append(label, node('p', { class: 'map-builder__hint', 'data-builder-property-section': 'appearance' },
                t('Disable artwork to edit collision geometry over an existing map image. Guides appear only while editing.')));
            input.addEventListener('change', () => {
                if (isBusy() || state.preview || input.disabled) return;
                if (input.checked) delete item.artwork; else item.artwork = false;
                commit(); renderCanvas();
            }, { signal });
        }
        if (isNativeKind(kind)) {
            const first = container.childElementCount;
            renderNativeProperties(container, { kind, item, t, signal, change: patch => {
                if (isBusy() || state.preview) return;
                Object.assign(item, patch); commit(); renderCanvas();
            } });
            for (const child of [...container.children].slice(first)) child.dataset.builderPropertySection = 'appearance';
        } else if (kind !== 'regions' && !item.empty && item.brush?.operation !== 'erase') {
            const assetLabel = node('label', { 'data-builder-property-section': 'appearance' }, t('Appearance')), select = node('select', { 'data-builder-property': 'assetId' });
            select.append(new Option(t('Default appearance'), ''));
            select.options[0].disabled = isSmartDecoration(item);
            for (const entry of state.document.assets.filter(entry => entry.role === roleForKind(kind))) {
                const asset = assetById(entry.assetId); if (asset) select.append(new Option(assetName(asset), asset.id));
            }
            select.value = item.assetId || ''; assetLabel.append(select); container.append(assetLabel);
            select.addEventListener('change', () => {
                if (!select.value && isSmartDecoration(item)) { select.value = item.assetId; return; }
                item.assetId = select.value || null;
                if (kind === 'floors') delete item.paint;
                commit(); renderCanvas(); renderLayers(); renderMaterials(); renderProperties();
            }, { signal });
        }
        if (kind === 'doors') {
            const anchorLabel = node('label', {}, t('Rotation anchor point'));
            const anchorSelect = node('select', { 'data-builder-property': 'rotationAnchor' });
            for (const [value, text] of [['', 'Default (center)'], ['start', 'Start of door'], ['center', 'Center of door'], ['end', 'End of door']])
                anchorSelect.append(new Option(t(text), value));
            anchorSelect.value = item.rotationAnchor ?? ''; anchorLabel.append(anchorSelect); container.append(anchorLabel);
            anchorSelect.addEventListener('change', () => {
                if (isBusy() || state.preview || anchorSelect.disabled || anchorSelect.value === (item.rotationAnchor ?? '')) return;
                if (!anchorSelect.value) delete item.rotationAnchor; else item.rotationAnchor = anchorSelect.value;
                commit(); renderCanvas();
            }, { signal });
            container.append(node('small', { class: 'map-builder__hint' }, t('An anchor rotates the door image 90° when opened.')));
            const field = node('div', { class: 'map-builder__state-field', 'data-builder-property-section': 'properties behavior' });
            const title = node('span', { id: `builder-door-state-${crypto.randomUUID()}` }, t('Initial state'));
            const group = node('div', { class: 'map-builder__segmented', role: 'group', 'aria-labelledby': title.id, 'data-builder-property': 'state', 'data-value': item.state });
            for (const [value, text] of [['closed', 'Closed'], ['open', 'Opened'], ['locked', 'Locked']]) {
                const option = node('button', { type: 'button', 'data-builder-door-state': value, 'aria-pressed': String(item.state === value) }, t(text));
                option.addEventListener('click', () => {
                    if (item.state === value) return;
                    item.state = value; group.dataset.value = value;
                    for (const other of group.children) other.setAttribute('aria-pressed', String(other === option));
                    commit(); renderCanvas();
                }, { signal });
                group.append(option);
            }
            field.append(title, group); container.append(field);
        }
        if (kind === 'decorations') {
            const first = container.childElementCount;
            const behaviorLabel = node('label', {}, t('Behavior'));
            const behavior = node('select', { 'data-builder-property': 'behavior' });
            behavior.append(new Option(t('None'), 'none'), new Option(t('Lever'), 'lever'), new Option(t('Torch'), 'torch'));
            for (const preset of interactiveObjectPresets) {
                const option = new Option(t(preset.name), `preset:${preset.id}`); option.disabled = Boolean(item.torch); behavior.append(option);
            }
            behavior.value = item.torch ? 'torch' : item.lever ? 'lever' : 'none'; behaviorLabel.append(behavior); if (!item.empty) container.append(behaviorLabel);
            behavior.addEventListener('change', () => {
                if (isBusy() || state.preview) return;
                const nextBehavior = behavior.value;
                if (nextBehavior.startsWith('preset:')) {
                    behavior.value = item.torch ? 'torch' : item.lever ? 'lever' : 'none';
                    if (item.torch) { notify(t('Choose a decorative object without torch components.'), [], 'error'); return; }
                    void openPreset(currentTarget, nextBehavior.slice(7)); return;
                }
                if (nextBehavior === (item.torch ? 'torch' : item.lever ? 'lever' : 'none')) return;
                if (behavior.value !== 'none' && !item.assetId) {
                    behavior.value = isSmartDecoration(item) ? item.torch ? 'torch' : 'lever' : 'none';
                    notify(t(nextBehavior === 'lever' ? 'Choose an object image before enabling lever behavior.' : 'Choose an object image before enabling torch behavior.'), [], 'error'); return;
                }
                if (nextBehavior === 'torch' && selection.all().length >= (state.limits.maxObjects || 2000)) { behavior.value = item.lever ? 'lever' : 'none'; notify(t('The map has too many objects.'), [], 'error'); return; }
                const before = clone(state.document);
                try {
                    if (item.torch) detachTorch(item);
                    delete item.lever; delete item.blueprint;
                    if (nextBehavior === 'none') delete item.interactionEnabled;
                    if (behavior.value === 'lever') {
                        item.lever = { state: 'off' };
                    } else if (behavior.value === 'torch') {
                        const light = createTorchComponent(item, 'lights');
                        if (!attachTorch(state.document, item.id, { lightId: light.id })) throw new Error('Choose an unlinked torch component from the same layer.');
                    }
                } catch (error) {
                    state.document = before; renderCanvas(); renderProperties(); notify(t(error.message), [], 'error'); return;
                }
                commit(); renderCanvas(); renderLayers(); renderProperties();
            }, { signal });
            if (!item.torch && (item.assetId || item.empty)) {
                const catalog = node('button', { type: 'button', 'data-builder-object-catalog': '' }, t('Interactive object catalog'));
                catalog.addEventListener('click', () => void openPreset(currentTarget), { signal });
                container.append(catalog);
            }
            if (item.lever) {
                const label = node('label', {}, t('Initial state'));
                const initial = node('select', { 'data-builder-property': 'leverState' });
                initial.append(new Option(t('Deactivated'), 'off'), new Option(t('Activated'), 'on'));
                initial.value = item.lever.state; label.append(initial); container.append(label);
                initial.addEventListener('change', () => { item.lever.state = initial.value; commit(); renderCanvas(); }, { signal });
                const edit = node('button', { type: 'button', 'data-builder-edit-behavior': '' }, t('Edit behavior'));
                edit.addEventListener('click', () => { closePropertyModal(); openBehavior(currentTarget); }, { signal }); container.append(edit);
                container.append(node('p', { class: 'map-builder__hint' }, t(item.empty ? 'Double-click the object to edit its states and actions.' : 'Double-click the lever to edit its states and actions.')));
            }
            if (item.torch) renderTorchProperties(container, item, { signal, target: currentTarget });
            for (const child of [...container.children].slice(first)) child.dataset.builderPropertySection ||= 'behavior';
        }
        if (['floors', 'walls'].includes(kind) && item.brush?.operation !== 'erase') {
            const first = container.childElementCount;
            const label = node('label', { class: 'map-builder__torch-lit' }), input = node('input', { type: 'checkbox', 'data-builder-property': 'dynamic' });
            input.checked = item.dynamic === true;
            label.append(input, node('span', {}, t('Dynamic surface'))); container.append(label,
                node('p', { class: 'map-builder__hint' }, t('Publish this artwork separately so behaviors can change its material or visibility during play.')));
            input.addEventListener('change', () => {
                if (isBusy() || state.preview || !setDynamicSurface(state.document, kind, item.id, input.checked)) return;
                commit(); renderCanvas();
            }, { signal });
            for (const child of [...container.children].slice(first)) child.dataset.builderPropertySection = 'behavior';
        }
        if (kind === 'doors' || kind === 'decorations' && isSmartDecoration(item)) {
            const first = container.childElementCount;
            const label = node('label', { class: 'map-builder__torch-lit' });
            const input = node('input', { type: 'checkbox', 'data-builder-property': 'interactionEnabled' });
            input.checked = item.interactionEnabled !== false;
            label.append(input, node('span', {}, t('Player interaction'))); container.append(label,
                node('p', { class: 'map-builder__hint' }, t('The GM can always operate and edit this element.')));
            input.addEventListener('change', () => {
                if (isBusy() || state.preview) return;
                if (input.checked) delete item.interactionEnabled; else item.interactionEnabled = false;
                commit();
            }, { signal });
            for (const child of [...container.children].slice(first)) child.dataset.builderPropertySection = 'behavior';
        }
        if (kind === 'regions') {
            const first = container.childElementCount;
            renderRegionProperties(container, item, { signal, target: currentTarget });
            for (const child of [...container.children].slice(first)) child.dataset.builderPropertySection = 'region behavior';
        }
        const button = node('button', { type: 'button', 'data-builder-delete': '' }, t('Delete object'));
        button.addEventListener('click', deleteSelection, { signal }); container.append(button);
        if (section) {
            for (const child of container.children) child.hidden = child.tagName === 'STRONG' ? false
                : !(child.dataset.builderPropertySection || 'properties').split(' ').includes(section) || child === button;
            if (![...container.children].some(child => !child.hidden && child.tagName !== 'STRONG')) {
                container.append(node('p', { class: 'map-builder__hint' }, t('This object has no options in this section.')));
            }
            for (const control of container.querySelectorAll('input,select,textarea,button')) control.disabled ||= isBusy() || state.preview;
        }
        applyPreviewControls();
    }
    function renderRegionProperties(container, item, { signal, target }) {
        const enabledLabel = node('label', { class: 'map-builder__torch-lit' });
        const enabled = node('input', { type: 'checkbox', 'data-builder-property': 'regionEnabled' });
        enabled.checked = item.enabled;
        enabledLabel.append(enabled, node('span', {}, t('Presence triggers enabled'))); container.append(enabledLabel);
        enabled.addEventListener('change', () => {
            if (isBusy() || state.preview) return;
            item.enabled = enabled.checked; commit(); renderCanvas();
        }, { signal });
        const vertical = node('div', { class: 'map-builder__fields' });
        for (const [key, label] of [['bottom', 'Minimum elevation'], ['top', 'Maximum elevation']]) {
            const field = node('label', {}, t(label)), input = node('input', { type: 'number', min: '-1000000', max: '1000000', step: 'any',
                placeholder: t('Unbounded'), 'data-builder-property': `region-${key}` });
            input.value = item.vertical?.[key] ?? ''; field.append(input); vertical.append(field);
            input.addEventListener('change', () => {
                if (isBusy() || state.preview || !input.checkValidity()) return;
                const next = { bottom: null, top: null, ...item.vertical, [key]: input.value === '' ? null : Number(input.value) };
                if (next.bottom !== null && next.top !== null && next.bottom > next.top) { renderProperties(); notify(t('Minimum elevation cannot exceed maximum elevation.'), [], 'error'); return; }
                if (sameDocument(item.vertical || { bottom: null, top: null }, next)) return;
                item.vertical = next; commit();
            }, { signal });
        }
        container.append(vertical, node('p', { class: 'map-builder__hint' },
            t('The first token activates the region; the last token leaving releases it. Region guides are visible only to the GM.')));
        container.append(createRegionFilterControls({ filters: item.filters, t, signal, linked: Boolean(state.sceneId),
            loadCatalog: loadFilterCatalog, onReady: applyPreviewControls, onChange: filters => {
                if (isBusy() || state.preview || !container.isConnected) return;
                const next = normalizeRegionFilters(filters);
                if (sameDocument(normalizeRegionFilters(item.filters), next)) return;
                if (!next.tokenIds.length && !next.actorIds.length && !next.dispositions.length && next.visibility === 'any') delete item.filters;
                else item.filters = next;
                commit();
            } }));
        const preset = node('fieldset', { class: 'map-builder__region-preset' });
        preset.append(node('legend', {}, t('Pressure plate')));
        const doorLabel = node('label', {}, t('Controlled door')), door = node('select', { 'data-builder-region-door': '' });
        door.append(new Option(t('Choose a door'), ''));
        state.document.doors.forEach((entry, index) => door.append(new Option(entry.name || `${t('Door')} ${index + 1}`, entry.id)));
        doorLabel.append(door); preset.append(doorLabel);
        const actions = node('div', { class: 'map-builder__region-actions' });
        const pick = node('button', { type: 'button', 'data-builder-region-pick-door': '' }, t('Pick door on map'));
        const apply = node('button', { type: 'button', 'data-builder-region-apply': '', disabled: '' }, t('Apply pressure plate'));
        door.addEventListener('change', () => { apply.disabled = !door.value; }, { signal });
        pick.disabled = !state.document.doors.length;
        pick.addEventListener('click', async () => {
            const modal = propertyModal?.body === container ? propertyModal.modal : null;
            const previousTab = state.sidebarTab;
            modal?.suspend?.(); setSidebarTab('library');
            try {
                const id = await pickOnMap('doors');
                if (isDisposed() || signal.aborted || !container.isConnected) return;
                setSidebarTab(modal ? previousTab : 'selection', !modal);
                if (id) { door.value = id; apply.disabled = false; }
            } finally {
                if (!isDisposed() && modal?.isConnected) { modal.resume?.(); pick.focus({ preventScroll: true }); }
            }
        }, { signal });
        apply.addEventListener('click', () => {
            if (isBusy() || state.preview || !state.document.doors.some(entry => entry.id === door.value)) return;
            configurePressurePlate(item, door.value); commit(); renderProperties();
            notify(t('Pressure plate configured: first token opens the door; last token closes it.'));
        }, { signal });
        actions.append(pick, apply); preset.append(actions,
            node('p', { class: 'map-builder__hint' }, t('Applying this preset replaces this region\u2019s Blueprint.')));
        const edit = node('button', { type: 'button', 'data-builder-edit-behavior': '' }, t('Edit behavior'));
        edit.addEventListener('click', () => { closePropertyModal(); openBehavior(target); }, { signal });
        container.append(preset, edit);
    }
    function renderTorchProperties(container, item, { signal, target }) {
        const mechanism = node('label', {}, t('Mechanism'));
        const stateControl = node('select', { 'data-builder-property': 'torchState' });
        stateControl.append(new Option(t('Normal'), 'off'), new Option(t('Turned'), 'on'));
        stateControl.value = item.torch.state; mechanism.append(stateControl); container.append(mechanism);
        stateControl.addEventListener('change', () => {
            if (isBusy() || state.preview) return;
            if (item.torch.state === stateControl.value) return;
            const previous = item.torch.state; item.torch.state = stateControl.value;
            if (!fitsBounds(state.document)) { item.torch.state = previous; renderProperties(); notify(t('Keep objects inside the map.'), [], 'error'); return; }
            commit(); renderCanvas();
        }, { signal });
        const litLabel = node('label', { class: 'map-builder__torch-lit' });
        const lit = node('input', { type: 'checkbox', 'data-builder-property': 'torchLit' }); lit.checked = item.torch.lit;
        litLabel.append(lit, node('span', {}, t('Flame lit'))); container.append(litLabel);
        lit.addEventListener('change', () => { if (!isBusy() && !state.preview) { item.torch.lit = lit.checked; commit(); renderCanvas(); } }, { signal });
        const components = node('section', { class: 'map-builder__torch-components', 'aria-label': t('Torch components'),
            'data-builder-property-section': 'components' });
        components.append(node('strong', {}, t('Torch components')));
        for (const [kind, key, label] of [['lights', 'lightId', 'Light'], ['particles', 'particleId', 'Particles'], ['shaders', 'shaderId', 'Shader']]) {
            const row = node('div', { class: 'map-builder__torch-component' }); row.append(node('span', {}, t(label)));
            const component = selection.item({ kind, id: item.torch[key] });
            if (component) {
                const edit = node('button', { type: 'button', 'data-builder-edit-torch-component': kind }, t('Edit'));
                edit.addEventListener('click', () => { closePropertyModal(); void openNativeEditor({ kind, id: component.id }, { keepSelection: true }); }, { signal }); row.append(edit);
                if (kind !== 'lights') {
                    const remove = node('button', { type: 'button', 'data-builder-remove-torch-component': kind }, t('Remove'));
                    remove.addEventListener('click', () => { if (isBusy() || state.preview) return; removeObject(state.document, kind, component.id); commit(); renderCanvas(); renderLayers(); renderProperties(); }, { signal }); row.append(remove);
                }
            } else {
                const add = node('button', { type: 'button', 'data-builder-add-torch-component': kind }, t('Add'));
                add.addEventListener('click', () => {
                    if (isBusy() || state.preview) return;
                    const maximum = state.limits.maxObjects || 2000;
                    if (selection.all().length >= maximum) { notify(t('The map has too many objects.'), [], 'error'); return; }
                    const next = createTorchComponent(item, kind); item.torch[key] = next.id;
                    commit(); renderCanvas(); renderLayers(); renderProperties();
                }, { signal }); row.append(add);
            }
            components.append(row);
        }
        container.append(components);
        const edit = node('button', { type: 'button', 'data-builder-edit-behavior': '' }, t('Edit behavior'));
        edit.addEventListener('click', () => { closePropertyModal(); openBehavior(target); }, { signal }); container.append(edit);
        container.append(node('p', { class: 'map-builder__hint' }, t('Turning the mechanism and lighting the flame are independent. Double-click the torch to edit its behavior.')));
    }
    function closePropertyModal() { propertyModal?.modal.close(); }
    async function openProperties(target = state.selection, section = 'properties') {
        if (isBusy() || state.preview || isDisposed() || !target || !selection.item(target)) return null;
        const source = state.document;
        const { mountModal } = await import('/static/gravewright_table/modal.js');
        if (isDisposed() || parentSignal?.aborted || state.document !== source || !selection.item(target)) return null;
        closePropertyModal();
        if (!document.querySelector('link[data-builder-property-modal-style]')) {
            const stylesheet = node('link', { rel: 'stylesheet', href: new URL('./property-modal.css', import.meta.url).href,
                'data-builder-property-modal-style': '' }); document.head.append(stylesheet);
        }
        const abort = fieldSignal(), { signal } = abort;
        const modal = node('section', { class: 'table-form-modal map-builder-property-modal',
            'data-builder-property-modal': section });
        const header = node('header'), title = node('strong', { id: `builder-properties-${crypto.randomUUID()}` }, t(sections[section] || sections.properties));
        modal.setAttribute('aria-labelledby', title.id);
        const close = node('button', { type: 'button' }, t('Close'));
        close.addEventListener('click', () => modal.close(), { signal }); header.append(title, close);
        const body = node('div', { class: 'map-builder-property-modal__body', 'data-builder-modal-properties': '' });
        const footer = node('footer'), done = node('button', { type: 'button' }, t('Done'));
        done.addEventListener('click', () => modal.close(), { signal }); footer.append(done); modal.append(header, body, footer);
        modal.addEventListener('gravewright:sheet-flush', () => {
            const focused = document.activeElement;
            if (body.contains(focused) && focused.matches('input,select,textarea') && !focused.disabled) {
                focused.dispatchEvent(new Event('change'));
            }
        }, { signal });
        propertyModal = { modal, body, target: { ...target }, section };
        modal.addEventListener('close', () => {
            abort.abort(); modalFieldsAbort?.abort();
            if (propertyModal?.modal === modal) propertyModal = null;
        }, { once: true });
        signal.addEventListener('abort', () => modal.close?.(true), { once: true });
        renderProperties(); mountModal(modal, { nested: true }); onModal?.(modal); return modal;
    }
    async function openPreset(target = state.selection, initialPreset) {
        const item = target && selection.item(target);
        if (openingObjectCatalog || isBusy() || state.preview || isDisposed() || target?.kind !== 'decorations' || !item || item.torch || !(item.assetId || item.empty)) return null;
        openingObjectCatalog = true;
        const source = state.document;
        closePropertyModal();
        try {
            const materials = source.assets.filter(entry => entry.role === 'decoration').flatMap(entry => {
                const asset = assetById(entry.assetId); return asset ? [{ ...asset, name: assetName(asset) }] : [];
            });
            const modal = await openInteractiveObjectCatalog({ element: item, doors: source.doors, handouts: state.handouts || [],
                users: state.users || [], sounds: state.sounds || [], assets: materials, materials, initialPreset, t, signal: parentSignal,
                onApply: result => {
                    if (isDisposed() || state.document !== source || !source.decorations.includes(item)) throw new Error('Select an object to edit its properties.');
                    item.lever = { state: result.initialState }; item.blueprint = result.blueprint;
                    if (!item.name || item.empty && item.name === t('Empty Object')) item.name = result.name;
                    commit(); renderCanvas(); renderLayers(); renderProperties();
                } });
            if (modal) onModal?.(modal); return modal;
        } catch (error) { if (!isDisposed()) notify(t(error.message || 'Could not load the editor.'), [], 'error'); return null; }
        finally { openingObjectCatalog = false; }
    }
    return { renderProperties, openProperties, openPreset };
}
