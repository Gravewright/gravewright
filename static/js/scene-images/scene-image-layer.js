(function () {
  const SceneImages = (window.GravewrightSceneImages = window.GravewrightSceneImages || {});

  const IMAGE_MIME_PREFIX = "image/";
  const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[ch]);
  }

  function csrf() {
    return typeof window.csrfToken === "function" ? window.csrfToken() : "";
  }

  function label(name, fallback) {
    return document.body?.dataset?.[name] || fallback;
  }

  function currentUserId() {
    return document.body.dataset.currentUserId || "";
  }


  function isEditableTarget(target) {
    const el = target instanceof Element ? target : null;
    if (!el) return false;
    if (el.isContentEditable) return true;
    const tag = el.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
  }

  async function jsonRequest(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "x-csrftoken": csrf(),
      },
      body: JSON.stringify(payload || {}),
      credentials: "same-origin",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error_key || "game.scene_images.errors.request_failed");
      error.payload = data;
      throw error;
    }
    return data;
  }

  const api = {
    async fetchState(roomId) {
      const response = await fetch(`/game/scene-images/state/${encodeURIComponent(roomId)}`, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error_key || "game.scene_images.errors.request_failed");
      return data;
    },
    placeAsset(roomId, payload) {
      return jsonRequest("/game/scene-images/place", { ...(payload || {}), campaign_id: roomId });
    },
    update(roomId, payload) {
      return jsonRequest("/game/scene-images/update", { ...(payload || {}), campaign_id: roomId });
    },
    remove(roomId, placementId) {
      return jsonRequest("/game/scene-images/delete", { campaign_id: roomId, placement_id: placementId });
    },
    async upload(roomId, sceneId, file, x, y, layer) {
      const form = new FormData();
      form.append("campaign_id", roomId);
      form.append("scene_id", sceneId);
      form.append("x", String(x));
      form.append("y", String(y));
      if (layer) form.append("layer", layer);
      form.append("file", file);
      const response = await fetch("/game/scene-images/upload", {
        method: "POST",
        headers: { Accept: "application/json", "x-csrftoken": csrf() },
        body: form,
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error_key || "game.scene_images.errors.request_failed");
      return data;
    },
  };
  SceneImages.api = api;

  const controllers = new Map();



  let activeLayer = "game";
  let imageClipboard = [];

  class SceneImageController {
    constructor(layer) {
      this.layer = layer;
      this.roomId = layer.dataset.roomId || "";
      this.isGm = layer.dataset.isGm === "true";
      this.placements = [];
      this.selectedIds = new Set();
      this.drag = null;
      controllers.set(this.roomId, this);
      this.bind();
      this.refresh();
    }

    canvas() {
      return this.layer.closest("[data-map-viewport]")?.querySelector("[data-map-canvas]") || null;
    }

    activeSceneId() {
      return this.canvas()?.dataset.sceneId || "";
    }

    canMove(placement) {
      const locked = window.GravewrightTools?.isLayerLocked?.(placement.layer, this.roomId);
      return !locked && (this.isGm || (placement.owner_user_id && placement.owner_user_id === currentUserId()));
    }

    camera() {
      const st = window.GravewrightMap?.stateFor?.(this.canvas());
      return {
        zoom: Number(st?.zoom) || 1,
        offsetX: Number(st?.offsetX) || 0,
        offsetY: Number(st?.offsetY) || 0,
      };
    }



    displayGeom(placement) {
      const scale = Number(placement.scale || 1);
      const nw = Number(placement.natural_width || 0);
      const nh = Number(placement.natural_height || 0);
      const rotation = Number(placement.rotation || 0);
      if (placement.layer === "composition") {
        const cam = this.camera();
        return {
          left: Number(placement.x || 0) * cam.zoom + cam.offsetX,
          top: Number(placement.y || 0) * cam.zoom + cam.offsetY,
          w: Math.max(1, nw * scale * cam.zoom),
          h: Math.max(1, nh * scale * cam.zoom),
          rotation,
        };
      }
      return {
        left: Number(placement.x || 0),
        top: Number(placement.y || 0),
        w: Math.max(1, nw * scale),
        h: Math.max(1, nh * scale),
        rotation,
      };
    }

    positionNode(node, placement) {
      if (!node) return;
      const g = this.displayGeom(placement);
      node.style.left = `${g.left}px`;
      node.style.top = `${g.top}px`;
      node.style.width = `${g.w}px`;
      node.style.height = `${g.h}px`;
      node.style.transform = `translate(-50%, -50%) rotate(${g.rotation}deg)`;
    }

    syncComposition() {
      if (this.drag || !this._hasComposition) return;
      const cam = this.camera();
      const last = this._lastCam;
      if (last && cam.zoom === last.zoom && cam.offsetX === last.offsetX && cam.offsetY === last.offsetY) return;
      this._lastCam = cam;
      const sceneId = this.activeSceneId();
      this.placements.forEach((placement) => {
        if (placement.layer !== "composition" || placement.scene_id !== sceneId) return;
        this.positionNode(this.nodeFor(placement.id), placement);
      });
    }

    async refresh() {
      if (!this.roomId) return;
      try {
        const state = await api.fetchState(this.roomId);
        this.placements = Array.isArray(state.placements) ? state.placements : [];
        this.selectedIds.forEach((id) => {
          if (!this.placements.some((p) => p.id === id)) this.selectedIds.delete(id);
        });
        this.render();
      } catch {

      }
    }

    render() {
      const sceneId = this.activeSceneId();
      this.lastSceneId = sceneId;
      if (!sceneId) {
        this.layer.innerHTML = "";
        return;
      }
      const placements = this.placements.filter((p) => p.scene_id === sceneId
        && window.GravewrightTools?.isLayerVisible?.(p.layer, this.roomId) !== false);
      this._hasComposition = placements.some((p) => p.layer === "composition");
      this._lastCam = null;
      this.layer.innerHTML = placements.map((placement) => this.placementHtml(placement)).join("");
    }

    placementHtml(placement) {
      const g = this.displayGeom(placement);
      const w = g.w;
      const h = g.h;
      const left = g.left;
      const top = g.top;
      const rotation = g.rotation;
      const isComposition = placement.layer === "composition";
      const gmOnly = placement.layer === "gm";
      const zIndex = (isComposition ? 5 : 10) + Number(placement.z_index || 0);
      const movable = this.canMove(placement);
      const selected = this.selectedIds.has(placement.id);
      const classes = ["scene-image"];
      if (movable) classes.push("is-movable");
      if (selected) classes.push("is-selected");
      if (gmOnly) classes.push("is-gm-layer");
      if (isComposition) classes.push("is-composition");
      const id = esc(placement.id);


      const handle = (movable && selected && this.selectedIds.size === 1)
        ? `<span class="scene-image__resize" data-scene-image-handle="resize" data-scene-image-id="${id}" title="${esc(label("sceneImageLabelResize", "Drag to resize"))}" aria-hidden="true"></span>`
        : "";
      return `<div class="${classes.join(" ")}" data-scene-image-id="${id}" style="left:${left}px;top:${top}px;width:${w}px;height:${h}px;transform:translate(-50%, -50%) rotate(${rotation}deg);z-index:${zIndex}">
        <img src="${esc(placement.src || "")}" alt="" draggable="false">
        ${handle}
      </div>`;
    }

    placementById(id) {
      return this.placements.find((p) => p.id === id) || null;
    }

    centerScreen(placement) {
      const rect = this.layer.getBoundingClientRect();
      const g = this.displayGeom(placement);
      return { x: rect.left + g.left, y: rect.top + g.top };
    }

    nodeFor(placementId) {
      return this.layer.querySelector(`[data-scene-image-id="${CSS.escape(placementId)}"]`);
    }

    bind() {
      this.layer.addEventListener("contextmenu", (event) => {
        const el = event.target.closest(".scene-image");
        if (!el) return;
        const placement = this.placementById(el.dataset.sceneImageId);
        if (!placement || placement.layer !== activeLayer || !this.canMove(placement)) return;
        event.preventDefault();
        event.stopPropagation();

        if (!this.selectedIds.has(placement.id)) this.setSelection(placement.id, false);
        this.openMenu(placement, event.clientX, event.clientY);
      });

      this.layer.addEventListener("pointerdown", (event) => {
        const el = event.target.closest(".scene-image");
        if (!el) return;
        const placement = this.placementById(el.dataset.sceneImageId);
        if (!placement || placement.layer !== activeLayer || !this.canMove(placement)) return;


        event.stopPropagation();
        if (event.button !== 0) return;
        event.preventDefault();



        const additive = event.ctrlKey || event.metaKey || event.shiftKey;
        if (additive) {
          this.setSelection(placement.id, true);
          return;
        }
        if (!this.selectedIds.has(placement.id)) this.setSelection(placement.id, false);

        const single = this.selectedIds.size === 1;
        const center = this.centerScreen(placement);



        if (single && event.target.closest('[data-scene-image-handle="resize"]')) {
          const startDist = Math.hypot(event.clientX - center.x, event.clientY - center.y) || 1;
          this.drag = {
            mode: "resize", placementId: placement.id, node: this.nodeFor(placement.id),
            center, startDist, baseScale: Number(placement.scale || 1), moved: false,
          };
          return;
        }
        this.drag = {
          mode: "move",
          startScreenX: event.clientX, startScreenY: event.clientY,
          moved: false,
          items: this.selectedMovable().map((p) => ({
            placement: p, node: this.nodeFor(p.id),
            zoom: p.layer === "composition" ? this.camera().zoom : 1,
            startX: Number(p.x || 0), startY: Number(p.y || 0),
          })),
        };
      });

      this._onPointerMove = (event) => {
        const drag = this.drag;
        if (!drag) return;

        if (drag.mode === "resize") {
          const placement = this.placementById(drag.placementId);
          if (!placement) return;
          const dist = Math.hypot(event.clientX - drag.center.x, event.clientY - drag.center.y);
          const scale = Math.max(0.05, Math.min(20, drag.baseScale * (dist / drag.startDist)));
          if (Math.abs(scale - drag.baseScale) > 0.001) drag.moved = true;
          placement.scale = scale;
          this.positionNode(drag.node, placement);
          return;
        }

        if (drag.mode === "rotate") {
          const placement = this.placementById(drag.placementId);
          if (!placement) return;
          const angle = Math.atan2(event.clientY - drag.center.y, event.clientX - drag.center.x);
          const deltaDeg = (angle - drag.startAngle) * (180 / Math.PI);
          if (Math.abs(deltaDeg) > 0.5) drag.moved = true;
          placement.rotation = drag.startRotation + deltaDeg;
          this.positionNode(drag.node, placement);
          return;
        }

        const dx = event.clientX - drag.startScreenX;
        const dy = event.clientY - drag.startScreenY;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) drag.moved = true;
        drag.items.forEach((item) => {
          item.placement.x = item.startX + dx / (item.zoom || 1);
          item.placement.y = item.startY + dy / (item.zoom || 1);
          this.positionNode(item.node, item.placement);
        });
      };

      this._onPointerUp = () => {
        const drag = this.drag;
        if (!drag) return;
        this.drag = null;
        if (!drag.moved) return;
        if (drag.mode === "resize" || drag.mode === "rotate") {
          const placement = this.placementById(drag.placementId);
          if (!placement) return;
          const payload = { placement_id: placement.id };
          if (drag.mode === "resize") payload.scale = placement.scale;
          else payload.rotation = placement.rotation;
          api.update(this.roomId, payload).catch(() => this.refresh());
          const key = drag.mode === "resize" ? "scale" : "rotation";
          const before = drag.mode === "resize" ? drag.baseScale : drag.startRotation;
          const after = placement[key];
          window.GravewrightMap?.history?.push?.({
            undo: () => { placement[key] = before; this.positionNode(this.nodeFor(placement.id), placement); void api.update(this.roomId, { placement_id: placement.id, [key]: before }); },
            redo: () => { placement[key] = after; this.positionNode(this.nodeFor(placement.id), placement); void api.update(this.roomId, { placement_id: placement.id, [key]: after }); },
          });
          return;
        }
        const moves = drag.items.map((item) => ({ id: item.placement.id, placement: item.placement,
          from: { x: item.startX, y: item.startY }, to: { x: item.placement.x, y: item.placement.y } }));
        drag.items.forEach((item) => {
          api.update(this.roomId, {
            placement_id: item.placement.id, x: item.placement.x, y: item.placement.y,
          }).catch(() => this.refresh());
        });
        const apply = (side) => moves.forEach((move) => {
          Object.assign(move.placement, move[side]); this.positionNode(this.nodeFor(move.id), move.placement);
          void api.update(this.roomId, { placement_id: move.id, ...move[side] });
        });
        window.GravewrightMap?.history?.push?.({ undo: () => apply("from"), redo: () => apply("to") });
      };

      document.addEventListener("pointermove", this._onPointerMove);
      document.addEventListener("pointerup", this._onPointerUp);
      document.addEventListener("pointercancel", this._onPointerUp);
    }


    selectedMovable() {
      const sceneId = this.activeSceneId();
      return [...this.selectedIds]
        .map((id) => this.placementById(id))
        .filter((p) => p && p.layer === activeLayer && this.canMove(p) && p.scene_id === sceneId);
    }

    setSelection(id, additive) {
      const placement = this.placementById(id);
      if (!placement || placement.layer !== activeLayer) return;
      if (additive) {
        if (this.selectedIds.has(id)) this.selectedIds.delete(id);
        else this.selectedIds.add(id);
      } else if (!this.selectedIds.has(id)) {
        this.selectedIds.clear();
        this.selectedIds.add(id);
      }
      this.render();
    }

    deselect() {
      if (!this.selectedIds.size) return;
      this.selectedIds.clear();
      this.render();
    }




    selectInRect(rect, { additive = false } = {}) {
      if (!additive) this.selectedIds.clear();
      this.placements.forEach((p) => {
        if (!this.canMove(p) || p.layer !== activeLayer) return;
        const node = this.nodeFor(p.id);
        if (!node) return;
        const r = node.getBoundingClientRect();
        if (r.left <= rect.right && r.right >= rect.left && r.top <= rect.bottom && r.bottom >= rect.top) {
          this.selectedIds.add(p.id);
        }
      });
      this.render();
    }

    rotateSelectedBy(deltaDeg) {
      const movers = this.selectedMovable();
      if (!movers.length) return false;
      movers.forEach((placement) => {
        placement.rotation = Number(placement.rotation || 0) + deltaDeg;
        const node = this.nodeFor(placement.id);
        if (node) node.style.transform = `translate(-50%, -50%) rotate(${placement.rotation}deg)`;
      });
      window.clearTimeout(this._rotateTimer);
      this._rotateTimer = window.setTimeout(() => {
        movers.forEach((p) => api.update(this.roomId, { placement_id: p.id, rotation: p.rotation }).catch(() => this.refresh()));
      }, 240);
      return true;
    }

    moveSelectedBy(dx, dy, record = true, placementIds = null) {
      const movers = placementIds
        ? placementIds.map((id) => this.placementById(id)).filter((item) => item && !item.locked)
        : this.selectedMovable();
      if (!movers.length || (!dx && !dy)) return false;
      movers.forEach((placement) => {
        placement.x = Number(placement.x || 0) + dx;
        placement.y = Number(placement.y || 0) + dy;
        const node = this.nodeFor(placement.id);
        if (node) this.positionNode(node, placement);
        api.update(this.roomId, { placement_id: placement.id, x: placement.x, y: placement.y })
          .catch(() => this.refresh());
      });
      if (record) {
        const ids = movers.map((placement) => placement.id);
        window.GravewrightMap?.history?.push?.({
        undo: () => this.moveSelectedBy(-dx, -dy, false, ids),
        redo: () => this.moveSelectedBy(dx, dy, false, ids),
      });
      }
      return true;
    }

    openMenu(placement, clientX, clientY) {
      const targets = this.selectedMovable();
      const suffix = targets.length > 1 ? ` (${targets.length})` : "";
      const items = [
        { label: label("sceneImageLabelBringFront", "Bring to front") + suffix, icon: "ph-arrow-line-up", onClick: () => this.zOrder(targets, true) },
        { label: label("sceneImageLabelSendBack", "Send to back") + suffix, icon: "ph-arrow-line-down", onClick: () => this.zOrder(targets, false) },
        { label: label("sceneImageLabelDuplicate", "Duplicate on active layer") + suffix, icon: "ph-copy", onClick: () => this.duplicateSelected() },
      ];
      if (this.isGm) {
        const layerLabels = {
          game: label("sceneImageLabelMoveGame", "Move to game layer"),
          gm: label("sceneImageLabelMoveGm", "Move to GM layer"),
          composition: label("sceneImageLabelMoveComposition", "Move to composition"),
        };
        ["game", "gm", "composition"].filter((layer) => layer !== activeLayer).forEach((layer) => {
          items.push({ label: layerLabels[layer] + suffix, icon: layer === "composition" ? "ph-images" : "ph-stack",
            onClick: () => this.moveToLayer(targets, layer) });
        });
      }
      items.push({ separator: true });
      items.push({ label: label("sceneImageLabelDelete", "Delete") + suffix, icon: "ph-trash", danger: true, onClick: () => this.deleteSelected() });
      window.GravewrightContextMenu?.show(clientX, clientY, items);
    }

    toggleGmLayer(placements, next) {
      if (!this.isGm) return;
      const list = (Array.isArray(placements) ? placements : [placements]).filter((p) => p && p.layer !== "composition");
      list.forEach((placement) => {
        placement.layer = next;
        placement.gm_only = next === "gm";
      });
      this.render();
      list.forEach((p) => api.update(this.roomId, { placement_id: p.id, layer: next }).catch(() => this.refresh()));
    }

    moveToLayer(placements, next) {
      if (!this.isGm || !["game", "gm", "composition"].includes(next)) return;
      const list = (Array.isArray(placements) ? placements : [placements]).filter(Boolean);
      const zoom = this.camera().zoom || 1;
      list.forEach((placement) => {
        const screen = this.displayGeom(placement);
        const point = this.toStored(screen.left, screen.top, next);
        let scale = Number(placement.scale || 1);
        if (placement.layer === "composition" && next !== "composition") scale *= zoom;
        if (placement.layer !== "composition" && next === "composition") scale /= zoom;
        placement.x = point.x; placement.y = point.y; placement.scale = scale;
        placement.layer = next; placement.gm_only = next === "gm";
        api.update(this.roomId, { placement_id: placement.id, x: point.x, y: point.y, scale, layer: next })
          .catch(() => this.refresh());
      });
      this.selectedIds.clear();
      this.render();
    }

    duplicateSelected() {
      const list = this.selectedMovable();
      if (!list.length) return false;
      imageClipboard = list.map((placement) => ({ ...placement }));
      return this.pasteSnapshots(imageClipboard, true);
    }

    copySelected() {
      const list = this.selectedMovable();
      if (!list.length) return false;
      imageClipboard = list.map((placement) => ({ ...placement }));
      return true;
    }

    pasteSnapshots(source = imageClipboard, record = true) {
      const list = (source || []).filter((placement) => placement.scene_id === this.activeSceneId());
      if (!list.length) return false;
      const offset = activeLayer === "composition" ? 12 / (this.camera().zoom || 1) : 12;
      Promise.all(list.map((placement) => api.placeAsset(this.roomId, {
        scene_id: placement.scene_id, asset_id: placement.asset_id,
        x: Number(placement.x || 0) + offset, y: Number(placement.y || 0) + offset,
        rotation: Number(placement.rotation || 0), scale: Number(placement.scale || 1), layer: activeLayer,
      }))).then((results) => {
        let live = results.map((result) => result.placement).filter(Boolean);
        this.placements.push(...live); this.selectedIds = new Set(live.map((item) => item.id)); this.render();
        if (record) window.GravewrightMap?.history?.push?.({
          undo: async () => { await Promise.all(live.map((item) => api.remove(this.roomId, item.id))); this.placements = this.placements.filter((item) => !live.some((gone) => gone.id === item.id)); this.render(); },
          redo: async () => { live = await this.createSnapshots(list, offset); },
        });
      }).catch(() => this.refresh());
      return true;
    }

    async createSnapshots(list, offset = 0) {
      const results = await Promise.all(list.map((placement) => api.placeAsset(this.roomId, {
        scene_id: placement.scene_id, asset_id: placement.asset_id,
        x: Number(placement.x || 0) + offset, y: Number(placement.y || 0) + offset,
        rotation: Number(placement.rotation || 0), scale: Number(placement.scale || 1), layer: activeLayer,
      })));
      const created = results.map((result) => result.placement).filter(Boolean);
      this.placements.push(...created); this.selectedIds = new Set(created.map((item) => item.id)); this.render();
      return created;
    }

    zOrder(placements, toFront) {
      const list = Array.isArray(placements) ? placements : [this.placementById(placements)].filter(Boolean);
      if (!list.length) return;
      const peers = this.placements.filter((p) => p.scene_id === list[0].scene_id);
      const zs = peers.map((p) => Number(p.z_index || 0));
      const base = toFront ? Math.max(...zs, 0) + 1 : Math.min(...zs, 0) - list.length;
      list.forEach((placement, i) => { placement.z_index = base + i; });
      this.render();
      list.forEach((p) => api.update(this.roomId, { placement_id: p.id, z_index: p.z_index }).catch(() => this.refresh()));
    }

    deleteSelected() {
      const movers = this.selectedMovable();
      if (!movers.length) return false;
      const ids = movers.map((p) => p.id);
      this.selectedIds.clear();
      this.placements = this.placements.filter((p) => !ids.includes(p.id));
      this.render();
      ids.forEach((id) => api.remove(this.roomId, id).catch(() => this.refresh()));
      let live = movers.map((item) => ({ ...item }));
      window.GravewrightMap?.history?.push?.({
        undo: async () => { live = await this.createSnapshots(movers, 0); },
        redo: async () => { await Promise.all(live.map((item) => api.remove(this.roomId, item.id))); this.placements = this.placements.filter((item) => !live.some((gone) => gone.id === item.id)); this.render(); },
      });
      return true;
    }



    toStored(x, y, layer) {
      if (layer === "composition") {
        const cam = this.camera();
        return { x: (x - cam.offsetX) / cam.zoom, y: (y - cam.offsetY) / cam.zoom };
      }
      return { x, y };
    }

    async uploadFile(file, x, y) {
      const sceneId = this.activeSceneId();
      if (!sceneId) return;
      const layer = activeLayer;
      const point = this.toStored(x, y, layer);
      try {
        await api.upload(this.roomId, sceneId, file, point.x, point.y, layer);
        await this.refresh();
      } catch (error) {
        if (window.GravewrightToasts?.showToast) {
          window.GravewrightToasts.showToast(label("sceneImageLabelUploadFailed", "Could not upload the image."), { duration: 2600 });
        }
        throw error;
      }
    }

    async placeLibraryAssetAt(assetId, clientX, clientY) {
      const sceneId = this.activeSceneId();
      if (!sceneId || !assetId) return false;
      const rect = this.layer.getBoundingClientRect();
      const layer = activeLayer;
      const point = this.toStored(clientX - rect.left, clientY - rect.top, layer);
      await api.placeAsset(this.roomId, {
        scene_id: sceneId,
        asset_id: assetId,
        x: point.x,
        y: point.y,
        layer,
      });
      await this.refresh();
      return true;
    }
  }

  function controllerForCanvas(canvas) {
    const layer = canvas?.closest("[data-map-viewport]")?.querySelector("[data-scene-image-layer]");
    if (!layer) return null;
    return controllers.get(layer.dataset.roomId || "") || null;
  }

  SceneImages.isSupportedImage = function isSupportedImage(file) {
    if (!file) return false;
    if (file.type) return ALLOWED_TYPES.has(file.type);
    return false;
  };

  SceneImages.hasImageFiles = function hasImageFiles(dataTransfer) {
    const items = dataTransfer?.items;
    if (items && items.length) {
      return Array.from(items).some((item) => item.kind === "file" && item.type.startsWith(IMAGE_MIME_PREFIX));
    }
    return Array.from(dataTransfer?.types || []).includes("Files");
  };

  SceneImages.uploadFilesAt = async function uploadFilesAt(canvas, files, clientX, clientY) {
    const controller = controllerForCanvas(canvas);
    if (!controller) return false;
    const images = Array.from(files || []).filter((file) => file.type.startsWith(IMAGE_MIME_PREFIX));
    if (!images.length) return false;
    const rect = controller.layer.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    for (const file of images) {
      await controller.uploadFile(file, x, y).catch(() => {});
    }
    return true;
  };

  SceneImages.placeLibraryAssetAt = async function placeLibraryAssetAt(canvas, raw, clientX, clientY) {
    const controller = controllerForCanvas(canvas);
    if (!controller || !raw) return false;
    try {
      const payload = JSON.parse(raw);
      return await controller.placeLibraryAssetAt(payload.asset_id, clientX, clientY);
    } catch {
      return false;
    }
  };


  SceneImages.selectInRect = function selectInRect(canvas, rect, opts) {
    controllerForCanvas(canvas)?.selectInRect(rect, opts || {});
  };

  function startTicker() {
    if (startTicker.handle) return;
    startTicker.handle = window.setInterval(() => {
      controllers.forEach((controller) => {
        if (controller.drag) return;
        if (controller.activeSceneId() !== controller.lastSceneId) {
          controller.render();
        }
      });
    }, 250);
  }



  function startCompositionFollow() {
    if (startCompositionFollow.running) return;
    startCompositionFollow.running = true;
    function frame() {
      controllers.forEach((controller) => controller.syncComposition());
      window.requestAnimationFrame(frame);
    }
    window.requestAnimationFrame(frame);
  }

  function init() {
    document.querySelectorAll("[data-scene-image-layer]").forEach((layer) => {
      if (layer.dataset.sceneImageReady === "true") return;
      layer.dataset.sceneImageReady = "true";
      new SceneImageController(layer);
    });
    startTicker();
    startCompositionFollow();

    document.addEventListener("tool:active-layer", (event) => {
      const layer = event.detail?.layer;
      const known = window.GravewrightToolsRegistry?.LAYERS
        || ["game", "gm", "composition", "effects", "walls", "lighting"];
      activeLayer = known.includes(layer) ? layer : "game";
      controllers.forEach((controller) => {
        controller.selectedIds.forEach((id) => {
          if (controller.placementById(id)?.layer !== activeLayer) controller.selectedIds.delete(id);
        });
        controller.render();
      });
    });

    document.addEventListener("tool:layer-state", (event) => {
      const controller = controllers.get(event.detail?.roomId);
      if (!controller) return;
      controller.selectedIds.forEach((id) => {
        const placement = controller.placementById(id);
        if (!placement || event.detail.visibility?.[placement.layer] === false
            || event.detail.locked?.[placement.layer]) controller.selectedIds.delete(id);
      });
      controller.render();
    });


    document.addEventListener("click", (event) => {
      const toggle = event.target.closest("[data-layer-hud-toggle]");
      if (!toggle) return;
      toggle.closest("[data-layer-hud]")?.classList.toggle("is-collapsed");
    });

    document.addEventListener("vtt:transport-event", (event) => {
      if (event.detail?.event !== "scene.images.updated") return;
      const controller = controllers.get(event.detail?.payload?.room_id);
      controller?.refresh();
    });



    document.addEventListener("pointerdown", (event) => {
      if (event.target.closest(".scene-image")) return;
      controllers.forEach((controller) => controller.deselect());
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        controllers.forEach((controller) => controller.deselect());
        return;
      }
      if (!isEditableTarget(event.target) && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "c") {
        for (const controller of controllers.values()) if (controller.copySelected()) { event.preventDefault(); return; }
      }
      if (!isEditableTarget(event.target) && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "v") {
        for (const controller of controllers.values()) if (controller.pasteSnapshots()) { event.preventDefault(); return; }
      }
      const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
      if (!isEditableTarget(event.target) && arrows[event.key]) {
        const [x, y] = arrows[event.key];
        for (const controller of controllers.values()) {
          const tile = Number(window.GravewrightMap?.sceneDataFor?.(controller.canvas)?.scaledTileSize || 32);
          const step = event.shiftKey ? 1 : tile / 2;
          if (controller.moveSelectedBy(x * step, y * step)) { event.preventDefault(); return; }
        }
      }
      if (event.key !== "Delete" && event.key !== "Backspace") return;
      if (isEditableTarget(event.target)) return;
      for (const controller of controllers.values()) {
        if (controller.deleteSelected()) {
          event.preventDefault();
          return;
        }
      }
    });



    document.addEventListener("wheel", (event) => {
      if (!event.shiftKey) return;
      const delta = event.deltaY || event.deltaX;
      if (!delta) return;
      const step = delta > 0 ? 6 : -6;
      for (const controller of controllers.values()) {
        if (controller.rotateSelectedBy(step)) {
          event.preventDefault();
          event.stopImmediatePropagation();
          return;
        }
      }
    }, { capture: true, passive: false });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
