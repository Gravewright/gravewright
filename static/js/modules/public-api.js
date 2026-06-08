(() => {
    const CAPABILITIES = Object.freeze({
        CHAT_CARDS: "chat.cards",
        HOOKS_CLIENT: "hooks.client",
        SETTINGS: "settings",
        TOKENS_EXTENDS: "tokens.extends",
        UI: "assets.ui",
    });

    const CAPABILITY_REQUIREMENTS = Object.freeze({
        "chat.send": CAPABILITIES.CHAT_CARDS,
        "hooks.on": CAPABILITIES.HOOKS_CLIENT,
        "hooks.once": CAPABILITIES.HOOKS_CLIENT,
        "scene.activeCanvas": CAPABILITIES.UI,
        "scene.activeCameraForScene": CAPABILITIES.UI,
        "settings.definitions": CAPABILITIES.SETTINGS,
        "settings.all": CAPABILITIES.SETTINGS,
        "settings.get": CAPABILITIES.SETTINGS,
        "settings.set": CAPABILITIES.SETTINGS,
        "tokens.centerOn": CAPABILITIES.TOKENS_EXTENDS,
        "tools.activeTool": CAPABILITIES.UI,
        "ui.closeModal": CAPABILITIES.UI,
        "ui.openModal": CAPABILITIES.UI,
        "ui.toast": CAPABILITIES.UI,
    });

    function freezeObject(value) {
        if (!value || typeof value !== "object") return value;
        return Object.freeze(value);
    }

    function clone(value) {
        if (value == null) return value;
        try {
            return JSON.parse(JSON.stringify(value));
        } catch (_err) {
            return value;
        }
    }

    function hasCapability(module, capability) {
        const caps = module?.capabilities || [];
        return Array.isArray(caps) && caps.includes(capability);
    }

    function requireCapability(module, capability, apiName) {
        if (!module) {
            throw new Error(`${apiName || "api"} requires a scoped module api`);
        }
        if (!hasCapability(module, capability)) {
            throw new Error(`Module ${module?.id || "(unknown)"} requires capability ${capability} for ${apiName}`);
        }
    }

    function requireApiCapability(module, apiName) {
        const capability = CAPABILITY_REQUIREMENTS[apiName];
        if (capability) requireCapability(module, capability, apiName);
        return true;
    }

    function createPublicApi({ hooks, contextProvider, module = null }) {
        const scopedModule = module || null;

        function scopedHookName(name) {
            return String(name || "").trim();
        }

        const api = {
            version: "1",
            capabilities: Object.freeze({
                has(capability) {
                    return scopedModule ? hasCapability(scopedModule, capability) : false;
                },
                require(capability, apiName = "api") {
                    requireCapability(scopedModule, capability, apiName);
                    return true;
                },
                requirement(apiName) {
                    return CAPABILITY_REQUIREMENTS[String(apiName || "")] || null;
                },
                list() {
                    return Object.freeze([...(scopedModule?.capabilities || [])]);
                },
            }),
            hooks: Object.freeze({
                on(name, fn, options = {}) {
                    requireApiCapability(scopedModule, "hooks.on");
                    return hooks.on(scopedHookName(name), fn, { ...options, moduleId: scopedModule.id });
                },
                once(name, fn, options = {}) {
                    requireApiCapability(scopedModule, "hooks.once");
                    return hooks.once(scopedHookName(name), fn, { ...options, moduleId: scopedModule.id });
                },
                off: hooks.off,
                official: hooks.officialHooks,
            }),
            game: Object.freeze({
                context() {
                    return freezeObject(clone(contextProvider?.() || {}));
                },
                campaign() {
                    const ctx = contextProvider?.() || {};
                    return freezeObject(clone(ctx.campaign || null));
                },
                scene() {
                    const ctx = contextProvider?.() || {};
                    return freezeObject(clone(ctx.scene || null));
                },
                user() {
                    const ctx = contextProvider?.() || {};
                    return freezeObject(clone(ctx.user || null));
                },
            }),
            chat: Object.freeze({
                send(message) {
                    requireApiCapability(scopedModule, "chat.send");
                    document.dispatchEvent(new CustomEvent("vtt:chat-send", { detail: { message, moduleId: scopedModule.id } }));
                },
            }),
            scene: Object.freeze({
                activeCanvas() {
                    requireApiCapability(scopedModule, "scene.activeCanvas");
                    return window.GravewrightMap?.activeCanvas?.() || null;
                },
                activeCameraForScene(sceneId) {
                    requireApiCapability(scopedModule, "scene.activeCameraForScene");
                    return window.GravewrightMap?.activeCameraForScene?.(sceneId) || null;
                },
            }),
            settings: Object.freeze({
                definitions() {
                    requireApiCapability(scopedModule, "settings.definitions");
                    return freezeObject(clone(scopedModule.settings || []));
                },
                all() {
                    requireApiCapability(scopedModule, "settings.all");
                    return freezeObject(clone(scopedModule.settingValues || {}));
                },
                get(key, fallback = undefined) {
                    requireApiCapability(scopedModule, "settings.get");
                    const values = scopedModule.settingValues || {};
                    return Object.prototype.hasOwnProperty.call(values, key) ? clone(values[key]) : fallback;
                },
                async set(key, value, options = {}) {
                    requireApiCapability(scopedModule, "settings.set");
                    const http = window.GravewrightCore?.http;
                    if (!http?.postJson) throw new Error("GravewrightCore.http is not available");
                    const ctx = contextProvider?.() || {};
                    const payload = {
                        module_id: scopedModule.id,
                        key,
                        value,
                        campaign_id: options.campaignId || ctx.campaign?.id || "",
                    };
                    return http.postJson("/modules/settings", payload);
                },
            }),
            tokens: Object.freeze({
                centerOn(tokenId) {
                    requireApiCapability(scopedModule, "tokens.centerOn");
                    return window.GravewrightMap?.centerOnToken?.(tokenId);
                },
            }),
            tools: Object.freeze({
                activeTool() {
                    requireApiCapability(scopedModule, "tools.activeTool");
                    return window.GravewrightTools?.activeTool || "select";
                },
            }),
            ui: Object.freeze({
                closeModal(modalOrId) {
                    requireApiCapability(scopedModule, "ui.closeModal");
                    return window.GravewrightModals?.close?.(modalOrId);
                },
                openModal(modalId) {
                    requireApiCapability(scopedModule, "ui.openModal");
                    return window.GravewrightModals?.open?.(modalId);
                },
                toast(message, options) {
                    requireApiCapability(scopedModule, "ui.toast");
                    return window.GravewrightToasts?.show?.(message, options);
                },
            }),
        };

        return Object.freeze(api);
    }

    window.GravewrightModulePublicApi = {
        CAPABILITIES,
        CAPABILITY_REQUIREMENTS,
        createPublicApi,
        hasCapability,
        requireApiCapability,
        requireCapability,
    };
})();
