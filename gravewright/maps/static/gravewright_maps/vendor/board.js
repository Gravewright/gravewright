// widgets/game-board/ui/board.js
import { observed, prefetchSnapshot } from "../runtime/widgets/game-board/model/prefetch-metrics.js";
import { tileBlobCache } from "../runtime/widgets/game-board/model/tile-blob-cache.js";
import { pingShapes, PING_DURATION } from "../runtime/widgets/game-board/model/map-ping.js";
import { LONG_PRESS_MS, movedBeyondThreshold, zoomAround } from "../runtime/widgets/game-board/model/board-input.js";
import { PRIORITY, TileScheduler } from "../runtime/widgets/game-board/model/tile-scheduler.js";
import { fitToSurface, planTiles, regionTileUrls, sameRegion, visibleRange, worldPoint } from "../runtime/widgets/game-board/model/board-view.js";
import { StableRegionHeartbeat } from "../runtime/widgets/game-board/model/stable-region-heartbeat.js";
import { AsyncWorkPump } from "../runtime/widgets/game-board/model/async-work-pump.js";
import { warmTiles } from "../runtime/widgets/game-board/lib/warm-tiles.js";
import { createPixiBoardRenderer } from "../runtime/widgets/game-board/lib/pixi-board-renderer.js";
import { renderingPreferences } from "/static/gravewright_maps/render-profile.js";
import { SceneLayers } from "../runtime/widgets/game-board/lib/scene-layers.js";
function preloadScene(manifest, surface, initialView) {
  const region = visibleRange(manifest, initialView || fitToSurface(surface, manifest), surface);
  const task = warmTiles(manifest, region);
  return { cancel: task.cancel, done: task.done.then(() => {
    if (!regionTileUrls(manifest, region, 24).some((url) => tileBlobCache.has(url)))
      throw new Error("Unable to preload this scene.");
  }) };
}
function createBoard(element, options, emit) {
  const props = { ...options };
  const host = { value: element };
  const overlayView = { set value(view) {
    emit("viewport", view);
  } };
  const failed = { set value(value) {
    element.parentElement?.querySelector("[data-map-render-error]")?.toggleAttribute("hidden", !value);
  } };
  const FALLBACK_BACKGROUND = "#171816";
  const FRAME_COLOR = "#c9a44c";
  const PING_HIGHLIGHT = "#e2c675";
  const PING_MS = PING_DURATION;
  const LOAD_BUDGET = 6;
  const RETRY_MS = [400, 1200, 3600];
  let board, resizeObserver;
  let sceneLayers;
  let gesture;
  const pingFrames = /* @__PURE__ */ new Set();
  let ready = false, panning = false, disposed = false, pings = 0;
  const scheduler = new TileScheduler();
  let generation = 0;
  let shown = /* @__PURE__ */ new Map();
  let wanted = /* @__PURE__ */ new Map();
  let backdrop = /* @__PURE__ */ new Map();
  let wantedDepth;
  let tilesNeedSync = false;
  const tilePump = new AsyncWorkPump(() => !disposed && (scheduler.size > 0 || tilesNeedSync), drain);
  const attempts = /* @__PURE__ */ new Map();
  const retries = /* @__PURE__ */ new Set();
  let previousSample;
  let interactions = 0;
  const regionHeartbeat = new StableRegionHeartbeat(sameRegion, (region) => {
    if (!board || !props.manifest)
      return;
    const view = board.viewport(), now = performance.now();
    const x = (board.surface.width / 2 - view.x) / view.scale / props.manifest.tileSize;
    const y = (board.surface.height / 2 - view.y) / view.scale / props.manifest.tileSize;
    const speed = previousSample ? Math.hypot(x - previousSample.x, y - previousSample.y) * 1e3 / Math.max(1, now - previousSample.at) : 0;
    emit("region", region, { camera_speed: speed, camera_deceleration: Math.max(0, (previousSample?.speed ?? 0) - speed), interaction_count: interactions });
    previousSample = { x, y, at: now, speed };
    interactions = 0;
  }, {
    after: (milliseconds, callback) => window.setTimeout(callback, milliseconds),
    cancel: (id) => window.clearTimeout(id)
  });
  let warming;
  let pendingWarm;
  let loading = false;
  let panOrigin = { x: 0, y: 0 }, panPointer;
  let press;
  function viewport() {
    return board?.viewport();
  }
  function reportRegion() {
    const engine = board, manifest = props.manifest;
    if (disposed || !engine || !manifest)
      return;
    regionHeartbeat.changed(visibleRange(manifest, engine.viewport(), engine.surface));
  }
  function warm(region, expires = Date.now() + 6e4, hint) {
    const manifest = props.manifest;
    if (!manifest || disposed || manifest.mapId !== region.mapId || expires <= Date.now())
      return;
    if (scheduler.size > 0 || loading || retries.size > 0) {
      pendingWarm = { region, expires, hint };
      return;
    }
    pendingWarm = void 0;
    warming?.cancel();
    warming = warmTiles(manifest, region, expires, new Set([...shown.values()].map((tile) => tile.url)), hint);
  }
  function worldAt(client) {
    const engine = board, element2 = host.value;
    if (!engine || !element2)
      return void 0;
    const bounds = element2.getBoundingClientRect();
    return worldPoint({ x: client.x - bounds.left, y: client.y - bounds.top }, engine.viewport());
  }
  function refreshTiles() {
    const engine = board, manifest = props.manifest;
    if (!engine || !manifest)
      return;
    warming?.cancel();
    pendingWarm = void 0;
    overlayView.value = { ...engine.viewport() };
    const view = generation += 1;
    const scene = manifest.mapId;
    reportRegion();
    scheduler.cancelScope({ sceneNot: scene, olderThanGeneration: view });
    const plan = planTiles(manifest, engine.viewport(), engine.surface);
    const nextDepth = plan[0]?.tile.depth;
    if (wantedDepth !== void 0 && nextDepth !== wantedDepth)
      backdrop = new Map(shown);
    else if (nextDepth === wantedDepth && backdrop.size === 0)
      backdrop.clear();
    wantedDepth = nextDepth;
    wanted = new Map(plan.map(({ tile }) => [tile.key, tile]));
    shown = new Map([...shown].filter(([key]) => wanted.has(key) || backdrop.has(key)));
    tilesNeedSync = true;
    for (const { tile, priority, distance } of plan) {
      if (shown.get(tile.key)?.url === tile.url)
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
      const requested = new Map(shown);
      for (const tile of batch)
        requested.set(tile.key, tile);
      loading = true;
      let failed2;
      try {
        failed2 = await engine.setTiles([...requested.values()]);
      } finally {
        loading = false;
      }
      for (const tile of batch) {
        if (wanted.get(tile.key)?.url !== tile.url)
          continue;
        if (failed2.includes(tile.key))
          retry(tile, generation);
        else if (generation === view) {
          shown.set(tile.key, tile);
          attempts.delete(tile.key);
        }
      }
      if (generation !== view)
        break;
      if (backdrop.size > 0 && [...wanted].every(([key, tile]) => shown.get(key)?.url === tile.url)) {
        backdrop.clear();
        shown = new Map([...shown].filter(([key]) => wanted.has(key)));
        tilesNeedSync = true;
      }
    }
    if (pendingWarm && scheduler.size === 0 && !loading)
      warm(pendingWarm.region, pendingWarm.expires, pendingWarm.hint);
  }
  function retry(tile, view) {
    const key = tile.key;
    const attempt = attempts.get(key) ?? 0;
    const delay = RETRY_MS[attempt];
    if (delay === void 0) {
      attempts.delete(key);
      return;
    }
    attempts.set(key, attempt + 1);
    const timer = setTimeout(() => {
      retries.delete(timer);
      warming?.cancel();
      if (disposed || generation !== view || !board || wanted.get(key)?.url !== tile.url)
        return;
      scheduler.enqueue({ key, payload: tile, priority: PRIORITY.normal, order: 0, scene: tile.key.split(":")[0] ?? "", generation }, performance.now());
      tilePump.request();
    }, delay);
    retries.add(timer);
  }
  function forgetTiles() {
    generation += 1;
    previousSample = void 0;
    interactions = 0;
    warming?.cancel();
    warming = void 0;
    pendingWarm = void 0;
    regionHeartbeat.stop();
    scheduler.clear();
    shown = /* @__PURE__ */ new Map();
    wanted = /* @__PURE__ */ new Map();
    backdrop = /* @__PURE__ */ new Map();
    wantedDepth = void 0;
    tilesNeedSync = false;
    cancelRetries();
  }
  function cancelRetries() {
    attempts.clear();
    for (const timer of retries)
      clearTimeout(timer);
    retries.clear();
  }
  function applySceneLayers() {
    if (board && props.state && props.manifest && !disposed) {
      sceneLayers ??= new SceneLayers(board);
      sceneLayers.render({ ...props.state, ...props.tokenPresentation }, props.grid?.cellSize ?? 70, props.manifest.width, props.manifest.height, !!props.gm);
      sceneLayers.setEditingLayer(props.editingLayer || "game");
    }
  }
  function assetDragOver(event) {
    if (event.dataTransfer?.types.includes("application/x-gravewright-hand-card") || props.gm && event.dataTransfer?.types.includes("application/x-gravewright-library-image")) {
      event.preventDefault();
      event.dataTransfer.dropEffect = event.dataTransfer.types.includes("application/x-gravewright-hand-card") ? "move" : "copy";
    }
  }
  function assetDrop(event) {
    const cardData = event.dataTransfer?.getData("application/x-gravewright-hand-card");
    if (cardData && board) {
      event.preventDefault();
      event.stopPropagation();
      try {
        const card = JSON.parse(cardData);
        if (typeof card.cardId === "string")
          emit("cardDrop", { cardId: card.cardId, reveal: card.reveal !== false, ...worldPoint(surfacePoint(event), board.viewport()) });
      } catch {
      }
      return;
    }
    const assetId = event.dataTransfer?.getData("application/x-gravewright-library-image");
    if (!props.gm || !assetId || !board)
      return;
    event.preventDefault();
    event.stopPropagation();
    const point = worldPoint(surfacePoint(event), board.viewport());
    emit("assetDrop", { assetId, ...point });
  }
  async function applyPieces() {
    await board?.setPieces(props.pieces ?? []);
  }
  function drawFrame(width, height) {
    board?.drawShape("frame", { x: 0, y: 0 }, [{ kind: "rectangle", width, height, stroke: { width: 1, color: FRAME_COLOR, alpha: 0.7 } }]);
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
    if (!press || pointerId !== void 0 && press.pointerId !== pointerId)
      return;
    clearTimeout(press.timer);
    press = void 0;
  }
  let focusFrame = 0;
  function cancelCameraFocus() {
    cancelAnimationFrame(focusFrame);
    focusFrame = 0;
  }
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
      const { scale } = engine.viewport();
      engine.drawShape(id, world, pingShapes(progress, scale, focus, color));
      if (progress < 1) {
        const frame = requestAnimationFrame(() => {
          pingFrames.delete(frame);
          step();
        });
        pingFrames.add(frame);
      } else
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
      press = void 0;
      emit("ping", candidate.world, candidate.focus);
    }, LONG_PRESS_MS);
    press = candidate;
  }
  function onPointerDown(event) {
    interactions = Math.min(3, interactions + 1);
    cancelCameraFocus();
    const point = board ? worldPoint(surfacePoint(event), board.viewport()) : void 0;
    const piece = props.interactivePieces !== false && point && (!props.tool || props.tool === "select") ? [...props.pieces ?? []].reverse().find((p) => Math.hypot(p.x - point.x, p.y - point.y) <= p.size / 2) : void 0;
    if (event.button === 0 && piece && point) {
      gesture = { from: point, pointer: event.pointerId, tool: "move-token", pieceId: piece.key };
    } else if (event.button === 0 && props.tool && props.tool !== "select" && board) {
      gesture = { from: worldPoint(surfacePoint(event), board.viewport()), pointer: event.pointerId, tool: props.tool };
    } else if (event.button === 0)
      beginPress(event);
    else if (event.button === 1 || event.button === 2) {
      if (event.button === 1)
        event.preventDefault();
      cancelPress();
      panning = true;
      panPointer = event.pointerId;
      panOrigin = { x: event.clientX, y: event.clientY };
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
      panPointer = void 0;
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
      gesture = void 0;
      board?.removeShape("tool-preview");
    }
    cancelPress(event.pointerId);
    if (panPointer === event.pointerId) {
      panning = false;
      panPointer = void 0;
    }
  }
  async function mount() {
    const element2 = host.value;
    if (!element2 || disposed)
      return;
    const create = props.renderer ?? createPixiBoardRenderer;
    try {
      const background = getComputedStyle(element2).getPropertyValue("--bg").trim() || FALLBACK_BACKGROUND;
      const created = await create({ host: element2, background, label: props.label });
      if (disposed || host.value !== element2 || !element2.isConnected) {
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
      resizeObserver.observe(element2);
      await render();
    } catch (error) {
      failed.value = true;
      console.error("[gravewright] the game board failed to start", error);
    }
  }
  const stopRenderProfile = renderingPreferences.subscribe(() => applySceneLayers());
  function shiftPing(event) {
    if (press)
      press.focus = event.shiftKey;
  }
  const listeners = { wheel: onWheel, pointerdown: onPointerDown, pointermove: onPointerMove, pointerup: onPointerUp, pointercancel: onPointerUp, dragover: assetDragOver, drop: assetDrop, contextmenu: (event) => event.preventDefault() };
  for (const [name, listener] of Object.entries(listeners))
    element.addEventListener(name, listener, { passive: false });
  window.addEventListener("keydown", shiftPing);
  window.addEventListener("keyup", shiftPing);
  const readyPromise = mount();
  function prioritize(region, tiles) {
    if (!board || !props.manifest || disposed || !sameRegion(region, visibleRange(props.manifest, board.viewport(), board.surface)))
      return;
    const pending = new Set(scheduler.pending(performance.now()).map((item) => item.key));
    for (const item of tiles) {
      const tile = wanted.get(item.key);
      if (!tile || !pending.has(item.key) || !Number.isInteger(item.priority) || item.priority < 0 || item.priority > 4)
        continue;
      scheduler.enqueue({
        key: item.key,
        payload: tile,
        priority: item.priority,
        order: item.order,
        scene: region.mapId,
        generation
      }, performance.now());
    }
    tilePump.request();
  }
  async function update(next) {
    const previous = props.manifest;
    const changed = "manifest" in next && JSON.stringify(next.manifest) !== JSON.stringify(previous);
    const sameScene = previous && next.manifest && previous.mapId === next.manifest.mapId;
    Object.assign(props, next);
    await readyPromise;
    if (disposed)
      return;
    if ("label" in next)
      board?.setLabel(props.label);
    if (changed && !sameScene) {
      cancelCameraFocus();
      await render();
    } else {
      if (next.grid)
        board?.setGrid(props.grid);
      if (changed) {
        board?.cancelTileLoads?.();
        cancelRetries();
        drawFrame(props.manifest.width, props.manifest.height);
        refreshTiles();
      }
      if ("pieces" in next)
        await applyPieces();
      if (changed || ["state", "tokenPresentation", "grid", "gm"].some((key) => key in next))
        applySceneLayers();
    }
  }
  return { viewport, worldAt, editingLayer(layer) {
    props.editingLayer = layer;
    sceneLayers?.setEditingLayer(layer);
  }, previewSelection(value) {
    sceneLayers?.previewSelection(value);
  }, previewImage(value) {
    sceneLayers?.previewImage(value);
  }, previewCard(value) {
    sceneLayers?.previewCard(value);
  }, warm, hint(value) {
    warm(value.region, value.expires_at_ms, observed(value));
  }, streamingStats: prefetchSnapshot, prioritize, ping, ready: readyPromise, update, destroy({ preservePrefetch = false } = {}) {
    if (!preservePrefetch) tileBlobCache.clear();
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
    gesture = void 0;
    disposed = true;
    cancelPress();
    forgetTiles();
    resizeObserver?.disconnect();
    resizeObserver = void 0;
    board?.destroy();
    board = void 0;
  } };
}
export {
  createBoard,
  preloadScene
};
