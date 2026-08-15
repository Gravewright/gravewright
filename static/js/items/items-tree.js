(() => {
  const FI = (window.GravewrightItemsInternals = window.GravewrightItemsInternals || {});
  const tree = window.GravewrightDirectoryTree.create({
    type: "items", panelSelector: "[data-item-panel]", hostSelector: "[data-item-tree-host]",
    searchSelector: "[data-item-search]", collapseSelector: "[data-item-collapse-all]",
    toggleSelector: "[data-item-folder-collapse]", folderClass: "item-folder", entrySelector: "[data-item-card]",
  });
  document.addEventListener("DOMContentLoaded", () => { tree.applyColors(document); document.querySelectorAll("[data-item-panel]").forEach(tree.restore); });
  FI.setFolderOpen = tree.setOpen; FI.applyFolderColors = tree.applyColors; FI.applySearch = tree.applySearch;
})();
