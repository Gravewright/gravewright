



(() => {
    const FI = (window.GravewrightFogInternals = window.GravewrightFogInternals || {});
    const fogStates = FI.fogStates;

    function streamerLocalMode() {
        return document.body?.dataset?.streamerMode === "true";
    }

    function bumpVersion(sceneId) {
        const fog = fogStates.get(sceneId);
        return (fog?.version || 0) + 1;
    }

    function sendOps(roomId, sceneId, ops) {
        if (!ops || ops.length === 0) return;
        if (streamerLocalMode()) {
            ops.forEach((op) => FI.appendLocalOp(sceneId, op));
            FI.refreshPanelForActiveScene?.();
            return;
        }
        const fog = fogStates.get(sceneId);
        const payload = {
            scene_id: sceneId,
            ops,
        };
        if (fog?.version != null) payload.expected_version = fog.version;
        window.GravewrightRealtime?.sendCommand?.("fog.paint", payload, { roomId });
    }

    function sendEnable(roomId, sceneId, initial) {
        if (streamerLocalMode()) {
            FI.applyFog(sceneId, {
                enabled: true,
                baseline: initial || "hide_all",
                ops: [],
                version: bumpVersion(sceneId),
            });
            return;
        }
        window.GravewrightRealtime?.sendCommand?.("fog.enable", {
            scene_id: sceneId,
            initial,
        }, { roomId });
    }

    function sendDisable(roomId, sceneId) {
        if (streamerLocalMode()) {
            FI.applyFog(sceneId, {
                enabled: false,
                baseline: fogStates.get(sceneId)?.baseline || "hide_all",
                ops: [],
                version: bumpVersion(sceneId),
            });
            return;
        }
        window.GravewrightRealtime?.sendCommand?.("fog.disable", {
            scene_id: sceneId,
        }, { roomId });
    }

    function sendReset(roomId, sceneId, to) {
        if (streamerLocalMode()) {
            FI.applyFog(sceneId, {
                enabled: true,
                baseline: to || "hide_all",
                ops: [],
                version: bumpVersion(sceneId),
            });
            return;
        }
        window.GravewrightRealtime?.sendCommand?.("fog.reset", {
            scene_id: sceneId,
            to,
        }, { roomId });
    }

    FI.sendOps = sendOps;
    FI.sendEnable = sendEnable;
    FI.sendDisable = sendDisable;
    FI.sendReset = sendReset;
})();
