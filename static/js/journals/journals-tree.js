



(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});

  function applyJournalFolderColors(scope) {
    (scope || document).querySelectorAll(".journal-folder[data-folder-color]").forEach((f) => {
      const c = f.dataset.folderColor;
      if (c) f.style.setProperty("--folder-color", c);
      else f.style.removeProperty("--folder-color");
    });
  }

  function setJournalFolderOpen(folder, open) {
    const body = folder.querySelector(":scope > .sheet-folder-body");
    if (open) {
      folder.setAttribute("data-open", "");
      if (body) body.hidden = false;
    } else {
      folder.removeAttribute("data-open");
      if (body) body.hidden = true;
    }
  }

  function applyJournalSearch(panel) {
    if (!panel) return;
    const query = (panel.querySelector("[data-journal-search]")?.value || "").trim().toLowerCase();
    const host = panel.querySelector("[data-journal-tree-host]");
    if (!host) return;
    host.querySelectorAll(".journal-card").forEach((card) => {
      const name = (card.querySelector("strong")?.textContent || "").toLowerCase();
      card.style.display = !query || name.includes(query) ? "" : "none";
    });
    host.querySelectorAll(".journal-folder").forEach((folder) => {
      const anyVisible = Array.from(folder.querySelectorAll(".journal-card")).some(
        (c) => c.style.display !== "none",
      );
      folder.style.display = query && !anyVisible ? "none" : "";
      if (query && anyVisible) setJournalFolderOpen(folder, true);
    });
  }

  document.addEventListener("input", (event) => {
    const search = event.target.closest("[data-journal-search]");
    if (search) applyJournalSearch(search.closest("[data-journal-panel]"));
  });

  document.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-journal-collapse-all]");
    if (!btn) return;
    const host = btn.closest("[data-journal-panel]")?.querySelector("[data-journal-tree-host]");
    if (!host) return;
    const folders = host.querySelectorAll(".journal-folder");
    const anyOpen = Array.from(folders).some((f) => f.hasAttribute("data-open"));
    folders.forEach((f) => setJournalFolderOpen(f, !anyOpen));
  });

  FI.applyJournalFolderColors = applyJournalFolderColors;
  FI.setJournalFolderOpen = setJournalFolderOpen;
  FI.applyJournalSearch = applyJournalSearch;
})();
