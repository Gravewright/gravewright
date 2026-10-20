import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { mountViewport } from './viewport.js';
import { mountModal } from '/static/gravewright_table/modal.js';
import { createAutosave } from './autosave.js';
import { createFloorPainter } from './floor-painter.js';
import { createTerrainPainter } from './terrain-painter.js';
import { createTerrainMaskCache } from './terrain-render.js';
import { createWallArtCache } from './wall-art.js';
import { createWallControls } from './wall-controls.js';
import { addWall, snapWallPoint } from './wall-edit.js';
import { wallProperties, nativeWallProperties, wallPropertyFields } from './wall-properties.js';
import { attachTorch, torchChildren, torchOwner, torchComponentState, torchSourcePoint } from './torch-model.js';
import { createRegion, configurePressurePlate, regionInstance, normalizeRegionFilters } from './region-model.js';
import { createRegionFilterControls } from './region-filter-ui.js';
import { wallJoinGeometry } from './wall-joins.js';
import { openBlueprintEditor } from './blueprint-editor.js';
import { openSceneNetwork } from './scene-network.js';
import { openPlaytest } from './playtest.js';
import { projectTestDocument } from './playtest-model.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';
import { openUniversalVtt } from '../universal-vtt.js';
import { openReadyMapImport } from './ready-map.js';
import { blueprintAppearance } from './blueprint-model.js';
import { detachDocumentAsset, sameDocument } from './asset-removal.js';
import { mountNativeEffects } from './native-effects.js';
import { isNativeKind, nativeFactory, nativeCatalog, presetName, renderNativeLibrary, renderNativeProperties } from './native-controls.js';
import { layerContents, layerSummaries, mergeLayerDown, moveSelectionToLayer, reorderLayer, duplicateLayer } from './layer-model.js';
import { clone, clamp, round, length, newDocument, normalizeDocument, nearestWall, doorFits, doorSegment, wallSegments, removeObject, fitsBounds, history,
    objectKinds, translateSelection, rotateSelection, doorRotationPoint, doorDisplaySegment, duplicateSelection, updateTorchGeometry, objectsInRectangle, familyAssetIds, sampleAssetId, snapWallSegment, floorBrushCells, sampleFloor,
    floorShapeRings, floorFreeContours, floorContainsPoint, documentEditingMode, setEditingMode, setDynamicSurface,
    setBackgroundImage } from './model.js';

