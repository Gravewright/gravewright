(() => {
  const FI = (window.GravewrightActorsInternals = window.GravewrightActorsInternals || {});
  const tree = window.GravewrightDirectoryTree.create({
    type: "actors", panelSelector: "[data-actor-panel]", hostSelector: "[data-actor-tree-host]",
    searchSelector: "[data-actor-search]", collapseSelector: "[data-actor-collapse-all]",
    toggleSelector: "[data-actor-folder-collapse]", folderClass: "actor-folder", entrySelector: "[data-actor-card]",
  });
  document.addEventListener("DOMContentLoaded", () => { tree.applyColors(document); document.querySelectorAll("[data-actor-panel]").forEach(tree.restore); });
  FI.setFolderOpen = tree.setOpen; FI.applyFolderColors = tree.applyColors; FI.applySearch = tree.applySearch;
})();
