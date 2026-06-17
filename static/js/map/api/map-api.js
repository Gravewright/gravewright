(() => {
    async function jsonFetch(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            cache: "no-store",
            ...options,
            headers: { Accept: "application/json", ...(options.headers || {}) },
        });
        if (!response.ok) {
            throw new Error(options.errorMessage || `Request failed: ${url}`);
        }
        return response.json();
    }

    function sendCommand(command, payload, context) {
        return window.GravewrightRealtime?.sendCommand(command, payload, context);
    }

    window.GravewrightMapApi = {
        jsonFetch,
        sendCommand,
        loadSceneManifest(sceneId) {
            return jsonFetch(`/game/scenes/${sceneId}/manifest`, {
                errorMessage: "manifest failed",
            });
        },
        loadSceneTokens(sceneId) {
            return jsonFetch(`/game/scenes/${sceneId}/tokens`);
        },
        loadActorSheetBundle(actorId) {
            return jsonFetch(`/game/actor/${encodeURIComponent(actorId)}/sheet-bundle`);
        },
        async updateTokenHp(payload) {
            const http = window.GravewrightCore?.http;
            if (!http?.postJson) throw new Error("HTTP API unavailable");
            const result = await http.postJson("/game/token/hp", payload);
            if (!result.ok) {
                const err = new Error(result.details?.error_key || result.message || "token hp update failed");
                err.details = result.details;
                throw err;
            }
            return result.data || {};
        },
    };
})();
