(() => {















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


    let target = null;
    let previewPatch = {};
    let sourcePreviewTimer = null;
    const presetChoice = new WeakMap();

    const CUSTOM_FORMAT = "gravewright-custom-shader";
    const CUSTOM_VERSION = 1;
    const MAX_DEFINITION_BYTES = 40000;
    const providerRegistry = new Map();
    const DEFAULT_CUSTOM = Object.freeze({
        format: CUSTOM_FORMAT, version: CUSTOM_VERSION,
        definition: Object.freeze({
            source: "void main() { float a = 0.35 * uIntensity; finalColor = vec4(uColor * a, a); }",
            opacity: 1, intensity: 0.6, scale: 1, speed: 1, rotation: 0,
            radius: 8, color: "#8fb6ff", blend_mode: "normal", enabled: true,
        }),
    });

    function customError(code, message = code) {
        const error = new Error(message); error.code = code; return error;
    }

    function validateCustomEnvelope(value) {
        if (!value || typeof value !== "object" || value.format !== CUSTOM_FORMAT
            || value.version !== CUSTOM_VERSION || !value.definition || typeof value.definition !== "object") {
            throw customError("CUSTOM_SHADER_INVALID");
        }
        let encoded;
        try { encoded = JSON.stringify(value); } catch { throw customError("CUSTOM_SHADER_INVALID"); }
        if (new TextEncoder().encode(encoded).byteLength > MAX_DEFINITION_BYTES) throw customError("CUSTOM_SHADER_INVALID");
        const input = value.definition;
        const source = String(input.source || "");
        if (!source.trim() || new TextEncoder().encode(source).byteLength > 32000) throw customError("CUSTOM_SHADER_INVALID");
        const number = (key, fallback, min, max) => {
            const result = input[key] === undefined ? fallback : Number(input[key]);
            if (!Number.isFinite(result) || result < min || result > max) throw customError("CUSTOM_SHADER_INVALID");
            return result;
        };
        const blend = String(input.blend_mode || "normal");
        const color = String(input.color || "#8fb6ff").toLowerCase();
        if (!new Set(["normal", "add", "multiply", "screen"]).has(blend) || !/^#[0-9a-f]{6}$/.test(color)) {
            throw customError("CUSTOM_SHADER_INVALID");
        }
        return Object.freeze({ format: CUSTOM_FORMAT, version: CUSTOM_VERSION, definition: Object.freeze({
            source, opacity: number("opacity", 1, 0, 1), intensity: number("intensity", .6, 0, 1),
            scale: number("scale", 1, .1, 20), speed: number("speed", 1, 0, 8),
            rotation: number("rotation", 0, 0, 359), radius: number("radius", 8, 0, 120),
            color, blend_mode: blend, enabled: input.enabled !== false,
        }) });
    }

    async function validateCustomForCore(value, roomId) {
        const envelope = validateCustomEnvelope(value);
        const canvas = canvasFor(roomId);
        lighting()?.previewCustomDefinition?.(canvas, envelope.definition);
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const problem = window.GravewrightShaderEffects?.errorFor?.("__gravewright_custom_shader_preview__");
        lighting()?.clearCustomDefinitionPreview?.(canvas);
        if (problem) throw customError("CUSTOM_SHADER_INVALID", problem);
        return envelope;
    }

    const modals = () => window.GravewrightModals;
    const lighting = () => window.GravewrightLighting;
    const panelFor = (roomId) =>
        document.querySelector(`[data-shader-editor-panel][data-room-id="${CSS.escape(roomId)}"]`);
    const canvasFor = (roomId) =>
        document.querySelector(`[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`);

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
        panel.querySelector("[data-shader-delete]")?.removeAttribute("hidden");
        previewPatch = {};
        fillFields(panel, shader || {});
        renderPresets(panel);
        window.GravewrightLimits?.paint?.(panel, "radius");
        const compileError = window.GravewrightShaderEffects?.errorFor?.(shader?.id);
        say(panel, compileError || "", Boolean(compileError));
    }

    function showCustom(roomId, envelope, resolve) {
        const panel = panelFor(roomId);
        if (!panel) throw customError("CUSTOM_SHADER_UNAVAILABLE");
        const value = validateCustomEnvelope(envelope || DEFAULT_CUSTOM);
        target = { roomId, shaderId: "", mode: "custom-library", resolve, settled: false };
        previewPatch = {};
        fillFields(panel, value.definition);
        panel.querySelector("[data-shader-delete]")?.setAttribute("hidden", "");
        renderPresets(panel);
        lighting()?.previewCustomDefinition?.(canvasFor(roomId), value.definition);
        say(panel, "", false);
    }

    function patch(patchValues) {
        if (!target?.shaderId) return Promise.resolve(null);
        const canvas = canvasFor(target.roomId);
        if (!canvas) return Promise.resolve(null);
        return lighting()?.patchShader?.(canvas, target.shaderId, patchValues);
    }

    function valueOf(input) {
        if (input.type === "checkbox") return input.checked;
        if (["color", "text"].includes(input.type) || ["SELECT", "TEXTAREA"].includes(input.tagName)) return input.value;
        const value = Number(input.value);
        if (!Number.isFinite(value)) return null;
        const min = input.min === "" ? -Infinity : Number(input.min);
        const max = input.max === "" ? Infinity : Number(input.max);
        return value < min || value > max ? null : value;
    }

    function preview(input, panel) {
        const key = input.dataset.shaderField;
        const value = valueOf(input);
        if (value === null) { say(panel, PROBLEMS["lighting.errors.invalid"], true); return false; }
        previewPatch[key] = value;
        const canvas = canvasFor(target.roomId);
        if (target.mode === "custom-library") lighting()?.previewCustomDefinition?.(canvas, { ...fieldsFrom(panel), [key]: value });
        else lighting()?.previewShader?.(canvas, target.shaderId, { [key]: value });
        say(panel, "", false);
        return true;
    }

    function fieldsFrom(panel) {
        const values = {};
        panel?.querySelectorAll("[data-shader-field]").forEach((input) => {
            const value = valueOf(input);
            if (value !== null) values[input.dataset.shaderField] = value;
        });
        return values;
    }

    async function commitPreview(panel) {
        if (target?.mode === "custom-library") { previewPatch = {}; return; }
        if (!target?.shaderId || !Object.keys(previewPatch).length) return;
        const values = previewPatch;
        previewPatch = {};
        try {
            await lighting()?.commitShaderPreview?.(canvasFor(target.roomId), target.shaderId, values);
            say(panel, "Salvo.", false);
        } catch (error) {
            say(panel, describe(error), true);
            const shader = shadersOf(target.roomId).find((candidate) => candidate.id === target.shaderId);
            fillFields(panel, shader || {});
        }
    }

    function cancelPreview() {
        if (!target) return;
        window.clearTimeout(sourcePreviewTimer);
        if (target.mode === "custom-library") lighting()?.clearCustomDefinitionPreview?.(canvasFor(target.roomId));
        else if (target.shaderId) lighting()?.restoreShaderPreview?.(canvasFor(target.roomId), target.shaderId);
        previewPatch = {};
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
        preview(input, panel);
    }

    document.addEventListener("input", (event) => {
        if (event.target?.tagName !== "SELECT") updateField(event);
        const source = event.target.closest?.('[data-shader-field="source"]');
        if (!source || !target) return;
        window.clearTimeout(sourcePreviewTimer);
        sourcePreviewTimer = window.setTimeout(() => {
            if (target.mode === "custom-library") lighting()?.previewCustomDefinition?.(canvasFor(target.roomId), fieldsFrom(source.closest("[data-shader-editor-panel]")));
            else if (target.shaderId) lighting()?.previewShader?.(canvasFor(target.roomId), target.shaderId, { source: source.value });
            window.GravewrightMap?.redraw?.();
        }, 350);
    });


    document.addEventListener("change", (event) => {
        if (event.target?.tagName === "SELECT") updateField(event);
        const input = event.target.closest?.("[data-shader-field]");
        if (input && LIVE_FIELDS.has(input.dataset.shaderField)) void commitPreview(input.closest("[data-shader-editor-panel]"));
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
        preview(panel.querySelector('[data-shader-field="radius"]'), panel);
        void commitPreview(panel);
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
            await commitPreview(panel);
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
            if (target.mode === "custom-library") {
                try {
                    const definition = await validateCustomForCore({ format: CUSTOM_FORMAT, version: CUSTOM_VERSION, definition: fieldsFrom(panel) }, roomId);
                    const complete = target; complete.settled = true;
                    cancelPreview(); complete.resolve(definition); target = null;
                    modals()?.close?.(`shader-editor-${roomId}`);
                } catch (error) { say(panel, error.code || "CUSTOM_SHADER_INVALID", true); }
                return;
            }
            await commitPreview(panel);
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
            await commitPreview(panel);
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

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape" || !target) return;
        cancelPreview();
        const panel = panelFor(target.roomId);
        const shader = shadersOf(target.roomId).find((candidate) => candidate.id === target.shaderId);
        fillFields(panel, shader || {});
    }, true);
    document.addEventListener("vtt:modal-closed", (event) => {
        const modalId = event.detail?.modal?.dataset?.modalId || event.detail?.modal?.id || "";
        if (target?.roomId && modalId === `shader-editor-${target.roomId}`) {
            const closing = target; cancelPreview();
            if (closing.mode === "custom-library" && !closing.settled) closing.resolve(null);
            target = null;
        }
    });



    document.addEventListener("lighting:edit-shader", (event) => {
        const roomId = event.detail?.roomId || "";
        if (!roomId) return;
        show(roomId, event.detail?.shaderId);
        modals()?.open?.(`shader-editor-${roomId}`);
    });

    function registerProvider(packageId, definition) {
        const localId = String(definition?.id || "");
        if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(localId) || typeof definition?.open !== "function") {
            throw new TypeError("custom shader provider requires a kebab-case id and open callback");
        }
        const id = `${packageId}.${localId}`;
        if (providerRegistry.has(id)) throw customError("CUSTOM_SHADER_PROVIDER_DUPLICATE");
        providerRegistry.set(id, Object.freeze({ id, packageId, label: String(definition.label || localId).slice(0, 80), description: String(definition.description || "").slice(0, 240), open: definition.open }));
        return () => providerRegistry.delete(id);
    }

    function openProviderPicker() {
        const providers = [...providerRegistry.values()];
        if (!providers.length) return false;
        if (providers.length === 1) { Promise.resolve().then(() => providers[0].open()).catch(() => {}); return true; }
        const dialog = document.createElement("dialog");
        dialog.className = "custom-shader-provider-picker";
        const heading = document.createElement("h2"); heading.textContent = "Custom shader libraries"; dialog.appendChild(heading);
        providers.forEach((provider) => {
            const button = document.createElement("button"); button.type = "button";
            button.textContent = provider.label; button.title = provider.description;
            button.addEventListener("click", () => { dialog.close(); Promise.resolve(provider.open()).catch(() => {}); });
            dialog.appendChild(button);
        });
        dialog.addEventListener("close", () => dialog.remove(), { once: true });
        document.body.appendChild(dialog); dialog.showModal(); return true;
    }

    function openCustomEditor(definition) {
        const roomId = document.querySelector(".room-workspace.is-active")?.dataset.roomId || "";
        if (!roomId || document.querySelector(".room-workspace.is-active")?.dataset.isGm !== "true") return Promise.reject(customError("PERMISSION_DENIED"));
        return new Promise((resolve, reject) => {
            try { showCustom(roomId, definition || DEFAULT_CUSTOM, resolve); modals()?.open?.(`shader-editor-${roomId}`); }
            catch (error) { reject(error); }
        });
    }

    async function useCustomDefinition(definition) {
        const workspace = document.querySelector(".room-workspace.is-active");
        if (!workspace || workspace.dataset.isGm !== "true") throw customError("PERMISSION_DENIED");
        const value = await validateCustomForCore(definition, workspace.dataset.roomId || "");
        if (!window.GravewrightTools?.selectCustomShaderDefinition) throw customError("CUSTOM_SHADER_UNAVAILABLE");
        window.GravewrightTools.selectCustomShaderDefinition(value);
        return Object.freeze({ accepted: true });
    }

    function previewCustomDefinition(definition) {
        const workspace = document.querySelector(".room-workspace.is-active");
        if (!workspace || workspace.dataset.isGm !== "true") throw customError("PERMISSION_DENIED");
        const value = validateCustomEnvelope(definition);
        lighting()?.previewCustomDefinition?.(canvasFor(workspace.dataset.roomId || ""), value.definition);
        return Object.freeze({ active: true });
    }

    function clearCustomPreview() {
        const roomId = document.querySelector(".room-workspace.is-active")?.dataset.roomId || "";
        if (roomId) lighting()?.clearCustomDefinitionPreview?.(canvasFor(roomId));
        return Object.freeze({ active: false });
    }

    window.GravewrightShaderEditor = { open: (roomId, shaderId) => { show(roomId, shaderId); modals()?.open?.(`shader-editor-${roomId}`); } };
    window.GravewrightCustomShaderLibraries = Object.freeze({ registerProvider, openProviderPicker, openEditor: openCustomEditor, preview: previewCustomDefinition, clearPreview: clearCustomPreview, use: useCustomDefinition, validate: validateCustomEnvelope });
})();
