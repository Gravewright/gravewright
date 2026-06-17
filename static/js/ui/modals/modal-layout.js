(() => {
    function createModalLayout(deps) {
        const positions = new Map();
        const positionRules = new Map();
        const autoFitFrames = new WeakMap();
        const observedModals = new WeakSet();
        const programmaticSizes = new WeakMap();
        let resizeObserver = null;

        const {
            autoFitMargin,
            autoFitPadding,
            cssEscape,
            defaultFitHeight,
            defaultX,
            defaultY,
            isClassicPanel,
            minWindowHeight,
            minWindowWidth,
            windowStoragePrefix,
        } = deps;

        function clamp(value, min, max) {
            return Math.max(min, Math.min(value, max));
        }

        function dataNumber(modal, key) {
            const value = Number(modal.dataset[key]);
            return Number.isFinite(value) ? value : null;
        }

        function writableSheet() {
            for (const sheet of document.styleSheets) {
                if (sheet.href && sheet.href.includes("/static/css/game.css")) {
                    return sheet;
                }
            }
            return null;
        }

        function ensurePositionRule(modal) {
            const key = modal.dataset.windowKey;
            if (!key) return null;

            const existingRule = positionRules.get(key);
            if (existingRule) return existingRule;

            const sheet = writableSheet();
            if (!sheet) return null;

            const selector = `.game-modal-window[data-window-key="${cssEscape(key)}"]`;
            const index = sheet.cssRules.length;

            try {
                sheet.insertRule(`${selector}{left:${defaultX}px;top:${defaultY}px;}`, index);
                const rule = sheet.cssRules[index];
                positionRules.set(key, rule);
                return rule;
            } catch {
                return null;
            }
        }

        function setPosition(modal, x, y) {
            const key = modal.dataset.windowKey;
            if (!key) return;

            const rule = ensurePositionRule(modal);
            if (!rule) {
                positions.set(key, { x: defaultX, y: defaultY });
                return;
            }

            rule.style.left = `${Math.round(x)}px`;
            rule.style.top = `${Math.round(y)}px`;
            positions.set(key, { x, y });
        }

        function getPosition(modal) {
            const key = modal.dataset.windowKey;
            if (!key) return { x: defaultX, y: defaultY };
            return positions.get(key) || { x: defaultX, y: defaultY };
        }

        function hasPosition(key) {
            return positions.has(key);
        }

        function windowStorageKey(modal) {
            const key = modal.dataset.windowKey;
            return key ? `${windowStoragePrefix}${key}` : null;
        }

        function readWindowState(modal) {
            const key = windowStorageKey(modal);
            if (!key) return null;
            try {
                const state = JSON.parse(window.localStorage.getItem(key) || "null");
                return state && typeof state === "object" ? state : null;
            } catch {
                return null;
            }
        }

        function saveWindowState(modal) {
            if (
                modal.hidden ||
                modal.dataset.maximized === "true" ||
                modal.dataset.autoSizing === "true"
            ) {
                return;
            }

            if (isClassicPanel(modal)) return;

            const key = windowStorageKey(modal);
            const position = getPosition(modal);
            const width = modal.offsetWidth;
            const height = modal.offsetHeight;
            if (!key || width <= 0 || height <= 0) return;

            try {
                window.localStorage.setItem(
                    key,
                    JSON.stringify({
                        x: Math.round(position.x),
                        y: Math.round(position.y),
                        width: Math.round(width),
                        height: Math.round(height),
                        userSized: modal.dataset.userSized === "true",
                    })
                );
            } catch {
                
            }
        }

        function restoreWindowState(modal) {
            if (isClassicPanel(modal)) return false;

            const state = readWindowState(modal);
            if (!state) return false;

            let restored = false;

            if (Number.isFinite(state.x) && Number.isFinite(state.y)) {
                setPosition(modal, state.x, state.y);
                restored = true;
            }


            if (state.userSized && Number.isFinite(state.width) && Number.isFinite(state.height)) {
                modal.dataset.userSized = "true";
                modal.style.width = `${state.width}px`;
                modal.style.height = `${state.height}px`;
                restored = true;
            }

            return restored;
        }

        function fitModalToContent(modal, options = {}) {
            if (
                !modal ||
                modal.hidden ||
                isClassicPanel(modal) ||
                document.body.dataset.detachedModal ||
                modal.dataset.maximized === "true" ||
                modal.dataset.userSized === "true"
            ) {
                return;
            }

            const layer = modal.closest(".game-modal-layer");
            if (!layer) return;

            const layerRect = layer.getBoundingClientRect();
            const availableWidth = Math.max(minWindowWidth, Math.floor(layerRect.width - autoFitMargin * 2));
            const availableHeight = Math.max(minWindowHeight, Math.floor(layerRect.height - autoFitMargin * 2));

            modal.dataset.autoSizing = "true";
            modal.style.maxWidth = `${availableWidth}px`;
            modal.style.maxHeight = "none";
            if (!options.preserveWidth) modal.style.width = "max-content";
            modal.style.height = "max-content";

            const preferredWidth = Number(modal.dataset.autoFitWidth);
            const minFitWidth = dataNumber(modal, "autoFitMinWidth") || minWindowWidth;
            const minFitHeight = dataNumber(modal, "autoFitMinHeight") || defaultFitHeight;
            const width = options.preserveWidth
                ? clamp(modal.offsetWidth, Math.max(minWindowWidth, minFitWidth), availableWidth)
                : clamp(
                    Number.isFinite(preferredWidth)
                        ? Math.min(Math.ceil(modal.scrollWidth + autoFitPadding), preferredWidth)
                        : Math.ceil(modal.scrollWidth + autoFitPadding),
                    Math.max(minWindowWidth, minFitWidth),
                    availableWidth
                );
            modal.style.width = `${width}px`;

            const heightFloor = Math.min(Math.max(minWindowHeight, minFitHeight), availableHeight);
            const height = clamp(
                Math.ceil(modal.scrollHeight + autoFitPadding),
                heightFloor,
                availableHeight
            );
            modal.style.height = `${height}px`;
            modal.style.maxHeight = `${availableHeight}px`;

            const position = getPosition(modal);
            setPosition(
                modal,
                clamp(position.x, autoFitMargin, Math.max(autoFitMargin, layerRect.width - modal.offsetWidth - autoFitMargin)),
                clamp(position.y, autoFitMargin, Math.max(autoFitMargin, layerRect.height - modal.offsetHeight - autoFitMargin))
            );

            delete modal.dataset.autoSizing;


            programmaticSizes.set(modal, {
                width: Math.round(modal.offsetWidth),
                height: Math.round(modal.offsetHeight),
            });
        }

        function queueFitModalToContent(modal, options = {}) {
            const pendingFrame = autoFitFrames.get(modal);
            if (pendingFrame) window.cancelAnimationFrame(pendingFrame);

            const frame = window.requestAnimationFrame(() => {
                fitModalToContent(modal, options);
                const settleFrame = window.requestAnimationFrame(() => {
                    fitModalToContent(modal, options);
                    autoFitFrames.delete(modal);
                });
                autoFitFrames.set(modal, settleFrame);
            });

            autoFitFrames.set(modal, frame);
        }

        function observeModal(modal) {
            if (!resizeObserver || observedModals.has(modal)) return;
            resizeObserver.observe(modal);
            observedModals.add(modal);
        }

        function detectUserResize(modal) {
            if (
                modal.hidden ||
                isClassicPanel(modal) ||
                modal.dataset.maximized === "true" ||
                modal.dataset.autoSizing === "true" ||
                modal.dataset.userSized === "true"
            ) {
                return;
            }


            const expected = programmaticSizes.get(modal);
            if (!expected) return;

            const width = Math.round(modal.offsetWidth);
            const height = Math.round(modal.offsetHeight);
            if (Math.abs(expected.width - width) > 1 || Math.abs(expected.height - height) > 1) {
                modal.dataset.userSized = "true";
            }
        }

        function startResizeObserver() {
            resizeObserver = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    detectUserResize(entry.target);
                    saveWindowState(entry.target);
                }
            });
        }

        return {
            clamp,
            fitModalToContent,
            getPosition,
            hasPosition,
            observeModal,
            queueFitModalToContent,
            restoreWindowState,
            saveWindowState,
            setPosition,
            startResizeObserver,
        };
    }

    window.GravewrightModalLayout = { createModalLayout };
})();
