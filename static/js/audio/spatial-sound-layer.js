(() => {
  "use strict";

  let emitters = [], selectedId = null, campaignId = "", sceneId = "", gesture = null;
  const activeCanvas = () => window.GravewrightMap?.activeCanvas?.();
  const canAuthor = canvas => Boolean(canvas && window.GravewrightMap?.viewerIsGm?.(canvas));
  const artisticLayerActive = () => window.GravewrightTools?.activeLayer === "composition";
  const soundAuthoringActive = () => window.GravewrightTools?.activeLayer === "composition" && document.body.dataset.activeArtisticDomain === "sounds";
  const wallReferenceActive = () => window.GravewrightTools?.activeLayer === "walls";
  const toolOwnsSound = () => ["sound", "select"].includes(window.GravewrightTools?.activeTool || "select");
  const contextFor = canvas => ({ canvas, campaignId: canvas?.dataset.roomId || "", sceneId: canvas?.dataset.sceneId || "" });
  const post = (url, value) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(value) }).then(async response => {
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error_key || "sound.request_failed");
    return result;
  });
  const requestRender = () => window.GravewrightMap?.redraw?.();

  function select(id) {
    selectedId = id || null;
    document.dispatchEvent(new CustomEvent("sound:spatial-selection", { detail: { id: selectedId } }));
    requestRender();
  }

  function projected(item, canvas) {
    const state = window.GravewrightMap?.stateFor?.(canvas), rect = canvas?.getBoundingClientRect?.();
    if (!state || !rect) return null;
    return { x: rect.left + state.offsetX + Number(item.x) * state.zoom, y: rect.top + state.offsetY + Number(item.y) * state.zoom, radius: Math.max(12, Number(item.radius || 0) * state.zoom) };
  }

  function hitAt(canvas, clientX, clientY) {
    for (let index = emitters.length - 1; index >= 0; index -= 1) {
      const item = emitters[index], point = projected(item, canvas);
      if (!point) continue;
      if (item.id === selectedId && Math.hypot(clientX - (point.x + point.radius), clientY - point.y) <= 12) return { item, mode: "radius" };
      if (Math.hypot(clientX - point.x, clientY - point.y) <= 18) return { item, mode: "move" };
    }
    return null;
  }

  function snapshotFor(canvas) {
    const context = contextFor(canvas), matches = context.campaignId === campaignId && context.sceneId === sceneId;
    const authoring = matches && canAuthor(canvas) && soundAuthoringActive();
    const artisticReference = matches && canAuthor(canvas) && artisticLayerActive() && !authoring;
    const wallReference = matches && canAuthor(canvas) && wallReferenceActive();
    const visible = authoring || artisticReference || wallReference;
    return { emitters: visible ? emitters : [], selectedId: authoring ? selectedId : null, authoring, artisticReference, wallReference };
  }

  document.addEventListener("pointerdown", event => {
    const canvas = event.target.closest?.("[data-map-canvas]");
    if (!canvas || document.body.classList.contains("is-placing-spatial-sound") || !soundAuthoringActive() || !toolOwnsSound() || !canAuthor(canvas)) return;
    const hit = hitAt(canvas, event.clientX, event.clientY);
    if (!hit) return;
    event.preventDefault(); event.stopImmediatePropagation(); select(hit.item.id);
    try { canvas.setPointerCapture?.(event.pointerId); } catch (error) {
      if (error?.name !== "InvalidStateError" && error?.name !== "NotFoundError") throw error;
    }
    gesture = { canvas, pointerId: event.pointerId, mode: hit.mode, item: hit.item, moved: false, startClientX: event.clientX, startClientY: event.clientY, snapshot: { x: hit.item.x, y: hit.item.y, radius: hit.item.radius } };
  }, true);

  document.addEventListener("pointermove", event => {
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    if (!gesture.moved && Math.hypot(event.clientX - gesture.startClientX, event.clientY - gesture.startClientY) < 5) return;
    const world = window.GravewrightMap?.worldFromScreen?.(gesture.canvas, event.clientX, event.clientY);
    if (!world) return;
    gesture.moved = true;
    if (gesture.mode === "move") Object.assign(gesture.item, { x: world.worldX, y: world.worldY });
    else gesture.item.radius = Math.max(10, Math.hypot(world.worldX - gesture.item.x, world.worldY - gesture.item.y));
    requestRender();
  });

  async function finish(event, commit) {
    if (!gesture || (event.pointerId != null && gesture.pointerId !== event.pointerId)) return;
    const current = gesture; gesture = null;
    if (!commit) Object.assign(current.item, current.snapshot);
    else if (current.moved) {
      const patch = current.mode === "move" ? { x: current.item.x, y: current.item.y } : { radius: current.item.radius };
      try {
        const updated = await post("/game/sounds/spatial/update", { campaignId: contextFor(current.canvas).campaignId, id: current.item.id, expectedVersion: current.item.version, patch });
        Object.assign(current.item, updated);
        document.dispatchEvent(new CustomEvent("sound:spatial-committed", { detail: updated }));
      } catch { Object.assign(current.item, current.snapshot); }
    }
    requestRender();
  }

  document.addEventListener("pointerup", event => finish(event, true));
  document.addEventListener("pointercancel", event => finish(event, false));
  document.addEventListener("keydown", event => { if (event.key === "Escape" && gesture) finish({ pointerId: gesture.pointerId }, false); });
  document.addEventListener("dblclick", event => {
    const canvas = event.target.closest?.("[data-map-canvas]");
    if (!canvas || !soundAuthoringActive() || !toolOwnsSound()) return;
    const hit = hitAt(canvas, event.clientX, event.clientY);
    if (!hit || hit.item.id === "spatial-sound-preview") return;
    event.preventDefault(); event.stopImmediatePropagation();
    document.dispatchEvent(new CustomEvent("sound:spatial-inspect", { detail: { id: hit.item.id } }));
  });
  document.addEventListener("sound:spatial-state", event => {
    emitters = Array.isArray(event.detail?.emitters) ? event.detail.emitters : [];
    campaignId = event.detail?.campaignId || ""; sceneId = event.detail?.sceneId || "";
    if (selectedId && !emitters.some(item => item.id === selectedId)) selectedId = null;
    requestRender();
  });
  document.addEventListener("sound:spatial-select", event => select(event.detail?.id));
  document.addEventListener("scene:activated", requestRender);
  document.addEventListener("tool:active-layer", requestRender);

  window.GravewrightSpatialSounds = {
    snapshotFor,
    debugSnapshot() {
      const canvas = activeCanvas();
      return { ...snapshotFor(canvas), projected: emitters.map(item => ({ id: item.id, ...projected(item, canvas) })), renderer: window.__gravewrightSpatialSoundPixi?.renderer || null };
    },
  };
})();
