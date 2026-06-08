





(function () {
  const Api = window.GravewrightContentApi;
  const SOURCE_MIME = Api.SOURCE_MIME;
  const csrf = Api.csrf;
  const getJSON = Api.getJSON;
  const postJSON = Api.postJSON;

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function renderEntry(browser, system, pack, entry) {
    const item = el("li", "content-entry");
    item.draggable = true;
    item.dataset.contentDrag = JSON.stringify({
      kind: "content_pack_entry",
      system_id: system.id, pack_id: pack.id, entry_id: entry.id, type: entry.type,
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
      importBtn.title = "Import";
      importBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const url = importKind === "actor" ? "/game/content/import" : "/game/item/content/import";
        const created = await postJSON(url, {
          csrf_token: csrf(), campaign_id: browser.dataset.roomId,
          system_id: system.id, pack_id: pack.id, entry_id: entry.id,
        });
        if (!created) return;
        if (importKind === "actor" && created.actor_id) {
          document.dispatchEvent(new CustomEvent("vtt:open-actor-sheet", { detail: { actorId: created.actor_id } }));
        } else if (importKind === "item" && created.item_id) {
          document.dispatchEvent(new CustomEvent("vtt:open-item-sheet", { detail: { itemId: created.item_id } }));
        }
      });
      item.appendChild(importBtn);
    }

    item.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData(SOURCE_MIME, item.dataset.contentDrag);
      e.dataTransfer.effectAllowed = "copy";
    });
    return item;
  }

  async function renderPack(browser, system, pack, container) {
    const details = el("details", "content-pack");
    const summary = el("summary", "content-pack-summary", `${pack.label || pack.id}`);
    details.appendChild(summary);
    const list = el("ul", "content-entry-list");
    details.appendChild(list);
    let loaded = false;
    details.addEventListener("toggle", async () => {
      if (!details.open || loaded) return;
      loaded = true;
      const full = await getJSON(`/game/content/pack/${encodeURIComponent(system.id)}/${encodeURIComponent(pack.id)}`);
      (full?.entries || []).forEach((entry) => list.appendChild(renderEntry(browser, system, pack, entry)));
      if (!full?.entries?.length) list.appendChild(el("li", "content-entry-empty", "—"));
    });
    container.appendChild(details);
  }

  async function renderBrowser(browser) {
    if (browser.dataset.loaded) return;
    browser.dataset.loaded = "1";
    let systems = [];
    try {
      systems = JSON.parse(browser.dataset.contentSystems || "[]");
    } catch {
      systems = [];
    }
    browser.innerHTML = "";
    if (!systems.length) {
      browser.appendChild(el("p", "content-empty", browser.dataset.emptyText || "No enabled systems."));
      return;
    }
    for (const system of systems) {
      const group = el("div", "content-system-group");
      group.appendChild(el("h4", "content-system-title", system.name || system.id));
      browser.appendChild(group);
      const packs = await getJSON(`/game/content/packs/${encodeURIComponent(system.id)}`);
      const list = (packs?.packs || []);
      if (!list.length) {
        group.appendChild(el("p", "content-empty", "—"));
        continue;
      }
      for (const pack of list) {
        await renderPack(browser, system, pack, group);
      }
    }
  }

  function initAll() {
    document.querySelectorAll("[data-content-browser]").forEach(renderBrowser);
  }

  document.addEventListener("DOMContentLoaded", initAll);
  
  document.addEventListener("click", (e) => {
    const toggle = e.target.closest("[data-panel-toggle]");
    if (toggle && toggle.dataset.panelToggle.startsWith("panel-content-")) {
      setTimeout(initAll, 0);
    }
  });
})();
