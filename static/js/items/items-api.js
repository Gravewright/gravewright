




(() => {
    const FI = (window.GravewrightItemsInternals = window.GravewrightItemsInternals || {});

    function csrf() {
        return window.csrfToken();
    }

    function panelFor(roomId) {
        return document.querySelector(
            `[data-item-panel][data-room-id="${CSS.escape(roomId)}"]`,
        );
    }

    function treeHostFor(roomId) {
        return panelFor(roomId)?.querySelector("[data-item-tree-host]");
    }

    function roomIdFromEvent(target) {
        return target?.closest?.("[data-item-panel]")?.dataset.roomId || "";
    }

    function closeDialog(form) {
        form?.closest("[data-modal-window]")?.querySelector("[data-modal-close]")?.click();
    }

    async function postForm(url, fields) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                Accept: "application/json",
            },
            body: new URLSearchParams({ csrf_token: csrf(), ...fields }),
            credentials: "same-origin",
        });
    }



    async function postJson(url, fields) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({ csrf_token: csrf(), ...fields }),
            credentials: "same-origin",
        });
    }

    async function refreshPanel(roomId) {
        const host = treeHostFor(roomId);
        if (!host) return false;
        try {
            const res = await fetch(`/game/items/panel/${encodeURIComponent(roomId)}`, {
                credentials: "same-origin",
                headers: { Accept: "text/html" },
            });
            if (!res.ok) return false;
            const html = await res.text();
            const expanded = new Set(
                Array.from(host.querySelectorAll(".item-folder[data-open]"))
                    .map((f) => f.dataset.folderId),
            );
            host.innerHTML = html;
            expanded.forEach((id) => {
                const f = host.querySelector(`.item-folder[data-folder-id="${CSS.escape(id)}"]`);
                if (f) FI.setFolderOpen(f, true);
            });
            FI.applyFolderColors(host);
            FI.applySearch(panelFor(roomId));
            host.dataset.directoryLoaded = "true";
            return true;
        } catch { return false; }
    }

    FI.panelFor = panelFor;
    FI.treeHostFor = treeHostFor;
    FI.roomIdFromEvent = roomIdFromEvent;
    FI.closeDialog = closeDialog;
    FI.postForm = postForm;
    FI.postJson = postJson;
    FI.refreshPanel = refreshPanel;
})();
