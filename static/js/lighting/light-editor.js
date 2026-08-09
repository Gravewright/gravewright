(() => {



    const COMMIT_DELAY_MS = 180;

    let pending = null;
    let lightTarget = null;
    let visionTarget = null;

    const modals = () => window.GravewrightModals;
    const panelFor = (attribute, roomId) =>
        document.querySelector(`[${attribute}][data-room-id="${CSS.escape(roomId)}"]`);

    function flush() {
        if (!pending) return;
        window.clearTimeout(pending.timer);
        const { run } = pending;
        pending = null;
        run();
    }



    function queue(run) {
        if (pending) window.clearTimeout(pending.timer);
        pending = { run, timer: window.setTimeout(flush, COMMIT_DELAY_MS) };
    }


    const decimals = (input, value) => {


        const step = Number(input.dataset?.baseStep ?? input.step) || 1;
        const base = step >= 1 ? 0 : (step >= 0.1 ? 1 : 2);


        return Number.isInteger(Number(value)) ? base : Math.max(base, 1);
    };





    function syncEmissionRows(panel) {
        const angle = Number(panel.querySelector('[data-light-field="angle"]')?.value);
        const row = panel.querySelector('[data-light-row="rotation"]');
        if (row) row.hidden = !Number.isFinite(angle) || angle >= 360;
    }



    function paintOutput(panel, key, input, value) {
        const output = panel?.querySelector(`[data-light-output="${key}"]`);
        if (!output) return;
        const limitless = window.GravewrightLimits?.text?.(panel, key, value);
        if (limitless) { output.textContent = limitless; return; }
        const suffix = input.dataset.lightSuffix || "";
        output.textContent = Number(value).toFixed(decimals(input, value)) + suffix;
    }

    function fillLightPanel(panel, light) {
        panel.querySelectorAll("[data-light-field]").forEach((input) => {
            const key = input.dataset.lightField;
            const value = light[key];
            if (value === undefined || value === null) return;
            if (input.type === "checkbox") {
                input.checked = Boolean(value) && value !== 0;
                return;
            }
            input.value = String(value);
            paintOutput(panel, key, input, value);
        });
        syncEmissionRows(panel);


        window.GravewrightLimits?.paint?.(panel, "dim_radius");
    }

    function openLightEditor(detail) {
        const roomId = detail.canvas?.dataset?.roomId || "";
        const panel = panelFor("data-light-editor-panel", roomId);
        const light = window.GravewrightLighting?.lightFor?.(detail.canvas, detail.lightId);
        if (!panel || !light) return;
        flush();
        lightTarget = { canvas: detail.canvas, lightId: detail.lightId };
        fillLightPanel(panel, light);
        modals()?.open?.(`light-editor-${roomId}`);
    }

    document.addEventListener("input", (event) => {
        const input = event.target.closest("[data-light-field]");
        if (!input || !lightTarget) return;
        const panel = input.closest("[data-light-editor-panel]");
        const key = input.dataset.lightField;
        const raw = input.type === "range" ? Number(input.value) : input.value;
        paintOutput(panel, key, input, raw);
        if (key === "angle" && panel) syncEmissionRows(panel);
        const { canvas, lightId } = lightTarget;
        queue(() => window.GravewrightLighting?.patchLight?.(canvas, lightId, { [key]: raw }));
    });


    document.addEventListener("change", (event) => {
        const field = event.target.closest("select[data-light-field], input[type=checkbox][data-light-field]");
        if (!field || !lightTarget) return;
        const value = field.type === "checkbox" ? field.checked : field.value;
        const { canvas, lightId } = lightTarget;
        queue(() => window.GravewrightLighting?.patchLight?.(canvas, lightId, { [field.dataset.lightField]: value }));
    });



    document.addEventListener("change", (event) => {
        const check = event.target.closest('[data-limit-for="dim_radius"]');
        if (!check || !lightTarget) return;
        const panel = check.closest("[data-light-editor-panel]");
        const value = window.GravewrightLimits?.next?.(panel, "dim_radius");
        if (value === null || value === undefined) return;
        const range = panel.querySelector('[data-light-field="dim_radius"]');
        paintOutput(panel, "dim_radius", range, value);
        const { canvas, lightId } = lightTarget;
        queue(() => window.GravewrightLighting?.patchLight?.(canvas, lightId, { dim_radius: value }));
    });

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-light-delete]");
        if (!button || !lightTarget) return;
        const { canvas, lightId } = lightTarget;
        pending = null;
        lightTarget = null;
        modals()?.close?.(button.closest("[data-modal-window]"));
        window.GravewrightLighting?.deleteLight?.(canvas, lightId);
    });






    let emitterTarget = null;

    function fillEmitterPanel(panel, emitter) {
        panel.querySelectorAll("[data-particle-field]").forEach((input) => {
            const key = input.dataset.particleField;
            const value = emitter[key];
            if (value === undefined || value === null) return;
            if (input.type === "checkbox") {
                input.checked = Boolean(value) && value !== 0;
                return;
            }
            input.value = String(value);
            const output = panel.querySelector(`[data-particle-output="${key}"]`);
            if (output) output.textContent = Number(value).toFixed(decimals(input, value));
        });
    }

    function openEmitterEditor(detail) {
        const roomId = detail.canvas?.dataset?.roomId || "";
        const panel = panelFor("data-particle-editor-panel", roomId);
        const emitter = window.GravewrightLighting?.emitterFor?.(detail.canvas, detail.emitterId);
        if (!panel || !emitter) return;
        flush();
        emitterTarget = { canvas: detail.canvas, emitterId: detail.emitterId };
        fillEmitterPanel(panel, emitter);
        modals()?.open?.(`particle-editor-${roomId}`);
    }

    function patchEmitter(key, value) {
        if (!emitterTarget) return;
        const { canvas, emitterId } = emitterTarget;
        queue(() => window.GravewrightLighting?.patchEmitter?.(canvas, emitterId, { [key]: value }));
    }

    document.addEventListener("input", (event) => {
        const input = event.target.closest("[data-particle-field]");
        if (!input || !emitterTarget) return;
        const key = input.dataset.particleField;
        const raw = input.type === "range" ? Number(input.value) : input.value;
        const output = input.closest("[data-particle-editor-panel]")
            ?.querySelector(`[data-particle-output="${key}"]`);
        if (output) output.textContent = Number(raw).toFixed(decimals(input, raw));
        patchEmitter(key, raw);
    });


    document.addEventListener("change", (event) => {
        const field = event.target.closest(
            "select[data-particle-field], input[type=checkbox][data-particle-field], input[type=color][data-particle-field]",
        );
        if (!field || !emitterTarget) return;
        patchEmitter(field.dataset.particleField, field.type === "checkbox" ? field.checked : field.value);
    });

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-particle-delete]");
        if (!button || !emitterTarget) return;
        const { canvas, emitterId } = emitterTarget;
        pending = null;
        emitterTarget = null;
        modals()?.close?.(button.closest("[data-modal-window]"));
        window.GravewrightLighting?.deleteEmitter?.(canvas, emitterId);
    });

    document.addEventListener("lighting:edit-emitter", (event) => openEmitterEditor(event.detail));
    document.addEventListener("lighting:edit-light", (event) => openLightEditor(event.detail));



    function rangeLabel(panel, value) {
        const output = panel.querySelector("[data-vision-output]");
        if (!output) return;
        output.textContent = value > 0
            ? String(value)
            : document.body?.dataset?.tokenVisionUnlimited || "∞";
        window.GravewrightLimits?.paint?.(panel, "vision_range");
    }

    const previewToken = (tokenId) => document.dispatchEvent(
        new CustomEvent("token:vision-preview", { detail: { tokenId } }));



    function watchVisionPanel(modal) {
        if (!modal || modal.dataset.visionPreviewWatched === "true") return;
        modal.dataset.visionPreviewWatched = "true";
        new MutationObserver(() => {
            if (modal.hidden) {
                previewToken("");
                visionTarget = null;
            }
        }).observe(modal, { attributes: true, attributeFilter: ["hidden"] });
    }

    function openVisionEditor(detail) {
        const roomId = detail.roomId || "";
        const panel = panelFor("data-token-vision-panel", roomId);
        if (!panel) return;
        flush();
        visionTarget = { roomId, sceneId: detail.sceneId, tokenIds: detail.tokenIds, token: detail.token };
        const name = panel.querySelector("[data-token-vision-name]");
        if (name) name.textContent = detail.token?.name || "";



        const canvas = document.querySelector(`[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`);
        const notice = panel.querySelector("[data-token-vision-notice]");
        if (notice) notice.hidden = parseFloat(canvas?.dataset.sceneDarkness || "0") > 0;
        const enabled = panel.querySelector('[data-vision-field="vision_enabled"]');
        const range = panel.querySelector('[data-vision-field="vision_range"]');
        if (enabled) enabled.checked = detail.token?.vision_enabled !== false;
        if (range) {
            range.value = String(detail.token?.vision_range || 0);
            rangeLabel(panel, Number(range.value));
        }
        modals()?.open?.(`token-vision-${roomId}`);
        watchVisionPanel(panel.closest("[data-modal-window]"));
        previewToken(detail.tokenIds?.[0] || detail.token?.token_id || "");
    }

    function sendVision(panel) {
        if (!visionTarget) return;
        const enabled = panel.querySelector('[data-vision-field="vision_enabled"]');
        const range = panel.querySelector('[data-vision-field="vision_range"]');
        const payload = {
            vision_enabled: enabled ? enabled.checked : true,
            vision_range: range ? Number(range.value) : 0,
        };
        const { roomId, sceneId, tokenIds } = visionTarget;
        tokenIds.forEach((tokenId) => {
            window.GravewrightRealtime?.sendCommand(
                "token.set_vision",
                { scene_id: sceneId, token_id: tokenId, ...payload },
                { sceneId, roomId },
            );
        });
    }

    document.addEventListener("change", (event) => {
        const check = event.target.closest('[data-limit-for="vision_range"]');
        if (!check || !visionTarget) return;
        const panel = check.closest("[data-token-vision-panel]");
        const value = window.GravewrightLimits?.next?.(panel, "vision_range");
        if (value === null || value === undefined) return;
        rangeLabel(panel, value);
        queue(() => sendVision(panel));
    });

    document.addEventListener("input", (event) => {
        const input = event.target.closest("[data-vision-field]");
        if (!input || !visionTarget) return;
        const panel = input.closest("[data-token-vision-panel]");
        if (!panel) return;
        if (input.type === "range") rangeLabel(panel, Number(input.value));
        queue(() => sendVision(panel));
    });

    document.addEventListener("change", (event) => {
        const input = event.target.closest('[data-vision-field="vision_enabled"]');
        if (!input || !visionTarget) return;
        const panel = input.closest("[data-token-vision-panel]");
        if (panel) queue(() => sendVision(panel));
    });

    document.addEventListener("token:edit-vision", (event) => openVisionEditor(event.detail));


    document.addEventListener("tool:active-layer", flush);
    document.addEventListener("tool:active-tool", flush);

    window.GravewrightLightEditor = { open: openLightEditor, openEmitter: openEmitterEditor, openVision: openVisionEditor, flush };
})();
