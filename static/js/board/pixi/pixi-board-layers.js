




(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _buildLayers(board) {
            board.worldLayer = new PIXI.Container();
            board.tilesLayer = new PIXI.Container();
            board.tokenWorldLayer = new PIXI.Container();
            board.tokenSpriteLayer = new PIXI.Container();
            board.tokenAdornmentLayer = new PIXI.Container();
            board.tokenWorldLayer.addChild(board.tokenSpriteLayer, board.tokenAdornmentLayer);
            board.tokenLabelLayer = new PIXI.Container();
            board.ghostWorldLayer = new PIXI.Container();
            board.originWorldLayer = new PIXI.Container();

            board.gridLayer = new PIXI.Container();
            board.gridGfx = new PIXI.Graphics();
            board.borderGfx = new PIXI.Graphics();

            board.ghostsGfx = new PIXI.Graphics();
            board.originGfx = new PIXI.Graphics();

            board.fogLayer = new PIXI.Container();
            board.fogSprite = new PIXI.Sprite(PIXI.Texture.EMPTY);
            board.fogUiGfx = new PIXI.Graphics();
            board.fogScene = new PIXI.Container();
            board.fogLayer.addChild(board.fogSprite, board.fogUiGfx);

            board.pingLayer = new PIXI.Container();
            board.pingGfx = new PIXI.Graphics();
            board.pingLayer.addChild(board.pingGfx);

            board.lightingLayer = new PIXI.Container();



            board.lightingSprite = new PIXI.Sprite(PIXI.Texture.EMPTY);
            board.lightingScene = new PIXI.Container();


            board.lightingGlowGfx = new PIXI.Container();
            board.lightingWallsGfx = new PIXI.Graphics();


            board.lightingDoorLayer = new PIXI.Container();



            board.lightingParticleGfx = new PIXI.Container();
            board.lightingLayer.addChild(
                board.lightingParticleGfx,
                board.lightingSprite,
                board.lightingGlowGfx,
                board.lightingWallsGfx,
                board.lightingDoorLayer,
            );

            board.ghostWorldLayer.addChild(board.ghostsGfx);
            board.originWorldLayer.addChild(board.originGfx);
            board.worldLayer.addChild(
                board.tilesLayer,
                board.tokenWorldLayer,
                board.ghostWorldLayer,
                board.originWorldLayer,
            );
            board.gridLayer.addChild(board.gridGfx, board.borderGfx);









            board.effectsLayer = new PIXI.Container();



            board.app.stage.addChild(
                board.worldLayer,
                board.gridLayer,
                board.tokenLabelLayer,
                board.effectsLayer,
                board.lightingLayer,
                board.fogLayer,
                board.pingLayer,
            );
        },
    });
})();
