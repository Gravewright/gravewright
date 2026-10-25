import { createTranslator } from '/static/gravewright_modules/i18n.js';
import { mountViewport } from './viewport.js';
import { mountModal } from '/static/gravewright_table/modal.js';
import { createProjectApi, createProjectPersistence, recoverProjectDraft } from './project-persistence.js';
import { createWorkspaceLibrary } from './workspace-library.js';
import { createWorkspaceImport } from './workspace-import.js';
import { createCanvasRenderer, ringPath } from './canvas-renderer.js';
import { createInspectorController } from './inspector-controller.js';
import { createObjectMenu } from './object-menu.js';
import { interactiveObjectPresets } from './interactive-presets.js';
import { defaultBlueprint } from './blueprint-model.js';
import { createLayerController } from './layer-controller.js';
import { createFloorPainter } from './floor-painter.js';
import { createTerrainPainter } from './terrain-painter.js';
import { createWallControls } from './wall-controls.js';
import { addWall, snapWallPoint } from './wall-edit.js';
import { wallProperties, nativeWallProperties, wallPropertyFields } from './wall-properties.js';
import { torchChildren, torchOwner, torchComponentState } from './torch-model.js';
import { createRegion, regionInstance } from './region-model.js';
import { createProductivity } from './productivity.js';
import { openPlayerTest } from './player-test.js';

import { openBlueprintEditor } from './blueprint-editor.js';
import { openSceneNetwork } from './scene-network.js';
import { openPlaytest } from './playtest.js';
import { projectTestDocument } from './playtest-model.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';
import { openUniversalVtt } from '../universal-vtt.js';
import { openReadyMapImport } from './ready-map.js';
import { detachDocumentAsset, sameDocument } from './asset-removal.js';
import { mergeSceneProject } from './scene-sync-model.js';
import { mountNativeEffects } from './native-effects.js';
import { isNativeKind, nativeFactory, nativeCatalog, presetName } from './native-controls.js';

