(() => {
    function bindKeyboardEvents(deps) {
        const {
            activeCanvas,
            boardPing,
            clearMeasures,
            deleteSelectedMeasure,
            getMeasureController,
            history,
            mapAddToScene,
            selectedSet,
            stopAddToScene,
            tokenDelete,
            tokenClipboard,
            tokenSteps,
        } = deps;

        function isTextInput(target) {
            const tag = (target?.tagName || "").toLowerCase();
            return tag === "input" || tag === "textarea" || target?.isContentEditable;
        }

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && mapAddToScene.isActive()) {
                stopAddToScene();
            }
            if (event.key === "Escape") {
                getMeasureController()?.handleEscape();
            }

            if (isTextInput(event.target)) return;
            if (window.GravewrightFog?.isActive?.()) return;

            const canvas = activeCanvas();
            if (!canvas) return;
            const componentLayer = ["walls", "lighting", "effects"].includes(window.GravewrightTools?.activeLayer);
            const sceneImageSelection = Boolean(document.querySelector?.(".scene-image.is-selected"));

            if (event.key === "Shift") {
                boardPing.setShiftKey(true);
            }

            if ((event.ctrlKey || event.metaKey) && (event.key === "z" || event.key === "Z")) {
                const isRedo = event.shiftKey;
                if (isRedo ? history?.canRedo?.() : history?.canUndo?.()) {
                    event.preventDefault();
                    if (isRedo) history.redo();
                    else history.undo();
                }
                return;
            }

            if ((event.ctrlKey || event.metaKey) && (event.key === "y" || event.key === "Y")) {
                if (history?.canRedo?.()) {
                    event.preventDefault();
                    history.redo();
                }
                return;
            }

            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "c") {
                const measureTool = ["shape", "draw"].includes(window.GravewrightTools?.activeTool);
                if (measureTool && getMeasureController()?.copySelectedMeasure?.(canvas)) {
                    event.preventDefault();
                    return;
                }
                if (!componentLayer && tokenClipboard?.copy?.(canvas)) event.preventDefault();
                return;
            }

            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "v") {
                const measureTool = ["shape", "draw"].includes(window.GravewrightTools?.activeTool);
                if (measureTool && getMeasureController()?.pasteMeasure?.(canvas)) {
                    event.preventDefault();
                    return;
                }
                if (!componentLayer && tokenClipboard?.paste?.(canvas)) event.preventDefault();
                return;
            }



            if (!componentLayer && !sceneImageSelection && tokenSteps?.handles?.(event.key)) {
                if (tokenSteps.step(canvas, event.key)) {
                    event.preventDefault();
                    return;
                }
            }

            if (event.key === "Delete" || event.key === "Backspace") {
                if (componentLayer || sceneImageSelection) return;
                const tool = window.GravewrightTools?.activeTool ?? "select";
                if (
                    (tool === "shape" || tool === "draw")
                    && deleteSelectedMeasure(canvas, { domain: tool })
                ) {
                    event.preventDefault();
                    return;
                }
                if (tool === "select" && deleteSelectedMeasure(canvas, { domain: "shape" })) {
                    event.preventDefault();
                    return;
                }
                if (!selectedSet(canvas).size) return;
                event.preventDefault();
                tokenDelete.deleteSelected(canvas);
            }
        });

        document.addEventListener("keyup", (event) => {
            if (event.key === "Shift") {
                boardPing.setShiftKey(false);
            }
        });

        document.addEventListener("tool:subtool-changed", (event) => {
            getMeasureController()?.handleSubtoolChanged(event.detail);
        });

        document.addEventListener("tool:clear", (event) => {
            if (["ruler", "shape", "draw"].includes(event.detail?.tool)) {
                clearMeasures(event.target.closest?.("[data-map-canvas]") || activeCanvas(), {
                    tool: event.detail.tool,
                });
            }
        });
    }

    window.GravewrightMapKeyboardEvents = { bindKeyboardEvents };
})();
