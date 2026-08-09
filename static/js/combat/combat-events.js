

(function () {
    document.addEventListener("vtt:transport-event", (event) => {
        const envelope = event.detail || {};
        if (!String(envelope.event || "").startsWith("combat.")) return;
        const campaignId = envelope.payload?.campaign_id;
        if (!campaignId) return;
        window.GravewrightCombatActions?.receiveState?.(campaignId, envelope.payload || {});
    });
})();
