(() => {
  let session = null;
  let activeTarget = null;
  let expandTimer = null;
  let ghost = null;

  function clearTarget() {
    if (activeTarget) {
      activeTarget.classList.remove("directory-drop-target", "directory-drop-invalid");
      activeTarget.removeAttribute("data-directory-drop-active");
    }
    activeTarget = null;
    window.clearTimeout(expandTimer);
    expandTimer = null;
  }

  function removeGhost() {
    ghost?.remove();
    ghost = null;
  }

  function start({ event, source, panel, kind, id, label, count = 0 }) {
    end();
    session = { source, panel, kind, id };
    source.classList.add("directory-drag-source");
    panel?.setAttribute("data-directory-dragging", kind);

    ghost = document.createElement("div");
    ghost.className = "directory-drag-ghost";
    const icon = document.createElement("i");
    icon.className = kind === "folder" ? "ph ph-folder" : "ph ph-file";
    icon.setAttribute("aria-hidden", "true");
    const text = document.createElement("span");
    text.textContent = label || "";
    ghost.append(icon, text);
    if (Number(count) > 0) {
      const badge = document.createElement("small");
      badge.textContent = String(count);
      ghost.append(badge);
    }
    document.body.appendChild(ghost);
    try { event.dataTransfer.setDragImage(ghost, 18, 18); } catch (_) { /* Optional browser API. */ }
  }

  function end() {
    clearTarget();
    session?.source?.classList.remove("directory-drag-source");
    session?.panel?.removeAttribute("data-directory-dragging");
    session = null;
    removeGhost();
  }

  function canDrop({ source, kind, targetFolder, targetFolderId = "", folderSelector }) {
    if (!source) return false;
    const sourceParentId = source.parentElement?.closest(folderSelector)?.dataset.folderId || "";
    if (kind !== "folder") return sourceParentId !== targetFolderId;
    const sourceId = source.dataset.folderId || "";
    if (sourceId === targetFolderId) return false;
    if (targetFolder && (targetFolder === source || source.contains(targetFolder))) return false;
    return sourceParentId !== targetFolderId;
  }

  function mark(event, { target, valid, folder, type, visual = true }) {
    if (!target) { clearTarget(); return false; }
    if (activeTarget !== target) clearTarget();
    activeTarget = target;
    if (visual) {
      target.classList.toggle("directory-drop-target", valid);
      target.classList.toggle("directory-drop-invalid", !valid);
      target.dataset.directoryDropActive = valid ? "valid" : "invalid";
    }
    event.dataTransfer.dropEffect = valid ? "move" : "none";
    if (!valid) return false;
    event.preventDefault();

    if (folder && !folder.hasAttribute("data-open") && !expandTimer) {
      expandTimer = window.setTimeout(() => {
        window.GravewrightDirectoryTree?.get(type)?.setOpen(folder, true);
        expandTimer = null;
      }, 650);
    }
    autoScroll(event, session?.panel);
    return true;
  }

  function autoScroll(event, panel) {
    const scroller = panel?.querySelector(".actor-tree, .item-tree, .journal-list-area, .journal-list") || panel;
    if (!scroller) return;
    const rect = scroller.getBoundingClientRect();
    const edge = Math.min(54, rect.height * 0.18);
    if (event.clientY < rect.top + edge) scroller.scrollBy({ top: -12, behavior: "auto" });
    else if (event.clientY > rect.bottom - edge) scroller.scrollBy({ top: 12, behavior: "auto" });
  }

  document.addEventListener("dragleave", (event) => {
    if (!event.relatedTarget) clearTarget();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") end();
  });
  window.addEventListener("blur", end);

  window.GravewrightDirectoryDrag = { canDrop, clearTarget, end, mark, start };
})();
