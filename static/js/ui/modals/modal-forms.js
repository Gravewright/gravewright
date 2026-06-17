(() => {
    const SCENE_CANVAS_ATTRS = [
        "data-scene-id",
        "data-scene-width",
        "data-scene-height",
        "data-scene-tile-size",
        "data-scene-grid-visible",
        "data-scene-grid-color",
        "data-scene-grid-opacity",
        "data-scene-image-scale",
        "data-scene-start-world-x",
        "data-scene-start-world-y",
        "data-scene-start-zoom",
        "data-scene-layer-id",
        "data-scene-tile-version",
    ];

    function createModalForms(deps) {
        const { bringToFront, closeModal, cssEscape, queueFitModalToContent } = deps;

        function syncCanvasFromResponse(doc, form) {
            const campaignId = form.querySelector('[name="campaign_id"]')?.value;
            if (!campaignId) return;

            const selector = `[data-map-canvas][data-room-id="${cssEscape(campaignId)}"]`;
            const nextCanvas = doc.querySelector(selector);
            const liveCanvas = document.querySelector(selector);
            if (!nextCanvas || !liveCanvas) return;

            let changed = false;
            for (const attr of SCENE_CANVAS_ATTRS) {
                const next = nextCanvas.getAttribute(attr);
                const current = liveCanvas.getAttribute(attr);
                if (next !== current) {
                    if (next === null) liveCanvas.removeAttribute(attr);
                    else liveCanvas.setAttribute(attr, next);
                    changed = true;
                }
            }

            if (changed && window.GravewrightMap) window.GravewrightMap.redraw();
        }

        function applyDotColors(root) {
            root.querySelectorAll(".scene-group-dot[data-dot-color]").forEach((el) => {
                el.style.background = el.dataset.dotColor;
            });
        }

        function dismissAutoNotices(root = document) {
            root.querySelectorAll("[data-auto-dismiss]").forEach((notice) => {
                if (notice.dataset.dismissScheduled === "true") return;
                notice.dataset.dismissScheduled = "true";
                window.setTimeout(() => {
                    notice.classList.add("is-dismissing");
                    window.setTimeout(() => notice.remove(), 220);
                }, 5000);
            });
        }

        function sceneGroupOpenLabels(modal) {
            return new Set(
                [...modal.querySelectorAll(".scene-group-block[open] summary strong")]
                    .map((label) => label.textContent.trim())
                    .filter(Boolean)
            );
        }

        function restoreSceneGroupOpenLabels(modal, labels) {
            if (!labels.size) return;
            modal.querySelectorAll(".scene-group-block").forEach((group) => {
                const label = group.querySelector("summary strong")?.textContent.trim();
                if (label && labels.has(label)) group.open = true;
            });
        }

        function showSceneRequestError(modal) {
            const body = modal.querySelector(".scene-manager-body");
            if (!body) return;

            const notice = document.createElement("div");
            notice.className = "game-notice game-notice--danger";
            notice.dataset.autoDismiss = "";
            notice.setAttribute("role", "alert");
            notice.textContent = document.body.dataset.sceneRequestError || "Could not update scenes.";
            body.prepend(notice);
            dismissAutoNotices(body);
        }

        function resolveSceneManagerModal(form) {
            let modal = form.closest(".scene-manager-modal");
            if (!modal) {
                const campaignId = form.querySelector("input[name='campaign_id']")?.value;
                if (campaignId) {
                    modal = document.querySelector(
                        `[data-modal-id="scene-manager-${cssEscape(campaignId)}"]`
                    );
                }
            }
            return modal;
        }

        function applySceneManagerResponse(text, { modal, modalId, form, editModal, openLabels }) {
            const doc = new DOMParser().parseFromString(text, "text/html");
            const nextBody = doc.querySelector(
                `[data-modal-id="${cssEscape(modalId)}"] .scene-manager-body`
            );
            const currentBody = modal.querySelector(".scene-manager-body");

            if (!nextBody || !currentBody) throw new Error("Scene manager body missing from response");

            currentBody.replaceWith(nextBody);
            applyDotColors(nextBody);
            syncCanvasFromResponse(doc, form);
            restoreSceneGroupOpenLabels(modal, openLabels);
            dismissAutoNotices(modal);
            if (editModal) closeModal(editModal);
            modal.hidden = false;
            bringToFront(modal);
            queueFitModalToContent(modal);
        }

        async function submitSceneAjaxForm(form, submitter) {
            if (form.matches("[data-upload-progress-form]")) {
                submitMapUploadForm(form, submitter);
                return;
            }

            const modal = resolveSceneManagerModal(form);
            const editModal = form.closest(".scene-edit-modal");
            const modalId = modal?.dataset.modalId;
            if (!modal || !modalId) {
                form.submit();
                return;
            }

            const openLabels = sceneGroupOpenLabels(modal);
            const method = (form.getAttribute("method") || "POST").toUpperCase();
            const isMultipart = form.enctype === "multipart/form-data";
            const formData = new FormData(form);
            const body = isMultipart ? formData : new URLSearchParams(formData);

            if (submitter) {
                submitter.disabled = true;
                submitter.setAttribute("aria-busy", "true");
            }

            try {
                const response = await fetch(form.action, {
                    method,
                    body,
                    credentials: "same-origin",
                    headers: {
                        Accept: "text/html",
                        "X-Requested-With": "fetch",
                    },
                });
                if (!response.ok) throw new Error(`Scene action failed: ${response.status}`);
                applySceneManagerResponse(await response.text(), { modal, modalId, form, editModal, openLabels });
            } catch {
                showSceneRequestError(editModal || modal);
            } finally {
                if (submitter) {
                    submitter.disabled = false;
                    submitter.removeAttribute("aria-busy");
                }
            }
        }

        function createUploadProgressController(form) {
            const root = form.querySelector("[data-upload-progress]");
            const bar = root?.querySelector("[data-upload-progress-bar]");
            const labelEl = root?.querySelector("[data-upload-progress-label]");
            const pctEl = root?.querySelector("[data-upload-progress-pct]");
            const labels = {
                uploading: root?.dataset.labelUploading || "Uploading...",
                preparing: root?.dataset.labelPreparing || "Preparing...",
                tiling: root?.dataset.labelTiling || "Processing...",
                chunking: root?.dataset.labelChunking || "Processing...",
                complete: root?.dataset.labelComplete || "Done",
            };

            return {
                show() {
                    if (root) root.hidden = false;
                },
                hide() {
                    if (root) root.hidden = true;
                },
                update(phase, percent) {
                    const clamped = Math.max(0, Math.min(100, Math.round(percent)));
                    if (bar) {
                        bar.style.width = `${clamped}%`;
                        bar.parentElement?.setAttribute("aria-valuenow", String(clamped));
                    }
                    if (pctEl) pctEl.textContent = `${clamped}%`;
                    if (labelEl) labelEl.textContent = labels[phase] || labels.tiling;
                },
            };
        }

        function submitMapUploadForm(form, submitter) {
            const modal = resolveSceneManagerModal(form);
            const editModal = form.closest(".scene-edit-modal");
            const modalId = modal?.dataset.modalId;
            if (!modal || !modalId) {
                form.submit();
                return;
            }

            const openLabels = sceneGroupOpenLabels(modal);
            const formData = new FormData(form);
            let uploadId = (form.querySelector("input[name='upload_id']")?.value || "").trim();
            if (!uploadId) {
                uploadId = window.crypto?.randomUUID?.() || `up-${Date.now()}-${Math.random().toString(16).slice(2)}`;
            }
            formData.set("upload_id", uploadId);

            const progress = createUploadProgressController(form);
            const UPLOAD_WEIGHT = 0.15;
            let uploadPct = 0;
            let serverPct = 0;

            const render = (phase) => {
                progress.update(phase, UPLOAD_WEIGHT * uploadPct + (1 - UPLOAD_WEIGHT) * serverPct);
            };

            const onTransport = (event) => {
                const envelope = event.detail;
                if (!envelope || envelope.event !== "scene.upload.progress") return;
                const payload = envelope.payload || {};
                if (payload.upload_id !== uploadId) return;
                if (typeof payload.percent === "number") serverPct = payload.percent;
                render(payload.phase || "tiling");
            };
            document.addEventListener("vtt:transport-event", onTransport);

            const cleanup = () => {
                document.removeEventListener("vtt:transport-event", onTransport);
                if (submitter) {
                    submitter.disabled = false;
                    submitter.removeAttribute("aria-busy");
                }
            };

            if (submitter) {
                submitter.disabled = true;
                submitter.setAttribute("aria-busy", "true");
            }
            progress.show();
            render("uploading");

            const xhr = new XMLHttpRequest();
            xhr.open((form.getAttribute("method") || "POST").toUpperCase(), form.action, true);
            xhr.withCredentials = true;
            xhr.setRequestHeader("Accept", "text/html");
            xhr.setRequestHeader("X-Requested-With", "fetch");

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    uploadPct = (e.loaded / e.total) * 100;
                    render("uploading");
                }
            });
            xhr.upload.addEventListener("load", () => {
                uploadPct = 100;
                render("preparing");
            });
            xhr.addEventListener("load", () => {
                if (xhr.status < 200 || xhr.status >= 400) {
                    cleanup();
                    progress.hide();
                    showSceneRequestError(editModal || modal);
                    return;
                }
                try {
                    serverPct = 100;
                    render("complete");
                    applySceneManagerResponse(xhr.responseText, { modal, modalId, form, editModal, openLabels });
                } catch {
                    showSceneRequestError(editModal || modal);
                } finally {
                    cleanup();
                    progress.hide();
                }
            });
            xhr.addEventListener("error", () => {
                cleanup();
                progress.hide();
                showSceneRequestError(editModal || modal);
            });
            xhr.addEventListener("abort", () => {
                cleanup();
                progress.hide();
            });

            try {
                xhr.send(formData);
            } catch {
                cleanup();
                progress.hide();
                showSceneRequestError(editModal || modal);
            }
        }

        async function submitPanelAjaxForm(form, submitter) {
            const modal = form.closest("[data-modal-window]");
            const modalId = modal?.dataset.modalId;
            if (!modal || !modalId) {
                form.submit();
                return;
            }

            if (submitter) {
                submitter.disabled = true;
                submitter.setAttribute("aria-busy", "true");
            }

            try {
                const response = await fetch(form.action, {
                    method: (form.getAttribute("method") || "POST").toUpperCase(),
                    body: new URLSearchParams(new FormData(form)),
                    credentials: "same-origin",
                    headers: {
                        Accept: "text/html",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-Requested-With": "fetch",
                    },
                });
                if (!response.ok) throw new Error(`Panel action failed: ${response.status}`);

                const doc = new DOMParser().parseFromString(await response.text(), "text/html");
                const nextBody = doc.querySelector(
                    `[data-modal-id="${cssEscape(modalId)}"] .game-panel-body`
                );
                const currentBody = modal.querySelector(".game-panel-body");
                if (!nextBody || !currentBody) throw new Error("Panel body missing from response");

                currentBody.replaceWith(nextBody);
                dismissAutoNotices(modal);
                modal.hidden = false;
                bringToFront(modal);
                queueFitModalToContent(modal);
            } catch {
                
            } finally {
                if (submitter) {
                    submitter.disabled = false;
                    submitter.removeAttribute("aria-busy");
                }
            }
        }

        async function submitTableSettingsForm(form, submitter) {
            if (submitter) submitter.disabled = true;
            try {
                const res = await fetch(form.action, {
                    method: "POST",
                    body: new URLSearchParams(new FormData(form)),
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                });
                if (!res.ok) return;
                const payload = await res.json();
                const seconds = String(payload.measure_flash_seconds || "");
                if (!seconds) return;
                form.querySelector("[data-measure-flash-seconds-input]").value = seconds;
                const roomId = form.dataset.roomId || "";
                document.querySelectorAll(`[data-map-canvas][data-room-id="${cssEscape(roomId)}"]`).forEach((canvas) => {
                    canvas.dataset.measureFlashSeconds = seconds;
                });
            } catch {
                
            } finally {
                if (submitter) submitter.disabled = false;
            }
        }

        async function submitResourcePermissionsForm(form, submitter) {
            const modal = form.closest("[data-modal-window]");
            if (submitter) submitter.disabled = true;
            try {
                const res = await fetch(form.action, {
                    method: "POST",
                    body: new URLSearchParams(new FormData(form)),
                    credentials: "same-origin",
                    headers: {
                        Accept: "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                });
                if (!res.ok) return;
                const resourceType = form.querySelector("input[name='resource_type']")?.value;
                const resourceId = form.querySelector("input[name='resource_id']")?.value;
                document.dispatchEvent(new CustomEvent("vtt:resource-permissions-saved", {
                    detail: { resourceType, resourceId },
                }));
                if (modal) closeModal(modal);
            } catch {
                
            } finally {
                if (submitter) submitter.disabled = false;
            }
        }

        function syncGridOpacityOutput(slider) {
            const output = slider.parentElement?.querySelector("[data-grid-opacity-output]");
            if (output) output.textContent = parseFloat(slider.value).toFixed(2);
        }

        function syncWarnOnChange(input) {
            let warning = input.nextElementSibling;
            if (!warning || !warning.classList.contains("scene-field-warning")) {
                warning = document.createElement("small");
                warning.className = "scene-field-warning";
                warning.textContent = input.dataset.warnOnChange;
                input.after(warning);
            }
            warning.hidden = input.value === String(input.defaultValue);
        }

        function confirmWarnOnChange(form) {
            const warnInput = form.querySelector("[data-warn-on-change]");
            return !warnInput
                || warnInput.value === String(warnInput.defaultValue)
                || window.confirm(warnInput.dataset.warnOnChange);
        }

        return {
            applyDotColors,
            confirmWarnOnChange,
            dismissAutoNotices,
            submitPanelAjaxForm,
            submitResourcePermissionsForm,
            submitSceneAjaxForm,
            submitTableSettingsForm,
            syncGridOpacityOutput,
            syncWarnOnChange,
        };
    }

    window.GravewrightModalForms = { createModalForms };
})();