import { clone, clamp, round, length, newDocument, normalizeDocument, nearestWall, doorFits, removeObject, fitsBounds, history, objectKinds, translateSelection, rotateSelection, duplicateSelection, objectsInRectangle, familyAssetIds, sampleAssetId, snapWallSegment, floorBrushCells, sampleFloor, floorFreeContours, floorContainsPoint, documentEditingMode, setEditingMode, setBackgroundImage, documentBounds } from './model.js';

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
    const { recovered, recoveryError } = recoverProjectDraft({ campaignId: root.dataset.campaignId,
        projectId: root.dataset.projectId, folderId: originalFolder });
    const api = createProjectApi({ base, signal, t,
        csrfUrl: document.querySelector('meta[name="gravewright-csrf-url"]')?.content || '/__gravewright/csrf' });
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
    let busy = false, gesture, brushResize, disposed = false, productivity;
    let ready = false, bootstrapFailed = false, lastFailure;
    let filterActorCatalog;
    const filterTokenCatalogs = new Map();
    let camera, drawerTrigger, activeModal, floorPainter, terrainPainter, nativeEffects, wallControls, openingNativeEditor = false;
    const panelScroll = new Map();
    let terrainPreviewFrame, terrainPreview, testPreviewRefresh;
    function clearTerrainPreview() {
        if (terrainPreviewFrame !== undefined) cancelAnimationFrame(terrainPreviewFrame);
        terrainPreviewFrame = terrainPreview = undefined;
    }
    const canvasRenderer = createCanvasRenderer({
        root, getDocument: () => state.document,
        getView: () => ({ preview: state.preview, layers: state.layers, grid: state.grid, soloLayer: state.soloLayer }),
        assetById: id => assetById(id),
        onError: (cause, asset) => notify(asset ? t('Could not load wall artwork: {name}.', { name: assetName(asset) })
            : t(cause.message), [], 'error'),
        onWallArtReady: id => {
            renderLayerVisibility();
            if (gesture?.tool === 'wall' && gesture.assetId === id) ghost();
            testPreviewRefresh?.();
        },
    });
    const { objectNode, ensureTexturePatterns, renderFloors } = canvasRenderer;
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
    const autosave = createProjectPersistence({
        state, campaignId: root.dataset.campaignId, api,
        canSave: ({ flushing }) => ready && !disposed && (!busy || flushing) && !gesture && !brushResize
            && !floorPainter?.active && !floorPainter?.polygon && !terrainPainter?.active && !wallControls?.active
            && !state.assetRemovals.length && form.checkValidity() && selectionFieldsValid(),
        onSaved: project => { projectMetadata(project); updateURL(); renderProjects(); updateSaveState(); },
        onState: value => {
            updateSaveState();
            if (value.status === 'conflict') notify(value.error.message, [
                ['Reload saved project', () => openProject(state.id)], ['Save a copy', saveCopy],
            ], 'error', 'autosave');
            else if (value.status === 'blocked' || value.status === 'error' && !value.retrying) notify(
                value.status === 'blocked' ? value.error.message : t('Could not save automatically. Your changes are kept in this tab.'),
                [['Retry', () => { autosave.retry(); void autosave.flush().catch(() => {}); }]], 'error', 'autosave');
            else if (value.status === 'saved' && $('[data-builder-notice]').dataset.source === 'autosave') hideNotice();
        },
    });
    const { dirty, rememberDraft, operation } = autosave;
    function startAutosave() { autosave.start(); }
    function setBusy(value) {
        if (value) objectMenu?.close(false);
        busy = value; root.setAttribute('aria-busy', String(value));
        for (const element of root.querySelectorAll('button,input,select,textarea')) element.disabled = value;
        if (!value) applyPreviewControls();
        updateSaveState();
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
        try { await autosave.pendingWrite?.catch(() => {}); await callback(); return true; }
        catch (cause) {
            if (cause.name === 'AbortError' || disposed) return;
            lastFailure = cause;
            autosave.keepDraft();
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
    const library = createWorkspaceLibrary({
        root, state, t, locale: () => translator.locale, signal, isBusy: () => busy, commit,
        onBrushChosen: (role, closePanel) => {
            setTool(role); setMobilePanel('workspace'); if (closePanel) setSidebarTab('library');
        },
        renderDockTools, chooseNativePreset, applyPreviewControls, selected,
        openImport: asset => openImport(asset), notify,
        onMaterialChosen: (kind, assetId) => {
            if (!selected() || busy || state.preview) return;
            cancelDrawing();
            const target = selected(); if (!target || target.empty || !assetId && isSmartDecoration(target)) return;
            target.assetId = assetId;
            if (kind === 'floors') delete target.paint;
            state.selectedAssets[roleForKind(kind)] = target.assetId;
            commit(); renderCanvas(); renderLayers(); renderProperties();
        },
    });
    const { assetById, roleFor, assetInfo, assetName, assetUsedByOtherRole, classify,
        familyGroups, brushAssetIds, chooseBrushAsset, chooseFamily, chooseMaterial,
        renderBrushMaterial, renderAssets, renderMaterials } = library;
    const { openImport } = createWorkspaceImport({
        root, state, t, locale: () => translator.locale, signal, isBusy: () => busy, isDisposed: () => disposed,
        beforeOpen: () => { cancelDrawing(); flushFocusedField(); },
        modals: { get current() { return activeModal; }, set current(value) { activeModal = value; }, mount: mountModal },
        setBusy, api, refreshLibrary, removeAsset, renderLayers, openMapImport, library, commit,
    });
    function cancelDrawing() {
        finishBrushResize(true);
        terrainPainter?.cancel(); clearTerrainPreview();
        camera?.cancel();
        floorPainter?.cancel();
        wallControls?.cancel();
        $('[data-builder-ghost]').replaceChildren();
        renderPaintControls();
    }
    async function removeAsset(asset) {
        let catalog;
        if (!state.assetRemovals.includes(asset.id)) state.assetRemovals.push(asset.id);
        rememberDraft();
        await autosave.pendingWrite?.catch(() => {});
        try { await api(`/api/containers/${root.dataset.campaignId}/library/assets/delete`, { asset_id: asset.id }); }
        catch (cause) {
            if (cause.name === 'AbortError' || disposed) throw cause;
            try { catalog = await api(); } catch { throw cause; }
            if (catalog.assets.some(row => row.id === asset.id)) {
                state.assetRemovals = state.assetRemovals.filter(id => id !== asset.id); rememberDraft(); throw cause;
            }
        }
        if (disposed) return;
        if (!catalog) { try { catalog = await api(); } catch { /* Reconcile when the catalog can be read. */ } }
        if (!disposed) await refreshAfterAssetRemoval(catalog);
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
        // Reconcile deleted resources without changing other drafts' revision guards.
        autosave.updateDrafts(draft => {
            draft.document = detach(draft.document);
            if (draft.saved) draft.saved = JSON.stringify(detach(JSON.parse(draft.saved)));
            draft.assetRemovals = [...new Set([...(draft.assetRemovals || []), ...missing])];
        });
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
    function renderLayerVisibility() {
        canvasRenderer.renderLayerVisibility(); updateNativePreview();
    }
    function updateNativePreview(document = state.document) {
        if (!nativeEffects) return;
        const preview = { ...document, layers: document.layers.map(layer => ({ ...layer, visible: state.preview || layerVisible(layer) })) };
        for (const kind of ['lights', 'particles', 'shaders']) preview[kind] = state.preview || state.layers[kind] ? document[kind] || [] : [];
        nativeEffects.update(preview);
    }
    const layerController = createLayerController({
        root, state, t, signal,
        selection: { refs: selectionRefs, item: itemFor, set: setSelection, label: elementLabel, editable },
        library, isBusy: () => busy, cancelDrawing, commit, rememberDraft,
        renderCanvas, renderProperties: () => renderProperties(), renderSelection,
        applyPreviewControls, setSidebarTab, setTool, notify,
    });
    function activeLayer(id) { return layerController.activeLayer(id); }
    function requestFirstLayer() { return layerController.requestFirstLayer(); }
    function updateLayerControls() { layerController.updateLayerControls(); }
    function renderLayers() { layerController.renderLayers(); }
    function projectMetadata(project, replace = false) {
        if (replace || state.sceneId !== project.sceneId) state.sceneVersion = project.sceneVersion;
        state.sceneId = project.sceneId; state.canUpdate = Boolean(project.canUpdate);
        if (replace || Object.hasOwn(project, 'importWarnings')) state.importWarnings = Array.isArray(project.importWarnings) ? project.importWarnings : [];
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
        if (state.document.sceneGeometry) target.append(node('p', { class: 'map-builder__hint' },
            t('Only walls, doors and lights are imported as editable objects. Other scene content remains in the scene.')),
            node('p', { class: 'map-builder__hint' }, t('The original image dimensions and grid are preserved. Disable snapping for precise adjustments to imported geometry.')));
        if (state.importWarnings?.length) {
            const warnings = node('ul', { class: 'map-builder__hint', 'data-builder-import-warnings': '' });
            for (const warning of state.importWarnings) warnings.append(node('li', {}, t(warning)));
            target.append(warnings);
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
    function renderCanvas() {
        const doc = canvasRenderer.render({ wallDraft: gesture?.tool === 'wall' ? brushObject() : undefined });
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
        wallControls?.render(canvasRenderer.renderSelection(selectionRefs(), camera.scale));
        productivity?.drawAreas();
    }
    const objectMenu = createObjectMenu({ t, signal, onError: cause => notify(t(cause.message), [], 'error') });
    const { renderProperties, openProperties, openPreset } = createInspectorController({
        root, state, t, signal, toolHints: strings,
        selection: { refs: selectionRefs, current: selected, item: itemFor, set: setSelection, all: allRefs, label: elementLabel },
        library, isBusy: () => busy, isDisposed: () => disposed,
        commit, renderCanvas, renderLayers, renderSelection, applyPreviewControls,
        chooseQuickTool, deleteSelection, openNativeEditor, openBehavior,
        loadFilterCatalog, setSidebarTab, pickOnMap, createTorchComponent, detachTorch, notify,
        onOptions: (target, trigger) => showObjectOptions(target, null, trigger),
        onModal: modal => {
            activeModal = modal;
            modal?.addEventListener('close', () => { if (activeModal === modal) { picking?.finish(null); activeModal = null; } }, { once: true });
        },
    });
    productivity = createProductivity({root,state,t,signal,base,refs:selectionRefs,select:setSelection,commit,
        render:()=>{renderCanvas();renderLayers();renderProperties();},setTool,brushAssets:brushAssetIds,notify,
        remember:rememberDraft,isBusy:()=>busy||!ready||!!activeModal,playerTest:openPlayerSimulation});
    async function openPlayerSimulation() {
        if(busy||activeModal)return;
        flushFocusedField();cancelDrawing();
        const source=clone(state.document),http=new HttpClient();setBusy(true);
        try{
            const catalog=await http.get(base+'/testing-catalog',{signal});if(disposed)return;
            activeModal=openPlayerTest({source,actors:catalog.actors,t,
                preview:(host,document,afterPaint)=>renderTestPreview(host,document,null,afterPaint),
                execute:(document,elementId,event,actorId,position,signal)=>http.post(base+'/test',{
                    request_id:crypto.randomUUID(),document,elementId,event,position,...(actorId?{actorId}:{}),
                    ...(state.version>0?{projectId:state.id}:{})},{signal}),
                onClose:()=>{activeModal=null;}});
        }catch(error){if(!disposed)notify(t(error.message),[],'error');}
        finally{if(!disposed)setBusy(false);}
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
    function commit() { floorPainter?.cancel(); terrainPainter?.cancel(); autosave.keepDraft(); undo.commit(state.document); rememberDraft(); updateSaveState(); if (!state.recoveryConflict) autosave?.schedule(); }
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
        const step = cell ? 1 : state.snapStep, bounds = documentBounds(state.document);
        const snap = value => snapping ? Math.round(value / step) * step : round(value);
        return { x: clamp(snap(point.x), 0, bounds.width), y: clamp(snap(point.y), 0, bounds.height) };
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
    function showObjectOptions(target, position, trigger = viewport) {
        if (disposed || busy || state.preview || activeModal || picking || gesture || brushResize || !target || !editable(target)) return;
        flushFocusedField();
        const item = itemFor(target); if (!item) return;
        if (!selectionRefs().some(ref => ref.kind === target.kind && ref.id === target.id)) {
            setSelection([target]); renderSelection(); renderProperties();
        }
        const entries = [{ id: 'properties', label: t('Properties'), action: () => openProperties(target, 'properties') }];
        if (!isNativeKind(target.kind) && target.kind !== 'regions' && !item.empty && item.brush?.operation !== 'erase')
            entries.push({ id: 'appearance', label: t('Appearance'), action: () => openProperties(target, 'appearance') });
        const intelligent = ['doors', 'regions'].includes(target.kind) || target.kind === 'decorations';
        if (intelligent) entries.push({ id: 'behavior', label: t('Behavior'), action: () => openProperties(target, 'behavior') });
        if (target.kind === 'decorations' && !item.torch && (item.assetId || item.empty)) entries.push({
            id: 'templates', label: t('Ready-made models'), children: interactiveObjectPresets.map(preset => ({
                id: 'preset:' + preset.id, label: t(preset.name), action: () => openPreset(target, preset.id),
            })),
        });
        if (target.kind === 'decorations' && item.torch) entries.push({ id: 'components', label: t('Torch components'), action: () => openProperties(target, 'components') });
        if (target.kind === 'regions') entries.push({ id: 'region', label: t('Presence filters'), action: () => openProperties(target, 'region') });
        if (hasNativeEditor(target.kind)) entries.push({ id: 'native', label: t('Open game editor'), action: () => openNativeEditor(target) });
        if (['doors', 'regions'].includes(target.kind) || target.kind === 'decorations' && (isSmartDecoration(item) || item.assetId))
            entries.push({ id: 'nodes', label: t('Edit nodes'), action: () => openBehavior(target) });
        entries.push({ id: 'duplicate', label: t('Duplicate'), action: () => transformSelection('duplicate') },
            { id: 'rotate', label: t('Rotate'), action: () => transformSelection('rotate') },
            { id: 'delete', label: t('Delete'), danger: true, action: deleteSelection });
        const anchor = trigger === viewport ? root.querySelector(`[data-object-kind="${target.kind}"][data-object-id="${CSS.escape(target.id)}"]`) : trigger;
        const box = (anchor || viewport).getBoundingClientRect();
        objectMenu.open({ ...(position || { x: box.left + Math.min(box.width / 2, 180), y: box.top + Math.min(box.height / 2, 100) }), entries,
            label: elementLabel(target.kind, item), returnTo: trigger.isConnected ? trigger : viewport });
    }
    function start(point, event, resumePaint = false) {
        if (busy || !ready || state.preview) return false;
        flushFocusedField();
        const bounds = documentBounds(state.document);
        if(productivity?.place(point))return false;
        const areaHandle = event.target.closest('[data-builder-area-handle]');
        if (areaHandle) {
            const target = { kind: 'decorations', id: areaHandle.dataset.builderAreaHandle };
            if (!editable(target)) return false;
            gesture = { before: clone(state.document), areaRadius: target.id }; return true;
        }
        if (state.tool === 'floor' && state.paintMode === 'brush' && !state.samplingFloor && event.button === 0 && event.shiftKey && !event.altKey && !event.ctrlKey && !event.metaKey) {
            if (point.x < 0 || point.y < 0 || point.x > bounds.width || point.y > bounds.height) return false;
            brushResize = { point: { x: point.x, y: point.y }, clientX: event.clientX, size: state.brush.floorSize };
            resizeBrush(event); return true;
        }
        const wallControl = wallControls?.start(point, event);
        if (wallControl !== undefined && wallControl !== null) return wallControl;
        if (point.x < 0 || point.y < 0 || point.x > bounds.width || point.y > bounds.height) return false;
        if (state.tool === 'floor' && (state.samplingFloor || event.altKey)) { pickFloorMaterial(point); return false; }
        const before = clone(state.document), target = hit(point, event);
        const activePaintLayer=state.document.layers.find(layer=>layer.id===state.activeLayer);
        if(state.tool==='decoration'&&activePaintLayer&&layerVisible(activePaintLayer)&&!activePaintLayer.locked&&productivity?.startBrush(point)){
            gesture={before,scatter:true};renderCanvas();return true;
        }
        if (!resumePaint && (hasNativeEditor(target?.kind) || target?.kind === 'decorations' && (isSmartDecoration(itemFor(target)) || itemFor(target)?.assetId))
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
            const dragged = Math.hypot(point.x - start.x, point.y - start.y) > .1, bounds = documentBounds(state.document);
            const width = Math.min(bounds.width, dragged ? Math.max(.05, Math.abs(point.x - start.x)) : state.brush.width);
            const height = Math.min(bounds.height, dragged ? Math.max(.05, Math.abs(point.y - start.y)) : state.brush.height);
            const object = { ...base, x: clamp(dragged ? Math.min(start.x, point.x) : start.x, 0, bounds.width - width),
                y: clamp(dragged ? Math.min(start.y, point.y) : start.y, 0, bounds.height - height), width, height, rotation: state.brush.rotation };
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
        if(gesture?.scatter){productivity.paint(point);return;}
        if (gesture?.areaRadius) {
            const item = itemFor({ kind: 'decorations', id: gesture.areaRadius });
            if (!item) return;
            item.presenceRadius = round(clamp(Math.hypot(point.x - item.x - item.width / 2, point.y - item.y - item.height / 2), .05, 200));
            renderSelection(); return;
        }
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
        if(gesture?.scatter){gesture=undefined;if(productivity.finishBrush()){commit();renderCanvas();renderLayers();renderProperties();}return;}
        if (floorPainter.active) { floorPainter.end(['brush', 'fill'].includes(state.paintMode) ? point : bounded(point, false, floorSnap())); return; }
        if (!gesture) return;
        if (gesture.areaRadius) {
            gesture = undefined; commit(); renderCanvas(); renderProperties(); return;
        }
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
        const bounds = documentBounds(state.document);
        if (point.x < 0 || point.y < 0 || point.x >= bounds.width || point.y >= bounds.height) return;
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
        guide.append(svg('path', { d: cells.map(cell => `M${cell.x} ${cell.y}h${Math.min(1, bounds.width - cell.x)}v${Math.min(1, bounds.height - cell.y)}h${-Math.min(1, bounds.width - cell.x)}Z`).join(' '),
            fill: erase ? '#e08b8029' : '#e4bf7629', stroke: erase ? '#e08b80' : '#e4bf76',
            'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', 'data-builder-brush-cursor': '', 'data-builder-brush-operation': state.paintOperation }));
    }
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
                : kind === 'doors' ? 'Click a door on the map. Esc cancels.' : kind==='shaders'?'Click a shader on the map. Esc cancels.':'Click a light on the map. Esc cancels.'),
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
        if (event.button !== 0) return;
        if (picking) { event.preventDefault(); return; }
        if (floorPainter.polygon) { event.preventDefault(); floorPainter.finish(); return; }
        if (busy || state.preview || activeModal) return;
        const matrix = $('[data-builder-canvas]').getScreenCTM(); if (!matrix) return;
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
        const target = hit(point, event);
        if ((isNativeKind(target?.kind) || target?.kind === 'walls') && !event.target.closest('.map-builder__wall-control')) {
            event.preventDefault(); void openNativeEditor(target); return;
        }
        if (!['doors', 'regions'].includes(target?.kind) && !(target?.kind === 'decorations' && (isSmartDecoration(itemFor(target)) || itemFor(target)?.assetId))) return;
        event.preventDefault(); openBehavior(target);
    }, { signal });
    viewport.addEventListener('contextmenu', event => {
        event.preventDefault();
        if (event.shiftKey && !event.clientX && !event.clientY) { showObjectOptions(state.selection); return; }
        const matrix = $('[data-builder-canvas]').getScreenCTM(); if (!matrix) return;
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
        showObjectOptions(hit(point, event), { x: event.clientX, y: event.clientY });
    }, { signal });
    viewport.addEventListener('keydown', event => {
        if (event.key !== 'ContextMenu' && !(event.shiftKey && event.key === 'F10')) return;
        event.preventDefault(); event.stopPropagation(); showObjectOptions(state.selection);
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
    function renderTestPreview(host, source, result, afterPaint) {
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
            afterPaint?.();
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
                    ...(state.version > 0 ? { projectId: state.id } : {}),
                }, { signal }),
                preview: (host, result) => renderTestPreview(host, source, result), onClose: () => { activeModal = null; },
            });
        } catch (error) { if (!disposed) notify(t(error.message || 'Could not run the test.'), [], 'error'); }
        finally { if (!disposed) setBusy(false); }
    }, { signal });
    $('[data-builder-uvtt-import]').addEventListener('click', async () => {
        if (busy || activeModal) return;
        flushFocusedField(); cancelDrawing();
        if (!await run(() => saveCurrent({ retry: true })) || disposed) return;
        activeModal = openUniversalVtt({ campaignId: root.dataset.campaignId, folderId: state.folderId, builderEditable: true, t,
            onImported: async result => {
                if (disposed) return;
                const accepted = await run(async () => {
                    await refreshLibrary();
                    if (disposed) return;
                    acceptProject(result.project);
                    notify([t('Map imported into Builder. Review the editable geometry before updating the scene.'),
                        ...(result.warnings || []).map(warning => t(warning))].join(' '));
                });
                if (!accepted && !disposed) throw lastFailure || new Error(t('Universal VTT interchange failed.'));
            },
        });
        activeModal.addEventListener('close', () => { activeModal = null; }, { once: true });
    }, { signal });
    $('[data-builder-network]').addEventListener('click', () => {
        if (busy || state.preview || activeModal) return;
        cancelDrawing();
        activeModal = openSceneNetwork({ campaignId: root.dataset.campaignId, t, pick: pickOnMap,
            load: async () => ({ elements: behaviorElements(), assets: behaviorMaterials(), materials: behaviorMaterials(), lights: state.document.lights,shaders:state.document.shaders,
                sounds: state.sounds || [], users: state.users || [], handouts: state.handouts || [], clocks: behaviorClocks(), clues: behaviorClues(), mindmaps: behaviorMindmaps() }),
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
        if (!['doors', 'regions'].includes(target.kind) && !(target.kind === 'decorations' && (isSmartDecoration(object) || object?.assetId))) return;
        if (target.kind === 'decorations' && !isSmartDecoration(object)) {
            object.lever = { state: 'off' };
            object.blueprint ||= defaultBlueprint('lever');
            commit(); renderCanvas(); renderLayers();
        }
        cancelDrawing(); setSelection([target]); renderSelection(); renderProperties();
        const kind = target.kind === 'regions' ? 'region' : target.kind === 'doors' ? 'door' : object.torch ? 'torch' : 'lever';
        const elements = behaviorElements();
        const assets = state.document.assets.filter(entry => entry.role === (kind === 'door' ? 'door' : 'decoration')).map(entry => {
            const asset = assetById(entry.assetId); return asset && { ...asset, name: assetName(asset) };
        }).filter(Boolean);
        activeModal = openBlueprintEditor({ element: elements.find(item => item.id === object.id), elements,
            assets, materials: behaviorMaterials(), campaignId: root.dataset.campaignId, linkedScene: Boolean(state.sceneId), users: state.users || [], handouts: state.handouts || [],
            clocks: behaviorClocks(), clues: behaviorClues(), mindmaps: behaviorMindmaps(), shaders:state.document.shaders,
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
        state.clocks = result.clocks || [];
        state.clues = result.clues || [];
        state.mindmaps = result.mindmaps || [];
        state.projects = result.projects; state.limits = result.limits || {};
        renderAssets(); renderProjects(); renderCanvas();
    }
    function behaviorClocks() {
        return (state.clocks || []).filter(clock => !clock.sceneId || clock.sceneId === state.sceneId);
    }
    function behaviorMindmaps() {
        return (state.mindmaps || []).filter(map => !map.sceneId || map.sceneId === state.sceneId);
    }
    function behaviorClues() {
        return (state.clues || []).filter(clue => !clue.sceneId || clue.sceneId === state.sceneId);
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
    async function synchronizedProject(project) {
        if (!project.sceneId || !project.canUpdate) return project;
        state.sceneSyncAttempts ||= {};
        const resumed = state.sceneSyncAttempts[project.id];
        const payload = resumed || { expected_version: project.version, expected_scene_version: project.sceneVersion };
        state.sceneSyncAttempts[project.id] = payload;
        try {
            const result = await operation('/projects/' + project.id + '/sync', payload);
            delete state.sceneSyncAttempts[project.id]; rememberDraft();
            // A lost acknowledgement can predate another game's edit. Settle its
            // original receipt before reading a fresh snapshot for the next sync.
            if (resumed) return synchronizedProject((await api('/projects/' + project.id)).project);
            return result.project;
        } catch (cause) {
            if (cause.status === 400 || cause.conflict) { delete state.sceneSyncAttempts[project.id]; rememberDraft(); }
            throw cause;
        }
    }
    async function synchronizeCurrent() {
        if (!state.version || state.recoveryConflict) return;
        await autosave.pendingWrite;
        // An unconfirmed write must retain its original payload and receipt.
        if (state.saveAttempt) throw new Error(t('A previous save could not be confirmed. Reload the saved project or save a copy.'));
        const id = state.id, sceneId = state.sceneId;
        const result = await api('/projects/' + id);
        if (disposed || state.id !== id) return;
        if (sceneId && result.project.sceneId !== sceneId) {
            const cause = new Error(t('The generated scene changed. Reload the project before updating it.'));
            cause.conflict = true; throw cause;
        }
        const project = await synchronizedProject(result.project);
        if (disposed || state.id !== id) return;
        const remote = normalizeDocument(project.document), base = JSON.parse(state.saved), local = state.document;
        const merged = mergeSceneProject(base, local, remote);
        if (merged.conflicts.length) {
            state.recoveryConflict = true; autosave.keepDraft(); rememberDraft(); updateSaveState();
            const cause = new Error(t('The same object properties changed in the game and in this draft. Your edits are kept in this tab.'));
            cause.conflict = true; throw cause;
        }
        if (!sameDocument(base, remote)) {
            await refreshLibrary();
            if (disposed || state.id !== id) return;
            undo.rebase(snapshot => mergeSceneProject(base, snapshot, remote, { preferRemote: true }).document);
        }
        state.version = project.version; state.folderId = project.folderId;
        state.document = merged.document; state.saved = JSON.stringify(remote); projectMetadata(project, true);
        state.projects = [project, ...state.projects.filter(row => row.id !== id)];
        startAutosave(); rememberDraft();
        setSelection(state.selections); renderForm(); renderAssets(); renderProjects(); renderCanvas(); renderLayers(); renderProperties();
        camera.resize(state.document.columns, state.document.rows, state.document.cellSize, false);
        updateSaveState(); if (dirty()) autosave.schedule();
    }
    function openProject(id) { return run(async () => {
        const result = await api('/projects/' + id);
        acceptProject(await synchronizedProject(result.project)); hideNotice();
    }); }
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
        return autosave.flush();
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
        if (!dirty() && !autosave.pendingWrite && !state.recoveryConflict && !['error', 'conflict', 'pending', 'saving'].includes(autosave.state.status)) { hideNotice(); return callback(); }
        if (await run(async () => { await saveCurrent({ retry: true }); hideNotice(); })) return callback();
        const cause = state.recoveryConflict ? { conflict: true,
            message: t('A previous save could not be confirmed. Reload the saved project or save a copy.') } : autosave.state.error;
        notify(cause?.message || t('Could not save automatically. Your changes are kept in this tab.'), [
            ...(cause?.conflict ? [['Reload saved project', () => openProject(state.id)], ['Save a copy', saveCopy]] : [['Retry', () => confirmLeave(callback)]]),
            ['Discard changes', () => { autosave.dispose(); autosave.discardDraft(); rememberDraft(); hideNotice(); callback(); }], ['Keep editing', hideNotice],
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
        if (['columns', 'rows', 'cellSize'].some(key => next[key] !== state.document[key])) delete next.sceneGeometry;
        if (!next.name.trim() || next.name.length > 120 || !/^#[0-9a-f]{6}$/i.test(next.background)
            || !Number.isInteger(next.columns) || next.columns < 1 || next.columns > 200
            || !Number.isInteger(next.rows) || next.rows < 1 || next.rows > 200
            || !Number.isInteger(next.cellSize) || next.cellSize < 16 || next.cellSize > 256) return false;
        const pixels = next.sceneGeometry ? next.sceneGeometry.width * next.sceneGeometry.height : next.columns * next.rows * next.cellSize ** 2;
        if (!fitsBounds(next) || pixels > (state.limits.maxPixels || 16777216)) {
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
            await synchronizeCurrent();
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
                const result = await api('/projects/' + initialId); acceptProject(await synchronizedProject(result.project));
            } else if (state.version && !state.recoveryConflict && !state.saveAttempt) await synchronizeCurrent();
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
    const synchronizeOnReturn = () => {
        if (!ready || disposed || busy || document.visibilityState === 'hidden' || activeModal || objectMenu.isOpen || gesture || brushResize
            || openingNativeEditor || picking || floorPainter?.active || floorPainter?.polygon || terrainPainter?.active
            || wallControls?.active || wallControls?.armed || document.querySelector('.ownership-modal-overlay:not([hidden])')
            || state.preview || state.recoveryConflict || state.saveAttempt || state.assetRemovals.length) return;
        void run(synchronizeCurrent);
    };
    window.addEventListener('focus', synchronizeOnReturn, { signal });
    document.addEventListener('visibilitychange', synchronizeOnReturn, { signal });
    if (recoveryError) notify(t(recoveryError), [], 'error');
    else if (recovered) notify(t('Recovered unsaved work from this tab.'));
    return () => { if (!autosave.discarded) flushFocusedField(); cancelDrawing(); disposed = true; autosave.dispose(); activeModal?.close(true); terrainPainter?.dispose(); clearTerrainPreview(); canvasRenderer.dispose(); nativeEffects?.dispose(); guideObserver.disconnect(); camera.dispose(); rememberDraft(); abort.abort(); };
}
if (root) {
    let dispose = mountWorkspace(root);
    addEventListener('pagehide', () => { dispose?.(); dispose = undefined; });
    addEventListener('pageshow', event => { if (event.persisted) { dispose?.(); dispose = mountWorkspace(root); } });
}
