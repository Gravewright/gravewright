// Gravewright SDK — browser runtime.
//
// The single public entry point for packages on the table:
//
//   window.GravewrightSDK.register({
//     id: "my-package",
//     setup(sdk, payload) { /* plugins, sheets, combat, local state */ },
//     ready(sdk, payload) { /* after the game runtime is ready */ },
//   });
//
// Each package receives a *scoped* ``sdk`` whose namespaces are gated by the
// capabilities it declared in its manifest (see sdk-capabilities.js).
(() => {
    const caps = window.GravewrightSDKCapabilities;
    const VERSION = "1";

    // --- internal state --------------------------------------------------------
    const manifestsById = new Map(); // package id -> client manifest
    const runtimes = new Map(); // package id -> { setup, ready }
    const setupDone = new Set();
    const readyDone = new Set();
    let context = {};
    let gameReady = false;


    // --- interop bus -----------------------------------------------------------
    // The formal package-to-package channel. One provider per RPC method.
    const busListeners = new Map(); // event name -> Set<fn>

    function busSubscribe(name, fn) {
        const key = String(name || "").trim();
        if (!key || typeof fn !== "function") return () => {};
        if (!busListeners.has(key)) busListeners.set(key, new Set());
        busListeners.get(key).add(fn);
        return () => busListeners.get(key)?.delete(fn);
    }

    function busPublish(name, payload) {
        const set = busListeners.get(String(name || "").trim());
        if (!set) return;
        // Deliver an immutable copy so a listener cannot mutate shared state.
        const frozen = freeze(clone(payload));
        for (const fn of [...set]) {
            try {
                fn(frozen);
            } catch (err) {
                console.error(`GravewrightSDK bus "${name}" listener failed`, err);
            }
        }
    }

    // RPC over the bus: one provider per method. Returns a structured BusResult.
    const busProviders = new Map(); // method -> { handler, packageId }
    const BUS_DEFAULT_TIMEOUT_MS = 5000;

    function busError(code, message) {
        return { ok: false, error: { code, message: message || code } };
    }

    function busException(code, message) {
        const error = new Error(message || code);
        error.code = code;
        return error;
    }

    function interopDeclares(pkg, section, name) {
        const entries = pkg && pkg.interop && pkg.interop[section];
        return !!(entries && typeof entries === "object" && entries[name]);
    }

    function busProvide(method, handler, packageId) {
        const key = String(method || "").trim();
        if (!key || typeof handler !== "function") return () => {};
        if (busProviders.has(key)) {
            throw busException("bus.provider_conflict", `duplicate provider for "${key}"`);
        }
        busProviders.set(key, { handler, packageId });
        return () => {
            const current = busProviders.get(key);
            if (current && current.handler === handler && current.packageId === packageId) {
                busProviders.delete(key);
            }
        };
    }

    async function busRequest(method, payload, options, callerPackageId) {
        const provider = busProviders.get(String(method || "").trim());
        if (!provider) {
            return busError("bus.provider_not_found", `no provider for "${method}"`);
        }
        const timeoutMs =
            Number(options && (options.timeoutMs || options.timeout)) || BUS_DEFAULT_TIMEOUT_MS;
        const frozen = freeze(clone(payload));
        let timer;
        const providerContext = freeze({
            callerPackageId: String(callerPackageId || ""),
            providerPackageId: provider.packageId,
            userId: context.user?.id,
            campaignId: context.campaign?.id,
            permissions: clone(context.permissions || null),
        });
        const timeout = new Promise((resolve) => {
            timer = setTimeout(
                () => resolve(busError("bus.provider_timeout", "provider timed out")),
                timeoutMs
            );
        });
        try {
            const value = await Promise.race([
                Promise.resolve().then(() => provider.handler(frozen, providerContext)),
                timeout,
            ]);
            // A timeout resolves to a BusResult; a handler value is wrapped.
            if (value && value.ok === true && Object.prototype.hasOwnProperty.call(value, "value")) {
                return value;
            }
            if (value && value.ok === false && value.error) return value;
            return { ok: true, value };
        } catch (err) {
            return busError("bus.response_invalid", String((err && err.message) || err));
        } finally {
            clearTimeout(timer);
        }
    }

    // --- helpers ---------------------------------------------------------------
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

    function clone(value) {
        if (value == null) return value;
        try {
            return JSON.parse(JSON.stringify(value));
        } catch (_err) {
            return value;
        }
    }

    function freeze(value) {
        return value && typeof value === "object" ? Object.freeze(value) : value;
    }

    function currentScriptPackageIdFromSrc() {
        const src = document.currentScript?.src || "";
        if (!src) return "";
        try {
            const url = new URL(src, window.location.href);
            const match = url.pathname.match(/^\/sdk\/packages\/([^/]+)\/asset\//);
            return match ? decodeURIComponent(match[1]) : "";
        } catch (_err) {
            return "";
        }
    }

    // The package id a registering script may claim. The server tags each package
    // <script> with data-gw-package + data-gw-nonce and ships the matching
    // {id: nonce} map in the game context; the nonce must match for the declared
    // id to be honored. This makes the script <-> package binding explicit and
    // testable rather than inferred from the URL alone. Falls back to the URL when
    // the data attributes are absent (e.g. non-asset scripts).
    function currentScriptPackageId() {
        const el = document.currentScript;
        const declared = el?.dataset?.gwPackage || "";
        if (declared) {
            const nonces = (context && context.packageNonces) || {};
            const expected = nonces[declared];
            const provided = el?.dataset?.gwNonce || "";
            if (expected && provided && expected === provided) {
                return declared;
            }
            console.error(
                `GravewrightSDK refused package "${declared}": missing or invalid nonce`
            );
            return "";
        }
        return currentScriptPackageIdFromSrc();
    }

    // --- HTML sheets -----------------------------------------------------------
    const sheetControllers = new Map(); // `${packageId}:${sheetType}` -> controller
    const mountedSheets = new WeakMap(); // root -> { controller, ctx, cleanups }

    function sheetKey(packageId, sheetType) {
        return `${packageId}:${String(sheetType || "").trim()}`;
    }

    function getPath(source, path) {
        return String(path || "")
            .split(".")
            .filter(Boolean)
            .reduce((value, part) => (value == null ? undefined : value[part]), source);
    }

    function setPath(source, path, value) {
        const parts = String(path || "").split(".").filter(Boolean);
        let cursor = source;
        for (const part of parts.slice(0, -1)) {
            if (!cursor[part] || typeof cursor[part] !== "object") cursor[part] = {};
            cursor = cursor[part];
        }
        if (parts.length) cursor[parts[parts.length - 1]] = value;
    }

    function sanitizeRichText(value) {
        const template = document.createElement("template");
        template.innerHTML = String(value == null ? "" : value);
        template.content.querySelectorAll("script, iframe, object, embed").forEach((n) => n.remove());
        template.content.querySelectorAll("*").forEach((node) => {
            for (const attr of [...node.attributes]) {
                const name = attr.name.toLowerCase();
                const val = String(attr.value || "").trim().toLowerCase();
                if (name.startsWith("on") || val.startsWith("javascript:")) {
                    node.removeAttribute(attr.name);
                }
            }
        });
        return template.innerHTML;
    }

    function bindHtmlSheet(root, ctx, controller) {
        const cleanups = [];
        root.querySelectorAll("[data-text]").forEach((node) => {
            node.textContent = getPath(ctx.data, node.dataset.text) ?? "";
        });
        root.querySelectorAll("[data-rich-text]").forEach((node) => {
            node.innerHTML = sanitizeRichText(getPath(ctx.data, node.dataset.richText));
        });
        root.querySelectorAll("[data-bind]").forEach((node) => {
            const path = node.dataset.bind;
            const value = getPath(ctx.data, path);
            if ("value" in node) node.value = value ?? "";
            const onInput = () => {
                const next = node.type === "number" ? Number(node.value) : node.value;
                setPath(ctx.data, path, next);
                ctx.onChange?.(path, next);
                controller.update?.(ctx);
            };
            node.addEventListener("input", onInput);
            cleanups.push(() => node.removeEventListener("input", onInput));
        });
        root.querySelectorAll("[data-action]").forEach((node) => {
            const onClick = (event) => {
                controller.onAction?.(
                    { name: node.dataset.action, event, element: node },
                    ctx
                );
            };
            node.addEventListener("click", onClick);
            cleanups.push(() => node.removeEventListener("click", onClick));
        });
        return cleanups;
    }

    function registerSheetController(packageId, sheetType, controller) {
        const key = sheetKey(packageId, sheetType);
        if (!sheetType || !controller || typeof controller !== "object") return false;
        if (sheetControllers.has(key)) {
            throw new Error(`Duplicate sheet controller "${sheetType}" for package "${packageId}"`);
        }
        sheetControllers.set(key, { ...controller, setupDone: false });
        return true;
    }

    function mountHtmlSheet(packageId, sheetType, root, data = {}, options = {}) {
        if (!root) return false;
        // A controller is optional: an HTML sheet may declare only a template and
        // still bind data-text/data-bind. data-action is a no-op without one.
        const controller = sheetControllers.get(sheetKey(packageId, sheetType)) || {};
        const ctx = {
            packageId,
            sheetType,
            root,
            data,
            actor: data.actor || null,
            item: data.item || null,
            onChange: options.onChange,
        };
        if (!controller.setupDone) {
            controller.setup?.(ctx);
            controller.setupDone = true;
        }
        controller.mount?.(ctx);
        const cleanups = bindHtmlSheet(root, ctx, controller);
        mountedSheets.set(root, { controller, ctx, cleanups });
        return true;
    }

    function updateHtmlSheet(root, data = {}) {
        const mounted = mountedSheets.get(root);
        if (!mounted) return false;
        mounted.ctx.data = data;
        mounted.cleanups.forEach((fn) => fn());
        mounted.cleanups = bindHtmlSheet(root, mounted.ctx, mounted.controller);
        mounted.controller.update?.(mounted.ctx);
        return true;
    }

    function unmountHtmlSheet(root) {
        const mounted = mountedSheets.get(root);
        if (!mounted) return false;
        mounted.controller.unmount?.(mounted.ctx);
        mounted.cleanups.forEach((fn) => fn());
        mountedSheets.delete(root);
        return true;
    }

    // --- scoped SDK ------------------------------------------------------------
    function buildScopedSdk(pkg) {
        const requireCap = (apiName) => caps.requireApiCapability(pkg, apiName);
        const http = () => window.GravewrightCore && window.GravewrightCore.http;

        const namespaces = {
            version: VERSION,
            package: freeze({ id: pkg.id, kind: pkg.kind, version: pkg.version || "0" }),
            kind: pkg.kind,
            capabilities: Object.freeze({
                has: (c) => caps.hasCapability(pkg, c),
                require: (c, apiName = "sdk") => {
                    caps.requireCapability(pkg, c, apiName);
                    return true;
                },
                list: () => Object.freeze([...(pkg.capabilities || [])]),
            }),
            context: () => freeze(clone(context)),
            game: Object.freeze({
                context: () => freeze(clone(context)),
                campaign: () => freeze(clone(context.campaign || null)),
                scene: () => freeze(clone(context.scene || null)),
                user: () => freeze(clone(context.user || null)),
                ready: () => gameReady,
            }),
            bus: Object.freeze({
                // Formal interop bus. A package may only publish in
                // its own "{id}.*" namespace; it may subscribe to any event.
                publish(name, payload) {
                    requireCap("bus.publish");
                    const event = String(name || "");
                    if (event !== pkg.id && !event.startsWith(pkg.id + ".")) {
                        throw new Error(
                            `Package "${pkg.id}" cannot publish to foreign namespace "${event}"`
                        );
                    }
                    if (!interopDeclares(pkg, "emits", event)) {
                        throw busException(
                            "sdk.interop.event_undeclared",
                            `Package "${pkg.id}" did not declare emitted event "${event}"`
                        );
                    }
                    return busPublish(event, payload);
                },
                subscribe(name, fn) {
                    requireCap("bus.subscribe");
                    // Strict policy: a package may subscribe only to events it
                    // declared in interop.listens (any namespace, including core).
                    const event = String(name || "");
                    if (!interopDeclares(pkg, "listens", event)) {
                        throw busException(
                            "sdk.interop.event_undeclared",
                            `Package "${pkg.id}" did not declare listened event "${event}"`
                        );
                    }
                    return busSubscribe(event, fn);
                },
                provide(method, handler) {
                    requireCap("bus.provide");
                    const name = String(method || "");
                    if (name !== pkg.id && !name.startsWith(pkg.id + ".")) {
                        throw new Error(
                            `Package "${pkg.id}" cannot provide in foreign namespace "${name}"`
                        );
                    }
                    if (!interopDeclares(pkg, "provides", name)) {
                        throw busException(
                            "sdk.interop.method_undeclared",
                            `Package "${pkg.id}" did not declare provided method "${name}"`
                        );
                    }
                    return busProvide(name, handler, pkg.id);
                },
                request(method, payload, options) {
                    requireCap("bus.request");
                    // Strict policy: a package may request only methods it
                    // declared in interop.requires.
                    const name = String(method || "");
                    if (!interopDeclares(pkg, "requires", name)) {
                        throw busException(
                            "sdk.interop.method_undeclared",
                            `Package "${pkg.id}" did not declare required method "${name}"`
                        );
                    }
                    return busRequest(name, payload, options, pkg.id);
                },
            }),
            commands: Object.freeze({
                register(name, handler) {
                    requireCap("commands.register");
                    document.dispatchEvent(
                        new CustomEvent("vtt:command-register", {
                            detail: { name, handler, packageId: pkg.id },
                        })
                    );
                },
            }),
            ui: Object.freeze({
                toast(message, options) {
                    requireCap("ui.toast");
                    return window.GravewrightToasts?.show?.(message, options);
                },
                openModal(modalId) {
                    requireCap("ui.openModal");
                    return window.GravewrightModals?.open?.(modalId);
                },
                closeModal(modalOrId) {
                    requireCap("ui.closeModal");
                    return window.GravewrightModals?.close?.(modalOrId);
                },
            }),
            chat: Object.freeze({
                send(message) {
                    requireCap("chat.send");
                    document.dispatchEvent(
                        new CustomEvent("vtt:chat-send", {
                            detail: { message, packageId: pkg.id },
                        })
                    );
                },
            }),
            settings: Object.freeze({
                definitions() {
                    requireCap("settings.definitions");
                    return freeze(clone(pkg.settingDefinitions || []));
                },
                all() {
                    requireCap("settings.all");
                    return freeze(clone(pkg.settingValues || {}));
                },
                get(key, fallback = undefined) {
                    requireCap("settings.get");
                    const values = pkg.settingValues || {};
                    return Object.prototype.hasOwnProperty.call(values, key)
                        ? clone(values[key])
                        : fallback;
                },
                async set(key, value, options = {}) {
                    requireCap("settings.set");
                    const client = http();
                    if (!client?.postJson) throw new Error("GravewrightCore.http is not available");
                    const result = await client.postJson("/sdk/packages/settings", {
                        package_id: pkg.id,
                        key,
                        value,
                        campaign_id: options.campaignId || context.campaign?.id || "",
                    });
                    if (result && result.success) {
                        pkg.settingValues = { ...(pkg.settingValues || {}), [key]: result.value };
                    }
                    return result;
                },
            }),
            sheets: Object.freeze({
                helpers() {
                    requireCap("sheets.helpers");
                    return window.GravewrightSheets?.helpers || {};
                },
                register(plugin) {
                    requireCap("sheets.register");
                    return window.GravewrightSheets?.registerSystem?.(pkg.id, plugin);
                },
                registerController(sheetType, controller) {
                    requireCap("sheets.registerController");
                    return registerSheetController(pkg.id, sheetType, controller);
                },
            }),
            combat: Object.freeze({
                register(plugin) {
                    requireCap("combat.register");
                    return window.GravewrightCombat?.registerSystem?.(pkg.id, plugin);
                },
                registerPanel(panel) {
                    requireCap("combat.registerPanel");
                    if (!panel || typeof panel !== "object") return false;
                    window.GravewrightCombatPanel = Object.freeze({ ...panel });
                    return true;
                },
                dispatch(name, payload) {
                    requireCap("combat.dispatch");
                    return window.GravewrightCombat?.dispatch?.(pkg.id, name, payload);
                },
                renderSlot(name, payload) {
                    requireCap("combat.renderSlot");
                    return window.GravewrightCombat?.renderSlot?.(pkg.id, name, payload) || [];
                },
            }),
            tokens: Object.freeze({
                centerOn(tokenId) {
                    requireCap("tokens.centerOn");
                    return window.GravewrightMap?.centerOnToken?.(tokenId);
                },
            }),
            scene: Object.freeze({
                activeCanvas() {
                    requireCap("scene.activeCanvas");
                    return window.GravewrightMap?.activeCanvas?.() || null;
                },
                activeCameraForScene(sceneId) {
                    requireCap("scene.activeCameraForScene");
                    return window.GravewrightMap?.activeCameraForScene?.(sceneId) || null;
                },
            }),
            tools: Object.freeze({
                activeTool() {
                    requireCap("tools.activeTool");
                    return window.GravewrightTools?.activeTool || "select";
                },
            }),
            content: Object.freeze({
                async packs() {
                    requireCap("content.packs");
                    const client = http();
                    return client?.getJson?.(`/sdk/packages/${pkg.id}/content/packs`);
                },
                async pack(packId) {
                    requireCap("content.pack");
                    const client = http();
                    return client?.getJson?.(`/sdk/packages/${pkg.id}/content/pack/${packId}`);
                },
            }),
            storage: Object.freeze({
                // Managed SQLite storage. The package
                // never sees a path or raw SQL — only a scope, a named query, and
                // typed params. The backend validates capability/scope/permission.
                sqlite: Object.freeze({
                    async query(scope, name, params = {}) {
                        requireCap("storage.sqlite.query");
                        const client = http();
                        return client?.postJson?.(`/sdk/packages/${pkg.id}/storage/sqlite/query`, {
                            scope,
                            query: name,
                            params,
                            campaign_id: context.campaign?.id || "",
                        });
                    },
                    async execute(scope, name, params = {}) {
                        requireCap("storage.sqlite.execute");
                        const client = http();
                        return client?.postJson?.(`/sdk/packages/${pkg.id}/storage/sqlite/execute`, {
                            scope,
                            query: name,
                            params,
                            campaign_id: context.campaign?.id || "",
                        });
                    },
                    async status(scope) {
                        requireCap("storage.sqlite.status");
                        const client = http();
                        return client?.postJson?.(`/sdk/packages/${pkg.id}/storage/sqlite/status`, {
                            scope,
                            campaign_id: context.campaign?.id || "",
                        });
                    },
                }),
            }),
            i18n: Object.freeze({
                t(key, fallback) {
                    requireCap("i18n.t");
                    const catalog = pkg.locale || {};
                    return Object.prototype.hasOwnProperty.call(catalog, key)
                        ? catalog[key]
                        : fallback != null
                          ? fallback
                          : key;
                },
            }),
        };

        // Ergonomic shortcuts that delegate to the namespaces above.
        namespaces.toast = (message, options) => namespaces.ui.toast(message, options);
        namespaces.setting = (key, value) =>
            value === undefined ? namespaces.settings.get(key) : namespaces.settings.set(key, value);

        return Object.freeze(namespaces);
    }

    // --- lifecycle -------------------------------------------------------------
    function runSetup(id) {
        if (setupDone.has(id)) return;
        const runtime = runtimes.get(id);
        const pkg = manifestsById.get(id);
        if (!runtime || !pkg) return;
        setupDone.add(id);
        const sdk = buildScopedSdk(pkg);
        try {
            runtime.setup?.(sdk, { package: pkg, context });
        } catch (err) {
            console.error(`GravewrightSDK setup failed for "${id}"`, err);
        }
        if (gameReady) runReady(id);
    }

    function runReady(id) {
        if (readyDone.has(id)) return;
        const runtime = runtimes.get(id);
        const pkg = manifestsById.get(id);
        if (!runtime || !pkg) return;
        readyDone.add(id);
        const sdk = buildScopedSdk(pkg);
        try {
            runtime.ready?.(sdk, { package: pkg, context });
        } catch (err) {
            console.error(`GravewrightSDK ready failed for "${id}"`, err);
        }
    }

    function register(definition) {
        const id = String(definition?.id || "").trim();
        if (!id) {
            console.error("GravewrightSDK.register requires an id");
            return false;
        }
        const scriptPackageId = currentScriptPackageId();
        if (!scriptPackageId) {
            console.error(`GravewrightSDK.register refused "${id}" outside a package script`);
            return false;
        }
        if (scriptPackageId !== id) {
            console.error(
                `GravewrightSDK.register refused package "${id}" from script owned by "${scriptPackageId}"`
            );
            return false;
        }
        if (!manifestsById.has(id)) {
            console.error(`GravewrightSDK.register refused inactive package "${id}"`);
            return false;
        }
        if (runtimes.has(id)) {
            console.error(`GravewrightSDK.register refused duplicate package "${id}"`);
            return false;
        }
        runtimes.set(id, {
            setup: typeof definition.setup === "function" ? definition.setup : null,
            ready: typeof definition.ready === "function" ? definition.ready : null,
        });
        // A package can register before or after manifests load; only run setup
        // once we know the package is actually active in this campaign.
        runSetup(id);
        return true;
    }

    function loadManifests(manifests) {
        for (const manifest of manifests || []) {
            if (manifest && manifest.id) {
                manifestsById.set(manifest.id, {
                    ...manifest,
                    interop: manifest.interop || {},
                    settingDefinitions: manifest.settingDefinitions || [],
                    settingValues: manifest.settingValues || manifest.settings || {},
                });
            }
        }
        for (const id of manifestsById.keys()) {
            if (runtimes.has(id)) runSetup(id);
        }
    }

    function init() {
        // Run each active package's ready() once the DOM and core are up.
        gameReady = true;
        for (const id of manifestsById.keys()) {
            if (runtimes.has(id)) runReady(id);
        }
    }

    const publicApi = {
        version: VERSION,
        register,
    };
    window.GravewrightSDK = Object.freeze(publicApi);
    window.GravewrightHTMLSheets = Object.freeze({
        mount: mountHtmlSheet,
        update: updateHtmlSheet,
        unmount: unmountHtmlSheet,
        sanitizeRichText,
    });

    context = Object.freeze({ ...(parseJsonScript("gravewright-game-context", {}) || {}) });
    loadManifests(parseJsonScript("gravewright-sdk-packages", []) || []);

    // Dev-only introspection. Gated on the server-provided debug flag (wired
    // from APP_DEBUG), so it is absent in production. Tests and package authors
    // use it to confirm which packages are active and which actually registered
    // a runtime via the SDK.
    if (context.debug === true) {
        window.GravewrightSDKDebug = Object.freeze({
            packages: () => Array.from(manifestsById.values()),
            runtimes: () => Array.from(runtimes.keys()),
            context: () => context,
        });
    }

    // Defer init until DOMContentLoaded so every deferred package script has had
    // a chance to register first. ``register`` still handles late registrations.
    if (document.readyState === "complete") {
        init();
    } else {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    }
})();
