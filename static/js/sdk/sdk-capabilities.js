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
        SHEETS_HOOKS: "sheets.hooks",
        SHEETS_COMPONENTS: "sheets.components",
        RULES_DECLARATIVE: "rules.declarative",
        RULES_EXTENDS: "rules.extends",
        DICE_ROLL: "dice.roll",
        ROLLS_INTENT: "rolls.intent",
        COMBAT_CONFIG: "combat.config",
        COMBAT_HOOKS: "combat.hooks",
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
        HOOKS_CLIENT: "hooks.client",
        COMMANDS_REGISTER: "commands.register",
    });

    // SDK method name -> required capability.
    const CAPABILITY_REQUIREMENTS = Object.freeze({
        "hooks.on": CAPABILITIES.HOOKS_CLIENT,
        "hooks.once": CAPABILITIES.HOOKS_CLIENT,
        "hooks.emit": CAPABILITIES.HOOKS_CLIENT,
        "events.on": CAPABILITIES.HOOKS_CLIENT,
        "events.once": CAPABILITIES.HOOKS_CLIENT,
        "commands.register": CAPABILITIES.COMMANDS_REGISTER,
        "chat.send": CAPABILITIES.CHAT_CARDS,
        "ui.toast": CAPABILITIES.ASSETS_UI,
        "ui.openModal": CAPABILITIES.ASSETS_UI,
        "ui.closeModal": CAPABILITIES.ASSETS_UI,
        "settings.definitions": CAPABILITIES.SETTINGS,
        "settings.all": CAPABILITIES.SETTINGS,
        "settings.get": CAPABILITIES.SETTINGS,
        "settings.set": CAPABILITIES.SETTINGS,
        "sheets.helpers": CAPABILITIES.SHEETS_HOOKS,
        "sheets.register": CAPABILITIES.SHEETS_HOOKS,
        "combat.register": CAPABILITIES.COMBAT_HOOKS,
        "combat.registerPanel": CAPABILITIES.COMBAT_HOOKS,
        "combat.callHook": CAPABILITIES.COMBAT_HOOKS,
        "combat.renderSlot": CAPABILITIES.COMBAT_HOOKS,
        "tokens.centerOn": CAPABILITIES.TOKENS_EXTENDS,
        "scene.activeCanvas": CAPABILITIES.SCENE_TOOLS,
        "scene.activeCameraForScene": CAPABILITIES.SCENE_TOOLS,
        "tools.activeTool": CAPABILITIES.SCENE_TOOLS,
        "content.packs": CAPABILITIES.CONTENT_PACKS,
        "content.pack": CAPABILITIES.CONTENT_PACKS,
        "i18n.t": CAPABILITIES.LOCALES,
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
