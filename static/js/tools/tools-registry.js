








(() => {
    const DEFAULT_TOOL = "select";


    const SUB_TOOLS = {
        draw:     { options: ["select", "brush", "text"], default: "brush" },
        ruler:    { options: ["line", "circle", "square", "cone"], default: "line" },
        shape:    { options: ["select", "square", "circle", "line", "cone"], default: "square" },
        light:     { options: ["none", "torch", "pulse"], default: "torch" },


        particles: { options: ["smoke", "ember", "dust", "arcane"], default: "smoke" },
        shader: { options: ["custom"], default: "custom" },
        sound: { options: ["place"], default: "place" },
    };


    const SHORTCUTS = {
        s: "select",
        r: "ruler",
        d: "draw",
        m: "shape",
    };










    const LAYERS = ["game", "gm", "composition", "effects", "walls", "lighting"];

    const TOOL_LAYERS = {
        select: LAYERS,
        ruler: ["game", "gm"],
        draw: ["game", "gm"],
        shape: ["game", "gm"],
        wall: ["walls"],
        door: ["walls"],
        light: ["lighting"],
        particles: ["effects"],
        shader: ["effects"],
        sound: ["composition"],
    };


    function registerSubTools(toolId, def) {
        if (!toolId || !def || !Array.isArray(def.options)) return false;
        SUB_TOOLS[toolId] = { options: def.options, default: def.default || def.options[0] };
        return true;
    }


    function registerShortcut(key, toolId) {
        if (!key || !toolId) return false;
        SHORTCUTS[key.toLowerCase()] = toolId;
        return true;
    }

    function subToolsFor(toolId) {
        return SUB_TOOLS[toolId] || null;
    }

    window.GravewrightToolsRegistry = {
        DEFAULT_TOOL,
        LAYERS,
        SUB_TOOLS,
        SHORTCUTS,
        TOOL_LAYERS,
        registerSubTools,
        registerShortcut,
        subToolsFor,
    };
})();
