



(() => {
    const FI = (window.GravewrightItemsInternals = window.GravewrightItemsInternals || {});

    function setFolderOpen(folder, open) {
        const bodyEl = folder.querySelector(":scope > .sheet-folder-body");
        if (open) { folder.setAttribute("data-open", ""); if (bodyEl) bodyEl.hidden = false; }
        else { folder.removeAttribute("data-open"); if (bodyEl) bodyEl.hidden = true; }
    }

    function applyFolderColors(scope) {
        (scope || document).querySelectorAll(".item-folder[data-folder-color]").forEach((f) => {
            const c = f.dataset.folderColor;
            if (c) f.style.setProperty("--folder-color", c);
            else f.style.removeProperty("--folder-color");
        });
    }

    
    function applySearch(panel) {
        if (!panel) return;
        const query = (panel.querySelector("[data-item-search]")?.value || "").trim().toLowerCase();
        const host = panel.querySelector("[data-item-tree-host]");
        if (!host) return;
        host.querySelectorAll("[data-item-card]").forEach((card) => {
            const name = (card.querySelector("strong")?.textContent || "").toLowerCase();
            card.style.display = !query || name.includes(query) ? "" : "none";
        });
        host.querySelectorAll(".item-folder").forEach((folder) => {
            const anyVisible = Array.from(folder.querySelectorAll("[data-item-card]"))
                .some((c) => c.style.display !== "none");
            folder.style.display = query && !anyVisible ? "none" : "";
            if (query && anyVisible) setFolderOpen(folder, true);
        });
    }

    document.addEventListener("input", (event) => {
        const search = event.target.closest("[data-item-search]");
        if (search) applySearch(search.closest("[data-item-panel]"));
    });

    
    document.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-item-collapse-all]");
        if (!btn) return;
        const host = btn.closest("[data-item-panel]")?.querySelector("[data-item-tree-host]");
        if (!host) return;
        const folders = host.querySelectorAll(".item-folder");
        const anyOpen = Array.from(folders).some((f) => f.hasAttribute("data-open"));
        folders.forEach((f) => setFolderOpen(f, !anyOpen));
    });

    
    document.addEventListener("click", (event) => {
        const toggle = event.target.closest("[data-item-folder-collapse]");
        if (!toggle) return;
        const folder = toggle.closest(".item-folder");
        if (folder) setFolderOpen(folder, !folder.hasAttribute("data-open"));
    });

    document.addEventListener("DOMContentLoaded", () => applyFolderColors(document));

    FI.setFolderOpen = setFolderOpen;
    FI.applyFolderColors = applyFolderColors;
    FI.applySearch = applySearch;
})();
