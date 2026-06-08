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

            if (event.key === "Delete" || event.key === "Backspace") {
                const tool = window.GravewrightTools?.activeTool ?? "select";
                const sub = window.GravewrightTools?.activeSubTool ?? "";
                if (
                    (tool === "shape" || tool === "draw")
                    && sub === "select"
                    && deleteSelectedMeasure(canvas)
                ) {
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
