/** Campaign assets, brush choices and their library/material controls. */
import { familyAssetIds, objectKinds } from './model.js';
import { isNativeKind, renderNativeLibrary } from './native-controls.js';

export function createWorkspaceLibrary({ root, state, t, locale, signal, isBusy, commit,
    onBrushChosen, renderDockTools, chooseNativePreset, applyPreviewControls,
    onMaterialChosen, openImport, notify, selected }) {
    const $ = selector => root.querySelector(selector);
    const kindForTool = tool => tool === 'decoration' ? 'decorations' : tool + 's';
    const roleForKind = kind => kind === 'decorations' ? 'decoration' : kind.slice(0, -1);
    const isSmartDecoration = item => Boolean(item?.lever || item?.torch);
    function node(tag, attrs = {}, text) {
        const element = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'class') element.className = value;
            else element.setAttribute(key, value);
        }
        if (text !== undefined) element.textContent = text;
        return element;
    }
    function assetById(id) { return state.assets.find(value => value.id === id); }
    function roleFor(id) { return state.document.assets.find(value => value.assetId === id)?.role; }
    function assetInfo(id) { return state.document.assets.find(value => value.assetId === id); }
    function assetName(asset) { return assetInfo(asset.id)?.name || asset.name; }
    function assetUsedByOtherRole(id, role) {
        return objectKinds.some(kind => kind !== kindForTool(role) && (state.document[kind] || []).some(item =>
            item.assetId === id || Object.values(item.blueprint?.states || {}).some(state =>
                state.appearance === 'asset' && state.assetId === id) || Object.values(item.blueprint?.graphs || {}).some(graph =>
                graph.nodes.some(node => node.type === 'sprite' && node.appearance === 'asset' && node.assetId === id))));
    }
    function classificationError(id, role, family = assetInfo(id)?.family) {
        if (!assetInfo(id) && state.document.assets.length >= (state.limits.maxAssets || 256)) return 'The map has too many assets.';
        if (assetUsedByOtherRole(id, role)) return 'This asset is already used by another brush. Upload a separate copy to use a different type.';
        if (family && state.document.assets.some(entry => entry.assetId !== id && entry.family === family && entry.role !== role)) {
            return 'An asset family must contain only one asset type.';
        }
        return null;
    }
    function classify(id, role, family) {
        const error = classificationError(id, role, family);
        if (error) throw new Error(t(error));
        const existing = state.document.assets.find(value => value.assetId === id);
        if (existing) existing.role = role;
        else state.document.assets.push({ assetId: id, role });
    }
    function builtinAssetName(role) {
        return t(role === 'floor' ? 'Solid floor' : role === 'wall' ? 'Plain wall' : role === 'door' ? 'Native door' : 'Empty object');
    }
    function chooseBrushAsset(id, role = state.role, closePanel = false) {
        if (isBusy() || state.preview) return;
        try { if (id) classify(id, role); }
        catch (cause) { renderBrushMaterial(); notify(cause.message, [], 'error'); return; }
        state.selectedAssets[role] = id || null; state.selectedFamilies[role] = null;
        if (id) commit();
        onBrushChosen(role, closePanel);
    }
    function familyGroups(role) {
        const result = new Map();
        for (const entry of state.document.assets) {
            const asset = assetById(entry.assetId);
            if (!entry.family || !asset || role && entry.role !== role) continue;
            if (!result.has(entry.family)) result.set(entry.family, { name: entry.family, role: entry.role, assets: [] });
            result.get(entry.family).assets.push(asset);
        }
        return [...result.values()].sort((a, b) => a.name.localeCompare(b.name, locale()));
    }
    function brushAssetIds(role) {
        const family = state.selectedFamilies[role];
        return family ? familyAssetIds(state.document, role, family).filter(id => assetById(id)) : [state.selectedAssets[role] || null];
    }
    function chooseFamily(name, role = state.role, closePanel = false) {
        if (isBusy() || state.preview || !familyAssetIds(state.document, role, name).length) return;
        state.selectedFamilies[role] = name;
        onBrushChosen(role, closePanel);
    }
    function chooseMaterial(value) {
        if (value.startsWith('family:')) chooseFamily(value.slice(7));
        else chooseBrushAsset(value);
    }
    function renderBrushMaterial() {
        const select = $('[data-builder-brush-material]');
        if (!select) return;
        const role = state.role, family = state.selectedFamilies[role], active = state.selectedAssets[role];
        const assets = state.assets.filter(asset => roleFor(asset.id) === role)
            .sort((a, b) => assetName(a).localeCompare(assetName(b), locale()));
        const unclassified = state.assets.filter(asset => !roleFor(asset.id))
            .sort((a, b) => assetName(a).localeCompare(assetName(b), locale()));
        const families = familyGroups(role);
        select.replaceChildren(new Option(builtinAssetName(role), ''));
        if (families.length) {
            const group = node('optgroup', { label: t('Asset families') });
            for (const entry of families) group.append(new Option(entry.name, 'family:' + entry.name));
            select.append(group);
        }
        const images = node('optgroup', { label: t('Images') });
        for (const asset of assets) images.append(new Option(assetName(asset), asset.id));
        select.append(images);
        if (unclassified.length) {
            const group = node('optgroup', { label: t('Unclassified images') });
            for (const asset of unclassified) group.append(new Option(assetName(asset), asset.id));
            select.append(group);
        }
        select.value = family ? 'family:' + family : active || '';
        const thumbnail = $('[data-builder-brush-thumbnail]'), asset = family ? assetById(brushAssetIds(role)[0]) : assetById(active);
        if (thumbnail) {
            thumbnail.hidden = !asset;
            if (asset) thumbnail.src = asset.url;
            else thumbnail.removeAttribute('src');
        }
    }
    function renderLibraryFilter() {
        const select = $('[data-builder-collection-filter]');
        if (!select) return null;
        const effects = state.libraryFilter === 'effect', label = effects ? 'Effect type' : 'Collection';
        select.setAttribute('aria-label', t(label));
        select.parentElement.querySelector('.map-builder__sr-only').textContent = t(label);
        if (effects) {
            select.replaceChildren(new Option(t('Particles'), 'particle'), new Option(t('Shaders'), 'shader'));
            select.value = state.effectLibraryTool;
        } else {
            const collections = [...new Set(state.document.assets.map(entry => entry.collection).filter(Boolean))]
                .sort((a, b) => a.localeCompare(b, locale()));
            select.replaceChildren(new Option(t('All collections'), ''), ...collections.map(name => new Option(name, name)));
            if (!collections.includes(state.libraryCollection)) state.libraryCollection = '';
            select.value = state.libraryCollection;
        }
        select.disabled = isBusy() || state.preview;
        return select;
    }
    function renderAssets() {
        const container = $('[data-builder-assets]'); container.replaceChildren();
        const light = ['light', 'effect'].includes(state.libraryFilter);
        root.dataset.libraryRole = state.libraryRole;
        container.hidden = false;
        container.classList.toggle('map-builder__asset-list--native', light);
        renderDockTools();
        const helper = $('[data-builder-library-help]');
        if (helper) { helper.hidden = !light; helper.textContent = light ? t('Choose a preset, then click the map to place it. Edit its settings in Selection.') : ''; }
        const upload = $('[data-builder-import]'); if (upload) upload.hidden = light;
        const details = root.querySelector('.map-builder__asset-details'); if (details) details.hidden = light;
        const search = $('[data-builder-search]').value.trim().toLocaleLowerCase(locale());
        const collection = renderLibraryFilter();
        if (light) {
            const count = renderNativeLibrary(container, { role: state.libraryFilter, effectTool: state.effectLibraryTool,
                search, choices: state.nativeChoices, t,
                choose: (tool, id) => chooseNativePreset(tool, id, true), signal });
            $('[data-builder-asset-count]').textContent = String(count);
            $('[data-builder-assets-empty]').hidden = count > 0;
            $('[data-builder-assets-empty]').textContent = t('No matching presets.');
            $('[data-builder-classify]').hidden = true;
            renderBrushMaterial(); renderMaterials(); applyPreviewControls(); return;
        }
        const chosenCollection = state.libraryCollection;
        const assets = light ? [] : state.assets.filter(asset => roleFor(asset.id) === state.libraryFilter
            && assetName(asset).toLocaleLowerCase(locale()).includes(search)
            && (!collection?.value || assetInfo(asset.id)?.collection === collection.value));
        for (const role of ['floor', 'wall', 'door', 'decoration']) {
            const id = state.selectedAssets[role];
            if (id && (!assetById(id) || roleFor(id) !== role)) state.selectedAssets[role] = null;
        }
        for (const role of ['floor', 'wall', 'door', 'decoration']) {
            if (state.selectedFamilies[role] && !brushAssetIds(role).length) state.selectedFamilies[role] = null;
        }
        const active = state.selectedAssets[state.role];
        if (state.libraryFilter === 'decoration' && !chosenCollection && t('Empty Object').toLocaleLowerCase(locale()).includes(search)) {
            const button = node('button', { type: 'button', class: 'map-builder__asset', 'data-builder-empty-object': '',
                'aria-pressed': String(state.tool === 'decoration' && !active && !state.selectedFamilies.decoration), title: t('Place an Empty Object') });
            const preview = node('span', { class: 'map-builder__empty-preview', 'aria-hidden': 'true' });
            preview.append($('[data-builder-empty-object] svg').cloneNode(true));
            button.append(preview, node('span', {}, t('Empty Object')));
            button.addEventListener('click', () => chooseBrushAsset(null, 'decoration', true), { signal }); container.append(button);
        }
        if (!light) for (const family of familyGroups()) {
            if (state.libraryFilter && family.role !== state.libraryFilter || !family.name.toLocaleLowerCase(locale()).includes(search)) continue;
            if (chosenCollection && !family.assets.some(asset => assetInfo(asset.id)?.collection === chosenCollection)) continue;
            const button = node('button', { type: 'button', class: 'map-builder__asset map-builder__family', 'data-family-name': family.name, 'data-family-role': family.role,
                title: t('Asset family: {name}', { name: family.name }), 'aria-pressed': String(state.selectedFamilies[state.role] === family.name && state.role === family.role) });
            const preview = node('span', { class: 'map-builder__family-preview', 'aria-hidden': 'true' });
            for (const asset of family.assets.slice(0, 4)) preview.append(node('img', { src: asset.url, alt: '', loading: 'lazy', draggable: 'false' }));
            preview.append(node('span', { class: 'map-builder__family-count' }, String(family.assets.length)));
            button.append(preview, node('span', { translate: 'no' }, family.name));
            button.addEventListener('click', () => chooseFamily(family.name, family.role, true), { signal }); container.append(button);
        }
        const roles = ['floor', 'wall', 'door', 'decoration'];
        const roleOrder = asset => { const index = roles.indexOf(roleFor(asset.id)); return index < 0 ? roles.length : index; };
        for (const asset of assets.sort((a, b) => roleOrder(a) - roleOrder(b) || assetName(a).localeCompare(assetName(b), locale()))) {
            const role = roleFor(asset.id), aspect = asset.width / asset.height;
            const button = node('button', { type: 'button', class: 'map-builder__asset', title: assetName(asset),
                'data-asset-id': asset.id, 'data-asset-role': role || '', 'aria-pressed': String(!state.selectedFamilies[state.role] && active === asset.id) });
            if (role === 'decoration' && Number.isFinite(aspect) && aspect > 1) button.style.setProperty('--builder-asset-aspect', String(Math.min(2, aspect)));
            const image = node('img', { src: asset.url, alt: '', loading: 'lazy', draggable: 'false' });
            button.append(image, node('span', { translate: 'no' }, assetName(asset)));
            button.addEventListener('click', () => chooseBrushAsset(asset.id, roleFor(asset.id) || state.role, true), { signal });
            button.addEventListener('dblclick', () => openImport(asset), { signal });
            button.addEventListener('contextmenu', event => { event.preventDefault(); openImport(asset); }, { signal });
            button.addEventListener('keydown', event => { if (event.key === 'ContextMenu' || event.shiftKey && event.key === 'F10') { event.preventDefault(); openImport(asset); } }, { signal });
            container.append(button);
        }
        $('[data-builder-asset-count]').textContent = String(state.assets.length);
        $('[data-builder-assets-empty]').textContent = t(state.assets.length ? 'No matching content.' : 'Upload your own textures and choose a brush to start.');
        $('[data-builder-assets-empty]').hidden = container.childElementCount > 0;
        $('[data-builder-classify]').hidden = light || !active;
        $('[data-builder-asset-role]').value = active ? roleFor(active) || state.role : state.role;
        if ($('[data-builder-asset-name]')) $('[data-builder-asset-name]').value = active ? assetName(assetById(active)) : '';
        if ($('[data-builder-asset-collection]')) $('[data-builder-asset-collection]').value = active ? assetInfo(active)?.collection || '' : '';
        renderBrushMaterial(); renderMaterials();
        applyPreviewControls();
    }
    function renderMaterials() {
        const container = $('[data-builder-material-list]');
        if (!container) return;
        container.replaceChildren();
        const item = selected(), kind = state.selection?.kind;
        const role = kind ? roleForKind(kind) : state.role;
        const current = item?.assetId || null;
        const title = $('[data-builder-material-name]');
        if (title) title.textContent = assetById(current) ? assetName(assetById(current)) : t('Default appearance');
        const choices = item?.empty || isNativeKind(kind) || state.selections.length > 1 ? [] : [null, ...state.assets.filter(asset => roleFor(asset.id) === role)];
        for (const asset of choices) {
            const button = node('button', { type: 'button', class: 'map-builder__material',
                'data-builder-material-id': asset?.id || '', 'aria-pressed': String(current === (asset?.id || null)),
                title: asset ? assetName(asset) : t('Default appearance'), 'aria-label': asset ? assetName(asset) : t('Default appearance') });
            if (asset) button.append(node('img', { src: asset.url, alt: '', loading: 'lazy', draggable: 'false' }));
            else button.append(node('span', { class: 'map-builder__material-default', 'aria-hidden': 'true' }));
            button.disabled = isBusy() || state.preview || !item || !asset && isSmartDecoration(item);
            button.addEventListener('click', () => onMaterialChosen(kind, asset?.id || null), { signal });
            container.append(button);
        }
    }
    return { assetById, roleFor, assetInfo, assetName, assetUsedByOtherRole, classify,
        familyGroups, brushAssetIds, chooseBrushAsset, chooseFamily, chooseMaterial,
        renderBrushMaterial, renderAssets, renderMaterials };
}
