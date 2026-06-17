



(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
    const label = FI.label;
    const showMenu = FI.showMenu;
    const body = document.body;

    function actorPanelFolders(panel) {
        if (!panel) return [];
        return Array.from(panel.querySelectorAll("[data-actor-folder]")).map((el) => ({
            id: el.dataset.folderId,
            name: el.dataset.folderName,
        }));
    }

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

        const folders = actorPanelFolders(panel);
        items.push({ type: "sep" });
        items.push({ type: "label", text: body.dataset.ctxActorMoveToFolder || "Move to folder" });
        items.push({
            text: body.dataset.ctxActorMoveToRoot || "Move out of folder",
            action() { window.GravewrightActors?.moveActor(actorId, "", roomId); },
        });
        for (const f of folders) {
            items.push({
                text: f.name,
                action() { window.GravewrightActors?.moveActor(actorId, f.id, roomId); },
            });
        }

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
                text: label("ctxActorFolderRename"),
                action() {
                    const name = window.prompt(label("ctxActorFolderRename"), currentName);
                    if (name && name.trim()) {
                        folderAction("actor-folder/rename", { folder_id: folderId, campaign_id: campaignId, name: name.trim() });
                    }
                },
            },
            {
                text: label("ctxActorFolderColor"),
                action() {
                    showMenu(e.clientX, e.clientY, ["#b9995d", "#8ea8ff", "#7ee0a1", "#e88", "#c98bdb"].map((c) => ({
                        text: c,
                        action() {
                            folderAction("actor-folder/color", { folder_id: folderId, campaign_id: campaignId, color: c });
                        },
                    })));
                },
            },
            {
                text: label("ctxActorFolderAddSubfolder"),
                action() {
                    const name = window.prompt(label("ctxActorFolderAddSubfolder"), "");
                    if (name && name.trim()) {
                        folderAction("actor-folder", { campaign_id: campaignId, name: name.trim(), parent_id: folderId });
                    }
                },
            },
            {
                text: label("ctxActorFolderMoveRoot"),
                action() {
                    folderAction("actor-folder/move", { folder_id: folderId, parent_id: "" });
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
