(() => {
    function bindZoomWheel(deps) {
        const {
            clampZoom,
            markDirty,
            scheduleCameraSave,
            scheduleViewportUpdate,
            stateFor,
        } = deps;

        document.addEventListener("wheel", (event) => {
            const canvas = event.target.closest("[data-map-canvas]");
            if (!canvas) return;

            if (event.altKey && window.GravewrightFog?.handleAltWheel?.(event)) {
                event.preventDefault();
                return;
            }

            event.preventDefault();

            const state = stateFor(canvas);
            const previousZoom = state.zoom;
            const zoomFactor = Math.exp(-event.deltaY * 0.00045);
            const nextZoom = clampZoom(previousZoom * zoomFactor, previousZoom);

            if (nextZoom === previousZoom) return;

            const worldX = (event.clientX - state.offsetX) / previousZoom;
            const worldY = (event.clientY - state.offsetY) / previousZoom;

            state.zoom = nextZoom;
            state.offsetX = event.clientX - worldX * nextZoom;
            state.offsetY = event.clientY - worldY * nextZoom;
            scheduleViewportUpdate(canvas);
            scheduleCameraSave(canvas);
            markDirty(canvas);
        }, { passive: false });
    }

    window.GravewrightMapZoom = { bindZoomWheel };
})();
