




(function () {
    const ROLES = {
        current: { role: "current", color: 0x28d17c, alpha: 0.96 },
        next: { role: "next", color: 0xef4444, alpha: 0.92 },
        acted: { role: "acted", color: 0x9ca3af, alpha: 0.68 },
    };

    const states = new Map();
    const markersByRoom = new Map();
    let animationFrame = 0;
    let lastFrameAt = 0;

    function roleFor(combatant) {
        if (combatant.is_current) return "current";
        if (combatant.is_next) return "next";
        return combatant.has_acted ? "acted" : "";
    }

    function buildMarkers(state) {
        const markers = new Map();
        if (!state?.active) return markers;
        (Array.isArray(state.combatants) ? state.combatants : []).forEach((combatant) => {
            const tokenId = combatant?.token_id;
            const role = tokenId ? roleFor(combatant) : "";
            if (!tokenId || (!role && !combatant.defeated)) return;
            markers.set(tokenId, {
                ...(ROLES[role] || {}),
                role,
                combatant_id: combatant.id,
                name: combatant.name || "",
                initiative: combatant.initiative,
                defeated: !!combatant.defeated,
            });
        });
        return markers;
    }

    function hasPulsingMarkers() {
        for (const markers of markersByRoom.values()) {
            for (const marker of markers.values()) {
                if (marker.role === "current" || marker.role === "next") return true;
            }
        }
        return false;
    }

    function stopLoop() {
        if (animationFrame) window.cancelAnimationFrame(animationFrame);
        animationFrame = 0;
        lastFrameAt = 0;
    }

    function loop(now) {
        if (!hasPulsingMarkers()) {
            stopLoop();
            return;
        }

        const profileFps = window.GravewrightGraphicsQuality?.config?.().animationFps || 60;
        const interval = Math.max(55, 1000 / profileFps);
        if (!lastFrameAt || now - lastFrameAt >= interval) {
            lastFrameAt = now;
            window.GravewrightMap?.redraw?.();
        }
        animationFrame = window.requestAnimationFrame(loop);
    }

    function ensureLoop() {
        if (!animationFrame && hasPulsingMarkers()) animationFrame = window.requestAnimationFrame(loop);
    }

    function announce(roomId, state) {
        document.dispatchEvent(new CustomEvent("vtt:combat-state-changed", { detail: { roomId, state } }));
        window.GravewrightMap?.redraw?.();
    }

    function set(roomId, state) {
        if (!roomId) return;
        states.set(roomId, state || {});
        markersByRoom.set(roomId, buildMarkers(state || {}));
        announce(roomId, state || {});
        ensureLoop();
    }

    function clear(roomId) {
        if (!roomId) return;
        states.delete(roomId);
        markersByRoom.delete(roomId);
        announce(roomId, null);
        if (!hasPulsingMarkers()) stopLoop();
    }

    function get(roomId) {
        return states.get(roomId) || null;
    }

    function markerForToken(roomId, tokenId) {
        if (!roomId || !tokenId) return null;
        return markersByRoom.get(roomId)?.get(tokenId) || null;
    }

    function roleForToken(roomId, tokenId) {
        return markerForToken(roomId, tokenId)?.role || "";
    }

    window.GravewrightCombatState = { clear, get, markerForToken, roleForToken, set };
})();
