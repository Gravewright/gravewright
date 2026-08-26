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

            // Na camada artistica os dois sentidos pegam tudo: a marquee mostra
            // sempre o traco de selecao ampla para nao prometer um filtro que nao existe.
            const artistic = (window.GravewrightTools?.activeLayer || "game") === "composition";
            el.classList.toggle("board-marquee--all", artistic || marquee.x >= marquee.startX);
            el.style.display = "block";
        }

        function hideEl() {
            if (marqueeEl) marqueeEl.style.display = "none";
        }

        function selectTokensInWorldRect(canvas, rect, { additive = false } = {}) {
            const scene = sceneDataFor(canvas);
            if (!scene) return 0;
            const gridSize = scene.scaledTileSize;
            const ids = [];

            tokenStoreFor(canvas).forEach((token) => {
                const cx = (scene.gridOffsetX || 0) + (token.grid_x + (token.width_cells || 1) / 2) * gridSize;
                const cy = (scene.gridOffsetY || 0) + (token.grid_y + (token.height_cells || 1) / 2) * gridSize;
                if (
                    cx >= rect.x0 && cx <= rect.x1
                    && cy >= rect.y0 && cy <= rect.y1
                ) {
                    ids.push(token.token_id);
                }
            });

            setSelection(canvas, ids, { additive });
            return ids.length;
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
            selectTokensInWorldRect(canvas, {
                x0: minWorld.worldX, y0: minWorld.worldY,
                x1: maxWorld.worldX, y1: maxWorld.worldY,
            }, { additive: marquee.additive });

            // Left-to-right is the broad selection: tokens plus every overlay.
            // Na camada artistica os overlays SAO o conteudo -- nao ha token para
            // separar -- entao ali a marquee pega nos dois sentidos, como nas
            // camadas de efeitos, paredes e iluminacao.
            const broad = marquee.x >= marquee.startX;
            const artistic = (window.GravewrightTools?.activeLayer || "game") === "composition";
            if (broad || artistic) {
                const rect = {
                    left: Math.min(marquee.startX, marquee.x),
                    top: Math.min(marquee.startY, marquee.y),
                    right: Math.max(marquee.startX, marquee.x),
                    bottom: Math.max(marquee.startY, marquee.y),
                };
                if (broad) window.GravewrightCards?.selectInRect?.(canvas, rect, { additive: marquee.additive });
                window.GravewrightSceneImages?.selectInRect?.(canvas, rect, { additive: marquee.additive });
                window.GravewrightSpatialSounds?.selectInRect?.(canvas, rect, { additive: marquee.additive });
            }
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

        function cancel(event) {
            if (!activeMarquee || activeMarquee.pointerId !== event.pointerId) return false;
            const marquee = activeMarquee;
            activeMarquee = null;
            hideEl();
            try { marquee.canvas.releasePointerCapture(event.pointerId); } catch {}
            return true;
        }

        return {
            cancel,
            selectTokensInWorldRect,
            start,
            stop,
            update,
        };
    }

    window.GravewrightMapMarquee = { createMarqueeController };
})();
