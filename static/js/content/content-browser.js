(function () {
  const Api = window.GravewrightContentApi;
  const SOURCE_MIME = Api.SOURCE_MIME;
  const getJSON = Api.getJSON;
  const postJSON = Api.postJSON;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function renderEntry(browser, packageInfo, pack, entry) {
    const item = el("li", "content-entry");
    item.draggable = true;
    item.dataset.contentDrag = JSON.stringify({
      kind: "content_pack_entry",
      package_id: packageInfo.id,
      system_id: packageInfo.id,
      pack_id: pack.id,
      entry_id: entry.id,
      type: entry.type,
      pack_type: pack.type,
      document_type: entry.document_type || pack.document_type || "",
    });
    // A entrada abre a ficha de verdade, em leitura. Antes o compendio era uma
    // lista de nomes: dava para importar ou arrastar, mas nao para LER.
    const nome = el("button", "content-entry-name", entry.name || entry.id);
    nome.type = "button";
    nome.title = browser.dataset.readText || "Open";
    const hasSheetPreview = ["actor_pack", "item_pack", "spell_pack"].includes(pack.type);
    nome.addEventListener("click", (event) => {
      event.stopPropagation();
      if (!hasSheetPreview) return;
      document.dispatchEvent(new CustomEvent("vtt:open-compendium-entry", {
        detail: {
          campaignId: browser.dataset.roomId,
          packageId: packageInfo.id,
          packId: pack.id,
          entryId: entry.id,
        },
      }));
    });
    item.appendChild(nome);
    if (entry.type) item.appendChild(el("span", "content-entry-type", entry.type));

    const importKind =
      pack.type === "actor_pack" ? "actor"
      : pack.type === "item_pack" || pack.type === "spell_pack" ? "item"
      : pack.type === "deck_pack" || pack.type === "card_pack" ? "deck"
      : pack.type === "journal_pack" ? "journal"
      : pack.type === "scene_pack" ? "scene"
      : null;
    if (importKind) {
      const importBtn = el("button", "content-import-btn", "+");
      importBtn.type = "button";
      importBtn.title = browser.dataset.importOneText || "Import";
      importBtn.addEventListener("click", async (event) => {
        event.stopPropagation();
        importBtn.disabled = true;
        const url = importKind === "item" ? "/game/item/content/import" : "/game/content/import";
        const created = await postJSON(url, {
          campaign_id: browser.dataset.roomId,
          package_id: packageInfo.id,
          pack_id: pack.id,
          entry_id: entry.id,
        });
        importBtn.disabled = false;
        if (!created) return;
        importBtn.textContent = "✓";
        if (created.actor_id) {
          document.dispatchEvent(new CustomEvent("vtt:open-actor-sheet", { detail: { actorId: created.actor_id } }));
        } else if (created.item_id) {
          document.dispatchEvent(new CustomEvent("vtt:open-item-sheet", { detail: { itemId: created.item_id } }));
        } else if (created.deck_id) {
          document.querySelector(`[data-modal-open="panel-cards-${CSS.escape(browser.dataset.roomId)}"]`)?.click();
        } else if (created.journal_id) {
          document.dispatchEvent(new CustomEvent("vtt:open-journal", { detail: { journalId: created.journal_id } }));
        } else if (created.scene_id) {
          await window.GravewrightScenes?.refreshPanel?.(browser.dataset.roomId);
        }
      });
      item.appendChild(importBtn);
    }

    item.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData(SOURCE_MIME, item.dataset.contentDrag);
      event.dataTransfer.effectAllowed = "copy";
    });
    return item;
  }

  function accessSelect(browser, packageInfo, pack) {
    const wrap = el("label", "content-pack-access");
    wrap.appendChild(el("span", "content-pack-access-label", browser.dataset.accessLabel || "Players"));
    const select = document.createElement("select");
    [["none", browser.dataset.accessNone || "No access"],
     ["read", browser.dataset.accessRead || "Read"],
     ["owner", browser.dataset.accessOwner || "Read and import"]].forEach(([value, text]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      if (value === (pack.player_access || "none")) option.selected = true;
      select.appendChild(option);
    });
    // O clique no seletor nao pode abrir/fechar o <details> que o contem.
    select.addEventListener("click", (event) => event.stopPropagation());
    select.addEventListener("change", async () => {
      const previous = pack.player_access || "none";
      select.disabled = true;
      const saved = await postJSON("/game/content/pack-access", {
        campaign_id: browser.dataset.roomId,
        package_id: packageInfo.id,
        pack_id: pack.id,
        role: "player",
        level: select.value,
      });
      select.disabled = false;
      if (saved) pack.player_access = select.value;
      else select.value = previous;
    });
    wrap.appendChild(select);
    return wrap;
  }

  function renderPack(browser, packageInfo, pack, container, canGrant) {
    const details = el("details", "content-pack");
    const summary = el("summary", "content-pack-summary", pack.label || pack.id);
    if (canGrant) summary.appendChild(accessSelect(browser, packageInfo, pack));
    details.appendChild(summary);
    const list = el("ul", "content-entry-list");
    details.appendChild(list);
    let loaded = false;
    details.addEventListener("toggle", async () => {
      if (!details.open || loaded) return;
      loaded = true;
      const full = await getJSON(`/game/content/pack/${encodeURIComponent(packageInfo.id)}/${encodeURIComponent(pack.id)}?campaign_id=${encodeURIComponent(browser.dataset.roomId)}`);
      (full?.entries || []).forEach((entry) => list.appendChild(renderEntry(browser, packageInfo, pack, entry)));
      if (!full?.entries?.length) list.appendChild(el("li", "content-entry-empty", "-"));
    });
    container.appendChild(details);
  }

  async function openPackageModal(browser, packageInfo) {
    const modalId = `content-package-${browser.dataset.roomId}-${packageInfo.id}`;
    document.querySelector(`[data-modal-id="${CSS.escape(modalId)}"]`)?.remove();
    const dialog = el("article", "game-modal-window content-package-modal");
    dialog.dataset.modalWindow = "";
    dialog.dataset.modalId = modalId;
    dialog.dataset.windowKey = modalId;
    dialog.dataset.autoFitWidth = "620";
    dialog.hidden = true;
    const shell = el("section", "content-package-modal-shell game-panel-body");
    const header = el("header", "content-package-modal-header game-modal-titlebar");
    header.dataset.modalDragHandle = "";
    header.appendChild(el("span", "game-modal-drag-grip"));
    const actions = el("div", "content-package-modal-actions");
    const importAll = el("button", "content-import-all", browser.dataset.importAllText || "Import all");
    importAll.type = "button";
    const close = el("button", "content-package-modal-close", "×");
    close.type = "button";
    close.classList.add("game-modal-control");
    close.dataset.modalClose = "";
    close.setAttribute("aria-label", browser.dataset.closeText || "Close");
    actions.append(importAll, close);
    header.append(actions, el("h3", "content-package-modal-title", packageInfo.name || packageInfo.id));
    const status = el("p", "content-package-import-status");
    const body = el("div", "content-package-modal-body");
    shell.append(header, status, body);
    dialog.appendChild(shell);
    (document.querySelector(".game-modal-layer") || document.body).appendChild(dialog);

    close.addEventListener("click", () => setTimeout(() => dialog.remove(), 250));
    importAll.addEventListener("click", async () => {
      importAll.disabled = true;
      status.textContent = browser.dataset.importingText || "Importing…";
      const result = await postJSON("/game/content/package/import", {
        campaign_id: browser.dataset.roomId,
        package_id: packageInfo.id,
      });
      importAll.disabled = false;
      status.textContent = result
        ? (browser.dataset.importedText || "{count} imported.").replace("{count}", String(result.imported || 0))
        : (browser.dataset.importFailedText || "Import failed.");
    });

    window.GravewrightModals?.open(modalId);
    const packs = await getJSON(`/game/content/packs/${encodeURIComponent(packageInfo.id)}?campaign_id=${encodeURIComponent(browser.dataset.roomId)}`);
    if (!packs?.packs?.length) {
      body.appendChild(el("p", "content-empty", browser.dataset.packEmptyText || "No content."));
      return;
    }
    packs.packs.forEach((pack) => renderPack(browser, packageInfo, pack, body, packs.can_grant === true));
  }

  async function renderBrowser(browser) {
    if (browser.dataset.loaded) return;
    browser.dataset.loaded = "1";
    let packages = [];
    const active = await getJSON(
      `/game/content/active-packages?campaign_id=${encodeURIComponent(browser.dataset.roomId)}`
    );
    if (Array.isArray(active?.packages)) packages = active.packages;
    browser.innerHTML = "";
    if (!packages.length) {
      browser.appendChild(el("p", "content-empty", browser.dataset.emptyText || "No active packages."));
      return;
    }
    const list = el("div", "content-package-buttons");
    packages.forEach((packageInfo) => {
      const button = el("button", "content-package-button", packageInfo.name || packageInfo.id);
      button.type = "button";
      button.addEventListener("click", () => void openPackageModal(browser, packageInfo));
      list.appendChild(button);
    });
    browser.appendChild(list);
  }

  function initAll() {
    document.querySelectorAll("[data-content-browser]").forEach(renderBrowser);
  }

  document.addEventListener("DOMContentLoaded", initAll);
  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-panel-toggle]");
    if (toggle && toggle.dataset.panelToggle.startsWith("panel-content-")) setTimeout(initAll, 0);
  });
})();
