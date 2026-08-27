(() => {
























    const SCALE = 0.5;
    const scale = () => window.GravewrightGraphicsQuality?.config?.().lightBufferScale || SCALE;

    const hexToInt = (hex) => {
        const parsed = parseInt(String(hex || "").replace("#", ""), 16);
        return Number.isFinite(parsed) ? parsed : 0xffd8a8;
    };

    const MAX_LIGHTS = 24;

    let scene = null;
    let pool = [];
    let ambient = null;

    function ensureTexture(board, cssW, cssH) {
        const activeScale = scale();
        const width = Math.max(1, Math.round(cssW * activeScale));
        const height = Math.max(1, Math.round(cssH * activeScale));
        if (board.lightBufferRT && board.lightBufferW === width && board.lightBufferH === height) {
            return board.lightBufferRT;
        }
        if (board.lightBufferRT) board.lightBufferRT.destroy(true);
        board.lightBufferRT = PIXI.RenderTexture.create({ width, height, resolution: 1 });
        board.lightBufferW = width;
        board.lightBufferH = height;
        board.lightBufferKey = "";
        return board.lightBufferRT;
    }

    function ensureScene() {
        if (scene) return scene;
        scene = new PIXI.Container();
        return scene;
    }

    function acquire(index) {
        let entry = pool[index];
        if (!entry) {
            const sprite = new PIXI.Sprite(window.GravewrightBoardInternals.falloff());
            sprite.anchor.set(0.5);


            sprite.blendMode = "add";
            const mask = new PIXI.Graphics();
            sprite.mask = mask;
            entry = { sprite, mask };
            pool[index] = entry;
        }
        entry.sprite.visible = true;
        entry.mask.clear();
        scene.addChild(entry.mask, entry.sprite);
        return entry;
    }



    function keyOf(lighting, cam, cssW, cssH) {
        const parts = [Math.round(cssW), Math.round(cssH), cam.zoom.toFixed(3),
                       Math.round(cam.offsetX), Math.round(cam.offsetY), lighting.geometryStamp,
                       (lighting.sceneDarkness ?? lighting.darkness ?? 0).toFixed(3)];
        (lighting.lights || []).forEach((light) => {
            parts.push(light.id, Math.round(light.x), Math.round(light.y),
                       Math.round(light.dim), light.color, light.alpha.toFixed(2));
        });
        return parts.join("|");
    }



    function build(board, lighting, cssW, cssH, cam) {
        if (!board?.app?.renderer || !window.GravewrightBoardInternals?.falloff) return null;
        const lights = (lighting.lights || []).filter((light) => light.alpha > 0 && light.dim > 0)
            .slice(0, MAX_LIGHTS);
        const texture = ensureTexture(board, cssW, cssH);
        const key = keyOf(lighting, cam, cssW, cssH);
        if (board.lightBufferKey === key) return texture;
        board.lightBufferKey = key;

        ensureScene();
        scene.removeChildren();
        pool.forEach(({ sprite, mask }) => { sprite.visible = false; mask.clear(); });







        if (!ambient) ambient = new PIXI.Graphics();
        ambient.clear();
        ambient.rect(0, 0, texture.width, texture.height).fill({ color: 0x000000, alpha: 1 });







        const level = Math.max(0, Math.min(1, 1 - (lighting.sceneDarkness ?? lighting.darkness ?? 0)));
        if (level > 0) {
            ambient.rect(0, 0, texture.width, texture.height)
                .fill({ color: 0xffffff, alpha: level });
        }
        scene.addChild(ambient);

        lights.forEach((light, index) => {
            const { sprite, mask } = acquire(index);
            const centre = { x: light.x * cam.zoom + cam.offsetX, y: light.y * cam.zoom + cam.offsetY };
            const activeScale = scale();
            sprite.position.set(centre.x * activeScale, centre.y * activeScale);
            sprite.width = sprite.height = light.dim * cam.zoom * 2 * activeScale;
            sprite.tint = hexToInt(light.color);
            sprite.alpha = Math.max(0, Math.min(1, light.alpha));


            const polygon = light.polygon || [];
            if (polygon.length >= 3) {
                const flat = [];
                polygon.forEach((point) => flat.push(
                    (point.x * cam.zoom + cam.offsetX) * activeScale,
                    (point.y * cam.zoom + cam.offsetY) * activeScale,
                ));
                mask.poly(flat).fill({ color: 0xffffff, alpha: 1 });
                sprite.mask = mask;
            } else {

                sprite.mask = null;
            }
        });



        board.app.renderer.render({
            container: scene, target: texture, clear: true, clearColor: [0, 0, 0, 1],
        });
        return texture;
    }

    function destroy(board) {
        if (board?.lightBufferRT) {
            board.lightBufferRT.destroy(true);
            board.lightBufferRT = null;
            board.lightBufferKey = "";
        }
    }

    window.GravewrightLightBuffer = { build, destroy, SCALE, MAX_LIGHTS };
})();
