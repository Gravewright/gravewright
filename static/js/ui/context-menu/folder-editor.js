(() => {
  const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
  let state = null;

  function pickerColor(value) {
    const color = String(value || "").trim();
    if (/^#[0-9a-f]{6}$/i.test(color)) return color;
    if (/^#[0-9a-f]{3}$/i.test(color)) {
      return `#${[...color.slice(1)].map((part) => part + part).join("")}`;
    }
    return "#b9995d";
  }

  function ensureModal() {
    let modal = document.querySelector('[data-modal-id="folder-edit"]');
    if (modal) return modal;

    modal = document.createElement("article");
    modal.className = "game-modal-window dialog-modal";
    modal.dataset.modalWindow = "";
    modal.dataset.modalId = "folder-edit";
    modal.dataset.windowKey = "folder-edit";
    modal.hidden = true;
    modal.innerHTML = `
      <header class="game-modal-titlebar" data-modal-drag-handle>
        <span class="game-modal-drag-grip" aria-hidden="true"></span>
        <div class="game-modal-sheet-title"><span class="sheet-modal-name"></span></div>
        <div class="game-modal-controls">
          <button class="game-modal-control" type="button" data-modal-close aria-label="Close">
            <i class="ph ph-x" aria-hidden="true"></i>
          </button>
        </div>
      </header>
      <form class="dialog-form" data-folder-edit-form>
        <label class="dialog-field">
          <span data-folder-edit-name-label></span>
          <input type="text" name="name" maxlength="60" required data-modal-autofocus>
        </label>
        <label class="dialog-field">
          <span data-folder-edit-color-label></span>
          <span class="dialog-color-row">
            <input type="text" name="color" maxlength="9" placeholder="#b9995d" data-folder-edit-color-text>
            <input type="color" data-folder-edit-color-pick>
          </span>
        </label>
        <button type="submit" class="dialog-submit">
          <i class="ph ph-check" aria-hidden="true"></i><span data-folder-edit-save-label></span>
        </button>
      </form>`;
    (document.querySelector(".game-modal-layer") || document.body).appendChild(modal);

    const text = modal.querySelector("[data-folder-edit-color-text]");
    const picker = modal.querySelector("[data-folder-edit-color-pick]");
    picker.addEventListener("input", () => { text.value = picker.value; });
    text.addEventListener("input", () => {
      if (/^#[0-9a-f]{6}$/i.test(text.value)) picker.value = text.value;
    });
    modal.querySelector("[data-folder-edit-form]").addEventListener("submit", save);
    return modal;
  }

  async function save(event) {
    event.preventDefault();
    if (!state) return;
    const form = event.currentTarget;
    const name = form.elements.name.value.trim();
    const color = form.elements.color.value.trim();
    if (!name) return;

    const internals = {
      actor: window.GravewrightActorsInternals,
      item: window.GravewrightItemsInternals,
      scene: window.GravewrightScenesInternals,
      journal: window.GravewrightJournalsInternals,
    }[state.kind] || window.GravewrightJournalsInternals;
    const basePath = state.kind === "journal"
      ? "/game/journal/folder"
      : `/game/${state.kind}-folder`;
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      if (name !== state.name) {
        const renamed = await (internals.postForm || internals.postJournal)(`${basePath}/rename`, {
          folder_id: state.folderId, campaign_id: state.campaignId, name,
        });
        if (!renamed.ok) return;
        state.name = name;
      }
      if (color !== state.color) {
        const recolored = await (internals.postForm || internals.postJournal)(`${basePath}/color`, {
          folder_id: state.folderId, campaign_id: state.campaignId, color,
        });
        if (!recolored.ok) return;
        state.color = color;
      }
      window.GravewrightModalInternals?.close(form.closest("[data-modal-window]"));
      await (internals.refreshPanel || internals.refreshJournalPanel)(state.campaignId);
    } finally {
      button.disabled = false;
    }
  }

  function openFolderEditor({ kind, folderId, campaignId, name = "", color = "" }) {
    state = { kind, folderId, campaignId, name, color };
    const modal = ensureModal();
    modal.querySelector(".sheet-modal-name").textContent = document.body.dataset.ctxFolderEdit || "Edit folder";
    modal.querySelector("[data-folder-edit-name-label]").textContent = document.body.dataset.ctxFolderName || "Name";
    modal.querySelector("[data-folder-edit-color-label]").textContent = document.body.dataset.ctxFolderColor || "Color";
    modal.querySelector("[data-folder-edit-save-label]").textContent = document.body.dataset.ctxFolderSave || "Save";
    modal.querySelector('[name="name"]').value = name;
    modal.querySelector('[name="color"]').value = color || "#b9995d";
    modal.querySelector("[data-folder-edit-color-pick]").value = pickerColor(color);
    openNearRight("folder-edit", kind, campaignId);
  }

  function openNearRight(modalId, kind, campaignId) {
    const modals = window.GravewrightModalInternals;
    modals?.open(modalId);
    const modal = document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`);
    if (!modal || modal.dataset.userPositionedFromContext === "true") return;
    window.requestAnimationFrame(() => {
      const panel = document.querySelector(
        `[data-${kind}-panel][data-room-id="${CSS.escape(campaignId)}"]`,
      );
      const panelRect = panel?.getBoundingClientRect();
      const layerRect = modal.closest(".game-modal-layer")?.getBoundingClientRect();
      if (!panelRect || !layerRect) return;
      const margin = 12;
      const x = Math.max(margin, panelRect.left - layerRect.left - modal.offsetWidth - margin);
      const y = Math.max(22, panelRect.top - layerRect.top + 10);
      modals?.setPosition(modal, x, y);
      modal.dataset.userPositionedFromContext = "true";
    });
  }

  function prepareCreateForm(kind, campaignId, parentId = "") {
    const modalId = `${kind}-folder-create-${campaignId}`;
    const modal = document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`);
    const form = modal?.querySelector(`[data-${kind}-folder-create-form]`);
    if (!form) return false;
    form.reset();
    const parent = form.querySelector('input[name="parent_id"]');
    if (parent) parent.value = parentId;
    const text = form.querySelector(`[data-${kind}-folder-color-text]`);
    const picker = form.querySelector(`[data-${kind}-folder-color-pick]`);
    if (text && picker) picker.value = pickerColor(text.value);
    return true;
  }

  function openFolderCreateModal({ kind, campaignId, parentId = "" }) {
    if (!prepareCreateForm(kind, campaignId, parentId)) return;
    openNearRight(`${kind}-folder-create-${campaignId}`, kind, campaignId);
  }

  function prepareActorCreateForm(campaignId, folderId = "") {
    const modalId = `actor-create-${campaignId}`;
    const modal = document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`);
    const form = modal?.querySelector("[data-actor-create-form]");
    if (!form) return false;
    form.reset();
    const folder = form.querySelector('input[name="folder_id"]');
    if (folder) folder.value = folderId;
    return true;
  }

  function openActorCreateModal({ campaignId, folderId = "" }) {
    if (!prepareActorCreateForm(campaignId, folderId)) return;
    openNearRight(`actor-create-${campaignId}`, "actor", campaignId);
  }

  function prepareItemCreateForm(campaignId, folderId = "") {
    const modalId = `item-create-${campaignId}`;
    const modal = document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`);
    const form = modal?.querySelector("[data-item-create-form]");
    if (!form) return false;
    form.reset();
    const folder = form.querySelector('input[name="folder_id"]');
    if (folder) folder.value = folderId;
    return true;
  }

  function openItemCreateModal({ campaignId, folderId = "" }) {
    if (!prepareItemCreateForm(campaignId, folderId)) return;
    openNearRight(`item-create-${campaignId}`, "item", campaignId);
  }

  document.addEventListener("click", (event) => {
    const opener = event.target.closest('[data-modal-open^="actor-folder-create-"], [data-modal-open^="item-folder-create-"], [data-modal-open^="journal-folder-create-"]');
    if (!opener) return;
    const kind = opener.dataset.modalOpen.startsWith("actor-")
      ? "actor"
      : opener.dataset.modalOpen.startsWith("item-") ? "item" : "journal";
    const campaignId = opener.dataset.modalOpen.slice(`${kind}-folder-create-`.length);
    prepareCreateForm(kind, campaignId, "");
  });

  // Abrir pelo botao do cabecalho cria na raiz: o form.reset() nao limpa um
  // hidden, entao a pasta escolhida no menu anterior ficaria grudada.
  document.addEventListener("click", (event) => {
    const opener = event.target.closest('[data-modal-open^="actor-create-"], [data-modal-open^="item-create-"]');
    if (!opener) return;
    const isActor = opener.dataset.modalOpen.startsWith("actor-create-");
    const prefix = isActor ? "actor-create-" : "item-create-";
    const campaignId = opener.dataset.modalOpen.slice(prefix.length);
    if (isActor) prepareActorCreateForm(campaignId, "");
    else prepareItemCreateForm(campaignId, "");
  });

  FI.openFolderEditor = openFolderEditor;
  FI.openFolderCreateModal = openFolderCreateModal;
  FI.openActorCreateModal = openActorCreateModal;
  FI.openItemCreateModal = openItemCreateModal;
})();
