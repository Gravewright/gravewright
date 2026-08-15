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
    });
    item.appendChild(el("span", "content-entry-name", entry.name || entry.id));
    if (entry.type) item.appendChild(el("span", "content-entry-type", entry.type));

    const importKind =
      pack.type === "actor_pack" ? "actor"
      : pack.type === "item_pack" || pack.type === "spell_pack" ? "item"
      : null;
    if (importKind) {
      const importBtn = el("button", "content-import-btn", "+");
      importBtn.type = "button";
      importBtn.title = browser.dataset.importOneText || "Import";
      importBtn.addEventListener("click", async (event) => {
        event.stopPropagation();
        importBtn.disabled = true;
        const url = importKind === "actor" ? "/game/content/import" : "/game/item/content/import";
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

  function renderPack(browser, packageInfo, pack, container) {
    const details = el("details", "content-pack");
    details.appendChild(el("summary", "content-pack-summary", pack.label || pack.id));
    const list = el("ul", "content-entry-list");
    details.appendChild(list);
    let loaded = false;
    details.addEventListener("toggle", async () => {
      if (!details.open || loaded) return;
      loaded = true;
      const full = await getJSON(`/game/content/pack/${encodeURIComponent(packageInfo.id)}/${encodeURIComponent(pack.id)}`);
      (full?.entries || []).forEach((entry) => list.appendChild(renderEntry(browser, packageInfo, pack, entry)));
      if (!full?.entries?.length) list.appendChild(el("li", "content-entry-empty", "—"));
    });
    container.appendChild(details);
  }

  async function openPackageModal(browser, packageInfo) {
    const dialog = el("dialog", "content-package-modal");
    const shell = el("section", "content-package-modal-shell");
    const header = el("header", "content-package-modal-header");
    const actions = el("div", "content-package-modal-actions");
    const importAll = el("button", "content-import-all", browser.dataset.importAllText || "Import all");
    importAll.type = "button";
    const close = el("button", "content-package-modal-close", "×");
    close.type = "button";
    close.setAttribute("aria-label", browser.dataset.closeText || "Close");
    actions.append(importAll, close);
    header.append(actions, el("h3", "content-package-modal-title", packageInfo.name || packageInfo.id));
    const status = el("p", "content-package-import-status");
    const body = el("div", "content-package-modal-body");
    shell.append(header, status, body);
    dialog.appendChild(shell);
    document.body.appendChild(dialog);

    close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => dialog.remove());
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

    dialog.showModal();
    const packs = await getJSON(`/game/content/packs/${encodeURIComponent(packageInfo.id)}`);
    if (!packs?.packs?.length) {
      body.appendChild(el("p", "content-empty", browser.dataset.packEmptyText || "No content."));
      return;
    }
    packs.packs.forEach((pack) => renderPack(browser, packageInfo, pack, body));
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
