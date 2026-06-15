(() => {
    function bindRealtimeEvents(deps) {
        const {
            activeCanvas,
            applyChunkBatchFrame,
            applyMeasureSnapshot,
            applyRemoteAreaMarkerClear,
            applyRemoteAreaMarkerDelete,
            applyRemoteAreaMarkerUpsert,
            applyRemoteDrawClear,
            applyRemoteDrawUpsert,
            applyRemoteMeasureClear,
            applyRemoteMeasureDelete,
            applyRemoteMeasureFlash,
            handleBoardPing,
            handleChunkUpdated,
            handleSceneActivated,
            handleSessionResumed,
            handleViewportReady,
            handleTokensConditionsUpdated,
            handleTokensCreated,
            handleTokensDeleted,
            handleTokensMoved,
            handleTokensSnapshot,
            handleTokensUpdated,
            handleTokensVisibilityChanged,
            loadTokensForScene,
            reloadTokensForRoom,
            sceneDataFor,
            scheduleViewportUpdate,
            sendSessionResume,
        } = deps;

        document.addEventListener("vtt:ws-open", () => {
            const canvas = activeCanvas();
            if (!canvas) return;
            if (!sendSessionResume(canvas)) scheduleViewportUpdate(canvas, true);
            const scene = sceneDataFor(canvas);
            if (scene) loadTokensForScene(canvas, scene, true);
        });

        document.addEventListener("vtt:transport-event", (event) => {
            const { event: evtName, payload } = event.detail ?? {};

            if (evtName === "scene.session.resumed") handleSessionResumed(payload);
            if (evtName === "scene.viewport.ready") handleViewportReady(payload);
            if (evtName === "scene.activated") handleSceneActivated(payload);
            if (evtName === "scene.deleted") {
                const deletedId = payload?.scene_id;
                const showing = deletedId && [...document.querySelectorAll("[data-map-canvas]")]
                    .some((canvas) => canvas.dataset.sceneId === deletedId);
                if (showing) window.location.reload();
            }
            if (evtName === "campaign.packages.changed") {
                const roomId = payload?.room_id;
                const showing = roomId && document.querySelector(`[data-room-id="${CSS.escape(roomId)}"]`);
                if (showing) window.location.reload();
            }
            if (evtName === "scene.chunk.updated") handleChunkUpdated(payload);
            if (evtName === "tokens.snapshot") handleTokensSnapshot(payload);
            if (evtName === "tokens.created") handleTokensCreated(payload);
            if (evtName === "tokens.moved") handleTokensMoved(payload);
            if (evtName === "tokens.updated") handleTokensUpdated(payload);
            if (evtName === "tokens.deleted") handleTokensDeleted(payload);
            if (evtName === "tokens.visibility_changed") handleTokensVisibilityChanged(payload);
            if (evtName === "tokens.conditions.updated") handleTokensConditionsUpdated(payload);
            if (evtName === "board.ping") handleBoardPing(payload);
            if (evtName === "board.area_marker.upserted") applyRemoteAreaMarkerUpsert(payload);
            if (evtName === "board.area_marker.deleted") applyRemoteAreaMarkerDelete(payload);
            if (evtName === "board.area_marker.cleared") applyRemoteAreaMarkerClear(payload);
            if (evtName === "board.measure.flashed") applyRemoteMeasureFlash(payload);
            if (evtName === "board.measure.deleted") applyRemoteMeasureDelete(payload);
            if (evtName === "board.measure.cleared") applyRemoteMeasureClear(payload);
            if (evtName === "board.draw.upserted") applyRemoteDrawUpsert(payload);
            if (evtName === "board.draw.cleared") applyRemoteDrawClear(payload);
            if (evtName === "sheet.owners.updated" || evtName === "sheet.deleted") {
                reloadTokensForRoom(payload?.room_id);
            }
        });

        document.addEventListener("vtt:binary-frame", (event) => {
            applyChunkBatchFrame(event.detail);
        });
    }

    window.GravewrightMapRealtimeEvents = { bindRealtimeEvents };
})();
