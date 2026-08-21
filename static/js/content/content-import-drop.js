/* Import a read-only compendium document by dropping it on its world directory. */
(() => {
  "use strict";
  const MIME = "application/x-gravewright-drop-source+json";
  const targets = {
    actor_pack: "[data-actor-panel]",
    item_pack: "[data-item-panel]",
    spell_pack: "[data-item-panel]",
    journal_pack: "[data-journal-panel]",
    scene_pack: "[data-scene-panel]",
    card_pack: "[data-card-panel]",
    deck_pack: "[data-card-panel]",
  };

  function source(event) {
    try {
      const value = JSON.parse(event.dataTransfer?.getData(MIME) || "null");
      return value?.kind === "content_pack_entry" ? value : null;
    } catch { return null; }
  }

  function target(event, payload) {
    const selector = targets[payload?.pack_type];
    return selector ? event.target.closest(selector) : null;
  }

  function folderId(node, packType) {
    if (packType === "actor_pack") return node.closest(".actor-folder")?.dataset.folderId || "";
    if (["item_pack", "spell_pack"].includes(packType)) return node.closest(".item-folder")?.dataset.folderId || "";
    if (packType === "journal_pack") return node.closest(".journal-folder")?.dataset.folderId || "";
    if (packType === "scene_pack") return node.closest(".scene-folder")?.dataset.folderId || "";
    return "";
  }

  function clear() {
    document.querySelectorAll(".content-import-drop-over").forEach((node) => node.classList.remove("content-import-drop-over"));
  }

  document.addEventListener("dragover", (event) => {
    const payload = source(event);
    const panel = payload && target(event, payload);
    if (!panel) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    clear();
    (event.target.closest(".sheet-folder") || panel).classList.add("content-import-drop-over");
    event.dataTransfer.dropEffect = "copy";
  }, true);

  document.addEventListener("dragleave", (event) => {
    if (!event.relatedTarget?.closest?.("[data-actor-panel],[data-item-panel],[data-journal-panel],[data-scene-panel],[data-card-panel]")) clear();
  }, true);

  document.addEventListener("drop", async (event) => {
    const payload = source(event);
    const panel = payload && target(event, payload);
    if (!panel) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    clear();
    const result = await window.GravewrightContentApi.postJSON("/game/content/import", {
      campaign_id: panel.dataset.roomId || "",
      package_id: payload.package_id,
      pack_id: payload.pack_id,
      entry_id: payload.entry_id,
      folder_id: folderId(event.target, payload.pack_type),
    });
    if (!result) return;
    const roomId = panel.dataset.roomId || "";
    if (result.actor_id) await window.GravewrightActorsInternals?.refreshPanel?.(roomId);
    if (result.item_id) await window.GravewrightItemsInternals?.refreshPanel?.(roomId);
    if (result.journal_id) await window.GravewrightJournalsInternals?.refreshJournalPanel?.(roomId);
    if (result.scene_id) await window.GravewrightScenes?.refreshPanel?.(roomId);
    if (result.deck_id) document.querySelector(`[data-modal-open="panel-cards-${CSS.escape(roomId)}"]`)?.click();
  }, true);
})();
