



(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
    const label = FI.label;
    const showMenu = FI.showMenu;
    const body = document.body;

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
        const currentColor = folderEl.dataset.folderColor || "";
        const folderAction = (path, fields) =>
            window.GravewrightItems?.folderAction(path, fields, campaignId);

        showMenu(e.clientX, e.clientY, [
            {
                text: body.dataset.ctxFolderEdit || "Edit folder",
                action() {
                    FI.openFolderEditor?.({
                        kind: "item", folderId, campaignId, name: currentName, color: currentColor,
                    });
                },
            },
            {
                text: label("ctxActorFolderAddSubfolder"),
                action() {
                    FI.openFolderCreateModal?.({ kind: "item", campaignId, parentId: folderId });
                },
            },
            { type: "sep" },
            {
                text: label("ctxActorFolderDelete"),
                danger: true,
                action() {
                    showMenu(e.clientX, e.clientY, [
                        { type: "label", text: label("ctxItemFolderDeleteQuestion") },
                        {
                            text: label("ctxItemFolderDeleteOnly"),
                            action() {
                                folderAction("item-folder/delete", {
                                    folder_id: folderId, campaign_id: campaignId, delete_contents: "false",
                                });
                            },
                        },
                        {
                            text: label("ctxItemFolderDeleteWithContents"),
                            danger: true,
                            action() {
                                folderAction("item-folder/delete", {
                                    folder_id: folderId, campaign_id: campaignId, delete_contents: "true",
                                });
                            },
                        },
                    ]);
                },
            },
        ]);
    }

    FI.openItemMenu = openItemMenu;
    FI.openItemFolderMenu = openItemFolderMenu;
})();
