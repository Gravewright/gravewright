import { hasBlueprintEventPath } from './builder/blueprint-model.js';

/** GM controls for existing scene elements. All writes use the host's authorized command. */
export function sceneControlKind(owner) {
    return owner.empty === true ? 'empty' : ['floor', 'wall'].includes(owner.surfaceKind) ? owner.surfaceKind : owner.kind || 'image';
}

export function sceneControlRows(catalog) {
    const native = [...(catalog.lights || []), ...(catalog.effects || [])].map(owner => ({ ...owner,
        kind: { lights: 'light', particles: 'particle', shaders: 'shader' }[owner.nativeKind] || 'light',
        enabled: owner.nativeData?.enabled ?? true, editable: false,
        point: owner.point || { x: owner.x, y: owner.y } }));
    return [...(catalog.elements || []), ...native];
}

export function sceneNativeItem(owner) {
    const item = { ...structuredClone(owner.nativeData), id: owner.id };
    if (owner.nativeKind === 'lights') Object.assign(item, { brightRadius: item.bright_radius, dimRadius: item.dim_radius });
    return item;
}

export function sceneNativePayload(owner, item, presets = []) {
    const fields = { lights: 'x y bright_radius dim_radius intensity color enabled angle rotation animation elevation',
        particles: 'x y kind scale density color enabled rotation light_response light_emission',
        shaders: 'name source x y radius scale intensity opacity speed color rotation blend_mode enabled light_response light_emission' };
    if (!Object.hasOwn(fields, owner.nativeKind)) throw new Error('Invalid effect.');
    const value = { ...item };
    if (owner.nativeKind === 'lights') Object.assign(value, { bright_radius: item.brightRadius, dim_radius: item.dimRadius });
    const preset = owner.nativeKind === 'shaders' && /^gravewright-preset:\/\/([^/]+)\/v1$/.exec(value.source);
    if (preset) {
        const source = presets.find(entry => entry.id === preset[1])?.source;
        if (!source) throw new Error('Unknown shader preset.');
        value.source = source;
    }
    const data = Object.fromEntries(fields[owner.nativeKind].split(' ').filter(key => value[key] !== undefined).map(key => [key, value[key]]));
    if (owner.nativeKind === 'lights') Object.assign(data, { light_id: owner.id, version: owner.version });
    else Object.assign(data, { [owner.nativeKind === 'particles' ? 'emitter_id' : 'shader_id']: owner.id, expected_version: owner.version });
    return data;
}

export function sceneControlPage(catalog, { query = '', type = 'all', page = 0 } = {}) {
    const text = query.trim().toLocaleLowerCase();
    const matches = sceneControlRows(catalog).filter(owner => (type === 'all' || sceneControlKind(owner) === type)
        && (!text || [owner.id, owner.name, owner.kind, owner.surfaceKind, ...Object.keys(owner.blueprint?.graphs || {})]
            .filter(Boolean).join(' ').toLocaleLowerCase().includes(text)));
    const pages = Math.max(1, Math.ceil(matches.length / 40));
    page = Number.isFinite(page) ? Math.max(0, Math.min(pages - 1, Math.trunc(page))) : 0;
    return { rows: matches.slice(page * 40, (page + 1) * 40), page, pages, total: matches.length };
}

export function sceneControlActions(owner) {
    const actions = [];
    const genericInteraction = owner.blueprint?.version === 2 && hasBlueprintEventPath(owner.blueprint, 'interact');
    if (owner.kind === 'door') {
        for (const [value, label] of [['open', 'Open door'], ['closed', 'Close door'], ['locked', 'Lock door']])
            actions.push({ action: 'state', value, label, disabled: owner.state === value });
        actions.push({ action: 'interact', label: 'Run interaction', disabled: !genericInteraction });
    }
    if (['lever', 'torch'].includes(owner.kind)) actions.push({ action: 'interact',
        label: owner.blueprint ? 'Run interaction' : owner.kind === 'torch' ? owner.state === 'on' ? 'Return torch' : 'Turn torch'
            : owner.state === 'on' ? 'Deactivate' : 'Activate', disabled: Boolean(owner.blueprint) && !genericInteraction });
    if (owner.kind === 'torch' && typeof owner.lit === 'boolean')
        actions.push({ action: 'flame', value: !owner.lit, label: owner.lit ? 'Extinguish torch' : 'Light torch' });
    if (typeof owner.visible === 'boolean')
        actions.push({ action: 'visibility', value: !owner.visible, label: owner.visible ? 'Hide' : 'Show' });
    return actions;
}

