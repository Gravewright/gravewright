



(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
    const label = FI.label;
    const showMenu = FI.showMenu;
    const body = document.body;

    function openActorMenu(e, cardEl) {
        const actorId = cardEl.dataset.actorOpen;
        const panel = cardEl.closest("[data-actor-panel]");
        const roomId = panel?.dataset.roomId || "";
        const isGm = panel?.dataset.isGm === "true";

        const items = [];
        const canvas = document.querySelector(
            `[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`
        );
        const sceneId = canvas?.dataset.sceneId || "";

        items.push({
            text: label("ctxTokenOpenSheet"),
            action() {
                document.dispatchEvent(new CustomEvent("vtt:open-actor-sheet", {
                    detail: { actorId },
                }));
            },
        });

        if (!isGm) {
            showMenu(e.clientX, e.clientY, items);
            return;
        }

        items.push({
            text: body.dataset.ctxSheetAddToScene || "Add to scene",
            disabled: !sceneId,
            action() {
                if (!sceneId) return;
                window.GravewrightMap?.startAddToScene({ actorIds: [actorId], sceneId, roomId });
            },
        });
        items.push({
            text: body.dataset.ctxActorPermissions || "Permissions",
            action() { window.GravewrightActors?.openPermissions(actorId); },
        });

        items.push({ type: "sep" });
        items.push({
            text: body.dataset.ctxActorDelete || "Delete actor",
            danger: true,
            action() {
                showMenu(e.clientX, e.clientY, [{
                    text: body.dataset.ctxActorDeleteConfirm || "Confirm delete",
                    danger: true,
                    action() { window.GravewrightActors?.deleteActor(actorId, roomId); },
                }]);
            },
        });

        showMenu(e.clientX, e.clientY, items);
    }

    function openActorFolderMenu(e, folderEl) {
        const folderId = folderEl.dataset.folderId;
        const panel = folderEl.closest("[data-actor-panel]");
        const campaignId = panel?.dataset.roomId || "";
        const currentName = folderEl.dataset.folderName || "";
        const currentColor = folderEl.dataset.folderColor || "";

        const folderAction = (path, fields) =>
            window.GravewrightActors?.folderAction(path, fields, campaignId);

        const canvas = document.querySelector(
            `[data-map-canvas][data-room-id="${CSS.escape(campaignId)}"]`,
        );
        const sceneId = canvas?.dataset.sceneId || "";

        const folderActorIds = Array.from(folderEl.querySelectorAll("[data-actor-card]"))
            .map((c) => c.dataset.actorCard).filter(Boolean);

        showMenu(e.clientX, e.clientY, [
            {
                text: body.dataset.ctxActorCreate || "Create actor",
                action() {
                    FI.openActorCreateModal?.({ campaignId, folderId });
                },
            },
            {
                text: body.dataset.ctxActorFolderAddToScene || "Add folder to scene",
                disabled: !sceneId || !folderActorIds.length,
                action() {
                    if (!sceneId || !folderActorIds.length) return;
                    window.GravewrightMap?.startAddToScene({
                        actorIds: folderActorIds, sceneId, roomId: campaignId,
                    });
                },
            },
            { type: "sep" },
            {
                text: body.dataset.ctxFolderEdit || "Edit folder",
                action() {
                    FI.openFolderEditor?.({
                        kind: "actor", folderId, campaignId, name: currentName, color: currentColor,
                    });
                },
            },
            {
                text: label("ctxActorFolderAddSubfolder"),
                action() {
                    FI.openFolderCreateModal?.({ kind: "actor", campaignId, parentId: folderId });
                },
            },
            { type: "sep" },
            {
                text: label("ctxActorFolderDelete"),
                danger: true,
                action() {
                    showMenu(e.clientX, e.clientY, [{
                        text: label("ctxActorFolderDeleteConfirm"),
                        danger: true,
                        action() {
                            folderAction("actor-folder/delete", { folder_id: folderId, campaign_id: campaignId });
                        },
                    }]);
                },
            },
        ]);
    }

    FI.openActorMenu = openActorMenu;
    FI.openActorFolderMenu = openActorFolderMenu;
})();
