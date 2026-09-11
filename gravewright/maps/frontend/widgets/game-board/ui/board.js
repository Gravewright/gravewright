import { observed, prefetchSnapshot } from "../model/prefetch-metrics.js";
import { tileBlobCache } from "../model/tile-blob-cache.js";
import { pingShapes, PING_DURATION } from "../model/map-ping.js";
import { LONG_PRESS_MS, movedBeyondThreshold, zoomAround } from "../model/board-input.js";
import { PRIORITY, TileScheduler } from "../model/tile-scheduler.js";
import { fitToSurface, planTiles, sameRegion, visibleRange, worldPoint } from "../model/board-view.js";
import { StableRegionHeartbeat } from "../model/stable-region-heartbeat.js";
import { AsyncWorkPump } from "../model/async-work-pump.js";
import { warmTiles } from "../lib/warm-tiles.js";
import { createPixiBoardRenderer } from "../lib/pixi-board-renderer.js";
import { renderingPreferences } from "../../../shared/rendering/render-profile.js";
import { SceneLayers } from "../lib/scene-layers.js";
// Lifecycle and DOM events use an explicit controller; no Vue runtime.
export function createBoard(element, options, emit) {
    const props = { ...options };
    const host = { value: element };
    const overlayView = { set value(view) { emit('viewport', view); } };
    const failed = { set value(value) { element.parentElement?.querySelector('[data-map-render-error]')?.toggleAttribute('hidden', !value); } };
    const FALLBACK_BACKGROUND = "#171816";
    const FRAME_COLOR = "#c9a44c";
    const PING_HIGHLIGHT = "#e2c675";
    const PING_MS = PING_DURATION;
    const LOAD_BUDGET = 6;
    const RETRY_MS = [400, 1200, 3600];
    let board, resizeObserver;
    let sceneLayers;
    let gesture;
    const pingFrames = new Set();
    let ready = false, panning = false, disposed = false, pings = 0;
    const scheduler = new TileScheduler();
    let generation = 0;
    let shown = new Map();
    let wanted = new Map();
    let backdrop = new Map();
    let wantedDepth;
    let tilesNeedSync = false;
    const tilePump = new AsyncWorkPump(() => !disposed && (scheduler.size > 0 || tilesNeedSync), drain);
    const attempts = new Map();
    const retries = new Set();
    let previousSample;
    let interactions = 0;
    const regionHeartbeat = new StableRegionHeartbeat(sameRegion, (region) => {
        if (!board || !props.manifest)
            return;
        const view = board.viewport(), now = performance.now();
        const x = (board.surface.width / 2 - view.x) / view.scale / props.manifest.tileSize;
        const y = (board.surface.height / 2 - view.y) / view.scale / props.manifest.tileSize;
        const speed = previousSample ? Math.hypot(x - previousSample.x, y - previousSample.y) * 1000 / Math.max(1, now - previousSample.at) : 0;
        emit("region", region, { camera_speed: speed, camera_deceleration: Math.max(0, (previousSample?.speed ?? 0) - speed), interaction_count: interactions });
        previousSample = { x, y, at: now, speed };
        interactions = 0;
    }, {
        after: (milliseconds, callback) => window.setTimeout(callback, milliseconds),
        cancel: (id) => window.clearTimeout(id),
    });
    let warming;
    let pendingWarm;
    let loading = false;
    let panOrigin = { x: 0, y: 0 }, panPointer;
    let press;
    function viewport() { return board?.viewport(); }
    function reportRegion() {
        const engine = board, manifest = props.manifest;
        if (disposed || !engine || !manifest)
            return;
        regionHeartbeat.changed(visibleRange(manifest, engine.viewport(), engine.surface));
    }
    function warm(region, expires = Date.now() + 60_000, hint) {
        const manifest = props.manifest;
        if (!manifest || disposed || manifest.mapId !== region.mapId || expires <= Date.now())
            return;
        if (scheduler.size > 0 || loading || retries.size > 0) {
            pendingWarm = { region, expires, hint };
            return;
        }
        pendingWarm = undefined;
        warming?.cancel();
        warming = warmTiles(manifest, region, expires, new Set([...shown.values()].map(tile => tile.url)), hint);
    }
    function worldAt(client) {
        const engine = board, element = host.value;
        if (!engine || !element)
            return undefined;
        const bounds = element.getBoundingClientRect();
        return worldPoint({ x: client.x - bounds.left, y: client.y - bounds.top }, engine.viewport());
    }
    function refreshTiles() {
        const engine = board, manifest = props.manifest;
        if (!engine || !manifest)
            return;
        warming?.cancel();
        pendingWarm = undefined;
        overlayView.value = { ...engine.viewport() };
        const view = generation += 1;
        const scene = manifest.mapId;
        reportRegion();
        scheduler.cancelScope({ sceneNot: scene, olderThanGeneration: view });
        const plan = planTiles(manifest, engine.viewport(), engine.surface);
        const nextDepth = plan[0]?.tile.depth;
        if (wantedDepth !== undefined && nextDepth !== wantedDepth)
            backdrop = new Map(shown);
        else if (nextDepth === wantedDepth && backdrop.size === 0)
            backdrop.clear();
        wantedDepth = nextDepth;
        wanted = new Map(plan.map(({ tile }) => [tile.key, tile]));
        // Ordinary panning releases the previous viewport immediately. Only a level transition is
        // allowed to retain its bounded, previous-plan backdrop.
        shown = new Map([...shown].filter(([key]) => wanted.has(key) || backdrop.has(key)));
        tilesNeedSync = true;
        for (const { tile, priority, distance } of plan) {
            if (shown.has(tile.key))
                continue;
            scheduler.enqueue({ key: tile.key, payload: tile, priority, order: distance, scene, generation: view }, performance.now());
        }
        tilePump.request();
    }
    async function drain() {
        const engine = board;
        if (!engine)
            return;
        while ((scheduler.size > 0 || tilesNeedSync) && !disposed) {
            const view = generation;
            const batch = scheduler.drain(performance.now(), { maxItems: LOAD_BUDGET });
            tilesNeedSync = false;
            for (const tile of batch)
                shown.set(tile.key, tile);
            loading = true;
            let failed;
            try {
                failed = await engine.setTiles([...shown.values()]);
            }
            finally {
                loading = false;
            }
            for (const key of failed)
                retry(key, view);
            for (const tile of batch)
                if (!failed.includes(tile.key))
                    attempts.delete(tile.key);
            // The viewport moved while this wave was in flight; the plan it produced is the one to follow.
            if (generation !== view)
                break;
            // `shown` only means successfully requested after this awaited renderer pass. Once every tile
            // in the new plan is present, the old level has done its job and can be released in one sync.
            if (backdrop.size > 0 && [...wanted.keys()].every((key) => shown.has(key))) {
                backdrop.clear();
                shown = new Map([...shown].filter(([key]) => wanted.has(key)));
                tilesNeedSync = true;
            }
        }
        if (pendingWarm && scheduler.size === 0 && !loading)
            warm(pendingWarm.region, pendingWarm.expires, pendingWarm.hint);
    }
    function retry(key, view) {
        const tile = shown.get(key);
        shown.delete(key);
        const attempt = attempts.get(key) ?? 0;
        const delay = RETRY_MS[attempt];
        if (!tile || delay === undefined) {
            attempts.delete(key);
            return;
        }
        attempts.set(key, attempt + 1);
        const timer = setTimeout(() => {
            retries.delete(timer);
            warming?.cancel();
            if (disposed || generation !== view || !board)
                return;
            scheduler.enqueue({ key, payload: tile, priority: PRIORITY.normal, order: 0, scene: tile.key.split(":")[0] ?? "", generation }, performance.now());
            tilePump.request();
        }, delay);
        retries.add(timer);
    }
    function forgetTiles() {
        tileBlobCache.clear();
        previousSample = undefined;
        interactions = 0;
        warming?.cancel();
        warming = undefined;
        pendingWarm = undefined;
        regionHeartbeat.stop();
        scheduler.clear();
        shown = new Map();
        wanted = new Map();
        backdrop = new Map();
        wantedDepth = undefined;
        tilesNeedSync = false;
        attempts.clear();
        for (const timer of retries)
            clearTimeout(timer);
        retries.clear();
    }
    function applySceneLayers() {
        if (board && props.state && props.manifest && !disposed) {
            sceneLayers ??= new SceneLayers(board);
            sceneLayers.render({ ...props.state, ...props.tokenPresentation }, props.grid?.cellSize ?? 70, props.manifest.width, props.manifest.height, !!props.gm);
        }
    }
    function assetDragOver(event) {
        if (event.dataTransfer?.types.includes('application/x-gravewright-hand-card') || (props.gm && event.dataTransfer?.types.includes('application/x-gravewright-library-image'))) {
            event.preventDefault();
            event.dataTransfer.dropEffect = 'copy';
        }
    }
    function assetDrop(event) {
        const cardData = event.dataTransfer?.getData('application/x-gravewright-hand-card');
        if (cardData && board) {
            event.preventDefault();
            event.stopPropagation();
            try {
                const card = JSON.parse(cardData);
                if (typeof card.cardId === 'string')
                    emit('cardDrop', { cardId: card.cardId, reveal: card.reveal !== false, ...worldPoint(surfacePoint(event), board.viewport()) });
            }
            catch { }
            return;
        }
        const assetId = event.dataTransfer?.getData('application/x-gravewright-library-image');
        if (!props.gm || !assetId || !board)
            return;
        event.preventDefault();
        event.stopPropagation();
        const point = worldPoint(surfacePoint(event), board.viewport());
        emit('assetDrop', { assetId, ...point });
    }
    async function applyPieces() {
        await board?.setPieces(props.pieces ?? []);
    }
    function drawFrame(width, height) {
        board?.drawShape("frame", { x: 0, y: 0 }, [{ kind: "rectangle", width, height, stroke: { width: 1, color: FRAME_COLOR, alpha: .7 } }]);
    }
    async function render() {
        const engine = board;
        if (!engine || disposed)
            return;
        failed.value = false;
        engine.clear();
        forgetTiles();
        ready = false;
        if (!props.manifest)
            return;
        if (props.grid)
            engine.setGrid(props.grid);
        drawFrame(props.manifest.width, props.manifest.height);
        engine.setViewport(props.initialView ?? fitToSurface(engine.surface, props.manifest));
        ready = true;
        refreshTiles();
        await applyPieces();
        applySceneLayers();
    }
    function surfacePoint(event) {
        const bounds = host.value.getBoundingClientRect();
        return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
    }
    function onWheel(event) {
        cancelCameraFocus();
        const engine = board;
        if (!engine)
            return;
        const view = engine.viewport();
        const next = zoomAround(surfacePoint(event), { x: view.x, y: view.y }, view.scale, event.deltaY);
        engine.setViewport({ x: next.position.x, y: next.position.y, scale: next.scale });
        refreshTiles();
    }
    function cancelPress(pointerId) {
        if (!press || (pointerId !== undefined && press.pointerId !== pointerId))
            return;
        clearTimeout(press.timer);
        press = undefined;
    }
    let focusFrame = 0;
    function cancelCameraFocus() { cancelAnimationFrame(focusFrame); focusFrame = 0; }
    function focusCamera(world) {
        const engine = board;
        if (!engine)
            return;
        cancelCameraFocus();
        const from = engine.viewport(), { width, height } = engine.surface;
        const target = { x: width / 2 - world.x * from.scale, y: height / 2 - world.y * from.scale };
        const start = performance.now();
        let lastTiles = start;
        const step = (now) => {
            if (disposed || board !== engine)
                return;
            const progress = Math.min(1, (now - start) / 450);
            const ease = progress * progress * (3 - 2 * progress);
            engine.setViewport({ x: from.x + (target.x - from.x) * ease, y: from.y + (target.y - from.y) * ease, scale: from.scale });
            overlayView.value = { ...engine.viewport() };
            if (now - lastTiles >= 80 || progress === 1) {
                refreshTiles();
                lastTiles = now;
            }
            focusFrame = progress < 1 ? requestAnimationFrame(step) : 0;
        };
        focusFrame = requestAnimationFrame(step);
    }
    function ping(world, focus, color) {
        const engine = board;
        if (!engine)
            return;
        if (focus)
            focusCamera(world);
        const id = `ping:${pings += 1}`;
        const start = performance.now();
        const step = () => {
            if (disposed || board !== engine)
                return;
            const progress = Math.min(1, (performance.now() - start) / PING_MS);
            // The mark is drawn in map units, so every radius is divided back out of the viewport scale and
            // the ping keeps the same size on screen however far the board is zoomed.
            const { scale } = engine.viewport();
            engine.drawShape(id, world, pingShapes(progress, scale, focus, color));
            if (progress < 1) {
                const frame = requestAnimationFrame(() => { pingFrames.delete(frame); step(); });
                pingFrames.add(frame);
            }
            else
                engine.removeShape(id);
        };
        step();
        refreshTiles();
    }
    function beginPress(event) {
        const engine = board;
        if (!engine)
            return;
        const world = worldPoint(surfacePoint(event), engine.viewport());
        const candidate = { pointerId: event.pointerId, origin: { x: event.clientX, y: event.clientY }, world, focus: event.shiftKey, timer: 0 };
        candidate.timer = window.setTimeout(() => {
            if (press?.pointerId !== candidate.pointerId)
                return;
            press = undefined;
            emit("ping", candidate.world, candidate.focus);
        }, LONG_PRESS_MS);
        press = candidate;
    }
    function onPointerDown(event) {
        interactions = Math.min(3, interactions + 1);
        cancelCameraFocus();
        const point = board ? worldPoint(surfacePoint(event), board.viewport()) : undefined;
        const piece = props.interactivePieces !== false && point && (!props.tool || props.tool === "select") ? [...(props.pieces ?? [])].reverse().find(p => Math.hypot(p.x - point.x, p.y - point.y) <= p.size / 2) : undefined;
        if (event.button === 0 && piece && point) {
            gesture = { from: point, pointer: event.pointerId, tool: "move-token", pieceId: piece.key };
        }
        else if (event.button === 0 && props.tool && props.tool !== "select" && board) {
            gesture = { from: worldPoint(surfacePoint(event), board.viewport()), pointer: event.pointerId, tool: props.tool };
        }
        else if (event.button === 0)
            beginPress(event);
        else if (event.button === 1 || event.button === 2) {
            if (event.button === 1)
                event.preventDefault();
            cancelPress();
            panning = true;
            panPointer = event.pointerId;
            panOrigin = { x: event.clientX, y: event.clientY };
            // Keep a secondary click targeted at its object. Capture only once it becomes a pan.
            return;
        }
        host.value?.setPointerCapture(event.pointerId);
    }
    function onPointerMove(event) {
        if (press)
            press.focus = event.shiftKey;
        if (gesture?.pointer === event.pointerId && board && gesture.tool !== "move-token") {
            const end = worldPoint(surfacePoint(event), board.viewport());
            board.drawShape("tool-preview", gesture.from, [{ kind: "line", to: { x: end.x - gesture.from.x, y: end.y - gesture.from.y }, stroke: { width: 2 / board.viewport().scale, color: FRAME_COLOR } }]);
        }
        if (press?.pointerId === event.pointerId) {
            press.focus = event.shiftKey;
            if (movedBeyondThreshold(press.origin, { x: event.clientX, y: event.clientY }))
                cancelPress(event.pointerId);
        }
        if (!panning || panPointer !== event.pointerId || !board)
            return;
        if (!(event.buttons & 6)) {
            panning = false;
            panPointer = undefined;
            return;
        }
        if (!host.value?.hasPointerCapture(event.pointerId)) {
            if (!movedBeyondThreshold(panOrigin, { x: event.clientX, y: event.clientY }, 5))
                return;
            host.value?.setPointerCapture(event.pointerId);
        }
        const view = board.viewport();
        board.setViewport({ x: view.x + event.clientX - panOrigin.x, y: view.y + event.clientY - panOrigin.y, scale: view.scale });
        panOrigin = { x: event.clientX, y: event.clientY };
        refreshTiles();
    }
    function onPointerUp(event) {
        if (gesture?.pointer === event.pointerId) {
            if (event.type !== "pointercancel" && board)
                emit("gesture", { from: gesture.from, to: worldPoint(surfacePoint(event), board.viewport()), tool: gesture.tool, pieceId: gesture.pieceId });
            gesture = undefined;
            board?.removeShape("tool-preview");
        }
        cancelPress(event.pointerId);
        if (panPointer === event.pointerId) {
            panning = false;
            panPointer = undefined;
        }
    }
    async function mount() {
        const element = host.value;
        if (!element || disposed)
            return;
        const create = props.renderer ?? createPixiBoardRenderer;
        try {
            const background = getComputedStyle(element).getPropertyValue("--bg").trim() || FALLBACK_BACKGROUND;
            const created = await create({ host: element, background, label: props.label });
            // Mounting is async, so the component may already be gone or remounted by the time it returns.
            if (disposed || host.value !== element || !element.isConnected) {
                created.destroy();
                return;
            }
            board = created;
            resizeObserver = new ResizeObserver(() => {
                if (disposed || !ready)
                    return;
                created.resize();
                refreshTiles();
            });
            resizeObserver.observe(element);
            // A module activated or disabled mid-scene reaches the board here.
            await render();
        }
        catch (error) {
            failed.value = true;
            // The board is a leaf with nowhere to report to, and the notice it shows cannot say why. Without
            // this line a failed stage leaves no trace at all.
            console.error("[gravewright] the game board failed to start", error);
        }
    }
    const stopRenderProfile = renderingPreferences.subscribe(() => applySceneLayers());
    function shiftPing(event) { if (press)
        press.focus = event.shiftKey; }
    const listeners = { wheel: onWheel, pointerdown: onPointerDown, pointermove: onPointerMove, pointerup: onPointerUp, pointercancel: onPointerUp, dragover: assetDragOver, drop: assetDrop, contextmenu: (event) => event.preventDefault() };
    for (const [name, listener] of Object.entries(listeners))
        element.addEventListener(name, listener, { passive: false });
    window.addEventListener('keydown', shiftPing);
    window.addEventListener('keyup', shiftPing);
    const readyPromise = mount();
    function prioritize(region, tiles) {
        if (!board || !props.manifest || disposed || !sameRegion(region, visibleRange(props.manifest, board.viewport(), board.surface)))
            return;
        const pending = new Set(scheduler.pending(performance.now()).map(item => item.key));
        for (const item of tiles) {
            const tile = wanted.get(item.key);
            if (!tile || !pending.has(item.key) || !Number.isInteger(item.priority) || item.priority < 0 || item.priority > 4)
                continue;
            scheduler.enqueue({ key: item.key, payload: tile, priority: item.priority,
                order: item.order, scene: region.mapId, generation }, performance.now());
        }
        tilePump.request();
    }
    return { viewport, worldAt, previewSelection(value){sceneLayers?.previewSelection(value);}, previewCard(value){sceneLayers?.previewCard(value);}, warm, hint(value) { warm(value.region, value.expires_at_ms, observed(value)); }, streamingStats: prefetchSnapshot, prioritize, ping, ready: readyPromise, async update(next) { const changed = next.manifest && JSON.stringify(next.manifest) !== JSON.stringify(props.manifest); Object.assign(props, next); await readyPromise; if (disposed)
            return; board?.setLabel(props.label); if (changed)
            await render();
        else {
            if (props.grid)
                board?.setGrid(props.grid);
            await applyPieces();
            applySceneLayers();
        } }, destroy() {
            tileBlobCache.clear();
            for (const [name, listener] of Object.entries(listeners))
                element.removeEventListener(name, listener);
            window.removeEventListener("keydown", shiftPing);
            window.removeEventListener("keyup", shiftPing);
            stopRenderProfile();
            cancelCameraFocus();
            for (const frame of pingFrames)
                cancelAnimationFrame(frame);
            pingFrames.clear();
            sceneLayers?.dispose();
            gesture = undefined;
            disposed = true;
            cancelPress();
            forgetTiles();
            resizeObserver?.disconnect();
            resizeObserver = undefined;
            board?.destroy();
            board = undefined;
        } };
}
