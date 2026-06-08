(() => {
    function createRegistry() {
        const modules = new Map();
        const runtimeDefinitions = new Map();
        const idPattern = /^[a-z0-9]+(-[a-z0-9]+)*$/;

        function normalizeManifest(manifest) {
            if (!manifest || typeof manifest !== "object") {
                throw new Error("Module manifest must be an object");
            }
            const id = String(manifest.id || "").trim();
            if (!idPattern.test(id)) throw new Error(`Invalid module id: ${id || "(empty)"}`);
            const version = String(manifest.version || "0.0.0").trim();
            const capabilities = Array.isArray(manifest.capabilities) ? [...manifest.capabilities] : [];
            return Object.freeze({
                ...manifest,
                id,
                version,
                name: String(manifest.name || id),
                apiVersion: String(manifest.apiVersion || manifest.api_version || "1"),
                capabilities: Object.freeze(capabilities),
                scripts: Object.freeze(Array.isArray(manifest.scripts) ? [...manifest.scripts] : []),
                styles: Object.freeze(Array.isArray(manifest.styles) ? [...manifest.styles] : []),
                settings: Object.freeze(Array.isArray(manifest.settings) ? [...manifest.settings] : []),
                settingValues: Object.freeze(manifest.settingValues && typeof manifest.settingValues === "object" ? { ...manifest.settingValues } : {}),
                hooks: Object.freeze(Array.isArray(manifest.hooks) ? [...manifest.hooks] : []),
                status: modules.get(id)?.status || "registered",
            });
        }

        function registerManifest(manifest) {
            const normalized = normalizeManifest(manifest);
            if (modules.has(normalized.id)) throw new Error(`Module already registered: ${normalized.id}`);
            modules.set(normalized.id, normalized);
            return normalized;
        }

        function registerRuntime(definition) {
            if (!definition || typeof definition !== "object") throw new Error("Module runtime definition must be an object");
            const id = String(definition.id || "").trim();
            if (!idPattern.test(id)) throw new Error(`Invalid module id: ${id || "(empty)"}`);
            const existing = runtimeDefinitions.get(id) || {};
            const merged = Object.freeze({ ...existing, ...definition, id });
            runtimeDefinitions.set(id, merged);
            return merged;
        }

        function get(id) {
            return modules.get(id) || null;
        }

        function getRuntime(id) {
            return runtimeDefinitions.get(id) || null;
        }

        function all() {
            return [...modules.values()];
        }

        function allRuntime() {
            return [...runtimeDefinitions.values()];
        }

        function setStatus(id, status, error = null) {
            const module = modules.get(id);
            if (!module) return null;
            const next = Object.freeze({ ...module, status, error });
            modules.set(id, next);
            return next;
        }

        return { all, allRuntime, get, getRuntime, registerManifest, registerRuntime, setStatus };
    }

    window.GravewrightModuleRegistry = { createRegistry };
})();
