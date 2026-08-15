(() => {
  const configurations = new Map();

  function normalized(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function storageKey(panel, type) {
    return `gravewright.directory.${panel?.dataset.roomId || "global"}.${type}.expanded`;
  }

  function readExpanded(panel, type) {
    try { return new Set(JSON.parse(localStorage.getItem(storageKey(panel, type)) || "[]")); }
    catch (_) { return new Set(); }
  }

  function writeExpanded(panel, type, ids) {
    try { localStorage.setItem(storageKey(panel, type), JSON.stringify([...ids])); }
    catch (_) { /* Storage may be unavailable in private/embedded contexts. */ }
  }

  function createDirectory(config) {
    const folderSelector = `.${config.folderClass}`;

    function setOpen(folder, open, persist = true) {
      if (!folder) return;
      const body = folder.querySelector(":scope > .sheet-folder-body");
      const toggle = folder.querySelector(`:scope > .sheet-folder-header ${config.toggleSelector}`);
      folder.toggleAttribute("data-open", open);
      if (body) body.hidden = !open;
      if (toggle) toggle.setAttribute("aria-expanded", String(open));
      const icon = toggle?.querySelector(".sheet-folder-icon");
      icon?.classList.toggle("ph-folder", !open);
      icon?.classList.toggle("ph-folder-open", open);
      if (!persist) return;
      const panel = folder.closest(config.panelSelector);
      const ids = readExpanded(panel, config.type);
      const id = folder.dataset.folderId;
      if (id) open ? ids.add(id) : ids.delete(id);
      writeExpanded(panel, config.type, ids);
    }

    function restore(panel) {
      const host = panel?.querySelector(config.hostSelector);
      if (!host) return;
      const expanded = readExpanded(panel, config.type);
      host.querySelectorAll(folderSelector).forEach((folder) => {
        setOpen(folder, expanded.has(folder.dataset.folderId), false);
      });
    }

    function folderName(folder) {
      return normalized(folder.querySelector(":scope > .sheet-folder-header .sheet-folder-name")?.textContent);
    }

    function ownEntries(folder) {
      const body = folder.querySelector(":scope > .sheet-folder-body");
      if (!body) return [];
      return [...body.children].flatMap((child) => {
        if (child.matches(config.entrySelector)) return [child];
        if (child.matches("ul")) return [...child.children].filter((entry) => entry.matches(config.entrySelector));
        return [];
      });
    }

    function applySearch(panel) {
      if (!panel) return;
      const host = panel.querySelector(config.hostSelector);
      if (!host) return;
      const query = normalized(panel.querySelector(config.searchSelector)?.value.trim());
      if (!query) restore(panel);

      function visit(folder, revealSubtree = false) {
        const ownMatch = Boolean(query && folderName(folder).includes(query));
        const reveal = revealSubtree || ownMatch;
        let matched = ownMatch;
        ownEntries(folder).forEach((entry) => {
          const entryMatch = reveal || !query || normalized(entry.dataset.directoryName || entry.querySelector("strong")?.textContent).includes(query);
          entry.hidden = !entryMatch;
          matched ||= entryMatch;
        });
        const body = folder.querySelector(":scope > .sheet-folder-body");
        const children = body ? [...body.children].filter((child) => child.matches(folderSelector)) : [];
        children.forEach((child) => { matched = visit(child, reveal) || matched; });
        folder.hidden = Boolean(query && !matched);
        if (query && matched) setOpen(folder, true, false);
        return matched;
      }

      [...host.children].forEach((child) => {
        if (child.matches(folderSelector)) visit(child);
        else if (child.matches(config.entrySelector)) {
          child.hidden = Boolean(query && !normalized(child.dataset.directoryName || child.querySelector("strong")?.textContent).includes(query));
        } else if (child.matches("ul")) {
          [...child.children].filter((entry) => entry.matches(config.entrySelector)).forEach((entry) => {
            entry.hidden = Boolean(query && !normalized(entry.dataset.directoryName || entry.querySelector("strong")?.textContent).includes(query));
          });
        }
      });
    }

    function applyColors(scope) {
      (scope || document).querySelectorAll(`${folderSelector}[data-folder-color]`).forEach((folder) => {
        const color = folder.dataset.folderColor;
        color ? folder.style.setProperty("--folder-color", color) : folder.style.removeProperty("--folder-color");
      });
    }

    document.addEventListener("input", (event) => {
      if (event.target.closest(config.searchSelector)) applySearch(event.target.closest(config.panelSelector));
    });
    document.addEventListener("click", (event) => {
      const toggle = event.target.closest(config.toggleSelector);
      if (toggle) {
        const folder = toggle.closest(folderSelector);
        setOpen(folder, !folder?.hasAttribute("data-open"));
        return;
      }
      const collapse = event.target.closest(config.collapseSelector);
      if (!collapse) return;
      const panel = collapse.closest(config.panelSelector);
      const folders = panel?.querySelectorAll(`${config.hostSelector} ${folderSelector}`) || [];
      const expand = ![...folders].some((folder) => folder.hasAttribute("data-open"));
      folders.forEach((folder) => setOpen(folder, expand, false));
      writeExpanded(panel, config.type, expand ? [...folders].map((folder) => folder.dataset.folderId).filter(Boolean) : []);
    });

    const api = { applyColors, applySearch, restore, setOpen };
    configurations.set(config.type, api);
    return api;
  }

  window.GravewrightDirectoryTree = { create: createDirectory, get: (type) => configurations.get(type) };
})();
