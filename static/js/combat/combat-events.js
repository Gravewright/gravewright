




(function () {
  const Panel = window.GravewrightCombatPanel;
  const renderHud = Panel.renderHud;
  const renderPanel = Panel.renderPanel;

  document.addEventListener("vtt:transport-event", (event) => {
    const envelope = event.detail || {};
    if (!String(envelope.event || "").startsWith("combat.")) return;
    const campaignId = envelope.payload?.campaign_id;
    if (campaignId) {
      if (window.GravewrightCombatActions?.receiveState) {
        window.GravewrightCombatActions.receiveState(campaignId, envelope.payload || {});
        return;
      }
      window.GravewrightCombatState?.set?.(campaignId, envelope.payload || {});
      document.querySelectorAll(`[data-combat-hud][data-room-id="${CSS.escape(campaignId)}"]`).forEach((hud) => renderHud(hud, envelope.payload || {}));
      document.querySelectorAll(`[data-combat-panel][data-room-id="${CSS.escape(campaignId)}"]`).forEach((panel) => renderPanel(panel, envelope.payload || {}));
    }
  });
})();
