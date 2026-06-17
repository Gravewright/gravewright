








(() => {
    const DEFAULT_TOOL = "select";

    
    const SUB_TOOLS = {
        draw:     { options: ["select", "brush", "text"], default: "brush" },
        ruler:    { options: ["line", "circle", "square", "cone"], default: "line" },
        shape:    { options: ["select", "square", "circle", "line", "cone"], default: "square" },
        hp:       { options: ["damage", "heal", "set"], default: "damage" },
    };

    
    const SHORTCUTS = {
        s: "select",
        r: "ruler",
        d: "draw",
        m: "shape",
        h: "hp",
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
        SUB_TOOLS,
        SHORTCUTS,
        registerSubTools,
        registerShortcut,
        subToolsFor,
    };
})();