const root = document.querySelector('[data-map-builder]');
const svgNS = 'http://www.w3.org/2000/svg';
const strings = {
    select: 'Select an object to edit its properties.',
    floor: 'Drag to paint the floor.',
    wall: 'Drag between two points to draw a wall.',
    door: 'Drag between two points to draw a door.',
    decoration: 'Click or drag to place a decorative object.',
    light: 'Click to place a light.',
    particle: 'Click to place a particle emitter.',
    shader: 'Click to place a shader effect.',
    region: 'Drag to draw a region. Configure its presence triggers in Selection.',
    erase: 'Click an object to erase it.',
    pan: 'Drag to pan. Scroll to zoom.',
};
let retained, retainedUndo;
function mountWorkspace(root) {
    const translator = createTranslator(), t = (key, params) => translator.t(key, params);
    const abort = new AbortController(), { signal } = abort;
    const $ = selector => root.querySelector(selector);
    const form = $('[data-builder-form]'), viewport = $('[data-builder-viewport]'), quickName = $('[data-builder-quick-name]');
    const quickBrushSize = $('[data-builder-quick-brush-size]');
    const base = `/api/containers/${root.dataset.campaignId}/map-builder`;
    const originalFolder = root.dataset.folderId || null;
    const legacyDraftKey = 'gravewright.map-builder.draft.' + root.dataset.campaignId;
    const draftPrefix = legacyDraftKey + '.', latestDraftKey = draftPrefix + 'latest';
    let recovered, recoveryError;
    try {
        const legacy = JSON.parse(sessionStorage.getItem(legacyDraftKey));
        if ([1, 2, 3].includes(legacy?.document?.schemaVersion) && typeof legacy.id === 'string') {
            if (!sessionStorage.getItem(draftPrefix + legacy.id)) sessionStorage.setItem(draftPrefix + legacy.id, JSON.stringify(legacy));
            if (!sessionStorage.getItem(latestDraftKey)) sessionStorage.setItem(latestDraftKey, legacy.id);
            sessionStorage.removeItem(legacyDraftKey);
        }
        const requested = root.dataset.projectId;
        const draft = JSON.parse(sessionStorage.getItem(draftPrefix + (requested || sessionStorage.getItem(latestDraftKey))));
        if ([1, 2, 3].includes(draft?.document?.schemaVersion) && (requested ? draft.id === requested : (draft.folderId || null) === originalFolder)) {
            const document = normalizeDocument(draft.document);
            const saved = draft.saved ? JSON.stringify(normalizeDocument(JSON.parse(draft.saved))) : '';
            recovered = { ...draft, document, saved, pending: new Map(draft.pending || []) };
        }
    } catch (cause) {
        // Keep an unreadable legacy draft in storage so recovery never discards its objects.
        if (cause instanceof TypeError) recoveryError = cause.message;
    }
    const restored = Boolean(retained);
    const state = retained || recovered || { document: newDocument(t('Untitled map'), { layerName: t('Layer 1') }), id: crypto.randomUUID(), version: 0,
        folderId: originalFolder, assets: [], projects: [], saved: '', selection: null, tool: 'wall', role: 'wall',
        selectedAssets: { floor: null, wall: null, door: null }, grid: true, snap: true, limits: {}, pending: new Map() };
    if (!state.saved && !restored && !recovered) state.saved = JSON.stringify(state.document);
    state.sidebarTab = 'library';
    state.category ||= ['wall', 'door'].includes(state.tool) ? 'structure' : 'terrain';
    state.layers = Object.fromEntries(objectKinds.map(kind => [kind, true]));
    state.nativeChoices = { light: 'none', particle: 'smoke', shader: 'orb-1', ...state.nativeChoices };
    state.effectLibraryTool = ['particle', 'shader'].includes(state.effectLibraryTool) ? state.effectLibraryTool
        : ['particle', 'shader'].includes(state.tool) ? state.tool : 'particle';
    state.libraryCollection = typeof state.libraryCollection === 'string' ? state.libraryCollection : '';
    state.selectedAssets = { decoration: null, ...state.selectedAssets };
    state.selectedFamilies = { floor: null, wall: null, door: null, decoration: null, ...state.selectedFamilies };
    state.paintMode ||= 'brush';
    state.paintOperation ||= 'paint';
    state.brushShape ||= 'square';
    state.samplingFloor = false;
    state.soloLayer = state.document.layers.some(layer => layer.id === state.soloLayer) ? state.soloLayer : null;
    if (!['floor', 'wall', 'door', 'decoration', 'light', 'effect'].includes(state.libraryRole)) state.libraryRole = 'floor';
    state.libraryFilter = state.libraryRole;
    state.libraryCollapsed = Boolean(state.libraryCollapsed);
    state.selections ||= state.selection ? [state.selection] : [];
    state.assetRemovals = Array.isArray(state.assetRemovals) ? state.assetRemovals.filter(id => typeof id === 'string') : [];
    state.activeLayer ||= state.document.layers[0]?.id || null;
    state.expandedLayers = Array.isArray(state.expandedLayers) ? state.expandedLayers : [];
    state.snapStep ||= .5;
    state.brush = { thickness: .2, floorSize: 1, rotation: 0, width: 1, height: 1,
        lightRadius: 2, lightDimRadius: 4, lightColor: '#ffd8a8', lightIntensity: .85,
        lightAnimation: 'none', lightAngle: 360, lightRotation: 0, lightElevation: 0, ...state.brush };
    // Recover Tiles tool preferences from drafts created by the former two-mode editor.
    if (state.editingToolMode === 'paint') {
        const tools = state.modeTools?.tiles || { tool: 'floor', paintMode: 'brush', operation: 'paint', shape: 'square', size: 1 };
        state.tool = tools.tool; state.paintMode = tools.paintMode; state.paintOperation = tools.operation;
        state.brushShape = tools.shape; state.brush.floorSize = tools.size;
        state.category = state.tool === 'floor' ? 'terrain' : ['wall', 'door'].includes(state.tool) ? 'structure' : 'decoration';
    }
    delete state.paintBrush; delete state.modeTools; delete state.editingToolMode;
    state.terrainBrush = { size: 3, hardness: .5, intensity: .35, ...state.terrainBrush };
    state.tileBrushSize ??= state.brush.floorSize;
    if (state.snap) state.tileBrushSize = clamp(Math.round(state.tileBrushSize), 1, 20);
    let displayedMode = documentEditingMode(state.document);
    state.brush.floorSize = displayedMode === 'paint' ? state.terrainBrush.size : state.tileBrushSize;
    if (displayedMode === 'paint') state.paintMode = 'brush';
    state.preview = Boolean(state.preview);
    retained = state;
    const terrainMode = () => documentEditingMode(state.document) === 'paint';
    const floorSnap = () => !terrainMode() && state.snap;
    const undo = retainedUndo || history(state.document); retainedUndo = undo;
    let busy = false, gesture, brushResize, disposed = false, csrf, discardDraft = false;
    let autosave, autosaveEpoch = 0, projectWrite, ready = false, bootstrapFailed = false, saveBarrier = false, lastFailure;
    let filterActorCatalog;
    const filterTokenCatalogs = new Map();
    let camera, drawerTrigger, activeModal, floorPainter, terrainPainter, nativeEffects, draggedLayer, wallControls, openingNativeEditor = false;
    const panelScroll = new Map();
    const terrainMasks = createTerrainMaskCache();
    let terrainPreviewFrame, terrainPreview, testPreviewRefresh;
    function clearTerrainPreview() {
        if (terrainPreviewFrame !== undefined) cancelAnimationFrame(terrainPreviewFrame);
        terrainPreviewFrame = terrainPreview = undefined;
    }
    const wallPatterns = new Map([...root.querySelectorAll('[data-wall-texture]')].map(pattern => [pattern.dataset.wallTexture, pattern]));
    let wallMeshes = new Map(), wallMeshError;
    const wallArt = createWallArtCache({
        onError: asset => notify(t('Could not load wall artwork: {name}.', { name: assetName(asset) }), [], 'error'),
        onReady: id => {
            if (disposed) return;
            const items = new Map(state.document.walls.filter(item => item.assetId === id).map(item => [item.id, item]));
            for (const element of $('[data-builder-walls]').children) {
                const item = items.get(element.dataset.objectId);
                if (item) element.replaceWith(objectNode('walls', item));
            }
            renderLayerVisibility();
            if (gesture?.tool === 'wall' && gesture.assetId === id) ghost();
            testPreviewRefresh?.();
        },
    });
    const kindName = kind => ({ floors: 'Floor', walls: 'Wall', doors: 'Door', decorations: 'Decorative object', lights: 'Light', particles: 'Particles', shaders: 'Shader', regions: 'Region' })[kind];
    const roleForKind = kind => kind === 'decorations' ? 'decoration' : kind.slice(0, -1);
    const kindForTool = tool => tool === 'decoration' ? 'decorations' : tool + 's';
    const allRefs = () => objectKinds.flatMap(kind => (state.document[kind] || []).map(item => ({ kind, id: item.id })));
    const itemFor = ref => ref && state.document[ref.kind]?.find(item => item.id === ref.id);
    const elementLabel = (kind, item, authored = true) => {
        if (authored && item.name) return item.name;
        if (item.empty) return t('Empty Object');
        const asset = assetById(item.assetId);
        return asset ? assetName(asset) : t(item.torch ? 'Torch' : item.lever ? 'Lever'
            : item.brush?.operation === 'erase' ? 'Erase stroke' : kindName(kind));
    };
    const isSmartDecoration = item => Boolean(item?.lever || item?.torch);
    const hasNativeEditor = kind => isNativeKind(kind) || kind === 'walls' || kind === 'doors';
    const layerFor = item => state.document.layers.find(layer => layer.id === item.layerId);
    const layerVisible = layer => Boolean(layer?.visible && (!state.soloLayer || state.soloLayer === layer.id));
    const editable = ref => {
        const item = itemFor(ref), layer = item && layerFor(item);
        return Boolean(item && state.layers[ref.kind] && layerVisible(layer) && !layer.locked);
    };
    function setSelection(refs) {
        const items = new Map(), layers = new Map(state.document.layers.map(layer => [layer.id, layer])), seen = new Set();
        if (refs.length) for (const kind of objectKinds) for (const item of state.document[kind] || []) items.set(`${kind}:${item.id}`, item);
        state.selections = refs.filter(ref => {
            const key = `${ref.kind}:${ref.id}`, item = items.get(key), layer = item && layers.get(item.layerId);
            if (seen.has(key) || !state.layers[ref.kind] || !layerVisible(layer) || layer.locked) return false;
            seen.add(key); return true;
        });
        state.selection = state.selections.at(-1) || null;
    }
    function selectionRefs() {
        setSelection(state.selections);
        return state.selections;
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
    function svg(tag, attrs = {}) {
        const element = document.createElementNS(svgNS, tag);
        for (const [key, value] of Object.entries(attrs)) if (value !== undefined) element.setAttribute(key, value);
        return element;
    }
    function notify(message, actions = [], tone = '', source = '') {
        const banner = $('[data-builder-notice]');
        banner.hidden = false; banner.dataset.tone = tone; banner.dataset.source = source;
        $('[data-builder-notice-text]').textContent = message;
        const buttons = $('[data-builder-notice-actions]'); buttons.replaceChildren();
        for (const [label, callback] of actions) {
            const button = node('button', { type: 'button' }, t(label));
            button.addEventListener('click', () => { if (!busy) callback(); }, { signal }); buttons.append(button);
        }
    }
    function hideNotice() { $('[data-builder-notice]').hidden = true; }
    const dirty = () => state.saved !== JSON.stringify(state.document);
    function rememberDraft() {
        try {
            const key = draftPrefix + state.id;
            if (!discardDraft && (dirty() || state.pending.size || state.saveAttempt || state.assetRemovals.length)) {
                sessionStorage.setItem(key, JSON.stringify({ ...state, assets: [], projects: [], pending: [...state.pending] }));
                sessionStorage.setItem(latestDraftKey, state.id);
            } else {
                sessionStorage.removeItem(key);
                if (sessionStorage.getItem(latestDraftKey) === state.id) sessionStorage.removeItem(latestDraftKey);
            }
        } catch { /* No destructive action depends on browser storage succeeding. */ }
    }
    function updateSaveState() {
        const status = state.recoveryConflict ? 'conflict' : bootstrapFailed ? 'blocked' : autosave?.state.status;
        const failed = ['error', 'conflict', 'blocked'].includes(status);
        const saving = status === 'saving';
        const pending = dirty() || status === 'pending' || Boolean(state.saveAttempt);
        $('[data-builder-save-state]').textContent = busy ? t('Working…') : failed ? t(status === 'error' ? 'Autosave failed' : 'Autosave paused')
            : saving ? t('Saving…') : pending ? t('Waiting to save…') : state.version ? t(state.sceneId ? 'Project saved' : 'Saved') : t('Not saved');
        $('[data-builder-save-state]').title = state.sceneId
            ? t('Edits save to the project. Update the scene to apply them in the game.') : '';
        $('[data-builder-undo]').disabled = busy || state.preview || !undo.canUndo;
        $('[data-builder-redo]').disabled = busy || state.preview || !undo.canRedo;
        root.dataset.saveState = busy ? 'working' : failed ? status : saving ? 'saving' : pending ? 'unsaved' : state.version ? 'saved' : 'new';
        projectMetadata({ sceneId: state.sceneId, sceneVersion: state.sceneVersion, canUpdate: state.canUpdate });
    }
    const projectKey = (document, id = state.id, folderId = state.folderId) => JSON.stringify([id, folderId, document]);
    function startAutosave() {
        autosave?.dispose();
        const epoch = ++autosaveEpoch;
        autosave = createAutosave({
            initialKey: state.version && state.saved ? projectKey(JSON.parse(state.saved)) : null,
            pendingSnapshot: state.saveAttempt,
            read: () => ({ key: projectKey(state.document), payload: {
                id: state.id, expected_version: state.version, folder_id: state.folderId, document: state.document,
            } }),
            canSave: () => ready && !disposed && !state.recoveryConflict && (!busy || saveBarrier) && !gesture && !brushResize
                && !floorPainter?.active && !floorPainter?.polygon && !terrainPainter?.active && !wallControls?.active
                && !state.assetRemovals.length && form.checkValidity() && selectionFieldsValid(),
            save: snapshot => {
                const job = (async () => {
                    const { id, ...payload } = snapshot.payload;
                    state.saveAttempt = clone(snapshot); rememberDraft();
                    let result;
                    try { result = await operation('/projects/' + id, payload); }
                    catch (cause) {
                        // Validation and revision rejection did not commit this snapshot.
                        // Uncertain transport failures must retain its body and receipt.
                        if ((cause.status === 400 || cause.conflict) && !disposed && epoch === autosaveEpoch && state.id === id) {
                            state.saveAttempt = null; rememberDraft();
                        }
                        throw cause;
                    }
                    if (disposed || epoch !== autosaveEpoch || state.id !== id) return result.project;
                    state.version = result.project.version;
                    // A response acknowledges its own snapshot. Keep newer edits,
                    // focused controls, object references and the undo stack intact.
                    state.saved = JSON.stringify(payload.document);
                    state.saveAttempt = null;
                    projectMetadata(result.project); updateURL(); rememberDraft();
                    state.projects = [{ id, name: result.project.document.name, version: state.version, updatedAt: result.project.updatedAt },
                        ...state.projects.filter(item => item.id !== id)];
                    renderProjects(); updateSaveState();
                    return result.project;
                })();
                projectWrite = job;
                return job.finally(() => { if (projectWrite === job) projectWrite = null; });
            },
            onState: value => {
                if (disposed || epoch !== autosaveEpoch) return;
                updateSaveState(); rememberDraft();
                if (value.status === 'conflict') notify(value.error.message, [
                    ['Reload saved project', () => openProject(state.id)], ['Save a copy', saveCopy],
                ], 'error', 'autosave');
                else if (value.status === 'blocked' || value.status === 'error' && !value.retrying) notify(
                    value.status === 'blocked' ? value.error.message : t('Could not save automatically. Your changes are kept in this tab.'),
                    [['Retry', () => { autosave.retry(); void autosave.flush().catch(() => {}); }]], 'error', 'autosave');
                else if (value.status === 'saved' && $('[data-builder-notice]').dataset.source === 'autosave') hideNotice();
            },
        });
    }
    function setBusy(value) {
        busy = value; root.setAttribute('aria-busy', String(value));
        for (const element of root.querySelectorAll('button,input,select,textarea')) element.disabled = value;
        if (!value) applyPreviewControls();
        updateSaveState();
    }
    async function api(path = '', body, method = body ? 'POST' : 'GET') {
        if (body && !csrf) {
            const endpoint = document.querySelector('meta[name="gravewright-csrf-url"]')?.content || '/__gravewright/csrf';
            const response = await fetch(endpoint, { credentials: 'same-origin', cache: 'no-store', signal });
            if (!response.ok) {
                const cause = new Error(t('Request failed ({status}).', { status: response.status })); cause.status = response.status; throw cause;
            }
            csrf = await response.json();
        }
        const response = await fetch(path.startsWith('/api/') ? path : base + path, { method, credentials: 'same-origin', cache: 'no-store', signal,
            headers: { ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}), ...(body ? { [csrf.header]: csrf.token } : {}) },
            ...(body ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}) });
        let result;
        try { result = await response.json(); } catch {
            const cause = new Error(t('Request failed ({status}).', { status: response.status })); cause.retryable = true; throw cause;
        }
        if (!response.ok) {
            const cause = new Error(t(result.error || 'Request failed ({status}).', { status: response.status }));
            cause.status = response.status; cause.conflict = response.status === 409; throw cause;
        }
        return result;
    }
    async function operation(path, payload) {
        const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(payload)));
        const key = path + ':' + Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
        if (!state.pending.has(key)) state.pending.set(key, crypto.randomUUID());
        rememberDraft();
        try {
            const result = await api(path, { ...payload, request_id: state.pending.get(key) });
            state.pending.delete(key); rememberDraft(); return result;
        } catch (cause) {
            if (cause.status === 400 || cause.conflict) { state.pending.delete(key); rememberDraft(); }
            throw cause;
        }
    }
    async function loadFilterCatalog(refresh = false) {
        const sceneId = state.sceneId || null, campaign = `/api/containers/${root.dataset.campaignId}`;
        if (refresh) { filterActorCatalog = null; if (sceneId) filterTokenCatalogs.delete(sceneId); }
        filterActorCatalog ||= api(`${campaign}/actors`).then(result => result.actors || []);
        if (sceneId && !filterTokenCatalogs.has(sceneId)) filterTokenCatalogs.set(sceneId,
            api(`${campaign}/maps/${sceneId}/tokens`).then(result => result.tokens || []));
        const [actors, tokens] = await Promise.all([filterActorCatalog, sceneId ? filterTokenCatalogs.get(sceneId) : Promise.resolve([])]);
        return { actors, tokens };
    }
    async function run(callback) {
        if (busy) return;
        lastFailure = null;
        flushFocusedField(); cancelDrawing(); setBusy(true);
        try { await projectWrite?.catch(() => {}); await callback(); return true; }
        catch (cause) {
            if (cause.name === 'AbortError' || disposed) return;
            lastFailure = cause;
            discardDraft = false;
            if (cause.conflict) notify(cause.message, [
                ['Reload saved project', () => openProject(state.id)], ['Save a copy', saveCopy],
            ], 'error');
            else notify(cause.message, [], 'error');
            return false;
        } finally { if (!disposed) setBusy(false); }
    }
    function setMobilePanel(name) {
        root.dataset.mobilePanel = name === 'inspector' ? 'sidebar' : 'workspace';
        if (name === 'inspector') setSidebarTab('settings');
        else if (name === 'library') { setLibraryCollapsed(false); setSidebarTab('library'); }
        for (const button of root.querySelectorAll('[data-builder-panel]')) button.setAttribute('aria-pressed', String(button.dataset.builderPanel === name));
    }
    function setLibraryCollapsed(value) {
        state.libraryCollapsed = value;
        root.classList.toggle('is-library-collapsed', value);
        for (const button of root.querySelectorAll('[data-builder-library-toggle]')) button.setAttribute('aria-expanded', String(!value));
    }
    function setSidebarTab(name, revealMobile = false) {
        flushFocusedField();
        const drawer = $('.map-builder__library'), content = $('.map-builder__sidebar-content'), launcher = $('.map-builder__layers-toggle');
        const wasHidden = drawer.hidden;
        const previous = state.sidebarTab;
        if (previous !== 'library' && !drawer.hidden) panelScroll.set(previous, content.scrollTop);
        const active = document.activeElement;
        if (name !== 'library' && revealMobile && active instanceof HTMLElement && !drawer.contains(active)) drawerTrigger = active;
        state.sidebarTab = name;
        root.dataset.sidebarTab = name;
        for (const panel of root.querySelectorAll('[data-builder-sidebar-panel]')) panel.hidden = !['library', name].includes(panel.dataset.builderSidebarPanel);
        $('[data-builder-projects-panel]').hidden = name !== 'projects';
        drawer.hidden = name === 'library';
        launcher.inert = !drawer.hidden;
        if (drawer.hidden && drawer.contains(active)) {
            const target = drawerTrigger?.isConnected && !drawer.contains(drawerTrigger) ? drawerTrigger : viewport;
            target.focus({ preventScroll: true });
        }
        const tabs = [...root.querySelectorAll('[data-builder-sidebar-tab][role=tab]')].filter(button => !button.hidden);
        const currentTab = tabs.find(button => button.dataset.builderSidebarTab === name) || tabs[0];
        for (const button of root.querySelectorAll('[data-builder-sidebar-tab]')) {
            button.setAttribute(button.getAttribute('role') === 'tab' ? 'aria-selected' : 'aria-pressed', String(button.dataset.builderSidebarTab === name));
            if (button.getAttribute('role') === 'tab') button.tabIndex = button === currentTab ? 0 : -1;
        }
        launcher.setAttribute('aria-expanded', String(!drawer.hidden));
        launcher.setAttribute('aria-pressed', String(!drawer.hidden));
        if (wasHidden && !drawer.hidden && revealMobile) currentTab.focus({ preventScroll: true });
        for (const button of root.querySelectorAll('[data-builder-library-tab]')) {
            if (button.getAttribute('role') !== 'tab') button.setAttribute('aria-pressed', String(button.dataset.builderLibraryTab === (name === 'projects' ? 'projects' : name === 'library' ? 'assets' : '')));
        }
        renderMaterials();
        if (previous !== name) content.scrollTop = panelScroll.get(name) || 0;
    }
    function libraryTab(name) {
        setSidebarTab(name === 'projects' ? 'projects' : 'library');
        if (name === 'assets') setLibraryCollapsed(false);
    }
    function setCategory(name, chooseTool = true) {
        state.category = name;
        root.dataset.category = name;
        for (const button of root.querySelectorAll('[data-builder-category]')) button.setAttribute('aria-pressed', String(button.dataset.builderCategory === name));
        if (name === 'review') {
            cancelDrawing();
            setSidebarTab('review', true);
            renderReview();
        } else if (chooseTool) {
            setTool(name === 'terrain' ? 'floor' : name === 'decoration' ? (state.tool === 'light' ? 'light' : 'decoration')
                : ['wall', 'door'].includes(state.tool) ? state.tool : 'wall');
            setSidebarTab('library');
        }
    }
    function setTool(name) {
        if (state.preview) return;
        cancelDrawing(); state.samplingFloor = false; state.tool = name; viewport.dataset.tool = name; root.dataset.tool = name;
        if (['particle', 'shader'].includes(name)) state.effectLibraryTool = name;
        // Keep click targets stable while transient floor tiles are replaced.
        // Material picking and object hits use the cell-space geometry below.
        $('[data-builder-floors]').style.pointerEvents = name === 'floor' ? 'none' : '';
        for (const button of root.querySelectorAll('[data-builder-tool]')) {
            button.setAttribute('aria-pressed', String(button.dataset.builderTool === name));
        }
        $('[data-builder-tool-help]').textContent = t(strings[name]);
        const activeTool = $('[data-builder-active-tool]');
        if (activeTool) activeTool.textContent = t({ select: 'Select', floor: 'Floor', wall: 'Wall', door: 'Door', decoration: 'Object', light: 'Light', particle: 'Particles', shader: 'Shader', region: 'Region', erase: 'Erase', pan: 'Pan' }[name]);
        const shortcut = $('[data-builder-active-shortcut]'), key = { select: 'V', floor: 'F', wall: 'W', door: 'D', erase: 'E', pan: 'H' }[name];
        shortcut.hidden = !key; shortcut.textContent = key || '';
        $('[data-builder-panel-tool-help]').textContent = t(strings[name]);
        for (const section of root.querySelectorAll('[data-builder-brush-context]')) {
            section.hidden = section.dataset.builderBrushContext === 'rotation' ? !['floor', 'decoration'].includes(name)
                : section.dataset.builderBrushContext !== (['wall', 'door'].includes(name) ? 'structure' : name);
        }
        const materialContext = $('[data-builder-brush-material-context]');
        if (materialContext) materialContext.hidden = !['floor', 'wall', 'door', 'decoration'].includes(name);
        $('[data-builder-stamp-size]').hidden = name !== 'floor' || state.paintMode !== 'brush';
        $('[data-builder-paint-mode]').title = state.paintMode === 'polygon'
            ? t('Click points, then double-click or press Enter to finish. Esc cancels.') : t('Shape');
        $('[data-builder-stamp-shape]').hidden = name !== 'floor' || state.paintMode !== 'brush';
        $('[data-builder-paint-operation]').value = state.paintOperation;
        renderPaintControls();
        const rotationInput = $('[data-builder-brush=rotation]'); if (rotationInput) rotationInput.step = name === 'floor' ? '90' : '1';
        renderNativeBrush();
        if (['floor', 'wall', 'door', 'decoration', 'light', 'particle', 'shader', 'region'].includes(name)) {
            const category = name === 'floor' ? 'terrain' : ['wall', 'door'].includes(name) ? 'structure' : 'decoration';
            if (state.category !== category) setCategory(category, false);
            state.layers[kindForTool(name)] = true;
            if (isNativeKind(kindForTool(name))) renderAssets();
            else if (name !== 'region') setRole(name, false);
            renderLayerVisibility();
        }
        renderDockTools(); applyPreviewControls(); renderSelection();
    }
    function renderDockTools() {
        const empty = state.tool === 'decoration' && !state.selectedAssets.decoration && !state.selectedFamilies.decoration;
        for (const button of root.querySelectorAll('[data-builder-dock-tool]')) {
            button.setAttribute('aria-pressed', String(button.dataset.builderDockTool === 'empty' ? empty
                : button.dataset.builderDockTool === state.tool));
        }
        for (const button of root.querySelectorAll('[data-builder-role]')) {
            button.setAttribute('aria-pressed', String(!empty && state.tool !== 'region' && button.dataset.builderRole === state.libraryRole));
        }
    }
    function chooseQuickTool(name) {
        if (busy || state.preview) return;
        flushFocusedField();
        if (name === 'paint') {
            state.paintMode = 'brush'; state.paintOperation = 'paint';
            state.libraryRole = 'floor'; state.libraryFilter = 'floor';
            $('[data-builder-paint-mode]').value = 'brush';
            setTool('floor');
        } else setTool(name);
        setSidebarTab('library'); viewport.focus({ preventScroll: true }); rememberDraft();
    }
    function renderPaintControls() {
        const mode = documentEditingMode(state.document), painting = mode === 'paint';
        if (displayedMode !== mode) {
            if (!painting && state.snap) state.tileBrushSize = clamp(Math.round(state.tileBrushSize), 1, 20);
            displayedMode = mode; state.brush.floorSize = painting ? state.terrainBrush.size : state.tileBrushSize;
            state.paintMode = 'brush'; $('[data-builder-paint-mode]').value = 'brush';
        }
        root.dataset.editingMode = mode;
        $('[data-builder-editing-mode]').value = mode;
        $('[data-builder-editing-mode]').disabled = busy || state.preview;
        $('[data-builder-tile-tools]').hidden = painting || state.tool !== 'floor';
        $('[data-builder-stamp-shape]').hidden = painting || state.tool !== 'floor' || state.paintMode !== 'brush';
        $('[data-builder-terrain-controls]').hidden = !painting || state.tool !== 'floor';
        $('[data-builder-terrain-help]').hidden = !painting;
        $('.map-builder__painting-layer').hidden = !['floor', 'wall', 'door', 'decoration', 'light', 'particle', 'shader', 'region'].includes(state.tool);
        $('[data-builder-panel-tool-help]').hidden = !['select', 'erase', 'pan', 'region'].includes(state.tool);
        for (const [field, selector] of [['hardness', '[data-builder-terrain-hardness]'], ['intensity', '[data-builder-terrain-intensity]']]) {
            const input = $(selector);
            if (document.activeElement !== input) input.value = String(Math.round(state.terrainBrush[field] * 100));
            input.disabled = busy || state.preview;
        }
        $('[data-builder-stamp-size]').hidden = state.tool !== 'floor' || state.paintMode !== 'brush';
        $('[data-builder-brush-material-context]').hidden = !['floor', 'wall', 'door', 'decoration'].includes(state.tool);
        $('[data-builder-sample-material]').setAttribute('aria-pressed', String(state.samplingFloor));
        $('[data-builder-polygon-actions]').hidden = painting || state.tool !== 'floor' || state.paintMode !== 'polygon';
        $('[data-builder-polygon-finish]').disabled = busy || state.preview || !floorPainter?.polygon;
        $('[data-builder-polygon-cancel]').disabled = busy || state.preview || !floorPainter?.polygon;
        viewport.classList.toggle('is-sampling', state.samplingFloor);
        const size = $('[data-builder-brush=floorSize]');
        size.min = floorSnap() ? '1' : '.05'; size.step = floorSnap() ? '1' : '.05';
        for (const input of [size, quickBrushSize]) {
            input.min = size.min; input.max = size.max; input.step = size.step;
            if (document.activeElement !== input) input.value = String(state.brush.floorSize);
        }
        quickBrushSize.disabled = busy || state.preview || state.tool !== 'floor' || state.paintMode !== 'brush';
        for (const button of root.querySelectorAll('[data-builder-quick-tool]')) {
            const active = button.dataset.builderQuickTool === 'paint'
                ? state.tool === 'floor' && state.paintMode === 'brush' && state.paintOperation === 'paint' && !state.samplingFloor
                : state.tool === button.dataset.builderQuickTool;
            button.setAttribute('aria-pressed', String(active));
            button.disabled = busy || state.preview;
        }
        $('[data-builder-paint-mode] option[value=fill]').textContent = t(floorSnap() ? 'Bucket fill' : 'Fill shape');
        const snap = $('[data-builder-toggle-snap]');
        snap.setAttribute('aria-pressed', String(state.snap && !(painting && state.tool === 'floor')));
        snap.disabled = busy || state.preview || painting && state.tool === 'floor';
    }
    function adjustBrush(delta) {
        if (busy || state.preview || state.tool !== 'floor') return;
        setFloorBrushSize(floorSnap() ? clamp(Math.round(state.brush.floorSize) + delta, 1, 20)
            : clamp(round(state.brush.floorSize + delta * .1), .05, 20));
    }
    function setFloorBrushSize(value) {
        if (busy || state.preview || !Number.isFinite(value) || value < (floorSnap() ? 1 : .05) || value > 20
            || floorSnap() && !Number.isInteger(value)) return false;
        if (value !== state.brush.floorSize) {
            cancelDrawing(); state.brush.floorSize = value;
            if (terrainMode()) state.terrainBrush.size = value; else state.tileBrushSize = value;
            rememberDraft();
        }
        for (const input of [quickBrushSize, $('[data-builder-brush=floorSize]')]) input.value = String(state.brush.floorSize);
        renderPaintControls(); return true;
    }
    function finishBrushResize(cancelled = false) {
        if (!brushResize) return false;
        const previous = brushResize; brushResize = undefined;
        if (cancelled) state.brush.floorSize = previous.size;
        if (terrainMode()) state.terrainBrush.size = state.brush.floorSize; else state.tileBrushSize = state.brush.floorSize;
        $('[data-builder-ghost]').replaceChildren(); renderPaintControls();
        if (!cancelled) rememberDraft();
        return true;
    }
    function resizeBrush(event) {
        if (!brushResize || !Number.isFinite(event?.clientX)) return;
        const value = brushResize.size + (event.clientX - brushResize.clientX) / 40;
        state.brush.floorSize = floorSnap() ? clamp(Math.round(value), 1, 20) : clamp(Math.round(value * 20) / 20, .05, 20);
        renderPaintControls(); renderBrushCursor(brushResize.point);
        const label = svg('text', { transform: `translate(${brushResize.point.x} ${brushResize.point.y}) scale(${1 / camera.scale})`,
            x: 0, y: 24, 'text-anchor': 'middle', fill: '#fff', stroke: '#10171c', 'stroke-width': 3,
            'paint-order': 'stroke', 'pointer-events': 'none', 'data-builder-resize-preview': '' });
        label.style.fontSize = '12px'; label.textContent = t('{size} cells', { size: state.brush.floorSize });
        $('[data-builder-ghost]').append(label);
    }
    function setSnap(value) {
        cancelDrawing(); state.snap = value; form.elements.snap.checked = value;
        if (value && !terrainMode()) {
            state.brush.floorSize = clamp(Math.round(state.brush.floorSize), 1, 20);
            state.tileBrushSize = state.brush.floorSize;
            $('[data-builder-brush=floorSize]').value = String(state.brush.floorSize);
        }
        renderPaintControls(); renderCanvas(); rememberDraft();
    }
    function chooseEditingMode(value) {
        if (busy || state.preview || !['tiles', 'paint'].includes(value) || value === documentEditingMode(state.document)) return;
        flushFocusedField(); cancelDrawing();
        setEditingMode(state.document, value);
        state.paintMode = 'brush'; state.paintOperation = 'paint'; state.samplingFloor = false;
        renderPaintControls(); setTool('floor'); commit(); renderCanvas(); renderLayers(); renderProperties();
        viewport.focus({ preventScroll: true });
    }
    function chooseEyedropper() {
        if (busy || state.preview) return;
        const wasSampling = state.samplingFloor;
        setTool('floor'); state.samplingFloor = !wasSampling;
        $('[data-builder-tool-help]').textContent = t(state.samplingFloor ? 'Click a floor on the active layer to sample its material.' : strings.floor);
        renderPaintControls();
    }
    function pickFloorMaterial(point) {
        const picked = sampleFloor(state.document, point, { layerId: state.activeLayer });
        if (!picked) { notify(t('There is no floor to sample on the active layer.')); return; }
        state.selectedAssets.floor = picked.assetId; state.selectedFamilies.floor = null;
        state.brush.rotation = picked.rotation || 0; state.paintOperation = 'paint';
        state.samplingFloor = false; state.paintMode = 'brush';
        $('[data-builder-paint-mode]').value = 'brush';
        $('[data-builder-brush=rotation]').value = String(state.brush.rotation);
        setTool('floor'); rememberDraft();
    }
    function setRole(role, changeTool = true) {
        if (role !== 'light') state.role = role;
        if (changeTool) setTool(role);
        else renderAssets();
    }
    function setLibraryRole(role) {
        if (busy || state.preview) return;
        flushFocusedField();
        state.libraryRole = role; state.libraryFilter = role;
        setTool(role === 'effect' ? state.effectLibraryTool : role);
        setSidebarTab('library'); rememberDraft();
    }
    function chooseNativePreset(tool, id, closePanel = false) {
        if (busy || state.preview) return;
        state.nativeChoices[tool] = id;
        if (tool === 'light') {
            const preset = nativeFactory(tool, id);
            Object.assign(state.brush, { lightRadius: preset.brightRadius, lightDimRadius: preset.dimRadius,
                lightColor: preset.color, lightIntensity: preset.intensity, lightAnimation: preset.animation,
                lightAngle: preset.angle, lightRotation: preset.rotation, lightElevation: preset.elevation || 0 });
            for (const input of root.querySelectorAll('[data-builder-brush]')) input.value = String(state.brush[input.dataset.builderBrush]);
        }
        setTool(tool); renderAssets(); setMobilePanel('workspace');
        if (closePanel) setSidebarTab('library');
    }
    function renderNativeBrush() {
        const select = $('[data-builder-native-preset]'); if (!select) return;
        const native = isNativeKind(kindForTool(state.tool));
        select.closest('[data-builder-native-brush]').hidden = !native;
        if (!native) return;
        const tool = state.tool;
        select.replaceChildren(...nativeCatalog(tool).map(preset => new Option(presetName(tool, preset, t), preset.id || preset.kind)));
        select.value = state.nativeChoices[tool];
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
        if (busy || state.preview) return;
        try { if (id) classify(id, role); }
        catch (cause) { renderBrushMaterial(); notify(cause.message, [], 'error'); return; }
        state.selectedAssets[role] = id || null; state.selectedFamilies[role] = null;
        if (id) commit();
        setTool(role); setMobilePanel('workspace');
        if (closePanel) setSidebarTab('library');
    }
    function familyGroups(role) {
        const result = new Map();
        for (const entry of state.document.assets) {
            const asset = assetById(entry.assetId);
            if (!entry.family || !asset || role && entry.role !== role) continue;
            if (!result.has(entry.family)) result.set(entry.family, { name: entry.family, role: entry.role, assets: [] });
            result.get(entry.family).assets.push(asset);
        }
        return [...result.values()].sort((a, b) => a.name.localeCompare(b.name, translator.locale));
    }
    function brushAssetIds(role) {
        const family = state.selectedFamilies[role];
        return family ? familyAssetIds(state.document, role, family).filter(id => assetById(id)) : [state.selectedAssets[role] || null];
    }
    function chooseFamily(name, role = state.role, closePanel = false) {
        if (busy || state.preview || !familyAssetIds(state.document, role, name).length) return;
        state.selectedFamilies[role] = name;
        setTool(role); setMobilePanel('workspace');
        if (closePanel) setSidebarTab('library');
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
            .sort((a, b) => assetName(a).localeCompare(assetName(b), translator.locale));
        const unclassified = state.assets.filter(asset => !roleFor(asset.id))
            .sort((a, b) => assetName(a).localeCompare(assetName(b), translator.locale));
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
                .sort((a, b) => a.localeCompare(b, translator.locale));
            select.replaceChildren(new Option(t('All collections'), ''), ...collections.map(name => new Option(name, name)));
            if (!collections.includes(state.libraryCollection)) state.libraryCollection = '';
            select.value = state.libraryCollection;
        }
        select.disabled = busy || state.preview;
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
        const search = $('[data-builder-search]').value.trim().toLocaleLowerCase(translator.locale);
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
            && assetName(asset).toLocaleLowerCase(translator.locale).includes(search)
            && (!collection?.value || assetInfo(asset.id)?.collection === collection.value));
        for (const role of ['floor', 'wall', 'door', 'decoration']) {
            const id = state.selectedAssets[role];
            if (id && (!assetById(id) || roleFor(id) !== role)) state.selectedAssets[role] = null;
        }
        for (const role of ['floor', 'wall', 'door', 'decoration']) {
            if (state.selectedFamilies[role] && !brushAssetIds(role).length) state.selectedFamilies[role] = null;
        }
        const active = state.selectedAssets[state.role];
        if (state.libraryFilter === 'decoration' && !chosenCollection && t('Empty Object').toLocaleLowerCase(translator.locale).includes(search)) {
            const button = node('button', { type: 'button', class: 'map-builder__asset', 'data-builder-empty-object': '',
                'aria-pressed': String(state.tool === 'decoration' && !active && !state.selectedFamilies.decoration), title: t('Place an Empty Object') });
            const preview = node('span', { class: 'map-builder__empty-preview', 'aria-hidden': 'true' });
            preview.append($('[data-builder-empty-object] svg').cloneNode(true));
            button.append(preview, node('span', {}, t('Empty Object')));
            button.addEventListener('click', () => chooseBrushAsset(null, 'decoration', true), { signal }); container.append(button);
        }
        if (!light) for (const family of familyGroups()) {
            if (state.libraryFilter && family.role !== state.libraryFilter || !family.name.toLocaleLowerCase(translator.locale).includes(search)) continue;
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
        for (const asset of assets.sort((a, b) => roleOrder(a) - roleOrder(b) || assetName(a).localeCompare(assetName(b), translator.locale))) {
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
    function cancelDrawing() {
        finishBrushResize(true);
        terrainPainter?.cancel(); clearTerrainPreview();
        camera?.cancel();
        floorPainter?.cancel();
        wallControls?.cancel();
        $('[data-builder-ghost]').replaceChildren();
        renderPaintControls();
    }
    function openImport(asset = null) {
        if (busy || state.preview || disposed) return;
        cancelDrawing(); flushFocusedField();
        if (activeModal) return;
        const modal = $('[data-builder-import-template]').content.firstElementChild.cloneNode(true);
        const modalForm = modal.querySelector('form'), roleInput = modal.querySelector('[data-builder-import-role]');
        const familyInput = modal.querySelector('[data-builder-import-family]'), filesInput = modal.querySelector('[data-builder-upload]');
        const collectionInput = modal.querySelector('[data-builder-import-collection]'), collections = modal.querySelector('[data-builder-import-collections]');
        const nameInput = modal.querySelector('[data-builder-import-name-input]'), list = modal.querySelector('datalist');
        const remove = modal.querySelector('[data-builder-asset-remove]');
        const alert = modal.querySelector('[role=alert]'), local = new AbortController();
        let working = false, removeModal;
        const completed = new Map();
        const readyMap = modal.querySelector('[data-builder-ready-map]');
        readyMap.hidden = Boolean(asset);
        readyMap.addEventListener('click', () => { modal.close(); openMapImport(); }, { signal: local.signal });
        list.id = 'builder-families-' + crypto.randomUUID(); familyInput.setAttribute('list', list.id);
        collections.id = 'builder-collections-' + crypto.randomUUID(); collectionInput.setAttribute('list', collections.id);
        collections.replaceChildren(...[...new Set(state.document.assets.map(entry => entry.collection).filter(Boolean))]
            .sort((a, b) => a.localeCompare(b, translator.locale)).map(name => new Option(name, name)));
        roleInput.value = asset ? roleFor(asset.id) || state.role : state.role;
        if (asset) {
            remove.hidden = false;
            modal.removeAttribute('data-builder-import-modal'); modal.dataset.builderAssetModal = '';
            modal.querySelector('strong').textContent = t('Edit asset');
            modal.querySelector('[data-builder-import-submit]').textContent = t('Save');
            modal.querySelector('[data-builder-import-files]').hidden = true; filesInput.required = false;
            modal.querySelector('[data-builder-import-name]').hidden = false; nameInput.required = true;
            nameInput.value = assetName(asset); familyInput.value = assetInfo(asset.id)?.family || '';
            collectionInput.value = assetInfo(asset.id)?.collection || '';
        }
        function families() {
            list.replaceChildren(...familyGroups(roleInput.value).map(entry => new Option(entry.name, entry.name)));
            familyInput.setCustomValidity('');
        }
        function close() { if (!working) modal.close(); }
        families();
        roleInput.addEventListener('change', families, { signal: local.signal });
        familyInput.addEventListener('input', () => familyInput.setCustomValidity(''), { signal: local.signal });
        filesInput.addEventListener('change', () => completed.clear(), { signal: local.signal });
        modal.querySelector('[data-builder-import-cancel]').addEventListener('click', close, { signal: local.signal });
        modal.querySelector('[data-builder-import-close]').addEventListener('click', close, { signal: local.signal });
        modal.addEventListener('close', () => { removeModal?.close(true); local.abort(); if (activeModal === modal) activeModal = null; }, { once: true });
        remove.addEventListener('click', () => {
            if (!asset || working || busy || disposed || removeModal) return;
            const confirmation = $('[data-builder-asset-remove-template]').content.firstElementChild.cloneNode(true);
            const issue = confirmation.querySelector('[role=alert]');
            confirmation.querySelector('[data-builder-asset-remove-message]').textContent = t(
                'Remove “{name}” from this campaign? This also removes it from other projects and scenes that use it.', { name: assetName(asset) });
            for (const selector of ['[data-builder-asset-remove-cancel]', '[data-builder-asset-remove-close]']) {
                confirmation.querySelector(selector).addEventListener('click', () => { if (!working) confirmation.close(); }, { signal: local.signal });
            }
            confirmation.addEventListener('close', () => { removeModal = null; }, { once: true });
            confirmation.querySelector('[data-builder-asset-remove-submit]').addEventListener('click', async () => {
                if (working || busy || disposed) return;
                working = true; issue.hidden = true; setBusy(true);
                for (const control of [...modal.querySelectorAll('button,input,select'), ...confirmation.querySelectorAll('button')]) control.disabled = true;
                let removed = false, catalog;
                if (!state.assetRemovals.includes(asset.id)) state.assetRemovals.push(asset.id);
                rememberDraft();
                try {
                    await projectWrite?.catch(() => {});
                    try { await api(`/api/containers/${root.dataset.campaignId}/library/assets/delete`, { asset_id: asset.id }); }
                    catch (cause) {
                        if (cause.name === 'AbortError' || disposed) throw cause;
                        // A lost acknowledgement may follow a committed deletion.
                        // Verify absence before treating a failed request as complete.
                        try { catalog = await api(); } catch { throw cause; }
                        if (catalog.assets.some(row => row.id === asset.id)) {
                            state.assetRemovals = state.assetRemovals.filter(id => id !== asset.id); rememberDraft(); throw cause;
                        }
                    }
                    if (disposed) return;
                    if (!catalog) { try { catalog = await api(); } catch { /* Reconcile again when the catalog can be read. */ } }
                    if (disposed) return;
                    removed = true;
                    await refreshAfterAssetRemoval(catalog);
                } catch (cause) {
                    if (cause.name !== 'AbortError' && !disposed) { issue.textContent = cause.message; issue.hidden = false; }
                } finally {
                    working = false;
                    if (!disposed) {
                        setBusy(false);
                        for (const control of [...modal.querySelectorAll('button,input,select'), ...confirmation.querySelectorAll('button')]) control.disabled = false;
                    }
                }
                if (!disposed) {
                    if (removed) { confirmation.close(); modal.close(); $('[data-builder-import]').focus({ preventScroll: true }); }
                    else confirmation.querySelector('[data-builder-asset-remove-submit]').focus({ preventScroll: true });
                }
            }, { signal: local.signal });
            removeModal = mountModal(confirmation, { nested: true, canClose: () => !working });
            confirmation.querySelector('form').addEventListener('submit', event => event.preventDefault(), { signal: local.signal });
        }, { signal: local.signal });
        modalForm.addEventListener('submit', async event => {
            event.preventDefault();
            if (working || busy || !modalForm.reportValidity()) return;
            const role = roleInput.value, family = familyInput.value.trim(), files = [...filesInput.files];
            const collection = collectionInput.value.trim();
            const conflict = state.document.assets.some(entry => entry.family === family && family && entry.role !== role
                && (!asset || entry.assetId !== asset.id));
            if (conflict) {
                alert.textContent = t('An asset family must contain only one asset type.'); alert.hidden = false;
                familyInput.setCustomValidity(t('An asset family must contain only one asset type.'));
                familyInput.reportValidity(); return;
            }
            if (family.length > 80 || family.includes('\0') || collection.length > 80 || collection.includes('\0')) {
                alert.textContent = t('Invalid map asset metadata.'); alert.hidden = false; return;
            }
            if (asset && assetUsedByOtherRole(asset.id, role)) {
                alert.textContent = t('This asset is already used by another brush. Upload a separate copy to use a different type.'); alert.hidden = false; return;
            }
            if (!asset && files.some(file => file.size > 25 * 1024 * 1024)) {
                alert.textContent = t('Choose an image up to 25 MB.'); alert.hidden = false; return;
            }
            if (!asset && state.document.assets.length + files.length - completed.size > (state.limits.maxAssets || 256)) {
                alert.textContent = t('The map has too many assets.'); alert.hidden = false; return;
            }
            working = true; alert.hidden = true; setBusy(true);
            for (const control of modal.querySelectorAll('button,input,select')) control.disabled = true;
            let imported;
            function metadata(id) {
                classify(id, role, family);
                const entry = assetInfo(id);
                if (family) entry.family = family; else delete entry.family;
                if (collection) entry.collection = collection; else delete entry.collection;
                if (asset) entry.name = nameInput.value.trim();
                commit();
            }
            try {
                if (asset) { metadata(asset.id); imported = asset.id; }
                else {
                    for (const [index, file] of files.entries()) {
                        let id = completed.get(index);
                        if (!id) {
                            const body = new FormData(); body.append('file', file);
                            id = (await api(`/api/containers/${root.dataset.campaignId}/library/upload`, body)).id;
                            completed.set(index, id);
                        }
                        metadata(id); imported = id;
                    }
                    await refreshLibrary();
                }
            } catch (cause) {
                if (cause.name !== 'AbortError' && !disposed) {
                    let message = cause.message;
                    if (completed.size) {
                        try { await refreshLibrary(); }
                        catch (refreshError) { message += '\n' + refreshError.message; }
                    }
                    alert.textContent = message; alert.hidden = false;
                }
                imported = null;
            } finally {
                working = false;
                if (!disposed) {
                    setBusy(false);
                    for (const control of modal.querySelectorAll('button,input,select')) control.disabled = false;
                }
            }
            if (imported && !disposed) {
                state.libraryRole = role; state.libraryFilter = role;
                if (family) chooseFamily(family, role); else chooseBrushAsset(imported, role);
                renderAssets(); renderLayers(); modal.close();
            }
        }, { signal: local.signal });
        activeModal = mountModal(modal, { canClose: () => !working });
    }
    function openMapImport() {
        if (busy || state.preview || disposed || activeModal) return;
        cancelDrawing(); flushFocusedField();
        activeModal = openReadyMapImport({ template: $('[data-builder-map-import-template]'), document: state.document,
            assets: state.assets, limits: state.limits, t,
            upload: async file => {
                const body = new FormData(); body.append('file', file);
                return (await api(`/api/containers/${root.dataset.campaignId}/library/upload`, body)).id;
            },
            apply: async (assetId, geometry) => {
                if (disposed) return;
                if (!assetById(assetId)) await refreshLibrary();
                if (disposed) return;
                if (setBackgroundImage(state.document, assetId, geometry, state.limits)) {
                    commit(); renderForm(); renderCanvas(); renderAssets(); renderLayers(); renderProperties();
                    camera.resize(state.document.columns, state.document.rows, state.document.cellSize);
                }
            },
            onClose: () => { activeModal = null; },
        });
    }
    function detachRemovedAsset(assetId, catalog = null) {
        const available = (catalog?.assets || state.assets).filter(asset => asset.id !== assetId).map(asset => asset.id);
        const availableIds = new Set(available);
        const missing = new Set([assetId, ...state.assets.filter(asset => !availableIds.has(asset.id)).map(asset => asset.id)]);
        const detach = document => {
            const ids = new Set([...missing, ...(document.assets || []).filter(asset => !availableIds.has(asset.assetId)).map(asset => asset.assetId)]);
            return [...ids].reduce((current, id) => detachDocumentAsset(current, id, available), document);
        };
        // The file deletion is permanent; undo still covers unrelated map edits.
        undo.commit(state.document); state.document = undo.rebase(detach);
        state.saved = JSON.stringify(detach(JSON.parse(state.saved)));
        state.assets = state.assets.filter(asset => availableIds.has(asset.id));
        for (const role of Object.keys(state.selectedAssets)) {
            if (!availableIds.has(state.selectedAssets[role])) state.selectedAssets[role] = null;
            if (state.selectedFamilies[role] && !familyAssetIds(state.document, role, state.selectedFamilies[role]).length) state.selectedFamilies[role] = null;
        }
        // Other recovered drafts keep their edits and stale revision guard,
        // while no longer referring to the deleted campaign resource.
        try {
            for (const key of Object.keys(sessionStorage).filter(key => key.startsWith(draftPrefix) && key !== latestDraftKey)) {
                try {
                    const draft = JSON.parse(sessionStorage.getItem(key));
                    if (!draft?.document) continue;
                    draft.document = detach(draft.document);
                    if (draft.saved) draft.saved = JSON.stringify(detach(JSON.parse(draft.saved)));
                    draft.assetRemovals = [...new Set([...(draft.assetRemovals || []), ...missing])];
                    sessionStorage.setItem(key, JSON.stringify(draft));
                } catch { /* Preserve unreadable drafts for recovery. */ }
            }
        } catch { /* Browser storage may be unavailable; current work stays in memory. */ }
        rememberDraft(); renderAssets(); renderCanvas(); renderLayers(); renderProperties(); updateSaveState();
    }
    async function refreshAfterAssetRemoval(catalog = null, { rethrow = false } = {}) {
        try {
            catalog ||= await api();
            if (disposed) return;
            const missing = state.assetRemovals.filter(id => !catalog.assets.some(asset => asset.id === id));
            if (!missing.length) {
                state.assetRemovals = []; rememberDraft();
                await refreshLibrary(catalog); return;
            }
            detachRemovedAsset(missing[0], catalog);
            await refreshLibrary(catalog);
            if (state.version) {
                const { project } = await api('/projects/' + state.id);
                if (disposed) return;
                // Adopt only the revision explained by this asset cleanup.
                // Concurrent project edits still require a reload or a copy.
                if (project.folderId !== state.folderId || !sameDocument(normalizeDocument(project.document), JSON.parse(state.saved))) {
                    const cause = new Error(t('Asset removed, but this project has changed elsewhere. Reload the saved project or save a copy.'));
                    cause.conflict = true; throw cause;
                }
                state.version = project.version; state.saved = JSON.stringify(normalizeDocument(project.document)); projectMetadata(project);
            }
            state.assetRemovals = [];
            rememberDraft(); updateSaveState(); notify(t('Asset removed.'));
        } catch (cause) {
            if (cause.name === 'AbortError' || disposed) return;
            if (rethrow) throw cause;
            if (cause.conflict) notify(cause.message, [
                ['Reload saved project', () => confirmLeave(() => openProject(state.id))], ['Save a copy', saveCopy],
            ], 'error');
            else notify(t('Asset removed, but the editor could not be refreshed. Try again.') + '\n' + cause.message,
                [['Retry', () => run(refreshAfterAssetRemoval)]], 'error');
        }
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
            button.disabled = busy || state.preview || !item || !asset && isSmartDecoration(item);
            button.addEventListener('click', () => {
                if (!item || busy || state.preview) return;
                cancelDrawing();
                const target = selected(); if (!target || target.empty || !asset && isSmartDecoration(target)) return;
                target.assetId = asset?.id || null;
                if (kind === 'floors') delete target.paint;
                state.selectedAssets[role] = target.assetId;
                commit(); renderCanvas(); renderLayers(); renderProperties();
            }, { signal });
            container.append(button);
        }
    }
    function renderLayerVisibility() {
        const layers = new Map(state.document.layers.map(layer => [layer.id, layer]));
        for (const kind of objectKinds) {
            $('[data-builder-' + kind + ']').style.display = state.layers[kind] || state.preview ? '' : 'none';
            const items = new Map((state.document[kind] || []).map(item => [item.id, item]));
            for (const element of $('[data-builder-' + kind + ']').querySelectorAll('[data-object-id], [data-builder-floor-layer]')) {
                const item = items.get(element.dataset.objectId);
                const layer = layers.get(item?.layerId || element.dataset.builderFloorLayer);
                element.style.display = item?.testHidden ? 'none' : state.preview || !layer || layerVisible(layer) ? '' : 'none';
            }
        }
        $('[data-builder-selection]').style.display = state.preview ? 'none' : '';
        updateNativePreview();
    }
    function updateNativePreview(document = state.document) {
        if (!nativeEffects) return;
        const preview = { ...document, layers: document.layers.map(layer => ({ ...layer, visible: state.preview || layerVisible(layer) })) };
        for (const kind of ['lights', 'particles', 'shaders']) preview[kind] = state.preview || state.layers[kind] ? document[kind] || [] : [];
        nativeEffects.update(preview);
    }
    let layerEvents;
    signal.addEventListener('abort', () => layerEvents?.abort(), { once: true });
    function activeLayer(id) {
        if (busy || state.preview || !state.document.layers.some(layer => layer.id === id)) return;
        cancelDrawing(); state.activeLayer = id;
        if (state.soloLayer) state.soloLayer = id;
        setSelection(state.selections); rememberDraft();
        renderCanvas(); renderLayers(); renderProperties();
    }
    function requestFirstLayer() {
        if (busy || state.preview) return;
        setSidebarTab('layers', true);
        $('[data-builder-layer-name]').focus({ preventScroll: true });
    }
    function updateLayerControls() {
        if (!state.document.layers.some(layer => layer.id === state.activeLayer)) state.activeLayer = state.document.layers[0]?.id || null;
        if (state.soloLayer && !state.document.layers.some(layer => layer.id === state.soloLayer)) state.soloLayer = null;
        const summaries = layerSummaries(state.document), current = summaries.find(layer => layer.id === state.activeLayer);
        const select = $('[data-builder-active-layer-select]');
        select.value = state.activeLayer || '';
        select.disabled = busy || state.preview || !current;
        $('[data-builder-active-layer-status]').textContent = current
            ? t(!current.visible ? 'Hidden layer' : current.locked ? 'Locked layer' : '{count} objects', { count: current.count }) : t('No active layer');
        $('[data-builder-layer-total]').textContent = String(summaries.length);
        $('[data-builder-layer-summary]').textContent = current ? t('Painting on: {name}', { name: current.name }) : t('Create a layer to start building your map.');
        $('[data-builder-layers-empty]').hidden = Boolean(summaries.length);
        $('[data-builder-create-first-layer]').hidden = Boolean(summaries.length) || state.preview;
        $('[data-builder-layer-add]').disabled = busy || state.preview || summaries.length >= 32 || !$('[data-builder-layer-name]').value.trim();
        for (const control of root.querySelectorAll('[data-builder-layers-show-all], [data-builder-layers-unlock-all]')) control.disabled = busy || state.preview || !summaries.length;
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
            transfer.disabled = busy || state.preview || !layer.visible || layer.locked || !state.selections.some(ref => itemFor(ref)?.layerId !== layer.id);
            row.querySelector('[data-builder-layer-select]').disabled = busy || state.preview || !layer.visible || layer.locked || !layer.count;
            row.querySelector('[data-builder-layer-merge]').disabled = busy || state.preview || !layer.canMergeDown;
            row.querySelector('[data-builder-layer-remove]').disabled = busy || state.preview || layer.count > 0 || layer.locked;
            row.querySelector('[data-builder-layer-copy]').disabled = busy || state.preview || layer.locked || summaries.length >= 32 || count + layer.count > (state.limits.maxObjects || 2000);
            row.querySelector('[data-builder-layer-drag]').draggable = !busy && !state.preview;
            for (const button of row.querySelectorAll('[data-builder-layer-object]')) {
                const ref = { kind: button.dataset.builderLayerObjectKind, id: button.dataset.builderLayerObject };
                button.disabled = busy || state.preview || !layer.visible || layer.locked || Boolean(state.soloLayer && state.soloLayer !== layer.id);
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
                if (busy || state.preview) { event.preventDefault(); return; }
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
                if (!draggedLayer || busy || state.preview || draggedLayer === layer.id) return;
                event.preventDefault(); event.dataTransfer.dropEffect = 'move';
                for (const element of target.children) delete element.dataset.dropTarget;
                row.dataset.dropTarget = event.clientY < row.getBoundingClientRect().top + row.offsetHeight / 2 ? 'before' : 'after';
            }, listen);
            row.addEventListener('dragleave', event => { if (!row.contains(event.relatedTarget)) delete row.dataset.dropTarget; }, listen);
            row.addEventListener('drop', event => {
                if (!draggedLayer || busy || state.preview) return;
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
                if (busy || state.preview || !name.value.trim()) { name.value = layer.name; return; }
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
                    if (busy || state.preview) return;
                    const value = input.checked; cancelDrawing();
                    const current = state.document.layers.find(item => item.id === layer.id); if (!current) return;
                    current[key] = value;
                    if (key === 'visible' && !value && state.soloLayer === layer.id) state.soloLayer = null;
                    setSelection(state.selections); commit(); refresh(layer.id, 'data-builder-layer-' + key);
                }, listen); actions.append(wrapper);
            }
            const action = (attribute, label, callback, glyph = label) => {
                const button = node('button', { type: 'button', [attribute]: layer.id, 'aria-label': t(label), title: t(label) }, t(glyph));
                button.addEventListener('click', () => { if (!busy && !state.preview) callback(); }, listen);
                actions.append(button); return button;
            };
            const isolate = action('data-builder-layer-solo', 'Isolate layer', () => {
                cancelDrawing(); state.soloLayer = state.soloLayer === layer.id ? null : layer.id;
                state.activeLayer = layer.id; setSelection(state.selections); rememberDraft(); refresh(layer.id, 'data-builder-layer-solo');
            }, 'Solo');
            isolate.setAttribute('aria-pressed', String(state.soloLayer === layer.id)); isolate.disabled = !layer.visible;
            action('data-builder-layer-select', 'Select layer objects', () => {
                cancelDrawing(); setSelection(layerContents(state.document, layer.id, { editable: true }));
                renderSelection(); renderProperties(); updateLayerControls();
            }, 'Select');
            action('data-builder-layer-transfer', 'Move selection to layer', () => {
                cancelDrawing(); const refs = [...selectionRefs()];
                if (!moveSelectionToLayer(state.document, refs, layer.id)) return;
                state.activeLayer = layer.id; if (state.soloLayer) state.soloLayer = layer.id;
                setSelection(refs); commit(); refresh(layer.id, 'data-builder-layer-transfer');
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
                setSelection(merged.moved); commit(); refresh(merged.layerId, 'data-builder-layer-active');
            }, 'Merge down');
            action('data-builder-layer-copy', 'Duplicate layer', () => {
                cancelDrawing();
                const copied = duplicateLayer(state.document, layer.id, t('{name} copy', { name: layer.name }).slice(0, 80));
                if (!copied) { notify(t('The layer cannot be duplicated here. Keep its contents inside the map and avoid overlapping doors.'), [], 'error'); return; }
                state.activeLayer = copied.layerId; if (state.soloLayer) state.soloLayer = copied.layerId;
                state.expandedLayers.push(copied.layerId);
                setSelection(copied.refs); commit(); refresh(copied.layerId, 'data-builder-layer-active');
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
                    const item = itemFor(ref); if (!item) continue;
                    const asset = assetById(item.assetId);
                    const label = elementLabel(ref.kind, item);
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
                        if (busy || state.preview || !editable(ref)) return;
                        cancelDrawing(); state.activeLayer = layer.id; setTool('select');
                        const previous = selectionRefs(), included = previous.some(value => value.kind === ref.kind && value.id === ref.id);
                        setSelection(event.shiftKey ? included ? previous.filter(value => value.kind !== ref.kind || value.id !== ref.id) : [...previous, ref] : [ref]);
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
    function projectMetadata(project, replace = false) {
        if (replace || state.sceneId !== project.sceneId) state.sceneVersion = project.sceneVersion;
        state.sceneId = project.sceneId; state.canUpdate = Boolean(project.canUpdate);
        const button = $('[data-builder-update]'), review = $('[data-builder-review-update]');
        const primary = $('[data-builder-generate]'), create = $('[data-builder-review-generate]');
        if (button) button.hidden = true;
        if (review) review.hidden = !state.sceneId;
        if (button) button.disabled = busy || !state.canUpdate;
        if (review) review.disabled = busy || !state.canUpdate;
        primary.textContent = t(state.sceneId ? 'Update scene' : 'Generate scene');
        primary.disabled = busy || Boolean(state.sceneId && !state.canUpdate);
        create.hidden = Boolean(state.sceneId);
        const status = $('[data-builder-update-status]');
        if (status) status.textContent = !state.sceneId ? t('Generate a scene before updating it.') : state.canUpdate
            ? t('Update replaces builder content and preserves manual objects and tokens.')
            : t('This scene has no update record. The linked scene cannot be updated.');
    }
    function renderReview() {
        const target = $('[data-builder-review-summary]');
        if (!target) return;
        target.replaceChildren();
        for (const [label, value] of [['Map name', state.document.name], ['Dimensions in cells', `${state.document.columns} × ${state.document.rows}`],
            ...objectKinds.map(kind => [kindName(kind), (state.document[kind] || []).length])]) {
            const row = node('div'); row.append(node('span', {}, t(label)), node('strong', { translate: 'no' }, String(value))); target.append(row);
        }
        projectMetadata({ sceneId: state.sceneId, sceneVersion: state.sceneVersion, canUpdate: state.canUpdate });
    }
    function applyPreviewControls() {
        $('[data-builder-collection-filter]').disabled = busy || state.preview;
        for (const control of root.querySelectorAll('[data-builder-quick-name], [data-builder-quick-tool], [data-builder-quick-brush-size], [data-builder-import], [data-family-name], [data-builder-tool], [data-builder-dock-tool], [data-builder-category], [data-builder-role], [data-builder-form] input, [data-builder-properties] input, [data-builder-properties] select, [data-builder-properties] textarea, [data-builder-properties] button, [data-builder-upload], [data-builder-classify] input, [data-builder-asset-role], [data-asset-id], [data-builder-material-id], [data-builder-brush-material], [data-builder-paint-mode], [data-builder-layer-list] input, [data-builder-layer-list] button, [data-builder-layer-add], [data-builder-layer-name], [data-builder-create-first-layer], [data-builder-brush], [data-builder-native-preset], [data-builder-light-preset], [data-builder-particle-preset], [data-builder-shader-preset], [data-builder-snap-step], [data-builder-duplicate], [data-builder-rotate], [data-builder-select-all], [data-builder-toggle-grid], [data-builder-toggle-snap]')) {
            control.disabled = state.preview || busy || control.matches('[data-builder-material-id]') && !selected()
                || control.matches('[data-builder-brush-material]') && !['floor', 'wall', 'door', 'decoration'].includes(state.tool);
            control.disabled ||= control.dataset.builderFilterDisabled === 'true';
            if (control.matches('[data-builder-region-apply]')) control.disabled ||= !$('[data-builder-region-door]')?.value;
            if (control.matches('[data-builder-region-pick-door]')) control.disabled ||= !state.document.doors.length;
        }
        for (const button of root.querySelectorAll('[data-builder-layer-move]')) {
            const index = state.document.layers.findIndex(layer => layer.id === button.closest('[data-builder-project-layer]').dataset.builderProjectLayer);
            button.disabled ||= index + Number(button.dataset.builderLayerMove) < 0 || index + Number(button.dataset.builderLayerMove) >= state.document.layers.length;
        }
        for (const control of root.querySelectorAll('[data-builder-brush-adjust], [data-builder-brush-shape], [data-builder-paint-operation], [data-builder-sample-material], [data-builder-active-layer-select], [data-builder-layers-show-all], [data-builder-layers-unlock-all]')) control.disabled = busy || state.preview;
        $('[data-builder-network]').disabled = busy || state.preview;
        for (const button of root.querySelectorAll('[data-builder-ready-map], [data-builder-empty-object], [data-builder-background-remove]')) button.disabled = busy || state.preview;
        for (const button of root.querySelectorAll('[data-builder-layer-solo]')) button.disabled ||= !state.document.layers.find(layer => layer.id === button.dataset.builderLayerSolo)?.visible;
        for (const selector of ['[data-builder-duplicate]', '[data-builder-rotate]']) {
            const button = $(selector); if (button) button.disabled ||= !state.selections.length;
        }
        projectMetadata({ sceneId: state.sceneId, sceneVersion: state.sceneVersion, canUpdate: state.canUpdate });
        updateLayerControls(); renderPaintControls();
    }
    function setPreview(value) {
        flushFocusedField(); cancelDrawing(); state.preview = value;
        root.classList.toggle('is-preview', value);
        const button = $('[data-builder-preview]');
        button.setAttribute('aria-pressed', String(value));
        button.textContent = t(value ? 'Back to editing' : 'Preview');
        if (!value) setTool(state.tool);
        applyPreviewControls(); renderCanvas();
    }
    function renderProjects() {
        const container = $('[data-builder-projects]'); container.replaceChildren();
        for (const project of state.projects) {
            const button = node('button', { type: 'button', class: 'map-builder__project', 'data-project-id': project.id, 'aria-pressed': String(project.id === state.id) });
            button.append(node('strong', { translate: 'no' }, project.name));
            const date = new Date(project.updatedAt);
            button.append(node('span', {}, Number.isNaN(date.getTime()) ? t('Saved project') : date.toLocaleString(translator.locale, { dateStyle: 'medium', timeStyle: 'short' })));
            button.addEventListener('click', () => confirmLeave(() => openProject(project.id)), { signal }); container.append(button);
        }
        $('[data-builder-projects-empty]').hidden = state.projects.length > 0;
    }
    function renderForm() {
        for (const name of ['name', 'columns', 'rows', 'cellSize', 'background']) form.elements[name].value = state.document[name];
        quickName.value = state.document.name;
        form.elements.grid.checked = state.grid; form.elements.snap.checked = state.snap;
        const folder = $('[data-builder-folder]'); if (folder) folder.hidden = state.folderId !== originalFolder;
    }
    function objectNode(kind, item) {
        const result = baseObjectNode(kind, item);
        if (item.name) {
            result.setAttribute('aria-label', item.name);
            const title = svg('title', { translate: 'no' }); title.textContent = item.name; result.append(title);
        }
        if (item.testHidden) result.style.display = 'none';
        if (!item.testTransform) return result;
        const wrapper = svg('g', { transform: item.testTransform }); wrapper.append(result); return wrapper;
    }
    function baseObjectNode(kind, item) {
        const attrs = { 'data-object-kind': kind, 'data-object-id': item.id, 'data-object-layer': item.layerId };
        if (kind === 'regions') {
            const group = svg('g', attrs);
            if (!state.preview || item.testRegion) group.append(svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height,
                fill: '#7ecabb18', stroke: item.enabled ? '#7ecabb' : '#899098', 'stroke-width': 1,
                'stroke-dasharray': '6 4', 'vector-effect': 'non-scaling-stroke' }));
            return group;
        }
        if (kind === 'floors') {
            if (item.brush?.operation === 'erase' || item.brush && !state.preview && (!state.layers.floors || !layerVisible(layerFor(item)))) return svg('g', attrs);
            const fill = item.paint?.color || (item.assetId && assetById(item.assetId) ? `url(#texture-${item.assetId}-${item.rotation || 0})` : '#49473f');
            if (item.paint) attrs.opacity = item.paint.opacity;
            if (!item.shape && !item.brush) return svg('rect', { ...attrs, x: item.x, y: item.y, width: item.width, height: item.height, fill });
            const group = svg('g', { ...attrs, 'data-builder-free-floor': '' }), defs = svg('defs');
            let shape = svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height, fill });
            if (item.brush) {
                const id = `floor-brush-${item.id}`, raster = terrainMasks.get(item, state.document.cellSize);
                const mask = svg('mask', { id, maskUnits: 'userSpaceOnUse', maskContentUnits: 'userSpaceOnUse',
                    x: raster.x, y: raster.y, width: raster.width, height: raster.height, 'mask-type': 'alpha' });
                mask.append(svg('image', { href: raster.url, x: raster.x, y: raster.y, width: raster.width, height: raster.height,
                    preserveAspectRatio: 'none', 'image-rendering': 'pixelated' }));
                defs.append(mask); shape.setAttribute('mask', `url(#${id})`);
            }
            if (item.shape) {
                const id = `floor-shape-${item.id}`, mask = floorGeometryMask(item, id);
                defs.append(mask);
                const clip = svg('g', { mask: `url(#${id})` }); clip.append(shape); shape = clip;
            }
            group.append(defs, shape);
            return group;
        }
        if (kind === 'decorations') {
            const group = svg('g', attrs);
            group.setAttribute('transform', `rotate(${(item.rotation || 0) + (item.torch?.state === 'on' ? 90 : 0)} ${item.x + item.width / 2} ${item.y + item.height / 2})`);
            if (item.empty) {
                if (!state.preview) {
                    group.dataset.builderEmptyMarker = '';
                    group.append(svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height,
                        fill: '#c09a5a18', stroke: '#c09a5a', 'stroke-width': 1, 'stroke-dasharray': '5 4', 'vector-effect': 'non-scaling-stroke' }));
                    const cx = item.x + item.width / 2, cy = item.y + item.height / 2, size = Math.min(item.width, item.height) * .2;
                    group.append(svg('path', { d: `M ${cx - size} ${cy} H ${cx + size} M ${cx} ${cy - size} V ${cy + size}`,
                        stroke: '#c09a5a', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }));
                }
                return group;
            }
            const appearance = item.testAppearance || (isSmartDecoration(item) ? blueprintAppearance(item) : { visible: true, assetId: item.assetId });
            const asset = appearance.visible && assetById(appearance.assetId);
            if (asset) group.append(svg('image', { href: asset.url, x: item.x, y: item.y, width: item.width, height: item.height, preserveAspectRatio: 'xMidYMid meet' }));
            else if (!state.preview) group.append(svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height,
                fill: '#c09a5a22', stroke: '#c09a5a', 'stroke-width': .03, 'stroke-dasharray': '.15 .1' }));
            return group;
        }
        if (isNativeKind(kind)) {
            item = torchComponentState(state.document, kind, item);
            const group = svg('g', attrs);
            if (!state.preview) {
                const radius = kind === 'lights' ? Math.max(item.brightRadius, item.dimRadius) : kind === 'shaders' ? item.radius : 0;
                if (radius > 0) group.append(svg('circle', { cx: item.x, cy: item.y, r: radius, fill: 'none',
                    stroke: item.color, opacity: .3, 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', 'pointer-events': 'none' }));
                group.append(svg('circle', { cx: item.x, cy: item.y, r: .16, fill: item.enabled ? item.color : '#899098', stroke: '#fff', 'stroke-width': .025 }));
                const mark = svg('text', { x: item.x, y: item.y, 'text-anchor': 'middle', 'dominant-baseline': 'central',
                    fill: '#10171c', 'font-size': .18, 'pointer-events': 'none' });
                mark.textContent = kind === 'lights' ? '☀' : kind === 'particles' ? '✦' : '◈'; group.append(mark);
            }
            return group;
        }
        if (kind === 'walls') {
            const group = svg('g', attrs);
            const size = length(item), dx = item.x2 - item.x1, dy = item.y2 - item.y1;
            const art = wallTexture(item);
            group.dataset.wallArt = art.status;
            const mesh = wallMeshes.get(item.id);
            if (mesh) {
                const strip = svg('g', { 'data-builder-wall-strip': '',
                    transform: `translate(${mesh.origin.x} ${mesh.origin.y}) rotate(${Math.atan2(mesh.direction.y, mesh.direction.x) * 180 / Math.PI})` });
                const path = mesh.polygons.map(polygon => ringPath(polygon.map(([x, y]) => [x + mesh.phase, y]))).join(' ');
                strip.append(svg('path', { d: path, fill: art.fill, 'fill-rule': 'nonzero',
                    transform: `translate(${-mesh.phase} 0)`, 'data-builder-wall-mesh': '' }));
                group.append(strip); return group;
            }
            const strip = svg('g', { 'data-builder-wall-strip': '',
                transform: `translate(${item.x1} ${item.y1}) rotate(${Math.atan2(dy, dx) * 180 / Math.PI})` });
            // Keep the texture's origin on the original wall when doors split it.
            if (size) for (const segment of wallSegments(state.document, item)) {
                const from = ((segment.x1 - item.x1) * dx + (segment.y1 - item.y1) * dy) / size;
                const to = ((segment.x2 - item.x1) * dx + (segment.y2 - item.y1) * dy) / size;
                strip.append(svg('rect', { x: from, y: -item.thickness / 2, width: Math.max(0, to - from),
                    height: item.thickness, fill: art.fill }));
            }
            group.append(strip);
            return group;
        }
        const segment = doorDisplaySegment(item); if (!segment) return svg('g');
        const group = svg('g', attrs);
        const appearance = item.testAppearance || blueprintAppearance(item), doorAsset = assetById(appearance.assetId);
        if (!appearance.visible) {
            if (!state.preview) group.append(svg('line', { x1: segment.x1, y1: segment.y1, x2: segment.x2, y2: segment.y2,
                stroke: '#c09a5a', 'stroke-width': .05, 'stroke-dasharray': '.15 .1' })); return group;
        }
        const shape = svg('g', { transform: `translate(${segment.x1} ${segment.y1}) rotate(${segment.angle})` });
        if (doorAsset) shape.append(svg('image', { href: doorAsset.url, x: 0, y: -segment.thickness / 2,
            width: length(item), height: segment.thickness, preserveAspectRatio: 'none' }));
        else shape.append(svg('rect', { x: 0, y: -Math.max(.16, segment.thickness) / 2, width: length(item),
            height: Math.max(.16, segment.thickness), fill: item.state === 'locked' ? '#c38155' : '#c09a5a', stroke: '#27221b', 'stroke-width': .04 }));
        group.append(shape);
        return group;
    }
    function ensureTexturePatterns(keys, prune = false) {
        const defs = $('[data-builder-defs]');
        const existing = new Map([...defs.querySelectorAll('[data-texture]')].map(item => [item.dataset.texture, item]));
        if (prune) for (const [key, element] of existing) if (!keys.has(key)) element.remove();
        for (const key of keys) {
            const split = key.lastIndexOf('-'), id = key.slice(0, split), rotation = Number(key.slice(split + 1));
            const asset = assetById(id); if (!asset || existing.has(key)) continue;
            const pattern = svg('pattern', { id: `texture-${key}`, 'data-texture': key, width: 1, height: 1, patternUnits: 'userSpaceOnUse', patternTransform: `rotate(${rotation})` });
            pattern.append(svg('image', { href: asset.url, x: 0, y: 0, width: 1, height: 1, preserveAspectRatio: 'none' })); defs.append(pattern);
        }
    }
    function wallPatternKey(item) { return `${item.assetId}-${item.thickness}`; }
    function wallTexture(item) {
        const asset = assetById(item.assetId);
        if (!asset) return { status: 'ready', fill: '#8d8170' };
        const art = wallArt.get(asset);
        if (art.status !== 'ready') return { status: art.status, fill: '#8d8170' };
        const key = wallPatternKey(item);
        if (!wallPatterns.has(key)) {
            const bounds = art.bounds, height = item.thickness, width = height * bounds.width / bounds.height;
            const pattern = svg('pattern', { id: `wall-texture-${key}`, 'data-wall-texture': key,
                x: 0, y: -height / 2, width, height, patternUnits: 'userSpaceOnUse' });
            const crop = svg('svg', { x: 0, y: 0, width, height,
                viewBox: `${bounds.x} ${bounds.y} ${bounds.width} ${bounds.height}`, preserveAspectRatio: 'none', overflow: 'hidden' });
            crop.append(svg('image', { href: asset.url, x: 0, y: 0, width: art.width, height: art.height, preserveAspectRatio: 'none' }));
            pattern.append(crop); $('[data-builder-defs]').append(pattern); wallPatterns.set(key, pattern);
        }
        return { status: 'ready', fill: `url(#wall-texture-${key})` };
    }
    function floorGeometryMask(item, id) {
        const mask = svg('mask', { id, maskUnits: 'userSpaceOnUse', maskContentUnits: 'userSpaceOnUse',
            x: item.x, y: item.y, width: item.width, height: item.height, 'mask-type': 'luminance' });
        for (const ring of floorShapeRings(item)) mask.append(svg('path', { d: ringPath(ring), fill: 'white', 'fill-rule': 'evenodd' }));
        for (const ring of floorShapeRings(item, 'cuts')) mask.append(svg('path', { d: ringPath(ring), fill: 'black', 'fill-rule': 'evenodd' }));
        return mask;
    }
    function renderFloors(doc) {
        const children = [];
        for (const layer of doc.layers) {
            const floors = doc.floors.filter(item => item.layerId === layer.id);
            if (!floors.some(item => item.brush?.operation === 'erase')) {
                children.push(...floors.map(item => objectNode('floors', item))); continue;
            }
            const group = svg('g', { 'data-builder-floor-layer': layer.id });
            if (!state.preview && (!state.layers.floors || !layerVisible(layer))) group.style.display = 'none';
            for (const item of floors) {
                if (item.brush?.operation !== 'erase') { group.append(objectNode('floors', item)); continue; }
                if (state.preview || state.layers.floors && layerVisible(layer)) {
                    const id = `floor-erase-${item.id}`, raster = terrainMasks.get(item, doc.cellSize), defs = svg('defs');
                    const mask = svg('mask', { id, maskUnits: 'userSpaceOnUse', maskContentUnits: 'userSpaceOnUse',
                        x: 0, y: 0, width: doc.columns, height: doc.rows, 'mask-type': 'luminance' });
                    mask.append(svg('rect', { x: 0, y: 0, width: doc.columns, height: doc.rows, fill: 'white' }));
                    let image = svg('image', { href: raster.url, x: raster.x, y: raster.y, width: raster.width, height: raster.height,
                        preserveAspectRatio: 'none', 'image-rendering': 'pixelated', opacity: item.paint?.opacity ?? 1 });
                    if (item.shape) {
                        const clipId = `floor-shape-${item.id}`; defs.append(floorGeometryMask(item, clipId));
                        const clip = svg('g', { mask: `url(#${clipId})` }); clip.append(image); image = clip;
                    }
                    mask.append(image); defs.append(mask);
                    const previous = svg('g', { mask: `url(#${id})` }); previous.append(...group.childNodes);
                    group.append(defs, previous);
                }
                group.append(objectNode('floors', item));
            }
            children.push(group);
        }
        $('[data-builder-floors]').replaceChildren(...children);
    }
    function renderCanvas() {
        const doc = state.document;
        try {
            wallMeshes = wallJoinGeometry(doc, doc.walls.flatMap(wall => wallSegments(doc, wall).map(span => ({ ...span, wall }))));
            wallMeshError = undefined;
        } catch (cause) {
            if (!(cause instanceof RangeError) || cause.message !== 'The map produces too many wall segments.') throw cause;
            wallMeshes = new Map();
            if (wallMeshError !== cause.message) notify(t(cause.message), [], 'error');
            wallMeshError = cause.message;
        }
        const used = new Set(doc.floors.map(item => item.assetId && `${item.assetId}-${item.rotation || 0}`).filter(Boolean));
        ensureTexturePatterns(used, true);
        const wallKeys = new Set(doc.walls.map(wallPatternKey));
        if (gesture?.tool === 'wall') wallKeys.add(wallPatternKey(brushObject()));
        for (const [key, pattern] of wallPatterns) if (!wallKeys.has(key)) { pattern.remove(); wallPatterns.delete(key); }
        const layerOrder = new Map(doc.layers.map((layer, index) => [layer.id, index]));
        terrainMasks.prune(doc.floors); renderFloors(doc);
        for (const kind of objectKinds) if (kind !== 'floors') $('[data-builder-' + kind + ']').replaceChildren(...(doc[kind] || []).slice()
            .sort((a, b) => layerOrder.get(a.layerId) - layerOrder.get(b.layerId)).map(item => objectNode(kind, item)));
        for (const element of root.querySelectorAll('[data-builder-paper],[data-builder-grid],[data-builder-outline]')) {
            element.setAttribute('width', doc.columns); element.setAttribute('height', doc.rows);
        }
        $('[data-builder-paper]').setAttribute('fill', doc.background);
        const backgroundAsset = assetById(doc.backgroundImage?.assetId);
        $('[data-builder-background-image]').replaceChildren(...(backgroundAsset ? [svg('image', { href: backgroundAsset.url,
            x: 0, y: 0, width: doc.columns, height: doc.rows, preserveAspectRatio: 'none' })] : []));
        $('[data-builder-background-name]').textContent = backgroundAsset ? backgroundAsset.name : '';
        $('[data-builder-background-remove]').hidden = !doc.backgroundImage;
        $('[data-builder-grid]').style.display = state.grid && !state.preview ? '' : 'none';
        $('[data-builder-outline]').style.display = state.preview ? 'none' : '';
        if (document.activeElement !== quickName) quickName.value = doc.name || t('Untitled map');
        const context = $('[data-builder-panel-context]');
        context.textContent = doc.name || t('Untitled map'); context.title = context.textContent;
        const mapLabel = $('[data-builder-map-name]'); if (mapLabel) mapLabel.textContent = doc.name || t('Untitled map');
        $('[data-builder-dimensions]').textContent = t('{columns} × {rows} cells', { columns: doc.columns, rows: doc.rows });
        $('[data-builder-object-count]').textContent = t('{count} objects', { count: objectKinds.reduce((count, kind) => count + (doc[kind] || []).length, 0) });
        renderSelection(); renderLayerVisibility(); renderReview(); updateSaveState(); updateLayerControls();
        const gridButton = $('[data-builder-toggle-grid]'); if (gridButton) gridButton.setAttribute('aria-pressed', String(state.grid));
        renderPaintControls();
    }
    function selected() { return state.selection && state.document[state.selection.kind].find(item => item.id === state.selection.id); }
    function renderSelection() {
        const container = $('[data-builder-selection]'); container.replaceChildren();
        for (const ref of selectionRefs()) {
            const source = itemFor(ref), item = isNativeKind(ref.kind) ? torchComponentState(state.document, ref.kind, source) : source;
            const style = { fill: 'none', stroke: '#e4bf76', 'stroke-width': 2, 'stroke-dasharray': '5 3', 'vector-effect': 'non-scaling-stroke' };
            if (ref.kind === 'doors' || ref.kind === 'walls') {
                container.append(svg('line', { x1: item.x1, y1: item.y1, x2: item.x2, y2: item.y2, ...style }));
                if (ref.kind === 'doors' && selectionRefs().length === 1) {
                    const anchor = doorRotationPoint(item);
                    container.append(svg('circle', { cx: anchor.x, cy: anchor.y, r: 5 / camera.scale,
                        fill: '#e4bf76', stroke: '#253038', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke',
                        'data-builder-door-anchor': item.rotationAnchor ?? 'center' }));
                }
            } else if (isNativeKind(ref.kind)) {
                container.append(svg('circle', { cx: item.x, cy: item.y, r: .22, ...style }));
            } else {
                const shape = svg('rect', { x: item.x, y: item.y, width: item.width, height: item.height, ...style });
                if (ref.kind === 'decorations') shape.setAttribute('transform', `rotate(${(item.rotation || 0) + (item.torch?.state === 'on' ? 90 : 0)} ${item.x + item.width / 2} ${item.y + item.height / 2})`);
                container.append(shape);
            }
        }
        wallControls?.render(container);
    }
    function renderProperties() {
        const container = $('[data-builder-properties]'); container.replaceChildren();
        const refs = selectionRefs();
        const item = selected();
        renderMaterials();
        const selectionLabel = $('[data-builder-selection-label]');
        if (selectionLabel) {
            selectionLabel.textContent = refs.length > 1 ? t('{count} selected', { count: refs.length })
                : item ? elementLabel(state.selection.kind, item) : t(strings[state.tool]);
        }
        const materials = $('[data-builder-materials]'); if (materials) materials.hidden = !item || item.empty || refs.length > 1 || isNativeKind(state.selection.kind) || state.selection.kind === 'regions' || item.brush?.operation === 'erase';
        container.dataset.empty = String(!item);
        if (!item) {
            container.append($('[data-builder-quick-tool=select] svg').cloneNode(true), node('strong', {}, t('Nothing selected')),
                node('p', { class: 'map-builder__hint' }, t(strings.select)));
            const choose = node('button', { type: 'button', 'data-builder-select-on-map': '' }, t('Select on map'));
            choose.addEventListener('click', () => chooseQuickTool('select'), { signal }); container.append(choose);
            applyPreviewControls(); return;
        }
        const layerLabel = node('label', {}, t('Layer')), layerSelect = node('select', { 'data-builder-property': 'layerId' });
        const sourceLayers = new Set(refs.map(ref => itemFor(ref).layerId));
        if (sourceLayers.size > 1) layerSelect.append(new Option(t('Multiple layers'), ''));
        for (const layer of state.document.layers) {
            const option = new Option(layer.name, layer.id); option.disabled = !layer.visible || layer.locked; layerSelect.append(option);
        }
        layerSelect.value = sourceLayers.size === 1 ? item.layerId : '';
        layerLabel.append(layerSelect); container.append(layerLabel);
        layerSelect.addEventListener('change', () => {
            if (busy || state.preview || !moveSelectionToLayer(state.document, refs, layerSelect.value)) return;
            if (state.soloLayer) state.soloLayer = layerSelect.value;
            setSelection(refs); commit(); renderCanvas(); renderLayers(); renderProperties();
        }, { signal });
        if (refs.length > 1) {
            container.prepend(node('strong', { 'data-builder-selected-count': String(refs.length) }, t('{count} selected', { count: refs.length })));
            const remove = node('button', { type: 'button', 'data-builder-delete': '' }, t('Delete selected objects'));
            remove.addEventListener('click', deleteSelection, { signal }); container.append(remove); applyPreviewControls(); return;
        }
        const { kind } = state.selection;
        container.prepend(node('strong', {}, t(item.empty ? 'Empty Object' : item.torch ? 'Torch' : kindName(kind))));
        const nameLabel = node('label', {}, t(item.empty ? 'Object name' : kind === 'regions' ? 'Region name' : 'Element name'));
        const nameInput = node('input', { type: 'text', maxlength: '120', autocomplete: 'off',
            'data-builder-property': kind === 'regions' ? 'regionName' : 'name', 'data-builder-selection-name': '', translate: 'no' });
        nameInput.required = item.empty === true || ['regions', 'shaders'].includes(kind);
        const currentName = () => item.name || (item.empty ? t('Empty Object') : '');
        nameInput.value = currentName(); nameInput.placeholder = elementLabel(kind, item, false);
        nameLabel.append(nameInput); container.append(nameLabel);
        nameInput.addEventListener('input', () => nameInput.setCustomValidity(''), { signal });
        nameInput.addEventListener('change', () => {
            if (busy || state.preview || nameInput.disabled) return;
            const name = nameInput.value.trim();
            nameInput.setCustomValidity(name.includes('\0') || Array.from(name).length > 120
                || nameInput.required && !name ? t('Use a name with 1 to 120 characters.') : '');
            if (!nameInput.reportValidity()) return;
            nameInput.value = name;
            if ((item.name || '') === name) return;
            if (name) item.name = name; else delete item.name;
            commit(); renderCanvas(); renderLayers();
            if (selectionLabel) selectionLabel.textContent = elementLabel(kind, item);
        }, { signal });
        nameInput.addEventListener('keydown', event => {
            if (event.isComposing || !['Enter', 'Escape'].includes(event.key)) return;
            event.preventDefault(); event.stopPropagation();
            if (event.key === 'Escape') { nameInput.value = currentName(); nameInput.setCustomValidity(''); }
            else nameInput.dispatchEvent(new Event('change'));
            if (nameInput.checkValidity()) { nameInput.blur(); viewport.focus({ preventScroll: true }); }
        }, { signal });
        if (item.empty) container.append(node('p', { class: 'map-builder__hint' },
            t('An invisible object with states and behaviors. Only the GM can see its marker.')));
        const owner = isNativeKind(kind) && torchOwner(state.document, kind, item.id);
        if (owner) {
            const selectTorch = node('button', { type: 'button', 'data-builder-select-torch': owner.id }, t('Select linked torch'));
            selectTorch.addEventListener('click', () => { setSelection([{ kind: 'decorations', id: owner.id }]); renderSelection(); renderProperties(); }, { signal });
            container.append(selectTorch);
        }
        if (hasNativeEditor(kind)) {
            const edit = node('button', { type: 'button', 'data-builder-edit-native': kind }, t('Open game editor'));
            edit.addEventListener('click', () => void openNativeEditor({ kind, id: item.id }), { signal });
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
                if (busy || state.preview || input.disabled || !input.checkValidity() || !Number.isFinite(Number(input.value))) return;
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
        if (kind === 'floors' || kind === 'decorations' || kind === 'regions') {
            addField('X', 'x', 0, state.document.columns); addField('Y', 'y', 0, state.document.rows);
            const minimum = kind === 'floors' && item.shape ? .001 : .05;
            addField('Width', 'width', minimum, state.document.columns); addField('Height', 'height', minimum, state.document.rows);
            if (kind !== 'regions') addField('Rotation', 'rotation', 0, kind === 'floors' ? 270 : 359, kind === 'floors' ? 90 : 1);
        } else if (kind === 'lights') {
            addField('X', 'x', 0, state.document.columns); addField('Y', 'y', 0, state.document.rows);
            addField('Bright radius (cells)', 'brightRadius', 0, 200); addField('Dim radius (cells)', 'dimRadius', 0, 200);
            addField('Intensity', 'intensity', 0, 1);
        } else if (isNativeKind(kind)) {
            addField('X', 'x', 0, state.document.columns); addField('Y', 'y', 0, state.document.rows);
        } else {
            addField('Start X', 'x1', 0, state.document.columns); addField('Start Y', 'y1', 0, state.document.rows);
            addField('End X', 'x2', 0, state.document.columns); addField('End Y', 'y2', 0, state.document.rows);
            addField('Thickness', 'thickness', .05, 2);
        }
        container.append(row);
        if (isNativeKind(kind)) {
            renderNativeProperties(container, { kind, item, t, signal, change: patch => {
                if (busy || state.preview) return;
                Object.assign(item, patch); commit(); renderCanvas();
            } });
        } else if (kind !== 'regions' && !item.empty && item.brush?.operation !== 'erase') {
            const assetLabel = node('label', {}, t('Appearance')), select = node('select', { 'data-builder-property': 'assetId' });
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
                if (busy || state.preview || anchorSelect.disabled || anchorSelect.value === (item.rotationAnchor ?? '')) return;
                if (!anchorSelect.value) delete item.rotationAnchor; else item.rotationAnchor = anchorSelect.value;
                commit(); renderCanvas();
            }, { signal });
            container.append(node('small', { class: 'map-builder__hint' }, t('An anchor rotates the door image 90° when opened.')));
            const field = node('div', { class: 'map-builder__state-field' }), title = node('span', { id: 'builder-door-state-label' }, t('Initial state'));
            const group = node('div', { class: 'map-builder__segmented', role: 'group', 'aria-labelledby': 'builder-door-state-label', 'data-builder-property': 'state', 'data-value': item.state });
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
            const behaviorLabel = node('label', {}, t('Behavior'));
            const behavior = node('select', { 'data-builder-property': 'behavior' });
            behavior.append(new Option(t('None'), 'none'), new Option(t('Lever'), 'lever'), new Option(t('Torch'), 'torch'));
            behavior.value = item.torch ? 'torch' : item.lever ? 'lever' : 'none'; behaviorLabel.append(behavior); if (!item.empty) container.append(behaviorLabel);
            behavior.addEventListener('change', () => {
                if (busy || state.preview) return;
                const nextBehavior = behavior.value;
                if (nextBehavior === (item.torch ? 'torch' : item.lever ? 'lever' : 'none')) return;
                if (behavior.value !== 'none' && !item.assetId) {
                    behavior.value = isSmartDecoration(item) ? item.torch ? 'torch' : 'lever' : 'none';
                    notify(t(nextBehavior === 'lever' ? 'Choose an object image before enabling lever behavior.' : 'Choose an object image before enabling torch behavior.'), [], 'error'); return;
                }
                if (nextBehavior === 'torch' && allRefs().length >= (state.limits.maxObjects || 2000)) { behavior.value = item.lever ? 'lever' : 'none'; notify(t('The map has too many objects.'), [], 'error'); return; }
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
            if (item.lever) {
                const label = node('label', {}, t('Initial state'));
                const initial = node('select', { 'data-builder-property': 'leverState' });
                initial.append(new Option(t('Deactivated'), 'off'), new Option(t('Activated'), 'on'));
                initial.value = item.lever.state; label.append(initial); container.append(label);
                initial.addEventListener('change', () => { item.lever.state = initial.value; commit(); renderCanvas(); }, { signal });
                const edit = node('button', { type: 'button', 'data-builder-edit-behavior': '' }, t('Edit behavior'));
                edit.addEventListener('click', () => openBehavior(state.selection), { signal }); container.append(edit);
                container.append(node('p', { class: 'map-builder__hint' }, t(item.empty ? 'Double-click the object to edit its states and actions.' : 'Double-click the lever to edit its states and actions.')));
            }
            if (item.torch) renderTorchProperties(container, item);
        }
        if (['floors', 'walls'].includes(kind) && item.brush?.operation !== 'erase') {
            const label = node('label', { class: 'map-builder__torch-lit' }), input = node('input', { type: 'checkbox', 'data-builder-property': 'dynamic' });
            input.checked = item.dynamic === true;
            label.append(input, node('span', {}, t('Dynamic surface'))); container.append(label,
                node('p', { class: 'map-builder__hint' }, t('Publish this artwork separately so behaviors can change its material or visibility during play.')));
            input.addEventListener('change', () => {
                if (busy || state.preview || !setDynamicSurface(state.document, kind, item.id, input.checked)) return;
                commit(); renderCanvas();
            }, { signal });
        }
        if (kind === 'doors' || kind === 'decorations' && isSmartDecoration(item)) {
            const label = node('label', { class: 'map-builder__torch-lit' });
            const input = node('input', { type: 'checkbox', 'data-builder-property': 'interactionEnabled' });
            input.checked = item.interactionEnabled !== false;
            label.append(input, node('span', {}, t('Player interaction'))); container.append(label,
                node('p', { class: 'map-builder__hint' }, t('The GM can always operate and edit this element.')));
            input.addEventListener('change', () => {
                if (busy || state.preview) return;
                if (input.checked) delete item.interactionEnabled; else item.interactionEnabled = false;
                commit();
            }, { signal });
        }
        if (kind === 'regions') renderRegionProperties(container, item);
        const button = node('button', { type: 'button', 'data-builder-delete': '' }, t('Delete object'));
        button.addEventListener('click', deleteSelection, { signal }); container.append(button);
        applyPreviewControls();
    }
    function renderRegionProperties(container, item) {
        const enabledLabel = node('label', { class: 'map-builder__torch-lit' });
        const enabled = node('input', { type: 'checkbox', 'data-builder-property': 'regionEnabled' });
        enabled.checked = item.enabled;
        enabledLabel.append(enabled, node('span', {}, t('Presence triggers enabled'))); container.append(enabledLabel);
        enabled.addEventListener('change', () => {
            if (busy || state.preview) return;
            item.enabled = enabled.checked; commit(); renderCanvas();
        }, { signal });
        const vertical = node('div', { class: 'map-builder__fields' });
        for (const [key, label] of [['bottom', 'Minimum elevation'], ['top', 'Maximum elevation']]) {
            const field = node('label', {}, t(label)), input = node('input', { type: 'number', min: '-1000000', max: '1000000', step: 'any',
                placeholder: t('Unbounded'), 'data-builder-property': `region-${key}` });
            input.value = item.vertical?.[key] ?? ''; field.append(input); vertical.append(field);
            input.addEventListener('change', () => {
                if (busy || state.preview || !input.checkValidity()) return;
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
                if (busy || state.preview || !container.isConnected) return;
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
            setSidebarTab('library');
            const id = await pickOnMap('doors');
            if (disposed || !container.isConnected) return;
            setSidebarTab('selection', true);
            if (id) { door.value = id; apply.disabled = false; }
        }, { signal });
        apply.addEventListener('click', () => {
            if (busy || state.preview || !state.document.doors.some(entry => entry.id === door.value)) return;
            configurePressurePlate(item, door.value); commit(); renderProperties();
            notify(t('Pressure plate configured: first token opens the door; last token closes it.'));
        }, { signal });
        actions.append(pick, apply); preset.append(actions,
            node('p', { class: 'map-builder__hint' }, t('Applying this preset replaces this region\u2019s Blueprint.')));
        const edit = node('button', { type: 'button', 'data-builder-edit-behavior': '' }, t('Edit behavior'));
        edit.addEventListener('click', () => openBehavior(state.selection), { signal });
        container.append(preset, edit);
    }
    function createTorchComponent(item, kind) {
        const tool = kind === 'lights' ? 'light' : kind === 'particles' ? 'particle' : 'shader';
        const preset = tool === 'light' ? 'torch' : tool === 'particle' ? 'ember' : state.nativeChoices.shader;
        const component = { id: crypto.randomUUID(), layerId: item.layerId,
            ...nativeFactory(tool, preset, item.x + item.width / 2, item.y + item.height / 2) };
        (state.document[kind] ||= []).push(component); return component;
    }
    function detachTorch(item) {
        const children = torchChildren(state.document, item);
        if (item.torch?.state === 'on') item.rotation = ((item.rotation || 0) + 90) % 360;
        delete item.torch; delete item.blueprint;
        for (const ref of children) removeObject(state.document, ref.kind, ref.id);
    }
    function renderTorchProperties(container, item) {
        const mechanism = node('label', {}, t('Mechanism'));
        const stateControl = node('select', { 'data-builder-property': 'torchState' });
        stateControl.append(new Option(t('Normal'), 'off'), new Option(t('Turned'), 'on'));
        stateControl.value = item.torch.state; mechanism.append(stateControl); container.append(mechanism);
        stateControl.addEventListener('change', () => {
            if (busy || state.preview) return;
            if (item.torch.state === stateControl.value) return;
            const previous = item.torch.state; item.torch.state = stateControl.value;
            if (!fitsBounds(state.document)) { item.torch.state = previous; renderProperties(); notify(t('Keep objects inside the map.'), [], 'error'); return; }
            commit(); renderCanvas();
        }, { signal });
        const litLabel = node('label', { class: 'map-builder__torch-lit' });
        const lit = node('input', { type: 'checkbox', 'data-builder-property': 'torchLit' }); lit.checked = item.torch.lit;
        litLabel.append(lit, node('span', {}, t('Flame lit'))); container.append(litLabel);
        lit.addEventListener('change', () => { if (!busy && !state.preview) { item.torch.lit = lit.checked; commit(); renderCanvas(); } }, { signal });
        const components = node('section', { class: 'map-builder__torch-components', 'aria-label': t('Torch components') });
        components.append(node('strong', {}, t('Torch components')));
        for (const [kind, key, label] of [['lights', 'lightId', 'Light'], ['particles', 'particleId', 'Particles'], ['shaders', 'shaderId', 'Shader']]) {
            const row = node('div', { class: 'map-builder__torch-component' }); row.append(node('span', {}, t(label)));
            const component = itemFor({ kind, id: item.torch[key] });
            if (component) {
                const edit = node('button', { type: 'button', 'data-builder-edit-torch-component': kind }, t('Edit'));
                edit.addEventListener('click', () => void openNativeEditor({ kind, id: component.id }, { keepSelection: true }), { signal }); row.append(edit);
                if (kind !== 'lights') {
                    const remove = node('button', { type: 'button', 'data-builder-remove-torch-component': kind }, t('Remove'));
                    remove.addEventListener('click', () => { if (busy || state.preview) return; removeObject(state.document, kind, component.id); commit(); renderCanvas(); renderLayers(); renderProperties(); }, { signal }); row.append(remove);
                }
            } else {
                const add = node('button', { type: 'button', 'data-builder-add-torch-component': kind }, t('Add'));
                add.addEventListener('click', () => {
                    if (busy || state.preview) return;
                    const maximum = state.limits.maxObjects || 2000;
                    if (allRefs().length >= maximum) { notify(t('The map has too many objects.'), [], 'error'); return; }
                    const next = createTorchComponent(item, kind); item.torch[key] = next.id;
                    commit(); renderCanvas(); renderLayers(); renderProperties();
                }, { signal }); row.append(add);
            }
            components.append(row);
        }
        container.append(components);
        const edit = node('button', { type: 'button', 'data-builder-edit-behavior': '' }, t('Edit behavior'));
        edit.addEventListener('click', () => openBehavior(state.selection), { signal }); container.append(edit);
        container.append(node('p', { class: 'map-builder__hint' }, t('Turning the mechanism and lighting the flame are independent. Double-click the torch to edit its behavior.')));
    }
    function commit() { floorPainter?.cancel(); terrainPainter?.cancel(); discardDraft = false; undo.commit(state.document); rememberDraft(); updateSaveState(); if (!state.recoveryConflict) autosave?.schedule(); }
    function changeHistory(direction) {
        if (busy || state.preview) return; cancelDrawing(); state.document = undo[direction]();
        renderForm(); renderAssets(); renderCanvas(); renderLayers(); renderProperties();
        camera.resize(state.document.columns, state.document.rows, state.document.cellSize, false); rememberDraft(); updateSaveState(); if (!state.recoveryConflict) autosave?.schedule();
    }
    function deleteSelection() {
        if (busy || state.preview) return;
        cancelDrawing();
        const candidate = clone(state.document);
        try { for (const ref of selectionRefs()) removeObject(candidate, ref.kind, ref.id); }
        catch (cause) { notify(t(cause.message), [], 'error'); return; }
        state.document = candidate;
        setSelection([]);
        commit(); renderCanvas(); renderLayers(); renderProperties();
    }
    function selectAll() {
        if (busy || state.preview) return;
        cancelDrawing(); setSelection(allRefs()); renderSelection(); renderProperties();
    }
    function transformSelection(action) {
        if (busy || state.preview || !selectionRefs().length) return;
        cancelDrawing(); const refs = [...selectionRefs()];
        let succeeded;
        if (action === 'duplicate') {
            if (allRefs().length + refs.length > (state.limits.maxObjects || 2000)) { notify(t('This map has reached the object limit.'), [], 'error'); return; }
            const copies = duplicateSelection(state.document, refs); succeeded = copies.length > 0;
            if (succeeded) setSelection(copies);
        } else succeeded = rotateSelection(state.document, refs, 90);
        if (!succeeded) { notify(t('The selection cannot fit here or would overlap another door.'), [], 'error'); return; }
        commit(); renderCanvas(); renderLayers(); renderProperties();
    }
    function bounded(point, cell = false, snapping = state.snap) {
        const step = cell ? 1 : state.snapStep;
        const snap = value => snapping ? Math.round(value / step) * step : round(value);
        return { x: clamp(snap(point.x), 0, state.document.columns), y: clamp(snap(point.y), 0, state.document.rows) };
    }
    function hit(point, event) {
        const element = event?.target.closest?.('[data-object-id]');
        const direct = element && { kind: element.dataset.objectKind, id: element.dataset.objectId };
        const composed = ref => {
            if (picking?.kind === ref.kind) return ref;
            const owner = isNativeKind(ref.kind) && torchOwner(state.document, ref.kind, ref.id);
            const exactSelection = selectionRefs().some(selected => selected.kind === ref.kind && selected.id === ref.id);
            return owner && !exactSelection && editable({ kind: 'decorations', id: owner.id }) ? { kind: 'decorations', id: owner.id } : ref;
        };
        const sampledLayers = new Map();
        const visibleFloor = ref => {
            const item = itemFor(ref);
            if (!sampledLayers.has(item.layerId)) sampledLayers.set(item.layerId, sampleFloor(state.document, point, { layerId: item.layerId })?.id);
            return item.brush?.operation !== 'erase' && floorContainsPoint(item, point)
                && sampledLayers.get(item.layerId) === item.id;
        };
        if (direct && editable(direct) && (direct.kind !== 'floors' || visibleFloor(direct))) return composed(direct);
        const unlocked = item => { const layer = layerFor(item); return layerVisible(layer) && !layer.locked; };
        const door = state.layers.doors && nearestWall({ walls: state.document.doors.filter(unlocked) }, point, 9 / camera.scale);
        if (door) return { kind: 'doors', id: door.wall.id };
        const near = state.layers.walls && nearestWall({ walls: state.document.walls.filter(unlocked) }, point, 9 / camera.scale);
        if (near) return { kind: 'walls', id: near.wall.id };
        for (const kind of ['shaders', 'particles', 'lights']) {
            const native = state.layers[kind] && (state.document[kind] || []).slice().reverse().find(item => {
                const shown = torchComponentState(state.document, kind, item);
                return unlocked(item) && Math.hypot(point.x - shown.x, point.y - shown.y) <= 9 / camera.scale;
            });
            if (native) return composed({ kind, id: native.id });
        }
        const objects = objectsInRectangle(state.document, { x: point.x, y: point.y, width: .0001, height: .0001 }).filter(ref => state.layers[ref.kind]);
        return objects.filter(ref => (ref.kind === 'regions' || ref.kind === 'decorations' || ref.kind === 'floors' && visibleFloor(ref)) && editable(ref)).at(-1) || null;
    }
    function start(point, event, resumePaint = false) {
        if (busy || !ready || state.preview) return false;
        flushFocusedField();
        if (state.tool === 'floor' && state.paintMode === 'brush' && !state.samplingFloor && event.button === 0 && event.shiftKey && !event.altKey && !event.ctrlKey && !event.metaKey) {
            if (point.x < 0 || point.y < 0 || point.x > state.document.columns || point.y > state.document.rows) return false;
            brushResize = { point: { x: point.x, y: point.y }, clientX: event.clientX, size: state.brush.floorSize };
            resizeBrush(event); return true;
        }
        const wallControl = wallControls?.start(point, event);
        if (wallControl !== undefined && wallControl !== null) return wallControl;
        if (point.x < 0 || point.y < 0 || point.x > state.document.columns || point.y > state.document.rows) return false;
        if (state.tool === 'floor' && (state.samplingFloor || event.altKey)) { pickFloorMaterial(point); return false; }
        const before = clone(state.document), target = hit(point, event);
        if (!resumePaint && (hasNativeEditor(target?.kind) || target?.kind === 'decorations' && isSmartDecoration(itemFor(target)))
            && !['select', 'erase'].includes(state.tool) && !floorPainter.polygon) {
            gesture = { before, pendingEdit: { point, event, target } }; return true;
        }
        if (state.tool === 'select') {
            const previous = [...selectionRefs()];
            if (event.shiftKey && target) {
                const present = previous.some(ref => ref.kind === target.kind && ref.id === target.id);
                setSelection(present ? previous.filter(ref => ref.kind !== target.kind || ref.id !== target.id) : [...previous, target]);
            } else if (target && !previous.some(ref => ref.kind === target.kind && ref.id === target.id)) setSelection([target]);
            else if (!target && !event.shiftKey) setSelection([]);
            renderSelection(); renderProperties();
            if (target) {
                setCategory(target.kind === 'floors' ? 'terrain' : ['walls', 'doors'].includes(target.kind) ? 'structure' : 'decoration', false);
                if (!isNativeKind(target.kind) && target.kind !== 'regions') setRole(roleForKind(target.kind), false);
            }
            gesture = !target || event.shiftKey ? { before, start: point, point, marquee: true, previous,
                additive: event.shiftKey, dragged: false } : { before, start: bounded(point), rawStart: point,
                    snapWalls: state.snap && selectionRefs().some(ref => ref.kind === 'walls'), refs: [...selectionRefs()] };
            return true;
        }
        if (state.tool === 'erase') {
            if (target) {
                try { removeObject(state.document, target.kind, target.id); }
                catch (cause) { notify(t(cause.message), [], 'error'); return false; }
                setSelection([]); commit(); renderCanvas(); renderLayers(); renderProperties();
            }
            return false;
        }
        const layer = state.document.layers.find(item => item.id === state.activeLayer);
        if (!layer) { event.preventDefault(); requestFirstLayer(); return false; }
        if (!layerVisible(layer) || layer.locked) { notify(t('Choose a visible, unlocked layer before painting.'), [], 'error'); return false; }
        if (state.tool === 'floor') {
            setSelection([]); renderSelection();
            viewport.focus({ preventScroll: true });
            return terrainMode() ? terrainPainter.start(point)
                : floorPainter.start(['brush', 'fill'].includes(state.paintMode) ? point : bounded(point, false, floorSnap()));
        }
        if (state.tool !== 'wall' && allRefs().length >= (state.limits.maxObjects || 2000)) {
            notify(t('This map has reached the object limit.'), [], 'error'); return false;
        }
        if (state.tool === 'region' && (state.document.regions || []).length >= 128) {
            notify(t('This map has reached the region limit.'), [], 'error'); return false;
        }
        gesture = { before, id: crypto.randomUUID(), start: bounded(point), point: bounded(point), tool: state.tool, layerId: state.activeLayer,
            assetId: state.tool === 'region' || isNativeKind(kindForTool(state.tool)) ? null : sampleAssetId(brushAssetIds(state.tool)) };
        if (state.tool === 'wall') {
            gesture.rawStart = point; gesture.snap = state.snap;
            const wall = snapWallSegment(state.document, point, point, { snap: gesture.snap });
            const anchor = snapWallPoint(state.document, point, { layerId: gesture.layerId, tolerance: Math.min(.35, 10 / camera.scale) });
            gesture.start = anchor.snapped ? { x: anchor.x, y: anchor.y } : { x: wall.x1, y: wall.y1 };
            gesture.point = { ...gesture.start };
            gesture.rawStart = { ...gesture.start };
        }
        ghost(); return true;
    }
    function brushObject() {
        const { start, point, tool, layerId } = gesture;
        const base = { id: gesture.id, layerId, assetId: gesture.assetId };
        if (tool === 'region') return { ...createRegion(state.document, start, point,
            { id: gesture.id, layerId, name: t('Region'), snap: state.snap }) };
        if (tool === 'light') return { ...nativeFactory(tool, state.nativeChoices[tool], point.x, point.y), id: base.id, layerId, brightRadius: state.brush.lightRadius,
            dimRadius: state.brush.lightDimRadius, color: state.brush.lightColor, intensity: state.brush.lightIntensity,
            enabled: true, rotation: state.brush.lightRotation, angle: state.brush.lightAngle,
            animation: state.brush.lightAnimation, elevation: state.brush.lightElevation };
        if (['particle', 'shader'].includes(tool)) return { ...nativeFactory(tool, state.nativeChoices[tool], point.x, point.y), id: base.id, layerId };
        if (tool === 'decoration') {
            const dragged = Math.hypot(point.x - start.x, point.y - start.y) > .1;
            const width = Math.min(state.document.columns, dragged ? Math.max(.05, Math.abs(point.x - start.x)) : state.brush.width);
            const height = Math.min(state.document.rows, dragged ? Math.max(.05, Math.abs(point.y - start.y)) : state.brush.height);
            const object = { ...base, x: clamp(dragged ? Math.min(start.x, point.x) : start.x, 0, state.document.columns - width),
                y: clamp(dragged ? Math.min(start.y, point.y) : start.y, 0, state.document.rows - height), width, height, rotation: state.brush.rotation };
            return object.assetId ? object : { ...object, empty: true, name: t('Empty Object'), lever: { state: 'off' } };
        }
        return { ...base, x1: start.x, y1: start.y, x2: point.x, y2: point.y, thickness: state.brush.thickness,
            ...(tool === 'door' ? { state: 'closed' } : {}) };
    }
    function ghost() {
        const container = $('[data-builder-ghost]'); container.replaceChildren();
        if (gesture?.marquee && gesture.dragged) {
            container.append(svg('rect', { x: Math.min(gesture.start.x, gesture.point.x), y: Math.min(gesture.start.y, gesture.point.y),
                width: Math.abs(gesture.start.x - gesture.point.x), height: Math.abs(gesture.start.y - gesture.point.y),
                fill: '#c09a5a22', stroke: '#e4bf76', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', 'data-builder-marquee': '' }));
            return;
        }
        if (!gesture?.tool) return;
        const shape = objectNode(kindForTool(gesture.tool), brushObject());
        shape.setAttribute('opacity', .65); container.append(shape);
        if (isNativeKind(kindForTool(gesture.tool))) {
            const candidate = { ...state.document, [kindForTool(gesture.tool)]: [...(state.document[kindForTool(gesture.tool)] || []), brushObject()] };
            updateNativePreview(candidate);
        }
    }
    function move(point, event) {
        if (brushResize) { resizeBrush(event); return; }
        if (wallControls?.active) { wallControls.move(point); return; }
        if (terrainPainter?.active) { terrainPainter.move(point); return; }
        if (gesture?.pendingEdit) {
            const pending = gesture.pendingEdit;
            if (Math.hypot(point.x - pending.point.x, point.y - pending.point.y) < 4 / camera.scale) return;
            gesture = undefined;
            start(pending.point, pending.event, true); move(point); return;
        }
        if (floorPainter.active) { floorPainter.move(['brush', 'fill'].includes(state.paintMode) ? point : bounded(point, false, floorSnap())); return; }
        if (!gesture) return;
        if (gesture.marquee) {
            gesture.point = point;
            gesture.dragged ||= Math.hypot(point.x - gesture.start.x, point.y - gesture.start.y) > 4 / camera.scale;
            if (gesture.dragged) {
                const rect = { x: Math.min(gesture.start.x, point.x), y: Math.min(gesture.start.y, point.y),
                    width: Math.abs(point.x - gesture.start.x), height: Math.abs(point.y - gesture.start.y) };
                setSelection([...(gesture.additive ? gesture.previous : []), ...objectsInRectangle(state.document, rect).filter(ref => state.layers[ref.kind])]);
                renderSelection();
            }
            ghost(); return;
        }
        const wall = gesture.tool === 'wall' && snapWallSegment(state.document, gesture.rawStart, point, { snap: gesture.snap });
        let next = wall ? { x: wall.x2, y: wall.y2 } : bounded(point, gesture.tool === 'floor');
        if (wall) {
            if (gesture.snap) {
                if (Math.abs(point.x - gesture.start.x) >= Math.abs(point.y - gesture.start.y)) next.y = gesture.start.y;
                else next.x = gesture.start.x;
            }
            const anchor = snapWallPoint(state.document, next, { layerId: gesture.layerId, tolerance: Math.min(.35, 10 / camera.scale) });
            if (anchor.snapped) next = { x: anchor.x, y: anchor.y };
        }
        if (gesture.tool) { gesture.point = next; ghost(); return; }
        const delta = gesture.snapWalls ? { x: Math.round(point.x - gesture.rawStart.x), y: Math.round(point.y - gesture.rawStart.y) }
            : { x: next.x - gesture.start.x, y: next.y - gesture.start.y };
        if (!delta.x && !delta.y && !gesture.moved) return;
        state.document = clone(gesture.before);
        const moved = translateSelection(state.document, gesture.refs, delta.x, delta.y, { snapStep: gesture.snapWalls ? 1 : 0 });
        gesture.moved ||= moved;
        renderCanvas();
    }
    function end(point, event) {
        if (brushResize) { resizeBrush(event); finishBrushResize(); return; }
        if (wallControls?.active) { wallControls.end(point); return; }
        if (terrainPainter?.active) { terrainPainter.end(point); return; }
        if (floorPainter.active) { floorPainter.end(['brush', 'fill'].includes(state.paintMode) ? point : bounded(point, false, floorSnap())); return; }
        if (!gesture) return;
        move(point);
        if (floorPainter.active) { floorPainter.end(['brush', 'fill'].includes(state.paintMode) ? point : bounded(point, false, floorSnap())); return; }
        if (!gesture) return;
        if (gesture.pendingEdit) {
            const target = gesture.pendingEdit.target; gesture = undefined;
            setSelection([target]); renderSelection(); renderProperties(); return;
        }
        if (gesture.tool) {
            const kind = kindForTool(gesture.tool), item = brushObject();
            if (kind === 'doors' && !doorFits(state.document, item)) {
                if (length(item) > 0) notify(t('Keep objects inside the map. Doors must be 0.25 to 20 cells long and cannot overlap another door.'), [], 'error');
            } else if (kind === 'walls' && length(item) >= .1) {
                const result = addWall(state.document, item, { maxObjects: state.limits.maxObjects || 2000 });
                if (!result.ok) notify(t(result.error), [], 'error');
                else if (result.changed) setSelection([{ kind, id: item.id }].filter(ref => itemFor(ref)).concat(
                    state.document.walls.some(wall => wall.id === item.id) ? [] : result.refs.slice(0, 1)));
            } else if (kind !== 'walls' && (!['doors'].includes(kind) || length(item) >= .1)) {
                (state.document[kind] ||= []).push(item);
                if (!fitsBounds(state.document)) {
                    state.document[kind].pop(); notify(t('Keep objects inside the map.'), [], 'error');
                } else setSelection([{ kind, id: item.id }]);
            }
        }
        const changed = gesture.tool || gesture.moved;
        gesture = undefined; $('[data-builder-ghost]').replaceChildren();
        if (changed) { commit(); renderCanvas(); }
        renderLayers(); renderProperties();
    }
    function cancel() {
        finishBrushResize(true);
        terrainPainter?.cancel(); clearTerrainPreview();
        floorPainter?.cancel();
        wallControls?.cancel();
        if (gesture) state.document = gesture.before;
        gesture = undefined; $('[data-builder-ghost]').replaceChildren(); renderCanvas(); renderLayers(); renderProperties();
    }
    floorPainter = createFloorPainter({
        getDocument: () => state.document,
        getOptions: () => ({ mode: state.paintMode, size: state.paintMode === 'brush' ? state.brush.floorSize : 1, layerId: state.activeLayer,
            // Legacy projects retain their source metadata, but all new edits use Tiles semantics.
            snap: floorSnap(), editingMode: 'tiles',
            operation: state.paintOperation, shape: state.brushShape, anchor: !floorSnap() || state.brushShape === 'circle' ? 'center' : 'corner',
            assetIds: brushAssetIds('floor'), rotation: Math.round(state.brush.rotation / 90) * 90 % 360,
            maxObjects: state.limits.maxObjects || 2000 }),
        onPreview: (candidate, metadata) => {
            ensureTexturePatterns(new Set(candidate.floors.filter(item => item.assetId).map(item => `${item.assetId}-${item.rotation || 0}`)));
            renderFloors(candidate); renderLayerVisibility();
            const guide = $('[data-builder-ghost]'); guide.replaceChildren();
            if (metadata.mode === 'polygon') {
                const points = [...metadata.vertices, metadata.cursor];
                guide.append(svg('polyline', { points: points.map(point => `${point.x},${point.y}`).join(' '), fill: 'none',
                    stroke: metadata.invalid ? '#e08b80' : '#e4bf76', 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke' }));
            }
            renderPaintControls();
        },
        onCommit: (document, refs) => {
            state.document = document; setSelection(refs); commit(); renderCanvas(); renderLayers(); renderProperties();
            $('[data-builder-ghost]').replaceChildren(); renderPaintControls();
        },
        onCancel: () => { $('[data-builder-ghost]').replaceChildren(); renderCanvas(); renderPaintControls(); },
        onError: message => notify(t(message), [], 'error'),
    });
    terrainPainter = createTerrainPainter({
        getDocument: () => state.document,
        getOptions: () => ({ layerId: state.activeLayer, size: state.terrainBrush.size, hardness: state.terrainBrush.hardness,
            intensity: state.terrainBrush.intensity, operation: state.paintOperation, assetIds: brushAssetIds('floor'),
            rotation: Math.round(state.brush.rotation / 90) * 90 % 360, maxObjects: state.limits.maxObjects || 2000 }),
        onPreview: (candidate, metadata) => {
            terrainPreview = { candidate, metadata };
            if (terrainPreviewFrame !== undefined) return;
            terrainPreviewFrame = requestAnimationFrame(() => {
                terrainPreviewFrame = undefined;
                if (disposed || !terrainPreview) return;
                const { candidate, metadata } = terrainPreview; terrainPreview = undefined;
                ensureTexturePatterns(new Set(candidate.floors.filter(item => item.assetId).map(item => `${item.assetId}-${item.rotation || 0}`)));
                renderFloors(candidate); renderLayerVisibility(); renderBrushCursor(metadata.cursor, metadata);
            });
        },
        onCommit: (document, refs) => {
            clearTerrainPreview(); state.document = document; setSelection(refs); commit(); renderCanvas(); renderLayers(); renderProperties();
            $('[data-builder-ghost]').replaceChildren();
        },
        onCancel: () => { clearTerrainPreview(); $('[data-builder-ghost]').replaceChildren(); if (!disposed) renderCanvas(); },
        onError: message => notify(t(message), [], 'error'),
    });
    wallControls = createWallControls({
        getDocument: () => state.document, setDocument: document => { state.document = document; },
        getScale: () => camera?.scale || 1, getSnap: () => state.snap, getSelection: selectionRefs,
        enabled: () => !busy && !state.preview && ['select', 'wall'].includes(state.tool),
        maxObjects: () => state.limits.maxObjects || 2000, t,
        onPreview: () => { renderCanvas(); },
        onCommit: refs => { if (refs?.length) setSelection(refs.slice(0, 1)); hideNotice(); commit(); renderCanvas(); renderLayers(); renderProperties(); },
        onError: message => notify(t(message), [], 'error'),
        onArmed: () => notify(t('Click to extend the wall. Esc cancels.'), [['Cancel', () => wallControls.cancel()]]),
        onCancel: hideNotice,
        onFocus: () => viewport.focus({ preventScroll: true }),
    });
    viewport.addEventListener('keydown', event => wallControls.keydown(event), { signal, capture: true });
    root.addEventListener('pointerdown', event => {
        if (wallControls.active && !viewport.contains(event.target)) wallControls.cancel();
    }, { signal, capture: true });
    camera = mountViewport(root, { isPan: () => state.preview || state.tool === 'pan', start, move, end, cancel });
    nativeEffects = mountNativeEffects({ host: $('[data-builder-native-effects]'), svg: $('[data-builder-canvas]'),
        onError: cause => { if (!disposed) notify(t(cause.message || String(cause)), [], 'error'); } });
    const syncGuides = () => $('[data-builder-guides]').setAttribute('viewBox', $('[data-builder-canvas]').getAttribute('viewBox') || '0 0 40 30');
    const guideObserver = new MutationObserver(() => { syncGuides(); renderSelection(); });
    guideObserver.observe($('[data-builder-canvas]'), { attributes: true, attributeFilter: ['viewBox'] }); syncGuides();
    viewport.addEventListener('pointermove', event => {
        if (busy || state.preview) return;
        const matrix = $('[data-builder-canvas]').getScreenCTM(); if (!matrix) return;
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
        if (wallControls.armed) { if (!viewport.hasPointerCapture(event.pointerId)) wallControls.move(point); return; }
        if (state.tool !== 'floor' || brushResize) return;
        if (floorPainter.polygon) floorPainter.move(bounded(point, false, floorSnap()));
        else if (!floorPainter.active && !terrainPainter.active && !gesture && !viewport.classList.contains('is-panning')) renderBrushCursor(point);
    }, { signal });
    function renderBrushCursor(point, metadata) {
        const guide = $('[data-builder-ghost]'); guide.replaceChildren();
        if (point.x < 0 || point.y < 0 || point.x >= state.document.columns || point.y >= state.document.rows) return;
        const layer = state.document.layers.find(item => item.id === state.activeLayer);
        if (!brushResize && (!layerVisible(layer) || layer.locked)) return;
        if (state.samplingFloor) {
            guide.append(svg('circle', { cx: point.x, cy: point.y, r: 7 / camera.scale, fill: 'none', stroke: '#e4bf76', 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke', 'data-builder-brush-cursor': '' })); return;
        }
        if (terrainMode()) {
            const radius = state.brush.floorSize / 2, color = metadata?.invalid || state.paintOperation === 'erase' ? '#e08b80' : '#e4bf76';
            const style = { cx: point.x, cy: point.y, fill: 'none', stroke: color, 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', 'pointer-events': 'none' };
            guide.append(svg('circle', { ...style, r: radius, 'data-builder-brush-cursor': '', 'data-builder-brush-operation': state.paintOperation }));
            if (state.terrainBrush.hardness > 0 && state.terrainBrush.hardness < 1) guide.append(svg('circle', {
                ...style, r: radius * state.terrainBrush.hardness, 'stroke-dasharray': '3 3', opacity: .65 }));
            return;
        }
        if (!['brush', 'fill'].includes(state.paintMode)) return;
        const erase = state.paintOperation === 'erase';
        if (!floorSnap() && state.paintMode === 'brush') {
            const rings = floorFreeContours(state.document, { mode: 'brush', start: point, end: point, points: [point],
                size: state.brush.floorSize, shape: state.brushShape, anchor: 'center' });
            for (const ring of rings) guide.append(svg('path', { d: ringPath(ring),
                fill: erase ? '#e08b8029' : '#e4bf7629', stroke: erase ? '#e08b80' : '#e4bf76',
                'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', 'data-builder-brush-cursor': '', 'data-builder-brush-operation': state.paintOperation }));
            return;
        }
        if (!floorSnap()) return;
        const cells = floorBrushCells(state.document, point, point, state.paintMode === 'brush' ? state.brush.floorSize : 1,
            { shape: state.brushShape, anchor: state.brushShape === 'circle' ? 'center' : 'corner' });
        guide.append(svg('path', { d: cells.map(cell => `M${cell.x} ${cell.y}h1v1h-1Z`).join(' '),
            fill: erase ? '#e08b8029' : '#e4bf7629', stroke: erase ? '#e08b80' : '#e4bf76',
            'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', 'data-builder-brush-cursor': '', 'data-builder-brush-operation': state.paintOperation }));
    }
    function ringPath(ring) { return ring.length ? 'M' + ring.map(([x, y]) => `${x} ${y}`).join('L') + 'Z' : ''; }
    viewport.addEventListener('pointerleave', () => { if (!floorPainter.active && !terrainPainter.active && !gesture && !brushResize) $('[data-builder-ghost]').replaceChildren(); }, { signal });
    // Map picking for the blueprint editor: the modal is suspended while the GM
    // clicks a door or light on the canvas; Escape or Cancel resumes it unchanged.
    let picking = null;
    function pickOnMap(kind, exclude) {
        picking?.finish(null);
        return new Promise(resolve => {
            const finish = id => {
                if (picking?.finish !== finish) return;
                picking = null; hideNotice(); viewport.classList.remove('is-picking'); resolve(id);
            };
            picking = { kind, exclude, finish };
            viewport.classList.add('is-picking'); viewport.focus({ preventScroll: true });
            notify(t(kind === 'elements' ? 'Click a live object, door or region on the map. Esc cancels.'
                : kind === 'doors' ? 'Click a door on the map. Esc cancels.' : 'Click a light on the map. Esc cancels.'),
                [['Cancel', () => finish(null)]]);
        });
    }
    viewport.addEventListener('pointerdown', event => {
        if (!picking) return;
        event.preventDefault(); event.stopImmediatePropagation();
        const matrix = $('[data-builder-canvas]').getScreenCTM(); if (!matrix) return;
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
        const target = hit(point, event);
        const matches = target && (target.kind === picking.kind || picking.kind === 'elements'
            && (['regions', 'doors', 'decorations'].includes(target.kind) || ['floors', 'walls'].includes(target.kind) && itemFor(target)?.dynamic === true));
        if (matches && target.id !== picking.exclude) picking.finish(target.id);
    }, { signal, capture: true });
    document.addEventListener('keydown', event => {
        if (!picking || event.key !== 'Escape') return;
        event.preventDefault(); event.stopImmediatePropagation(); picking.finish(null);
    }, { signal, capture: true });
    viewport.addEventListener('dblclick', event => {
        if (picking) { event.preventDefault(); return; }
        if (floorPainter.polygon) { event.preventDefault(); floorPainter.finish(); return; }
        if (busy || state.preview || activeModal) return;
        const matrix = $('[data-builder-canvas]').getScreenCTM(); if (!matrix) return;
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
        const target = hit(point, event);
        if ((isNativeKind(target?.kind) || target?.kind === 'walls') && !event.target.closest('.map-builder__wall-control')) {
            event.preventDefault(); void openNativeEditor(target); return;
        }
        if (!['doors', 'regions'].includes(target?.kind) && !(target?.kind === 'decorations' && isSmartDecoration(itemFor(target)))) return;
        event.preventDefault(); openBehavior(target);
    }, { signal });
    function applyNativeItem(target, next) {
        if (disposed || state.preview || !editable(target)) throw new Error(t('Choose a visible, unlocked object.'));
        const current = itemFor(target);
        if (sameDocument(current, next)) return;
        const candidate = { ...state.document, [target.kind]: state.document[target.kind].map(item => item.id === target.id ? next : item) };
        if (!fitsBounds(candidate)) throw new Error(t('Keep objects inside the map.'));
        state.document = candidate;
        commit(); renderCanvas(); renderLayers(); renderProperties();
    }
    async function openNativeEditor(target, { keepSelection = false } = {}) {
        if (busy || state.preview || activeModal || openingNativeEditor || disposed || !target || !editable(target) || !hasNativeEditor(target.kind)) return;
        const trigger = document.activeElement;
        const fromPanel = trigger?.matches('[data-builder-edit-native], [data-builder-edit-torch-component]');
        const restoreFocus = () => {
            const component = trigger?.dataset.builderEditTorchComponent;
            if (!disposed) (fromPanel ? (component ? $(`[data-builder-edit-torch-component="${component}"]`) : $('[data-builder-edit-native]')) || viewport : viewport).focus({ preventScroll: true });
        };
        cancelDrawing(); if (!keepSelection) setSelection([target]); renderSelection(); renderProperties();
        openingNativeEditor = true; setBusy(true);
        try {
            const native = isNativeKind(target.kind);
            const module = await (native ? import('../builder-editors.js') : import('../wall-editor.js'));
            if (disposed || state.preview || !editable(target)) return;
            const original = clone(itemFor(target));
            if (native) {
                activeModal = module.openBuilderNativeEditor({ kind: target.kind, item: original, t,
                    onSave: next => applyNativeItem(target, next),
                    onPreview: next => {
                        if (disposed) return;
                        updateNativePreview(next ? { ...state.document,
                            [target.kind]: state.document[target.kind].map(item => item.id === target.id ? next : item) } : state.document);
                    },
                    onClose: () => { activeModal = null; if (!disposed) updateNativePreview(); restoreFocus(); },
                });
            } else {
                const baseline = wallProperties(original);
                const modal = module.createWallEditor({ ...original, kind: target.kind === 'doors' ? 'door' : 'wall', ...nativeWallProperties(original) }, {
                    transactional: true, t,
                    onSave: patch => {
                        const next = clone(original);
                        for (const key of wallPropertyFields) if (!sameDocument(baseline[key], patch[key])) next[key] = clone(patch[key]);
                        if (target.kind === 'doors' && 'interactionEnabled' in patch) {
                            if (patch.interactionEnabled) delete next.interactionEnabled; else next.interactionEnabled = false;
                        }
                        if (target.kind === 'doors' && 'rotationAnchor' in patch) {
                            if (patch.rotationAnchor === null) delete next.rotationAnchor; else next.rotationAnchor = patch.rotationAnchor;
                        }
                        applyNativeItem(target, next); modal.close(true);
                    },
                    onClose: () => { if (!modal.querySelector('fieldset').disabled) modal.close(); },
                });
                modal.classList.add('map-builder-native-wall-editor'); modal.dataset.builderNativeEditor = target.kind;
                modal.addEventListener('close', () => { modal.dispose(); activeModal = null; restoreFocus(); }, { once: true });
                activeModal = mountModal(modal, { canClose: () => !modal.querySelector('fieldset').disabled });
            }
        } catch (error) { if (!disposed) notify(t(error.message || 'Could not load the editor.'), [], 'error'); }
        finally { openingNativeEditor = false; if (!disposed) setBusy(false); }
    }
    function behaviorElements() {
        return [
            ...state.document.doors.map((item, index) => ({ ...item, kind: 'door', sourceKind: 'doors', editable: editable({ kind: 'doors', id: item.id }), name: item.name || `${t('Door')} ${index + 1}` })),
            ...state.document.decorations.filter(item => item.lever).map((item, index) => ({ ...item, kind: 'lever', sourceKind: 'decorations', editable: editable({ kind: 'decorations', id: item.id }), state: item.lever.state, name: item.name || `${t(item.empty ? 'Empty Object' : 'Lever')} ${index + 1}` })),
            ...state.document.decorations.filter(item => item.torch).map((item, index) => ({ ...item, kind: 'torch', sourceKind: 'decorations', editable: editable({ kind: 'decorations', id: item.id }), state: item.torch.state, name: item.name || `${t('Torch')} ${index + 1}` })),
            ...state.document.decorations.filter(item => !isSmartDecoration(item)).map((item, index) => ({ ...item, kind: 'image', state: null,
                name: item.name || (item.assetId && assetById(item.assetId) ? assetName(assetById(item.assetId)) : `${t('Object')} ${index + 1}`) })),
            ...(state.document.regions || []).map(item => ({ ...regionInstance(item), sourceKind: 'regions', editable: editable({ kind: 'regions', id: item.id }) })),
            ...['floors', 'walls'].flatMap(kind => state.document[kind].filter(item => item.dynamic === true).map((item, index) => ({ ...item, kind: 'image', editable: false, state: null,
                name: item.name || `${t(kind === 'floors' ? 'Dynamic floor' : 'Dynamic wall')} ${index + 1}` }))),
        ];
    }
    function behaviorMaterials() {
        return state.document.assets.map(entry => {
            const asset = assetById(entry.assetId); return asset && { ...asset, role: entry.role, name: assetName(asset) };
        }).filter(Boolean);
    }
    function renderTestPreview(host, source, result) {
        const projected = projectTestDocument(source, result);
        let closed = false, renderer;
        function paint() {
            if (closed) return;
            renderer?.dispose(); host.replaceChildren();
            const previous = { document: state.document, preview: state.preview };
            let canvas;
            try {
                state.document = projected; state.preview = true; renderCanvas();
                canvas = $('[data-builder-canvas]').cloneNode(true);
            } finally { Object.assign(state, previous); renderCanvas(); }
            // Isolate SVG resources so two maps can display different materials at once.
            const ids = new Map(), prefix = `test-${crypto.randomUUID()}-`;
            for (const node of canvas.querySelectorAll('[id]')) { const old = node.id; ids.set(old, prefix + old); node.id = prefix + old; }
            for (const node of [canvas, ...canvas.querySelectorAll('*')]) for (const attr of [...node.attributes]) {
                let value = attr.value.replace(/url\(#([^)]*)\)/g, (match, id) => ids.has(id) ? `url(#${ids.get(id)})` : match);
                if (value.startsWith('#') && ids.has(value.slice(1))) value = '#' + ids.get(value.slice(1));
                if (value !== attr.value) node.setAttribute(attr.name, value);
            }
            canvas.removeAttribute('data-builder-canvas'); canvas.setAttribute('viewBox', `0 0 ${source.columns} ${source.rows}`);
            canvas.removeAttribute('style'); canvas.setAttribute('aria-hidden', 'true');
            for (const node of canvas.querySelectorAll('[data-builder-selection],[data-builder-drawing]')) node.remove();
            for (const token of result?.changes?.tokens || []) if (token.after) canvas.append(svg('circle', {
                cx: token.after.grid_x + .5, cy: token.after.grid_y + .5, r: .35, fill: '#7ecabb', stroke: '#fff', 'stroke-width': .04,
                'data-playtest-token-position': token.id,
            }));
            const effects = document.createElement('div'); effects.className = 'playtest__effects'; host.append(canvas, effects);
            renderer = mountNativeEffects({ host: effects, svg: canvas, onError: error => {
                const message = document.createElement('p'); message.textContent = t(error.message || 'Could not render native effects.'); message.setAttribute('role', 'alert'); host.append(message);
            } });
            renderer.update(projected);
        }
        testPreviewRefresh = paint; paint();
        return () => { closed = true; if (testPreviewRefresh === paint) testPreviewRefresh = undefined; renderer?.dispose(); };
    }
    $('[data-builder-test]').addEventListener('click', async () => {
        if (busy || activeModal) return;
        flushFocusedField(); cancelDrawing();
        const source = clone(state.document), elements = behaviorElements(), http = new HttpClient();
        setBusy(true);
        try {
            const catalog = await http.get(base + '/testing-catalog', { signal });
            if (disposed) return;
            activeModal = openPlaytest({ elements, actors: catalog.actors, draft: true, t, initialElement: state.selection?.id,
                execute: (owner, event, actor, requestId, signal) => http.post(base + '/test', {
                    request_id: requestId, document: source, elementId: owner.id, event, ...(actor ? { actorId: actor } : {}),
                }, { signal }),
                preview: (host, result) => renderTestPreview(host, source, result), onClose: () => { activeModal = null; },
            });
        } catch (error) { if (!disposed) notify(t(error.message || 'Could not run the test.'), [], 'error'); }
        finally { if (!disposed) setBusy(false); }
    }, { signal });
    $('[data-builder-uvtt-import]').addEventListener('click', () => {
        if (busy || activeModal) return;
        flushFocusedField(); cancelDrawing();
        activeModal = openUniversalVtt({ campaignId: root.dataset.campaignId, folderId: state.folderId, t });
        activeModal.addEventListener('close', () => { activeModal = null; }, { once: true });
    }, { signal });
    $('[data-builder-network]').addEventListener('click', () => {
        if (busy || state.preview || activeModal) return;
        cancelDrawing();
        activeModal = openSceneNetwork({ campaignId: root.dataset.campaignId, t, pick: pickOnMap,
            load: async () => ({ elements: behaviorElements(), assets: behaviorMaterials(), materials: behaviorMaterials(), lights: state.document.lights,
                sounds: state.sounds || [], users: state.users || [], handouts: state.handouts || [] }),
            save: async (owner, blueprint) => {
                const target = { kind: owner.sourceKind, id: owner.id }, item = itemFor(target);
                if (!item || !editable(target)) throw new Error(t('Choose a visible, unlocked object.'));
                if (!sameDocument(item.blueprint, blueprint)) { item.blueprint = blueprint; commit(); renderCanvas(); renderProperties(); }
                await saveCurrent({ settings: false, retry: true });
            }, discard: (owner, blueprint) => {
                const item = itemFor({ kind: owner.sourceKind, id: owner.id }); if (!item) return;
                if (blueprint === undefined) delete item.blueprint; else item.blueprint = blueprint;
                commit(); renderCanvas(); renderProperties();
                if (autosave.state.status === 'error') autosave.retry();
            }, onClose: () => { picking?.finish(null); activeModal = null; },
        });
    }, { signal });
    function openBehavior(target) {
        if (busy || state.preview || activeModal || !target || !editable(target)) return;
        const object = itemFor(target);
        if (!['doors', 'regions'].includes(target.kind) && !(target.kind === 'decorations' && isSmartDecoration(object))) return;
        cancelDrawing(); setSelection([target]); renderSelection(); renderProperties();
        const kind = target.kind === 'regions' ? 'region' : target.kind === 'doors' ? 'door' : object.torch ? 'torch' : 'lever';
        const elements = behaviorElements();
        const assets = state.document.assets.filter(entry => entry.role === (kind === 'door' ? 'door' : 'decoration')).map(entry => {
            const asset = assetById(entry.assetId); return asset && { ...asset, name: assetName(asset) };
        }).filter(Boolean);
        activeModal = openBlueprintEditor({ element: elements.find(item => item.id === object.id), elements,
            assets, materials: behaviorMaterials(), campaignId: root.dataset.campaignId, linkedScene: Boolean(state.sceneId), users: state.users || [], handouts: state.handouts || [],
            lights: state.document.lights, sounds: state.sounds || [], t, pick: pickOnMap,
            onSave: async blueprint => {
                const current = itemFor(target); if (!current || !editable(target)) throw new Error(t('Choose a visible, unlocked object.'));
                if (!sameDocument(current.blueprint, blueprint)) { current.blueprint = blueprint; commit(); renderCanvas(); renderProperties(); }
                await saveCurrent({ settings: false, retry: true });
            }, onDiscard: blueprint => {
                const current = itemFor(target); if (!current) return;
                if (blueprint === undefined) delete current.blueprint; else current.blueprint = blueprint;
                commit(); renderCanvas(); renderProperties();
                if (autosave.state.status === 'error') autosave.retry();
            }, onClose: () => { picking?.finish(null); activeModal = null; },
        });
    }
    async function refreshLibrary(result = null) {
        result ||= await api(); if (disposed) return;
        state.assets = result.assets; state.sounds = result.sounds || []; state.users = result.users || []; state.handouts = result.handouts || [];
        state.projects = result.projects; state.limits = result.limits || {};
        renderAssets(); renderProjects(); renderCanvas();
    }
    function updateURL() {
        const url = new URL(location.href); url.searchParams.set('project', state.id);
        if (state.folderId) url.searchParams.set('folder', state.folderId); else url.searchParams.delete('folder');
        window.history.replaceState(null, '', url);
    }
    function acceptProject(project) {
        const previousId = state.id;
        state.pending = new Map([...state.pending].filter(([key]) => !key.startsWith('/projects/' + previousId + ':')));
        state.saveAttempt = null; state.recoveryConflict = false;
        state.assetRemovals = []; state.soloLayer = null; state.samplingFloor = false;
        state.id = project.id; state.version = project.version; state.folderId = project.folderId;
        state.document = normalizeDocument(project.document); state.saved = JSON.stringify(state.document); setSelection([]);
        state.activeLayer = state.document.layers[0]?.id || null; state.expandedLayers = []; projectMetadata(project, true);
        state.selectedAssets = { floor: null, wall: null, door: null, decoration: null };
        state.selectedFamilies = { floor: null, wall: null, door: null, decoration: null }; undo.reset(state.document);
        startAutosave();
        updateURL(); rememberDraft(); renderForm(); renderAssets(); renderProjects(); renderCanvas(); renderLayers(); renderProperties();
        camera.resize(state.document.columns, state.document.rows, state.document.cellSize); setMobilePanel('workspace');
    }
    function openProject(id) { return run(async () => { const result = await api('/projects/' + id); acceptProject(result.project); hideNotice(); }); }
    async function saveCurrent({ settings = true, retry = false } = {}) {
        if (!ready) {
            const cause = new Error(t('The editor is still loading. Retry loading the project.')); cause.validation = true; throw cause;
        }
        if (state.recoveryConflict) {
            const cause = new Error(t('A previous save could not be confirmed. Reload the saved project or save a copy.')); cause.conflict = true; throw cause;
        }
        if (state.assetRemovals.length) await refreshAfterAssetRemoval(null, { rethrow: true });
        if (!form.checkValidity() || !selectionFieldsValid(true) || settings && !applySettings()) {
            const cause = new Error(t('Check the map settings before saving.')); cause.validation = true; throw cause;
        }
        if (retry && autosave.state.status === 'error') autosave.retry();
        saveBarrier = true;
        try { return await autosave.flush(); }
        finally { saveBarrier = false; }
    }
    function saveCopy() { return run(async () => {
        rememberDraft();
        const previousId = state.id;
        autosave.dispose();
        state.saveAttempt = null; state.recoveryConflict = false;
        state.id = crypto.randomUUID(); state.version = 0; projectMetadata({ sceneId: null, sceneVersion: null, canUpdate: false }, true);
        state.pending = new Map([...state.pending].filter(([key]) => !key.startsWith('/projects/' + previousId + ':')));
        startAutosave();
        await saveCurrent(); hideNotice();
    }); }
    async function confirmLeave(callback) {
        if (busy) return;
        flushFocusedField(); cancelDrawing();
        if (!dirty() && !projectWrite && !state.recoveryConflict && !['error', 'conflict', 'pending', 'saving'].includes(autosave.state.status)) { hideNotice(); return callback(); }
        if (await run(async () => { await saveCurrent({ retry: true }); hideNotice(); })) return callback();
        const cause = state.recoveryConflict ? { conflict: true,
            message: t('A previous save could not be confirmed. Reload the saved project or save a copy.') } : autosave.state.error;
        notify(cause?.message || t('Could not save automatically. Your changes are kept in this tab.'), [
            ...(cause?.conflict ? [['Reload saved project', () => openProject(state.id)], ['Save a copy', saveCopy]] : [['Retry', () => confirmLeave(callback)]]),
            ['Discard changes', () => { autosave.dispose(); discardDraft = true; rememberDraft(); hideNotice(); callback(); }], ['Keep editing', hideNotice],
        ], 'error');
    }
    function freshProject() {
        state.saveAttempt = null; state.recoveryConflict = false;
        state.soloLayer = null; state.samplingFloor = false;
        state.document = newDocument(t('Untitled map'), { layerName: t('Layer 1') }); state.id = crypto.randomUUID(); state.version = 0; state.saved = JSON.stringify(state.document);
        state.folderId = originalFolder; setSelection([]); state.activeLayer = state.document.layers[0].id; state.expandedLayers = [];
        projectMetadata({ sceneId: null, sceneVersion: null, canUpdate: false }, true);
        state.selectedAssets = { floor: null, wall: null, door: null, decoration: null };
        state.selectedFamilies = { floor: null, wall: null, door: null, decoration: null };
        startAutosave();
        undo.reset(state.document); updateURL(); rememberDraft(); renderForm(); renderAssets(); renderCanvas(); renderLayers(); renderProperties();
        camera.resize(state.document.columns, state.document.rows, state.document.cellSize); setMobilePanel('workspace');
    }
    function applySettings() {
        const next = { ...state.document };
        for (const key of ['name', 'columns', 'rows', 'cellSize', 'background']) next[key] = key === 'name' || key === 'background' ? form.elements[key].value : Number(form.elements[key].value);
        if (!next.name.trim() || next.name.length > 120 || !/^#[0-9a-f]{6}$/i.test(next.background)
            || !Number.isInteger(next.columns) || next.columns < 1 || next.columns > 200
            || !Number.isInteger(next.rows) || next.rows < 1 || next.rows > 200
            || !Number.isInteger(next.cellSize) || next.cellSize < 16 || next.cellSize > 256) return false;
        if (!fitsBounds(next) || next.columns * next.rows * next.cellSize ** 2 > (state.limits.maxPixels || 16777216)) {
            notify(t('Keep existing objects inside the map and the output image within 16 megapixels.'), [], 'error'); return false;
        }
        state.document = next; commit(); renderCanvas(); camera.resize(next.columns, next.rows, next.cellSize, false); return true;
    }
    function selectionFieldsValid(report = false) {
        for (const input of root.querySelectorAll('[data-builder-properties] input, [data-builder-properties] select, [data-builder-properties] textarea')) {
            const disabled = input.disabled; input.disabled = false;
            const valid = report ? input.reportValidity() : input.checkValidity(); input.disabled = disabled;
            if (!valid) { if (report) setSidebarTab('selection', true); return false; }
        }
        return true;
    }
    function flushFocusedField() {
        if (busy) return;
        const focused = document.activeElement;
        if (focused === quickName) commitQuickName();
        if (focused?.matches('[data-builder-property], [data-builder-asset-name], [data-builder-asset-collection], [data-builder-layer-title], [data-builder-brush], [data-builder-quick-brush-size]') && focused.checkValidity()) focused.dispatchEvent(new Event('change'));
        if (form.contains(focused) && form.checkValidity()) applySettings();
    }
    function commitQuickName(preserveInput = false) {
        if (busy || state.preview) { quickName.value = state.document.name; return; }
        const name = quickName.value.trim();
        if (!name || name.length > 120) { if (!preserveInput) quickName.value = state.document.name; return; }
        if (!preserveInput) quickName.value = name;
        form.elements.name.value = name;
        if (name === state.document.name) return;
        cancelDrawing(); state.document.name = name;
        commit(); renderCanvas();
        if (state.sidebarTab === 'review') renderReview();
    }
    quickName.addEventListener('blur', () => commitQuickName(), { signal });
    quickName.addEventListener('input', event => { if (!event.isComposing) commitQuickName(true); }, { signal });
    quickName.addEventListener('compositionend', () => commitQuickName(true), { signal });
    quickName.addEventListener('keydown', event => {
        if (event.isComposing || !['Enter', 'Escape'].includes(event.key)) return;
        event.preventDefault(); event.stopPropagation();
        if (event.key === 'Escape') quickName.value = state.document.name;
        else commitQuickName();
        viewport.focus({ preventScroll: true });
    }, { signal });
    function commitQuickBrushSize() {
        if (!quickBrushSize.checkValidity() || !setFloorBrushSize(Number(quickBrushSize.value))) quickBrushSize.value = String(state.brush.floorSize);
    }
    quickBrushSize.addEventListener('change', commitQuickBrushSize, { signal });
    quickBrushSize.addEventListener('blur', commitQuickBrushSize, { signal });
    quickBrushSize.addEventListener('keydown', event => {
        if (event.isComposing || !['Enter', 'Escape'].includes(event.key)) return;
        event.preventDefault(); event.stopPropagation();
        if (event.key === 'Escape') quickBrushSize.value = String(state.brush.floorSize);
        else commitQuickBrushSize();
        viewport.focus({ preventScroll: true });
    }, { signal });
    root.addEventListener('click', event => {
        if (busy || !ready && !event.target.closest('[data-builder-notice], .map-builder__back')) { event.preventDefault(); event.stopImmediatePropagation(); }
    }, { signal, capture: true });
    form.addEventListener('submit', event => event.preventDefault(), { signal });
    form.addEventListener('change', event => {
        if (busy) return;
        if (event.target.name === 'snap') { setSnap(event.target.checked); return; }
        if (event.target.name === 'grid') { state.grid = event.target.checked; renderCanvas(); return; }
        if (!form.reportValidity()) return;
        if (!applySettings()) renderForm();
    }, { signal });
    $('[data-builder-paint-mode]').value = state.paintMode;
    $('[data-builder-paint-mode]').addEventListener('change', event => {
        if (busy || state.preview) return;
        cancelDrawing(); state.paintMode = event.target.value;
        if (state.paintMode === 'fill') state.paintOperation = 'paint';
        setTool(state.tool); rememberDraft();
    }, { signal });
    $('[data-builder-brush-shape]').value = state.brushShape;
    $('[data-builder-brush-shape]').addEventListener('change', event => {
        if (busy || state.preview) return;
        cancelDrawing(); state.brushShape = event.target.value; rememberDraft();
    }, { signal });
    $('[data-builder-paint-operation]').addEventListener('change', event => {
        if (busy || state.preview) return;
        cancelDrawing(); state.paintOperation = event.target.value;
        if (state.paintOperation === 'erase' && state.paintMode === 'fill') {
            state.paintMode = 'brush'; $('[data-builder-paint-mode]').value = 'brush';
        }
        setTool(state.tool); rememberDraft();
    }, { signal });
    $('[data-builder-editing-mode]').addEventListener('change', event => chooseEditingMode(event.target.value), { signal });
    for (const [field, selector] of [['hardness', '[data-builder-terrain-hardness]'], ['intensity', '[data-builder-terrain-intensity]']]) {
        $(selector).addEventListener('change', event => {
            if (busy || state.preview || !event.target.checkValidity()) return;
            cancelDrawing(); state.terrainBrush[field] = Number(event.target.value) / 100; rememberDraft(); renderPaintControls();
        }, { signal });
    }
    $('[data-builder-sample-material]').addEventListener('click', chooseEyedropper, { signal });
    for (const button of root.querySelectorAll('[data-builder-brush-adjust]')) button.addEventListener('click', () => adjustBrush(Number(button.dataset.builderBrushAdjust)), { signal });
    $('[data-builder-polygon-finish]').addEventListener('click', () => { if (!busy && !state.preview) floorPainter.finish(); }, { signal });
    $('[data-builder-polygon-cancel]').addEventListener('click', () => { if (!busy && !state.preview) cancelDrawing(); }, { signal });
    $('[data-builder-active-layer-select]').addEventListener('change', event => activeLayer(event.target.value), { signal });
    for (const [selector, key, value] of [['[data-builder-layers-show-all]', 'visible', true], ['[data-builder-layers-unlock-all]', 'locked', false]]) {
        $(selector).addEventListener('click', () => {
            if (busy || state.preview) return;
            cancelDrawing();
            const changed = state.document.layers.some(layer => layer[key] !== value);
            for (const layer of state.document.layers) layer[key] = value;
            if (key === 'visible') state.soloLayer = null;
            if (changed) commit(); else rememberDraft();
            renderCanvas(); renderLayers(); renderProperties();
        }, { signal });
    }
    $('[data-builder-search]').addEventListener('input', renderAssets, { signal });
    $('[data-builder-collection-filter]').addEventListener('change', event => {
        if (busy || state.preview) { renderAssets(); return; }
        if (state.libraryFilter === 'effect') {
            if (['particle', 'shader'].includes(event.target.value)) setTool(event.target.value);
            else renderAssets();
        } else {
            state.libraryCollection = event.target.value; renderAssets();
        }
        rememberDraft();
    }, { signal });
    $('[data-builder-brush-material]')?.addEventListener('change', event => chooseMaterial(event.target.value), { signal });
    $('[data-builder-native-preset]')?.addEventListener('change', event => chooseNativePreset(state.tool, event.target.value), { signal });
    $('[data-builder-library-toggle]')?.addEventListener('click', () => setLibraryCollapsed(!state.libraryCollapsed), { signal });
    $('[data-builder-close-panel]')?.addEventListener('click', () => setSidebarTab('library'), { signal });
    for (const [selector, field] of [['[data-builder-asset-name]', 'name'], ['[data-builder-asset-collection]', 'collection']]) {
        $(selector).addEventListener('change', event => {
            if (busy || state.preview) return;
            const entry = assetInfo(state.selectedAssets[state.role]); if (!entry) return;
            const value = event.target.value.trim();
            if (value) entry[field] = value; else delete entry[field];
            commit(); renderAssets(); renderLayers(); renderProperties();
        }, { signal });
    }
    for (const input of root.querySelectorAll('[data-builder-brush]')) {
        input.value = String(state.brush[input.dataset.builderBrush]);
        input.addEventListener('change', () => {
            if (busy || state.preview || !input.checkValidity()) return;
            const next = input.type === 'color' || input.tagName === 'SELECT' ? input.value : Number(input.value);
            if (input.dataset.builderBrush === 'floorSize') { setFloorBrushSize(next); return; }
            if (state.brush[input.dataset.builderBrush] === next) return;
            cancelDrawing();
            state.brush[input.dataset.builderBrush] = next;
            rememberDraft();
        }, { signal });
    }
    $('[data-builder-snap-step]').value = String(state.snapStep);
    $('[data-builder-snap-step]').addEventListener('change', event => { state.snapStep = Number(event.target.value); }, { signal });
    $('[data-builder-layer-add]').addEventListener('click', () => {
        if (busy || state.preview) return;
        cancelDrawing();
        if (state.document.layers.length >= 32) { notify(t('This project has reached the layer limit.'), [], 'error'); return; }
        const input = $('[data-builder-layer-name]'), name = input.value.trim();
        if (!name) { notify(t('Name your layer before adding it.')); input.focus(); return; }
        const layer = { id: crypto.randomUUID(), name, visible: true, locked: false };
        state.document.layers.push(layer); state.activeLayer = layer.id; input.value = '';
        if (state.soloLayer) state.soloLayer = layer.id;
        commit(); renderCanvas(); renderLayers(); renderProperties();
    }, { signal });
    $('[data-builder-create-first-layer]').addEventListener('click', requestFirstLayer, { signal });
    $('[data-builder-layer-name]').addEventListener('input', event => {
        $('[data-builder-layer-add]').disabled = busy || state.preview || state.document.layers.length >= 32 || !event.target.value.trim();
    }, { signal });
    $('[data-builder-layer-name]').addEventListener('keydown', event => {
        if (event.key !== 'Enter') return;
        event.preventDefault(); $('[data-builder-layer-add]').click();
    }, { signal });
    $('[data-builder-select-all]').addEventListener('click', selectAll, { signal });
    $('[data-builder-duplicate]').addEventListener('click', () => transformSelection('duplicate'), { signal });
    $('[data-builder-rotate]').addEventListener('click', () => transformSelection('rotate'), { signal });
    $('[data-builder-asset-role]').addEventListener('change', event => {
        const id = state.selectedAssets[state.role], role = event.target.value; if (!id) return;
        // Used material keeps its type; changing a library classification must not invalidate existing geometry.
        const used = assetUsedByOtherRole(id, role);
        if (used) { notify(t('This asset is already used by another brush. Upload a separate copy to use a different type.'), [], 'error'); renderAssets(); return; }
        try { classify(id, role); }
        catch (cause) { notify(cause.message, [], 'error'); renderAssets(); return; }
        state.selectedAssets[state.role] = null; state.selectedAssets[role] = id; commit(); setRole(role);
    }, { signal });
    $('[data-builder-import]').addEventListener('click', () => openImport(), { signal });
    for (const button of root.querySelectorAll('[data-builder-ready-map]')) button.addEventListener('click', openMapImport, { signal });
    for (const button of root.querySelectorAll('[data-builder-empty-object]')) button.addEventListener('click', () => chooseBrushAsset(null, 'decoration'), { signal });
    $('[data-builder-background-remove]').addEventListener('click', () => {
        if (busy || state.preview) return;
        cancelDrawing(); flushFocusedField();
        if (setBackgroundImage(state.document, null)) { commit(); renderCanvas(); }
    }, { signal });
    for (const button of root.querySelectorAll('[data-builder-tool]')) button.addEventListener('click', () => setTool(button.dataset.builderTool), { signal });
    for (const button of root.querySelectorAll('[data-builder-dock-tool]')) button.addEventListener('click', () => {
        if (busy || state.preview) return;
        flushFocusedField();
        const tool = button.dataset.builderDockTool;
        if (tool === 'empty') {
            state.libraryRole = state.libraryFilter = 'decoration';
            chooseBrushAsset(null, 'decoration', true);
        } else { setTool(tool); setSidebarTab('library'); }
        viewport.focus({ preventScroll: true }); rememberDraft();
    }, { signal });
    for (const button of root.querySelectorAll('[data-builder-quick-tool]')) button.addEventListener('click', () => chooseQuickTool(button.dataset.builderQuickTool), { signal });
    for (const button of root.querySelectorAll('[data-builder-role]')) button.addEventListener('click', () => setLibraryRole(button.dataset.builderRole), { signal });
    for (const button of root.querySelectorAll('[data-builder-panel]')) button.addEventListener('click', () => setMobilePanel(button.dataset.builderPanel), { signal });
    for (const button of root.querySelectorAll('[data-builder-sidebar-tab]')) button.addEventListener('click', () => {
        const name = button.dataset.builderSidebarTab;
        const launcher = button.classList.contains('map-builder__layers-toggle');
        setSidebarTab(launcher && !$('.map-builder__library').hidden ? 'library' : name, true);
    }, { signal });
    for (const button of root.querySelectorAll('[data-builder-library-tab]')) {
        if (!button.hasAttribute('data-builder-sidebar-tab')) button.addEventListener('click', () => {
            libraryTab(button.dataset.builderLibraryTab); setSidebarTab(state.sidebarTab, true);
        }, { signal });
    }
    for (const button of root.querySelectorAll('[data-builder-category]')) button.addEventListener('click', () => setCategory(button.dataset.builderCategory), { signal });
    $('[data-builder-preview]').addEventListener('click', () => setPreview(!state.preview), { signal });
    $('[data-builder-toggle-grid]').addEventListener('click', () => {
        state.grid = !state.grid; form.elements.grid.checked = state.grid; renderCanvas();
    }, { signal });
    $('[data-builder-toggle-snap]').addEventListener('click', () => {
        if (!busy && !state.preview) setSnap(!state.snap);
    }, { signal });
    $('[data-builder-undo]').addEventListener('click', () => changeHistory('undo'), { signal });
    $('[data-builder-redo]').addEventListener('click', () => changeHistory('redo'), { signal });
    $('[data-builder-dismiss]').addEventListener('click', hideNotice, { signal });
    $('[data-builder-new]').addEventListener('click', () => confirmLeave(freshProject), { signal });
    $('[data-builder-open]').addEventListener('click', () => {
        if (!$('[data-builder-open]').hasAttribute('data-builder-sidebar-tab')) setSidebarTab('projects', true);
        if (state.sidebarTab === 'projects') run(refreshLibrary);
    }, { signal });
    $('[data-builder-save]').addEventListener('click', () => run(async () => { await saveCurrent({ retry: true }); hideNotice(); }), { signal });
    function applyScene(updateOnly = false) {
        return run(async () => {
            const sceneId = state.sceneId || null, expectedSceneVersion = state.sceneVersion;
            if (updateOnly && !sceneId) throw new Error(t('Generate a scene before updating it.'));
            if (sceneId && !state.canUpdate) throw new Error(t('This scene has no update record. The linked scene cannot be updated.'));
            await saveCurrent();
            if ((state.sceneId || null) !== sceneId) {
                const cause = new Error(t('The generated scene changed. Reload the project before updating it.'));
                cause.conflict = true; throw cause;
            }
            notify(t(sceneId ? 'Updating the linked scene…' : 'Generating a new private scene…'));
            const result = await operation('/projects/' + state.id + (sceneId ? '/update' : '/generate'), {
                expected_version: state.version, ...(sceneId ? { expected_scene_version: expectedSceneVersion } : {}),
            });
            projectMetadata(result.project, true); location.assign($('.map-builder__back').href);
        });
    }
    $('[data-builder-generate]').addEventListener('click', () => applyScene(), { signal });
    $('[data-builder-review-generate]').addEventListener('click', () => $('[data-builder-generate]').click(), { signal });
    $('[data-builder-update]').addEventListener('click', () => applyScene(true), { signal });
    $('[data-builder-review-update]').addEventListener('click', () => $('[data-builder-update]').click(), { signal });
    $('.map-builder__back').addEventListener('click', event => {
        if (busy) { event.preventDefault(); return; }
        const href = event.currentTarget.href; event.preventDefault(); void confirmLeave(() => location.assign(href));
    }, { signal });
    root.addEventListener('keydown', event => {
        if (busy) { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') event.preventDefault(); return; }
        const sidebarTab = event.target.closest('[data-builder-sidebar-tab][role=tab]');
        if (sidebarTab && ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) {
            const tabs = [...root.querySelectorAll('[data-builder-sidebar-tab][role=tab]')].filter(button => !button.hidden);
            const index = tabs.indexOf(sidebarTab);
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
                : (index + ({ ArrowLeft: -1, ArrowRight: 1, ArrowUp: -3, ArrowDown: 3 }[event.key]) + tabs.length) % tabs.length;
            event.preventDefault(); setSidebarTab(tabs[next].dataset.builderSidebarTab, true); tabs[next].focus(); return;
        }
        const typing = event.target.closest('input,select,textarea,[contenteditable=true]');
        if (!typing && event.key === 'Escape' && !activeModal && !picking && !brushResize && !gesture
            && !floorPainter.active && !terrainPainter.active && !wallControls.active && !wallControls.armed
            && !$('.map-builder__library').hidden && $('.map-builder__library').contains(event.target)) {
            event.preventDefault(); setSidebarTab('library'); return;
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
            event.preventDefault();
            if (event.target.matches('[data-builder-property]')) event.target.dispatchEvent(new Event('change'));
            $('[data-builder-save]').click(); return;
        }
        if (!typing && event.key === 'Escape' && state.preview) {
            event.preventDefault(); setPreview(false); return;
        }
        if (state.preview) return;
        if (typing || busy) return;
        if (floorPainter.polygon && event.key === 'Enter' && !event.target.closest('button,a,summary')) { event.preventDefault(); floorPainter.finish(); return; }
        if ((event.ctrlKey || event.metaKey) && ['z', 'y'].includes(event.key.toLowerCase())) {
            event.preventDefault(); changeHistory(event.shiftKey || event.key.toLowerCase() === 'y' ? 'redo' : 'undo'); return;
        }
        if ((event.ctrlKey || event.metaKey) && ['a', 'd'].includes(event.key.toLowerCase())) {
            event.preventDefault(); if (event.key.toLowerCase() === 'a') selectAll(); else transformSelection('duplicate'); return;
        }
        if (event.ctrlKey || event.metaKey || event.altKey) return;
        if (event.key === 'Delete' || event.key === 'Backspace') { event.preventDefault(); deleteSelection(); }
        else if (event.key === 'Escape') { cancelDrawing(); state.samplingFloor = false; renderPaintControls(); setSelection([]); renderSelection(); renderProperties(); }
        else if (event.key === '[' || event.key === ']') { event.preventDefault(); adjustBrush(event.key === '[' ? -1 : 1); }
        else if (event.key.toLowerCase() === 'i') { event.preventDefault(); chooseEyedropper(); }
        else if (event.key.toLowerCase() === 'g' && !terrainMode()) {
            event.preventDefault(); state.paintMode = 'fill'; state.paintOperation = 'paint';
            $('[data-builder-paint-mode]').value = 'fill'; setTool('floor');
        }
        else if (event.key.toLowerCase() === 'r') { event.preventDefault(); transformSelection('rotate'); }
        else if ({ v: 'select', f: 'paint', e: 'erase' }[event.key.toLowerCase()]) {
            event.preventDefault(); chooseQuickTool({ v: 'select', f: 'paint', e: 'erase' }[event.key.toLowerCase()]);
        }
        else if ({ w: 'wall', d: 'door', h: 'pan' }[event.key.toLowerCase()]) {
            setTool({ w: 'wall', d: 'door', h: 'pan' }[event.key.toLowerCase()]);
        }
    }, { signal });
    setMobilePanel('workspace'); renderForm(); renderAssets(); renderProjects(); renderCanvas(); renderLayers(); renderProperties();
    setCategory(state.category, false); setSidebarTab('library'); setLibraryCollapsed(state.libraryCollapsed);
    const preview = state.preview; state.preview = false; setTool(state.tool);
    if (preview) setPreview(true);
    camera.resize(state.document.columns, state.document.rows, state.document.cellSize);
    startAutosave();
    async function loadInitialWorkspace() {
        const result = await run(async () => {
            await refreshLibrary();
            if (state.assetRemovals.length) await refreshAfterAssetRemoval(null, { rethrow: true });
            const initialId = root.dataset.projectId;
            if (!restored && !recovered && !recoveryError && !dirty() && initialId) {
                const result = await api('/projects/' + initialId); acceptProject(result.project);
            }
        });
        if (disposed) return;
        bootstrapFailed = !result;
        if (!result) {
            if (lastFailure?.conflict) {
                ready = true; bootstrapFailed = false; state.recoveryConflict = true;
                notify(lastFailure.message, [['Reload saved project', () => openProject(state.id)], ['Save a copy', saveCopy]], 'error', 'autosave');
                updateSaveState(); return;
            }
            for (const element of root.querySelectorAll('button,input,select,textarea')) if (!element.closest('[data-builder-notice]')) element.disabled = true;
            notify($('[data-builder-notice-text]').textContent || t('The editor is still loading. Retry loading the project.'),
                [['Retry', () => void loadInitialWorkspace()]], 'error');
            updateSaveState(); return;
        }
        ready = true;
        // Older tab drafts retained an operation UUID without its sent body.
        // Such an acknowledgement cannot safely be guessed or marked as saved.
        if (!state.saveAttempt && [...state.pending.keys()].some(key => key.startsWith('/projects/' + state.id + ':'))) state.recoveryConflict = true;
        if (state.recoveryConflict) notify(t('A previous save could not be confirmed. Reload the saved project or save a copy.'), [
            ['Reload saved project', () => openProject(state.id)], ['Save a copy', saveCopy],
        ], 'error', 'autosave');
        else if (dirty() || state.saveAttempt) autosave.schedule();
        updateSaveState();
    }
    void loadInitialWorkspace();
    if (recoveryError) notify(t(recoveryError), [], 'error');
    else if (recovered) notify(t('Recovered unsaved work from this tab.'));
    return () => { if (!discardDraft) flushFocusedField(); cancelDrawing(); disposed = true; autosave.dispose(); activeModal?.close(true); terrainPainter?.dispose(); clearTerrainPreview(); terrainMasks.dispose(); wallArt.dispose(); nativeEffects?.dispose(); guideObserver.disconnect(); camera.dispose(); rememberDraft(); abort.abort(); };
}
if (root) {
    let dispose = mountWorkspace(root);
    addEventListener('pagehide', () => { dispose?.(); dispose = undefined; });
    addEventListener('pageshow', event => { if (event.persisted) { dispose?.(); dispose = mountWorkspace(root); } });
}
