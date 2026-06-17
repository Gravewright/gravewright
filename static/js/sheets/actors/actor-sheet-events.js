




(function () {
  const FI = (window.GravewrightActorSheetInternals = window.GravewrightActorSheetInternals || {});
  const refresh = FI.refresh;
  const mount = FI.mount;

  document.addEventListener("vtt:transport-event", (event) => {
    const envelope = event.detail || {};
    if (envelope.event !== "sheet.data.updated") return;
    const actorId = envelope.payload?.actor_id;
    if (!actorId) return;
    const modal = document.querySelector(`[data-modal-id="actor-${CSS.escape(actorId)}"]`);
    const root = modal?.querySelector("[data-actor-sheet-root]");
    if (root) refresh(root);
  });

  document.addEventListener("vtt:actor-sheet-modal-mounted", (event) => {
    const modal = event.detail?.modal;
    if (modal) mount(modal);
  });


  document.addEventListener("vtt:modal-closed", (event) => {
    const root = event.detail?.modal?.querySelector("[data-actor-sheet-root]");
    if (root) window.GravewrightHTMLSheets?.unmount?.(root);
  });

  
  document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-actor-open]");
    if (!opener) return;
    document.dispatchEvent(new CustomEvent("vtt:open-actor-sheet", {
      detail: { actorId: opener.dataset.actorOpen },
    }));
  });

  

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-actor-sheet-root]").forEach((root) => {
      const modal = root.closest("[data-modal-window]");
      if (modal) mount(modal);
    });
  });
})();
