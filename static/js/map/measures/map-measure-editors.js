(() => {
    function createMeasureEditors(deps) {
        let activeAreaMarkerTextEditor = null;
        let activeTextEditor = null;
        const {
            activeDrawColor,
            applyActiveLayer,
            areaMarkerTextAnchor,
            broadcastAreaMarkerUpsert,
            broadcastDrawUpsert,
            currentUserId,
            history,
            isGmForCanvas,
            measureStoreFor,
            newMeasureId,
            normalizedAreaMarkerText,
            rawMeasurePointFromEvent,
            sceneDataFor,
            setSelectedMeasure,
            stateFor,
            textFontSizeFor,
            upsertMeasureLocal,
            worldToScreenXY,
        } = deps;

        function areaMarkerTextPlaceholder() {
            return document.querySelector('[data-tool-sub-panel="shape"]')?.dataset.textPlaceholder
                || "Text for players";
        }

        function positionAreaMarkerTextEditor(editor = activeAreaMarkerTextEditor) {
            if (!editor) return;
            const marker = measureStoreFor(editor.canvas).find((item) => item.id === editor.markerId);
            if (!marker) return;
            const screen = worldToScreenXY(areaMarkerTextAnchor(marker), stateFor(editor.canvas));
            editor.input.style.left = `${Math.round(screen.x)}px`;
            editor.input.style.top = `${Math.round(screen.y)}px`;
        }

        function startAreaMarkerTextEditor(canvas, marker) {
            if (!isGmForCanvas(canvas)) return false;
            commitAreaMarkerTextEditor();

            const input = document.createElement("textarea");
            input.maxLength = 220;
            input.rows = 2;
            input.className = "board-area-marker-input";
            input.placeholder = areaMarkerTextPlaceholder();
            input.value = normalizedAreaMarkerText(marker);
            document.body.appendChild(input);

            activeAreaMarkerTextEditor = { canvas, input, markerId: marker.id };
            positionAreaMarkerTextEditor(activeAreaMarkerTextEditor);

            input.addEventListener("keydown", (ev) => {
                if (ev.key === "Enter" && !ev.shiftKey) {
                    ev.preventDefault();
                    commitAreaMarkerTextEditor();
                } else if (ev.key === "Escape") {
                    ev.preventDefault();
                    cancelAreaMarkerTextEditor({ broadcast: true });
                }
            });
            input.addEventListener("blur", () => commitAreaMarkerTextEditor());

            requestAnimationFrame(() => {
                input.focus();
                input.select();
            });
            return true;
        }

        function commitAreaMarkerTextEditor() {
            const editor = activeAreaMarkerTextEditor;
            if (!editor) return;
            activeAreaMarkerTextEditor = null;

            const text = normalizedAreaMarkerText({ text: editor.input.value });
            editor.input.remove();

            const marker = measureStoreFor(editor.canvas).find((item) => item.id === editor.markerId);
            if (!marker) return;

            const before = JSON.parse(JSON.stringify(marker));
            const next = { ...marker };
            if (text) next.text = text;
            else delete next.text;

            upsertMeasureLocal(editor.canvas, next);
            setSelectedMeasure(editor.canvas, next.id);
            broadcastAreaMarkerUpsert(editor.canvas, next);
            history?.push?.({
                undo() {
                    broadcastAreaMarkerUpsert(editor.canvas, before);
                },
                redo() {
                    broadcastAreaMarkerUpsert(editor.canvas, next);
                },
            });
        }

        function cancelAreaMarkerTextEditor({ broadcast = false } = {}) {
            const editor = activeAreaMarkerTextEditor;
            if (!editor) return;
            activeAreaMarkerTextEditor = null;
            editor.input.remove();
            const marker = measureStoreFor(editor.canvas).find((item) => item.id === editor.markerId);
            if (marker && broadcast) broadcastAreaMarkerUpsert(editor.canvas, marker);
        }

        function startTextPlacement(canvas, event) {
            const scene = sceneDataFor(canvas);
            if (!scene) return false;
            commitTextEditor();
            const position = rawMeasurePointFromEvent(canvas, event);
            if (!position) return false;

            const state = stateFor(canvas);
            const fontSize = textFontSizeFor(scene);
            const color = activeDrawColor(canvas);
            const screen = worldToScreenXY(position, state);

            const input = document.createElement("input");
            input.type = "text";
            input.maxLength = 200;
            input.className = "board-text-input";
            input.placeholder = document.querySelector('[data-tool-sub-panel="draw"]')?.dataset.textPlaceholder || "";
            input.style.left = `${Math.round(screen.x)}px`;
            input.style.top = `${Math.round(screen.y)}px`;
            input.style.fontSize = `${Math.max(8, fontSize * state.zoom)}px`;
            input.style.color = /^#[0-9a-fA-F]{6}$/.test(color) ? color : "#f8fafc";
            document.body.appendChild(input);

            activeTextEditor = { canvas, input, position, fontSize, color: input.style.color };

            input.addEventListener("keydown", (ev) => {
                if (ev.key === "Enter") {
                    ev.preventDefault();
                    commitTextEditor();
                } else if (ev.key === "Escape") {
                    ev.preventDefault();
                    cancelTextEditor();
                }
            });
            input.addEventListener("blur", () => commitTextEditor());

            requestAnimationFrame(() => input.focus());
            return true;
        }

        function commitTextEditor() {
            const editor = activeTextEditor;
            if (!editor) return;
            activeTextEditor = null;
            const text = editor.input.value.trim();
            editor.input.remove();
            if (!text) return;

            const scene = sceneDataFor(editor.canvas);
            if (!scene) return;
            const saved = {
                id: newMeasureId().replace("measure-", "text-"),
                scene_id: scene.id,
                kind: "text",
                position: editor.position,
                text,
                fontSize: editor.fontSize,
                style: { fill: editor.color },
                owner_id: currentUserId(),
            };
            applyActiveLayer(saved, editor.canvas);
            upsertMeasureLocal(editor.canvas, saved);
            broadcastDrawUpsert(editor.canvas, saved);
            history?.push?.({
                undo() {
                    window.GravewrightRealtime?.sendCommand?.(
                        "board.area_marker.delete",
                        { scene_id: saved.scene_id, marker_id: saved.id },
                        { sceneId: saved.scene_id, roomId: editor.canvas.dataset.roomId || "" },
                    );
                },
                redo() {
                    broadcastDrawUpsert(editor.canvas, saved);
                },
            });
        }

        function cancelTextEditor() {
            const editor = activeTextEditor;
            if (!editor) return;
            activeTextEditor = null;
            editor.input.remove();
        }

        function activeAreaMarkerCanvas() {
            return activeAreaMarkerTextEditor?.canvas || null;
        }

        function activeTextCanvas() {
            return activeTextEditor?.canvas || null;
        }

        return {
            activeAreaMarkerCanvas,
            activeTextCanvas,
            areaMarkerTextPlaceholder,
            cancelAreaMarkerTextEditor,
            cancelTextEditor,
            commitAreaMarkerTextEditor,
            commitTextEditor,
            positionAreaMarkerTextEditor,
            startAreaMarkerTextEditor,
            startTextPlacement,
        };
    }

    window.GravewrightMapMeasureEditors = { createMeasureEditors };
})();
