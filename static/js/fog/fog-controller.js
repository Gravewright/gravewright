




(() => {
    const FI = (window.GravewrightFogInternals = window.GravewrightFogInternals || {});

    document.addEventListener("pointerdown", FI.onCapturePointerDown, { capture: true });
    document.addEventListener("pointermove", FI.onCapturePointerMove, { capture: true });
    document.addEventListener("pointerup", FI.onCapturePointerUp, { capture: true });
    document.addEventListener("pointercancel", FI.onCapturePointerUp, { capture: true });
    document.addEventListener("pointerleave", FI.onPointerLeave, { capture: true });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && FI.isActive()) {
            FI.clearPolygonInProgress();
        }
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", FI.initPanels, { once: true });
    } else {
        FI.initPanels();
    }

    

    window.GravewrightFog = {
        isActive: FI.isActive,
        fogViewFor: FI.fogViewFor,
        handleAltWheel: FI.handleAltWheel,
        applyFog: FI.applyFog,
        gmOpacity: () => FI.activePanelState()?.gmOpacity ?? FI.loadGmOpacity(),
    };
})();
