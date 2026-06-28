(function () {
  const Cards = (window.GravewrightCards = window.GravewrightCards || {});

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[ch]);
  }

  function assetUrl(assetId) {
    return `/game/journal/asset/${encodeURIComponent(assetId)}`;
  }

  function label(name, fallback) {
    return document.body?.dataset?.[name] || fallback;
  }

  function format(template, values) {
    return String(template || "").replace(/\{(\w+)\}/g, (_, key) => String(values?.[key] ?? `{${key}}`));
  }

  // Don't hijack Delete/Backspace while the user is typing in a field.
  function isEditableTarget(target) {
    const el = target instanceof Element ? target : null;
    if (!el) return false;
    if (el.isContentEditable) return true;
    const tag = el.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
  }

  // ── Card table layer ────────────────────────────────────────────────────
  // Cards played to a scene live here, anchored to scene world coordinates so
  // they pan/zoom with the board. The interaction model mirrors the scene-image
  // (asset) layer — select, move, resize via the corner handle, rotate with
  // Shift-drag or Shift+wheel, z-order — but cards stay in the cards domain so
  // face state, ownership and discard-back-to-pile keep working.
  const tableControllers = new Set();

  function isGmForRoom(roomId) {
    return !!document.querySelector(`[data-card-panel][data-room-id="${CSS.escape(roomId)}"][data-is-gm="true"]`);
  }

  function refreshRoom(roomId) {
    document.querySelectorAll(`[data-card-panel][data-room-id="${CSS.escape(roomId)}"]`)
      .forEach((root) => root.__cardPanel?.refresh());
  }

  function tableCardFace(card, placement) {
    if (placement.face_state === "face_down") {
      if (card?.back_asset_id) {
        return `<img src="${assetUrl(card.back_asset_id)}" alt="${esc(label("cardLabelCardBack", "Card back"))}" draggable="false">`;
      }
      return '<div class="table-card__back" aria-hidden="true"><i class="ph ph-cards"></i></div>';
    }
    if (card?.front_asset_id) {
      return `<img src="${assetUrl(card.front_asset_id)}" alt="${esc(card.name || label("cardLabelCardName", "Card"))}" draggable="false">`;
    }
    return '<i class="ph ph-cardholder" aria-hidden="true"></i>';
  }

  class CardTableController {
    constructor(layer) {
      this.layer = layer;
      this.roomId = layer.dataset.roomId || "";
      this.userId = document.body.dataset.currentUserId || "";
      this.cards = [];
      this.placements = [];
      this.selectedIds = new Set();
      this.drag = null;
      this.state = null;
      this._sig = "";
      this._sceneId = "";
      this._lastCam = null;
      layer.__cardTable = this;
      tableControllers.add(this);
      this.bind();
    }

    canvas() {
      return this.layer.closest("[data-map-viewport]")?.querySelector("[data-map-canvas]") || null;
    }

    activeSceneId() {
      return this.canvas()?.dataset.sceneId || "";
    }

    // GM controls every table card; a player controls only the cards they own
    // (and that aren't locked) — same rule the backend enforces.
    canMove(placement) {
      if (isGmForRoom(this.roomId)) return true;
      return !!placement && !placement.locked && !!placement.owner_user_id && placement.owner_user_id === this.userId;
    }

    camera() {
      const st = window.GravewrightMap?.stateFor?.(this.canvas());
      return { zoom: Number(st?.zoom) || 1, offsetX: Number(st?.offsetX) || 0, offsetY: Number(st?.offsetY) || 0 };
    }

    placementById(id) {
      return this.placements.find((p) => p.id === id) || null;
    }

    cardFor(placement) {
      return this.cards.find((item) => item.id === placement.card_instance_id) || {};
    }

    // Pull a fresh state snapshot and rebuild only when the placement set
    // actually changed (signature); otherwise leave the DOM for follow() to nudge.
    update(state) {
      this.state = state || null;
      if (this.drag) return;
      const sceneId = this.activeSceneId();
      const canvas = this.canvas();
      const valid = !!(state && canvas && sceneId && window.GravewrightMap?.stateFor && state.campaign_id === this.roomId);
      this.cards = valid ? (state.cards || []) : [];
      this.placements = valid ? (state.scene_placements || []).filter((p) => p.scene_id === sceneId) : [];
      this.selectedIds.forEach((id) => {
        if (!this.placements.some((p) => p.id === id)) this.selectedIds.delete(id);
      });
      const sig = this.signature();
      if (sig !== this._sig || sceneId !== this._sceneId) {
        this._sig = sig;
        this._sceneId = sceneId;
        this._lastCam = null;
        this.render();
      }
    }

    signature() {
      return this.placements
        .map((p) => `${p.id}:${p.card_instance_id}:${p.face_state}:${Math.round(p.x)}:${Math.round(p.y)}:${p.scale}:${p.rotation}:${p.z_index}`)
        .join("|") + `#${[...this.selectedIds].sort().join(",")}`;
    }

    displayGeom(placement) {
      const cam = this.camera();
      return {
        left: Number(placement.x || 0) * cam.zoom + cam.offsetX,
        top: Number(placement.y || 0) * cam.zoom + cam.offsetY,
        scale: Math.max(0.2, Number(placement.scale || 1) * cam.zoom),
        rotation: Number(placement.rotation || 0),
      };
    }

    nodeFor(id) {
      return this.layer.querySelector(`[data-table-card-id="${CSS.escape(id)}"]`);
    }

    positionNode(node, placement) {
      if (!node) return;
      const g = this.displayGeom(placement);
      node.style.left = `${g.left}px`;
      node.style.top = `${g.top}px`;
      node.style.transform = `translate(-50%, -50%) rotate(${g.rotation}deg) scale(${g.scale})`;
    }

    render() {
      if (!this.canvas() || !this.placements.length) {
        this.layer.innerHTML = "";
        return;
      }
      this.layer.innerHTML = this.placements.map((placement) => {
        const card = this.cardFor(placement);
        const g = this.displayGeom(placement);
        const zIndex = 20 + Number(placement.z_index || 0);
        const movable = this.canMove(placement);
        const selected = movable && this.selectedIds.has(placement.id);
        const classes = ["table-card"];
        if (movable) classes.push("is-movable");
        if (selected) classes.push("is-selected");
        // Resize handle only when exactly one card is selected.
        const handle = selected && this.selectedIds.size === 1
          ? '<span class="table-card__resize" data-table-card-handle="resize" aria-hidden="true"></span>'
          : "";
        return `<article class="${classes.join(" ")}" data-table-card-id="${esc(placement.id)}" style="left:${g.left}px;top:${g.top}px;transform:translate(-50%, -50%) rotate(${g.rotation}deg) scale(${g.scale});z-index:${zIndex}">
          <div class="table-card__image">${tableCardFace(card, placement)}</div>
          ${handle}
        </article>`;
      }).join("");
    }

    // Keep world-anchored cards glued to the board as the camera pans/zooms;
    // a no-op unless the camera actually moved since the last frame.
    follow() {
      if (this.drag || !this.placements.length) return;
      const cam = this.camera();
      const last = this._lastCam;
      if (last && cam.zoom === last.zoom && cam.offsetX === last.offsetX && cam.offsetY === last.offsetY) return;
      this._lastCam = cam;
      this.placements.forEach((p) => this.positionNode(this.nodeFor(p.id), p));
    }

    tick() {
      if (this.drag) return;
      if (this.activeSceneId() !== this._sceneId) {
        this.update(this.state);
        return;
      }
      this.follow();
    }

    centerScreen(placement) {
      const rect = this.layer.getBoundingClientRect();
      const g = this.displayGeom(placement);
      return { x: rect.left + g.left, y: rect.top + g.top };
    }

    // The selected placements the viewer is actually allowed to manipulate.
    selectedMovable() {
      return [...this.selectedIds]
        .map((id) => this.placementById(id))
        .filter((p) => p && this.canMove(p));
    }

    setSelection(id, additive) {
      if (additive) {
        if (this.selectedIds.has(id)) this.selectedIds.delete(id);
        else this.selectedIds.add(id);
      } else if (!this.selectedIds.has(id)) {
        this.selectedIds.clear();
        this.selectedIds.add(id);
      }
      this._sig = "";
      this.render();
    }

    deselect() {
      if (!this.selectedIds.size) return;
      this.selectedIds.clear();
      this._sig = "";
      this.render();
    }

    // Marquee selection: pick every movable card whose on-screen box touches the
    // screen-space rect (used by the board's right-to-left drag).
    selectInRect(rect, { additive = false } = {}) {
      if (!additive) this.selectedIds.clear();
      this.placements.forEach((p) => {
        if (!this.canMove(p)) return;
        const node = this.nodeFor(p.id);
        if (!node) return;
        const r = node.getBoundingClientRect();
        if (r.left <= rect.right && r.right >= rect.left && r.top <= rect.bottom && r.bottom >= rect.top) {
          this.selectedIds.add(p.id);
        }
      });
      this._sig = "";
      this.render();
    }

    persist(payload) {
      Cards.api.updateSceneCardPlacement(this.roomId, payload)
        .then(() => refreshRoom(this.roomId))
        .catch(() => refreshRoom(this.roomId));
    }

    persistBatch(payloads) {
      if (!payloads.length) return;
      Promise.all(payloads.map((p) => Cards.api.updateSceneCardPlacement(this.roomId, p).catch(() => {})))
        .then(() => refreshRoom(this.roomId));
    }

    zOrder(placements, toFront) {
      const list = Array.isArray(placements) ? placements : [placements];
      const zs = this.placements.map((p) => Number(p.z_index || 0));
      const base = toFront ? Math.max(...zs, 0) + 1 : Math.min(...zs, 0) - list.length;
      this.persistBatch(list.map((p, i) => ({ placement_id: p.id, z_index: base + i })));
    }

    deleteSelected() {
      const movers = this.selectedMovable();
      if (!movers.length) return false;
      this.selectedIds.clear();
      Promise.all(movers.map((p) => Cards.api.discardSceneCardPlacement(this.roomId, p.id).catch(() => {})))
        .then(() => refreshRoom(this.roomId));
      return true;
    }

    rotateSelectedBy(deltaDeg) {
      const movers = this.selectedMovable();
      if (!movers.length) return false;
      movers.forEach((placement) => {
        placement.rotation = Number(placement.rotation || 0) + deltaDeg;
        this.positionNode(this.nodeFor(placement.id), placement);
      });
      window.clearTimeout(this._rotateTimer);
      this._rotateTimer = window.setTimeout(() => {
        this.persistBatch(movers.map((p) => ({ placement_id: p.id, rotation: Number(p.rotation.toFixed(2)) })));
      }, 240);
      return true;
    }

    bind() {
      this.layer.addEventListener("pointerdown", (event) => {
        const el = event.target.closest("[data-table-card-id]");
        if (!el) return;
        const placement = this.placementById(el.dataset.tableCardId);
        if (!placement || !this.canMove(placement)) return;
        // Stop the map from panning under the card; let right-click fall through
        // to the contextmenu handler without starting a drag.
        event.stopPropagation();
        if (event.button !== 0) return;
        event.preventDefault();

        // Shift / Ctrl / Cmd + click toggles this card in the multi-selection
        // (no drag). Rotation lives on Shift + mouse wheel.
        const additive = event.ctrlKey || event.metaKey || event.shiftKey;
        if (additive) {
          this.setSelection(placement.id, true);
          return;
        }
        if (!this.selectedIds.has(placement.id)) this.setSelection(placement.id, false);

        const single = this.selectedIds.size === 1;
        const node = this.nodeFor(placement.id);
        const center = this.centerScreen(placement);

        // Resize acts on a single card; with several selected we move the whole
        // group together.
        if (single && event.target.closest('[data-table-card-handle="resize"]')) {
          const startDist = Math.hypot(event.clientX - center.x, event.clientY - center.y) || 1;
          this.drag = {
            mode: "resize", placementId: placement.id, node, center, startDist,
            baseScale: Number(placement.scale || 1), scale: Number(placement.scale || 1), moved: false,
          };
          return;
        }
        const cam = this.camera();
        this.drag = {
          mode: "move", zoom: cam.zoom,
          startScreenX: event.clientX, startScreenY: event.clientY,
          moved: false,
          items: this.selectedMovable().map((p) => ({
            placement: p, node: this.nodeFor(p.id),
            startX: Number(p.x || 0), startY: Number(p.y || 0),
          })),
        };
      });

      this._onMove = (event) => {
        const drag = this.drag;
        if (!drag) return;
        if (drag.mode === "resize") {
          const placement = this.placementById(drag.placementId) || {};
          const dist = Math.hypot(event.clientX - drag.center.x, event.clientY - drag.center.y);
          const scale = Math.max(0.1, Math.min(8, drag.baseScale * (dist / drag.startDist)));
          if (Math.abs(scale - drag.baseScale) > 0.001) drag.moved = true;
          drag.scale = scale;
          this.positionNode(drag.node, { ...placement, scale });
          return;
        }
        if (drag.mode === "rotate") {
          const placement = this.placementById(drag.placementId) || {};
          const angle = Math.atan2(event.clientY - drag.center.y, event.clientX - drag.center.x);
          const deltaDeg = (angle - drag.startAngle) * (180 / Math.PI);
          if (Math.abs(deltaDeg) > 0.5) drag.moved = true;
          drag.rotation = drag.startRotation + deltaDeg;
          this.positionNode(drag.node, { ...placement, rotation: drag.rotation });
          return;
        }
        const dx = event.clientX - drag.startScreenX;
        const dy = event.clientY - drag.startScreenY;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) drag.moved = true;
        const zoom = drag.zoom || 1;
        drag.items.forEach((item) => {
          item.x = item.startX + dx / zoom;
          item.y = item.startY + dy / zoom;
          this.positionNode(item.node, { ...item.placement, x: item.x, y: item.y });
        });
      };

      this._onUp = () => {
        const drag = this.drag;
        if (!drag) return;
        this.drag = null;
        if (!drag.moved) return;
        if (drag.mode === "resize") {
          this.persist({ placement_id: drag.placementId, scale: Number(drag.scale.toFixed(3)) });
        } else if (drag.mode === "rotate") {
          this.persist({ placement_id: drag.placementId, rotation: Number(drag.rotation.toFixed(2)) });
        } else {
          this.persistBatch(drag.items.map((item) => ({
            placement_id: item.placement.id, x: Math.round(item.x), y: Math.round(item.y),
          })));
        }
      };

      document.addEventListener("pointermove", this._onMove);
      document.addEventListener("pointerup", this._onUp);
      document.addEventListener("pointercancel", this._onUp);

      this.layer.addEventListener("contextmenu", (event) => {
        const el = event.target.closest("[data-table-card-id]");
        if (!el) return;
        const placement = this.placementById(el.dataset.tableCardId);
        if (!placement || !this.canMove(placement)) return;
        event.preventDefault();
        event.stopPropagation();
        // Right-clicking a card outside the current selection selects just it;
        // otherwise the menu acts on the whole selection.
        if (!this.selectedIds.has(placement.id)) this.setSelection(placement.id, false);
        const targets = this.selectedMovable();
        const many = targets.length > 1;
        const suffix = many ? ` (${targets.length})` : "";
        const faceTarget = placement.face_state === "face_up" ? "face_down" : "face_up";
        window.GravewrightContextMenu?.show(event.clientX, event.clientY, [
          {
            label: (placement.face_state === "face_up" ? label("cardLabelFlipDown", "Flip face down") : label("cardLabelFlipUp", "Flip face up")) + suffix,
            icon: "ph-arrows-clockwise",
            onClick: () => this.persistBatch(targets.map((p) => ({ placement_id: p.id, face_state: faceTarget }))),
          },
          { label: label("cardLabelBringFront", "Bring to front") + suffix, icon: "ph-arrow-line-up", onClick: () => this.zOrder(targets, true) },
          { label: label("cardLabelSendBack", "Send to back") + suffix, icon: "ph-arrow-line-down", onClick: () => this.zOrder(targets, false) },
          { separator: true },
          {
            label: label("cardLabelRemoveTable", "Remove from table") + suffix,
            icon: "ph-trash",
            danger: true,
            onClick: () => {
              const ids = targets.map((p) => p.id);
              this.selectedIds.clear();
              Promise.all(ids.map((id) => Cards.api.discardSceneCardPlacement(this.roomId, id).catch(() => {})))
                .then(() => refreshRoom(this.roomId));
            },
          },
        ]);
      });
    }
  }

  function renderSceneLayer(state) {
    document.querySelectorAll("[data-card-scene-layer]").forEach((layer) => {
      const controller = layer.__cardTable || new CardTableController(layer);
      controller.update(state);
    });
  }

  function startTableFollow() {
    if (startTableFollow.running) return;
    startTableFollow.running = true;
    function frame() {
      tableControllers.forEach((controller) => controller.tick());
      window.requestAnimationFrame(frame);
    }
    window.requestAnimationFrame(frame);
  }

  function bindGlobalTableHandlers() {
    if (bindGlobalTableHandlers.bound) return;
    bindGlobalTableHandlers.bound = true;

    // Deselect when clicking empty space (table cards stopPropagation on their
    // own pointerdown, so this only fires off-card).
    document.addEventListener("pointerdown", (event) => {
      if (event.target.closest("[data-table-card-id]")) return;
      tableControllers.forEach((controller) => controller.deselect());
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        tableControllers.forEach((controller) => controller.deselect());
        return;
      }
      if (event.key !== "Delete" && event.key !== "Backspace") return;
      if (isEditableTarget(event.target)) return;
      for (const controller of tableControllers) {
        if (controller.deleteSelected()) {
          event.preventDefault();
          return;
        }
      }
    });

    // Shift + wheel rotates the selected table card. Capture phase so it wins
    // over the map zoom-wheel handler; only consumes the event if it rotated.
    document.addEventListener("wheel", (event) => {
      if (!event.shiftKey) return;
      const delta = event.deltaY || event.deltaX;
      if (!delta) return;
      const step = delta > 0 ? 6 : -6;
      for (const controller of tableControllers) {
        if (controller.rotateSelectedBy(step)) {
          event.preventDefault();
          event.stopImmediatePropagation();
          return;
        }
      }
    }, { capture: true, passive: false });
  }

  class CardPanel {
    constructor(root) {
      this.root = root;
      this.roomId = root.dataset.roomId;
      this.mode = root.dataset.cardPanelMode || "deck";
      this.userId = document.body.dataset.currentUserId || "";
      this.isGm = root.dataset.isGm === "true";
      this.store = new Cards.CardStateStore();
      this.store.subscribe(() => this.render());
      // Hand cards the player has flipped to their back face (local-only): the
      // shown face decides which face the card lands on when dragged to the table.
      this.flipped = new Set();
      root.__cardPanel = this;
      this.bind();
      // Re-fit the fan when the hand panel is shown or resized (modal open,
      // window/modal resize) — innerHTML stays put, only the CSS vars change.
      if (this.mode === "hand" && typeof ResizeObserver !== "undefined") {
        this.handHost = root.querySelector("[data-card-hand]");
        if (this.handHost) {
          this.resizeObserver = new ResizeObserver(() => this.layoutFan());
          this.resizeObserver.observe(this.handHost);
        }
      }
      this.refresh();
    }

    async refresh() {
      this.root.classList.add("is-loading");
      try {
        this.store.replaceState(await Cards.api.fetchCardState(this.roomId));
      } catch (error) {
        this.notice(error.message || label("cardLabelRequestFailed", "Cards request failed."), true);
      } finally {
        this.root.classList.remove("is-loading");
      }
    }

    bind() {
      this.root.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-card-action]");
        if (!button) return;
        const action = button.dataset.cardAction;
        if (action === "refresh") this.refresh();
        if (action === "shuffle") this.shuffle(button.dataset.deckId);
        if (action === "delete-deck") this.removeDeck(button.dataset.deckId, button.dataset.deckName);
        if (action === "draw-selected") this.drawSelected("hand");
        if (action === "draw-chat-selected") this.drawSelected("chat");
        if (action === "flip-hand") this.toggleHandFlip(button.dataset.cardId);
        if (action === "discard") this.discard(button.dataset.cardId);
        if (action === "flip") this.flipPlacement(button.dataset.placementId, button.dataset.faceState);
        if (action === "discard-placement") this.discardPlacement(button.dataset.placementId);
        if (action === "reset") this.reset(button.dataset.deckId);
      });

      const form = this.root.querySelector("[data-card-create-form]");
      if (form) {
        form.addEventListener("submit", (event) => {
          event.preventDefault();
          this.createDeck(form);
        });
      }
      this.root.addEventListener("cards:refresh", () => this.refresh());

      this.root.addEventListener("change", (event) => {
        if (event.target.matches("[data-hand-deck]")) {
          this.selectedDeckId = event.target.value;
          this.render();
        }
      });

      this.root.addEventListener("dragstart", (event) => {
        const article = event.target.closest("[data-card-drag-id]");
        if (!article || !event.dataTransfer) return;
        const img = article.querySelector("img");
        // A card flipped to its back in hand lands face-down on the table.
        const flipped = article.dataset.cardFlipped === "true";
        const payload = {
          card_id: article.dataset.cardDragId,
          roomId: this.roomId,
          name: article.dataset.cardName || "",
          src: img?.currentSrc || img?.src || "",
          width: 128,
          height: 180,
          reveal: !flipped,
        };
        Cards.currentDragPayload = payload;
        event.dataTransfer.setData(
          "application/x-gravewright-card+json",
          JSON.stringify(payload),
        );
        event.dataTransfer.effectAllowed = "move";
      });

      this.root.addEventListener("dragend", () => {
        Cards.currentDragPayload = null;
      });
    }

    async createDeck(form) {
      const files = Array.from(form.querySelector('[name="fronts"]').files || []);
      const name = form.querySelector('[name="name"]').value.trim();
      const backFile = form.querySelector('[name="back"]').files?.[0] || null;
      if (!this.isGm || !name || !files.length) return;
      try {
        this.notice(label("cardLabelUploading", "Uploading card assets..."));
        const back = backFile ? await Cards.api.uploadCardAsset(this.roomId, backFile, { purpose: "card_back" }) : null;
        const uploaded = [];
        for (const file of files) {
          uploaded.push(await Cards.api.uploadCardAsset(this.roomId, file, { purpose: "card_front" }));
        }
        const deck = await Cards.api.createDeckDefinition(this.roomId, {
          name,
          default_back_asset_id: back?.asset_id || null,
          cards: uploaded.map((asset, index) => ({
            name: files[index].name.replace(/\.[^.]+$/, "") || format(label("cardLabelCardNumber", "Card {count}"), { count: index + 1 }),
            front_asset_id: asset.asset_id,
            back_asset_id: back?.asset_id || null,
            metadata: { src: asset.src },
          })),
        });
        await Cards.api.instantiateDeck(this.roomId, deck.deck.id, {});
        form.reset();
        this.notice(label("cardLabelDeckCreated", "Deck created."));
        await this.refresh();
      } catch (error) {
        this.notice(error.message || label("cardLabelDeckCreationFailed", "Deck creation failed."), true);
      }
    }

    async shuffle(deckId) {
      // Shuffling only reorders the (hidden) draw pile, so confirm it visibly —
      // otherwise the button looks like it does nothing.
      try {
        await Cards.api.shuffleDeck(this.roomId, deckId);
        await this.refresh();
        this.notice(label("cardLabelDeckShuffled", "Deck shuffled."));
      } catch (error) {
        this.notice(error.message || label("cardLabelRequestFailed", "Cards request failed."), true);
      }
    }

    async reset(deckId) {
      await this.run(() => Cards.api.resetDeck(this.roomId, deckId, { shuffle: true }));
    }

    async removeDeck(deckId, deckName) {
      if (!deckId) return;
      const deckLabel = deckName ? `"${deckName}"` : label("cardLabelThisDeck", "this deck");
      if (!window.confirm(format(label("cardLabelDeleteDeckConfirm", "Remove {deck}? All its cards in hands, discard and table will be deleted."), { deck: deckLabel }))) return;
      try {
        await Cards.api.deleteDeck(this.roomId, deckId);
        await this.refresh();
        this.notice(label("cardLabelDeckRemoved", "Deck removed."));
      } catch (error) {
        this.notice(error.message || label("cardLabelRequestFailed", "Cards request failed."), true);
      }
    }

    async draw(deckId, destination) {
      await this.run(() => Cards.api.drawCards(this.roomId, { deck_instance_id: deckId, count: 1, destination }));
    }

    async drawSelected(destination = "hand") {
      const select = this.root.querySelector("[data-hand-deck]");
      const deckId = select?.value || this.selectedDeckId;
      if (!deckId) return;
      await this.draw(deckId, destination);
    }

    // Flip a hand card between its front and back face. Local-only — the player
    // just decides which side to show before dragging it onto the table.
    toggleHandFlip(cardId) {
      if (!cardId) return;
      if (this.flipped.has(cardId)) this.flipped.delete(cardId);
      else this.flipped.add(cardId);
      this.render();
    }

    async discard(cardId) {
      await this.run(() => Cards.api.discardCards(this.roomId, [cardId]));
    }

    async flipPlacement(placementId, currentFace) {
      await this.run(() => Cards.api.updateSceneCardPlacement(this.roomId, {
        placement_id: placementId,
        face_state: currentFace === "face_up" ? "face_down" : "face_up",
      }));
    }

    async discardPlacement(placementId) {
      await this.run(() => Cards.api.discardSceneCardPlacement(this.roomId, placementId));
    }

    async run(operation) {
      try {
        await operation();
        await this.refresh();
      } catch (error) {
        this.notice(error.message || label("cardLabelRequestFailed", "Cards request failed."), true);
      }
    }

    notice(message, danger = false) {
      const target = this.root.querySelector("[data-card-notice]");
      if (!target) return;
      const labels = {
        "game.cards.errors.invalid_draw": label("cardLabelErrorInvalidDraw", "Deck is empty."),
        "game.cards.errors.deck_not_found": label("cardLabelErrorDeckNotFound", "Deck is no longer available."),
        "game.cards.errors.pile_not_found": label("cardLabelErrorPileNotFound", "Card pile is no longer available."),
        "permissions.errors.denied": label("cardLabelErrorDenied", "You cannot perform this card action."),
      };
      target.textContent = labels[message] || message;
      target.hidden = false;
      target.classList.toggle("is-danger", danger);
      window.clearTimeout(this.noticeTimer);
      this.noticeTimer = window.setTimeout(() => { target.hidden = true; }, 3500);
    }

    render() {
      const state = this.store.state || {};
      renderSceneLayer(state);
      if (this.mode === "deck") {
        this.renderDecks(state);
      }
      if (this.mode === "hand") {
        this.renderHand(state);
      }
    }

    renderDecks(state) {
      const host = this.root.querySelector("[data-card-decks]");
      if (!host) return;
      const decks = state.decks || [];
      if (!decks.length) {
        host.innerHTML = `<div class="cards-empty">${esc(label("cardLabelEmptyDecks", "No decks in play."))}</div>`;
        return;
      }
      host.innerHTML = decks.map((deck) => {
        const drawCount = Number.isFinite(Number(deck.draw_count)) ? Number(deck.draw_count) : null;
        const countLabel = drawCount === null ? label("cardLabelDeckReady", "Deck ready") : format(label("cardLabelCardsRemaining", "{count} cards remaining"), { count: drawCount });
        return `<article class="cards-deck">
          <div class="cards-deck-stack" aria-hidden="true">
            <span class="cards-deck-card cards-deck-card--back"></span>
            <span class="cards-deck-card cards-deck-card--mid"></span>
            <span class="cards-deck-card cards-deck-card--top">
              <i class="ph ph-cards" aria-hidden="true"></i>
            </span>
          </div>
          <div class="cards-deck-caption">
            <strong>${esc(deck.name)}</strong>
            <small>${esc(countLabel)}</small>
          </div>
          <div class="cards-deck-actions">
            <button type="button" data-card-action="shuffle" data-deck-id="${esc(deck.id)}" title="${esc(label("cardLabelShuffle", "Shuffle"))}"><i class="ph ph-shuffle"></i><span>${esc(label("cardLabelShuffle", "Shuffle"))}</span></button>
            <button type="button" data-card-action="reset" data-deck-id="${esc(deck.id)}" title="${esc(label("cardLabelReset", "Reset"))}"><i class="ph ph-arrow-clockwise"></i><span>${esc(label("cardLabelReset", "Reset"))}</span></button>
            ${this.isGm ? `<button type="button" class="is-danger" data-card-action="delete-deck" data-deck-id="${esc(deck.id)}" data-deck-name="${esc(deck.name)}" title="${esc(label("cardLabelRemoveDeck", "Remove deck"))}"><i class="ph ph-trash"></i><span>${esc(label("cardLabelRemoveDeck", "Remove"))}</span></button>` : ""}
          </div>
        </article>`;
      }).join("");
    }

    renderHand(state) {
      const host = this.root.querySelector("[data-card-hand]");
      if (!host) return;
      const decks = state.decks || [];
      const drawbar = this.drawBarHtml(decks);
      const hand = this.store.getHandForUser(this.userId);
      let cards = hand ? this.store.cardsForPile(hand.id) : [];
      if (this.selectedDeckId) {
        cards = cards.filter((card) => card.deck_instance_id === this.selectedDeckId);
      }
      host.innerHTML = drawbar + this.fanHtml(cards);
      this.layoutFan();
      // Re-measure after layout settles (e.g. once the modal auto-fits its width).
      window.requestAnimationFrame(() => this.layoutFan());
    }

    // Size and overlap the hand so all cards fit the panel width without
    // scrolling: cards keep their natural size until space runs out, then
    // overlap more and finally shrink. Re-runs on resize via a ResizeObserver.
    layoutFan() {
      const host = this.handHost || this.root.querySelector("[data-card-hand]");
      const fan = host?.querySelector(".cards-fan:not(.is-empty)");
      if (!fan) return;
      const n = fan.querySelectorAll(".fan-card").length;
      const styles = getComputedStyle(fan);
      const padX = parseFloat(styles.paddingLeft) + parseFloat(styles.paddingRight);
      const avail = Math.max(0, fan.clientWidth - padX);
      if (!avail || n <= 0) return;
      const CW_MAX = 130;
      const CW_MIN = 64;
      const STEP_MAX = CW_MAX * 0.62;   // comfortable spread
      const STEP_TIGHT = 0.26;          // tightest visible strip (fraction of card)
      let cw = CW_MAX;
      let step = STEP_MAX;
      if (n > 1) {
        if (cw + (n - 1) * step > avail) {
          step = Math.max(cw * STEP_TIGHT, (avail - cw) / (n - 1));
        }
        if (cw + (n - 1) * step > avail) {
          cw = Math.max(CW_MIN, avail / (1 + (n - 1) * STEP_TIGHT));
          step = cw * STEP_TIGHT;
        }
      }
      fan.style.setProperty("--fan-card-w", `${Math.round(cw)}px`);
      fan.style.setProperty("--fan-overlap", `${Math.round(step - cw)}px`);
    }

    drawBarHtml(decks) {
      let selectedId = this.selectedDeckId && decks.some((d) => d.id === this.selectedDeckId)
        ? this.selectedDeckId
        : (decks[0]?.id || "");
      this.selectedDeckId = selectedId;
      const selected = decks.find((d) => d.id === selectedId) || null;
      const remaining = selected && Number.isFinite(Number(selected.draw_count)) ? Number(selected.draw_count) : null;
      const drawDisabled = !decks.length || remaining === 0;
      const options = decks.length
        ? decks.map((d) => `<option value="${esc(d.id)}"${d.id === selectedId ? " selected" : ""}>${esc(d.name)}</option>`).join("")
        : `<option value="">${esc(label("cardLabelNoDeck", "No deck available"))}</option>`;
      const count = remaining === null ? "" : format(label("cardLabelRemaining", "{count} remaining"), { count: remaining });
      return `<div class="hand-drawbar">
        <div class="hand-draw-pick">
          <i class="ph ph-cards" aria-hidden="true"></i>
          <select data-hand-deck aria-label="${esc(label("cardLabelDeckSelect", "Deck"))}"${decks.length ? "" : " disabled"}>${options}</select>
        </div>
        <button type="button" class="hand-draw-btn" data-card-action="draw-selected"${drawDisabled ? ' disabled aria-disabled="true"' : ""}>
          <i class="ph ph-plus" aria-hidden="true"></i><span>${esc(label("cardLabelDraw", "Draw"))}</span>
        </button>
        <button type="button" class="hand-draw-btn hand-draw-btn--chat" data-card-action="draw-chat-selected" title="${esc(label("cardLabelDrawChat", "Draw and reveal in chat"))}"${drawDisabled ? ' disabled aria-disabled="true"' : ""}>
          <i class="ph ph-chats" aria-hidden="true"></i><span>${esc(label("cardLabelToChat", "To chat"))}</span>
        </button>
        <small class="hand-draw-count">${esc(count)}</small>
      </div>`;
    }

    fanHtml(cards) {
      if (!cards.length) {
        return `<div class="cards-fan is-empty"><div class="cards-empty">${esc(label("cardLabelHandEmpty", "Your hand is empty. Draw a card."))}</div></div>`;
      }
      const n = cards.length;
      const spread = Math.min(7, 22 / Math.max(1, n - 1 || 1));
      const inner = cards.map((card, i) => {
        const offset = i - (n - 1) / 2;
        const rot = (offset * spread).toFixed(2);
        const arc = (Math.abs(offset) * 5).toFixed(1);
        const flipped = this.flipped.has(card.id);
        const flipTitle = flipped ? label("cardLabelShowFront", "Show front") : label("cardLabelShowBack", "Flip to back");
        return `<article class="fan-card${flipped ? " is-flipped" : ""}" draggable="true" data-card-drag-id="${esc(card.id)}" data-card-name="${esc(card.name || label("cardLabelCardName", "Card"))}" data-card-flipped="${flipped ? "true" : "false"}" title="${esc(label("cardLabelDragTable", "Drag to table"))}" style="--rot:${rot}deg;--arc:${arc}px;z-index:${i + 1}">
          <div class="fan-card__img">${this.handFace(card, flipped)}</div>
          <div class="fan-card__name">${esc(card.name || label("cardLabelCardName", "Card"))}</div>
          <div class="fan-card__actions">
            <button type="button" draggable="false" data-card-action="flip-hand" data-card-id="${esc(card.id)}" title="${esc(flipTitle)}"><i class="ph ph-arrows-clockwise"></i></button>
            <button type="button" draggable="false" data-card-action="discard" data-card-id="${esc(card.id)}" title="${esc(label("cardLabelDiscard", "Discard"))}"><i class="ph ph-trash"></i></button>
          </div>
        </article>`;
      }).join("");
      return `<div class="cards-fan" style="--count:${n}">${inner}</div>`;
    }

    // The face shown in hand: front by default, the card's back (or a generic
    // card-back) when the player has flipped it.
    handFace(card, flipped) {
      if (flipped) {
        if (card?.back_asset_id) {
          return `<img src="${assetUrl(card.back_asset_id)}" alt="${esc(label("cardLabelCardBack", "Card back"))}" draggable="false">`;
        }
        return '<div class="fan-card__back" aria-hidden="true"><i class="ph ph-cards"></i></div>';
      }
      if (card?.front_asset_id) {
        return `<img src="${assetUrl(card.front_asset_id)}" alt="${esc(card.name || label("cardLabelCardName", "Card"))}" draggable="false">`;
      }
      return '<i class="ph ph-cardholder" aria-hidden="true"></i>';
    }

    renderScene(state) {
      const host = this.root.querySelector("[data-card-scene]");
      if (!host) return;
      const placements = state.scene_placements || [];
      if (!placements.length) {
        host.innerHTML = `<div class="cards-empty">${esc(label("cardLabelEmptyScene", "No scene cards."))}</div>`;
        return;
      }
      host.innerHTML = placements.map((placement) => {
        const card = (state.cards || []).find((item) => item.id === placement.card_instance_id) || {};
        return `<article class="cards-row">
          <div><strong>${esc(card.name || label("cardLabelHiddenCard", "Hidden card"))}</strong><small>${esc(placement.face_state)} - ${Math.round(placement.x)}, ${Math.round(placement.y)}</small></div>
          <div class="cards-actions">
            <button type="button" data-card-action="flip" data-placement-id="${esc(placement.id)}" data-face-state="${esc(placement.face_state)}" title="${esc(label("cardLabelFlip", "Flip"))}"><i class="ph ph-arrows-clockwise"></i></button>
            <button type="button" data-card-action="discard-placement" data-placement-id="${esc(placement.id)}" title="${esc(label("cardLabelDiscard", "Discard"))}"><i class="ph ph-trash"></i></button>
          </div>
        </article>`;
      }).join("");
    }

  }

  function init() {
    startTableFollow();
    bindGlobalTableHandlers();
    document.querySelectorAll("[data-card-panel]").forEach((root) => {
      if (root.dataset.cardPanelReady === "true") return;
      root.dataset.cardPanelReady = "true";
      new CardPanel(root);
    });
    document.addEventListener("vtt:transport-event", (event) => {
      if (event.detail?.event !== "cards.state.updated") return;
      document.querySelectorAll("[data-card-panel]").forEach((root) => {
        if (root.dataset.roomId === event.detail?.payload?.room_id) root.__cardPanel?.refresh();
      });
    });
  }

  // Drop a hand card onto the table: placed through the cards' own scene-placement
  // layer (this domain), converting screen coordinates into scene coordinates.
  Cards.placeCardAtScene = async function placeCardAtScene(canvas, payload, clientX, clientY) {
    if (!canvas || !payload?.card_id) return false;
    const sceneId = canvas.dataset.sceneId || "";
    const roomId = canvas.dataset.roomId || payload.roomId || "";
    if (!sceneId || !roomId) return false;
    const mapState = window.GravewrightMap?.stateFor ? window.GravewrightMap.stateFor(canvas) : null;
    const layer = canvas.closest("[data-map-viewport]")?.querySelector("[data-card-scene-layer]") || canvas;
    const rect = layer.getBoundingClientRect();
    const zoom = Number(mapState?.zoom || 1) || 1;
    const offsetX = Number(mapState?.offsetX || 0);
    const offsetY = Number(mapState?.offsetY || 0);
    const x = (clientX - rect.left - offsetX) / zoom;
    const y = (clientY - rect.top - offsetY) / zoom;
    try {
      await Cards.api.playCardToScene(roomId, {
        card_id: payload.card_id,
        scene_id: sceneId,
        x: Math.round(x),
        y: Math.round(y),
        reveal: payload.reveal !== false,
      });
      const panel = document.querySelector(`[data-card-panel][data-room-id="${CSS.escape(roomId)}"]`);
      panel?.__cardPanel?.refresh();
      return true;
    } catch {
      return false;
    }
  };

  // Marquee select hook for the board's right-to-left drag (map-marquee.js).
  Cards.selectInRect = function selectInRect(canvas, rect, opts) {
    const layer = canvas?.closest("[data-map-viewport]")?.querySelector("[data-card-scene-layer]");
    layer?.__cardTable?.selectInRect(rect, opts || {});
  };

  Cards.CardPanel = CardPanel;
  document.addEventListener("DOMContentLoaded", init);
})();
