(() => {
    const STORAGE_KEY = "gravewright.tools";
    
    
    
    const Registry = window.GravewrightToolsRegistry;
    const DEFAULT_TOOL = Registry.DEFAULT_TOOL;
    const SUB_TOOLS = Registry.SUB_TOOLS;
    const SHORTCUTS = Registry.SHORTCUTS;

    let activeTool = DEFAULT_TOOL;
    const activeSubTool = {};
    let activeMarkerPresetId = "";
    let activeDrawColor = "#f8fafc";

    for (const [tool, def] of Object.entries(SUB_TOOLS)) {
        activeSubTool[tool] = def.default;
    }

    

    function toolsEnabled() {
        return Boolean(document.querySelector("[data-tool-dock]"));
    }

    function streamerMode() {
        return document.body?.dataset?.streamerMode === "true";
    }

    function getActiveDock() {
        return document.querySelector("[data-tool-dock]:not([hidden])");
    }

    function closeAllSubPanels() {
        document.querySelectorAll("[data-tool-sub-panel]").forEach((p) => {
            p.hidden = true;
        });
    }

    function positionSubPanel(panel, triggerBtn) {
        const dock = getActiveDock();
        if (!dock || !triggerBtn) return;

        const dockRect = dock.getBoundingClientRect();
        const btnRect = triggerBtn.getBoundingClientRect();

        panel.style.left = `${Math.round(dockRect.right + 8)}px`;
        panel.style.top = `${Math.round(btnRect.top + btnRect.height / 2)}px`;
        panel.style.transform = "translateY(-50%)";
    }

    function isActiveRoomGm() {
        return document.querySelector(".room-workspace.is-active")?.dataset.isGm === "true";
    }

    
    
    function syncGmOnly(panel) {
        const gm = isActiveRoomGm();
        panel.querySelectorAll("[data-gm-only]").forEach((el) => { el.hidden = !gm; });
    }

    function openSubPanel(tool) {
        closeAllSubPanels();

        const panel = document.querySelector(`[data-tool-sub-panel="${tool}"]`);
        if (!panel) return;

        if (tool === "shape") renderAreaMarkerPresets(panel);
        syncGmOnly(panel);

        const btn = getActiveDock()?.querySelector(`[data-tool="${tool}"]`);
        panel.hidden = false;
        positionSubPanel(panel, btn);
    }

    function activeCanvas() {
        return window.GravewrightMap?.activeCanvas?.()
            || document.querySelector(".room-workspace.is-active [data-map-canvas]");
    }

    function areaMarkerPresetsForActiveCanvas() {
        try {
            const raw = JSON.parse(activeCanvas()?.dataset.areaMarkerPresets || "[]");
            return Array.isArray(raw) ? raw.filter((item) => item && typeof item === "object") : [];
        } catch {
            return [];
        }
    }

    function iconForShape(shape) {
        if (shape === "circle") return "ph-circle";
        if (shape === "line") return "ph-minus";
        if (shape === "cone") return "ph-triangle";
        return "ph-square";
    }

    function markerPresetById(presetId) {
        return areaMarkerPresetsForActiveCanvas()
            .find((preset) => preset.id === presetId) || null;
    }

    function markerPresetShape(preset) {
        return SUB_TOOLS.shape.options.includes(preset?.shape) && preset.shape !== "select"
            ? preset.shape
            : "square";
    }

    function setMarkerPreset(presetId) {
        const preset = markerPresetById(presetId);
        activeMarkerPresetId = preset?.id || "";
        try { localStorage.setItem(`${STORAGE_KEY}.shape.preset`, activeMarkerPresetId); } catch {  }

        document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
            canvas.dataset.activeMarkerPreset = activeMarkerPresetId;
        });
        renderAreaMarkerPresets();

        if (preset) setSubTool("shape", markerPresetShape(preset));
        document.dispatchEvent(new CustomEvent("tool:marker-preset-changed", {
            detail: { presetId: activeMarkerPresetId },
        }));
    }

    function clearMarkerPreset() {
        if (!activeMarkerPresetId) return;
        activeMarkerPresetId = "";
        try { localStorage.setItem(`${STORAGE_KEY}.shape.preset`, ""); } catch {  }
        document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
            canvas.dataset.activeMarkerPreset = "";
        });
        renderAreaMarkerPresets();
    }

    function renderAreaMarkerPresets(panel = document.querySelector('[data-tool-sub-panel="shape"]')) {
        if (!panel) return;
        const list = panel.querySelector("[data-area-marker-presets-list]");
        const heading = panel.querySelector("[data-area-marker-presets-heading]");
        const sep = panel.querySelector("[data-area-marker-presets-sep]");
        if (!list || !heading) return;

        const presets = areaMarkerPresetsForActiveCanvas();
        list.replaceChildren();
        const visible = presets.length > 0;
        list.hidden = !visible;
        heading.hidden = !visible;
        if (sep) sep.hidden = !visible;
        if (!visible) return;

        presets.forEach((preset) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "tool-sub-btn";
            button.dataset.areaMarkerPreset = preset.id || "";
            button.setAttribute("aria-pressed", activeMarkerPresetId === preset.id ? "true" : "false");

            const swatch = document.createElement("span");
            swatch.className = "tool-sub-swatch";
            swatch.style.background = preset.style?.fill || "rgba(242, 198, 121, 0.18)";
            swatch.style.borderColor = preset.style?.stroke || "rgba(242, 198, 121, 0.95)";
            button.appendChild(swatch);

            const icon = document.createElement("i");
            icon.className = `ph ${iconForShape(preset.shape)}`;
            icon.setAttribute("aria-hidden", "true");
            button.appendChild(icon);

            const label = document.createElement("span");
            label.textContent = preset.label || preset.id || "Preset";
            button.appendChild(label);
            list.appendChild(button);
        });
    }

    

    function toggleLayersPanel(triggerBtn) {
        const panel = document.querySelector('[data-tool-sub-panel="layers"]');
        if (!panel) return;
        const isOpen = !panel.hidden;
        closeAllSubPanels();
        if (!isOpen) {
            panel.hidden = false;
            positionSubPanel(panel, triggerBtn);
        }
    }

    function setActiveLayer(layer) {
        const value = ["game", "gm", "composition"].includes(layer) ? layer : "game";
        document.querySelectorAll("[data-active-layer]").forEach((btn) => {
            btn.setAttribute("aria-pressed", btn.dataset.activeLayer === value ? "true" : "false");
        });
        document.dispatchEvent(new CustomEvent("tool:active-layer", { detail: { layer: value } }));
    }

    function setDrawColor(color) {
        if (!/^#[0-9a-fA-F]{6}$/.test(color || "")) return;
        activeDrawColor = color.toLowerCase();
        try { localStorage.setItem(`${STORAGE_KEY}.draw.color`, activeDrawColor); } catch {  }
        document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
            canvas.dataset.activeDrawColor = activeDrawColor;
        });
        document.querySelectorAll("[data-draw-color]").forEach((button) => {
            button.setAttribute("aria-pressed", button.dataset.drawColor.toLowerCase() === activeDrawColor ? "true" : "false");
        });
    }

    

    function setActiveTool(tool) {
        if (streamerMode() && tool === "hp") {
            tool = DEFAULT_TOOL;
        }
        if (!toolsEnabled()) {
            tool = DEFAULT_TOOL;
        }
        if (!document.querySelector(`[data-tool="${CSS.escape(tool)}"]`)) {
            tool = DEFAULT_TOOL;
        }

        activeTool = tool;

        document.querySelectorAll("[data-tool]").forEach((btn) => {
            btn.setAttribute("aria-pressed", btn.dataset.tool === tool ? "true" : "false");
        });

        document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
            canvas.dataset.activeTool = tool;
            canvas.dataset.activeSubtool = activeSubTool[tool] || "";
            canvas.dataset.activeMarkerPreset = activeMarkerPresetId;
            canvas.dataset.activeDrawColor = activeDrawColor;
        });

        if (SUB_TOOLS[tool]) {
            openSubPanel(tool);
        } else {
            closeAllSubPanels();
        }

        if (toolsEnabled()) {
            try { localStorage.setItem(`${STORAGE_KEY}.active`, tool); } catch {  }
        }
    }

    function setSubTool(tool, sub) {
        activeSubTool[tool] = sub;
        if (tool === "shape" && sub === "select") {
            clearMarkerPreset();
        }

        const panel = document.querySelector(`[data-tool-sub-panel="${tool}"]`);
        if (!panel) return;

        panel.querySelectorAll("[data-subtool]").forEach((btn) => {
            btn.setAttribute("aria-pressed", btn.dataset.subtool === sub ? "true" : "false");
        });

        try { localStorage.setItem(`${STORAGE_KEY}.sub.${tool}`, sub); } catch {  }

        if (activeTool === tool) {
            document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
                canvas.dataset.activeSubtool = sub || "";
                canvas.dataset.activeMarkerPreset = activeMarkerPresetId;
            });
            document.dispatchEvent(new CustomEvent("tool:subtool-changed", {
                detail: { tool, sub },
            }));
        }
    }

    function clearTool(tool) {
        const canvas = window.GravewrightMap?.activeCanvas();
        if (!canvas) return;
        canvas.dispatchEvent(new CustomEvent("tool:clear", { detail: { tool }, bubbles: true }));
    }

    function setCollapsed(dock, collapsed) {
        dock.classList.toggle("is-collapsed", collapsed);
        if (collapsed) closeAllSubPanels();
        try { localStorage.setItem(`${STORAGE_KEY}.collapsed`, collapsed ? "1" : "0"); } catch {  }
    }

    

    document.addEventListener("click", (event) => {
        const toggle = event.target.closest("[data-tool-dock-toggle]");
        if (toggle) {
            const dock = toggle.closest("[data-tool-dock]");
            if (dock) setCollapsed(dock, !dock.classList.contains("is-collapsed"));
            return;
        }

        const toolBtn = event.target.closest("[data-tool]");
        if (toolBtn?.closest("[data-tool-dock]")) {
            setActiveTool(toolBtn.dataset.tool);
            return;
        }

        const undoBtn = event.target.closest("[data-history-undo]");
        if (undoBtn) {
            window.GravewrightMap?.historyUndo?.();
            return;
        }

        const redoBtn = event.target.closest("[data-history-redo]");
        if (redoBtn) {
            window.GravewrightMap?.historyRedo?.();
            return;
        }

        const subBtn = event.target.closest("[data-subtool]");
        if (subBtn) {
            if (activeTool === "shape") clearMarkerPreset();
            setSubTool(activeTool, subBtn.dataset.subtool);
            return;
        }

        const presetBtn = event.target.closest("[data-area-marker-preset]");
        if (presetBtn) {
            setMarkerPreset(presetBtn.dataset.areaMarkerPreset || "");
            return;
        }

        const colorBtn = event.target.closest("[data-draw-color]");
        if (colorBtn) {
            setDrawColor(colorBtn.dataset.drawColor || "");
            return;
        }

        const visionBtn = event.target.closest("[data-vision-toggle]");
        if (visionBtn) {
            document.dispatchEvent(new CustomEvent("tool:vision-toggle"));
            return;
        }

        const layersBtn = event.target.closest("[data-layers-toggle]");
        if (layersBtn) {
            toggleLayersPanel(layersBtn);
            return;
        }

        const activeLayerBtn = event.target.closest("[data-active-layer]");
        if (activeLayerBtn) {
            setActiveLayer(activeLayerBtn.dataset.activeLayer);
            return;
        }

        const moveLayerBtn = event.target.closest("[data-move-layer]");
        if (moveLayerBtn) {
            document.dispatchEvent(new CustomEvent("tool:move-layer", {
                detail: { layer: moveLayerBtn.dataset.moveLayer },
            }));
            return;
        }

        const clearBtn = event.target.closest("[data-tool-clear]");
        if (clearBtn) {
            const panel = clearBtn.closest("[data-tool-sub-panel]");
            if (panel) clearTool(panel.dataset.toolSubPanel);
            return;
        }

        
        
        if (!event.target.closest("[data-tool-sub-panel]")
            && !event.target.closest("[data-map-canvas]")) {
            closeAllSubPanels();
        }
    });

    

    const tooltip = document.createElement("div");
    tooltip.className = "tool-dock-tooltip";
    tooltip.setAttribute("aria-hidden", "true");
    document.body.appendChild(tooltip);

    let tooltipTimeout = null;

    function showTooltip(btn) {
        const label = btn.dataset.tooltip;
        if (!label) return;

        tooltip.textContent = label;
        tooltip.style.opacity = "0";

        const rect = btn.getBoundingClientRect();
        const dock = btn.closest("[data-tool-dock]");
        const dockRect = dock ? dock.getBoundingClientRect() : rect;

        tooltip.style.left = `${Math.round(dockRect.right + 10)}px`;
        tooltip.style.top = `${Math.round(rect.top + rect.height / 2)}px`;
        tooltip.style.transform = "translateY(-50%)";

        clearTimeout(tooltipTimeout);
        tooltipTimeout = setTimeout(() => { tooltip.style.opacity = "1"; }, 80);
    }

    function hideTooltip() {
        clearTimeout(tooltipTimeout);
        tooltip.style.opacity = "0";
    }

    document.addEventListener("mouseover", (event) => {
        const btn = event.target.closest("[data-tool-dock] [data-tooltip]");
        if (btn) showTooltip(btn);
    });

    document.addEventListener("mouseout", (event) => {
        if (event.target.closest("[data-tool-dock] [data-tooltip]")) hideTooltip();
    });

    

    document.addEventListener("keydown", (event) => {
        if (!toolsEnabled()) return;
        if (event.target.matches("input, textarea, select, [contenteditable]")) return;
        if (event.ctrlKey || event.metaKey || event.altKey) return;

        const tool = SHORTCUTS[event.key.toLowerCase()];
        if (tool) setActiveTool(tool);
    });

    document.addEventListener("change", (event) => {
        if (event.target.matches('input[name="selected-room"]')) {
            renderAreaMarkerPresets();
        }
    });


    document.addEventListener("vtt:transport-event", (event) => {
        const { event: evtName, payload } = event.detail ?? {};
        if (evtName !== "campaign.system.changed") return;

        const roomId = payload?.room_id;
        if (!roomId) return;

        const presets = Array.isArray(payload.area_markers) ? payload.area_markers : [];
        const json = JSON.stringify(presets);
        document
            .querySelectorAll(`[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`)
            .forEach((canvas) => { canvas.dataset.areaMarkerPresets = json; });

        if (roomId !== activeCanvas()?.dataset.roomId) return;
        if (activeMarkerPresetId && !presets.some((preset) => preset?.id === activeMarkerPresetId)) {
            activeMarkerPresetId = "";
        }
        renderAreaMarkerPresets();
    });

    
    document.addEventListener("vision:changed", (event) => {
        const playerView = Boolean(event.detail?.playerView);
        document.querySelectorAll("[data-vision-toggle]").forEach((btn) => {
            btn.setAttribute("aria-pressed", playerView ? "true" : "false");
            const icon = btn.querySelector("i");
            if (icon) icon.className = playerView ? "ph ph-eye-slash" : "ph ph-eye";
        });
    });

    

    try {
        const saved = toolsEnabled() ? localStorage.getItem(`${STORAGE_KEY}.active`) : null;
        if (saved) {
            activeTool = saved;
        }

        if (toolsEnabled()) {
            for (const tool of Object.keys(SUB_TOOLS)) {
                const savedSub = localStorage.getItem(`${STORAGE_KEY}.sub.${tool}`);
                if (savedSub && SUB_TOOLS[tool].options.includes(savedSub)) {
                    activeSubTool[tool] = savedSub;
                }
            }
            const savedPreset = localStorage.getItem(`${STORAGE_KEY}.shape.preset`);
            if (savedPreset) activeMarkerPresetId = savedPreset;
            const savedDrawColor = localStorage.getItem(`${STORAGE_KEY}.draw.color`);
            if (savedDrawColor) activeDrawColor = savedDrawColor;
        }
    } catch {  }

    setActiveTool(activeTool);
    setDrawColor(activeDrawColor);

    for (const [tool, sub] of Object.entries(activeSubTool)) {
        setSubTool(tool, sub);
    }

    try {
        if (localStorage.getItem(`${STORAGE_KEY}.collapsed`) === "1") {
            document.querySelectorAll("[data-tool-dock]").forEach((dock) => {
                dock.classList.add("is-collapsed");
            });
        }
    } catch {  }

    

    window.GravewrightTools = {
        get activeTool() { return activeTool; },
        get activeSubTool() { return activeSubTool[activeTool]; },
        get activeMarkerPresetId() { return activeMarkerPresetId; },
        get activeMarkerPreset() { return markerPresetById(activeMarkerPresetId); },
        get activeDrawColor() { return activeDrawColor; },
        setActiveTool,
        clearTool,
    };
})();
