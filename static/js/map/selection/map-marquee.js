(() => {
    function createMarqueeController(deps) {
        const {
            clearSelection,
            sceneDataFor,
            screenToWorldXY,
            setSelection,
            stateFor,
            tokenStoreFor,
        } = deps;

        let activeMarquee = null;
        let marqueeEl = null;

        function ensureEl() {
            if (marqueeEl) return marqueeEl;
            marqueeEl = document.createElement("div");
            marqueeEl.className = "board-marquee";
            document.body.appendChild(marqueeEl);
            return marqueeEl;
        }

        function updateEl(marquee) {
            const el = ensureEl();
            el.style.left = `${Math.min(marquee.startX, marquee.x)}px`;
            el.style.top = `${Math.min(marquee.startY, marquee.y)}px`;
            el.style.width = `${Math.abs(marquee.x - marquee.startX)}px`;
            el.style.height = `${Math.abs(marquee.y - marquee.startY)}px`;
            el.style.display = "block";
        }

        function hideEl() {
            if (marqueeEl) marqueeEl.style.display = "none";
        }

        function finish(marquee) {
            const canvas = marquee.canvas;
            const scene = sceneDataFor(canvas);
            if (!scene) return;

            const state = stateFor(canvas);
            const minWorld = screenToWorldXY(
                Math.min(marquee.startX, marquee.x),
                Math.min(marquee.startY, marquee.y),
                state,
            );
            const maxWorld = screenToWorldXY(
                Math.max(marquee.startX, marquee.x),
                Math.max(marquee.startY, marquee.y),
                state,
            );
            const gridSize = scene.scaledTileSize;
            const ids = [];

            tokenStoreFor(canvas).forEach((token) => {
                const cx = (token.grid_x + (token.width_cells || 1) / 2) * gridSize;
                const cy = (token.grid_y + (token.height_cells || 1) / 2) * gridSize;
                if (
                    cx >= minWorld.worldX
                    && cx <= maxWorld.worldX
                    && cy >= minWorld.worldY
                    && cy <= maxWorld.worldY
                ) {
                    ids.push(token.token_id);
                }
            });

            setSelection(canvas, ids, { additive: marquee.additive });
        }

        function start(canvas, event, { additive = false } = {}) {
            activeMarquee = {
                canvas,
                pointerId: event.pointerId,
                startX: event.clientX,
                startY: event.clientY,
                x: event.clientX,
                y: event.clientY,
                additive,
                moved: false,
            };
            canvas.setPointerCapture(event.pointerId);
        }

        function update(event) {
            if (!activeMarquee || activeMarquee.pointerId !== event.pointerId) {
                return false;
            }

            activeMarquee.x = event.clientX;
            activeMarquee.y = event.clientY;
            if (
                Math.abs(activeMarquee.x - activeMarquee.startX) > 3
                || Math.abs(activeMarquee.y - activeMarquee.startY) > 3
            ) {
                activeMarquee.moved = true;
            }
            updateEl(activeMarquee);
            return true;
        }

        function stop(event) {
            if (!activeMarquee || activeMarquee.pointerId !== event.pointerId) {
                return false;
            }

            const marquee = activeMarquee;
            activeMarquee = null;
            hideEl();

            try {
                marquee.canvas.releasePointerCapture(event.pointerId);
            } catch {
                
            }

            if (marquee.moved) finish(marquee);
            else if (!marquee.additive) clearSelection(marquee.canvas);

            return true;
        }

        return {
            start,
            stop,
            update,
        };
    }

    window.GravewrightMapMarquee = { createMarqueeController };
})();
