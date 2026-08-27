




(() => {
  const FI = (window.GravewrightJournalsInternals = window.GravewrightJournalsInternals || {});

  function csrfToken() {
    return window.csrfToken();
  }


  function journalPanelFor(roomId) {
    return document.querySelector(`[data-journal-panel][data-room-id="${CSS.escape(roomId)}"]`);
  }
  function journalTreeHost(roomId) {
    return journalPanelFor(roomId)?.querySelector("[data-journal-tree-host]");
  }
  function roomIdForJournalEl(el) {
    return el?.closest?.("[data-journal-panel]")?.dataset.roomId || "";
  }
  async function refreshJournalPanel(roomId) {
    const host = journalTreeHost(roomId);
    if (!host) return false;
    try {
      const res = await fetch(`/game/journals/panel/${encodeURIComponent(roomId)}`, {
        credentials: "same-origin",
        headers: { Accept: "text/html" },
      });
      if (!res.ok) return false;
      const expanded = new Set(
        Array.from(host.querySelectorAll(".journal-folder[data-open]")).map((f) => f.dataset.folderId),
      );
      host.innerHTML = await res.text();
      expanded.forEach((id) => {
        const f = host.querySelector(`.journal-folder[data-folder-id="${CSS.escape(id)}"]`);
        if (f) FI.setJournalFolderOpen(f, true);
      });
      FI.applyJournalFolderColors(host);
      host.dataset.directoryLoaded = "true";
      return true;
    } catch { return false; }
  }

  async function postJournal(path, fields) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
      body: new URLSearchParams({ csrf_token: csrfToken(), ...fields }),
      credentials: "same-origin",
    });
  }

  async function boardPost(path, fields) {
    const body = new URLSearchParams({ csrf_token: csrfToken(), ...fields });
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
      body,
      credentials: "same-origin",
    });
    return res.ok;
  }

  FI.csrfToken = csrfToken;
  FI.journalPanelFor = journalPanelFor;
  FI.journalTreeHost = journalTreeHost;
  FI.roomIdForJournalEl = roomIdForJournalEl;
  FI.refreshJournalPanel = refreshJournalPanel;
  FI.postJournal = postJournal;
  FI.boardPost = boardPost;
})();
