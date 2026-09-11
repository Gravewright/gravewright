// gravewright/maps/frontend/directory.js
function normalized(value) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase().trim();
}
function directoryView(folders, entries, search) {
  const query = normalized(search), visibleFolders = /* @__PURE__ */ new Set(), visibleEntries = /* @__PURE__ */ new Set();
  const byId = new Map(folders.map((folder) => [folder.id, folder]));
  function ancestors(id) {
    const result = [];
    while (id && byId.has(id) && !result.includes(id)) {
      result.push(id);
      id = byId.get(id)?.parentId;
    }
    return result;
  }
  const matchingFolders = new Set(folders.filter((folder) => normalized(folder.name).includes(query)).map((folder) => folder.id));
  for (const folder of folders)
    if (!query || ancestors(folder.id).some((id) => matchingFolders.has(id)))
      for (const id of ancestors(folder.id))
        visibleFolders.add(id);
  for (const entry of entries) {
    const parents = ancestors(entry.folderId);
    if (!query || normalized(entry.name).includes(query) || parents.some((id) => matchingFolders.has(id))) {
      visibleEntries.add(entry.id);
      for (const id of parents)
        visibleFolders.add(id);
    }
  }
  const counts = new Map(folders.map((folder) => [folder.id, 0]));
  for (const entry of entries)
    for (const id of ancestors(entry.folderId))
      counts.set(id, (counts.get(id) ?? 0) + 1);
  return { visibleFolders, visibleEntries, counts };
}
export {
  directoryView,
  normalized
};
