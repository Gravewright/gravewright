(() => {















    const COMMIT_DELAY_MS = 200;



    const LIVE_FIELDS = new Set(["intensity", "opacity", "radius", "rotation", "scale", "speed", "color", "blend_mode", "enabled"]);



    const DECIMALS = { intensity: 2, opacity: 2, radius: 0, rotation: 0 };




    const casas = (key, value) => {
        const base = DECIMALS[key] ?? 1;
        return Number.isInteger(Number(value)) ? base : Math.max(base, 1);
    };



    const PROBLEMS = {
        "lighting.errors.shader_empty": "O shader está vazio.",
        "lighting.errors.shader_long": "Texto longo demais (limite de 32000 caracteres).",
        "lighting.errors.denied": "Só o mestre da mesa escreve shader.",
        "lighting.errors.invalid": "Algum valor está fora do intervalo.",
    };


    let pending = null;
    let target = null;
    const presetChoice = new WeakMap();

    const modals = () => window.GravewrightModals;
    const lighting = () => window.GravewrightLighting;
    const panelFor = (roomId) =>
        document.querySelector(`[data-shader-editor-panel][data-room-id="${CSS.escape(roomId)}"]`);
    const canvasFor = (roomId) =>
        document.querySelector(`[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`);

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

    function say(panel, message, bad) {
        const status = panel?.querySelector("[data-shader-status]");
        if (!status) return;
        status.textContent = message || "";
        status.classList.toggle("is-error", Boolean(bad));
    }

    function shadersOf(roomId) {
        const canvas = canvasFor(roomId);
        return canvas ? lighting()?.shadersFor?.(canvas) || [] : [];
    }

    function fillFields(panel, shader) {
        panel.querySelectorAll("[data-shader-field]").forEach((input) => {
            const key = input.dataset.shaderField;
            const value = shader?.[key];
            if (value === undefined || value === null) return;
            if (input.type === "checkbox") { input.checked = Boolean(value) && value !== 0; return; }
            input.value = String(value);
            paint(panel, key, input, value);
        });
    }

    const presets = () => window.GravewrightShaderPresets || [];
    const searchable = (value) => String(value || "").normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "").toLowerCase();

    function choosePreset(panel, preset) {
        const library = panel?.querySelector("[data-shader-preset-library]");
        const choice = library?.querySelector("[data-shader-preset-choice]");
        if (!library || !choice) return;
        presetChoice.set(library, preset);
        choice.hidden = !preset;
        choice.querySelector("[data-shader-preset-name]").textContent = preset?.name || "";
        choice.querySelector("[data-shader-preset-description]").textContent = preset?.description || "";
        library.querySelectorAll("[data-shader-preset-id]").forEach((button) => {
            const selected = button.dataset.shaderPresetId === preset?.id;
            button.classList.toggle("is-selected", selected);
            button.setAttribute("aria-selected", String(selected));
        });
    }

    function renderPresets(panel) {
        const library = panel?.querySelector("[data-shader-preset-library]");
        if (!library) return;
        const category = library.querySelector("[data-shader-preset-category]");
        if (!category.dataset.ready) {
            [...new Set(presets().map((preset) => preset.category))].forEach((name) => {
                const option = document.createElement("option");
                option.value = name;
                option.textContent = name;
                category.appendChild(option);
            });
            category.dataset.ready = "1";
        }
        const query = searchable(library.querySelector("[data-shader-preset-search]")?.value);
        const wantedCategory = category.value;
        const visible = presets().filter((preset) => (!wantedCategory || preset.category === wantedCategory)
            && (!query || searchable(`${preset.name} ${preset.description} ${preset.category}`).includes(query)));
        const list = library.querySelector("[data-shader-preset-list]");
        list.replaceChildren();
        if (!visible.length) {
            const empty = document.createElement("p");
            empty.className = "scene-field-hint shader-preset-empty";
            empty.textContent = library.dataset.empty || "";
            list.appendChild(empty);
            choosePreset(panel, null);
            return;
        }
        visible.forEach((preset) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "shader-preset-card";
            button.dataset.shaderPresetId = preset.id;
            button.setAttribute("role", "option");
            button.setAttribute("aria-selected", "false");
            const swatch = document.createElement("span");
            swatch.className = "shader-preset-swatch";
            swatch.style.setProperty("--preset-color", preset.color);
            const text = document.createElement("span");
            const name = document.createElement("strong");
            const kind = document.createElement("small");
            name.textContent = preset.name;
            kind.textContent = preset.category;
            text.append(name, kind);
            button.append(swatch, text);
            list.appendChild(button);
        });
        const current = presetChoice.get(library);
        choosePreset(panel, visible.find((preset) => preset.id === current?.id) || null);
    }



    function paint(panel, key, input, value) {
        const output = panel?.querySelector(`[data-shader-output="${key}"]`);
        if (!output) return;


        const limitless = window.GravewrightLimits?.text?.(panel, key, value);
        output.textContent = limitless
            || Number(value).toFixed(casas(key, value)) + (input.dataset.shaderSuffix || "");
    }

    function show(roomId, shaderId) {
        const panel = panelFor(roomId);
        if (!panel) return;
        const shader = shadersOf(roomId).find((candidate) => candidate.id === shaderId) || null;
        target = { roomId, shaderId: shader?.id || "" };
        fillFields(panel, shader || {});
        renderPresets(panel);
        window.GravewrightLimits?.paint?.(panel, "radius");
        const compileError = window.GravewrightShaderEffects?.errorFor?.(shader?.id);
        say(panel, compileError || "", Boolean(compileError));
    }

    function patch(patchValues) {
        if (!target?.shaderId) return Promise.resolve(null);
        const canvas = canvasFor(target.roomId);
        if (!canvas) return Promise.resolve(null);
        return lighting()?.patchShader?.(canvas, target.shaderId, patchValues);
    }

    function describe(error) {
        const key = String(error?.message || error || "");
        return PROBLEMS[key] || `Não foi possível salvar (${key}).`;
    }

    function updateField(event) {
        const input = event.target.closest?.("[data-shader-field]");
        if (!input || !target) return;
        const key = input.dataset.shaderField;
        const panel = input.closest("[data-shader-editor-panel]");
        paint(panel, key, input, input.value);
        if (!LIVE_FIELDS.has(key)) return;
        const value = input.type === "checkbox" ? input.checked : input.value;
        queue(() => { patch({ [key]: value })?.catch?.((error) => say(panel, describe(error), true)); });
    }

    document.addEventListener("input", (event) => {
        if (event.target?.tagName !== "SELECT") updateField(event);
    });


    document.addEventListener("change", (event) => {
        if (event.target?.tagName === "SELECT") updateField(event);
    });
    document.addEventListener("input", (event) => {
        const library = event.target.closest?.("[data-shader-preset-library]");
        if (library && event.target.matches("[data-shader-preset-search]")) {
            renderPresets(library.closest("[data-shader-editor-panel]"));
        }
    });
    document.addEventListener("change", (event) => {
        const library = event.target.closest?.("[data-shader-preset-library]");
        if (library && event.target.matches("[data-shader-preset-category]")) {
            renderPresets(library.closest("[data-shader-editor-panel]"));
        }
    });



    document.addEventListener("change", (event) => {
        const check = event.target.closest?.('[data-limit-for="radius"]');
        if (!check || !target) return;
        const panel = check.closest("[data-shader-editor-panel]");
        const value = window.GravewrightLimits?.next?.(panel, "radius");
        if (value === null || value === undefined) return;
        paint(panel, "radius", panel.querySelector('[data-shader-field="radius"]'), value);
        queue(() => { patch({ radius: value })?.catch?.((error) => say(panel, describe(error), true)); });
    });

    document.addEventListener("click", async (event) => {
        const panel = event.target.closest?.("[data-shader-editor-panel]");
        if (!panel || !target) return;
        const roomId = panel.dataset.roomId || "";

        const presetButton = event.target.closest("[data-shader-preset-id]");
        if (presetButton) {
            const preset = presets().find((candidate) => candidate.id === presetButton.dataset.shaderPresetId);
            if (preset) choosePreset(panel, preset);
            return;
        }

        if (event.target.closest("[data-shader-preset-apply]")) {
            const library = panel.querySelector("[data-shader-preset-library]");
            const preset = presetChoice.get(library);
            if (!preset) return;
            flush();
            const keys = ["source", "opacity", "intensity", "scale", "speed", "rotation",
                "radius", "color", "blend_mode", "enabled"];
            const values = Object.fromEntries(keys.map((key) => [key, preset[key]]));
            try {
                await patch(values);
                fillFields(panel, values);
                window.GravewrightLimits?.paint?.(panel, "radius");
                window.GravewrightShaderEffects?.invalidate?.(target.shaderId);
                window.GravewrightMap?.redraw?.();
                say(panel, library.dataset.applied || "", false);
            } catch (error) {
                say(panel, describe(error), true);
            }
            return;
        }

        if (event.target.closest("[data-shader-save]")) {
            flush();
            const source = panel.querySelector('[data-shader-field="source"]')?.value || "";
            try {
                await patch({ source });


                say(panel, "Salvo.", false);
            } catch (error) {
                say(panel, describe(error), true);
            }
            return;
        }

        if (event.target.closest("[data-shader-delete]")) {
            flush();
            const removed = target.shaderId;
            if (!removed) return;
            await lighting()?.deleteShader?.(canvasFor(roomId), removed);
            modals()?.close?.(`shader-editor-${roomId}`);
        }
    });




    document.addEventListener("click", async (event) => {
        const button = event.target.closest?.("[data-shader-prompt-copy]");
        if (!button) return;
        event.preventDefault();


        const field = button.previousElementSibling?.matches?.("[data-shader-prompt]")
            ? button.previousElementSibling
            : button.closest("details")?.querySelector("[data-shader-prompt]");
        if (!field) return;
        try {
            await navigator.clipboard.writeText(field.value);
        } catch {


            field.focus();
            field.select();
            return;
        }
        const label = button.querySelector("span");
        if (!label || button.dataset.busy) return;
        button.dataset.busy = "1";
        const original = label.textContent;
        label.textContent = button.dataset.copied || original;
        window.setTimeout(() => { label.textContent = original; delete button.dataset.busy; }, 1400);
    });




    document.addEventListener("vtt:shader-error", (event) => {
        if (!target || event.detail?.shaderId !== target.shaderId) return;
        say(panelFor(target.roomId), event.detail.error || "", true);
    });



    document.addEventListener("lighting:edit-shader", (event) => {
        const roomId = event.detail?.roomId || "";
        if (!roomId) return;
        show(roomId, event.detail?.shaderId);
        modals()?.open?.(`shader-editor-${roomId}`);
    });

    window.GravewrightShaderEditor = { open: (roomId, shaderId) => { show(roomId, shaderId); modals()?.open?.(`shader-editor-${roomId}`); } };
})();
