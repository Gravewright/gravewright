(() => {
    function createBoardHistory({ limit = 100 } = {}) {
        const undoStack = [];
        const redoStack = [];

        function push(action) {
            if (!action || typeof action.undo !== "function" || typeof action.redo !== "function") return false;
            undoStack.push(action);
            if (undoStack.length > limit) undoStack.shift();
            redoStack.length = 0;
            return true;
        }

        function undo() {
            const action = undoStack.pop();
            if (!action) return false;
            action.undo();
            redoStack.push(action);
            return true;
        }

        function redo() {
            const action = redoStack.pop();
            if (!action) return false;
            action.redo();
            undoStack.push(action);
            return true;
        }

        return {
            canRedo: () => redoStack.length > 0,
            canUndo: () => undoStack.length > 0,
            push,
            redo,
            undo,
        };
    }

    window.GravewrightBoardHistory = { createBoardHistory };
})();
