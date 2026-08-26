(() => {
    function createSceneStreaming(deps) {
        const runtimes = new WeakMap();
        const {
            api,
            applyCameraToState,
            applyMeasureSnapshot,
            chunkHeaderBytes,
            chunkMagic,
            defaultChunkSize,
            initialCameraFor,
            loadTokensForScene,
            markDirty,
            maxRetries,
            pullMs,
            retryMs,
            sceneDataFor,
            selection,
            stateFor,
            tokens,
            tokenStoreFor,
            viewportSizeFor,
            viewportUpdateMs,
            viewChunkMargin,
        } = deps;

        function runtimeFor(canvas) {
            let runtime = runtimes.get(canvas);
            if (!runtime) {
                runtime = {
                    manifest: null,
                    manifestPromise: null,
                    tileTables: new Map(),
                    tileIndexRequests: new Map(),
                    tileIndexPagesLoaded: 0,
                    tileDescriptorCount: 0,
                    tileDescriptorRevision: 0,
                    metrics: {
                        manifestBytes: 0, chunkBytesReceived: 0, cacheHits: 0,
                        cacheMisses: 0, viewportGenerations: 0,
                        gm_hint_created: 0, gm_hint_prefetch_requested: 0,
                        gm_hint_prefetch_completed: 0, gm_hint_promoted_to_visible: 0,
                        gm_hint_expired_unused: 0, gm_hint_bytes_downloaded: 0,
                        gm_hint_bytes_used: 0, gm_hint_bytes_wasted: 0,
                        gm_hint_cache_hit: 0, gm_hint_cache_miss: 0,
                        gm_hint_cancelled: 0, gm_hint_lead_time_ms: 0,
                        gm_hint_latency_saved_ms: 0, gm_hint_scheduler_debt_ms: 0,
                        gm_hint_candidates: 0, gm_hint_prefetch_started: 0,
                        gm_hint_promoted: 0, gm_hint_bytes_prefetched: 0,
                        gm_hint_bytes_promoted: 0, gm_hint_bytes_expired: 0,
                        gm_hint_bytes_evicted: 0, gm_hint_score_at_prefetch: 0,
                        gm_hint_score_at_promotion: 0, gm_hint_dwell_at_prefetch_ms: 0,
                        gm_hint_momentum_at_prefetch: 0,
                    },
                    chunks: new Map(),
                    chunkRevision: 0,
                    known: new Map(),
                    generation: 0,
                    lastViewportKey: "",
                    lastSentAt: 0,
                    pendingTimer: null,
                    chunkRetryTimer: null,
                    chunkRetryCount: 0,
                    lastMissingCount: null,
                    cachedInfoEpoch: null,
                    sceneRuntimeCache: new Map(),
                    tokenRuntimeCache: new Map(),
                    gmHints: new Map(),
                    gmPrefetchQueue: [],
                    gmPrefetchActive: false,
                    gmSampleTimer: null,
                    gmLastSample: null,
                    gmInteractionCount: 0,
                    gmDecayTimer: null,
                    gmHintBuckets: {},
                    gmPrefetchController: null,
                    gmQueuedBytes: 0,
                };
                runtimes.set(canvas, runtime);
            }
            return runtime;
        }

        function visibleTileRange(scene, cameraState, canvasW, canvasH) {
            const worldX0 = -cameraState.offsetX / cameraState.zoom;
            const worldY0 = -cameraState.offsetY / cameraState.zoom;
            const worldX1 = (canvasW - cameraState.offsetX) / cameraState.zoom;
            const worldY1 = (canvasH - cameraState.offsetY) / cameraState.zoom;

            const s = scene.scaledRasterTileSize || scene.scaledTileSize;
            const rasterSize = scene.rasterTileSize || scene.tileSize;
            const tileCols = Math.ceil(scene.baseWidth / rasterSize);
            const tileRows = Math.ceil(scene.baseHeight / rasterSize);

            return {
                tx0: Math.max(0, Math.floor(worldX0 / s)),
                tx1: Math.min(tileCols - 1, Math.floor(worldX1 / s)),
                ty0: Math.max(0, Math.floor(worldY0 / s)),
                ty1: Math.min(tileRows - 1, Math.floor(worldY1 / s)),
            };
        }

        function visibleChunkRange(canvas, scene, cameraState) {
            const viewport = viewportSizeFor(canvas);
            const { tx0, tx1, ty0, ty1 } = visibleTileRange(
                scene, cameraState, viewport.width, viewport.height,
            );
            if (tx0 > tx1 || ty0 > ty1) return null;

            const runtime = runtimeFor(canvas);
            const chunkSize = runtime.manifest?.chunk_size || defaultChunkSize;

            const rasterSize = scene.rasterTileSize || scene.tileSize;
            const tileCols = Math.ceil(scene.baseWidth / rasterSize);
            const tileRows = Math.ceil(scene.baseHeight / rasterSize);
            const maxCx = Math.max(0, Math.floor((tileCols - 1) / chunkSize));
            const maxCy = Math.max(0, Math.floor((tileRows - 1) / chunkSize));

            return {
                cx0: Math.max(0, Math.floor(tx0 / chunkSize) - viewChunkMargin),
                cy0: Math.max(0, Math.floor(ty0 / chunkSize) - viewChunkMargin),
                cx1: Math.min(maxCx, Math.floor(tx1 / chunkSize) + viewChunkMargin),
                cy1: Math.min(maxCy, Math.floor(ty1 / chunkSize) + viewChunkMargin),
            };
        }

        function viewportFocusChunk(canvas, scene, cameraState) {
            const viewport = viewportSizeFor(canvas);
            const runtime = runtimeFor(canvas);
            const chunkSize = runtime.manifest?.chunk_size || defaultChunkSize;
            const s = scene.scaledRasterTileSize || scene.scaledTileSize;
            const centerWorldX = (viewport.width / 2 - cameraState.offsetX) / cameraState.zoom;
            const centerWorldY = (viewport.height / 2 - cameraState.offsetY) / cameraState.zoom;
            return {
                focus_cx: centerWorldX / s / chunkSize,
                focus_cy: centerWorldY / s / chunkSize,
            };
        }

        function chunkKey(layerId, cx, cy) {
            return `${layerId}:${cx}:${cy}`;
        }

        function sceneRuntimeKey(sceneId, tileVersion) {
            return `${sceneId}:${tileVersion || 1}`;
        }

        function buildTileTables(manifest) {
            const tables = new Map();
            (manifest.layers || []).forEach((layer) => {
                const table = new Map();
                (layer.tiles || []).forEach((tile) => {
                    table.set(tile.tile_ref, tile);
                });
                tables.set(layer.layer_id, table);
            });
            return tables;
        }

        function ensureTileDescriptors(canvas, scene, range, lod = 0) {
            const runtime = runtimeFor(canvas);
            const manifest = runtime.manifest;
            if (!manifest || manifest.scene_format_version < 2 || !range) return Promise.resolve();
            const chunkSize = manifest.chunk_size || defaultChunkSize;
            const tx0 = range.cx0 * chunkSize;
            const ty0 = range.cy0 * chunkSize;
            const tx1 = (range.cx1 + 1) * chunkSize - 1;
            const ty1 = (range.cy1 + 1) * chunkSize - 1;
            const jobs = (manifest.layers || []).map((layer) => {
                const key = `${layer.layer_id}:${lod}:${tx0}:${ty0}:${tx1}:${ty1}:${layer.tile_index_version || 1}`;
                if (runtime.tileIndexRequests.has(key)) return runtime.tileIndexRequests.get(key);
                const job = api.loadSceneTileIndex(scene.id, layer.layer_id, {
                    lod, tx0, ty0, tx1, ty1, limit: 4096,
                }).then((page) => {
                    const table = runtime.tileTables.get(layer.layer_id) || new Map();
                    (page.tiles || []).forEach((tile) => table.set(tile.tile_ref, tile));
                    runtime.tileTables.set(layer.layer_id, table);
                    runtime.tileIndexPagesLoaded += 1;
                    runtime.tileDescriptorCount = Array.from(runtime.tileTables.values())
                        .reduce((total, item) => total + item.size, 0);
                    runtime.tileDescriptorRevision += 1;
                    markDirty(canvas);
                }).catch((error) => {
                    runtime.tileIndexRequests.delete(key);
                    console.error("Scene tile index load failed", { sceneId: scene.id, layerId: layer.layer_id, error });
                });
                runtime.tileIndexRequests.set(key, job);
                return job;
            });
            return Promise.all(jobs);
        }

        function isGmViewer() {
            return document.body?.dataset?.gmGuidedPrefetch === "true"
                && ["gm", "assistant_gm"].includes(document.body?.dataset?.currentMemberRole || "");
        }

        function scheduleGmSample(canvas) {
            const runtime = runtimeFor(canvas);
            if (!isGmViewer() || runtime.gmSampleTimer) return;
            runtime.gmSampleTimer = window.setTimeout(() => {
                runtime.gmSampleTimer = null;
                const scene = sceneDataFor(canvas);
                if (!scene || !canvas.isConnected) return;
                const range = visibleChunkRange(canvas, scene, stateFor(canvas));
                if (range && window.GravewrightRealtime?.isOpen?.()) {
                    const now = performance.now();
                    const focus = viewportFocusChunk(canvas, scene, stateFor(canvas));
                    const previous = runtime.gmLastSample;
                    const elapsed = Math.max(1, now - (previous?.at || now));
                    const speed = previous
                        ? Math.hypot(focus.focus_cx - previous.focus_cx, focus.focus_cy - previous.focus_cy) * 1000 / elapsed
                        : 0;
                    const deceleration = Math.max(0, (previous?.speed || 0) - speed);
                    window.GravewrightRealtime.sendCommand("gm_hint.sample", {
                        viewport_id: "gm-hint", generation: runtime.generation,
                        ...range, ...focus, camera_speed: speed,
                        camera_deceleration: deceleration,
                        interaction_count: runtime.gmInteractionCount,
                    }, { sceneId: scene.id, roomId: canvas.dataset.roomId || "" });
                    runtime.gmLastSample = { ...focus, speed, at: now };
                    runtime.gmInteractionCount = 0;
                }
                scheduleGmSample(canvas);
            }, 1000);
        }

        if (!window.__gravewrightGmHintInteractionBound) {
            window.__gravewrightGmHintInteractionBound = true;
            const interactionEvents = new Set([
                "tokens.created", "tokens.moved", "tokens.updated",
                "scene.walls.updated", "scene.lights.updated",
                "scene.particles.updated", "scene.shaders.updated",
            ]);
            document.addEventListener("vtt:transport-event", (event) => {
                if (!isGmViewer() || !interactionEvents.has(event.detail?.event)) return;
                document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
                    const runtime = runtimeFor(canvas);
                    if (canvas.dataset.sceneId === event.detail?.payload?.scene_id) {
                        runtime.gmInteractionCount += 1;
                    }
                });
            });
        }

        function hintKey(hint) {
            return `${hint.scene_id}:${hint.cx0}:${hint.cy0}:${hint.cx1}:${hint.cy1}`;
        }

        function expireGmHints(runtime, now = Date.now()) {
            runtime.gmHints.forEach((hint, key) => {
                if (hint.promoted || now < hint.expires_at_ms) return;
                runtime.metrics.gm_hint_expired_unused += 1;
                hint.state = "expired";
                recordHintOutcome(runtime, hint, false);
                window.GravewrightTileBlobCache?.expireSpeculative?.(now).then((expired) => {
                    runtime.metrics.gm_hint_bytes_wasted += expired?.bytes || 0;
                    runtime.metrics.gm_hint_bytes_expired += expired?.bytes || 0;
                });
                runtime.gmHints.delete(key);
            });
        }

        function scheduleHintDecay(runtime) {
            if (runtime.gmDecayTimer) return;
            runtime.gmDecayTimer = window.setTimeout(() => {
                runtime.gmDecayTimer = null;
                expireGmHints(runtime);
                if (runtime.gmHints.size) scheduleHintDecay(runtime);
            }, 1000);
        }

        function dwellBucket(dwellMs) {
            if (dwellMs < 2000) return "0-2s";
            if (dwellMs < 5000) return "2-5s";
            if (dwellMs < 10000) return "5-10s";
            return ">10s";
        }

        function recordHintOutcome(runtime, hint, promoted) {
            const key = dwellBucket(Number(hint.dwell_ms) || 0);
            const bucket = runtime.gmHintBuckets[key] || (runtime.gmHintBuckets[key] = {
                hits: 0, misses: 0, bytes_used: 0, bytes_wasted: 0,
                mean_time_to_use_ms: 0, samples: 0,
            });
            bucket.samples += 1;
            if (promoted) bucket.hits += 1;
            else bucket.misses += 1;
            bucket.bytes_used += hint.usedBytes || 0;
            bucket.bytes_wasted += promoted ? 0 : hint.bytes || 0;
            if (promoted) {
                const value = Date.now() - hint.hintedAt;
                bucket.mean_time_to_use_ms += (value - bucket.mean_time_to_use_ms) / bucket.hits;
            }
        }

        function tileUrlsForHint(runtime, hint) {
            const urls = new Map();
            const chunkSize = runtime.manifest?.chunk_size || defaultChunkSize;
            const centerTx = ((hint.cx0 + hint.cx1 + 1) * chunkSize - 1) / 2;
            const centerTy = ((hint.cy0 + hint.cy1 + 1) * chunkSize - 1) / 2;
            const minTx = hint.cx0 * chunkSize;
            const minTy = hint.cy0 * chunkSize;
            const maxTx = (hint.cx1 + 1) * chunkSize - 1;
            const maxTy = (hint.cy1 + 1) * chunkSize - 1;
            (hint.layer_ids || []).forEach((layerId) => {
                const table = runtime.tileTables.get(layerId);
                if (!table) return;
                table.forEach((tile) => {
                    if (tile.tx < minTx || tile.tx > maxTx || tile.ty < minTy || tile.ty > maxTy) return;
                    const distance = (tile.tx - centerTx) ** 2 + (tile.ty - centerTy) ** 2;
                    const previous = urls.get(tile.url);
                    if (tile.url && (previous == null || distance < previous)) urls.set(tile.url, distance);
                });
                for (let cy = hint.cy0; cy <= hint.cy1; cy += 1) {
                    for (let cx = hint.cx0; cx <= hint.cx1; cx += 1) {
                        const chunk = runtime.chunks.get(chunkKey(layerId, cx, cy));
                        if (!chunk) continue;
                        (chunk.refs || []).slice(0, chunkSize * chunkSize).forEach((ref, index) => {
                            const url = table.get(ref)?.url;
                            if (!url) return;
                            const tx = cx * chunkSize + index % chunkSize;
                            const ty = cy * chunkSize + Math.floor(index / chunkSize);
                            const distance = (tx - centerTx) ** 2 + (ty - centerTy) ** 2;
                            const previous = urls.get(url);
                            if (previous == null || distance < previous) urls.set(url, distance);
                        });
                    }
                }
            });
            return [...urls.entries()].map(([url, distance]) => ({ url, distance }));
        }

        async function warmGmHintUrl(runtime, hint, url, signal) {
            const cache = window.GravewrightTileBlobCache;
            if (!cache?.enabled?.()) return;
            const cached = await cache.get(url);
            if (cached) {
                runtime.metrics.gm_hint_cache_hit += 1;
                return;
            }
            runtime.metrics.gm_hint_cache_miss += 1;
            const startedAt = performance.now();
            const response = await fetch(url, { credentials: "same-origin", cache: "force-cache", signal });
            if (!response.ok) return;
            const blob = await response.blob();
            if ((hint.bytes || 0) + blob.size > 64 * 1024 * 1024) return;
            await cache.put(url, blob, {
                sources: ["gm_hint"], speculativeExpiresAt: hint.expires_at_ms,
            });
            hint.bytes = (hint.bytes || 0) + blob.size;
            hint.downloadedUrls.set(url, { bytes: blob.size, downloadedAt: Date.now(), networkMs: performance.now() - startedAt });
            runtime.metrics.gm_hint_bytes_downloaded += blob.size;
            runtime.metrics.gm_hint_bytes_prefetched += blob.size;
        }

        async function drainGmPrefetch(canvas) {
            const runtime = runtimeFor(canvas);
            if (runtime.gmPrefetchActive) return;
            const scene = sceneDataFor(canvas);
            const visible = scene && visibleChunkRange(canvas, scene, stateFor(canvas));
            const layers = scene && visible ? layerIdsFor(canvas, scene) : [];
            const visibleBacklog = visible && missingVisibleChunkKeys(runtime, layers, visible).length > 0;
            if (!scene || (document.body?.dataset?.gmHintIdleOnly === "true" && visibleBacklog)) return;
            const job = runtime.gmPrefetchQueue.shift();
            if (!job || Date.now() >= job.hint.expires_at_ms) return;
            runtime.gmPrefetchActive = true;
            job.hint.state = "prefetching";
            runtime.gmQueuedBytes = Math.max(0, runtime.gmQueuedBytes - (job.byteSize || 0));
            const controller = new AbortController();
            runtime.gmPrefetchController = controller;
            runtime.metrics.gm_hint_prefetch_requested += 1;
            runtime.metrics.gm_hint_prefetch_started += 1;
            runtime.metrics.gm_hint_score_at_prefetch = Number(job.hint.score) || 0;
            runtime.metrics.gm_hint_dwell_at_prefetch_ms = Number(job.hint.dwell_ms) || 0;
            runtime.metrics.gm_hint_momentum_at_prefetch = Number(job.hint.momentum) || 0;
            try {
                await warmGmHintUrl(runtime, job.hint, job.url, controller.signal);
                runtime.metrics.gm_hint_prefetch_completed += 1;
                job.hint.state = "warm";
            } catch (error) {
                if (error?.name === "AbortError") runtime.metrics.gm_hint_cancelled += 1;

            } finally {
                runtime.gmPrefetchController = null;
                runtime.gmPrefetchActive = false;
                window.setTimeout(() => drainGmPrefetch(canvas), 0);
            }
        }

        async function handleGmPrefetchHint(hint) {
            if (document.body?.dataset?.gmGuidedPrefetch !== "true") return;
            if (!hint?.scene_id || Date.now() >= Number(hint.expires_at_ms || 0)) return;
            const canvas = [...document.querySelectorAll("[data-map-canvas]")]
                .find((item) => item.dataset.sceneId === hint.scene_id);
            if (!canvas) return;
            const scene = sceneDataFor(canvas);
            const runtime = runtimeFor(canvas);
            if (!scene || !runtime.manifest) return;
            expireGmHints(runtime);
            const key = hintKey(hint);
            if (runtime.gmHints.has(key)) return;
            const state = {
                ...hint, bytes: 0, usedBytes: 0, promoted: false, hintedAt: Date.now(),
                source: "gm_hint", sources: new Set(["gm_hint"]), state: "observed",
                downloadedUrls: new Map(),
            };
            runtime.gmHints.set(key, state);
            scheduleHintDecay(runtime);
            runtime.metrics.gm_hint_created += 1;
            runtime.metrics.gm_hint_candidates += 1;
            await ensureTileDescriptors(canvas, scene, hint);
            const tableByUrl = new Map();
            runtime.tileTables.forEach((table) => table.forEach((tile) => tableByUrl.set(tile.url, tile)));
            const maxQueuedBytes = Math.max(1, Number(document.body?.dataset?.gmHintMaxQueuedBytes) || 64 * 1024 * 1024);
            const candidates = tileUrlsForHint(runtime, hint).map((candidate) => {
                const byteSize = Number(tableByUrl.get(candidate.url)?.byte_size) || 1;
                const spatialBenefit = 1 / (1 + candidate.distance);
                return { ...candidate, byteSize, priorityPerByte: (Number(hint.utility) || Number(hint.score) || 0) * spatialBenefit / byteSize };
            });
            candidates.sort(document.body?.dataset?.gmHintPolicy === "utility_per_byte"
                ? (a, b) => b.priorityPerByte - a.priorityPerByte
                : (a, b) => a.distance - b.distance);
            candidates.forEach(({ url, byteSize }) => {
                if (runtime.gmQueuedBytes + byteSize > maxQueuedBytes) return;
                runtime.gmQueuedBytes += byteSize;
                runtime.gmPrefetchQueue.push({ hint: state, url, byteSize });
            });
            state.state = runtime.gmPrefetchQueue.some((job) => job.hint === state) ? "candidate" : "observed";
            drainGmPrefetch(canvas);
        }

        function chunkCacheIndexKey(sceneId, tileVersion) {
            return `gravewright.sceneChunks.${sceneId}.${tileVersion}.index`;
        }

        function chunkCacheKey(sceneId, tileVersion, key) {
            return `gravewright.sceneChunks.${sceneId}.${tileVersion}.${key}`;
        }

        function sceneInfoCacheKey(sceneId, sceneEpoch) {
            return `gravewright.sceneInfo.${sceneId}.${sceneEpoch}`;
        }

        function invalidateSceneInfo(sceneId) {
            if (!sceneId) return;
            const prefix = `gravewright.sceneInfo.${sceneId}.`;
            try {
                for (let index = localStorage.length - 1; index >= 0; index -= 1) {
                    const key = localStorage.key(index);
                    if (key?.startsWith(prefix)) localStorage.removeItem(key);
                }
            } catch {  }
            document.querySelectorAll(`[data-map-canvas][data-scene-id="${CSS.escape(sceneId)}"]`)
                .forEach((canvas) => { runtimeFor(canvas).cachedInfoEpoch = null; });
        }

        function updateSceneInfoCache(eventName, payload) {
            const sceneId = payload?.scene_id;
            if (!sceneId) return;
            const prefix = `gravewright.sceneInfo.${sceneId}.`;
            let updated = 0;
            try {
                for (let index = 0; index < localStorage.length; index += 1) {
                    const key = localStorage.key(index);
                    if (!key?.startsWith(prefix)) continue;
                    const cached = JSON.parse(localStorage.getItem(key) || "null");
                    if (!cached || !Array.isArray(cached.board_area_markers)) continue;
                    const markers = cached.board_area_markers;
                    if (eventName === "board.area_marker.upserted" && payload.marker) {
                        const at = markers.findIndex((item) => item.id === payload.marker.id);
                        if (at >= 0) markers[at] = payload.marker;
                        else markers.push(payload.marker);
                    } else if (eventName === "board.area_marker.deleted") {
                        cached.board_area_markers = markers.filter((item) => item.id !== payload.marker_id);
                    } else if (eventName === "board.area_marker.cleared") {
                        cached.board_area_markers = markers.filter((item) =>
                            item.kind === "freehand" || item.kind === "text" || (payload.keep_gm_layer === true && item.layer === "gm")
                        );
                    } else if (eventName === "board.draw.upserted" && payload.drawing) {
                        const at = markers.findIndex((item) => item.id === payload.drawing.id);
                        if (at >= 0) markers[at] = payload.drawing;
                        else markers.push(payload.drawing);
                    } else if (eventName === "board.draw.cleared") {
                        cached.board_area_markers = markers.filter((item) => {
                            if (item.kind !== "freehand" && item.kind !== "text") return true;
                            return Boolean(payload.owner_id && item.owner_id !== payload.owner_id);
                        });
                    }
                    localStorage.setItem(key, JSON.stringify(cached));
                    updated += 1;
                }
            } catch {  }
            if (!updated) invalidateSceneInfo(sceneId);
        }

        function readChunkCacheIndex(sceneId, tileVersion) {
            try {
                const raw = localStorage.getItem(chunkCacheIndexKey(sceneId, tileVersion));
                const parsed = raw ? JSON.parse(raw) : [];
                return Array.isArray(parsed) ? parsed.filter((key) => typeof key === "string") : [];
            } catch {
                return [];
            }
        }

        function hydrateCachedChunks(runtime, manifest) {
            const keys = readChunkCacheIndex(manifest.scene_id, manifest.tile_table_version);
            let hydrated = 0;
            keys.forEach((key) => {
                try {
                    const raw = localStorage.getItem(chunkCacheKey(manifest.scene_id, manifest.tile_table_version, key));
                    if (!raw) return;
                    const cached = JSON.parse(raw);
                    if (!cached || !Array.isArray(cached.refs) || !Number.isInteger(cached.version)) return;
                    runtime.chunks.set(key, {
                        layerId: cached.layerId,
                        cx: cached.cx,
                        cy: cached.cy,
                        version: cached.version,
                        hash: cached.hash,
                        refs: cached.refs,
                    });
                    runtime.known.set(key, cached.version);
                    runtime.metrics.cacheHits += 1;
                    hydrated += 1;
                } catch {

                }
            });
            if (hydrated) runtime.chunkRevision += 1;
        }

        function readCachedSceneInfo(manifest) {
            if (!manifest?.scene_id || !Number.isInteger(manifest.scene_epoch)) return null;
            try {
                const raw = localStorage.getItem(sceneInfoCacheKey(manifest.scene_id, manifest.scene_epoch));
                if (!raw) return null;
                const cached = JSON.parse(raw);
                if (!cached || cached.scene_id !== manifest.scene_id) return null;
                if (!Array.isArray(cached.board_area_markers)) return null;
                return cached;
            } catch {
                return null;
            }
        }

        function persistSceneInfoSnapshot(payload) {
            if (!payload?.scene_id || !Number.isInteger(payload.scene_epoch)) return;
            if (!Array.isArray(payload.board_area_markers)) return;
            try {
                localStorage.setItem(
                    sceneInfoCacheKey(payload.scene_id, payload.scene_epoch),
                    JSON.stringify({
                        scene_id: payload.scene_id,
                        scene_epoch: payload.scene_epoch,
                        board_area_markers: payload.board_area_markers,
                    }),
                );
            } catch {

            }
        }

        function hydrateCachedSceneInfo(runtime, manifest) {
            const cached = readCachedSceneInfo(manifest);
            if (!cached) return false;
            applyMeasureSnapshot(cached);
            runtime.cachedInfoEpoch = cached.scene_epoch;
            return true;
        }

        function persistCachedChunk(manifest, key, chunk) {
            try {
                const indexKey = chunkCacheIndexKey(manifest.scene_id, manifest.tile_table_version);
                const index = readChunkCacheIndex(manifest.scene_id, manifest.tile_table_version);
                if (!index.includes(key)) {
                    index.push(key);
                    localStorage.setItem(indexKey, JSON.stringify(index.slice(-4096)));
                }
                localStorage.setItem(chunkCacheKey(manifest.scene_id, manifest.tile_table_version, key), JSON.stringify(chunk));
            } catch {

            }
        }

        function clearChunkStreamRetry(runtime) {
            if (runtime.chunkRetryTimer) {
                window.clearTimeout(runtime.chunkRetryTimer);
                runtime.chunkRetryTimer = null;
            }
            runtime.chunkRetryCount = 0;
            runtime.lastMissingCount = null;
        }

        function ensureManifest(canvas, scene) {
            const runtime = runtimeFor(canvas);
            if (
                runtime.manifest?.scene_id === scene.id
                && runtime.manifest?.tile_table_version === scene.tileVersion
            ) {
                return runtime.manifestPromise || Promise.resolve(runtime.manifest);
            }
            if (runtime.manifestPromise) return runtime.manifestPromise;

            const requestGeneration = runtime.generation;
            let manifestPromise;
            manifestPromise = api.loadSceneManifest(scene.id)
                .then((manifest) => {
                    const currentScene = sceneDataFor(canvas);
                    if (
                        !currentScene
                        || currentScene.id !== manifest.scene_id
                        || currentScene.tileVersion !== manifest.tile_table_version
                        || runtime.generation !== requestGeneration
                    ) {
                        if (runtime.manifestPromise === manifestPromise) runtime.manifestPromise = null;
                        return manifest;
                    }

                    const tilingChanged =
                        runtime.manifest?.scene_id !== manifest.scene_id
                        || runtime.manifest?.tile_table_version !== manifest.tile_table_version;
                    if (tilingChanged) {
                        clearChunkStreamRetry(runtime);
                        runtime.chunks.clear();
                        runtime.chunkRevision += 1;
                        runtime.known.clear();
                        runtime.tileIndexRequests.clear();
                        runtime.tileIndexPagesLoaded = 0;
                        runtime.tileDescriptorCount = 0;
                        runtime.tileDescriptorRevision += 1;
                        runtime.generation = 0;
                        runtime.lastViewportKey = "";
                        runtime.cachedInfoEpoch = null;
                    }
                    runtime.manifest = manifest;
                    runtime.metrics.manifestBytes = new TextEncoder().encode(JSON.stringify(manifest)).byteLength;
                    runtime.tileTables = buildTileTables(manifest);
                    hydrateCachedChunks(runtime, manifest);
                    runtime.manifestPromise = null;
                    loadTokensForScene(canvas, scene);
                    markDirty(canvas);
                    const range = visibleChunkRange(canvas, scene, stateFor(canvas));
                    const layerIds = range ? layerIdsFor(canvas, scene) : [];
                    if (range && viewportReadyFromCache(runtime, manifest, layerIds, range)) {
                        runtime.lastViewportKey = viewportKeyFor(scene, layerIds, range);
                        clearChunkStreamRetry(runtime);
                    } else {
                        scheduleViewportUpdate(canvas, true);
                    }
                    document.dispatchEvent(new CustomEvent("vtt:manifest-loaded", {
                        detail: { sceneId: manifest.scene_id, manifest },
                    }));
                    return manifest;
                })
                .catch((err) => {
                    if (runtime.manifestPromise === manifestPromise) runtime.manifestPromise = null;
                    console.error("Scene manifest load failed", scene.id, err);
                    return null;
                });

            runtime.manifestPromise = manifestPromise;
            return runtime.manifestPromise;
        }

        function layerIdsFor(canvas, scene) {
            const runtime = runtimeFor(canvas);
            if (runtime.manifest?.layers?.length) {
                return runtime.manifest.layers.map((layer) => layer.layer_id);
            }
            return scene.layerId ? [scene.layerId] : [];
        }

        function viewportKeyFor(scene, layerIds, range) {
            return `${scene.id}:${layerIds.join(",")}:${range.cx0}:${range.cy0}:${range.cx1}:${range.cy1}`;
        }

        function knownChunksObject(runtime) {
            const known = {};
            runtime.known.forEach((version, key) => {
                known[key] = version;
            });
            return known;
        }

        function missingVisibleChunkKeys(runtime, layerIds, range) {
            const missing = [];
            layerIds.forEach((layerId) => {
                for (let cy = range.cy0; cy <= range.cy1; cy += 1) {
                    for (let cx = range.cx0; cx <= range.cx1; cx += 1) {
                        const key = chunkKey(layerId, cx, cy);
                        if (!runtime.chunks.has(key)) missing.push(key);
                    }
                }
            });
            return missing;
        }

        function viewportReadyFromCache(runtime, manifest, layerIds, range) {
            if (!manifest || !range || !layerIds.length) return false;
            if (missingVisibleChunkKeys(runtime, layerIds, range).length) return false;
            if (runtime.cachedInfoEpoch === manifest.scene_epoch) return true;
            return hydrateCachedSceneInfo(runtime, manifest);
        }

        function scheduleChunkStreamRetry(canvas, scene, layerIds, range) {
            const runtime = runtimeFor(canvas);
            const missing = missingVisibleChunkKeys(runtime, layerIds, range);
            if (!missing.length) {
                clearChunkStreamRetry(runtime);
                return;
            }

            const progressed =
                runtime.lastMissingCount === null || missing.length < runtime.lastMissingCount;
            runtime.lastMissingCount = missing.length;
            if (progressed) runtime.chunkRetryCount = 0;

            if (runtime.chunkRetryTimer) return;
            if (runtime.chunkRetryCount >= maxRetries) {
                console.error("Scene chunk stream stalled", {
                    sceneId: scene.id,
                    generation: runtime.generation,
                    range,
                    missing,
                });
                return;
            }

            const delay = progressed ? pullMs : retryMs;
            runtime.chunkRetryTimer = window.setTimeout(() => {
                runtime.chunkRetryTimer = null;
                if (!progressed) runtime.chunkRetryCount += 1;
                sendViewportUpdate(canvas, true);
            }, delay);
        }

        function scheduleViewportUpdate(canvas, immediate = false) {
            const scene = sceneDataFor(canvas);
            if (!scene) return;
            const runtime = runtimeFor(canvas);

            if (immediate && runtime.pendingTimer) {
                window.clearTimeout(runtime.pendingTimer);
                runtime.pendingTimer = null;
            }

            // A pending callback reads the latest camera state when it fires.
            // Replacing it on every pointermove creates avoidable timer churn and
            // can starve viewport streaming during a long, uninterrupted pan.
            if (!immediate && runtime.pendingTimer) return;

            const now = Date.now();
            const elapsed = now - runtime.lastSentAt;
            if (immediate || elapsed >= viewportUpdateMs) {
                sendViewportUpdate(canvas);
                return;
            }

            runtime.pendingTimer = window.setTimeout(() => {
                runtime.pendingTimer = null;
                sendViewportUpdate(canvas);
            }, viewportUpdateMs - elapsed);
        }

        function performViewportUpdate(canvas, force = false) {
            const scene = sceneDataFor(canvas);
            const realtime = window.GravewrightRealtime;
            if (!scene) return false;
            if (!realtime?.isOpen()) {
                const runtime = runtimeFor(canvas);
                if (runtime.manifest) {
                    const range = visibleChunkRange(canvas, scene, stateFor(canvas));
                    const layerIds = range ? layerIdsFor(canvas, scene) : [];
                    if (range && viewportReadyFromCache(runtime, runtime.manifest, layerIds, range)) {
                        runtime.lastViewportKey = viewportKeyFor(scene, layerIds, range);
                        clearChunkStreamRetry(runtime);
                        markDirty(canvas);
                        return true;
                    }
                    if (range && layerIds.length) scheduleChunkStreamRetry(canvas, scene, layerIds, range);
                }
                return false;
            }

            const runtime = runtimeFor(canvas);
            if (!runtime.manifest) {
                ensureManifest(canvas, scene);
                return false;
            }

            const range = visibleChunkRange(canvas, scene, stateFor(canvas));
            if (!range) return false;
            scheduleGmSample(canvas);
            expireGmHints(runtime);
            const currentLayers = layerIdsFor(canvas, scene);
            if (document.body?.dataset?.gmHintCancelVisible === "true"
                && missingVisibleChunkKeys(runtime, currentLayers, range).length > 0) {
                runtime.gmPrefetchController?.abort();
                runtime.metrics.gm_hint_scheduler_debt_ms = 0;
            }
            runtime.gmHints.forEach((hint) => {
                if (hint.promoted) return;
                const intersects = range.cx0 <= hint.cx1 && range.cx1 >= hint.cx0
                    && range.cy0 <= hint.cy1 && range.cy1 >= hint.cy0;
                if (!intersects) return;
                hint.promoted = true;
                hint.state = "promoted";
                runtime.gmPrefetchQueue = runtime.gmPrefetchQueue.filter((job) => job.hint !== hint);
                runtime.gmQueuedBytes = runtime.gmPrefetchQueue.reduce((sum, job) => sum + (job.byteSize || 0), 0);
                runtime.gmPrefetchController?.abort();
                const viewport = viewportSizeFor(canvas);
                const tileRange = visibleTileRange(scene, stateFor(canvas), viewport.width, viewport.height);
                const visibleUrls = new Set();
                runtime.tileTables.forEach((table) => table.forEach((tile) => {
                    if (tile.tx >= tileRange.tx0 && tile.tx <= tileRange.tx1
                        && tile.ty >= tileRange.ty0 && tile.ty <= tileRange.ty1) visibleUrls.add(tile.url);
                }));
                let usedBytes = 0;
                let savedMs = 0;
                let latestDownloadAt = 0;
                hint.downloadedUrls.forEach((entry, url) => {
                    if (!visibleUrls.has(url)) return;
                    usedBytes += entry.bytes || 0;
                    savedMs += entry.networkMs || 0;
                    latestDownloadAt = Math.max(latestDownloadAt, entry.downloadedAt || 0);
                    window.GravewrightTileBlobCache?.promote?.(url, "visible");
                });
                hint.usedBytes = usedBytes;
                hint.sources.add("visible");
                runtime.metrics.gm_hint_promoted_to_visible += 1;
                runtime.metrics.gm_hint_promoted += 1;
                runtime.metrics.gm_hint_score_at_promotion = Number(hint.score) || 0;
                runtime.metrics.gm_hint_bytes_used += usedBytes;
                runtime.metrics.gm_hint_bytes_promoted += usedBytes;
                runtime.metrics.gm_hint_time_to_use_ms = Date.now() - hint.hintedAt;
                runtime.metrics.gm_hint_lead_time_ms = latestDownloadAt ? Date.now() - latestDownloadAt : 0;
                runtime.metrics.gm_hint_latency_saved_ms += savedMs;
                recordHintOutcome(runtime, hint, true);
            });

            const layerIds = layerIdsFor(canvas, scene);
            if (!layerIds.length) return false;
            ensureTileDescriptors(canvas, scene, range);

            const viewportKey = viewportKeyFor(scene, layerIds, range);
            if (viewportReadyFromCache(runtime, runtime.manifest, layerIds, range)) {
                runtime.lastViewportKey = viewportKey;
                clearChunkStreamRetry(runtime);
                markDirty(canvas);
                drainGmPrefetch(canvas);
                return true;
            }
            if (!force && viewportKey === runtime.lastViewportKey) return true;

            const nextGeneration = runtime.generation + 1;
            const sent = realtime.sendCommand(
                nextGeneration === 1 ? "viewport.subscribe" : "viewport.update",
                {
                    viewport_id: "main",
                    generation: nextGeneration,
                    layers: layerIds,
                    ...range,
                    ...viewportFocusChunk(canvas, scene, stateFor(canvas)),
                    known: knownChunksObject(runtime),
                },
                {
                    sceneId: scene.id,
                    roomId: canvas.dataset.roomId || "",
                },
            );

            if (!sent) return false;

            runtime.generation = nextGeneration;
            runtime.metrics.viewportGenerations += 1;
            runtime.metrics.cacheMisses += missingVisibleChunkKeys(runtime, layerIds, range).length;
            runtime.lastViewportKey = viewportKey;
            runtime.lastSentAt = Date.now();
            scheduleChunkStreamRetry(canvas, scene, layerIds, range);
            return true;
        }

        function sendViewportUpdate(canvas, force = false) {
            const startedAt = window.__gravewrightMeasureRender === true ? performance.now() : 0;
            const result = performViewportUpdate(canvas, force);
            if (startedAt) window.__gravewrightPerfRecord?.("streaming_update", performance.now() - startedAt);
            return result;
        }

        function sendSessionResume(canvas) {
            const scene = sceneDataFor(canvas);
            const realtime = window.GravewrightRealtime;
            if (!scene || !realtime?.isOpen()) return false;

            const runtime = runtimeFor(canvas);
            if (!runtime.manifest) {
                ensureManifest(canvas, scene);
                return false;
            }

            const range = visibleChunkRange(canvas, scene, stateFor(canvas));
            if (!range) return false;

            const layerIds = layerIdsFor(canvas, scene);
            if (!layerIds.length) return false;

            const nextGeneration = runtime.generation + 1;
            const roomId = canvas.dataset.roomId || "";
            const sent = realtime.sendCommand(
                "session.resume",
                {
                    active_scene_id: scene.id,
                    scene_epoch: runtime.manifest.scene_epoch || 0,
                    last_event_seq: realtime.lastEventSeq?.(roomId) || 0,
                    viewport: {
                        viewport_id: "main",
                        generation: nextGeneration,
                        layers: layerIds,
                        ...range,
                        ...viewportFocusChunk(canvas, scene, stateFor(canvas)),
                    },
                    known_chunks: knownChunksObject(runtime),
                },
                { sceneId: scene.id, roomId },
            );

            if (!sent) return false;

            runtime.generation = nextGeneration;
            runtime.lastViewportKey = viewportKeyFor(scene, layerIds, range);
            runtime.lastSentAt = Date.now();
            scheduleChunkStreamRetry(canvas, scene, layerIds, range);
            return true;
        }

        function decodeChunkRefsView(payload, start, length, encoding) {
            if (encoding !== "uint32_tile_refs_v1") return [];
            const view = new DataView(payload.buffer, payload.byteOffset + start, length);
            const refs = new Array(Math.floor(length / 4));
            for (let index = 0, offset = 0; offset < length; index += 1, offset += 4) {
                refs[index] = view.getUint32(offset, true);
            }
            return refs;
        }

        function decodeChunkBatchFrame(buffer) {
            if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < chunkHeaderBytes) return null;
            const view = new DataView(buffer);
            const magic = String.fromCharCode(
                view.getUint8(0),
                view.getUint8(1),
                view.getUint8(2),
                view.getUint8(3),
            );
            if (magic !== chunkMagic || view.getUint8(4) !== 1 || view.getUint8(5) !== 1) return null;

            const headerLength = view.getUint32(8, true);
            const headerStart = chunkHeaderBytes;
            const headerEnd = headerStart + headerLength;
            if (headerEnd > buffer.byteLength) return null;

            const headerBytes = new Uint8Array(buffer, headerStart, headerLength);
            const header = JSON.parse(new TextDecoder().decode(headerBytes));
            const payload = new Uint8Array(buffer, headerEnd);
            return { header, payload };
        }

        function applyChunkBatchFrame(buffer) {
            let frame;
            try {
                frame = decodeChunkBatchFrame(buffer);
            } catch (err) {
                console.error("Scene chunk frame decode failed", err);
                return;
            }
            if (!frame?.header?.scene_id || !Array.isArray(frame.header.chunks)) {
                console.error("Scene chunk frame is invalid", frame?.header || null);
                return;
            }

            let applied = false;
            document.querySelectorAll(`[data-map-canvas][data-scene-id="${frame.header.scene_id}"]`)
                .forEach((canvas) => {
                    const runtime = runtimeFor(canvas);
                    frame.header.chunks.forEach((meta) => {
                        const start = meta.offset;
                        const end = start + meta.length;
                        if (start < 0 || end > frame.payload.byteLength) return;

                        const key = chunkKey(meta.layer_id, meta.cx, meta.cy);
                        const knownVersion = runtime.known.get(key) || 0;
                        if (!Number.isInteger(meta.version) || meta.version < knownVersion) return;

                        const refs = decodeChunkRefsView(
                            frame.payload,
                            start,
                            meta.length,
                            meta.encoding,
                        );
                        runtime.chunks.set(key, {
                            layerId: meta.layer_id,
                            cx: meta.cx,
                            cy: meta.cy,
                            version: meta.version,
                            hash: meta.hash,
                            refs,
                        });
                        runtime.metrics.chunkBytesReceived += Number(meta.byte_size || meta.length || 0);
                        if (runtime.manifest) {
                            persistCachedChunk(runtime.manifest, key, {
                                layerId: meta.layer_id,
                                cx: meta.cx,
                                cy: meta.cy,
                                version: meta.version,
                                hash: meta.hash,
                                refs,
                            });
                        }
                        runtime.chunkRevision += 1;
                        runtime.known.set(key, meta.version);
                    });

                    const scene = sceneDataFor(canvas);
                    const range = scene ? visibleChunkRange(canvas, scene, stateFor(canvas)) : null;
                    const layerIds = scene && range ? layerIdsFor(canvas, scene) : [];
                    if (scene && range && layerIds.length) {
                        scheduleChunkStreamRetry(canvas, scene, layerIds, range);
                    }
                    applied = true;
                    markDirty(canvas);
                });

            if (frame.header.batch_id && window.GravewrightRealtime?.sendCommand) {
                window.GravewrightRealtime.sendCommand(
                    "chunk.ack",
                    {
                        batch_id: frame.header.batch_id,
                        applied,
                        reason: applied ? undefined : "stale_generation",
                    },
                );
            }
        }

        function handleChunkUpdated(payload) {
            if (!payload?.scene_id || !payload.layer_id) return;
            if (!Number.isInteger(payload.cx) || !Number.isInteger(payload.cy)) return;

            document.querySelectorAll(`[data-map-canvas][data-scene-id="${payload.scene_id}"]`)
                .forEach((canvas) => {
                    const runtime = runtimeFor(canvas);
                    const key = chunkKey(payload.layer_id, payload.cx, payload.cy);
                    const knownVersion = runtime.known.get(key) || 0;
                    if (Number.isInteger(payload.version) && knownVersion >= payload.version) return;

                    runtime.known.delete(key);
                    if (runtime.chunks.delete(key)) runtime.chunkRevision += 1;
                    runtime.lastViewportKey = "";
                    scheduleViewportUpdate(canvas, true);
                    markDirty(canvas);
                });
        }

        function handleViewportReady(payload) {
            persistSceneInfoSnapshot(payload);
            applyMeasureSnapshot(payload);
            document.querySelectorAll(`[data-map-canvas][data-scene-id="${payload?.scene_id}"]`)
                .forEach((canvas) => {
                    const runtime = runtimeFor(canvas);
                    if (Number.isInteger(payload?.scene_epoch)) {
                        runtime.cachedInfoEpoch = payload.scene_epoch;
                    }
                });
        }

        function handleSessionResumed(payload) {
            if (!payload?.scene_id) return;
            persistSceneInfoSnapshot(payload);
            applyMeasureSnapshot(payload);
            (payload.events || []).forEach((eventEnvelope) => {
                document.dispatchEvent(
                    new CustomEvent("vtt:transport-event", { detail: eventEnvelope })
                );
            });

            document.querySelectorAll(`[data-map-canvas][data-scene-id="${payload.scene_id}"]`)
                .forEach((canvas) => {
                    const scene = sceneDataFor(canvas);
                    if (scene) loadTokensForScene(canvas, scene, true);

                    const runtime = runtimeFor(canvas);
                    if (runtime.manifest && Number.isInteger(payload.scene_epoch)) {
                        runtime.manifest.scene_epoch = payload.scene_epoch;
                    }
                    if (!payload.resync_required) return;

                    runtime.manifest = null;
                    runtime.manifestPromise = null;
                    runtime.tileTables = new Map();
                    runtime.tileDescriptorRevision += 1;
                    clearChunkStreamRetry(runtime);
                    runtime.chunks.clear();
                    runtime.chunkRevision += 1;
                    runtime.known.clear();
                    runtime.generation = 0;
                    runtime.lastViewportKey = "";
                    runtime.cachedInfoEpoch = null;

                    if (scene) ensureManifest(canvas, scene);
                    markDirty(canvas);
                });
        }

        function resetSceneRuntime(canvas) {
            const runtime = runtimeFor(canvas);
            clearChunkStreamRetry(runtime);
            runtime.manifest = null;
            runtime.manifestPromise = null;
            runtime.tileTables = new Map();
            runtime.tileDescriptorRevision += 1;
            runtime.chunks.clear();
            runtime.chunkRevision += 1;
            runtime.known.clear();
            runtime.generation += 1;
            runtime.lastViewportKey = "";
            runtime.cachedInfoEpoch = null;

            tokenStoreFor(canvas).clear();
            tokens.clearLoadState(canvas);
            selection.reset(canvas);
        }

        function cloneToken(token) {
            return token && typeof token === "object" ? { ...token } : token;
        }

        function pruneRuntimeCache(cache, maxEntries = 12) {
            while (cache.size > maxEntries) {
                const firstKey = cache.keys().next().value;
                cache.delete(firstKey);
            }
        }

        function saveSceneRuntime(canvas, sceneId, tileVersion) {
            if (!sceneId) return;
            const runtime = runtimeFor(canvas);
            const key = sceneRuntimeKey(sceneId, tileVersion);
            runtime.sceneRuntimeCache.set(key, {
                manifest: runtime.manifest,
                tileTables: runtime.tileTables,
                tileDescriptorRevision: runtime.tileDescriptorRevision,
                chunks: new Map(runtime.chunks),
                chunkRevision: runtime.chunkRevision,
                known: new Map(runtime.known),
                generation: runtime.generation,
                lastViewportKey: runtime.lastViewportKey,
                cachedInfoEpoch: runtime.cachedInfoEpoch,
            });
            runtime.tokenRuntimeCache.set(
                key,
                [...tokenStoreFor(canvas).values()].map(cloneToken),
            );
            pruneRuntimeCache(runtime.sceneRuntimeCache);
            pruneRuntimeCache(runtime.tokenRuntimeCache);
        }

        function restoreSceneRuntime(canvas, sceneId, tileVersion) {
            const runtime = runtimeFor(canvas);
            const key = sceneRuntimeKey(sceneId, tileVersion);
            const cached = runtime.sceneRuntimeCache.get(key);
            if (!cached) return false;

            clearChunkStreamRetry(runtime);
            runtime.manifest = cached.manifest;
            runtime.manifestPromise = null;
            runtime.tileTables = cached.tileTables || new Map();
            runtime.tileDescriptorRevision = (cached.tileDescriptorRevision || 0) + 1;
            runtime.chunks = new Map(cached.chunks || []);
            runtime.chunkRevision = (cached.chunkRevision || 0) + 1;
            runtime.known = new Map(cached.known || []);
            runtime.generation = cached.generation || 0;
            runtime.lastViewportKey = cached.lastViewportKey || "";
            runtime.cachedInfoEpoch = cached.cachedInfoEpoch || null;

            const tokenStore = tokenStoreFor(canvas);
            tokenStore.clear();
            (runtime.tokenRuntimeCache.get(key) || []).forEach((token) => {
                if (token?.token_id) tokenStore.set(token.token_id, cloneToken(token));
            });
            tokens.clearLoadState(canvas);
            selection.reset(canvas);
            return true;
        }

        function syncCanvasScene(canvas, scenePayload) {
            if (!canvas || !scenePayload?.id) return;
            const previousSceneId = canvas.dataset.sceneId || "";
            const previousTileVersion = canvas.dataset.sceneTileVersion || "";
            const nextTileVersion = String(scenePayload.tile_table_version || 1);
            const sceneChanged = previousSceneId !== scenePayload.id
                || previousTileVersion !== nextTileVersion;

            if (sceneChanged && previousSceneId) {
                saveSceneRuntime(canvas, previousSceneId, previousTileVersion);
            }

            canvas.dataset.sceneId = scenePayload.id;
            canvas.dataset.sceneWidth = String(scenePayload.width || 0);
            canvas.dataset.sceneHeight = String(scenePayload.height || 0);
            canvas.dataset.sceneTileSize = String(scenePayload.tile_size || defaultGridSize());
            canvas.dataset.sceneRasterTileSize = String(scenePayload.raster_tile_size || scenePayload.tile_size || defaultGridSize());
            canvas.dataset.sceneGridSize = String(scenePayload.grid_size || scenePayload.tile_size || defaultGridSize());
            canvas.dataset.sceneGridVisible = scenePayload.grid_visible === false ? "false" : "true";
            canvas.dataset.sceneGridOffsetX = String(scenePayload.grid_offset_x || 0);
            canvas.dataset.sceneGridOffsetY = String(scenePayload.grid_offset_y || 0);
            canvas.dataset.sceneGridColor = scenePayload.grid_color || "";
            canvas.dataset.sceneGridOpacity = String(scenePayload.grid_opacity ?? 0.4);
            canvas.dataset.sceneDarkness = String(scenePayload.darkness ?? 0);
            canvas.dataset.sceneDarknessConfig = String(scenePayload.darkness_config ?? scenePayload.darkness ?? 0);
            canvas.dataset.sceneLightingMode = scenePayload.lighting_mode || "none";
            canvas.dataset.sceneLightsOut = scenePayload.lights_out === false ? "false" : "true";
            canvas.dataset.sceneImageScale = String(scenePayload.image_scale || 1);
            canvas.dataset.sceneStartWorldX = String(scenePayload.start_world_x ?? (scenePayload.width || 0) / 2);
            canvas.dataset.sceneStartWorldY = String(scenePayload.start_world_y ?? (scenePayload.height || 0) / 2);
            canvas.dataset.sceneStartZoom = String(scenePayload.start_zoom || 1);
            canvas.dataset.sceneLayerId = scenePayload.layer_id || "";
            canvas.dataset.sceneTileVersion = nextTileVersion;

            const emptyOverlay = canvas.closest("[data-map-viewport]")?.querySelector("[data-map-overlay]");
            if (emptyOverlay) emptyOverlay.hidden = true;

            if (sceneChanged) {
                resetSceneRuntime(canvas);
                const cameraState = stateFor(canvas);
                applyCameraToState(canvas, initialCameraFor(canvas), cameraState);
                restoreSceneRuntime(canvas, scenePayload.id, nextTileVersion);
            } else {
                const runtime = runtimeFor(canvas);
                if (runtime.manifest && Number.isInteger(scenePayload.scene_epoch)) {
                    runtime.manifest.scene_epoch = scenePayload.scene_epoch;
                }
            }

            const scene = sceneDataFor(canvas);
            if (!scene) return;
            ensureManifest(canvas, scene);
            loadTokensForScene(canvas, scene, true);
            scheduleViewportUpdate(canvas, true);
            markDirty(canvas);
        }

        function defaultGridSize() {
            return deps.defaultGridSize;
        }

        function handleSceneActivated(payload) {
            if (!payload?.room_id || !payload?.scene) return;
            document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
                if (canvas.dataset.roomId !== payload.room_id) return;
                canvas.dataset.loadedSceneId = payload.scene.id;
                const navigatingLocally = canvas.dataset.localSceneNavigation === "true"
                    && canvas.dataset.sceneId !== payload.scene.id;
                if (navigatingLocally) return;
                canvas.dataset.localSceneNavigation = "false";
                syncCanvasScene(canvas, payload.scene);
            });
        }




        function handleSceneUpdated(payload) {
            if (!payload?.room_id || !payload?.scene?.id) return;
            document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
                if (canvas.dataset.roomId !== payload.room_id) return;
                if (canvas.dataset.sceneId !== payload.scene.id) return;
                syncCanvasScene(canvas, payload.scene);
            });
        }

        function debugSnapshot(canvas) {
            const scene = canvas ? sceneDataFor(canvas) : null;
            const runtime = canvas ? runtimeFor(canvas) : null;
            const cameraState = canvas ? stateFor(canvas) : null;
            const range = scene ? visibleChunkRange(canvas, scene, cameraState) : null;
            const layerIds = scene ? layerIdsFor(canvas, scene) : [];
            return {
                manifestLoaded: !!runtime?.manifest,
                generation: runtime?.generation ?? 0,
                range,
                layerIds,
                chunks: runtime ? [...runtime.chunks.keys()] : [],
                tileIndexPagesLoaded: runtime?.tileIndexPagesLoaded || 0,
                tileDescriptorCount: runtime?.tileDescriptorCount || 0,
                metrics: runtime ? {
                    ...runtime.metrics,
                    gm_hint_promotion_rate: runtime.metrics.gm_hint_created
                        ? runtime.metrics.gm_hint_promoted_to_visible / runtime.metrics.gm_hint_created : 0,
                    gm_hint_useful_byte_ratio: runtime.metrics.gm_hint_bytes_downloaded
                        ? runtime.metrics.gm_hint_bytes_used / runtime.metrics.gm_hint_bytes_downloaded : 0,
                } : null,
                gmHintStates: runtime ? [...runtime.gmHints.values()].map((hint) => ({
                    state: hint.state, score: hint.score, source: hint.source,
                    sources: [...hint.sources], bytes: hint.bytes, usedBytes: hint.usedBytes,
                })) : [],
                gmHintBuckets: runtime ? structuredClone(runtime.gmHintBuckets) : {},
                missingVisibleChunks: runtime && range ? missingVisibleChunkKeys(runtime, layerIds, range) : [],
                chunkRetryCount: runtime?.chunkRetryCount ?? 0,
            };
        }

        return {
            applyChunkBatchFrame,
            buildTileTables,
            ensureTileDescriptors,
            chunkKey,
            clearChunkStreamRetry,
            decodeChunkBatchFrame,
            decodeChunkRefsView,
            debugSnapshot,
            ensureManifest,
            handleChunkUpdated,
            handleGmPrefetchHint,
            handleSceneActivated,
            handleSceneUpdated,
            handleSessionResumed,
            handleViewportReady,
            invalidateSceneInfo,
            updateSceneInfoCache,
            knownChunksObject,
            layerIdsFor,
            missingVisibleChunkKeys,
            resetSceneRuntime,
            runtimeFor,
            scheduleChunkStreamRetry,
            scheduleViewportUpdate,
            sendSessionResume,
            sendViewportUpdate,
            syncCanvasScene,
            viewportFocusChunk,
            viewportKeyFor,
            viewportReadyFromCache,
            visibleChunkRange,
            visibleTileRange,
        };
    }

    window.GravewrightMapStreaming = { createSceneStreaming };
})();
