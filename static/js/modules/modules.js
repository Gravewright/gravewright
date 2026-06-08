(() => {
    const hooks = window.GravewrightModuleHooks.createHooks();
    const registry = window.GravewrightModuleRegistry.createRegistry();
    let context = {};
    let initialized = false;

    function parseJsonScript(id, fallback) {
        const el = document.getElementById(id);
        if (!el) return fallback;
        try {
            return JSON.parse(el.textContent || "");
        } catch (err) {
            console.error(`Invalid JSON in #${id}`, err);
            return fallback;
        }
    }

    function setContext(nextContext = {}) {
        context = Object.freeze({ ...(nextContext || {}) });
        return context;
    }

    function contextProvider() {
        return context;
    }

    function scopedApiFor(module) {
        return window.GravewrightModulePublicApi.createPublicApi({ hooks, contextProvider, module });
    }

    const rootApi = window.GravewrightModulePublicApi.createPublicApi({ hooks, contextProvider, module: null });

    async function invokeRuntime(module, hookName) {
        const runtime = registry.getRuntime(module.id);
        if (!runtime) return;
        const api = scopedApiFor(module);
        const payload = { module, api, context };
        try {
            if (hookName === "module:init" && typeof runtime.init === "function") {
                await runtime.init(api, payload);
            } else if (hookName === "game:ready" && typeof runtime.ready === "function") {
                await runtime.ready(api, payload);
            }
        } catch (err) {
            registry.setStatus(module.id, "failed", err);
            await hooks.emit("module:failed", { module, api, error: err });
            console.error("Gravewright module runtime failed", { moduleId: module.id, hookName, error: err });
        }
    }

    async function init(manifests = null, nextContext = null) {
        if (initialized) return registry.all();
        initialized = true;

        setContext(nextContext || parseJsonScript("gravewright-game-context", {}));
        const declared = manifests || parseJsonScript("gravewright-module-manifests", []);

        for (const manifest of declared) {
            try {
                registry.registerManifest(manifest);
            } catch (err) {
                console.error("Gravewright module manifest registration failed", { manifest, error: err });
            }
        }

        for (const module of registry.all()) {
            registry.setStatus(module.id, "initializing");
            await invokeRuntime(module, "module:init");
            const current = registry.get(module.id);
            if (current?.status !== "failed") registry.setStatus(module.id, "ready");
            await hooks.emit("module:ready", { module: registry.get(module.id), api: scopedApiFor(registry.get(module.id)), context });
        }

        await hooks.emit("campaign:loaded", { campaign: context.campaign || null, context });
        if (context.scene) await hooks.emit("scene:loaded", { scene: context.scene, context });
        await hooks.emit("game:ready", { api: rootApi, context, modules: registry.all() });

        for (const module of registry.all()) {
            if (module.status !== "failed") await invokeRuntime(module, "game:ready");
        }

        return registry.all();
    }

    function register(definition) {
        return registry.registerRuntime(definition);
    }

    function apiFor(moduleId) {
        const module = registry.get(moduleId);
        if (!module) throw new Error(`Unknown module: ${moduleId}`);
        return scopedApiFor(module);
    }

    const modulesNamespace = Object.freeze({
        apiFor,
        context: contextProvider,
        init,
        list: registry.all,
        register,
        status: (moduleId) => registry.get(moduleId)?.status || "unknown",
    });

    window.GravewrightModules = {
        api: rootApi,
        hooks,
        ...modulesNamespace,
    };

    window.Gravewright = window.Gravewright || {};
    window.Gravewright.apiVersion = "1";
    window.Gravewright.modules = modulesNamespace;
    window.Gravewright.hooks = rootApi.hooks;
    window.Gravewright.game = rootApi.game;
    window.Gravewright.chat = rootApi.chat;
    window.Gravewright.scene = rootApi.scene;
    window.Gravewright.settings = rootApi.settings;
    window.Gravewright.tokens = rootApi.tokens;
    window.Gravewright.tools = rootApi.tools;
    window.Gravewright.ui = rootApi.ui;
})();
