/* User-specific scene projection. Authority and destination are server-owned. */
(() => {
    "use strict";
    let transitioning = false;

    function sceneFromManifest(manifest) {
        const layer = manifest.layers?.find((candidate) => candidate.visible && candidate.kind === "raster")
            || manifest.layers?.find((candidate) => candidate.visible);
        return {
            id: manifest.scene_id, name: manifest.name,
            width: manifest.width, height: manifest.height,
            tile_size: manifest.tile_size, raster_tile_size: manifest.raster_tile_size,
            grid_size: manifest.grid_size, grid_visible: manifest.grid_visible,
            grid_color: manifest.grid_color, grid_opacity: manifest.grid_opacity,
            darkness: manifest.darkness, darkness_config: manifest.darkness_config,
            lighting_mode: manifest.lighting_mode, lights_out: manifest.lights_out,
            image_scale: manifest.image_scale, start_world_x: manifest.start_world_x,
            start_world_y: manifest.start_world_y, start_zoom: manifest.start_zoom,
            layer_id: layer?.layer_id || "", tile_table_version: manifest.tile_table_version,
            scene_epoch: manifest.scene_epoch,
        };
    }

    async function navigate(sceneId, roomId = "", { local = false } = {}) {
        if (!sceneId || transitioning) return false;
        const canvas = roomId
            ? document.querySelector(`[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`)
            : document.querySelector("[data-map-canvas]");
        if (canvas?.dataset.sceneId === sceneId) return true;
        transitioning = true;
        try {
            const manifest = await window.GravewrightMapApi.loadSceneManifest(sceneId);
            const targetRoom = roomId || manifest.campaign_id;
            if (canvas) canvas.dataset.localSceneNavigation = "false";
            document.dispatchEvent(new CustomEvent("vtt:transport-event", { detail: {
                event: "scene.activated",
                payload: { room_id: targetRoom, scene: sceneFromManifest(manifest) },
            } }));
            if (local) {
                if (canvas) canvas.dataset.localSceneNavigation = "true";
                const url = new URL(window.location.href);
                url.searchParams.set("room", targetRoom);
                url.searchParams.set("view_scene", sceneId);
                history.replaceState(history.state, "", url);
            }
            return true;
        } catch {
            if (window.GravewrightUiState?.reload) window.GravewrightUiState.reload("scene-navigation-fallback");
            else window.location.reload();
            return false;
        } finally {
            transitioning = false;
        }
    }

    window.GravewrightSceneNavigation = { navigate };
    document.addEventListener("vtt:transport-event", (event) => {
        const { event: name, payload } = event.detail || {};
        if (name !== "navigation.scene.changed" || !payload?.scene_id || transitioning) return;
        const context = JSON.parse(document.getElementById("gravewright-game-context")?.textContent || "{}");
        if (context.scene?.id === payload.scene_id) return;
        void navigate(payload.scene_id, payload.room_id || context.room?.id || "");
    });
})();
