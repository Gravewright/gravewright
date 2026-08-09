




(function () {
  const FI = (window.GravewrightActorSheetInternals = window.GravewrightActorSheetInternals || {});
  const refresh = FI.refresh;
  const mount = FI.mount;






  const pendente = new WeakSet();

  function refreshQuandoOcioso(root) {
    if (!root.contains(document.activeElement)) {
      refresh(root);
      return;
    }
    if (pendente.has(root)) return;
    pendente.add(root);

    const aoSair = () => {


      setTimeout(() => {
        if (root.contains(document.activeElement)) return;
        root.removeEventListener("focusout", aoSair);
        pendente.delete(root);
        refresh(root);
      }, 0);
    };
    root.addEventListener("focusout", aoSair);
  }






  const souEu = (payload) => {
    const eu = document.body?.dataset?.currentUserId || "";
    return Boolean(eu) && payload?.updated_by === eu;
  };

  document.addEventListener("vtt:transport-event", (event) => {
    const envelope = event.detail || {};
    if (!["sheet.data.updated", "actor.updated"].includes(envelope.event)) return;
    const actorId = envelope.payload?.actor_id;
    if (!actorId) return;
    const modal = document.querySelector(`[data-modal-id="actor-${CSS.escape(actorId)}"]`);
    const root = modal?.querySelector("[data-actor-sheet-root]");
    if (!root) return;





    if (souEu(envelope.payload) && root.contains(document.activeElement)) return;
    if (envelope.event === "actor.updated") {
      void refresh(root).then((ok) => {
        if (ok === false) modal.querySelector("[data-modal-close]")?.click();
      });
      return;
    }
    refreshQuandoOcioso(root);
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
