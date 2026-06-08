(() => {
    function createMeasureToolkit(deps) {
        const store = window.GravewrightMapMeasureStore.createMeasureStore();
        const geometry = window.GravewrightMapMeasureGeometry.createMeasureGeometry({
            ...deps,
            measureStoreFor: (canvas) => store.measureStoreFor(canvas),
        });
        const renderer = window.GravewrightMapMeasureRenderer.createMeasureRenderer({
            ...deps,
            flashStoreFor: (canvas) => store.flashStoreFor(canvas),
            geometry,
            measureStoreFor: (canvas) => store.measureStoreFor(canvas),
            svgStyleFor: window.GravewrightMapMeasureStore.svgStyleFor,
        });
        const editors = window.GravewrightMapMeasureEditors.createMeasureEditors({
            ...deps,
            areaMarkerTextAnchor: geometry.areaMarkerTextAnchor,
            measureStoreFor: (canvas) => store.measureStoreFor(canvas),
            newMeasureId: store.newMeasureId,
            normalizedAreaMarkerText: window.GravewrightMapMeasureStore.normalizedAreaMarkerText,
            rawMeasurePointFromEvent: geometry.rawMeasurePointFromEvent,
            worldToScreenXY: geometry.worldToScreenXY,
        });

        return {
            data: window.GravewrightMapMeasureStore,
            editors,
            geometry,
            renderer,
            store,
        };
    }

    window.GravewrightMapMeasures = { createMeasureToolkit };
})();
