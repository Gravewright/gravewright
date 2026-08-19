/* Core-owned projection of authorized semantic content-open intents. */
(() => {
  document.addEventListener("vtt:content-open", (event) => {
    const ref = event.detail?.ref;
    if (!ref?.id || !ref?.kind) return;
    if (ref.kind === "journal") {
      document.dispatchEvent(new CustomEvent("vtt:open-journal", {
        detail: { journalId: ref.id, campaignId: ref.campaignId || "" },
      }));
    }
  });
})();
