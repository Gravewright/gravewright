(function () {
  const Assets = (window.GravewrightAssets = window.GravewrightAssets || {});

  const ASSET_DROP_MIME = "application/x-gravewright-asset+json";
  const IMAGE_MIME_PREFIX = "image/";

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
      const error = new Error(data.error_key || "game.assets.errors.request_failed");
      error.payload = data;
      throw error;
    }
    return data;
  }

  const api = {
    async fetchLibrary(roomId) {
      const response = await fetch(`/game/assets/state/${encodeURIComponent(roomId)}`, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error_key || "game.assets.errors.request_failed");
      return data;
    },
    createFolder(roomId, payload) {
      return jsonRequest("/game/assets/folders", { ...(payload || {}), campaign_id: roomId });
    },
    moveAsset(roomId, payload) {
      return jsonRequest("/game/assets/move", { ...(payload || {}), campaign_id: roomId });
    },
    deleteAsset(roomId, assetId) {
      return jsonRequest("/game/assets/delete", { campaign_id: roomId, asset_id: assetId });
    },
    async upload(roomId, file, folderId) {
      const form = new FormData();
      form.append("campaign_id", roomId);
      if (folderId) form.append("folder_id", folderId);
      form.append("file", file);
      const response = await fetch("/game/assets/upload", {
        method: "POST",
        headers: { Accept: "application/json", "x-csrftoken": csrf() },
        body: form,
        credentials: "same-origin",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error_key || "game.assets.errors.request_failed");
      return data;
    },
  };
  Assets.api = api;

  const controllers = new Map();

  function assetName(asset) {
    const tail = asset.filename || String(asset.src || "").split("/").pop() || asset.id || "asset";
    return tail.length > 18 ? `${tail.slice(0, 18)}...` : tail;
  }

  class AssetLibrary {
    constructor(workspace) {
      this.workspace = workspace;
      this.roomId = workspace.dataset.roomId || "";
      this.panel = workspace.querySelector("[data-scene-assets-panel]");
      this.assets = [];
      this.folders = [];
      this.selectedFolderId = "";
      controllers.set(this.roomId, this);
      this.refresh();
    }

    async refresh() {
      if (!this.roomId) return;
      try {
        const state = await api.fetchLibrary(this.roomId);
        this.assets = Array.isArray(state.assets) ? state.assets : [];
        this.folders = Array.isArray(state.folders) ? state.folders : [];
        if (this.selectedFolderId && !this.folders.some((folder) => folder.id === this.selectedFolderId)) {
          this.selectedFolderId = "";
        }
        this.render();
      } catch {
        /* keep last known state */
      }
    }

    render() {
      if (!this.panel) return;
      const folders = this.folders || [];
      const assets = (this.assets || []).filter((asset) => (asset.folder_id || "") === this.selectedFolderId);
      const foldersHtml = `<div class="asset-folder-bar">
        <button type="button" data-asset-folder="" class="${this.selectedFolderId ? "" : "is-active"}"><i class="ph ph-folder-open" aria-hidden="true"></i><span>${esc(label("assetLabelRoot", "Root"))}</span></button>
        ${folders.map((folder) => `<button type="button" data-asset-folder="${esc(folder.id)}" class="${this.selectedFolderId === folder.id ? "is-active" : ""}"><i class="ph ph-folder" aria-hidden="true"></i><span>${esc(folder.name)}</span></button>`).join("")}
      </div>`;
      const assetsHtml = assets.length ? assets.map((asset) => {
        const id = esc(asset.id);
        return `<article class="asset-row" draggable="true" data-library-asset-id="${id}" data-library-asset-src="${esc(asset.src || "")}" data-library-asset-name="${esc(asset.filename || label("assetLabelImage", "Image"))}" title="${esc(label("assetLabelDragTitle", "Drag to the scene or to a folder"))}">
          <img src="${esc(asset.src || "")}" alt="">
          <div class="asset-row__meta">
            <strong>${esc(assetName(asset))}</strong>
            <small>${Number(asset.width || 0)} x ${Number(asset.height || 0)}</small>
          </div>
          <div class="asset-row__actions">
            <button type="button" class="asset-row__delete" data-asset-delete="${id}" title="${esc(label("assetLabelDeleteImage", "Delete image"))}" aria-label="${esc(label("assetLabelDeleteImage", "Delete image"))}"><i class="ph ph-trash" aria-hidden="true"></i></button>
          </div>
        </article>`;
      }).join("") : `<div class="cards-empty">${esc(label("assetLabelEmptyFolder", "No images in this folder."))}</div>`;
      this.panel.innerHTML = foldersHtml + assetsHtml;
    }

    async createFolder(name) {
      if (!name) return;
      await api.createFolder(this.roomId, { name });
      await this.refresh();
    }

    async moveAsset(assetId, folderId) {
      await api.moveAsset(this.roomId, { asset_id: assetId, folder_id: folderId || null });
      await this.refresh();
    }

    async deleteAsset(assetId) {
      if (!assetId) return;
      this.assets = this.assets.filter((asset) => asset.id !== assetId);
      this.render();
      await api.deleteAsset(this.roomId, assetId).catch(() => this.refresh());
    }

    async uploadFiles(files) {
      const images = Array.from(files || []).filter((file) => file.type.startsWith(IMAGE_MIME_PREFIX));
      if (!images.length) return false;
      for (const file of images) {
        await api.upload(this.roomId, file, this.selectedFolderId).catch(() => {});
      }
      await this.refresh();
      return true;
    }
  }

  function controllerFromElement(element) {
    const host = element.closest("[data-scene-assets-workspace], [data-scene-assets-panel]");
    return host ? controllers.get(host.dataset.roomId || "") || null : null;
  }

  document.addEventListener("click", (event) => {
    const deleteButton = event.target.closest("[data-asset-delete]");
    if (deleteButton) {
      const controller = controllerFromElement(deleteButton);
      if (controller) controller.deleteAsset(deleteButton.dataset.assetDelete);
      return;
    }

    const folderButton = event.target.closest("[data-asset-folder]");
    if (folderButton) {
      const controller = controllerFromElement(folderButton);
      if (!controller) return;
      controller.selectedFolderId = folderButton.dataset.assetFolder || "";
      controller.render();
      return;
    }

    const createFolderButton = event.target.closest("[data-scene-asset-create-folder]");
    if (createFolderButton) {
      const workspace = createFolderButton.closest("[data-scene-assets-workspace]");
      const controller = workspace ? controllers.get(workspace.dataset.roomId || "") : null;
      const input = workspace?.querySelector("[data-scene-asset-folder-name]");
      const name = input?.value?.trim();
      if (!controller || !name) return;
      controller.createFolder(name).then(() => {
        input.value = "";
      });
      return;
    }

    const uploadButton = event.target.closest("[data-scene-asset-upload]");
    if (uploadButton) {
      const workspace = uploadButton.closest("[data-scene-assets-workspace]");
      const input = workspace?.querySelector("[data-scene-asset-upload-input]");
      input?.click();
    }
  });

  document.addEventListener("change", (event) => {
    const input = event.target.closest("[data-scene-asset-upload-input]");
    if (!input) return;
    const workspace = input.closest("[data-scene-assets-workspace]");
    const controller = workspace ? controllers.get(workspace.dataset.roomId || "") : null;
    if (!controller) return;
    controller.uploadFiles(input.files).finally(() => {
      input.value = "";
    });
  });

  // Drag source: library asset rows can be dropped onto the scene image layer
  // (handled by the map controller) or onto a folder button to re-file them.
  document.addEventListener("dragstart", (event) => {
    const row = event.target.closest("[data-library-asset-id]");
    if (!row || !event.dataTransfer) return;
    event.dataTransfer.setData(ASSET_DROP_MIME, JSON.stringify({
      asset_id: row.dataset.libraryAssetId,
      src: row.dataset.libraryAssetSrc || "",
      name: row.dataset.libraryAssetName || label("assetLabelImage", "Image"),
    }));
    event.dataTransfer.effectAllowed = "copyMove";
    row.classList.add("is-dragging");
  });

  document.addEventListener("dragend", (event) => {
    event.target.closest("[data-library-asset-id]")?.classList.remove("is-dragging");
  });

  // Drag target: folder buttons accept a dropped asset to move it into the folder.
  document.addEventListener("dragover", (event) => {
    const folderButton = event.target.closest("[data-asset-folder]");
    if (!folderButton) return;
    const types = Array.from(event.dataTransfer?.types || []);
    if (!types.includes(ASSET_DROP_MIME)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    folderButton.classList.add("is-drop-target");
  });

  document.addEventListener("dragleave", (event) => {
    event.target.closest("[data-asset-folder]")?.classList.remove("is-drop-target");
  });

  document.addEventListener("drop", (event) => {
    const folderButton = event.target.closest("[data-asset-folder]");
    if (!folderButton) return;
    const raw = event.dataTransfer?.getData(ASSET_DROP_MIME);
    if (!raw) return;
    event.preventDefault();
    folderButton.classList.remove("is-drop-target");
    const controller = controllerFromElement(folderButton);
    if (!controller) return;
    try {
      const payload = JSON.parse(raw);
      if (payload.asset_id) controller.moveAsset(payload.asset_id, folderButton.dataset.assetFolder || null);
    } catch {
      /* ignore malformed payload */
    }
  });

  function init() {
    document.querySelectorAll("[data-scene-assets-workspace]").forEach((workspace) => {
      if (workspace.dataset.assetLibraryReady === "true") return;
      workspace.dataset.assetLibraryReady = "true";
      new AssetLibrary(workspace);
    });
    document.addEventListener("vtt:transport-event", (event) => {
      if (event.detail?.event !== "assets.library.updated") return;
      controllers.get(event.detail?.payload?.room_id)?.refresh();
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
