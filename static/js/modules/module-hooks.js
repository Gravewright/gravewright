(() => {
    const OFFICIAL_HOOKS = new Set([
        "module:init",
        "module:ready",
        "module:failed",
        "game:ready",
        "campaign:loaded",
        "scene:loaded",
    ]);

    function createHooks() {
        const handlers = new Map();

        function listFor(name) {
            if (!handlers.has(name)) handlers.set(name, []);
            return handlers.get(name);
        }

        function on(name, fn, options = {}) {
            const hookName = String(name || "").trim();
            if (!hookName || typeof fn !== "function") return () => {};
            const entry = {
                fn,
                moduleId: options.moduleId || "",
                order: Number.isFinite(options.order) ? options.order : 0,
                once: !!options.once,
            };
            const list = listFor(hookName);
            list.push(entry);
            list.sort((a, b) => a.order - b.order || a.moduleId.localeCompare(b.moduleId));
            return () => off(hookName, fn);
        }

        function once(name, fn, options = {}) {
            return on(name, fn, { ...options, once: true });
        }

        function off(name, fn) {
            const hookName = String(name || "").trim();
            const list = handlers.get(hookName);
            if (!list) return;
            const next = list.filter((entry) => entry.fn !== fn);
            if (next.length) handlers.set(hookName, next);
            else handlers.delete(hookName);
        }

        async function emit(name, payload) {
            const hookName = String(name || "").trim();
            const list = [...(handlers.get(hookName) || [])];
            const results = [];
            for (const entry of list) {
                try {
                    results.push(await entry.fn(payload));
                } catch (err) {
                    console.error("Gravewright module hook failed", {
                        hook: hookName,
                        moduleId: entry.moduleId,
                        error: err,
                    });
                } finally {
                    if (entry.once) off(hookName, entry.fn);
                }
            }
            return results;
        }

        function snapshot() {
            const out = {};
            handlers.forEach((list, name) => {
                out[name] = list.map((entry) => ({ moduleId: entry.moduleId, order: entry.order, once: entry.once }));
            });
            return out;
        }

        return { emit, off, on, once, officialHooks: () => [...OFFICIAL_HOOKS], snapshot };
    }

    window.GravewrightModuleHooks = { createHooks, OFFICIAL_HOOKS: [...OFFICIAL_HOOKS] };
})();
