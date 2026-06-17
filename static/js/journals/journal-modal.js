





(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});
  const csrfToken = FI.csrfToken;
  const boardPost = FI.boardPost;
  const applyJournalFolderColors = FI.applyJournalFolderColors;
  const editors = FI.editors;
  const initRichTextIn = FI.initRichTextIn;
  const renderMarkdownIn = FI.renderMarkdownIn;
  const mountBlockEditorsIn = FI.mountBlockEditorsIn;
  const mountDocReadersIn = FI.mountDocReadersIn;
  const destroyBlockEditorsIn = FI.destroyBlockEditorsIn;
  const initQuestEditors = FI.initQuestEditors;
  const initImageUpload = FI.initImageUpload;
  const flushEditors = FI.flushEditors;
  const autosaveJournal = FI.autosaveJournal;
  const scheduleAutosave = FI.scheduleAutosave;
  const initPanel = FI.initPanel;

  const initialized = new WeakSet();

  

  function initBoardAdmin(modal) {
    const admin = modal.querySelector("[data-board-admin]");
    if (!admin) return;
    const boardId = admin.dataset.boardId;

    const refresh = () => reloadJournalModal(boardId, "editor");

    admin.querySelector("[data-board-add-quest]")?.addEventListener("click", async () => {
      const select = admin.querySelector("[data-board-quest-select]");
      const questId = select?.value;
      if (!questId) return;
      if (await boardPost("/game/journal/board/add", { board_id: boardId, quest_id: questId })) refresh();
    });

    admin.addEventListener("click", async (event) => {
      const entry = event.target.closest("[data-board-entry]");
      if (!entry) return;
      const questId = entry.dataset.boardEntry;

      if (event.target.closest("[data-board-remove]")) {
        if (await boardPost("/game/journal/board/remove", { board_id: boardId, quest_id: questId })) refresh();
        return;
      }
      const pinBtn = event.target.closest("[data-board-pin]");
      if (pinBtn) {
        if (await boardPost("/game/journal/board/pin", { board_id: boardId, quest_id: questId, pinned: pinBtn.dataset.boardPin }))
          refresh();
        return;
      }
      const moveBtn = event.target.closest("[data-board-move]");
      if (moveBtn) {
        const list = admin.querySelector("[data-board-entries]");
        const rows = Array.from(list.querySelectorAll("[data-board-entry]"));
        const index = rows.indexOf(entry);
        const target = moveBtn.dataset.boardMove === "up" ? index - 1 : index + 1;
        if (target < 0 || target >= rows.length) return;
        const ordered = rows.map((r) => r.dataset.boardEntry);
        [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
        const params = new URLSearchParams({ csrf_token: csrfToken(), board_id: boardId });
        ordered.forEach((id) => params.append("quest_ids", id));
        const res = await fetch("/game/journal/board/reorder", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
          body: params,
          credentials: "same-origin",
        });
        if (res.ok) refresh();
      }
    });
  }

  

  function setJournalView(modal, view) {
    modal.querySelectorAll("[data-journal-view]").forEach((el) => {
      el.hidden = el.dataset.journalView !== view;
    });
    if (view === "editor") {
      
      modal.querySelectorAll("[data-journal-editor] [data-journal-rich-text]").forEach((t) => {
        editors.get(t)?.codemirror.refresh();
      });
    }
  }

  function initJournalModal(modal) {
    if (initialized.has(modal)) return;
    initialized.add(modal);
    initRichTextIn(modal);
    renderMarkdownIn(modal);
    mountBlockEditorsIn(modal);
    mountDocReadersIn(modal);
    initQuestEditors(modal);
    initImageUpload(modal);
    initBoardAdmin(modal);
    syncCreateTypeFields(modal);

    const editForm = modal.querySelector("[data-journal-editor]");
    if (editForm) {
      
      editForm.addEventListener("change", () => scheduleAutosave(editForm));
    }

    
    modal.addEventListener("click", (event) => {
      if (event.target.closest("[data-journal-edit-toggle]")) {
        setJournalView(modal, "editor");
      } else if (event.target.closest("[data-journal-read-toggle]")) {
        if (editForm) autosaveJournal(editForm);
        reloadJournalModal(modal.dataset.journalId || "");
      }
    });

    modal.addEventListener("submit", (event) => {
      const form = event.target.closest("form");
      if (form) flushEditors(form);
      
      if (form && form.matches("[data-journal-editor]")) {
        event.preventDefault();
        scheduleAutosave(editForm, true);
      }
    });
  }

  async function reloadJournalModal(journalId, keepView) {
    const modal = document.querySelector(`[data-modal-id="journal-${CSS.escape(journalId)}"]`);
    if (!modal) return;
    try {
      const res = await fetch(`/game/journal/modal/${encodeURIComponent(journalId)}`, {
        credentials: "same-origin",
        headers: { Accept: "text/html" },
      });
      if (!res.ok) return;
      const html = (await res.text()).trim();
      const template = document.createElement("template");
      template.innerHTML = html;
      const next = template.content.querySelector("[data-modal-window]");
      if (!next) return;
      next.hidden = false;
      destroyBlockEditorsIn(modal);
      modal.replaceWith(next);
      initJournalModal(next);
      
      if (keepView === "editor" && next.querySelector("[data-journal-editor]")) {
        setJournalView(next, "editor");
      }
    } catch {
      
    }
  }

  function isEditorVisible(modal) {
    return !!modal.querySelector('[data-journal-view="editor"]:not([hidden])');
  }

  function reloadOpenQuestBoardsForCampaign(campaignId, keepEditor = true) {
    if (!campaignId) return;
    document
      .querySelectorAll(
        `[data-journal-type="quest_board"][data-journal-campaign="${CSS.escape(campaignId)}"]`,
      )
      .forEach((modal) => {
        const boardId = modal.dataset.journalId;
        if (boardId) reloadJournalModal(boardId, keepEditor && isEditorVisible(modal) ? "editor" : undefined);
      });
  }

  function syncCreateTypeFields(modal) {
    const typeSelect = modal.querySelector("[data-journal-create-type]");
    if (!typeSelect) return;
    const update = () => {
      modal.querySelectorAll("[data-journal-type-fields]").forEach((block) => {
        const visible = block.dataset.journalTypeFields === typeSelect.value;
        block.hidden = !visible;
        if (visible) {
          
          block.querySelectorAll("[data-journal-rich-text]").forEach((textarea) => {
            const editor = editors.get(textarea);
            if (editor) editor.codemirror.refresh();
          });
        }
      });
      const form = modal.querySelector("[data-journal-create-form]");
      if (form) form.dataset.journalType = typeSelect.value;
    };
    typeSelect.addEventListener("change", update);
    update();
  }

  

  const JOURNAL_EVENTS = new Set([
    "journal.updated",
    "quest.status_changed",
    "quest.objective_updated",
    "quest_board.updated",
  ]);

  document.addEventListener("vtt:transport-event", (event) => {
    const envelope = event.detail || {};
    const payload = envelope.payload || {};
    const journalId = payload.journal_id;
    if (!journalId) return;

    if (envelope.event === "journal.deleted") {
      const modal = document.querySelector(`[data-modal-id="journal-${CSS.escape(journalId)}"]`);
      modal?.querySelector("[data-modal-close]")?.click();
      modal?.remove();
      if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
      return;
    }

    if (envelope.event === "journal.created" && payload.type === "quest") {
      reloadOpenQuestBoardsForCampaign(payload.room_id);
      return;
    }

    if (JOURNAL_EVENTS.has(envelope.event)) {
      const modal = document.querySelector(`[data-modal-id="journal-${CSS.escape(journalId)}"]`);
      if (!modal) {
        if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
        return;
      }
      
      
      
      const editorForm = modal.querySelector("[data-journal-editor]");
      if (editorForm && !editorForm.hidden) {
        if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
        return;
      }
      reloadJournalModal(journalId);
      if (payload.type === "quest") reloadOpenQuestBoardsForCampaign(payload.room_id);
    }
  });

  

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-journal-panel]").forEach(initPanel);
    document.querySelectorAll("[data-journal-modal]").forEach((body) => {
      const modal = body.closest("[data-modal-window]");
      if (modal) initJournalModal(modal);
    });
    applyJournalFolderColors(document);
  });

  document.addEventListener("vtt:journal-modal-mounted", (event) => {
    const modal = event.detail?.modal;
    if (modal) initJournalModal(modal);
  });
})();
