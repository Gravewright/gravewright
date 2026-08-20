/* Arrastar cena entre pastas, no mesmo contrato de atores, itens e diarios.
 *
 * So a cena arrasta: grupos de cena nao aninham (scene_groups nao tem
 * parent_id), entao nao ha para onde arrastar uma pasta.
 */
(() => {
  "use strict";

  let dragId = null;

  const cardFor = (id) => document.querySelector(`[data-scene-card="${CSS.escape(id)}"]`);

  function dropTarget(event) {
    const folder = event.target.closest(".scene-folder[data-folder-id]");
    if (folder) return folder.querySelector(":scope > .sheet-folder-header[data-scene-folder-drop]");
    return event.target.closest("[data-scene-root-list]")
      || event.target.closest("[data-scene-panel]")?.querySelector("[data-scene-root-list]")
      || null;
  }

  function clearHints() {
    document.querySelectorAll(".scene-drop-over").forEach((el) => el.classList.remove("scene-drop-over"));
    window.GravewrightDirectoryDrag?.clearTarget();
  }

  document.addEventListener("dragstart", (event) => {
    const entry = event.target.closest("[data-scene-card]");
    if (!entry || !entry.closest("[data-scene-panel]")) return;
    dragId = entry.dataset.sceneCard;
    window.GravewrightDirectoryDrag?.start({
      event,
      source: entry,
      panel: entry.closest("[data-scene-panel]"),
      kind: "scene",
      id: dragId,
      label: entry.dataset.directoryName || "",
    });
    event.dataTransfer.effectAllowed = "move";
    try { event.dataTransfer.setData("text/plain", dragId); } catch { /* opcional */ }
  });

  document.addEventListener("dragend", () => {
    clearHints();
    window.GravewrightDirectoryDrag?.end();
    dragId = null;
  });

  document.addEventListener("dragover", (event) => {
    if (!dragId) return;
    const target = dropTarget(event);
    if (!target) return;
    const folder = target.closest(".scene-folder");
    const targetFolderId = target.dataset.sceneFolderDrop || "";
    const valid = window.GravewrightDirectoryDrag?.canDrop({
      source: cardFor(dragId), kind: "scene", targetFolder: folder,
      targetFolderId, folderSelector: ".scene-folder",
    }) ?? true;
    clearHints();
    if (window.GravewrightDirectoryDrag) {
      window.GravewrightDirectoryDrag.mark(event, {
        target, valid, folder, type: "scenes", visual: true,
      });
    } else if (valid) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      target.classList.add("scene-drop-over");
    }
  });

  document.addEventListener("drop", async (event) => {
    if (!dragId) return;
    const target = dropTarget(event);
    if (!target) return;
    event.preventDefault();
    const targetFolderId = target.dataset.sceneFolderDrop || "";
    const valid = window.GravewrightDirectoryDrag?.canDrop({
      source: cardFor(dragId), kind: "scene", targetFolder: target.closest(".scene-folder"),
      targetFolderId, folderSelector: ".scene-folder",
    }) ?? true;
    const roomId = target.closest("[data-scene-panel]")?.dataset.roomId || "";
    const sceneId = dragId;
    clearHints();
    dragId = null;
    window.GravewrightDirectoryDrag?.end();
    if (!valid || !sceneId) return;
    await window.GravewrightScenes?.moveScene(sceneId, targetFolderId, roomId);
  });
})();
