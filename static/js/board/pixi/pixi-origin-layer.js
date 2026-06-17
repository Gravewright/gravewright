



(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _renderOrigin(board) {
            const cam = this.camera;
            const zoom = Math.max(0.001, cam.zoom || 1);
            const arm = 10 / zoom;
            const c = this._colorAlpha(this.theme.originColor);

            board.originGfx.clear();
            board.originGfx
                .moveTo(-arm, 0)
                .lineTo(arm, 0)
                .moveTo(0, -arm)
                .lineTo(0, arm)
                .stroke({
                    width: 2 / zoom,
                    color: c.color,
                    alpha: c.alpha,
                });
        },
    });
})();