/** Mount inside the existing Automation window. Disposing cancels reads and listeners. */
export function mountSceneControls(host, { t, getSceneId, load, control, edit, locate, onChange, onTest }) {
    if (!document.querySelector('link[data-scene-controls-css]')) {
        const link = document.createElement('link'); link.rel = 'stylesheet';
        link.href = new URL('./scene-controls.css', import.meta.url).href; link.dataset.sceneControlsCss = '';
        document.head.append(link);
    }
    const lifetime = new AbortController(), signal = lifetime.signal;
    let scene = getSceneId(), sceneLifetime = new AbortController(), read, ticket = 0;
    let catalog = { elements: [], assets: [] }, selected, page = 0, loading = false, busy = false, failed = false, disposed = false;
    let notice = '', noticeError = false, currentChild, nativeEditor;
    const materialChoices = new Map();
    const make = (tag, attrs = {}, text) => {
        const node = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const listen = (node, event, handler) => node.addEventListener(event, handler, { signal });
    const button = (label, attrs, handler) => {
        const node = make('button', { type: 'button', ...attrs }, t(label));
        listen(node, 'click', handler); return node;
    };
    const panel = make('section', { class: 'scene-controls', 'data-scene-controls': '' });
    const toolbar = make('div', { class: 'scene-controls__toolbar' });
    const search = make('input', { type: 'search', maxlength: '240', 'data-scene-controls-search': '' });
    const types = make('select', { 'data-scene-controls-type': '' });
    const kinds = { all: 'All elements', door: 'Door', lever: 'Lever', torch: 'Torch', empty: 'Empty Object', region: 'Region', floor: 'Dynamic floor', wall: 'Dynamic wall', image: 'Object', light: 'Light', particle: 'Particles', shader: 'Shader' };
    for (const [value, label] of Object.entries(kinds)) types.append(make('option', { value }, t(label)));
    const refreshButton = button('Refresh', { 'data-scene-controls-refresh': '' }, () => void refresh());
    toolbar.append(search, types, refreshButton);
    const status = make('p', { class: 'scene-controls__status', role: 'status', 'data-scene-controls-status': '' });
    const list = make('ol', { class: 'scene-controls__list', 'data-scene-controls-list': '' });
    const navigation = make('div', { class: 'scene-controls__pagination' });
    const previous = button('Previous elements', { 'data-scene-controls-previous': '' }, () => { page--; render(); });
    const next = button('More elements', { 'data-scene-controls-next': '' }, () => { page++; render(); });
    const position = make('span', { 'data-scene-controls-page': '' });
    navigation.append(previous, position, next);
    const inspector = make('div', { class: 'scene-controls__inspector', 'data-scene-controls-inspector': '' });
    panel.append(toolbar, status, list, navigation, inspector); host.replaceChildren(panel);

    const kindName = owner => t(kinds[sceneControlKind(owner)] || 'Element');
    const ownerName = owner => owner.name || `${kindName(owner)} ${owner.ordinal || ''}`.trim();
    const stateName = owner => owner.state == null ? '' : t(owner.kind === 'torch'
        ? { on: 'Turned', off: 'Normal' }[owner.state] || owner.state
        : { open: 'Opened', closed: 'Closed', locked: 'Locked', on: 'Activated', off: 'Deactivated', empty: 'Empty', occupied: 'Occupied' }[owner.state] || owner.state);
    const locked = () => loading || busy || failed || !scene;

    function setCatalog(value) {
        catalog = value && typeof value === 'object' ? value : { elements: [] };
        if (!sceneControlRows(catalog).some(owner => owner.id === selected)) selected = undefined;
    }
    function setScene() {
        const current = getSceneId();
        if (current === scene) return;
        nativeEditor?.close(true); nativeEditor = undefined;
        sceneLifetime.abort(); sceneLifetime = new AbortController(); read?.abort(); ticket++;
        materialChoices.clear();
        scene = current; selected = undefined; page = 0; catalog = { elements: [], assets: [] }; failed = false; notice = ''; noticeError = false; busy = false;
    }
    function checkbox(owner, key, label, action) {
        const row = make('label', { class: 'scene-controls__check' });
        const input = make('input', { type: 'checkbox', 'data-scene-controls-flag': action });
        input.checked = owner[key]; input.disabled = locked();
        listen(input, 'change', () => void apply(action, owner, input.checked));
        row.append(input, make('span', {}, t(label))); return row;
    }
    function inspect() {
        inspector.replaceChildren();
        const owner = sceneControlRows(catalog).find(row => row.id === selected);
        if (!owner) { inspector.append(make('p', { class: 'scene-controls__hint' }, t('Choose an element to control it.'))); return; }
        const head = make('div', { class: 'scene-controls__head' });
        head.append(make('strong', { translate: 'no' }, ownerName(owner)), make('span', { class: 'scene-controls__kind' }, kindName(owner)));
        const tools = make('div', { class: 'scene-controls__tools' });
        if (locate && owner.point) tools.append(button('Show element on the map', { 'data-scene-controls-locate': '' }, () => locate(owner)));
        if (owner.editable && edit) tools.append(button('Edit behavior', { 'data-scene-controls-edit': '' }, () => void child(edit, owner)));
        if (owner.editable && onTest) tools.append(button('Test behavior', { 'data-scene-controls-test': '' }, () => void child(onTest, owner)));
        if (owner.nativeKind) tools.append(button('Edit settings', { 'data-scene-controls-settings': '' }, () => void child(editSettings, owner)));
        for (const node of tools.querySelectorAll('button')) node.disabled = locked();
        inspector.append(head, tools, make('p', { class: 'scene-controls__hint' }, t('Changes apply to the live scene.')));
        const actions = make('div', { class: 'scene-controls__actions' });
        for (const item of sceneControlActions(owner)) {
            const action = button(item.label, { 'data-scene-controls-action': item.action, ...(item.value === undefined ? {} : { 'data-scene-controls-value': String(item.value) }) },
                () => void apply(item.action, owner, item.value));
            action.disabled = locked() || item.disabled === true; actions.append(action);
        }
        inspector.append(actions);
        if (['door', 'lever', 'torch'].includes(owner.kind) && typeof owner.interactionEnabled === 'boolean')
            inspector.append(checkbox(owner, 'interactionEnabled', 'Player interaction', 'interaction'));
        if (owner.kind === 'region' && typeof owner.enabled === 'boolean')
            inspector.append(checkbox(owner, 'enabled', 'Region active', 'region'));
        if (owner.nativeKind) inspector.append(checkbox(owner, 'enabled', 'Enabled', 'enabled'));
        if (!owner.empty && (owner.surfaceKind || owner.assetId) && ['door', 'lever', 'torch', 'image'].includes(owner.kind)) {
            const materialRow = make('div', { class: 'scene-controls__material' });
            const label = make('label'), material = make('select', { 'data-scene-controls-material': '', 'aria-label': t('Choose a material') });
            label.append(make('span', {}, t('Material')), material);
            material.append(make('option', { value: '' }, t('Choose a material')));
            for (const asset of catalog.materials || catalog.assets || []) material.append(make('option', { value: asset.id, translate: 'no' }, asset.name));
            material.value = materialChoices.get(owner.id) ?? owner.materialId ?? ''; material.disabled = locked();
            const applyButton = button('Apply material', { 'data-scene-controls-apply-material': '' }, () => void apply('appearance', owner, material.value));
            applyButton.disabled = locked() || !material.value;
            listen(material, 'change', () => { materialChoices.set(owner.id, material.value); applyButton.disabled = locked() || !material.value; });
            const restore = button('Restore original appearance', { 'data-scene-controls-restore-material': '' }, () => void apply('appearance', owner, null));
            restore.disabled = locked() || !(owner.materialId || owner.appearanceOverride);
            materialRow.append(label, applyButton, restore); inspector.append(materialRow);
        }
    }
    function render() {
        if (disposed) return;
        const focused = panel.contains(document.activeElement) ? document.activeElement?.dataset.sceneControlsElement : undefined;
        const result = sceneControlPage(catalog, { query: search.value, type: types.value, page }); page = result.page;
        list.replaceChildren(...result.rows.map(owner => {
            const row = make('li');
            const select = button('Inspect element', { class: 'scene-controls__element', 'data-scene-controls-element': owner.id, 'aria-pressed': String(owner.id === selected) }, () => {
                selected = owner.id; render();
            });
            select.replaceChildren(make('strong', { translate: 'no' }, ownerName(owner)), make('span', {}, [kindName(owner), stateName(owner),
                typeof owner.visible === 'boolean' ? t(owner.visible ? 'Visible' : 'Hidden') : '',
                owner.nativeKind ? t(owner.enabled ? 'Enabled' : 'Disabled') : ''].filter(Boolean).join(' · ')));
            row.append(select); return row;
        }));
        previous.disabled = loading || page === 0; next.disabled = loading || page + 1 >= result.pages;
        navigation.hidden = result.pages < 2;
        position.textContent = t('Page {0} of {1}', { 0: page + 1, 1: result.pages });
        refreshButton.disabled = loading || busy || !scene;
        panel.setAttribute('aria-busy', String(loading || busy));
        status.textContent = notice || t(!scene ? 'Open a scene to see its automation.' : failed ? 'Could not load scene controls.' : loading ? 'Loading scene controls...' : !result.total ? 'No matching elements.' : '{0} elements', { 0: result.total });
        panel.classList.toggle('is-inspecting', !!selected);
        status.classList.toggle('is-error', failed || noticeError); inspect();
        if (focused) list.querySelector(`[data-scene-controls-element="${CSS.escape(focused)}"]`)?.focus({ preventScroll: true });
    }
    async function child(callback, owner) {
        if (locked() || currentChild) return;
        currentChild = true;
        try { await callback(owner); }
        catch (error) { if (!disposed) { notice = t(error.message || 'Could not load scene controls.'); noticeError = true; render(); } }
        finally { currentChild = false; }
    }
    async function updateNative(owner, item, presets, ownScene) {
        if (disposed || ownScene !== getSceneId()) throw new Error('This scene changed.');
        const data = sceneNativePayload(owner, item, presets);
        try {
            await window.gravewrightRealtime.mapCommand('objects', { mapId: ownScene, area: owner.nativeKind, action: 'update', data });
            if (!disposed && ownScene === getSceneId()) { onChange?.(); await refresh(); }
        } catch (error) {
            // Refresh after CAS or an uncertain acknowledgement without replaying the edit.
            if (!disposed && ownScene === getSceneId()) await refresh();
            throw error;
        }
    }
    async function editSettings(owner) {
        if (nativeEditor || disposed) return;
        const ownScene = scene;
        const [{ openBuilderNativeEditor }, { shaderPresets }] = await Promise.all([import('./builder-editors.js'), import('./builder-catalog.js')]);
        if (disposed || ownScene !== getSceneId()) return;
        nativeEditor = openBuilderNativeEditor({ kind: owner.nativeKind, item: sceneNativeItem(owner), t,
            onSave: item => updateNative(owner, item, shaderPresets, ownScene),
            onClose: () => { nativeEditor = undefined; if (!disposed && ownScene === getSceneId()) void refresh(); } });
    }
    async function refresh() {
        if (disposed) return;
        setScene(); read?.abort(); read = new AbortController();
        const ownScene = scene, ownRead = read, id = ++ticket;
        loading = !!scene; failed = false; render();
        if (!scene) return;
        try {
            const result = await load(scene, ownRead.signal);
            if (disposed || ownScene !== getSceneId() || id !== ticket) return;
            setCatalog(result); notice = ''; noticeError = false; failed = false;
        } catch (error) {
            if (disposed || ownScene !== getSceneId() || id !== ticket || ownRead.signal.aborted) return;
            failed = true; notice = t(error.message || 'Could not load scene controls.');
        } finally { if (!disposed && ownScene === getSceneId() && id === ticket) { loading = false; render(); } }
    }
    async function apply(action, owner, value) {
        if (locked() || scene !== getSceneId()) return;
        const ownScene = scene, commandSignal = sceneLifetime.signal;
        busy = true; notice = ''; noticeError = false; render();
        try {
            if (action === 'enabled' && owner.nativeKind) {
                const { shaderPresets } = await import('./builder-catalog.js');
                await updateNative(owner, { ...sceneNativeItem(owner), enabled: value }, shaderPresets, ownScene);
                return;
            }
            await control(action, owner, value, commandSignal);
            if (disposed || ownScene !== getSceneId()) return;
            if (action === 'appearance') materialChoices.delete(owner.id);
            onChange?.(); await refresh();
        } catch (error) {
            if (disposed || ownScene !== getSceneId() || commandSignal.aborted) return;
            // A missing acknowledgement may follow a committed command. Refresh without repeating it.
            await refresh(); notice = t(error.message || 'Could not apply scene control.'); noticeError = true;
        } finally { if (!disposed && ownScene === getSceneId()) { busy = false; render(); } }
    }
    function translate() {
        search.placeholder = t('Search scene elements'); search.setAttribute('aria-label', t('Search scene elements'));
        types.setAttribute('aria-label', t('Element type'));
        for (const option of types.options) option.textContent = t(kinds[option.value]);
        refreshButton.textContent = t('Refresh'); previous.textContent = t('Previous elements'); next.textContent = t('More elements');
        panel.setAttribute('aria-label', t('Scene controls')); render();
    }
    listen(search, 'input', () => { page = 0; render(); }); listen(types, 'change', () => { page = 0; render(); });
    translate();
    return { refresh, translate, update(value) { setScene(); ticket++; read?.abort(); setCatalog(value); failed = false; loading = false; notice = ''; noticeError = false; render(); },
        destroy() { disposed = true; ticket++; nativeEditor?.close(true); read?.abort(); sceneLifetime.abort(); lifetime.abort(); panel.remove(); } };
}
