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
        loadSceneTileIndex(sceneId, layerId, query) {
            const params = new URLSearchParams(query);
            return jsonFetch(
                `/game/scenes/${encodeURIComponent(sceneId)}/layers/${encodeURIComponent(layerId)}/tile-index?${params}`,
                { errorMessage: "tile index failed" },
            );
        },
        loadSceneTokens(sceneId) {
            return jsonFetch(`/game/scenes/${sceneId}/tokens`);
        },
        loadActorSheetBundle(actorId) {
            return jsonFetch(`/game/actor/${encodeURIComponent(actorId)}/sheet-bundle`);
        },
    };
})();
