(() => {
    function createPanController(deps) {
        const {
            markDirty,
            scheduleCameraSave,
            scheduleViewportUpdate,
            stateFor,
        } = deps;

        let activePan = null;

        function start(canvas, event) {
            const state = stateFor(canvas);
            activePan = {
                canvas,
                pointerId: event.pointerId,
                startX: event.clientX,
                startY: event.clientY,
                offsetX: state.offsetX,
                offsetY: state.offsetY,
            };
            canvas.setPointerCapture(event.pointerId);
            canvas.classList.add("is-panning");
        }

        function update(event) {
            if (!activePan || activePan.pointerId !== event.pointerId) return false;

            const inputStartedAt = window.__gravewrightMeasureRender === true ? performance.now() : 0;
            const cameraStartedAt = inputStartedAt ? performance.now() : 0;
            const state = stateFor(activePan.canvas);
            state.offsetX = activePan.offsetX + event.clientX - activePan.startX;
            state.offsetY = activePan.offsetY + event.clientY - activePan.startY;
            if (cameraStartedAt) window.__gravewrightPerfRecord?.("camera_update", performance.now() - cameraStartedAt);
            scheduleViewportUpdate(activePan.canvas);
            markDirty(activePan.canvas, ["camera", "overlays", "viewport"]);
            if (inputStartedAt) window.__gravewrightPerfRecord?.("input_processing", performance.now() - inputStartedAt);
            return true;
        }

        function stop(event) {
            if (!activePan || activePan.pointerId !== event.pointerId) return false;

            try {
                activePan.canvas.releasePointerCapture(event.pointerId);
            } catch {

            }

            activePan.canvas.classList.remove("is-panning");
            scheduleCameraSave(activePan.canvas);
            activePan = null;
            return true;
        }

        return {
            start,
            stop,
            update,
        };
    }

    window.GravewrightMapPan = { createPanController };
})();
