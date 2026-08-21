



(() => {
    const FI = (window.GravewrightActorsInternals = window.GravewrightActorsInternals || {});
    const roomIdFromEvent = FI.roomIdFromEvent;
    const ACTOR_DROP_MIME = "application/x-gravewright-actors+json";

    let dragKind = null;
    let dragId = null;
    let tableDropPayload = null;
    let folderDragFromHandle = false;

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

    document.addEventListener("pointerdown", (event) => {
        if (event.target.closest("[data-actor-panel]")) {
            folderDragFromHandle = !!event.target.closest(".sheet-folder-drag-handle");
        }
    }, true);

    document.addEventListener("dragstart", (event) => {
        const card = event.target.closest("[data-actor-card]");
        const folderHeader = event.target.closest(".actor-folder .sheet-folder-header");
        const folder = folderHeader?.closest(".actor-folder") || event.target.closest(".actor-folder[draggable='true']");
        if (card) {
            dragKind = "actor"; dragId = card.dataset.actorCard;
            setTableDropPayload(event, card);
        } else if (folder && folderDragFromHandle) {
            dragKind = "folder"; dragId = folder.dataset.folderId;
            setTableDropPayload(event, folder);
        } else {
            if (folder) event.preventDefault();
            folderDragFromHandle = false;
            return;
        }
        const source = card || folder;
        const label = source.dataset.directoryName || source.dataset.folderName ||
            source.querySelector(":scope > .sheet-folder-header .sheet-folder-name, strong")?.textContent?.trim() || "";
        const count = folder ? folderActorIds(folder).length : 0;
        window.GravewrightDirectoryDrag?.start({
            event, source, panel: source.closest("[data-actor-panel]"), kind: dragKind, id: dragId, label, count,
        });
        folderDragFromHandle = false;
        event.dataTransfer.effectAllowed = "copyMove";
        try { event.dataTransfer.setData("text/plain", dragId); } catch {  }
    });

    document.addEventListener("dragend", () => {
        clearDropHints(); window.GravewrightDirectoryDrag?.end();
        dragKind = null; dragId = null; tableDropPayload = null; folderDragFromHandle = false;
    });

    function dropTarget(event) {
        if (event.target.closest("[data-templates-folder]")) return null;
        const folder = event.target.closest(".actor-folder[data-folder-id]");
        return folder?.querySelector(":scope > .sheet-folder-header[data-actor-folder-drop]") ||
            event.target.closest("[data-actor-panel]");
    }
    function clearDropHints() {
        document.querySelectorAll(".actor-drop-over").forEach((el) => el.classList.remove("actor-drop-over"));
        window.GravewrightDirectoryDrag?.clearTarget();
    }

    document.addEventListener("dragover", (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        const source = document.querySelector(dragKind === "folder"
            ? `.actor-folder[data-folder-id="${CSS.escape(dragId)}"]`
            : `[data-actor-card="${CSS.escape(dragId)}"]`);
        const folderEl = target.closest(".actor-folder");
        const targetFolderId = target.dataset.actorFolderDrop || "";
        const valid = window.GravewrightDirectoryDrag?.canDrop({
            source, kind: dragKind, targetFolder: folderEl, targetFolderId, folderSelector: ".actor-folder",
        }) ?? true;
        clearDropHints();
        if (window.GravewrightDirectoryDrag) {
            window.GravewrightDirectoryDrag.mark(event, {
                target, valid, folder: folderEl, type: "actors", visual: Boolean(folderEl),
            });
        } else if (valid) {
            event.preventDefault(); event.dataTransfer.dropEffect = "move"; target.classList.add("actor-drop-over");
        }
    });

    document.addEventListener("drop", async (event) => {
        if (!dragKind) return;
        const target = dropTarget(event);
        if (!target) return;
        event.preventDefault();
        const source = document.querySelector(dragKind === "folder"
            ? `.actor-folder[data-folder-id="${CSS.escape(dragId)}"]`
            : `[data-actor-card="${CSS.escape(dragId)}"]`);
        const targetFolderId = target.dataset.actorFolderDrop || "";
        const valid = window.GravewrightDirectoryDrag?.canDrop({
            source, kind: dragKind, targetFolder: target.closest(".actor-folder"), targetFolderId,
            folderSelector: ".actor-folder",
        }) ?? true;
        clearDropHints();
        if (!valid) return;
        const roomId = roomIdFromEvent(target);
        const kind = dragKind, id = dragId;
        dragKind = null; dragId = null;
        window.GravewrightDirectoryDrag?.end();
        if (!id) return;
        if (kind === "actor") {
            await window.GravewrightActors.moveActor(id, targetFolderId, roomId);
        } else if (kind === "folder" && id !== targetFolderId) {
            await window.GravewrightActors.moveFolder(id, targetFolderId, roomId);
        }
    });

    FI.currentTableDropPayload = () => tableDropPayload || tablePayloadFor(dragKind, dragId);
})();
