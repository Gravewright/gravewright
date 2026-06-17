



(() => {
    const FI = (window.GravewrightActorsInternals = window.GravewrightActorsInternals || {});
    const roomIdFromEvent = FI.roomIdFromEvent;
    const ACTOR_DROP_MIME = "application/x-gravewright-actors+json";

    let dragKind = null;
    let dragId = null;
    let tableDropPayload = null;

    function folderActorIds(folder) {
        return Array.from(folder.querySelectorAll("[data-actor-card]"))
            .map((card) => card.dataset.actorCard)
            .filter(Boolean);
    }

    function tablePayloadFor(kind, id) {
        if (!kind || !id) return null;
        if (kind === "actor") {
            const card = document.querySelector(`[data-actor-card="${CSS.escape(id)}"]`);
            const panel = card?.closest("[data-actor-panel]");
            if (!card || panel?.dataset.canTableDrop !== "true") return null;
            return { actorIds: [id], roomId: panel.dataset.roomId || "" };
        }
        if (kind === "folder") {
            const folder = document.querySelector(`.actor-folder[data-folder-id="${CSS.escape(id)}"]`);
            const panel = folder?.closest("[data-actor-panel]");
            if (!folder || panel?.dataset.canTableDrop !== "true") return null;
            const actorIds = folderActorIds(folder);
            if (!actorIds.length) return null;
            return { actorIds, roomId: panel.dataset.roomId || "" };
        }
        return null;
    }

    function setTableDropPayload(event, source) {
        const panel = source.closest("[data-actor-panel]");
        if (panel?.dataset.canTableDrop !== "true") return;
        const roomId = panel.dataset.roomId || "";
        let actorIds = [];
        if (source.matches("[data-actor-card]")) actorIds = [source.dataset.actorCard].filter(Boolean);
        else actorIds = folderActorIds(source);
        if (!actorIds.length) return;
        tableDropPayload = { actorIds, roomId };
        try {
            event.dataTransfer.setData(ACTOR_DROP_MIME, JSON.stringify(tableDropPayload));
        } catch {  }
    }

    document.addEventListener("dragstart", (event) => {
        const card = event.target.closest("[data-actor-card]");
        const folderHeader = event.target.closest(".actor-folder .sheet-folder-header");
        const folder = folderHeader?.closest(".actor-folder") || event.target.closest(".actor-folder[draggable='true']");
        if (card) {
            dragKind = "actor"; dragId = card.dataset.actorCard;
            setTableDropPayload(event, card);
        } else if (folder && (folderHeader || event.target.closest(".sheet-folder-header"))) {
            dragKind = "folder"; dragId = folder.dataset.folderId;
            setTableDropPayload(event, folder);
        } else {
            return;
        }
        event.dataTransfer.effectAllowed = "copyMove";
        try { event.dataTransfer.setData("text/plain", dragId); } catch {  }
    });

    document.addEventListener("dragend", () => { clearDropHints(); dragKind = null; dragId = null; tableDropPayload = null; });

    function dropTarget(event) { return event.target.closest("[data-actor-folder-drop]"); }
    function clearDropHints() {
        document.querySelectorAll(".actor-drop-over").forEach((el) => el.classList.remove("actor-drop-over"));
    }

    document.addEventListener("dragover", (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        if (dragKind === "folder") {
            const folderEl = target.closest(".actor-folder");
            if (folderEl && (folderEl.dataset.folderId === dragId ||
                folderEl.closest(`.actor-folder[data-folder-id="${CSS.escape(dragId)}"]`))) {
                return;
            }
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
        clearDropHints();
        target.classList.add("actor-drop-over");
    });

    document.addEventListener("drop", async (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        event.preventDefault();
        clearDropHints();
        const roomId = roomIdFromEvent(target);
        const targetFolderId = target.dataset.actorFolderDrop || "";
        const kind = dragKind, id = dragId;
        dragKind = null; dragId = null;
        if (!id) return;
        if (kind === "actor") {
            await window.GravewrightActors.moveActor(id, targetFolderId, roomId);
        } else if (kind === "folder" && id !== targetFolderId) {
            await window.GravewrightActors.moveFolder(id, targetFolderId, roomId);
        }
    });

    FI.currentTableDropPayload = () => tableDropPayload || tablePayloadFor(dragKind, dragId);
})();
