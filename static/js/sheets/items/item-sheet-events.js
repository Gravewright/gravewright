




(function () {
  const FI = (window.GravewrightItemSheetInternals = window.GravewrightItemSheetInternals || {});
  const refresh = FI.refresh;
  const mount = FI.mount;

  document.addEventListener("vtt:transport-event", (event) => {
    const envelope = event.detail || {};
    if (!["sheet.data.updated", "item.updated", "handout.access_changed"].includes(envelope.event)) return;
    const itemId = envelope.payload?.item_id;
    if (!itemId) return;
    const modal = document.querySelector(`[data-modal-id="item-${CSS.escape(itemId)}"]`);
    const root = modal?.querySelector("[data-item-sheet-root]");
    if (!root) return;
    void refresh(root).then((ok) => {
      if (ok === false && envelope.event !== "sheet.data.updated") {
        modal.querySelector("[data-modal-close]")?.click();
      }
    });
  });

  document.addEventListener("vtt:item-sheet-modal-mounted", (event) => {
    const modal = event.detail?.modal;
    if (modal) mount(modal);
  });

  document.addEventListener("vtt:modal-closed", (event) => {
    const root = event.detail?.modal?.querySelector("[data-item-sheet-root]");
    if (root) window.GravewrightHTMLSheets?.unmount?.(root);
  });


  document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-item-open]");
    if (!opener) return;
    document.dispatchEvent(new CustomEvent("vtt:open-item-sheet", {
      detail: { itemId: opener.dataset.itemOpen },
    }));
  });

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-item-sheet-root]").forEach((root) => {
      const modal = root.closest("[data-modal-window]");
      if (modal) mount(modal);
    });
  });
})();
