(function () {
  const Assets = (window.GravewrightAssets = window.GravewrightAssets || {});

  const ASSET_DROP_MIME = "application/x-gravewright-asset+json";
  const IMAGE_MIME_PREFIX = "image/";

  const PDF_MIME = "application/pdf";

  const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
  const MAX_PDF_BYTES = 25 * 1024 * 1024;

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



      if (!response.ok) throw new Error(data.error_key || String(response.status));
      return data;
    },
  };
  Assets.api = api;

  const controllers = new Map();

  async function getJson(url) {
    const response = await fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error_key || "game.assets.errors.request_failed");
    return data;
  }

  function node(tag, cls, text) {
    const element = document.createElement(tag);
    if (cls) element.className = cls;
    if (text != null) element.textContent = String(text);
    return element;
  }

  async function openAssetPackageBrowser(controller) {
    const dialog = node("dialog", "content-package-modal asset-package-modal");
    const shell = node("section", "content-package-modal-shell");
    const header = node("header", "content-package-modal-header");
    const close = node("button", "content-package-modal-close", "×");
    close.type = "button";
    header.append(close, node("h3", "content-package-modal-title", label("assetLabelImportPackage", "Import asset package")));
    const status = node("p", "content-package-import-status");
    const body = node("div", "content-package-modal-body");
    shell.append(header, status, body);
    dialog.append(shell);
    document.body.append(dialog);
    close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener("close", () => dialog.remove());
    dialog.showModal();

    const packageState = await getJson(`/game/assets/packages/${encodeURIComponent(controller.roomId)}`).catch(() => null);
    const packages = packageState?.packages || [];
    if (!packages.length) {
      body.append(node("p", "content-empty", label("assetLabelNoPackages", "No active asset packages.")));
      return;
    }
    for (const packageInfo of packages) {
      const details = node("details", "content-pack");
      const summary = node("summary", "content-pack-summary", packageInfo.name || packageInfo.id);
      details.append(summary);
      const packageActions = node("div", "content-package-modal-actions");
      const importAll = node("button", "content-import-all", label("assetLabelImportAll", "Import all"));
      importAll.type = "button";
      packageActions.append(importAll);
      details.append(packageActions);
      const list = node("ul", "content-entry-list");
      details.append(list);
      let loaded = false;
      let rendered = false;
      let entries = [];
      async function loadEntries() {
        if (loaded) return entries;
        loaded = true;
        const state = await getJson(
          `/game/assets/packages/${encodeURIComponent(controller.roomId)}/${encodeURIComponent(packageInfo.id)}`
        ).catch(() => null);
        entries = state?.assets || [];
        return entries;
      }
      importAll.addEventListener("click", async () => {
        importAll.disabled = true;
        const available = await loadEntries();
        const result = await jsonRequest("/game/assets/packages/import", {
          campaign_id: controller.roomId,
          package_id: packageInfo.id,
          asset_ids: available.map((entry) => entry.id),
          folder_id: controller.selectedFolderId || null,
        }).catch(() => null);
        importAll.disabled = false;
        if (!result) return;
        status.textContent = label("assetLabelImportedCount", "{count} assets imported.")
          .replace("{count}", String(result.imported || 0));
        await controller.refresh();
      });
      details.addEventListener("toggle", async () => {
        if (!details.open || rendered) return;
        rendered = true;
        const available = await loadEntries();
        available.forEach((entry) => {
          const row = node("li", "content-entry asset-package-entry");
          if (entry.category !== "audio") {
            const preview = document.createElement("img");
            preview.className = "asset-package-entry__preview";
            preview.src = entry.src;
            preview.alt = "";
            preview.loading = "lazy";
            row.append(preview);
          }
          row.append(node("span", "content-entry-name", entry.label || entry.id));
          const button = node("button", "content-import-btn", "+");
          button.type = "button";
          button.title = label("assetLabelImportOne", "Import");
          button.addEventListener("click", async () => {
            button.disabled = true;
            const result = await jsonRequest("/game/assets/packages/import", {
              campaign_id: controller.roomId,
              package_id: packageInfo.id,
              asset_id: entry.id,
              folder_id: controller.selectedFolderId || null,
            }).catch(() => null);
            button.disabled = false;
            if (!result?.imported) return;
            button.textContent = "✓";
            status.textContent = label("assetLabelImported", "Asset imported.");
            await controller.refresh();
          });
          row.append(button);
          list.append(row);
        });
        if (!available.length) list.append(node("li", "content-entry-empty", "-"));
      });
      body.append(details);
    }
  }

  function assetName(asset) {
    const tail = asset.filename || String(asset.src || "").split("/").pop() || asset.id || "asset";
    return tail.length > 18 ? `${tail.slice(0, 18)}...` : tail;
  }



  function uploadErrorLabel(error) {
    const key = String(error?.message || "");
    if (key.includes("too_large") || key === "413") {
      return label("assetLabelTooLarge", "File is too large.");
    }
    if (key.includes("unsupported_type") || key.includes("invalid_image")) {
      return label("assetLabelUnsupported", "Unsupported file.");
    }
    return label("assetLabelUploadFailed", "Could not upload the file.");
  }

  function reportUploadFailure(file, error) {
    const message = `${file?.name || "?"}: ${uploadErrorLabel(error)}`;
    if (window.GravewrightToasts?.showToast) {
      window.GravewrightToasts.showToast(message, { type: "error" });
    } else {
      console.error("[assets]", message, error);
    }
  }



  function formatBytes(bytes) {
    const size = Number(bytes) || 0;
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  class AssetLibrary {
    constructor(workspace) {
      this.workspace = workspace;
      this.roomId = workspace.dataset.roomId || "";
      this.panel = workspace.querySelector("[data-scene-assets-panel]");
      this.assets = [];
      this.folders = [];
      this.selectedFolderId = "";
      this.kind = "";
      this.search = "";
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

      }
    }




    visibleAssets() {
      const termo = (this.search || "").trim().toLowerCase();
      return (this.assets || []).filter((asset) => {
        if ((asset.folder_id || "") !== this.selectedFolderId) return false;
        if (this.kind && (asset.kind || "image") !== this.kind) return false;
        if (!termo) return true;
        return String(asset.filename || "").toLowerCase().includes(termo);
      });
    }

    renderFolders() {
      const rail = this.workspace.querySelector("[data-scene-asset-folder-list]");
      if (!rail) return;
      const contar = (id) => (this.assets || []).filter((a) => (a.folder_id || "") === id).length;

      const item = (id, nome, icone) => `
        <button type="button" class="asset-folder ${this.selectedFolderId === id ? "is-active" : ""}"
                data-asset-folder="${esc(id)}">
          <i class="ph ${icone}" aria-hidden="true"></i>
          <span class="asset-folder__name">${esc(nome)}</span>
          <span class="asset-folder__count">${contar(id)}</span>
        </button>`;

      rail.innerHTML =
        item("", label("assetLabelRoot", "Root"), "ph-folder-open") +
        (this.folders || []).map((f) => item(f.id, f.name, "ph-folder")).join("");
    }

    renderGrid() {
      const assets = this.visibleAssets();
      const podeApresentar = this.workspace.dataset.isCampaignGm === "true";

      this.panel.innerHTML = assets.length
        ? assets.map((asset) => {
            const id = esc(asset.id);
            const kind = asset.kind || "image";


            const isPdf = kind === "pdf";
            const preview = isPdf
              ? `<span class="asset-card__icon" aria-hidden="true"><i class="ph ph-file-pdf"></i></span>`
              : `<img class="asset-card__img" src="${esc(asset.src || "")}" alt="" loading="lazy">`;
            const detail = isPdf
              ? esc(formatBytes(asset.byte_size))
              : `${Number(asset.width || 0)} × ${Number(asset.height || 0)}`;

            return `<article class="asset-card" draggable="true"
              data-library-asset-id="${id}"
              data-library-asset-kind="${esc(kind)}"
              data-library-asset-src="${esc(asset.src || "")}"
              data-library-asset-name="${esc(asset.filename || label("assetLabelImage", "Image"))}"
              title="${esc(asset.filename || "")}">
              <div class="asset-card__thumb">${preview}</div>
              <div class="asset-card__meta">
                <strong>${esc(assetName(asset))}</strong>
                <small>${detail}</small>
              </div>
              <div class="asset-card__actions">
                ${podeApresentar ? `<button type="button" data-handout-resource="asset" data-resource-id="${id}" data-campaign-id="${esc(this.roomId)}" title="${esc(label("assetLabelShow", "Show to players"))}" aria-label="${esc(label("assetLabelShow", "Show to players"))}"><i class="ph ph-hand-pointing" aria-hidden="true"></i></button>` : ""}
                <button type="button" class="asset-card__delete" data-asset-delete="${id}"
                        title="${esc(label("assetLabelDeleteImage", "Delete"))}"
                        aria-label="${esc(label("assetLabelDeleteImage", "Delete"))}"><i class="ph ph-trash" aria-hidden="true"></i></button>
              </div>
            </article>`;
          }).join("")
        : `<p class="asset-empty">${esc(this.emptyMessage())}</p>`;
    }



    emptyMessage() {
      if ((this.search || "").trim()) return label("assetLabelNoMatch", "Nothing matches your search.");
      if (this.kind) return label("assetLabelNoKind", "Nothing of this type in this folder.");
      return label("assetLabelEmptyFolder", "This folder is empty.");
    }

    renderSummary() {
      const rodape = this.workspace.querySelector("[data-asset-summary]");
      if (!rodape) return;
      const visiveis = this.visibleAssets();
      const total = (this.assets || []).length;
      const bytes = visiveis.reduce((soma, a) => soma + (Number(a.byte_size) || 0), 0);
      rodape.textContent = `${visiveis.length}/${total} · ${formatBytes(bytes)}`;
    }

    render() {
      if (!this.panel) return;
      this.renderFolders();
      this.renderGrid();
      this.renderSummary();
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
      const accepted = Array.from(files || []).filter(
        (file) => file.type.startsWith(IMAGE_MIME_PREFIX) || file.type === PDF_MIME,
      );
      if (!accepted.length) return false;
      for (const file of accepted) {



        const cap = file.type === PDF_MIME ? MAX_PDF_BYTES : MAX_IMAGE_BYTES;
        if (file.size > cap) {
          reportUploadFailure(file, new Error("too_large"));
          continue;
        }



        await api.upload(this.roomId, file, this.selectedFolderId).catch((error) => {
          reportUploadFailure(file, error);
        });
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



      const kind = uploadButton.dataset.sceneAssetUpload || "image";
      const input = workspace?.querySelector(`[data-scene-asset-upload-input="${kind}"]`);
      input?.click();
      return;
    }

    const packageButton = event.target.closest("[data-asset-package-open]");
    if (packageButton) {
      const workspace = packageButton.closest("[data-scene-assets-workspace]");
      const controller = workspace ? controllers.get(workspace.dataset.roomId || "") : null;
      if (controller) void openAssetPackageBrowser(controller);
    }
  });

  document.addEventListener("input", (event) => {
    const campo = event.target.closest("[data-asset-search]");
    if (!campo) return;
    const controller = controllerFromElement(campo);
    if (!controller) return;


    controller.search = campo.value;
    controller.renderGrid();
    controller.renderSummary();
  });

  document.addEventListener("click", (event) => {
    const botao = event.target.closest("[data-asset-kind]");
    if (!botao) return;
    const controller = controllerFromElement(botao);
    if (!controller) return;
    controller.kind = botao.dataset.assetKind || "";
    botao.parentElement?.querySelectorAll("[data-asset-kind]").forEach((outro) => {
      const ativo = outro === botao;
      outro.classList.toggle("is-active", ativo);
      outro.setAttribute("aria-pressed", String(ativo));
    });
    controller.renderGrid();
    controller.renderSummary();
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



  document.addEventListener("dragstart", (event) => {
    const row = event.target.closest("[data-library-asset-id]");
    if (!row || !event.dataTransfer) return;
    event.dataTransfer.setData(ASSET_DROP_MIME, JSON.stringify({
      asset_id: row.dataset.libraryAssetId,
      src: row.dataset.libraryAssetSrc || "",
      name: row.dataset.libraryAssetName || label("assetLabelImage", "Image"),


      kind: row.dataset.libraryAssetKind || "image",
    }));
    event.dataTransfer.effectAllowed = "copyMove";
    row.classList.add("is-dragging");
  });

  document.addEventListener("dragend", (event) => {
    event.target.closest("[data-library-asset-id]")?.classList.remove("is-dragging");
  });


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

    }
  });

  function init() {
    document.querySelectorAll("[data-scene-assets-workspace]").forEach((workspace) => {
      if (workspace.dataset.assetLibraryReady === "true") return;
      workspace.dataset.assetLibraryReady = "true";
      new AssetLibrary(workspace);
    });
    document.addEventListener("vtt:transport-event", (event) => {
      if (!["assets.library.updated", "handout.access_changed"].includes(event.detail?.event)) return;
      controllers.get(event.detail?.payload?.room_id)?.refresh();
    });
    document.addEventListener("vtt:ws-open", () => {
      controllers.forEach((controller) => controller.refresh());
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
