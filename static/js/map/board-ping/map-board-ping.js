(() => {
    function createBoardPingController(deps) {
        let pending = null;
        const {
            holdMs,
            moveTolerance,
            sceneDataFor,
            stateFor,
            activeCanvas,
            screenToWorldXY,
            focusWorldPoint,
            boardRenderer,
        } = deps;

        function validColor(value) {
            return /^#[0-9a-f]{6}$/i.test(String(value || ""));
        }

        function streamerLocalMode() {
            return document.body?.dataset?.streamerMode === "true";
        }

        function render(canvas, worldX, worldY, variant = "ping", color = "") {
            const resolvedColor = validColor(color)
                ? color.toLowerCase()
                : (document.body?.dataset?.pingColor || "#f2c679");
            boardRenderer.showPing(canvas, {
                worldX,
                worldY,
                variant: variant === "focus" ? "focus" : "ping",
                color: resolvedColor,
            });
        }

        function handle(payload) {
            if (!payload || payload.scene_id == null) return;
            const roomId = String(payload.room_id || "");
            const sceneId = String(payload.scene_id || "");
            const canvas = activeCanvas();
            if (
                !canvas
                || canvas.dataset.sceneId !== sceneId
                || (roomId && canvas.dataset.roomId !== roomId)
            ) return;

            const worldX = Number(payload.world_x);
            const worldY = Number(payload.world_y);
            if (!Number.isFinite(worldX) || !Number.isFinite(worldY)) return;

            const variant = payload.variant === "focus" ? "focus" : "ping";
            if (variant === "focus") focusWorldPoint(canvas, worldX, worldY);
            render(canvas, worldX, worldY, variant, payload.color);
        }

        function cancel(pointerId = null) {
            if (!pending) return;
            if (pointerId != null && pending.pointerId !== pointerId) return;
            window.clearTimeout(pending.timer);
            pending = null;
        }

        function send(ping) {
            const variant = ping.shiftKey ? "focus" : "ping";
            if (streamerLocalMode()) {
                if (variant === "focus") focusWorldPoint(ping.canvas, ping.worldX, ping.worldY);
                render(ping.canvas, ping.worldX, ping.worldY, variant, document.body?.dataset?.pingColor);
                return;
            }
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
                render(ping.canvas, ping.worldX, ping.worldY, variant, document.body?.dataset?.pingColor);
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

    document.addEventListener("change", async (event) => {
        const input = event.target.closest?.("[data-ping-color-input]");
        if (!input || !validPreferenceColor(input.value)) return;
        const body = new URLSearchParams({ ping_color: input.value.toLowerCase() });
        const response = await fetch("/game/preferences/ping", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "x-csrftoken": typeof window.csrfToken === "function" ? window.csrfToken() : "",
            },
            body,
        });
        if (response.ok) document.body.dataset.pingColor = input.value.toLowerCase();
    });

    function validPreferenceColor(value) {
        return /^#[0-9a-f]{6}$/i.test(String(value || ""));
    }
})();
