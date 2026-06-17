





(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});

  
  window.Gravewright = window.Gravewright || {};

  function detectEnvironment() {
    const body = document.body;
    return {
      page: (body && body.dataset && body.dataset.page) || "",
      currentUserId: (body && body.dataset && body.dataset.currentUserId) || "",
      hasWebSocket: "WebSocket" in window,
      hasPixi: typeof window.PIXI !== "undefined",
    };
  }

  let ready = false;

  function bootstrap() {
    if (ready) {
      return Core;
    }
    ready = true;
    Core.env = detectEnvironment();
    if (Core.events && typeof Core.events.emit === "function") {
      Core.events.emit("vtt:core-ready", { env: Core.env });
    } else {
      window.dispatchEvent(
        new CustomEvent("vtt:core-ready", { detail: { env: Core.env } })
      );
    }
    return Core;
  }

  Core.isReady = () => ready;
  Core.bootstrap = bootstrap;
})();
