// Gravewright SDK — browser runtime.
//
// The single public entry point for packages on the table:
//
//   window.GravewrightSDK.register({
//     id: "my-package",
//     setup(sdk, payload) { /* hooks, sheets, combat, local state */ },
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

    // --- hook bus --------------------------------------------------------------
    const listeners = new Map(); // event name -> Set<fn>

    function on(name, fn) {
        const key = String(name || "").trim();
        if (!key || typeof fn !== "function") return () => {};
        if (!listeners.has(key)) listeners.set(key, new Set());
        listeners.get(key).add(fn);
        return () => listeners.get(key)?.delete(fn);
    }

    function once(name, fn) {
        const off = on(name, (payload) => {
            off();
            fn(payload);
        });
        return off;
    }

    function emit(name, payload) {
        const set = listeners.get(String(name || "").trim());
        if (!set) return;
        for (const fn of [...set]) {
            try {
                fn(payload);
            } catch (err) {
                console.error(`GravewrightSDK hook "${name}" failed`, err);
            }
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
            hooks: Object.freeze({
                on(name, fn) {
                    requireCap("hooks.on");
                    return on(name, fn);
                },
                once(name, fn) {
                    requireCap("hooks.once");
                    return once(name, fn);
                },
                emit(name, payload) {
                    requireCap("hooks.emit");
                    return emit(name, payload);
                },
            }),
            events: Object.freeze({
                on(name, fn) {
                    requireCap("events.on");
                    return on(name, fn);
                },
                once(name, fn) {
                    requireCap("events.once");
                    return once(name, fn);
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
                callHook(name, payload) {
                    requireCap("combat.callHook");
                    return window.GravewrightCombat?.callHook?.(pkg.id, name, payload);
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
        namespaces.on = namespaces.hooks.on;
        namespaces.once = namespaces.hooks.once;
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
        // Fire game:ready once the DOM and core are up.
        gameReady = true;
        for (const id of manifestsById.keys()) {
            if (runtimes.has(id)) runReady(id);
        }
        emit("game:ready", { context });
    }

    const publicApi = {
        version: VERSION,
        register,
    };
    window.GravewrightSDK = Object.freeze(publicApi);

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
            listeners: () => Array.from(listeners.keys()),
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
