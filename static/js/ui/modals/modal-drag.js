(() => {
    const FI = window.GravewrightModalInternals || {};
    const DRAG_THRESHOLD = 4;

    function clamp(value, min, max) {
        return Math.max(min, Math.min(value, max));
    }

    function startDrag(event, handle) {
        if (event.target.closest("button, a, input, select, textarea, summary")) {
            return;
        }

        const modal = handle.closest("[data-modal-window]");
        if (!modal || FI.isClassicPanel?.(modal)) return;

        const layer = modal.closest(".game-modal-layer");
        if (!layer) return;

        FI.bringToFront?.(modal);

        const start = FI.getPosition?.(modal) || { x: 22, y: FI.defaultY || 22 };
        const startPointerX = event.clientX;
        const startPointerY = event.clientY;
        let dragging = false;

        handle.setPointerCapture(event.pointerId);

        let bounds = null;
        let frame = 0;
        let pendingX = 0;
        let pendingY = 0;

        function applyPosition() {
            frame = 0;
            FI.setPosition?.(modal, pendingX, pendingY);
        }

        function move(moveEvent) {
            const dx = moveEvent.clientX - startPointerX;
            const dy = moveEvent.clientY - startPointerY;

            if (!dragging) {
                if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;

                dragging = true;
                modal.setAttribute("data-dragging", "true");

                const layerRect = layer.getBoundingClientRect();
                const margin = 8;
                bounds = {
                    minX: margin,
                    maxX: Math.max(margin, layerRect.width - (modal.offsetWidth || 200) - margin),
                    minY: FI.defaultY || 22,
                    maxY: Math.max(FI.defaultY || 22, layerRect.height - (modal.offsetHeight || 100) - margin),
                };
            }

            pendingX = clamp(start.x + dx, bounds.minX, bounds.maxX);
            pendingY = clamp(start.y + dy, bounds.minY, bounds.maxY);
            if (!frame) frame = window.requestAnimationFrame(applyPosition);
        }

        function stop(stopEvent) {
            if (frame) {
                window.cancelAnimationFrame(frame);
                frame = 0;
                FI.setPosition?.(modal, pendingX, pendingY);
            }
            modal.removeAttribute("data-dragging");

            try {
                handle.releasePointerCapture(stopEvent.pointerId);
            } catch {
                
            }

            handle.removeEventListener("pointermove", move);
            handle.removeEventListener("pointerup", stop);
            handle.removeEventListener("pointercancel", stop);
            FI.saveWindowState?.(modal);
        }

        handle.addEventListener("pointermove", move);
        handle.addEventListener("pointerup", stop);
        handle.addEventListener("pointercancel", stop);
    }

    document.addEventListener("pointerdown", (event) => {
        const handle = event.target.closest("[data-modal-drag-handle]");
        if (handle) startDrag(event, handle);
    });

    FI.startDrag = startDrag;
})();
