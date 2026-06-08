(() => {
    function createLoader({ api, hooks, registry }) {
        function appendScript(src, moduleId) {
            return new Promise((resolve, reject) => {
                const script = document.createElement("script");
                script.defer = true;
                script.src = src;
                script.dataset.moduleScript = moduleId;
                script.addEventListener("load", resolve, { once: true });
                script.addEventListener("error", () => reject(new Error(`Script failed: ${src}`)), { once: true });
                document.head.appendChild(script);
            });
        }

        function appendStyle(src, moduleId) {
            return new Promise((resolve, reject) => {
                const link = document.createElement("link");
                link.rel = "stylesheet";
                link.href = src;
                link.dataset.moduleStyle = moduleId;
                link.addEventListener("load", resolve, { once: true });
                link.addEventListener("error", () => reject(new Error(`Style failed: ${src}`)), { once: true });
                document.head.appendChild(link);
            });
        }

        async function loadModule(module) {
            registry.setStatus(module.id, "loading");
            try {
                for (const style of module.styles || []) await appendStyle(style, module.id);
                for (const script of module.scripts || []) await appendScript(script, module.id);
                registry.setStatus(module.id, "ready");
                await hooks.emit("module:ready", { module, api });
                return true;
            } catch (err) {
                registry.setStatus(module.id, "failed", err);
                await hooks.emit("module:failed", { module, error: err });
                console.error("Gravewright module load failed", module.id, err);
                return false;
            }
        }

        async function loadAll() {
            for (const module of registry.all()) {
                await loadModule(module);
            }
        }

        return { appendScript, appendStyle, loadAll, loadModule };
    }

    window.GravewrightModuleLoader = { createLoader };
})();
