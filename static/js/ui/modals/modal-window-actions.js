(() => {
    function createModalWindowActions(deps) {
        const {
            dockButtonFor,
            isClassicPanel,
            isGravewrightPanel,
            maxMargin,
            minHeight,
            minWidth,
            modalLayout,
            panelToggleFor,
            removeGravewrightPanel,
            setPanelToggleState,
        } = deps;

        function close(modal) {
            const modalId = modal.dataset.modalId;
            if (isClassicPanel(modal)) return;
            if (isGravewrightPanel(modal) && removeGravewrightPanel(modalId)) return;

            if (document.body.dataset.detachedModal && modalId === document.body.dataset.detachedModal) {
                window.close();
            }

            modal.hidden = true;
            // Let sheet runtimes tear down (e.g. unmount HTML sheets, drop listeners).
            document.dispatchEvent(new CustomEvent("vtt:modal-closed", { detail: { modal } }));

            if (modalId) {
                const dockButton = dockButtonFor(modalId);
                if (dockButton) dockButton.hidden = true;

                const panelBtn = panelToggleFor(modalId);
                if (panelBtn) panelBtn.setAttribute("aria-pressed", "false");
            }
        }

        function minimize(modal) {
            const modalId = modal.dataset.modalId;
            if (isClassicPanel(modal)) return;
            if (isGravewrightPanel(modal) && removeGravewrightPanel(modalId)) return;

            modal.hidden = true;
            if (!modalId) return;

            const dockButton = dockButtonFor(modalId);
            if (dockButton) dockButton.hidden = false;

            if (modal.classList.contains("game-panel")) {
                setPanelToggleState(modalId, false);
            }
        }

        function topVisible() {
            const visibleModals = [
                ...document.querySelectorAll(".game-modal-layer [data-modal-window]:not([hidden])"),
            ].filter((modal) => !isClassicPanel(modal));
            return visibleModals.at(-1) || null;
        }

        function toggleMaximize(modal) {
            if (isClassicPanel(modal)) return;

            if (modal.dataset.maximized === "true") {
                modal.dataset.maximized = "false";

                if (modal.dataset.restoreWidth) modal.style.width = modal.dataset.restoreWidth;
                if (modal.dataset.restoreHeight) modal.style.height = modal.dataset.restoreHeight;

                const x = Number(modal.dataset.restoreX);
                const y = Number(modal.dataset.restoreY);
                if (Number.isFinite(x) && Number.isFinite(y)) modalLayout.setPosition(modal, x, y);

                modalLayout.saveWindowState(modal);
                return;
            }

            const layer = modal.closest(".game-modal-layer");
            const layerRect = layer?.getBoundingClientRect();
            if (!layerRect) return;

            const position = modalLayout.getPosition(modal);
            modal.dataset.restoreWidth = modal.style.width || `${modal.offsetWidth}px`;
            modal.dataset.restoreHeight = modal.style.height || `${modal.offsetHeight}px`;
            modal.dataset.restoreX = String(position.x);
            modal.dataset.restoreY = String(position.y);
            modal.dataset.maximized = "true";

            modalLayout.setPosition(modal, maxMargin, maxMargin);
            modal.style.width = `${Math.max(minWidth, layerRect.width - maxMargin * 2)}px`;
            modal.style.height = `${Math.max(minHeight, layerRect.height - maxMargin * 2)}px`;
        }

        function detach(modal) {
            const modalId = modal.dataset.modalId;
            if (!modalId || isClassicPanel(modal)) return;

            const url = new URL("/game", window.location.origin);
            url.searchParams.set("detached_modal", modalId);
            const activeRoom = document.querySelector('input[name="selected-room"]:checked')?.value;
            if (activeRoom) url.searchParams.set("room", activeRoom);

            window.open(
                url.toString(),
                `gravewright-${modalId}`,
                "width=520,height=720,resizable=yes,scrollbars=yes,popup=yes"
            );

            minimize(modal);
        }

        return { close, detach, minimize, toggleMaximize, topVisible };
    }

    window.GravewrightModalWindowActions = { createModalWindowActions };
})();
