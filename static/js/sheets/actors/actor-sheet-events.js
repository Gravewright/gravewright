




(function () {
  const FI = (window.GravewrightActorSheetInternals = window.GravewrightActorSheetInternals || {});
  const refresh = FI.refresh;
  const mount = FI.mount;






  const pendente = new WeakSet();

  function estaEditando(root) {
    const active = document.activeElement;
    return root.contains(active) && Boolean(active?.matches?.("input, textarea, select, [contenteditable]"));
  }

  function refreshQuandoOcioso(root) {
    if (!estaEditando(root)) {
      refresh(root);
      return;
    }
    if (pendente.has(root)) return;
    pendente.add(root);

    const aoSair = () => {


      setTimeout(() => {
        if (estaEditando(root)) return;
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
    if (!["sheet.data.updated", "actor.updated", "tokens.updated", "token.updated"].includes(envelope.event)) return;
    if (envelope.event === "tokens.updated" || envelope.event === "token.updated") {
      const values = Array.isArray(envelope.payload?.tokens)
        ? envelope.payload.tokens
        : (envelope.payload?.token ? [envelope.payload.token] : []);
      const tokenIds = new Set(values.map((token) => String(token?.token_id || token?.id || "")).filter(Boolean));
      if (!tokenIds.size) return;
      document.querySelectorAll("[data-actor-sheet-root][data-token-id]").forEach((root) => {
        if (!tokenIds.has(root.dataset.tokenId || "")) return;
        if (souEu(envelope.payload) && estaEditando(root)) return;
        refreshQuandoOcioso(root);
      });
      return;
    }
    const actorId = envelope.payload?.actor_id;
    if (!actorId) return;
    const roots = document.querySelectorAll(`[data-actor-sheet-root][data-actor-id="${CSS.escape(actorId)}"]`);
    roots.forEach((root) => {
      const modal = root.closest("[data-modal-window]");
      if (souEu(envelope.payload) && estaEditando(root)) return;
      if (envelope.event === "actor.updated") {
        void refresh(root).then((ok) => {
          if (ok === false) modal?.querySelector("[data-modal-close]")?.click();
        });
        return;
      }
      refreshQuandoOcioso(root);
    });
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
