



(() => {
    const FI = (window.GravewrightItemsInternals = window.GravewrightItemsInternals || {});
    const postForm = FI.postForm;
    const postJson = FI.postJson;
    const refreshPanel = FI.refreshPanel;

    window.GravewrightItems = {
        async folderAction(path, fields, roomId) {
            const res = await postForm(`/game/${path}`, fields);
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async moveItem(itemId, folderId, roomId) {
            const res = await postForm("/game/item/move", { item_id: itemId, folder_id: folderId || "" });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async moveFolder(folderId, parentId, roomId) {
            const res = await postForm("/game/item-folder/move", { folder_id: folderId, parent_id: parentId || "" });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async toggleOwner(itemId, userId, roomId) {
            const res = await postForm("/game/item/owner", { item_id: itemId, owner_user_id: userId });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async deleteItem(itemId, roomId) {
            const res = await postJson("/game/item/delete", { item_id: itemId });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        refreshPanel,
        openPermissions(itemId) {
            const trigger = document.createElement("button");
            trigger.type = "button";
            trigger.dataset.resourcePermissions = "item";
            trigger.dataset.resourceId = itemId;
            trigger.style.display = "none";
            document.body.appendChild(trigger);
            trigger.click();
            trigger.remove();
        },
    };
})();
