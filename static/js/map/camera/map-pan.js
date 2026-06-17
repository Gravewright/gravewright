(() => {
    function createPanController(deps) {
        const {
            markDirty,
            saveCameraNow,
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

            const state = stateFor(activePan.canvas);
            state.offsetX = activePan.offsetX + event.clientX - activePan.startX;
            state.offsetY = activePan.offsetY + event.clientY - activePan.startY;
            scheduleViewportUpdate(activePan.canvas);
            scheduleCameraSave(activePan.canvas);
            markDirty(activePan.canvas);
            return true;
        }

        function stop(event) {
            if (!activePan || activePan.pointerId !== event.pointerId) return false;

            try {
                activePan.canvas.releasePointerCapture(event.pointerId);
            } catch {
                
            }

            activePan.canvas.classList.remove("is-panning");
            saveCameraNow(activePan.canvas);
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
