














(() => {
    function tileLifecycle(url) {
        if (window.__gravewrightMeasureRender !== true) return null;
        const store = window.__gravewrightTileLifecycle
            || (window.__gravewrightTileLifecycle = { tiles: {}, active: 0, maxConcurrency: 0 });
        return store.tiles[url] || (store.tiles[url] = { url, timestamps: {}, cache: "unknown" });
    }

    function stampTile(entry, stage) {
        if (entry && entry.timestamps[stage] == null) entry.timestamps[stage] = performance.now();
    }

    function beginTileWork(entry) {
        if (!entry) return;
        const store = window.__gravewrightTileLifecycle;
        store.active += 1;
        store.maxConcurrency = Math.max(store.maxConcurrency, store.active);
    }

    function endTileWork(entry) {
        if (!entry) return;
        const store = window.__gravewrightTileLifecycle;
        store.active = Math.max(0, store.active - 1);
    }

    const TileBlobCache = (() => {
        const DB_NAME = "gravewright-map-tile-cache";
        const STORE = "tiles";
        const MAX_ENTRIES = Math.max(1, Number(window.__gravewrightTileBlobCacheMaxEntries) || 4096);
        const MAX_BYTES = Math.max(1, Number(window.__gravewrightTileBlobCacheMaxBytes) || 512 * 1024 * 1024);
        let dbPromise = null;
        let statsPromise = null;
        let writeChain = Promise.resolve();
        const stats = {
            entries: 0,
            bytes: 0,
            evictions: 0,
            evictedBytes: 0,
            initialized: false,
        };
        let supported = typeof indexedDB !== "undefined" && typeof URL !== "undefined";

        function enabled() {
            return supported;
        }

        function openDb() {
            if (!supported) return Promise.resolve(null);
            if (dbPromise) return dbPromise;
            dbPromise = new Promise((resolve) => {
                const req = indexedDB.open(DB_NAME, 2);
                req.onupgradeneeded = () => {
                    const db = req.result;
                    if (!db.objectStoreNames.contains(STORE)) {
                        const store = db.createObjectStore(STORE, { keyPath: "url" });
                        store.createIndex("lastUsedAt", "lastUsedAt");
                        store.createIndex("speculativeExpiresAt", "speculativeExpiresAt");
                    } else {
                        const store = req.transaction.objectStore(STORE);
                        if (!store.indexNames.contains("speculativeExpiresAt")) {
                            store.createIndex("speculativeExpiresAt", "speculativeExpiresAt");
                        }
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

        async function put(url, blob, provenance = {}) {
            const db = await openDb();
            if (!db || !blob) return;
            writeChain = writeChain.catch(() => {}).then(async () => {
                await initializeStats(db);
                const previous = await readRow(db, url);
                const size = Number(blob.size) || 0;
                await new Promise((resolve) => {
                    const tx = db.transaction(STORE, "readwrite");
                    tx.oncomplete = resolve;
                    tx.onerror = resolve;
                    const sources = new Set([...(previous?.sources || []), ...(provenance.sources || [])]);
                    tx.objectStore(STORE).put({
                        url, blob, size, lastUsedAt: Date.now(), sources: [...sources],
                        speculativeExpiresAt: provenance.speculativeExpiresAt || previous?.speculativeExpiresAt || null,
                    });
                });
                if (!previous) stats.entries += 1;
                stats.bytes += size - rowSize(previous);
                await prune(db);
            });
            await writeChain;
        }

        async function promote(url, source = "visible") {
            const db = await openDb();
            if (!db) return false;
            const row = await readRow(db, url);
            if (!row) return false;
            row.sources = [...new Set([...(row.sources || []), source])];
            row.speculativeExpiresAt = null;
            await new Promise((resolve) => {
                const tx = db.transaction(STORE, "readwrite");
                tx.oncomplete = resolve; tx.onerror = resolve;
                tx.objectStore(STORE).put(row);
            });
            return true;
        }

        async function expireSpeculative(now = Date.now()) {
            const db = await openDb();
            if (!db) return { entries: 0, bytes: 0 };
            let entries = 0; let bytes = 0;
            await initializeStats(db);
            await new Promise((resolve) => {
                const tx = db.transaction(STORE, "readwrite");
                tx.oncomplete = resolve; tx.onerror = resolve;
                tx.objectStore(STORE).openCursor().onsuccess = (event) => {
                    const cursor = event.target.result;
                    if (!cursor) return;
                    const row = cursor.value;
                    const sources = row.sources || [];
                    if (row.speculativeExpiresAt && row.speculativeExpiresAt <= now
                        && sources.length === 1 && sources[0] === "gm_hint") {
                        const size = rowSize(row); cursor.delete(); entries += 1; bytes += size;
                        stats.entries = Math.max(0, stats.entries - 1);
                        stats.bytes = Math.max(0, stats.bytes - size);
                    }
                    cursor.continue();
                };
            });
            return { entries, bytes };
        }

        function rowSize(row) {
            return Number(row?.size) || Number(row?.blob?.size) || 0;
        }

        function readRow(db, url) {
            return new Promise((resolve) => {
                const tx = db.transaction(STORE, "readonly");
                const req = tx.objectStore(STORE).get(url);
                req.onsuccess = () => resolve(req.result || null);
                req.onerror = () => resolve(null);
            });
        }

        function initializeStats(db) {
            if (statsPromise) return statsPromise;
            statsPromise = new Promise((resolve) => {
                const tx = db.transaction(STORE, "readonly");
                const req = tx.objectStore(STORE).openCursor();
                req.onsuccess = () => {
                    const cursor = req.result;
                    if (!cursor) return;
                    stats.entries += 1;
                    stats.bytes += rowSize(cursor.value);
                    cursor.continue();
                };
                tx.oncomplete = () => {
                    stats.initialized = true;
                    resolve();
                };
                tx.onerror = () => resolve();
            });
            return statsPromise;
        }

        async function prune(db) {
            try {
                if (stats.entries <= MAX_ENTRIES && stats.bytes <= MAX_BYTES) return;
                await new Promise((resolve) => {
                    const tx = db.transaction(STORE, "readwrite");
                    const index = tx.objectStore(STORE).index("lastUsedAt");
                    tx.oncomplete = resolve;
                    tx.onerror = resolve;
                    index.openCursor().onsuccess = (event) => {
                        const cursor = event.target.result;
                        if (!cursor || (stats.entries <= MAX_ENTRIES && stats.bytes <= MAX_BYTES)) return;
                        const size = rowSize(cursor.value);
                        cursor.delete();
                        stats.entries = Math.max(0, stats.entries - 1);
                        stats.bytes = Math.max(0, stats.bytes - size);
                        stats.evictions += 1;
                        stats.evictedBytes += size;
                        cursor.continue();
                    };
                });
            } catch {

            }
        }

        function snapshot() {
            return { ...stats, maxEntries: MAX_ENTRIES, maxBytes: MAX_BYTES };
        }

        return { enabled, get, put, promote, expireSpeculative, snapshot };
    })();

    window.GravewrightTileBlobCache = window.GravewrightTileBlobCache || TileBlobCache;

    class PixiBoardRenderer {
        constructor(deps) {
            this.deps = deps || {};
            this.boards = new Map();
            this.textures = new Map();
            this.textureObjectUrls = new Map();
            this.textureMeta = new Map();
            this.textureCacheBytes = 0;
            this.textureCacheEvictions = 0;
            this.textureCacheEvictedBytes = 0;
            this.maxTextureCacheEntries = Math.max(1, Number(window.__gravewrightTextureCacheMaxEntries) || 192);
            this.maxTextureCacheBytes = Math.max(1, Number(window.__gravewrightTextureCacheMaxBytes) || 192 * 1024 * 1024);
            this.textureQueue = [];
            this.textureJobs = new Map();
            this.activeTextureJobs = new Map();
            this.textureFrameWanted = new Set();
            this.activeTextureLoads = 0;
            this.maxTextureLoads = Math.max(1, Number(window.__gravewrightTextureConcurrency) || 8);
            this.maxTextureMaterializationsPerFrame = Math.max(
                1,
                Number(window.__gravewrightTextureMaterializationBudget) || 4,
            );
            this.minTextureMaterializationsPerFrame = 1;
            this.maxAdaptiveTextureMaterializationsPerFrame = Math.max(
                this.maxTextureMaterializationsPerFrame,
                Number(window.__gravewrightTextureMaterializationBudgetMax) || 12,
            );
            this.textureFrameTargetMs = Math.max(8, Number(window.__gravewrightTextureFrameTargetMs) || 16.7);
            this.textureFrameWorkEmaMs = 0;
            this.textureMaterializationCostEmaMs = 0.25;
            this.textureBudgetHeadroomFrames = 0;
            this.textureGovernorState = "idle";
            this.textureGovernorIncreases = 0;
            this.textureGovernorDecreases = 0;
            this.lastCameraChangeAt = 0;
            this.textureInteractionWindowMs = Math.max(
                50,
                Number(window.__gravewrightTextureInteractionWindowMs) || 120,
            );
            this.textureRecoveryWindowMs = Math.max(
                this.textureInteractionWindowMs,
                Number(window.__gravewrightTextureRecoveryWindowMs) || 650,
            );
            this.prefetchPausedUntil = 0;
            this.latestTextureGeneration = 0;
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
            if (!camera) return;
            if (
                camera.offsetX !== this.camera.offsetX
                || camera.offsetY !== this.camera.offsetY
                || camera.zoom !== this.camera.zoom
            ) this.lastCameraChangeAt = performance.now();
            this.camera = camera;
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

        showPing(canvas, ping) {
            this.attach(canvas);
            const board = this.boards.get(canvas);
            if (!board) return;
            board.pings.push({ ...ping, startedAt: performance.now() });
            this.deps.requestRender?.();
        }

        render() {
            const board = this.active && this.boards.get(this.active);
            if (!board || !board.ready) return;
            const measureFrame = window.__gravewrightMeasureRender === true;
            const prepareStartedAt = performance.now();

            const { width: cssW, height: cssH } = this._cssSize(this.active);

            if (board.cssW !== cssW || board.cssH !== cssH) {
                board.app.renderer.resize(cssW, cssH);
                board.cssW = cssW;
                board.cssH = cssH;
            }

            board.app.renderer.background.color = this._color(this._background());

            this.textureFrameWanted.clear();
            board.textureMaterializationsThisFrame = 0;
            board.deferredTextureMaterializations = 0;
            board.deferredVisibleTextureMaterializations = 0;
            board.deferredPrefetchTextureMaterializations = 0;
            board.textureMaterializationWorkMs = 0;
            this._renderTiles(board, cssW, cssH);
            this._renderGrid(board, cssW, cssH);
            this._renderTokens(board, cssW, cssH);
            this._renderGhosts(board);
            this._renderOrigin(board);
            this._renderLighting?.(board, cssW, cssH);
            this._renderFog(board, cssW, cssH);
            this._renderPings(board);
            this._cancelObsoleteTextureJobs();
            this._enforceTextureBudget();

            if (measureFrame && board.textureMaterializationsThisFrame > 0) {
                window.__gravewrightPerfRecord?.(
                    "texture_materialization",
                    board.textureMaterializationWorkMs,
                );
            }
            if (measureFrame) window.__gravewrightPerfRecord?.("render_prepare", performance.now() - prepareStartedAt);
            const pixiStartedAt = measureFrame ? performance.now() : 0;
            board.app.render();
            if (measureFrame) window.__gravewrightPerfRecord?.("app_render", performance.now() - pixiStartedAt);
            this._updateAdaptiveTextureBudget(performance.now() - prepareStartedAt, board);
            if (board.pendingPresentedTiles?.size) {
                board.pendingPresentedTiles.forEach((url) => {
                    const lifecycle = tileLifecycle(url);
                    stampTile(lifecycle, "gpu_ready");
                    stampTile(lifecycle, "first_presented");
                });
                board.pendingPresentedTiles.clear();
            }
            if (board.deferredTextureMaterializations > 0) this.deps.requestRender?.();
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
                lightingLayer: null,
                lightingSprite: null,
                lightingScene: null,
                lightingParticleGfx: null,
                lightingParticlePool: [],
                lightingGlowGfx: null,
                lightingGlowPool: [],



                lightingVeilPool: [],
                lightingRT: null,
                lightingRTW: 0,
                lightingRTH: 0,
                lightingRTDpr: 0,
                lightingKey: "",
                lightingDoorLayer: null,
                lightingDoorPool: [],
                lightingGfxPool: [],
                lightingDarkGlowPool: [],
                lightingPoolIndex: 0,
                lightingWallsGfx: null,


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

                pingLayer: null,
                pingGfx: null,
                pings: [],

                tileSprites: new Map(),
                tokenNodes: new Map(),
                fastTokenSprites: new Map(),
                tilePlanKey: "",
                tilePlan: [],
                pendingPresentedTiles: new Set(),
                textureMaterializationsThisFrame: 0,
                deferredTextureMaterializations: 0,
                deferredVisibleTextureMaterializations: 0,
                deferredPrefetchTextureMaterializations: 0,
                textureMaterializationWorkMs: 0,
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
                background: this._color(this._background()),
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

        _background() {
            const themed = getComputedStyle(document.documentElement)
                .getPropertyValue("--gw-board-background")
                .trim();
            return themed || this.theme.background;
        }

        _renderPings(board) {
            const gfx = board.pingGfx;
            if (!gfx) return;
            gfx.clear();
            const now = performance.now();
            const duration = 2400;
            board.pings = board.pings.filter((ping) => now - ping.startedAt < duration);
            board.pings.forEach((ping) => {
                const age = Math.max(0, Math.min(1, (now - ping.startedAt) / duration));
                const x = ping.worldX * this.camera.zoom + this.camera.offsetX;
                const y = ping.worldY * this.camera.zoom + this.camera.offsetY;
                const color = this._color(ping.color || "#f2c679");
                for (let index = 0; index < 3; index += 1) {
                    const progress = Math.max(0, Math.min(1, age * 1.45 - index * 0.18));
                    if (progress <= 0 || progress >= 1) continue;
                    const radius = 18 + 92 * progress;
                    const alpha = Math.pow(1 - progress, 1.35);
                    if (ping.variant === "focus") {
                        gfx.poly([x, y - radius, x + radius, y, x, y + radius, x - radius, y])
                            .stroke({ color, width: 4, alpha });
                    } else {
                        gfx.circle(x, y, radius).stroke({ color, width: 4, alpha });
                    }
                }
                const pulse = 1 + 0.24 * Math.sin(age * Math.PI * 8);
                gfx.circle(x, y, 9 * pulse)
                    .fill({ color, alpha: Math.max(0.35, 1 - age) })
                    .stroke({ color: 0xffffff, width: 2, alpha: Math.max(0.2, 0.75 - age) });
                gfx.circle(x, y, 18 * pulse)
                    .stroke({ color, width: 3, alpha: Math.max(0.18, 0.8 - age) });
            });
            if (board.pings.length) this.deps.requestRender?.();
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

        _texture(url, request = {}) {
            this.textureFrameWanted.add(url);
            const lifecycle = tileLifecycle(url);
            stampTile(lifecycle, "tile_needed");
            const requestedGeneration = Number(request.generation) || 0;
            if (requestedGeneration > this.latestTextureGeneration) {
                this.latestTextureGeneration = requestedGeneration;
                this._dropObsoleteQueuedTextures(requestedGeneration);
            }
            if (request.visible) {
                stampTile(lifecycle, "visible_needed");
                if (lifecycle) lifecycle.requestClass = "visible";
            } else if (lifecycle && !lifecycle.requestClass) {
                lifecycle.requestClass = "prefetch";
            }
            if (!request.visible && performance.now() < this.prefetchPausedUntil && !this.textures.has(url)) {
                if (lifecycle) lifecycle.deferred = "adaptive_prefetch_pause";
                return null;
            }
            const cached = this.textures.get(url);
            if (cached === "queued") {
                const job = this.textureJobs.get(url);
                if (job) {
                    const nextPriority = (request.visible ? 0 : 1_000_000)
                        + (Number(request.priority) || 0);
                    job.priority = Math.min(job.priority, nextPriority);
                    job.generation = Math.max(job.generation, Number(request.generation) || 0);
                    if (lifecycle) {
                        lifecycle.priority = job.priority;
                        lifecycle.generation = job.generation;
                    }
                    this._sortTextureQueue();
                }
                return null;
            }
            if (cached === "loading") {
                const job = this.activeTextureJobs.get(url);
                if (job) job.generation = Math.max(job.generation, requestedGeneration);
                return null;
            }
            if (cached === "error") return null;
            if (cached) {
                const meta = this.textureMeta.get(url);
                if (meta) meta.lastUsedAt = performance.now();
                if (lifecycle) lifecycle.gpuTextureHit = true;
                return cached;
            }

            this.textures.set(url, "queued");
            stampTile(lifecycle, "scheduler_enqueued");
            const spatialPriority = (request.visible ? 0 : 1_000_000)
                + (Number(request.priority) || 0);
            const job = {
                url,
                lifecycle,
                priority: spatialPriority,
                generation: Number(request.generation) || 0,
                sequence: performance.now(),
            };
            if (lifecycle) {
                lifecycle.priority = spatialPriority;
                lifecycle.generation = job.generation;
            }
            this.textureJobs.set(url, job);
            this.textureQueue.push(job);
            this._sortTextureQueue();
            this._pumpTextureQueue();
            return null;
        }

        _dropObsoleteQueuedTextures(currentGeneration) {
            const retained = [];
            this.textureQueue.forEach((job) => {
                if (job.generation >= currentGeneration) {
                    retained.push(job);
                    return;
                }
                if (this.textures.get(job.url) === "queued") this.textures.delete(job.url);
                this.textureJobs.delete(job.url);
                if (job.lifecycle) {
                    job.lifecycle.cancelled = "obsolete_generation_while_queued";
                    stampTile(job.lifecycle, "cancelled");
                }
            });
            this.textureQueue = retained;
        }

        _sortTextureQueue() {
            this.textureQueue.sort((a, b) =>
                b.generation - a.generation
                || a.priority - b.priority
                || a.sequence - b.sequence
            );
        }

        _cancelObsoleteTextureJobs() {
            this.activeTextureJobs.forEach((job, url) => {
                if (job.generation >= this.latestTextureGeneration || this.textureFrameWanted.has(url)) return;
                job.obsolete = true;
                job.controller?.abort();
                if (job.lifecycle) {
                    job.lifecycle.cancelled = "obsolete_generation_in_flight";
                    stampTile(job.lifecycle, "cancelled");
                }
            });
        }

        _pumpTextureQueue() {
            while (this.activeTextureLoads < this.maxTextureLoads && this.textureQueue.length) {
                const job = this.textureQueue.shift();
                if (!job || this.textures.get(job.url) !== "queued") continue;
                this._startTextureJob(job);
            }
        }

        _startTextureJob(job) {
            const { url, lifecycle } = job;
            this.textureJobs.delete(url);
            this.textures.set(url, "loading");
            job.controller = new AbortController();
            this.activeTextureJobs.set(url, job);
            this.activeTextureLoads += 1;
            stampTile(lifecycle, "request_started");
            beginTileWork(lifecycle);
            const textureStartedAt = window.__gravewrightMeasureRender === true ? performance.now() : 0;

            this._loadTextureSource(url, lifecycle, job.controller.signal)
                .then((source) => {
                    if (job.obsolete) throw new DOMException("Obsolete tile generation", "AbortError");
                    return this._decodeAndCreateTexture(source, url, lifecycle);
                })
                .then((texture) => {
                    stampTile(lifecycle, "decode_complete");
                    stampTile(lifecycle, "texture_create_complete");
                    if (!texture) {
                        throw new Error("Pixi returned no texture for image URL");
                    }

                    if (job.obsolete && !this.textureFrameWanted.has(url)) {
                        texture.destroy?.(true);
                        this.textures.delete(url);
                        return;
                    }

                    if (this.textures.get(url) !== "loading") return;

                    this.textures.set(url, texture);
                    const size = this._estimateTextureBytes(texture);
                    this.textureMeta.set(url, { bytes: size, lastUsedAt: performance.now() });
                    this.textureCacheBytes += size;
                    if (textureStartedAt) window.__gravewrightPerfRecord?.(
                        "texture_pipeline_total", performance.now() - textureStartedAt
                    );
                    this.deps.requestRender?.();
                })
                .catch((err) => {
                    if (this.textures.get(url) !== "loading") return;

                    if (err?.name === "AbortError") {
                        this.textures.delete(url);
                        return;
                    }

                    this.textures.set(url, "error");
                    console.error("PixiBoardRenderer texture load failed", url, err);
                })
                .finally(() => {
                    endTileWork(lifecycle);
                    this.activeTextureJobs.delete(url);
                    this.activeTextureLoads = Math.max(0, this.activeTextureLoads - 1);
                    this._pumpTextureQueue();
                });
        }

        async _loadTextureSource(url, lifecycle = null, signal = undefined) {
            const cache = window.GravewrightTileBlobCache;
            if (!cache || !cache.enabled?.() || !url.includes("/game/scenes/")) {
                if (lifecycle) lifecycle.cache = "bypass";
                stampTile(lifecycle, "response_headers");
                stampTile(lifecycle, "response_complete");
                return { sourceUrl: url, blob: null };
            }

            stampTile(lifecycle, "cache_read_started");
            const cached = await cache.get(url);
            if (signal?.aborted) throw new DOMException("Obsolete tile generation", "AbortError");
            stampTile(lifecycle, "cache_read_complete");
            if (cached) {
                if (lifecycle) lifecycle.cache = "indexeddb_blob_hit";
                stampTile(lifecycle, "response_headers");
                stampTile(lifecycle, "response_complete");
                return { sourceUrl: this._objectUrlFor(url, cached), blob: cached };
            }

            stampTile(lifecycle, "network_request_started");
            const response = await fetch(url, {
                credentials: "same-origin",
                cache: "force-cache",
                signal,
            });
            stampTile(lifecycle, "response_headers");
            if (!response.ok) throw new Error(`Texture request failed: ${response.status}`);
            const blob = await response.blob();
            stampTile(lifecycle, "response_complete");
            if (lifecycle) lifecycle.cache = "network_or_http_cache";
            await cache.put(url, blob);
            return { sourceUrl: this._objectUrlFor(url, blob), blob };
        }

        async _decodeAndCreateTexture(source, url, lifecycle) {
            if (source.blob && typeof createImageBitmap === "function") {
                stampTile(lifecycle, "decode_started");
                const decodeStartedAt = performance.now();
                const bitmap = await createImageBitmap(source.blob);
                stampTile(lifecycle, "decode_complete");
                window.__gravewrightPerfRecord?.("image_decode", performance.now() - decodeStartedAt);

                stampTile(lifecycle, "texture_create_started");
                const createStartedAt = performance.now();
                const texture = PIXI.Texture.from(bitmap);
                texture.__gravewrightOwned = true;
                texture.__gravewrightBitmap = bitmap;
                stampTile(lifecycle, "texture_create_complete");
                window.__gravewrightPerfRecord?.("texture_create", performance.now() - createStartedAt);
                return texture;
            }

            stampTile(lifecycle, "decode_started");
            stampTile(lifecycle, "texture_create_started");
            const texture = await PIXI.Assets.load({
                src: source.sourceUrl,
                alias: url,
                loadParser: "loadTextures",
            });
            stampTile(lifecycle, "decode_complete");
            stampTile(lifecycle, "texture_create_complete");
            return texture;
        }

        _objectUrlFor(url, blob) {
            const current = this.textureObjectUrls.get(url);
            if (current) return current;
            const objectUrl = URL.createObjectURL(blob);
            this.textureObjectUrls.set(url, objectUrl);
            return objectUrl;
        }

        _estimateTextureBytes(texture) {
            const source = texture?.source;
            const width = Number(source?.pixelWidth || source?.width || texture?.width) || 0;
            const height = Number(source?.pixelHeight || source?.height || texture?.height) || 0;
            return Math.max(0, width * height * 4);
        }

        _forgetTexture(url) {
            const texture = this.textures.get(url);
            if (!texture || typeof texture === "string") return false;
            const meta = this.textureMeta.get(url);
            const bytes = Number(meta?.bytes) || 0;
            this.textures.delete(url);
            this.textureMeta.delete(url);
            this.textureCacheBytes = Math.max(0, this.textureCacheBytes - bytes);
            const objectUrl = this.textureObjectUrls.get(url);
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
                this.textureObjectUrls.delete(url);
            }
            PIXI.Assets?.unload?.(url)?.catch?.(() => {});
            if (texture.__gravewrightOwned) {
                texture.destroy?.(true);
                texture.__gravewrightBitmap?.close?.();
            }
            return bytes;
        }

        _updateAdaptiveTextureBudget(frameWorkMs, board) {
            this.textureFrameWorkEmaMs = this.textureFrameWorkEmaMs
                ? this.textureFrameWorkEmaMs * 0.8 + frameWorkMs * 0.2
                : frameWorkMs;
            if (board.textureMaterializationsThisFrame > 0) {
                const cost = board.textureMaterializationWorkMs / board.textureMaterializationsThisFrame;
                this.textureMaterializationCostEmaMs = this.textureMaterializationCostEmaMs * 0.8 + cost * 0.2;
            }
            const sinceCameraChange = performance.now() - this.lastCameraChangeAt;
            this.textureGovernorState = sinceCameraChange <= this.textureInteractionWindowMs
                ? "active"
                : sinceCameraChange <= this.textureRecoveryWindowMs ? "recovery" : "idle";
            const stateMax = this.textureGovernorState === "active"
                ? Math.min(3, this.maxAdaptiveTextureMaterializationsPerFrame)
                : this.textureGovernorState === "recovery"
                    ? Math.min(10, this.maxAdaptiveTextureMaterializationsPerFrame)
                    : this.maxAdaptiveTextureMaterializationsPerFrame;
            const overloaded = frameWorkMs > this.textureFrameTargetMs
                || this.textureFrameWorkEmaMs > this.textureFrameTargetMs * 0.9;
            if (overloaded) {
                const nextBudget = Math.max(
                    this.minTextureMaterializationsPerFrame,
                    Math.min(stateMax, Math.floor(this.maxTextureMaterializationsPerFrame / 2)),
                );
                if (nextBudget < this.maxTextureMaterializationsPerFrame) this.textureGovernorDecreases += 1;
                this.maxTextureMaterializationsPerFrame = nextBudget;
                this.textureBudgetHeadroomFrames = 0;
                this.prefetchPausedUntil = performance.now() + 150;
                return;
            }
            if (!board.deferredTextureMaterializations) {
                this.textureBudgetHeadroomFrames = 0;
                return;
            }
            const visiblePressure = board.deferredVisibleTextureMaterializations > 0;
            const headroom = Math.max(0, this.textureFrameTargetMs * 0.65 - this.textureFrameWorkEmaMs);
            const affordable = Math.max(1, Math.floor(headroom / Math.max(0.1, this.textureMaterializationCostEmaMs)));
            const desiredBudget = Math.max(
                visiblePressure ? Math.min(6, stateMax) : this.minTextureMaterializationsPerFrame,
                Math.min(stateMax, affordable),
            );
            if (desiredBudget <= this.maxTextureMaterializationsPerFrame) {
                this.textureBudgetHeadroomFrames = 0;
                return;
            }
            this.textureBudgetHeadroomFrames += 1;
            const recoveryFrames = visiblePressure ? 1 : this.textureGovernorState === "active" ? 3 : 2;
            if (this.textureBudgetHeadroomFrames < recoveryFrames) return;
            const step = visiblePressure || this.textureGovernorState !== "active" ? 2 : 1;
            this.maxTextureMaterializationsPerFrame = Math.min(desiredBudget, this.maxTextureMaterializationsPerFrame + step);
            this.textureGovernorIncreases += 1;
            this.textureBudgetHeadroomFrames = 0;
        }

        _evictTexture(url) {
            this.boards.forEach((board) => {
                board.tileSprites?.forEach((sprite, key) => {
                    if (sprite.__tileUrl !== url) return;
                    board.tileSprites.delete(key);
                    sprite.destroy();
                });
            });
            const bytes = this._forgetTexture(url);
            if (bytes === false) return;
            this.textureCacheEvictions += 1;
            this.textureCacheEvictedBytes += bytes;
        }

        _enforceTextureBudget() {
            if (
                this.textureMeta.size <= this.maxTextureCacheEntries
                && this.textureCacheBytes <= this.maxTextureCacheBytes
            ) return;
            const candidates = [...this.textureMeta.entries()]
                .filter(([url]) => url.includes("/game/scenes/") && !this.textureFrameWanted.has(url))
                .sort((a, b) => a[1].lastUsedAt - b[1].lastUsedAt);
            for (const [url] of candidates) {
                if (
                    this.textureMeta.size <= this.maxTextureCacheEntries
                    && this.textureCacheBytes <= this.maxTextureCacheBytes
                ) break;
                this._evictTexture(url);
            }
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
