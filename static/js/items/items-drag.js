




(() => {
    const FI = (window.GravewrightItemsInternals = window.GravewrightItemsInternals || {});
    const roomIdFromEvent = FI.roomIdFromEvent;

    let dragKind = null;
    let dragId = null;

    document.addEventListener("dragstart", (event) => {
        const card = event.target.closest("[data-item-card]");
        const folder = event.target.closest(".item-folder[draggable='true']");
        if (card) {
            dragKind = "item"; dragId = card.dataset.itemCard;
            
            
            
            try {
                event.dataTransfer.setData(
                    "application/x-gravewright-drop-source+json",
                    JSON.stringify({ kind: "item", item_id: dragId }),
                );
            } catch {  }
            event.dataTransfer.effectAllowed = "copyMove";
        } else if (folder && event.target.closest(".sheet-folder-header")) {
            dragKind = "folder"; dragId = folder.dataset.folderId;
            event.dataTransfer.effectAllowed = "move";
        } else {
            return;
        }
        try { event.dataTransfer.setData("text/plain", dragId); } catch {  }
    });

    document.addEventListener("dragend", () => { clearDropHints(); dragKind = null; dragId = null; });

    function dropTarget(event) { return event.target.closest("[data-item-folder-drop]"); }
    function clearDropHints() {
        document.querySelectorAll(".item-drop-over").forEach((el) => el.classList.remove("item-drop-over"));
    }

    document.addEventListener("dragover", (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        if (dragKind === "folder") {
            const folderEl = target.closest(".item-folder");
            if (folderEl && (folderEl.dataset.folderId === dragId ||
                folderEl.closest(`.item-folder[data-folder-id="${CSS.escape(dragId)}"]`))) {
                return;
            }
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        clearDropHints();
        target.classList.add("item-drop-over");
    });

    document.addEventListener("drop", async (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        event.preventDefault();
        clearDropHints();
        const roomId = roomIdFromEvent(target);
        const targetFolderId = target.dataset.itemFolderDrop || "";
        const kind = dragKind, id = dragId;
        dragKind = null; dragId = null;
        if (!id) return;
        if (kind === "item") {
            await window.GravewrightItems.moveItem(id, targetFolderId, roomId);
        } else if (kind === "folder" && id !== targetFolderId) {
            await window.GravewrightItems.moveFolder(id, targetFolderId, roomId);
        }
    });
})();
