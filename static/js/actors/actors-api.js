




(() => {
    const FI = (window.GravewrightActorsInternals = window.GravewrightActorsInternals || {});

    function csrf() {
        return window.csrfToken();
    }

    function panelFor(roomId) {
        return document.querySelector(
            `[data-actor-panel][data-room-id="${CSS.escape(roomId)}"]`,
        );
    }

    function treeHostFor(roomId) {
        return panelFor(roomId)?.querySelector("[data-actor-tree-host]");
    }

    function roomIdFromEvent(target) {
        return target?.closest?.("[data-actor-panel]")?.dataset.roomId || "";
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
        if (!host) return;
        try {
            const res = await fetch(`/game/actors/panel/${encodeURIComponent(roomId)}`, {
                credentials: "same-origin",
                headers: { Accept: "text/html" },
            });
            if (!res.ok) return;
            const html = await res.text();
            const collapsed = new Set(
                Array.from(host.querySelectorAll(".actor-folder:not([data-open])"))
                    .map((f) => f.dataset.folderId),
            );
            host.innerHTML = html;
            collapsed.forEach((id) => {
                const f = host.querySelector(`.actor-folder[data-folder-id="${CSS.escape(id)}"]`);
                if (f) FI.setFolderOpen(f, false);
            });
            FI.applyFolderColors(host);
            FI.applySearch(panelFor(roomId));
        } catch {  }
    }

    FI.panelFor = panelFor;
    FI.treeHostFor = treeHostFor;
    FI.roomIdFromEvent = roomIdFromEvent;
    FI.closeDialog = closeDialog;
    FI.postForm = postForm;
    FI.postJson = postJson;
    FI.refreshPanel = refreshPanel;
})();
