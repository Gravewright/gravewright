(() => {
    const definitions = new Map();
    const instances = new Map();

    function key(packageId, applicationId) { return `${packageId}:${applicationId}`; }
    function asNode(result) {
        if (result instanceof Node) return result;
        const template = document.createElement("template");
        template.innerHTML = String(result ?? "");
        return template.content;
    }

    function register(packageId, applicationId, definition) {
        if (!packageId || !applicationId || !definition || typeof definition !== "object") {
            throw new TypeError("partial application requires package, id and definition");
        }
        const parts = definition.parts || {};
        if (!Object.keys(parts).length) throw new TypeError("partial application requires at least one part");
        definitions.set(key(packageId, applicationId), { ...definition, parts: { ...parts } });
        return () => definitions.delete(key(packageId, applicationId));
    }

    async function render(packageId, applicationId, host, context = {}, options = {}) {
        const definition = definitions.get(key(packageId, applicationId));
        if (!definition || !(host instanceof Element)) return null;
        const instanceKey = key(packageId, applicationId);
        let instance = instances.get(instanceKey);
        if (!instance || instance.host !== host) {
            instance?.close?.();
            const root = document.createElement("section");
            root.dataset.sdkApplication = applicationId;
            root.dataset.sdkPackage = packageId;
            host.replaceChildren(root);
            instance = { host, root, context: {}, cleanups: new Map() };
            instance.close = () => {
                instance.cleanups.forEach((cleanup) => cleanup?.());
                instance.cleanups.clear();
                instance.root.remove();
                instances.delete(instanceKey);
                definition.close?.(instance.context);
            };
            instances.set(instanceKey, instance);
        }
        instance.context = { ...instance.context, ...context };
        const requested = options.parts ? new Set(options.parts) : new Set(Object.keys(definition.parts));
        const active = document.activeElement;
        const focusKey = active?.closest?.("[data-focus-key]")?.dataset.focusKey;
        for (const [partId, part] of Object.entries(definition.parts)) {
            if (!requested.has(partId)) continue;
            let partRoot = instance.root.querySelector(`:scope > [data-app-part="${CSS.escape(partId)}"]`);
            if (!partRoot) {
                partRoot = document.createElement("div");
                partRoot.dataset.appPart = partId;
                instance.root.appendChild(partRoot);
            }
            instance.cleanups.get(partId)?.();
            const renderer = typeof part === "function" ? part : part.render;
            const result = await renderer?.(Object.freeze({ ...instance.context }), partRoot);
            if (result !== undefined) partRoot.replaceChildren(asNode(result));
            const activate = typeof part === "object" ? part.activate : null;
            instance.cleanups.set(partId, activate?.(partRoot, instance.context));
        }
        if (focusKey) instance.root.querySelector(`[data-focus-key="${CSS.escape(focusKey)}"]`)?.focus?.();
        definition.rendered?.(instance.root, instance.context, [...requested]);
        return Object.freeze({ root: instance.root, update: (next, parts) => render(packageId, applicationId, host, next, { parts }), close: instance.close });
    }

    window.GravewrightApplications = Object.freeze({ register, render, close(packageId, applicationId) { instances.get(key(packageId, applicationId))?.close?.(); } });
})();
