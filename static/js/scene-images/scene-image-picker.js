/* Camada artística: as imagens que o GM enviou, prontas para arrastar ao mapa. */
(function () {
  "use strict";

  const MODAL_PREFIX = "scene-image-picker-";

  function label(name, fallback) {
    return document.body?.dataset?.[name] || fallback;
  }

  function esc(value) {
    const node = document.createElement("span");
    node.textContent = String(value ?? "");
    return node.innerHTML;
  }

  function activeRoomId() {
    return document.querySelector(".room-workspace.is-active [data-map-canvas]")?.dataset.roomId
      || document.querySelector("[data-map-canvas]")?.dataset.roomId
      || "";
  }

  async function fetchImages(roomId) {
    const response = await fetch(`/game/assets/state/${encodeURIComponent(roomId)}`, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error_key || "game.assets.errors.request_failed");
    return (data.assets || []).filter((asset) => (asset.kind || "image") === "image");
  }

  const pickers = new Map();

  class SceneImagePicker {
    constructor(roomId) {
      this.roomId = roomId;
      this.modalId = MODAL_PREFIX + roomId;
      this.images = [];
      this.term = "";
      this.build();
    }

    build() {
      const layer = document.querySelector(".game-modal-layer");
      if (!layer) return;
      const modal = document.createElement("article");
      modal.className = "game-modal-window dialog-modal scene-image-picker";
      modal.dataset.modalWindow = "";
      modal.dataset.modalId = this.modalId;
      modal.dataset.windowKey = this.modalId;
      modal.innerHTML = `
        <header class="game-modal-titlebar" data-modal-drag-handle>
          <span class="game-modal-drag-grip"></span>
          <span class="game-panel-title"><i class="ph ph-images" aria-hidden="true"></i> ${esc(label("sceneImageLabelTitle", "Map images"))}</span>
          <div class="game-modal-controls">
            <button class="game-modal-control" type="button" data-modal-minimize aria-label="${esc(label("sceneImageLabelMinimize", "Minimize"))}"><i class="ph ph-minus" aria-hidden="true"></i></button>
            <button class="game-modal-control" type="button" data-modal-close aria-label="${esc(label("sceneImageLabelClose", "Close"))}"><i class="ph ph-x" aria-hidden="true"></i></button>
          </div>
        </header>
        <div class="game-modal-body scene-image-picker-body">
          <label class="scene-image-picker-search">
            <i class="ph ph-magnifying-glass" aria-hidden="true"></i>
            <input type="search" data-scene-image-search autocomplete="off"
                   placeholder="${esc(label("sceneImageLabelSearch", "Search images"))}"
                   aria-label="${esc(label("sceneImageLabelSearch", "Search images"))}">
          </label>
          <p class="scene-image-picker-hint">${esc(label("sceneImageLabelHint", "Drag an image onto the map to place it."))}</p>
          <div class="asset-grid" data-scene-image-grid></div>
        </div>`;
      layer.append(modal);
      this.modal = modal;
      this.grid = modal.querySelector("[data-scene-image-grid]");
      const search = modal.querySelector("[data-scene-image-search]");
      search.addEventListener("input", () => {
        this.term = search.value.trim().toLocaleLowerCase();
        this.render();
      });
    }

    render() {
      if (!this.grid) return;
      const term = this.term;
      const visible = term
        ? this.images.filter((image) => String(image.filename || "").toLocaleLowerCase().includes(term))
        : this.images;
      if (!visible.length) {
        const message = this.images.length
          ? label("sceneImageLabelNoMatch", "No image matches this search.")
          : label("sceneImageLabelEmpty", "No image has been uploaded to this campaign yet.");
        this.grid.innerHTML = `<p class="asset-empty">${esc(message)}</p>`;
        return;
      }
      // Os mesmos data-attributes da biblioteca: o dragstart do core já monta o
      // payload que o mapa aceita, então a grade não duplica esse contrato.
      this.grid.innerHTML = visible.map((image) => {
        const name = image.filename || label("assetLabelImage", "Image");
        const size = `${Number(image.width || 0)} × ${Number(image.height || 0)}`;
        return `<article class="asset-card" draggable="true"
          data-library-asset-id="${esc(image.id)}"
          data-library-asset-kind="image"
          data-library-asset-src="${esc(image.src || "")}"
          data-library-asset-name="${esc(name)}"
          title="${esc(name)}">
          <div class="asset-card__thumb"><img class="asset-card__img" src="${esc(image.src || "")}" alt="" loading="lazy" draggable="false"></div>
          <div class="asset-card__meta"><strong>${esc(name)}</strong><small>${esc(size)}</small></div>
        </article>`;
      }).join("");
    }

    async refresh() {
      if (!this.modal) return;
      try {
        this.images = await fetchImages(this.roomId);
      } catch {
        this.images = [];
      }
      this.render();
    }
  }

  function pickerFor(roomId) {
    if (!roomId) return null;
    let picker = pickers.get(roomId);
    if (picker && !picker.modal?.isConnected) {
      pickers.delete(roomId);
      picker = null;
    }
    if (!picker) {
      picker = new SceneImagePicker(roomId);
      if (!picker.modal) return null;
      pickers.set(roomId, picker);
    }
    return picker;
  }

  document.addEventListener("artistic:image-picker", async (event) => {
    const roomId = event.detail?.roomId || activeRoomId();
    const picker = pickerFor(roomId);
    if (!picker) return;
    await picker.refresh();
    window.GravewrightModals?.open?.(picker.modalId);
  });

  // A grade espelha a biblioteca, então acompanha as mesmas mudanças autoritativas.
  document.addEventListener("vtt:transport-event", (event) => {
    if (event.detail?.event !== "assets.library.updated") return;
    pickers.get(event.detail?.payload?.room_id)?.refresh();
  });
  document.addEventListener("vtt:ws-open", () => {
    pickers.forEach((picker) => picker.refresh());
  });
})();
