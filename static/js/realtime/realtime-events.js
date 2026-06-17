








(function () {
  const MEMBER_JOINED_EVENT = "member.joined";
  const MEMBER_REMOVED_EVENT = "member.removed";
  const PRESENCE_UPDATED_EVENT = "presence.updated";
  const PRESENCE_SNAPSHOT_EVENT = "presence.snapshot";

  function presence() {
    return window.GravewrightPresence || null;
  }

  function processTransportEvents(events) {
    if (!Array.isArray(events)) {
      return;
    }

    events.forEach((eventEnvelope) => {
      const ui = presence();

      if (ui) {
        if (eventEnvelope.event === MEMBER_JOINED_EVENT) {
          ui.processPlayerJoined(eventEnvelope.payload);
        }

        if (eventEnvelope.event === MEMBER_REMOVED_EVENT) {
          ui.processPlayerLeft(eventEnvelope.payload);
        }

        if (eventEnvelope.event === PRESENCE_UPDATED_EVENT) {
          ui.processPresenceUpdated(eventEnvelope.payload);
        }

        if (eventEnvelope.event === PRESENCE_SNAPSHOT_EVENT) {
          ui.processPresenceSnapshot(eventEnvelope.payload);
        }
      }

      document.dispatchEvent(
        new CustomEvent("vtt:transport-event", { detail: eventEnvelope })
      );
    });
  }

  function process(envelope) {
    processTransportEvents([envelope]);
  }

  window.GravewrightRealtimeEvents = { process, processTransportEvents };
})();
