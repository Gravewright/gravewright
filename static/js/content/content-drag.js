





(function () {
  const Api = window.GravewrightContentApi;
  const SOURCE_MIME = Api.SOURCE_MIME;
  const csrf = Api.csrf;
  const postJSON = Api.postJSON;

  
  
  function hasDropSource(e) {
    return Array.from(e.dataTransfer.types || []).includes(SOURCE_MIME);
  }

  document.addEventListener("dragover", (e) => {
    const sheet = e.target.closest("[data-actor-sheet-root]");
    if (!sheet || !hasDropSource(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    sheet.classList.add("is-drop-active");
  });

  document.addEventListener("dragleave", (e) => {
    const sheet = e.target.closest("[data-actor-sheet-root]");
    
    if (sheet && !sheet.contains(e.relatedTarget)) sheet.classList.remove("is-drop-active");
  });

  document.addEventListener("drop", async (e) => {
    const sheet = e.target.closest("[data-actor-sheet-root]");
    if (!sheet) return;
    const raw = e.dataTransfer.getData(SOURCE_MIME);
    if (!raw) return;
    e.preventDefault();
    sheet.classList.remove("is-drop-active");
    let source;
    try {
      source = JSON.parse(raw);
    } catch {
      return;
    }
    const actorId = sheet.dataset.actorId || sheet.closest("[data-modal-window]")?.dataset.actorId;
    if (!actorId) return;
    
    await postJSON("/game/actor/drop", {
      csrf_token: csrf(),
      actor_id: actorId,
      source,
      target: {},
    });
    
  });
})();
