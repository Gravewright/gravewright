




(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});
  const csrfToken = FI.csrfToken;
  const journalPanelFor = FI.journalPanelFor;
  const roomIdForJournalEl = FI.roomIdForJournalEl;
  const refreshJournalPanel = FI.refreshJournalPanel;
  const postJournal = FI.postJournal;
  const flushEditors = FI.flushEditors;

  
  async function promptCreateFolder(button) {
    const campaignId = button.dataset.campaignId;
    const parentId = button.dataset.parentId || "";
    if (!campaignId) return;
    const name = window.prompt(parentId ? "Nome da subpasta" : "Nome da nova pasta");
    if (!name || !name.trim()) return;
    const res = await postJournal("/game/journal/folder", {
      campaign_id: campaignId, parent_id: parentId, name: name.trim(),
    });
    if (res.ok) refreshJournalPanel(campaignId);
  }

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
        promptCreateFolder(folderCreateBtn);
        return;
      }

      const folderCollapse = event.target.closest("[data-journal-folder-collapse]");
      if (folderCollapse) {
        const folder = folderCollapse.closest("[data-journal-folder]");
        if (folder) {
          if (folder.hasAttribute("data-open")) {
            folder.removeAttribute("data-open");
            const body = folder.querySelector(":scope > .sheet-folder-body");
            if (body) body.hidden = true;
          } else {
            folder.setAttribute("data-open", "");
            const body = folder.querySelector(":scope > .sheet-folder-body");
            if (body) body.hidden = false;
          }
        }
      }
    });
  }

  

  let folderDragFromHandle = false;
  let activeDragZone = null;

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
    const listArea = e.target.closest(".journal-list-area");
    if (!listArea) return;
    if (!isGmJournalArea(listArea)) { e.preventDefault(); return; }

    const card = e.target.closest(".journal-card[data-journal-id]");
    if (card) {
      e.dataTransfer.setData("vtt/journal", card.dataset.journalId);
      e.dataTransfer.effectAllowed = "move";
      card.classList.add("is-dragging");
      folderDragFromHandle = false;
      return;
    }

    const folder = e.target.closest(".journal-folder[data-folder-id]");
    if (folder) {
      if (!folderDragFromHandle) { e.preventDefault(); folderDragFromHandle = false; return; }
      e.dataTransfer.setData("vtt/journal-folder", folder.dataset.folderId);
      e.dataTransfer.effectAllowed = "move";
      folder.classList.add("is-dragging");
      folderDragFromHandle = false;
    }
  });

  document.addEventListener("dragend", (e) => {
    e.target.closest(".journal-card[data-journal-id]")?.classList.remove("is-dragging");
    e.target.closest(".journal-folder[data-folder-id]")?.classList.remove("is-dragging");
    setActiveDragZone(null);
  });

  document.addEventListener("dragover", (e) => {
    const listArea = e.target.closest(".journal-list-area");
    if (!listArea || !isGmJournalArea(listArea)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";

    const rootDropZone = e.target.closest("[data-journal-root-drop]");
    const folderHeader = e.target.closest(".journal-folder .sheet-folder-header");
    if (folderHeader) { setActiveDragZone(folderHeader, "drag-over"); return; }
    const folderBody = e.target.closest(".journal-folder .sheet-folder-body");
    if (folderBody) { setActiveDragZone(folderBody, "drag-over"); return; }
    if (rootDropZone) { setActiveDragZone(rootDropZone, "drag-over-root"); return; }
    setActiveDragZone(listArea, "drag-over-root");
  });

  document.addEventListener("dragleave", (e) => {
    if (!e.relatedTarget || !e.relatedTarget.closest(".journal-list-area")) {
      setActiveDragZone(null);
    }
  });

  document.addEventListener("drop", async (e) => {
    const listArea = e.target.closest(".journal-list-area");
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

  
  document.addEventListener("click", (event) => {
    const card = event.target.closest(".quest-card[data-journal-select]");
    if (!card) return;
    document.dispatchEvent(new CustomEvent("vtt:open-journal", {
      detail: { journalId: card.dataset.journalSelect },
    }));
  });

  
  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-journal-folder-create-form]");
    if (!form) return;
    event.preventDefault();
    const roomId = form.dataset.roomId || "";
    const name = (form.querySelector("input[name='name']")?.value || "").trim();
    if (!name) return;
    const color = form.querySelector("[data-journal-folder-color-text]")?.value || "";
    const res = await postJournal("/game/journal/folder", { campaign_id: roomId, name, color });
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
      document.dispatchEvent(new CustomEvent("vtt:open-journal", { detail: { journalId: data.journal_id } }));
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
    "journal.access_changed", 
  ]);
  document.addEventListener("vtt:transport-event", (event) => {
    const env = event.detail || {};
    if (!PANEL_REFRESH_EVENTS.has(env.event)) return;
    const roomId = env.payload?.room_id;
    if (roomId && journalPanelFor(roomId)) refreshJournalPanel(roomId);
  });

  FI.initPanel = initPanel;
})();
