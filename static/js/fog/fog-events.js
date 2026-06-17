



(() => {
    const FI = (window.GravewrightFogInternals = window.GravewrightFogInternals || {});
    const applyFog = FI.applyFog;
    const clearPolygonInProgress = FI.clearPolygonInProgress;

    document.addEventListener("vtt:manifest-loaded", (e) => {
        const sceneId = e.detail?.sceneId;
        const fog = e.detail?.manifest?.fog;
        if (sceneId && fog) applyFog(sceneId, fog);
    });

    document.addEventListener("vtt:transport-event", (e) => {
        const { event: evtName, payload } = e.detail ?? {};
        if (evtName === "fog.updated" && payload?.scene_id) {
            applyFog(payload.scene_id, {
                enabled: payload.enabled,
                version: payload.version,
                baseline: payload.baseline,
                ops: payload.ops,
                new_ops: payload.new_ops,
            });
        }
        if (evtName === "scene.activated") {
            clearPolygonInProgress();
        }
    });
})();
