// Group compendium directory packs by the folders their collections declare.

/** A pack's declared folder path; packs without a valid one stay at the top level. */
export function folderPath(pack) {
  const path = Array.isArray(pack?.folder) ? pack.folder : [];
  return path.every(name => typeof name === 'string' && name.trim()) ? path.map(name => name.trim()) : [];
}

/** Stable key used to remember which folders a member keeps open. */
export const folderKey = path => JSON.stringify(path);

/**
 * Build the directory tree from already filtered rows of `{pack, entries}`.
 * Each folder counts the entries of every pack beneath it; empty folders are
 * never created because folders exist only through the rows placed in them.
 * `accessId` is the server's permission key for the folder, when provided.
 */
export function compendiumTree(rows) {
  const branch = path => ({id: folderKey(path), name: path.at(-1) || '', path, folders: new Map(), packs: [], count: 0, accessId: ''});
  const root = branch([]);
  for (const row of rows) {
    let current = root;
    current.count += row.entries.length;
    const path = folderPath(row.pack), ids = row.pack.folderIds;
    const access = Array.isArray(ids) && ids.length === path.length && ids.every(id => typeof id === 'string' && id) ? ids : [];
    path.forEach((name, depth) => {
      if (!current.folders.has(name)) current.folders.set(name, branch([...current.path, name]));
      current = current.folders.get(name);
      current.accessId ||= access[depth] || '';
      current.count += row.entries.length;
    });
    current.packs.push(row);
  }
  return root;
}
