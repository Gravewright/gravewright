(() => {
    function createBoardPingController(deps) {
        let pending = null;
        const {
            holdMs,
            moveTolerance,
            sceneDataFor,
            stateFor,
            screenFromWorld,
            screenToWorldXY,
            focusWorldPoint,
        } = deps;

        function render(canvas, worldX, worldY, variant = "ping") {
            const state = stateFor(canvas);
            const x = screenFromWorld(worldX, state.offsetX, state.zoom);
            const y = screenFromWorld(worldY, state.offsetY, state.zoom);
            const ping = document.createElement("div");
            ping.className = `board-ping board-ping--${variant === "focus" ? "focus" : "ping"}`;
            ping.style.left = `${Math.round(x)}px`;
            ping.style.top = `${Math.round(y)}px`;
            for (let i = 0; i < 3; i += 1) {
                const wave = document.createElement("span");
                wave.className = "board-ping__wave";
                wave.style.animationDelay = `${i * 0.16}s`;
                ping.appendChild(wave);
            }
            const core = document.createElement("span");
            core.className = "board-ping__core";
            ping.appendChild(core);
            document.body.appendChild(ping);
            window.setTimeout(() => ping.remove(), 1900);
        }

        function handle(payload) {
            if (!payload || payload.scene_id == null) return;
            const roomId = String(payload.room_id || "");
            const sceneId = String(payload.scene_id || "");
            const canvas = Array.from(document.querySelectorAll("[data-map-canvas]"))
                .find((candidate) => (
                    candidate.dataset.sceneId === sceneId
                    && (!roomId || candidate.dataset.roomId === roomId)
                    && candidate.closest(".room-workspace")?.classList.contains("is-active")
                ));
            if (!canvas) return;

            const worldX = Number(payload.world_x);
            const worldY = Number(payload.world_y);
            if (!Number.isFinite(worldX) || !Number.isFinite(worldY)) return;

            const variant = payload.variant === "focus" ? "focus" : "ping";
            if (variant === "focus") focusWorldPoint(canvas, worldX, worldY);
            render(canvas, worldX, worldY, variant);
        }

        function cancel(pointerId = null) {
            if (!pending) return;
            if (pointerId != null && pending.pointerId !== pointerId) return;
            window.clearTimeout(pending.timer);
            pending = null;
        }

        function send(ping) {
            const variant = ping.shiftKey ? "focus" : "ping";
            const sent = window.GravewrightRealtime?.sendCommand(
                "board.ping",
                {
                    scene_id: ping.sceneId,
                    world_x: Math.round(ping.worldX * 100) / 100,
                    world_y: Math.round(ping.worldY * 100) / 100,
                    variant,
                },
                {
                    sceneId: ping.sceneId,
                    roomId: ping.roomId,
                },
            );
            if (!sent) {
                if (variant === "focus") focusWorldPoint(ping.canvas, ping.worldX, ping.worldY);
                render(ping.canvas, ping.worldX, ping.worldY, variant);
            }
        }

        function schedule(canvas, event) {
            const scene = sceneDataFor(canvas);
            if (!scene) return;
            cancel();
            const world = screenToWorldXY(event.clientX, event.clientY, stateFor(canvas));
            const ping = {
                canvas,
                pointerId: event.pointerId,
                startX: event.clientX,
                startY: event.clientY,
                worldX: world.worldX,
                worldY: world.worldY,
                sceneId: scene.id,
                roomId: canvas.dataset.roomId || "",
                shiftKey: event.shiftKey,
                timer: null,
            };
            ping.timer = window.setTimeout(() => {
                if (!pending || pending.pointerId !== ping.pointerId) return;
                pending = null;
                send(ping);
            }, holdMs);
            pending = ping;
        }

        function update(event) {
            if (!pending || pending.pointerId !== event.pointerId) return;
            const dx = event.clientX - pending.startX;
            const dy = event.clientY - pending.startY;
            if (Math.sqrt(dx * dx + dy * dy) > moveTolerance) {
                cancel(event.pointerId);
                return;
            }
            pending.shiftKey = event.shiftKey;
        }

        function setShiftKey(active) {
            if (pending) pending.shiftKey = active;
        }

        return {
            cancel,
            handle,
            render,
            schedule,
            send,
            setShiftKey,
            update,
        };
    }

    window.GravewrightMapBoardPing = { createBoardPingController };
})();
