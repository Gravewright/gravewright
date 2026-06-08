














(() => {
    const TileBlobCache = (() => {
        const DB_NAME = "gravewright-map-tile-cache";
        const STORE = "tiles";
        const MAX_ENTRIES = 15000;
        let dbPromise = null;
        let supported = typeof indexedDB !== "undefined" && typeof URL !== "undefined";

        function enabled() {
            return supported;
        }

        function openDb() {
            if (!supported) return Promise.resolve(null);
            if (dbPromise) return dbPromise;
            dbPromise = new Promise((resolve) => {
                const req = indexedDB.open(DB_NAME, 1);
                req.onupgradeneeded = () => {
                    const db = req.result;
                    if (!db.objectStoreNames.contains(STORE)) {
                        const store = db.createObjectStore(STORE, { keyPath: "url" });
                        store.createIndex("lastUsedAt", "lastUsedAt");
                    }
                };
                req.onerror = () => {
                    supported = false;
                    resolve(null);
                };
                req.onsuccess = () => resolve(req.result);
            });
            return dbPromise;
        }

        async function get(url) {
            const db = await openDb();
            if (!db) return null;
            return new Promise((resolve) => {
                const tx = db.transaction(STORE, "readwrite");
                const store = tx.objectStore(STORE);
                const req = store.get(url);
                req.onerror = () => resolve(null);
                req.onsuccess = () => {
                    const row = req.result;
                    if (!row?.blob) {
                        resolve(null);
                        return;
                    }
                    row.lastUsedAt = Date.now();
                    store.put(row);
                    resolve(row.blob);
                };
            });
        }

        async function put(url, blob) {
            const db = await openDb();
            if (!db || !blob) return;
            await new Promise((resolve) => {
                const tx = db.transaction(STORE, "readwrite");
                tx.oncomplete = resolve;
                tx.onerror = resolve;
                tx.objectStore(STORE).put({ url, blob, lastUsedAt: Date.now() });
            });
            void prune(db);
        }

        async function prune(db) {
            try {
                const count = await new Promise((resolve) => {
                    const tx = db.transaction(STORE, "readonly");
                    const req = tx.objectStore(STORE).count();
                    req.onsuccess = () => resolve(req.result || 0);
                    req.onerror = () => resolve(0);
                });
                const extra = Math.max(0, count - MAX_ENTRIES);
                if (!extra) return;
                await new Promise((resolve) => {
                    let removed = 0;
                    const tx = db.transaction(STORE, "readwrite");
                    const index = tx.objectStore(STORE).index("lastUsedAt");
                    tx.oncomplete = resolve;
                    tx.onerror = resolve;
                    index.openCursor().onsuccess = (event) => {
                        const cursor = event.target.result;
                        if (!cursor || removed >= extra) return;
                        cursor.delete();
                        removed += 1;
                        cursor.continue();
                    };
                });
            } catch {
                
            }
        }

        return { enabled, get, put };
    })();

    window.GravewrightTileBlobCache = window.GravewrightTileBlobCache || TileBlobCache;

    class PixiBoardRenderer {
        constructor(deps) {
            this.deps = deps || {};
            this.boards = new Map();
            this.textures = new Map();
            this.textureObjectUrls = new Map();
            this.active = null;

            this.theme = {
                background: "#11151a",
                gridColor: "rgba(192,154,90,0.18)",
                originColor: "rgba(192,154,90,0.45)",
                sceneBorderColor: "rgba(255,255,255,0.12)",
            };
            this.scene = null;
            this.camera = { offsetX: 0, offsetY: 0, zoom: 1 };
            this.tiles = null;
            this.tokens = [];
            this.overlays = {};
            this.fog = null;
        }

        attach(canvas) {
            this.active = canvas;
            if (!this.boards.has(canvas)) {
                this.boards.set(canvas, this._createBoard(canvas));
            }
        }

        detach() {
            this.active = null;
        }

        resize() {
            
        }

        setTheme(theme) {
            if (theme) this.theme = theme;
        }

        setScene(scene) {
            this.scene = scene;
        }

        setCamera(camera) {
            if (camera) this.camera = camera;
        }

        setTiles(tiles) {
            this.tiles = tiles;
        }

        setTokens(tokens) {
            this.tokens = tokens || [];
        }

        setOverlays(overlays) {
            this.overlays = overlays || {};
        }

        setFog(fog) {
            this.fog = fog || null;
        }

        render() {
            const board = this.active && this.boards.get(this.active);
            if (!board || !board.ready) return;

            const { width: cssW, height: cssH } = this._cssSize(this.active);

            if (board.cssW !== cssW || board.cssH !== cssH) {
                board.app.renderer.resize(cssW, cssH);
                board.cssW = cssW;
                board.cssH = cssH;
            }

            board.app.renderer.background.color = this._color(this.theme.background);

            this._renderTiles(board, cssW, cssH);
            this._renderGrid(board, cssW, cssH);
            this._renderTokens(board, cssW, cssH);
            this._renderGhosts(board);
            this._renderOrigin(board);
            this._renderFog(board, cssW, cssH);

            board.app.render();
        }

        _createBoard(canvas) {
            const board = {
                app: new PIXI.Application(),
                ready: false,
                cssW: 0,
                cssH: 0,

                worldLayer: null,
                tilesLayer: null,
                gridLayer: null,
                gridGfx: null,
                borderGfx: null,
                tokenWorldLayer: null,
                tokenLabelLayer: null,
                ghostWorldLayer: null,
                originWorldLayer: null,
                ghostsGfx: null,
                originGfx: null,

                
                fogLayer: null,
                fogSprite: null,
                fogUiGfx: null,
                fogScene: null,   
                fogRT: null,
                fogRTW: 0,
                fogRTH: 0,
                fogRTDpr: 0,
                fogKey: "",
                fogGfxPool: [],
                fogPoolIndex: 0,

                tileSprites: new Map(),
                tokenNodes: new Map(),
                tilePlanKey: "",
                tilePlan: [],
                tileRenderPass: 0,
            };

            const { width, height } = this._cssSize(canvas);

            this._initApp(board.app, {
                canvas,
                width,
                height,
                resolution: window.devicePixelRatio || 1,
                autoDensity: true,

                
                
                antialias: false,

                autoStart: false,
                background: this._color(this.theme.background),
            })
                .then(() => {
                    this._buildLayers(board);

                    board.ready = true;
                    this.deps.requestRender?.();
                })
                .catch((err) => {
                    console.error("PixiBoardRenderer init failed", err);
                });

            return board;
        }

        _initApp(app, options) {
            const preference = PIXI.isWebGLSupported() ? "webgl" : "canvas";
            return app.init({ ...options, preference });
        }

        _color(css) {
            try {
                return new PIXI.Color(css).toNumber();
            } catch {
                return 0x11151a;
            }
        }

        _colorAlpha(css) {
            const m = /rgba?\(([^)]+)\)/.exec(css);

            if (m) {
                const parts = m[1].split(",").map((p) => parseFloat(p.trim()));
                const [r, g, b, a = 1] = parts;

                return {
                    color: (r << 16) | (g << 8) | b,
                    alpha: a,
                };
            }

            return {
                color: this._color(css),
                alpha: 1,
            };
        }

        _texture(url) {
            const cached = this.textures.get(url);
            if (cached === "loading" || cached === "error") return null;
            if (cached) return cached;

            this.textures.set(url, "loading");

            
            
            this._loadTextureSource(url)
                .then((sourceUrl) => PIXI.Assets.load({
                    src: sourceUrl,
                    alias: url,
                    loadParser: "loadTextures",
                }))
                .then((texture) => {
                    if (!texture) {
                        throw new Error("Pixi returned no texture for image URL");
                    }

                    if (this.textures.get(url) !== "loading") return;

                    this.textures.set(url, texture);
                    this.deps.requestRender?.();
                })
                .catch((err) => {
                    if (this.textures.get(url) !== "loading") return;

                    this.textures.set(url, "error");
                    console.error("PixiBoardRenderer texture load failed", url, err);
                });

            return null;
        }

        async _loadTextureSource(url) {
            const cache = window.GravewrightTileBlobCache;
            if (!cache || !cache.enabled?.() || !url.includes("/game/scenes/")) return url;

            const cached = await cache.get(url);
            if (cached) return this._objectUrlFor(url, cached);

            const response = await fetch(url, {
                credentials: "same-origin",
                cache: "force-cache",
            });
            if (!response.ok) throw new Error(`Texture request failed: ${response.status}`);
            const blob = await response.blob();
            await cache.put(url, blob);
            return this._objectUrlFor(url, blob);
        }

        _objectUrlFor(url, blob) {
            const current = this.textureObjectUrls.get(url);
            if (current) return current;
            const objectUrl = URL.createObjectURL(blob);
            this.textureObjectUrls.set(url, objectUrl);
            return objectUrl;
        }

        _cssSize(canvas) {
            const rect = canvas.getBoundingClientRect();

            return {
                width: rect.width || canvas.clientWidth || window.innerWidth,
                height: rect.height || canvas.clientHeight || window.innerHeight,
            };
        }
    }

    
    
    window.GravewrightBoardInternals = window.GravewrightBoardInternals || {};
    window.GravewrightBoardInternals.PixiBoardRenderer = PixiBoardRenderer;

    
    
    window.GravewrightBoard.registerRenderer("pixi", (deps) => new PixiBoardRenderer(deps));
})();
