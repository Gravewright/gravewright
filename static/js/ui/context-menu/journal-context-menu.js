


(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
    const showMenu = FI.showMenu;
    const getCsrf = FI.getCsrf;
    const body = document.body;

    function openJournalPermissions(journalId) {

        const trigger = document.createElement("button");
        trigger.type = "button";
        trigger.dataset.resourcePermissions = "journal";
        trigger.dataset.resourceId = journalId;
        trigger.style.display = "none";
        body.appendChild(trigger);
        trigger.click();
        trigger.remove();
    }

    async function deleteJournal(journalId) {
        await fetch("/game/journal/delete", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
            body: new URLSearchParams({ csrf_token: getCsrf(), journal_id: journalId }),
            credentials: "same-origin",
        });

    }

    function openJournalMenu(e, cardEl) {
        const journalId = cardEl.dataset.journalSelect || cardEl.dataset.journalId;
        if (!journalId) return;
        const isGm = cardEl.closest("[data-journal-panel]")?.dataset.isGm === "true";
        const currentUserId = body.dataset.currentUserId || "";
        let isOwner = false;
        try {
            const owners = JSON.parse(cardEl.dataset.ownersJson || "[]");
            isOwner = Array.isArray(owners) && owners.some((o) => o && o.id === currentUserId);
        } catch {  }

        const items = [{
            text: body.dataset.ctxJournalOpen || "Open",
            action() {
                document.dispatchEvent(new CustomEvent("vtt:open-journal", { detail: { journalId } }));
            },
        }];

        if (isGm) {
            items.push({
                text: body.dataset.ctxJournalOwner || "Permissions",
                action() { openJournalPermissions(journalId); },
            });
        }

        if (isGm || isOwner) {
            items.push({ type: "sep" });
            items.push({
                text: body.dataset.ctxJournalDelete || "Delete",
                danger: true,
                action() {
                    showMenu(e.clientX, e.clientY, [{
                        text: body.dataset.ctxJournalDeleteConfirm || "Confirm delete",
                        danger: true,
                        action() { deleteJournal(journalId); },
                    }]);
                },
            });
        }

        showMenu(e.clientX, e.clientY, items);
    }

    function openJournalFolderMenu(e, folderEl) {
        const panel = folderEl.closest("[data-journal-panel]");
        const campaignId = panel?.dataset.roomId || "";
        const folderId = folderEl.dataset.folderId || "";
        if (!campaignId || !folderId) return;
        showMenu(e.clientX, e.clientY, [
            {
                text: body.dataset.ctxFolderEdit || "Edit folder",
                action() {
                    FI.openFolderEditor({
                        kind: "journal", folderId, campaignId,
                        name: folderEl.dataset.folderName || "",
                        color: folderEl.dataset.folderColor || "",
                    });
                },
            },
            {
                text: body.dataset.ctxActorFolderAddSubfolder || "New subfolder",
                action() {
                    FI.openFolderCreateModal({ kind: "journal", campaignId, parentId: folderId });
                },
            },
            { type: "sep" },
            {
                text: body.dataset.ctxJournalCreate || "Create journal",
                action() {
                    document.dispatchEvent(new CustomEvent("vtt:open-journal-create", {
                        detail: { campaignId, folderId },
                    }));
                },
            },
            { type: "sep" },
            {
                text: body.dataset.ctxJournalFolderDelete || "Delete folder",
                danger: true,
                action() {
                    showMenu(e.clientX, e.clientY, [{
                        text: body.dataset.ctxActorFolderDeleteConfirm || "Confirm delete folder",
                        danger: true,
                        async action() {
                            const response = await window.GravewrightJournalsInternals.postJournal(
                                "/game/journal/folder/delete",
                                { folder_id: folderId, campaign_id: campaignId },
                            );
                            if (response.ok) {
                                window.GravewrightJournalsInternals.refreshJournalPanel(campaignId);
                            }
                        },
                    }]);
                },
            },
        ]);
    }

    FI.openJournalMenu = openJournalMenu;
    FI.openJournalFolderMenu = openJournalFolderMenu;
})();
