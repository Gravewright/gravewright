





(function () {
  const Api = window.GravewrightContentApi;
  const SOURCE_MIME = Api.SOURCE_MIME;
  const csrf = Api.csrf;
  const postJSON = Api.postJSON;

  
  
  function hasDropSource(e) {
    return Array.from(e.dataTransfer.types || []).includes(SOURCE_MIME);
  }



  function zoneAcceptsType(zone, type) {
    const accepts = zone?.dataset.dropAccepts;
    if (!accepts) return true;
    const dropped = String(type || "").trim().toLowerCase();
    if (!dropped) return true;
    const allowed = accepts.split(",").map((part) => part.trim().toLowerCase()).filter(Boolean);
    return !allowed.length || allowed.includes(dropped);
  }

  document.addEventListener("dragover", (e) => {
    const sheet = e.target.closest("[data-actor-sheet-root]");
    if (!sheet || !hasDropSource(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    const zone = e.target.closest("[data-drop-zone]");
    (zone || sheet).classList.add("is-drop-active");
  });

  document.addEventListener("dragleave", (e) => {
    const sheet = e.target.closest("[data-actor-sheet-root]");
    const zone = e.target.closest("[data-drop-zone]");
    
    if (zone && !zone.contains(e.relatedTarget)) zone.classList.remove("is-drop-active");
    if (sheet && !sheet.contains(e.relatedTarget)) sheet.classList.remove("is-drop-active");
  });

  document.addEventListener("drop", async (e) => {
    const sheet = e.target.closest("[data-actor-sheet-root]");
    if (!sheet) return;
    const raw = e.dataTransfer.getData(SOURCE_MIME);
    if (!raw) return;
    e.preventDefault();
    sheet.classList.remove("is-drop-active");
    const zone = e.target.closest("[data-drop-zone]");
    zone?.classList.remove("is-drop-active");
    let source;
    try {
      source = JSON.parse(raw);
    } catch {
      return;
    }
    const actorId = sheet.dataset.actorId || sheet.closest("[data-modal-window]")?.dataset.actorId;
    if (!actorId) return;

    // Reject a wrong-typed drop (e.g. a Weapon onto the Skills zone) before it
    // reaches the server. The zone's empty-state text already names what it
    // accepts, so reuse it as a localized hint rather than a hardcoded string.
    const droppedType = source.item_type || source.type || source.entry_type || "";
    if (zone && !zoneAcceptsType(zone, droppedType)) {
      const hint = zone.dataset.emptyText;
      if (hint) window.GravewrightToasts?.showToast(hint);
      return;
    }

    await postJSON("/game/actor/drop", {
      csrf_token: csrf(),
      actor_id: actorId,
      source,
      target: { drop_zone: zone?.dataset.dropZone || "" },
    });

  });
})();
