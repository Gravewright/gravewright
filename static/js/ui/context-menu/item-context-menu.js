



(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
    const label = FI.label;
    const showMenu = FI.showMenu;
    const body = document.body;

    function itemPanelFolders(panel) {
        if (!panel) return [];
        return Array.from(panel.querySelectorAll("[data-item-folder]")).map((el) => ({
            id: el.dataset.folderId,
            name: el.dataset.folderName,
        }));
    }

    function openItemMenu(e, cardEl) {
        const itemId = cardEl.dataset.itemOpen;
        const panel = cardEl.closest("[data-item-panel]");
        const roomId = panel?.dataset.roomId || "";
        const isGm = panel?.dataset.isGm === "true";

        const items = [{
            text: body.dataset.ctxItemOpen || "Open item",
            action() {
                document.dispatchEvent(new CustomEvent("vtt:open-item-sheet", { detail: { itemId } }));
            },
        }];

        if (!isGm) {
            showMenu(e.clientX, e.clientY, items);
            return;
        }

        items.push({
            text: body.dataset.ctxActorPermissions || "Permissions",
            action() { window.GravewrightItems?.openPermissions(itemId); },
        });

        const folders = itemPanelFolders(panel);
        items.push({ type: "sep" });
        items.push({ type: "label", text: body.dataset.ctxActorMoveToFolder || "Move to folder" });
        items.push({
            text: body.dataset.ctxActorMoveToRoot || "Move out of folder",
            action() { window.GravewrightItems?.moveItem(itemId, "", roomId); },
        });
        for (const f of folders) {
            items.push({
                text: f.name,
                action() { window.GravewrightItems?.moveItem(itemId, f.id, roomId); },
            });
        }

        items.push({ type: "sep" });
        items.push({
            text: body.dataset.ctxItemDelete || "Delete item",
            danger: true,
            action() {
                showMenu(e.clientX, e.clientY, [{
                    text: body.dataset.ctxItemDeleteConfirm || "Confirm delete",
                    danger: true,
                    action() { window.GravewrightItems?.deleteItem(itemId, roomId); },
                }]);
            },
        });

        showMenu(e.clientX, e.clientY, items);
    }

    function openItemFolderMenu(e, folderEl) {
        const folderId = folderEl.dataset.folderId;
        const panel = folderEl.closest("[data-item-panel]");
        const campaignId = panel?.dataset.roomId || "";
        const currentName = folderEl.dataset.folderName || "";
        const folderAction = (path, fields) =>
            window.GravewrightItems?.folderAction(path, fields, campaignId);

        showMenu(e.clientX, e.clientY, [
            {
                text: label("ctxActorFolderRename"),
                action() {
                    const name = window.prompt(label("ctxActorFolderRename"), currentName);
                    if (name && name.trim()) {
                        folderAction("item-folder/rename", { folder_id: folderId, campaign_id: campaignId, name: name.trim() });
                    }
                },
            },
            {
                text: label("ctxActorFolderColor"),
                action() {
                    showMenu(e.clientX, e.clientY, ["#b9995d", "#8ea8ff", "#7ee0a1", "#e88", "#c98bdb"].map((c) => ({
                        text: c,
                        action() {
                            folderAction("item-folder/color", { folder_id: folderId, campaign_id: campaignId, color: c });
                        },
                    })));
                },
            },
            {
                text: label("ctxActorFolderAddSubfolder"),
                action() {
                    const name = window.prompt(label("ctxActorFolderAddSubfolder"), "");
                    if (name && name.trim()) {
                        folderAction("item-folder", { campaign_id: campaignId, name: name.trim(), parent_id: folderId });
                    }
                },
            },
            {
                text: label("ctxActorFolderMoveRoot"),
                action() {
                    folderAction("item-folder/move", { folder_id: folderId, parent_id: "" });
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
                            folderAction("item-folder/delete", { folder_id: folderId, campaign_id: campaignId });
                        },
                    }]);
                },
            },
        ]);
    }

    FI.openItemMenu = openItemMenu;
    FI.openItemFolderMenu = openItemFolderMenu;
})();
