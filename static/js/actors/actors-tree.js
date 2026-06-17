



(() => {
    const FI = (window.GravewrightActorsInternals = window.GravewrightActorsInternals || {});

    function setFolderOpen(folder, open) {
        const bodyEl = folder.querySelector(":scope > .sheet-folder-body");
        if (open) { folder.setAttribute("data-open", ""); if (bodyEl) bodyEl.hidden = false; }
        else { folder.removeAttribute("data-open"); if (bodyEl) bodyEl.hidden = true; }
    }

    
    
    function applyFolderColors(scope) {
        (scope || document).querySelectorAll(".actor-folder[data-folder-color]").forEach((f) => {
            const c = f.dataset.folderColor;
            if (c) f.style.setProperty("--folder-color", c);
            else f.style.removeProperty("--folder-color");
        });
    }

    
    function applySearch(panel) {
        if (!panel) return;
        const query = (panel.querySelector("[data-actor-search]")?.value || "").trim().toLowerCase();
        const host = panel.querySelector("[data-actor-tree-host]");
        if (!host) return;
        host.querySelectorAll("[data-actor-card]").forEach((card) => {
            const name = (card.querySelector("strong")?.textContent || "").toLowerCase();
            card.style.display = !query || name.includes(query) ? "" : "none";
        });
        
        host.querySelectorAll(".actor-folder").forEach((folder) => {
            const anyVisible = Array.from(folder.querySelectorAll("[data-actor-card]"))
                .some((c) => c.style.display !== "none");
            folder.style.display = query && !anyVisible ? "none" : "";
            if (query && anyVisible) setFolderOpen(folder, true);
        });
    }

    document.addEventListener("input", (event) => {
        const search = event.target.closest("[data-actor-search]");
        if (search) applySearch(search.closest("[data-actor-panel]"));
    });

    
    document.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-actor-collapse-all]");
        if (!btn) return;
        const host = btn.closest("[data-actor-panel]")?.querySelector("[data-actor-tree-host]");
        if (!host) return;
        const folders = host.querySelectorAll(".actor-folder");
        const anyOpen = Array.from(folders).some((f) => f.hasAttribute("data-open"));
        folders.forEach((f) => setFolderOpen(f, !anyOpen));
    });

    
    document.addEventListener("click", (event) => {
        const toggle = event.target.closest("[data-actor-folder-collapse]");
        if (!toggle) return;
        const folder = toggle.closest(".actor-folder");
        if (folder) setFolderOpen(folder, !folder.hasAttribute("data-open"));
    });

    
    document.addEventListener("DOMContentLoaded", () => applyFolderColors(document));

    FI.setFolderOpen = setFolderOpen;
    FI.applyFolderColors = applyFolderColors;
    FI.applySearch = applySearch;
})();
