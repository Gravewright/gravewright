





(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});

    const menu = document.getElementById("ctx-menu");
    const inner = menu?.querySelector(".ctx-menu-inner");

    const body = document.body;

    function label(key) {
        return body.dataset[key] || key;
    }

    function getCsrf() {
        return body.dataset.presenceCsrfToken || "";
    }

    

    function closeMenu() {
        menu.hidden = true;
        inner.innerHTML = "";
    }

    function showMenu(x, y, items) {
        inner.innerHTML = "";

        for (const item of items) {
            if (item.type === "sep") {
                const sep = document.createElement("hr");
                sep.className = "ctx-sep";
                inner.appendChild(sep);
                continue;
            }

            if (item.type === "label") {
                const el = document.createElement("p");
                el.className = "ctx-section-label";
                el.textContent = item.text;
                inner.appendChild(el);
                continue;
            }

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "ctx-item"
                + (item.danger ? " ctx-item--danger" : "")
                + (item.checked ? " ctx-item--checked" : "")
                + (item.small ? " ctx-item--small" : "");
            btn.textContent = item.text;
            if (item.disabled) btn.disabled = true;
            btn.addEventListener("click", (ev) => {
                ev.stopPropagation();
                closeMenu();
                item.action?.();
            });
            inner.appendChild(btn);
        }

        menu.hidden = false;

        
        const mw = menu.offsetWidth || 180;
        const mh = menu.offsetHeight || 100;
        const vw = window.innerWidth;
        const vh = window.innerHeight;

        menu.style.left = Math.min(x, vw - mw - 4) + "px";
        menu.style.top = Math.min(y, vh - mh - 4) + "px";
    }

    
    
    FI.label = label;
    FI.getCsrf = getCsrf;
    FI.closeMenu = closeMenu;
    FI.showMenu = showMenu;

    if (!menu || !inner) return;

    

    document.addEventListener("contextmenu", (e) => {
        const itemFolderHeader = e.target.closest("[data-item-panel] .sheet-folder-header");
        if (itemFolderHeader) {
            const folderEl = itemFolderHeader.closest(".item-folder[data-folder-id]");
            if (folderEl && folderEl.closest("[data-item-panel]")?.dataset.isGm === "true") {
                e.preventDefault();
                FI.openItemFolderMenu(e, folderEl);
                return;
            }
        }

        const itemCard = e.target.closest(".item-card[data-item-open]");
        if (itemCard) {
            e.preventDefault();
            FI.openItemMenu(e, itemCard);
            return;
        }

        const actorFolderHeader = e.target.closest("[data-actor-panel] .sheet-folder-header");
        if (actorFolderHeader) {
            const folderEl = actorFolderHeader.closest(".actor-folder[data-folder-id]");
            if (folderEl && folderEl.closest("[data-actor-panel]")?.dataset.isGm === "true") {
                e.preventDefault();
                FI.openActorFolderMenu(e, folderEl);
                return;
            }
        }

        const actorCard = e.target.closest(".actor-card[data-actor-open]");
        if (actorCard) {
            e.preventDefault();
            FI.openActorMenu(e, actorCard);
            return;
        }

        const journalCard = e.target.closest(".journal-card[data-journal-select]");
        if (journalCard) {
            e.preventDefault();
            FI.openJournalMenu(e, journalCard);
            return;
        }
    });

    document.addEventListener("click", (e) => {
        if (!menu.hidden && !menu.contains(e.target)) {
            closeMenu();
        }
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !menu.hidden) {
            closeMenu();
        }
    });

    window.addEventListener("scroll", closeMenu, { passive: true });
    window.addEventListener("resize", closeMenu, { passive: true });

    
    
    document.addEventListener("vtt:token-contextmenu", (e) => FI.openTokenMenu(e));
    document.addEventListener("vtt:measure-contextmenu", (e) => FI.openMeasureMenu?.(e));
})();
