(() => {
    function createCameraController(deps) {
        const states = new WeakMap();
        const saveTimers = new WeakMap();
        const {
            storagePrefix,
            storageVersion,
            saveMs,
            sceneDataFor,
            viewportSizeFor,
            clampZoom,
            markDirty,
            scheduleViewportUpdate,
        } = deps;

        function storageKey(sceneId) {
            const userId = document.body.dataset.currentUserId || "anon";
            return `${storagePrefix}${userId}.${sceneId}`;
        }

        function sceneStartCamera(scene) {
            return {
                worldX: scene.startWorldX,
                worldY: scene.startWorldY,
                zoom: scene.startZoom,
            };
        }

        function intersectsScene(canvas, scene, camera) {
            const viewport = viewportSizeFor(canvas);
            const zoom = clampZoom(camera.zoom, 1);
            const halfWorldW = viewport.width / zoom / 2;
            const halfWorldH = viewport.height / zoom / 2;
            return camera.worldX + halfWorldW > 0
                && camera.worldY + halfWorldH > 0
                && camera.worldX - halfWorldW < scene.width
                && camera.worldY - halfWorldH < scene.height;
        }

        function readStored(canvas, scene) {
            try {
                const camera = JSON.parse(window.localStorage.getItem(storageKey(scene.id)) || "null");
                if (!camera || typeof camera !== "object") return null;
                if (camera.version !== storageVersion) return null;
                if (!Number.isFinite(camera.worldX) || !Number.isFinite(camera.worldY)) return null;
                const restored = {
                    worldX: camera.worldX,
                    worldY: camera.worldY,
                    zoom: clampZoom(camera.zoom, 1),
                };
                return intersectsScene(canvas, scene, restored) ? restored : null;
            } catch {
                return null;
            }
        }

        function cameraFromState(canvas) {
            const scene = sceneDataFor(canvas);
            if (!scene) return null;
            const state = stateFor(canvas);
            const viewport = viewportSizeFor(canvas);
            return {
                worldX: (viewport.width / 2 - state.offsetX) / state.zoom,
                worldY: (viewport.height / 2 - state.offsetY) / state.zoom,
                zoom: state.zoom,
            };
        }

        function applyToState(canvas, camera, state = stateFor(canvas)) {
            const viewport = viewportSizeFor(canvas);
            state.zoom = clampZoom(camera.zoom, 1);
            state.offsetX = viewport.width / 2 - camera.worldX * state.zoom;
            state.offsetY = viewport.height / 2 - camera.worldY * state.zoom;
            state.dirty = true;
        }

        function initialFor(canvas) {
            const scene = sceneDataFor(canvas);
            if (!scene) {
                return { worldX: 0, worldY: 0, zoom: 1 };
            }
            return readStored(canvas, scene) || sceneStartCamera(scene);
        }

        function saveNow(canvas) {
            const scene = sceneDataFor(canvas);
            const camera = scene ? cameraFromState(canvas) : null;
            if (!scene || !camera) return;

            try {
                window.localStorage.setItem(
                    storageKey(scene.id),
                    JSON.stringify({
                        version: storageVersion,
                        worldX: Math.round(camera.worldX * 100) / 100,
                        worldY: Math.round(camera.worldY * 100) / 100,
                        zoom: Math.round(camera.zoom * 1000) / 1000,
                    }),
                );
            } catch {
                
            }
        }

        function scheduleSave(canvas) {
            const existing = saveTimers.get(canvas);
            if (existing) window.clearTimeout(existing);

            saveTimers.set(canvas, window.setTimeout(() => {
                saveTimers.delete(canvas);
                saveNow(canvas);
            }, saveMs));
        }

        function stateFor(canvas) {
            let state = states.get(canvas);
            if (!state) {
                state = {
                    offsetX: window.innerWidth / 2,
                    offsetY: window.innerHeight / 2,
                    zoom: 1,
                    dirty: true,
                };
                applyToState(canvas, initialFor(canvas), state);
                states.set(canvas, state);
            }
            return state;
        }

        function activeCanvas() {
            return document.querySelector(".room-workspace.is-active [data-map-canvas]");
        }

        function activeForScene(sceneId) {
            const canvas = activeCanvas();
            if (!canvas || canvas.dataset.sceneId !== sceneId) return null;
            return cameraFromState(canvas);
        }

        function focusWorldPoint(canvas, worldX, worldY) {
            const scene = sceneDataFor(canvas);
            if (!scene) return;
            const state = stateFor(canvas);
            const viewport = viewportSizeFor(canvas);
            state.offsetX = viewport.width / 2 - worldX * state.zoom;
            state.offsetY = viewport.height / 2 - worldY * state.zoom;
            scheduleViewportUpdate(canvas);
            scheduleSave(canvas);
            markDirty(canvas);
        }

        return {
            activeCanvas,
            activeForScene,
            applyToState,
            cameraFromState,
            focusWorldPoint,
            initialFor,
            scheduleSave,
            saveNow,
            stateFor,
        };
    }

    window.GravewrightMapCamera = { createCameraController };
})();
