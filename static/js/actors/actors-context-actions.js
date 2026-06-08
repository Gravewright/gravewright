



(() => {
    const FI = (window.GravewrightActorsInternals = window.GravewrightActorsInternals || {});
    const postForm = FI.postForm;
    const postJson = FI.postJson;
    const refreshPanel = FI.refreshPanel;

    window.GravewrightActors = {
        async folderAction(path, fields, roomId) {
            const res = await postForm(`/game/${path}`, fields);
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async moveActor(actorId, folderId, roomId) {
            const res = await postForm("/game/actor/move", { actor_id: actorId, folder_id: folderId || "" });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async moveFolder(folderId, parentId, roomId) {
            const res = await postForm("/game/actor-folder/move", { folder_id: folderId, parent_id: parentId || "" });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async toggleOwner(actorId, userId, roomId) {
            const res = await postForm("/game/actor/owner", { actor_id: actorId, owner_user_id: userId });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        async deleteActor(actorId, roomId) {
            const res = await postJson("/game/actor/delete", { actor_id: actorId });
            if (res.ok) await refreshPanel(roomId);
            return res.ok;
        },
        refreshPanel,
        openPermissions(actorId) {
            const trigger = document.createElement("button");
            trigger.type = "button";
            trigger.dataset.resourcePermissions = "actor";
            trigger.dataset.resourceId = actorId;
            trigger.style.display = "none";
            document.body.appendChild(trigger);
            trigger.click();
            trigger.remove();
        },
    };
})();
