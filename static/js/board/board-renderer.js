








































(() => {
    const registry = new Map();

    window.GravewrightBoard = {
        
        registerRenderer(kind, factory) {
            registry.set(kind, factory);
        },

        
        create(kind, deps) {
            const factory = registry.get(kind);
            if (!factory) {
                throw new Error(`Unknown board renderer: ${kind}`);
            }
            return factory(deps || {});
        },

        has(kind) {
            return registry.has(kind);
        },
    };
})();
