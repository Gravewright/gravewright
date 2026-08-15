




(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});
  const csrfToken = FI.csrfToken;
  const journalPanelFor = FI.journalPanelFor;
  const roomIdForJournalEl = FI.roomIdForJournalEl;
  const refreshJournalPanel = FI.refreshJournalPanel;
  const postJournal = FI.postJournal;
  const flushEditors = FI.flushEditors;


  function initPanel(panel) {
    panel.addEventListener("click", (event) => {
      if (event.target.closest(".sheet-folder-drag-handle")) return;

      const selectButton = event.target.closest("[data-journal-select]");
      if (selectButton) {
        document.dispatchEvent(new CustomEvent("vtt:open-journal", {
          detail: { journalId: selectButton.dataset.journalSelect },
        }));
        return;
      }

      const createBtn = event.target.closest("[data-journal-create-open]");
      if (createBtn) {
        document.dispatchEvent(new CustomEvent("vtt:open-journal-create", {
          detail: {
            campaignId: createBtn.dataset.campaignId,
            folderId: createBtn.dataset.folderId || "",
          },
        }));
        return;
      }

      const folderCreateBtn = event.target.closest("[data-journal-folder-create]");
      if (folderCreateBtn) {
        window.GravewrightContextMenuInternals?.openFolderCreateModal({
          kind: "journal",
          campaignId: folderCreateBtn.dataset.campaignId,
          parentId: folderCreateBtn.dataset.parentId || "",
        });
        return;
      }

      // Folder expansion is handled by the shared directory tree controller.
    });
  }



  let folderDragFromHandle = false;
  let activeDragZone = null;
  let directoryDrag = null;

  function setActiveDragZone(el, cls) {
    if (activeDragZone && activeDragZone.el !== el) {
      activeDragZone.el.classList.remove(activeDragZone.cls);
    }
    activeDragZone = el ? { el, cls } : null;
    if (el) el.classList.add(cls);
  }

  function isGmJournalArea(el) {
    return el.closest(".journal-list-area")?.dataset.isGm === "true";
  }

  document.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".journal-list-area")) {
      folderDragFromHandle = !!e.target.closest(".sheet-folder-drag-handle");
    }
  });

  document.addEventListener("dragstart", (e) => {
    const listArea = e.target.closest("[data-journal-panel]");
    if (!listArea) return;
    if (!isGmJournalArea(listArea)) { e.preventDefault(); return; }

    const card = e.target.closest(".journal-card[data-journal-id]");
    if (card) {
      e.dataTransfer.setData("vtt/journal", card.dataset.journalId);
      e.dataTransfer.effectAllowed = "move";
      card.classList.add("is-dragging");
      directoryDrag = { kind: "journal", id: card.dataset.journalId, source: card };
      window.GravewrightDirectoryDrag?.start({
        event: e, source: card, panel: listArea, kind: "journal", id: card.dataset.journalId,
        label: card.dataset.directoryName || card.querySelector("strong")?.textContent?.trim() || "",
      });
      folderDragFromHandle = false;
      return;
    }

    const folder = e.target.closest(".journal-folder[data-folder-id]");
    if (folder) {
      if (!folderDragFromHandle) { e.preventDefault(); folderDragFromHandle = false; return; }
      e.dataTransfer.setData("vtt/journal-folder", folder.dataset.folderId);
      e.dataTransfer.effectAllowed = "move";
      folder.classList.add("is-dragging");
      directoryDrag = { kind: "folder", id: folder.dataset.folderId, source: folder };
      window.GravewrightDirectoryDrag?.start({
        event: e, source: folder, panel: listArea, kind: "folder", id: folder.dataset.folderId,
        label: folder.querySelector(":scope > .sheet-folder-header .sheet-folder-name")?.textContent?.trim() || "",
        count: folder.querySelectorAll(".journal-card[data-journal-id]").length,
      });
      folderDragFromHandle = false;
    }
  });

  document.addEventListener("dragend", (e) => {
    e.target.closest(".journal-card[data-journal-id]")?.classList.remove("is-dragging");
    e.target.closest(".journal-folder[data-folder-id]")?.classList.remove("is-dragging");
    setActiveDragZone(null);
    window.GravewrightDirectoryDrag?.end();
    directoryDrag = null;
  });

  document.addEventListener("dragover", (e) => {
    const listArea = e.target.closest("[data-journal-panel]");
    if (!listArea || !isGmJournalArea(listArea)) return;
    const folderHeader = e.target.closest(".journal-folder .sheet-folder-header");
    const folderBody = e.target.closest(".journal-folder .sheet-folder-body");
    const folder = (folderHeader || folderBody)?.closest(".journal-folder[data-folder-id]") || null;
    const target = folderHeader || folderBody || listArea;
    const targetFolderId = folder?.dataset.folderId || "";
    const valid = directoryDrag && (window.GravewrightDirectoryDrag?.canDrop({
      source: directoryDrag.source, kind: directoryDrag.kind, targetFolder: folder, targetFolderId,
      folderSelector: ".journal-folder",
    }) ?? true);
    setActiveDragZone(null);
    if (window.GravewrightDirectoryDrag) {
      window.GravewrightDirectoryDrag.mark(e, {
        target, valid, folder, type: "journals", visual: Boolean(folder),
      });
    } else if (valid) {
      e.preventDefault(); e.dataTransfer.dropEffect = "move";
      setActiveDragZone(target, folder ? "drag-over" : "drag-over-root");
    }
  });

  document.addEventListener("dragleave", (e) => {
    if (!e.relatedTarget || !e.relatedTarget.closest("[data-journal-panel]")) {
      setActiveDragZone(null);
      window.GravewrightDirectoryDrag?.clearTarget();
    }
  });

  document.addEventListener("drop", async (e) => {
    const listArea = e.target.closest("[data-journal-panel]");
    if (!listArea || !isGmJournalArea(listArea)) return;
    e.preventDefault();
    setActiveDragZone(null);

    const csrf = csrfToken();
    const journalId = e.dataTransfer.getData("vtt/journal");
    const droppedFolderId = e.dataTransfer.getData("vtt/journal-folder");

    let targetFolderId = "";
    const folderHeader = e.target.closest(".journal-folder .sheet-folder-header");
    const folderBody = e.target.closest(".journal-folder .sheet-folder-body");
    if (folderHeader) {
      targetFolderId = folderHeader.closest(".journal-folder[data-folder-id]")?.dataset.folderId || "";
    } else if (folderBody) {
      targetFolderId = folderBody.closest(".journal-folder[data-folder-id]")?.dataset.folderId || "";
    }

    const targetFolder = (folderHeader || folderBody)?.closest(".journal-folder[data-folder-id]") || null;
    const valid = directoryDrag && (window.GravewrightDirectoryDrag?.canDrop({
      source: directoryDrag.source, kind: directoryDrag.kind, targetFolder, targetFolderId,
      folderSelector: ".journal-folder",
    }) ?? true);
    if (!valid) return;
    window.GravewrightDirectoryDrag?.end();
    directoryDrag = null;

    const roomId = roomIdForJournalEl(listArea);
    if (journalId) {
      const res = await fetch("/game/journal/move", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
        body: new URLSearchParams({ csrf_token: csrf, journal_id: journalId, folder_id: targetFolderId }),
        credentials: "same-origin",
      });
      if (res.ok) refreshJournalPanel(roomId);
      return;
    }

    if (droppedFolderId) {
      if (droppedFolderId === targetFolderId) return;
      const res = await fetch("/game/journal/folder/move", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
        body: new URLSearchParams({ csrf_token: csrf, folder_id: droppedFolderId, parent_id: targetFolderId }),
        credentials: "same-origin",
      });
      if (res.ok) refreshJournalPanel(roomId);
    }
  });


  const openBoardCard = (card) => {
    document.dispatchEvent(new CustomEvent("vtt:open-journal", {
      detail: { journalId: card.dataset.journalSelect },
    }));
  };

  document.addEventListener("click", (event) => {
    const card = event.target.closest(".board-card[data-journal-select]");
    if (card) openBoardCard(card);
  });

  // The cards carry role="button"; keyboard has to open them as one.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const card = event.target.closest?.(".board-card[data-journal-select]");
    if (!card) return;
    event.preventDefault();
    openBoardCard(card);
  });


  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-journal-folder-create-form]");
    if (!form) return;
    event.preventDefault();
    const roomId = form.dataset.roomId || "";
    const name = (form.querySelector("input[name='name']")?.value || "").trim();
    if (!name) return;
    const color = form.querySelector("[data-journal-folder-color-text]")?.value || "";
    const parentId = form.querySelector("input[name='parent_id']")?.value || "";
    const res = await postJournal("/game/journal/folder", {
      campaign_id: roomId, parent_id: parentId, name, color,
    });
    if (res.ok) {
      form.querySelector("input[name='name']").value = "";
      form.closest("[data-modal-window]")?.querySelector("[data-modal-close]")?.click();
      refreshJournalPanel(roomId);
    }
  });


  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-journal-create-form]");
    if (!form) return;
    event.preventDefault();
    flushEditors(form);
    const roomId = form.querySelector("input[name='campaign_id']")?.value || "";
    const res = await fetch(form.action, {
      method: "POST",
      body: new URLSearchParams(new FormData(form)),
      credentials: "same-origin",
      headers: { Accept: "application/json", "Content-Type": "application/x-www-form-urlencoded" },
    });
    if (!res.ok) return;
    const data = await res.json().catch(() => ({}));
    form.closest("[data-modal-window]")?.querySelector("[data-modal-close]")?.click();
    if (roomId) refreshJournalPanel(roomId);
    if (data.journal_id) {
      document.dispatchEvent(new CustomEvent("vtt:open-journal", {
        detail: { journalId: data.journal_id, edit: true },
      }));
    }
  });


  document.addEventListener("input", (event) => {
    const pick = event.target.closest("[data-journal-folder-color-pick]");
    if (pick) {
      const text = pick.closest(".dialog-color-row")?.querySelector("[data-journal-folder-color-text]");
      if (text) text.value = pick.value;
      return;
    }
    const text = event.target.closest("[data-journal-folder-color-text]");
    if (text && /^#[0-9a-fA-F]{6}$/.test(text.value)) {
      const picker = text.closest(".dialog-color-row")?.querySelector("[data-journal-folder-color-pick]");
      if (picker) picker.value = text.value;
    }
  });


  const PANEL_REFRESH_EVENTS = new Set([
    "journal.created",
    "journal.deleted",


    "journal.updated",
    "journal.access_changed",
    "handout.access_changed",
  ]);
  document.addEventListener("vtt:transport-event", (event) => {
    const env = event.detail || {};
    if (!PANEL_REFRESH_EVENTS.has(env.event)) return;
    const roomId = env.payload?.room_id;
    if (roomId && journalPanelFor(roomId)) refreshJournalPanel(roomId);
  });

  document.addEventListener("vtt:ws-open", () => {
    document.querySelectorAll("[data-journal-panel][data-room-id]").forEach((panel) => {
      if (panel.dataset.roomId) refreshJournalPanel(panel.dataset.roomId);
    });
  });

  FI.initPanel = initPanel;
})();
