(() => {
    function createModalDocking(deps) {
        const gravewrightPanelGroups = new Map();
        const {
            bringToFront,
            classicLayout,
            cssEscape,
            defaultLayout,
            defaultPanelWidth,
            defaultY,
            dockClearance,
            layoutStorageKey,
            modalLayout,
            observeModal,
            queueFitModalToContent,
        } = deps;

        function dockButtonFor(modalId) {
            return document.querySelector(`[data-modal-restore="${modalId}"]`);
        }

        function panelToggleFor(panelId) {
            return document.querySelector(`[data-panel-toggle="${panelId}"]`);
        }

        function isValidLayoutMode(mode) {
            return mode === defaultLayout || mode === classicLayout;
        }

        function getLayoutMode() {
            const mode = document.body.dataset.gameLayout || defaultLayout;
            return isValidLayoutMode(mode) ? mode : defaultLayout;
        }

        function isClassicLayout() {
            if (document.body.dataset.detachedModal) return false;
            return getLayoutMode() === classicLayout;
        }

        function isClassicPanel(modal) {
            return modal?.classList.contains("game-panel") && isClassicLayout();
        }

        function getActiveRoomId() {
            const checked = document.querySelector('input[name="selected-room"]:checked');
            return checked ? checked.value : null;
        }

        function panelSelectorForRoom(roomId) {
            return `.game-panel[data-panel-room="${cssEscape(roomId)}"]`;
        }

        function defaultPanelIdForRoom(roomId) {
            return `panel-chat-${roomId}`;
        }

        function setPanelToggleState(panelId, isPressed) {
            document.querySelectorAll(`[data-panel-toggle="${panelId}"]`).forEach((btn) => {
                btn.setAttribute("aria-pressed", isPressed ? "true" : "false");
            });
        }

        function isGravewrightPanel(modal) {
            return (
                modal?.classList.contains("game-panel")
                && !isClassicLayout()
                && !document.body.dataset.detachedModal
            );
        }

        function gravewrightPanelGroup(roomId, create = false) {
            if (!roomId) return null;
            if (!gravewrightPanelGroups.has(roomId) && create) {
                gravewrightPanelGroups.set(roomId, {
                    roomId,
                    panelIds: [],
                    activePanelId: null,
                });
            }
            return gravewrightPanelGroups.get(roomId) || null;
        }

        function clearGravewrightPanelTabs() {
            document.querySelectorAll(".game-panel-tabs").forEach((tabs) => tabs.remove());
            gravewrightPanelGroups.clear();
        }

        function panelTabLabel(panel) {
            return panel.querySelector(".game-panel-title")?.textContent.trim()
                || panel.dataset.modalId
                || "";
        }

        function renderGravewrightPanelTabs(group) {
            group.panelIds = group.panelIds.filter((panelId) => (
                document.querySelector(`.game-panel[data-modal-id="${cssEscape(panelId)}"]`)
            ));

            group.panelIds.forEach((panelId) => {
                const panel = document.querySelector(
                    `.game-panel[data-modal-id="${cssEscape(panelId)}"]`
                );
                panel?.querySelector(":scope > .game-panel-tabs")?.remove();
            });

            if (group.panelIds.length < 2) return;

            const activePanel = document.querySelector(
                `.game-panel[data-modal-id="${cssEscape(group.activePanelId)}"]`
            );
            const titlebar = activePanel?.querySelector(":scope > .game-modal-titlebar");
            if (!titlebar) return;

            const tabs = document.createElement("nav");
            tabs.className = "game-panel-tabs";
            tabs.setAttribute("role", "tablist");
            tabs.setAttribute("aria-label", "Ferramentas abertas");

            group.panelIds.forEach((panelId) => {
                const panel = document.querySelector(
                    `.game-panel[data-modal-id="${cssEscape(panelId)}"]`
                );
                if (!panel) return;

                const item = document.createElement("span");
                item.className = "game-panel-tab-item";

                const tab = document.createElement("button");
                tab.className = "game-panel-tab";
                tab.type = "button";
                tab.dataset.gravewrightPanelTab = panelId;
                tab.setAttribute("role", "tab");
                tab.setAttribute("aria-selected", panelId === group.activePanelId ? "true" : "false");

                const dockIcon = panelToggleFor(panelId)?.querySelector("i");
                if (dockIcon) tab.appendChild(dockIcon.cloneNode());

                const label = document.createElement("span");
                label.textContent = panelTabLabel(panel);
                tab.title = label.textContent;
                tab.setAttribute("aria-label", label.textContent);
                tab.appendChild(label);

                const close = document.createElement("button");
                close.className = "game-panel-tab-close";
                close.type = "button";
                close.dataset.gravewrightPanelTabClose = panelId;
                close.setAttribute("aria-label", `Fechar ${label.textContent}`);
                close.innerHTML = '<i class="ph ph-x" aria-hidden="true"></i>';

                item.append(tab, close);
                tabs.appendChild(item);
            });

            titlebar.after(tabs);
        }

        function copyPanelFrame(sourcePanel, targetPanel) {
            if (!sourcePanel || !targetPanel || sourcePanel === targetPanel) return;

            const position = modalLayout.getPosition(sourcePanel);
            modalLayout.setPosition(targetPanel, position.x, position.y);

            if (sourcePanel.offsetWidth > 0) targetPanel.style.width = `${sourcePanel.offsetWidth}px`;
            if (sourcePanel.offsetHeight > 0) targetPanel.style.height = `${sourcePanel.offsetHeight}px`;


            if (sourcePanel.dataset.userSized === "true") {
                targetPanel.dataset.userSized = "true";
            } else {
                delete targetPanel.dataset.userSized;
            }
        }

        function showFloatingModal(modal, options = {}) {
            const key = modal.dataset.windowKey;
            modal.dataset.maximized = "false";

            if (options.framePrepared) {
                
            } else if (options.sourcePanel) {
                copyPanelFrame(options.sourcePanel, modal);
            } else if (modalLayout.restoreWindowState(modal)) {
                
            } else if (!modalLayout.hasPosition(key) && modal.classList.contains("game-panel")) {
                const x = Math.max(20, window.innerWidth - dockClearance - defaultPanelWidth);
                modalLayout.setPosition(modal, x, defaultY);
            } else {
                const currentPosition = modalLayout.getPosition(modal);
                modalLayout.setPosition(modal, currentPosition.x, currentPosition.y);
            }

            const dockButton = dockButtonFor(modal.dataset.modalId);
            modal.hidden = false;
            if (dockButton) dockButton.hidden = true;

            observeModal(modal);
            bringToFront(modal);

            if (options.fit !== false) {
                queueFitModalToContent(modal, { preserveWidth: Boolean(options.preserveWidth) });
            }
        }

        function activateGravewrightPanel(group, panelId, sourcePanel = null) {
            const panel = document.querySelector(
                `.game-panel[data-modal-id="${cssEscape(panelId)}"]`
            );
            if (!panel) return;

            const previousPanel = sourcePanel || document.querySelector(
                `.game-panel[data-modal-id="${cssEscape(group.activePanelId || "")}"]`
            );

            if (previousPanel && previousPanel !== panel) {
                copyPanelFrame(previousPanel, panel);
                previousPanel.hidden = true;
            }

            group.activePanelId = panelId;
            group.panelIds.forEach((groupPanelId) => {
                const groupPanel = document.querySelector(
                    `.game-panel[data-modal-id="${cssEscape(groupPanelId)}"]`
                );
                if (groupPanel && groupPanel !== panel) groupPanel.hidden = true;
                setPanelToggleState(groupPanelId, true);
            });

            showFloatingModal(panel, {
                framePrepared: Boolean(previousPanel && previousPanel !== panel),
                fit: true,
                preserveWidth: Boolean(previousPanel && previousPanel !== panel),
            });
            renderGravewrightPanelTabs(group);
        }

        function openGravewrightPanel(panel) {
            const panelId = panel.dataset.modalId;
            const roomId = panel.dataset.panelRoom;
            const group = gravewrightPanelGroup(roomId, true);

            if (!panelId || !group) {
                showFloatingModal(panel);
                return;
            }

            document.querySelectorAll(`${panelSelectorForRoom(roomId)}:not([hidden])`).forEach(
                (visiblePanel) => {
                    const visiblePanelId = visiblePanel.dataset.modalId;
                    if (visiblePanelId && !group.panelIds.includes(visiblePanelId)) {
                        group.panelIds.push(visiblePanelId);
                    }
                }
            );

            if (!group.panelIds.includes(panelId)) group.panelIds.push(panelId);
            activateGravewrightPanel(group, panelId);
        }

        function removeGravewrightPanel(panelId) {
            const panel = document.querySelector(
                `.game-panel[data-modal-id="${cssEscape(panelId)}"]`
            );
            const group = gravewrightPanelGroup(panel?.dataset.panelRoom);

            if (!panel || !group || !group.panelIds.includes(panelId)) return false;

            const removedIndex = group.panelIds.indexOf(panelId);
            group.panelIds.splice(removedIndex, 1);
            panel.querySelector(":scope > .game-panel-tabs")?.remove();
            setPanelToggleState(panelId, false);

            if (!group.panelIds.length) {
                panel.hidden = true;
                gravewrightPanelGroups.delete(group.roomId);
                return true;
            }

            if (group.activePanelId === panelId) {
                const nextIndex = Math.min(removedIndex, group.panelIds.length - 1);
                activateGravewrightPanel(group, group.panelIds[nextIndex], panel);
            } else {
                panel.hidden = true;
                renderGravewrightPanelTabs(group);
            }

            return true;
        }

        function toggleGravewrightPanel(panel) {
            const panelId = panel.dataset.modalId;
            const group = gravewrightPanelGroup(panel.dataset.panelRoom);

            if (panelId && group?.panelIds.includes(panelId)) {
                removeGravewrightPanel(panelId);
                return;
            }

            openGravewrightPanel(panel);
        }

        function closeClassicPanelsExcept(panelId) {
            document.querySelectorAll(".game-panel").forEach((panel) => {
                const isTarget = panel.dataset.modalId === panelId;
                panel.hidden = !isTarget;
                if (panel.dataset.modalId) setPanelToggleState(panel.dataset.modalId, isTarget);
            });
        }

        function openClassicPanel(panelId) {
            const panel = document.querySelector(`.game-panel[data-modal-id="${panelId}"]`);
            if (panel) closeClassicPanelsExcept(panelId);
        }

        function updateLayoutButtons(mode) {
            document.querySelectorAll("[data-layout-mode]").forEach((button) => {
                const selected = button.dataset.layoutMode === mode;
                button.setAttribute("aria-pressed", selected ? "true" : "false");
            });
        }

        function syncActiveRoomUi(roomId) {
            if (!roomId) return;

            document.querySelectorAll(".room-workspace").forEach((workspace) => {
                workspace.classList.toggle("is-active", workspace.dataset.roomId === roomId);
            });

            document.querySelectorAll("[data-dock-room]").forEach((dockGroup) => {
                dockGroup.hidden = dockGroup.dataset.dockRoom !== roomId;
            });

            if (isClassicLayout()) {
                const visiblePanel = document.querySelector(
                    `${panelSelectorForRoom(roomId)}:not([hidden])`
                );
                openClassicPanel(visiblePanel?.dataset.modalId || defaultPanelIdForRoom(roomId));
            }
        }

        async function persistLayoutMode(mode) {
            try {
                await fetch("/game/preferences/layout", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        Accept: "application/json",
                    },
                    body: new URLSearchParams({
                        csrf_token: document.body.dataset.presenceCsrfToken || "",
                        layout_mode: mode,
                    }),
                    credentials: "same-origin",
                });
            } catch {
                
            }
        }

        function applyLayoutMode(mode, preferredPanelId = null, persist = false) {
            const normalizedMode = isValidLayoutMode(mode) ? mode : defaultLayout;
            const previousMode = getLayoutMode();

            if (previousMode !== normalizedMode) clearGravewrightPanelTabs();
            document.body.dataset.gameLayout = normalizedMode;

            try {
                window.localStorage.setItem(layoutStorageKey, normalizedMode);
            } catch {
                
            }

            updateLayoutButtons(normalizedMode);

            if (normalizedMode === classicLayout) {
                const activeRoomId = getActiveRoomId();
                const panelId = preferredPanelId || (activeRoomId ? defaultPanelIdForRoom(activeRoomId) : null);
                if (panelId) openClassicPanel(panelId);
            } else if (previousMode !== normalizedMode) {
                const activeRoomId = getActiveRoomId();
                const visiblePanel = activeRoomId
                    ? document.querySelector(`${panelSelectorForRoom(activeRoomId)}:not([hidden])`)
                    : null;
                if (visiblePanel) openGravewrightPanel(visiblePanel);
            }

            window.requestAnimationFrame(() => {
                window.GravewrightMap?.redraw();
            });

            if (persist) persistLayoutMode(normalizedMode);
        }

        return {
            activateGravewrightPanel,
            applyLayoutMode,
            defaultPanelIdForRoom,
            dockButtonFor,
            getActiveRoomId,
            getLayoutMode,
            gravewrightPanelGroup,
            isClassicLayout,
            isClassicPanel,
            isGravewrightPanel,
            openClassicPanel,
            openGravewrightPanel,
            panelToggleFor,
            removeGravewrightPanel,
            setPanelToggleState,
            showFloatingModal,
            syncActiveRoomUi,
            toggleGravewrightPanel,
        };
    }

    window.GravewrightModalDocking = { createModalDocking };
})();
