(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});
  const tree = window.GravewrightDirectoryTree.create({
    type: "journals", panelSelector: "[data-journal-panel]", hostSelector: "[data-journal-tree-host]",
    searchSelector: "[data-journal-search]", collapseSelector: "[data-journal-collapse-all]",
    toggleSelector: "[data-journal-folder-collapse]", folderClass: "journal-folder", entrySelector: ".journal-card",
  });
  document.addEventListener("DOMContentLoaded", () => { tree.applyColors(document); document.querySelectorAll("[data-journal-panel]").forEach(tree.restore); });
  FI.applyJournalFolderColors = tree.applyColors; FI.setJournalFolderOpen = tree.setOpen; FI.applyJournalSearch = tree.applySearch;
})();
