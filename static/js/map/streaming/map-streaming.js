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

            const s = scene.scaledTileSize;
            const tileCols = Math.ceil(scene.baseWidth / scene.tileSize);
            const tileRows = Math.ceil(scene.baseHeight / scene.tileSize);

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

            const tileCols = Math.ceil(scene.baseWidth / scene.tileSize);
            const tileRows = Math.ceil(scene.baseHeight / scene.tileSize);
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
            const s = scene.scaledTileSize;
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

        function chunkCacheIndexKey(sceneId, tileVersion) {
            return `gravewright.sceneChunks.${sceneId}.${tileVersion}.index`;
        }

        function chunkCacheKey(sceneId, tileVersion, key) {
            return `gravewright.sceneChunks.${sceneId}.${tileVersion}.${key}`;
        }

        function sceneInfoCacheKey(sceneId, sceneEpoch) {
            return `gravewright.sceneInfo.${sceneId}.${sceneEpoch}`;
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
                        runtime.generation = 0;
                        runtime.lastViewportKey = "";
                        runtime.cachedInfoEpoch = null;
                    }
                    runtime.manifest = manifest;
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

            if (runtime.pendingTimer) {
                window.clearTimeout(runtime.pendingTimer);
                runtime.pendingTimer = null;
            }

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

        function sendViewportUpdate(canvas, force = false) {
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

            const layerIds = layerIdsFor(canvas, scene);
            if (!layerIds.length) return false;

            const viewportKey = viewportKeyFor(scene, layerIds, range);
            if (viewportReadyFromCache(runtime, runtime.manifest, layerIds, range)) {
                runtime.lastViewportKey = viewportKey;
                clearChunkStreamRetry(runtime);
                markDirty(canvas);
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
            runtime.lastViewportKey = viewportKey;
            runtime.lastSentAt = Date.now();
            scheduleChunkStreamRetry(canvas, scene, layerIds, range);
            return true;
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
            canvas.dataset.sceneGridVisible = scenePayload.grid_visible === false ? "false" : "true";
            canvas.dataset.sceneGridColor = scenePayload.grid_color || "";
            canvas.dataset.sceneGridOpacity = String(scenePayload.grid_opacity ?? 0.4);
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
                if (canvas.dataset.roomId === payload.room_id) syncCanvasScene(canvas, payload.scene);
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
                missingVisibleChunks: runtime && range ? missingVisibleChunkKeys(runtime, layerIds, range) : [],
                chunkRetryCount: runtime?.chunkRetryCount ?? 0,
            };
        }

        return {
            applyChunkBatchFrame,
            buildTileTables,
            chunkKey,
            clearChunkStreamRetry,
            decodeChunkBatchFrame,
            decodeChunkRefsView,
            debugSnapshot,
            ensureManifest,
            handleChunkUpdated,
            handleSceneActivated,
            handleSessionResumed,
            handleViewportReady,
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
