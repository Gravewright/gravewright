





(() => {
    function createMapDebug(deps) {
        const {
            activeCanvas,
            sceneDataFor,
            streaming,
            cameraFromState,
            viewportSizeFor,
            boardRenderer,
        } = deps;

        function snapshot() {
            const canvas = activeCanvas();
            if (!canvas) return { activeCanvas: false };
            const scene = sceneDataFor(canvas);
            const stream = streaming().debugSnapshot(canvas);
            return {
                activeCanvas: true,
                scene,
                camera: cameraFromState(canvas),
                viewport: viewportSizeFor(canvas),
                ...stream,
                realtimeOpen: !!window.GravewrightRealtime?.isOpen?.(),
                renderer: boardRenderer.debugSnapshot?.() || null,
            };
        }

        return { snapshot };
    }

    window.GravewrightMapDebug = { createMapDebug };
})();
