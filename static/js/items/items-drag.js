




(() => {
    const FI = (window.GravewrightItemsInternals = window.GravewrightItemsInternals || {});
    const roomIdFromEvent = FI.roomIdFromEvent;

    let dragKind = null;
    let dragId = null;
    let folderDragFromHandle = false;





    document.addEventListener("pointerdown", (event) => {
        const card = event.target.closest("[data-item-card]");
        if (card) card.draggable = true;
        if (event.target.closest("[data-item-panel]")) {
            folderDragFromHandle = !!event.target.closest(".sheet-folder-drag-handle");
        }
    }, true);

    document.addEventListener("dragstart", (event) => {
        const card = event.target.closest("[data-item-card]");
        const folder = event.target.closest(".item-folder[draggable='true']");
        if (card) {
            dragKind = "item"; dragId = card.dataset.itemCard;



            try {
                event.dataTransfer.setData(
                    "application/x-gravewright-drop-source+json",


                    JSON.stringify({ kind: "item", item_id: dragId, item_type: card.dataset.itemType || "" }),
                );
            } catch {  }
            event.dataTransfer.effectAllowed = "copyMove";
        } else if (folder && folderDragFromHandle) {
            dragKind = "folder"; dragId = folder.dataset.folderId;
            event.dataTransfer.effectAllowed = "move";
        } else {
            if (folder) event.preventDefault();
            folderDragFromHandle = false;
            return;
        }
        const source = card || folder;
        const label = source.dataset.directoryName || source.dataset.folderName ||
            source.querySelector(":scope > .sheet-folder-header .sheet-folder-name, strong")?.textContent?.trim() || "";
        const count = folder ? folder.querySelectorAll("[data-item-card]").length : 0;
        window.GravewrightDirectoryDrag?.start({
            event, source, panel: source.closest("[data-item-panel]"), kind: dragKind, id: dragId, label, count,
        });
        folderDragFromHandle = false;
        try { event.dataTransfer.setData("text/plain", dragId); } catch {  }
    });

    document.addEventListener("dragend", () => {
        clearDropHints(); window.GravewrightDirectoryDrag?.end();
        dragKind = null; dragId = null; folderDragFromHandle = false;
    });

    function dropTarget(event) {
        const folder = event.target.closest(".item-folder[data-folder-id]");
        return folder?.querySelector(":scope > .sheet-folder-header[data-item-folder-drop]") ||
            event.target.closest("[data-item-panel]");
    }
    function clearDropHints() {
        document.querySelectorAll(".item-drop-over").forEach((el) => el.classList.remove("item-drop-over"));
        window.GravewrightDirectoryDrag?.clearTarget();
    }

    document.addEventListener("dragover", (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        const source = document.querySelector(dragKind === "folder"
            ? `.item-folder[data-folder-id="${CSS.escape(dragId)}"]`
            : `[data-item-card="${CSS.escape(dragId)}"]`);
        const folderEl = target.closest(".item-folder");
        const targetFolderId = target.dataset.itemFolderDrop || "";
        const valid = window.GravewrightDirectoryDrag?.canDrop({
            source, kind: dragKind, targetFolder: folderEl, targetFolderId, folderSelector: ".item-folder",
        }) ?? true;
        clearDropHints();
        if (window.GravewrightDirectoryDrag) {
            window.GravewrightDirectoryDrag.mark(event, {
                target, valid, folder: folderEl, type: "items", visual: Boolean(folderEl),
            });
        } else if (valid) {
            event.preventDefault(); event.dataTransfer.dropEffect = "move"; target.classList.add("item-drop-over");
        }
    });

    document.addEventListener("drop", async (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        event.preventDefault();
        const source = document.querySelector(dragKind === "folder"
            ? `.item-folder[data-folder-id="${CSS.escape(dragId)}"]`
            : `[data-item-card="${CSS.escape(dragId)}"]`);
        const targetFolderId = target.dataset.itemFolderDrop || "";
        const valid = window.GravewrightDirectoryDrag?.canDrop({
            source, kind: dragKind, targetFolder: target.closest(".item-folder"), targetFolderId,
            folderSelector: ".item-folder",
        }) ?? true;
        clearDropHints();
        if (!valid) return;
        const roomId = roomIdFromEvent(target);
        const kind = dragKind, id = dragId;
        dragKind = null; dragId = null;
        window.GravewrightDirectoryDrag?.end();
        if (!id) return;
        if (kind === "item") {
            await window.GravewrightItems.moveItem(id, targetFolderId, roomId);
        } else if (kind === "folder" && id !== targetFolderId) {
            await window.GravewrightItems.moveFolder(id, targetFolderId, roomId);
        }
    });
})();
