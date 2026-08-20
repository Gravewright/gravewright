(() => {
  "use strict";

  let emitters = [], selectedIds = new Set(), campaignId = "", sceneId = "", gesture = null;
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

  // O ultimo id entrando no Set e o "selecionado" para quem so sabe lidar com
  // um: o inspetor e a lista do painel de sons continuam falando essa lingua.
  const lastSelected = () => { let last = null; selectedIds.forEach(id => { last = id; }); return last; };

  function announce() {
    document.dispatchEvent(new CustomEvent("sound:spatial-selection", { detail: { id: lastSelected(), ids: [...selectedIds] } }));
    requestRender();
  }

  function select(id, { additive = false } = {}) {
    if (!id) { if (!selectedIds.size) return; selectedIds.clear(); }
    else if (additive) { if (selectedIds.has(id)) selectedIds.delete(id); else selectedIds.add(id); }
    else if (selectedIds.size === 1 && selectedIds.has(id)) return;
    else { selectedIds.clear(); selectedIds.add(id); }
    announce();
  }

  function selectInRect(canvas, rect, { additive = false } = {}) {
    if (!canvas || !soundAuthoringActive() || !canAuthor(canvas)) return;
    const context = contextFor(canvas);
    if (context.campaignId !== campaignId || context.sceneId !== sceneId) return;
    if (!additive) selectedIds.clear();
    emitters.forEach(item => {
      if (item.id === "spatial-sound-preview") return;
      const point = projected(item, canvas);
      if (!point) return;
      if (point.x >= rect.left && point.x <= rect.right && point.y >= rect.top && point.y <= rect.bottom) selectedIds.add(item.id);
    });
    announce();
  }

  const selectedEmitters = () => emitters.filter(item => selectedIds.has(item.id));

  function projected(item, canvas) {
    const state = window.GravewrightMap?.stateFor?.(canvas), rect = canvas?.getBoundingClientRect?.();
    if (!state || !rect) return null;
    return { x: rect.left + state.offsetX + Number(item.x) * state.zoom, y: rect.top + state.offsetY + Number(item.y) * state.zoom, radius: Math.max(12, Number(item.radius || 0) * state.zoom) };
  }

  function hitAt(canvas, clientX, clientY) {
    for (let index = emitters.length - 1; index >= 0; index -= 1) {
      const item = emitters[index], point = projected(item, canvas);
      if (!point) continue;
      // A alca de raio so aparece quando ha um unico som selecionado.
      if (selectedIds.size === 1 && selectedIds.has(item.id) && Math.hypot(clientX - (point.x + point.radius), clientY - point.y) <= 12) return { item, mode: "radius" };
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
    return { emitters: visible ? emitters : [], selectedId: authoring ? lastSelected() : null,
      selectedIds: authoring ? [...selectedIds] : [], authoring, artisticReference, wallReference };
  }

  document.addEventListener("pointerdown", event => {
    const canvas = event.target.closest?.("[data-map-canvas]");
    if (!canvas || document.body.classList.contains("is-placing-spatial-sound") || !soundAuthoringActive() || !toolOwnsSound() || !canAuthor(canvas)) return;
    const hit = hitAt(canvas, event.clientX, event.clientY);
    const additive = event.shiftKey || event.ctrlKey || event.metaKey;
    // Vazio: a marquee do mapa assume a partir daqui; aqui so soltamos a selecao.
    if (!hit) { if (!additive && event.button === 0) select(null); return; }
    event.preventDefault(); event.stopImmediatePropagation();
    if (additive) { select(hit.item.id, { additive: true }); return; }
    if (!selectedIds.has(hit.item.id)) select(hit.item.id);
    try { canvas.setPointerCapture?.(event.pointerId); } catch (error) {
      if (error?.name !== "InvalidStateError" && error?.name !== "NotFoundError") throw error;
    }
    // Arrastar um som da selecao leva o grupo inteiro junto; a alca de raio e sempre individual.
    const moving = hit.mode === "move" ? selectedEmitters() : [hit.item];
    gesture = { canvas, pointerId: event.pointerId, mode: hit.mode, item: hit.item, moved: false,
      startClientX: event.clientX, startClientY: event.clientY,
      anchor: { x: hit.item.x, y: hit.item.y },
      items: moving.map(item => ({ item, snapshot: { x: item.x, y: item.y, radius: item.radius } })) };
  }, true);

  document.addEventListener("pointermove", event => {
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    if (!gesture.moved && Math.hypot(event.clientX - gesture.startClientX, event.clientY - gesture.startClientY) < 5) return;
    const world = window.GravewrightMap?.worldFromScreen?.(gesture.canvas, event.clientX, event.clientY);
    if (!world) return;
    gesture.moved = true;
    if (gesture.mode === "move") {
      // O som agarrado cola no ponteiro; o resto da selecao anda pelo mesmo delta.
      const dx = world.worldX - gesture.anchor.x, dy = world.worldY - gesture.anchor.y;
      gesture.items.forEach(({ item, snapshot }) => Object.assign(item, { x: snapshot.x + dx, y: snapshot.y + dy }));
    } else gesture.item.radius = Math.max(10, Math.hypot(world.worldX - gesture.item.x, world.worldY - gesture.item.y));
    requestRender();
  });

  async function finish(event, commit) {
    if (!gesture || (event.pointerId != null && gesture.pointerId !== event.pointerId)) return;
    const current = gesture; gesture = null;
    if (!commit) current.items.forEach(({ item, snapshot }) => Object.assign(item, snapshot));
    else if (current.moved) {
      const campaign = contextFor(current.canvas).campaignId;
      await Promise.all(current.items.map(async ({ item, snapshot }) => {
        const patch = current.mode === "move" ? { x: item.x, y: item.y } : { radius: item.radius };
        try {
          const updated = await post("/game/sounds/spatial/update", { campaignId: campaign, id: item.id, expectedVersion: item.version, patch });
          Object.assign(item, updated);
          document.dispatchEvent(new CustomEvent("sound:spatial-committed", { detail: updated }));
        } catch { Object.assign(item, snapshot); }
      }));
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
    [...selectedIds].forEach(id => { if (!emitters.some(item => item.id === id)) selectedIds.delete(id); });
    requestRender();
  });
  document.addEventListener("sound:spatial-select", event => select(event.detail?.id));
  document.addEventListener("scene:activated", requestRender);
  document.addEventListener("tool:active-layer", requestRender);

  window.GravewrightSpatialSounds = {
    snapshotFor,
    selectInRect,
    debugSnapshot() {
      const canvas = activeCanvas();
      return { ...snapshotFor(canvas), projected: emitters.map(item => ({ id: item.id, ...projected(item, canvas) })), renderer: window.__gravewrightSpatialSoundPixi?.renderer || null };
    },
  };
})();
