// Gravewright SDK — capability enforcement.
//
// Every package declares a set of capabilities in its manifest. SDK methods are
// gated: calling a method a package did not declare a capability for throws a
// clear, actionable error. This module owns the capability set and the
// method -> capability map shared by every scoped SDK instance.
(() => {
    const CAPABILITIES = Object.freeze({
        ACTORS_REGISTER: "actors.register",
        ITEMS_REGISTER: "items.register",
        SHEETS_DECLARATIVE: "sheets.declarative",
        SHEETS_RUNTIME: "sheets.runtime",
        SHEETS_COMPONENTS: "sheets.components",
        RULES_DECLARATIVE: "rules.declarative",
        RULES_EXTENDS: "rules.extends",
        DICE_ROLL: "dice.roll",
        ROLLS_INTENT: "rolls.intent",
        COMBAT_CONFIG: "combat.config",
        COMBAT_RUNTIME: "combat.runtime",
        TOKENS_MAPPINGS: "tokens.mappings",
        TOKENS_EXTENDS: "tokens.extends",
        SCENE_TOOLS: "scene.tools",
        SCENE_OVERLAYS: "scene.overlays",
        CHAT_CARDS: "chat.cards",
        CONTENT_PACKS: "content.packs",
        SETTINGS: "settings",
        LOCALES: "locales",
        ASSETS_UI: "assets.ui",
        ASSETS_STYLES: "assets.styles",
        ASSETS_SCRIPTS: "assets.scripts",
        ASSETS_VIDEO: "assets.video",
        COMMANDS_REGISTER: "commands.register",
        STORAGE_SQLITE: "storage.sqlite",
        BUS_PUBLISH: "bus.publish",
        BUS_SUBSCRIBE: "bus.subscribe",
        BUS_REQUEST: "bus.request",
        BUS_PROVIDE: "bus.provide",
<<<<<<< HEAD
        SHEETS_CONTROLLER: "sheets.controller",
=======
>>>>>>> origin/main
    });

    // SDK method name -> required capability.
    const CAPABILITY_REQUIREMENTS = Object.freeze({
        "commands.register": CAPABILITIES.COMMANDS_REGISTER,
        "chat.send": CAPABILITIES.CHAT_CARDS,
        "ui.toast": CAPABILITIES.ASSETS_UI,
        "ui.openModal": CAPABILITIES.ASSETS_UI,
        "ui.closeModal": CAPABILITIES.ASSETS_UI,
        "settings.definitions": CAPABILITIES.SETTINGS,
        "settings.all": CAPABILITIES.SETTINGS,
        "settings.get": CAPABILITIES.SETTINGS,
        "settings.set": CAPABILITIES.SETTINGS,
        "sheets.helpers": CAPABILITIES.SHEETS_RUNTIME,
        "sheets.register": CAPABILITIES.SHEETS_RUNTIME,
        "sheets.registerController": CAPABILITIES.SHEETS_CONTROLLER,
        "combat.register": CAPABILITIES.COMBAT_RUNTIME,
        "combat.registerPanel": CAPABILITIES.COMBAT_RUNTIME,
        "combat.dispatch": CAPABILITIES.COMBAT_RUNTIME,
        "combat.renderSlot": CAPABILITIES.COMBAT_RUNTIME,
        "tokens.centerOn": CAPABILITIES.TOKENS_EXTENDS,
        "scene.activeCanvas": CAPABILITIES.SCENE_TOOLS,
        "scene.activeCameraForScene": CAPABILITIES.SCENE_TOOLS,
        "tools.activeTool": CAPABILITIES.SCENE_TOOLS,
        "content.packs": CAPABILITIES.CONTENT_PACKS,
        "content.pack": CAPABILITIES.CONTENT_PACKS,
        "i18n.t": CAPABILITIES.LOCALES,
<<<<<<< HEAD
        "storage.sqlite.query": CAPABILITIES.STORAGE_SQLITE,
        "storage.sqlite.execute": CAPABILITIES.STORAGE_SQLITE,
        "storage.sqlite.status": CAPABILITIES.STORAGE_SQLITE,
=======
        // Experimental managed storage (Phase 7B).
        "storage.sqlite.query": CAPABILITIES.STORAGE_SQLITE,
        "storage.sqlite.execute": CAPABILITIES.STORAGE_SQLITE,
        "storage.sqlite.status": CAPABILITIES.STORAGE_SQLITE,
        // Experimental interop bus (Phase 12).
>>>>>>> origin/main
        "bus.publish": CAPABILITIES.BUS_PUBLISH,
        "bus.subscribe": CAPABILITIES.BUS_SUBSCRIBE,
        "bus.request": CAPABILITIES.BUS_REQUEST,
        "bus.provide": CAPABILITIES.BUS_PROVIDE,
    });

    function hasCapability(pkg, capability) {
        const caps = pkg && pkg.capabilities;
        return Array.isArray(caps) && caps.includes(capability);
    }

    function requireCapability(pkg, capability, apiName) {
        if (!pkg) {
            throw new Error(`${apiName || "sdk"} requires a scoped SDK instance`);
        }
        if (!hasCapability(pkg, capability)) {
            throw new Error(
                `Package "${pkg.id || "(unknown)"}" attempted to use sdk.${apiName} ` +
                    `but does not declare capability "${capability}".`
            );
        }
    }

    function requireApiCapability(pkg, apiName) {
        const capability = CAPABILITY_REQUIREMENTS[String(apiName || "")];
        if (capability) requireCapability(pkg, capability, apiName);
        return true;
    }

    window.GravewrightSDKCapabilities = Object.freeze({
        CAPABILITIES,
        CAPABILITY_REQUIREMENTS,
        hasCapability,
        requireCapability,
        requireApiCapability,
    });
})();
