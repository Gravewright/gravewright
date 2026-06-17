

(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
    const label = FI.label;
    const showMenu = FI.showMenu;

    function openMeasureMenu(e) {
        const { measure, x, y, isGm } = e.detail || {};
        if (!isGm || !measure) return;

        showMenu(x, y, [{
            text: measure.layer === "gm" ? label("ctxTokenReveal") : label("ctxTokenHide"),
            small: true,
            action() {
                document.dispatchEvent(new CustomEvent("tool:move-layer", {
                    detail: { layer: measure.layer === "gm" ? "game" : "gm" },
                }));
            },
        }]);
    }

    FI.openMeasureMenu = openMeasureMenu;
})();
