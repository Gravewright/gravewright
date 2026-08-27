(() => {
    const FI = (window.GravewrightModalInternals = window.GravewrightModalInternals || {});
    const DEFAULT_X = 22;
    const DEFAULT_Y = 22;
    const PANEL_DEFAULT_WIDTH = 340;
    const CLASSIC_PANEL_WIDTH = 320;
    const CLASSIC_PANEL_TABS_HEIGHT = 46;
    const DOCK_CLEARANCE = 64;
    const LAYOUT_STORAGE_KEY = "gravewright.game.layout";
    const DEFAULT_LAYOUT = "gravewright";
    const CLASSIC_LAYOUT = "classic";
    const MAXIMIZED_MARGIN = 14;
    const AUTO_FIT_PADDING = 10;
    const AUTO_FIT_MARGIN = 10;
    const MIN_WINDOW_WIDTH = 260;
    const MIN_WINDOW_HEIGHT = 180;

    // Window geometry belongs to the signed-in user. Browsers are commonly
    // shared between the GM and a player during local sessions; using only the
    // resource id here leaked the GM's large editor dimensions into the
    // player's read-only window.
    const windowOwner = document.body.dataset.currentUserId || "anonymous";
    const modalLayout = window.GravewrightModalLayout.createModalLayout({
        autoFitMargin: AUTO_FIT_MARGIN,
        autoFitPadding: AUTO_FIT_PADDING,
        cssEscape,
        defaultX: DEFAULT_X,
        defaultY: DEFAULT_Y,
        isClassicPanel,
        isGravewrightPanel,
        gravewrightPanelHeightOffset: CLASSIC_PANEL_TABS_HEIGHT,
        gravewrightPanelWidth: CLASSIC_PANEL_WIDTH,
        minWindowHeight: MIN_WINDOW_HEIGHT,
        minWindowWidth: MIN_WINDOW_WIDTH,
        windowStoragePrefix: `gravewright.game.window.${windowOwner}.`,
    });
    const modalDocking = window.GravewrightModalDocking.createModalDocking({
        bringToFront,
        classicLayout: CLASSIC_LAYOUT,
        cssEscape,
        defaultLayout: DEFAULT_LAYOUT,
        defaultPanelWidth: PANEL_DEFAULT_WIDTH,
        defaultY: DEFAULT_Y,
        dockClearance: DOCK_CLEARANCE,
        layoutStorageKey: LAYOUT_STORAGE_KEY,
        modalLayout,
        observeModal,
        queueFitModalToContent,
    });
    const modalRemote = window.GravewrightModalRemote.createModalRemote({ cssEscape });
    const modalActions = window.GravewrightModalWindowActions.createModalWindowActions({
        dockButtonFor,
        isClassicPanel,
        isGravewrightPanel,
        maxMargin: MAXIMIZED_MARGIN,
        minHeight: MIN_WINDOW_HEIGHT,
        minWidth: MIN_WINDOW_WIDTH,
        modalLayout,
        panelToggleFor,
        removeGravewrightPanel,
        setPanelToggleState,
    });
    const modalForms = window.GravewrightModalForms.createModalForms({
        bringToFront,
        closeModal,
        cssEscape,
        queueFitModalToContent,
    });

    function cssEscape(value) {
        if (window.CSS && typeof window.CSS.escape === "function") {
            return window.CSS.escape(value);
        }

        return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
    }

    function setPosition(modal, x, y) {
        modalLayout.setPosition(modal, x, y);
    }

    function getPosition(modal) {
        return modalLayout.getPosition(modal);
    }

    function saveWindowState(modal) {
        modalLayout.saveWindowState(modal);
    }

    function restoreWindowState(modal) {
        return modalLayout.restoreWindowState(modal);
    }

    function fitModalToContent(modal, options = {}) {
        modalLayout.fitModalToContent(modal, options);
    }

    function queueFitModalToContent(modal, options = {}) {
        modalLayout.queueFitModalToContent(modal, options);
    }

    document.addEventListener("vtt:modal-content-updated", (event) => {
        const modal = event.detail?.modal;
        if (modal) {
            queueFitModalToContent(modal, { preserveWidth: true });
        }
    });

    function observeModal(modal) {
        modalLayout.observeModal(modal);
    }

    function bringToFront(modal) {
        const layer = modal.closest(".game-modal-layer");

        if (!layer) {
            return;
        }



        if (layer.lastElementChild === modal) {
            return;
        }

        layer.appendChild(modal);
    }

    function dockButtonFor(modalId) {
        return modalDocking.dockButtonFor(modalId);
    }

    function panelToggleFor(panelId) {
        return modalDocking.panelToggleFor(panelId);
    }

    function isClassicLayout() {
        return modalDocking.isClassicLayout();
    }

    function isClassicPanel(modal) {
        return modalDocking.isClassicPanel(modal);
    }

    function getActiveRoomId() {
        return modalDocking.getActiveRoomId();
    }

    function setPanelToggleState(panelId, isPressed) {
        modalDocking.setPanelToggleState(panelId, isPressed);
    }

    function isGravewrightPanel(modal) {
        return modalDocking.isGravewrightPanel(modal);
    }

    function gravewrightPanelGroup(roomId, create = false) {
        return modalDocking.gravewrightPanelGroup(roomId, create);
    }

    function showFloatingModal(modal, options = {}) {
        modalDocking.showFloatingModal(modal, options);
    }

    function activateGravewrightPanel(group, panelId, sourcePanel = null) {
        modalDocking.activateGravewrightPanel(group, panelId, sourcePanel);
    }

    function openGravewrightPanel(panel) {
        modalDocking.openGravewrightPanel(panel);
    }

    function removeGravewrightPanel(panelId) {
        return modalDocking.removeGravewrightPanel(panelId);
    }

    function toggleGravewrightPanel(panel) {
        modalDocking.toggleGravewrightPanel(panel);
    }

    function openClassicPanel(panelId) {
        modalDocking.openClassicPanel(panelId);
    }

    function syncActiveRoomUi(roomId) {
        modalDocking.syncActiveRoomUi(roomId);
    }

    function applyLayoutMode(mode, preferredPanelId = null, persist = false) {
        modalDocking.applyLayoutMode(mode, preferredPanelId, persist);
    }

    function openModal(modalId) {
        const modal = document.querySelector(`[data-modal-id="${modalId}"]`);

        if (!modal) {
            return;
        }

        if (isClassicPanel(modal)) {
            openClassicPanel(modalId);
            return;
        }

        if (isGravewrightPanel(modal)) {
            openGravewrightPanel(modal);
            return;
        }

        showFloatingModal(modal);
    }

    function resourcePanel(resourceType, campaignId = "", resourceId = "", trigger = null) {
        const panelAttr = `data-${resourceType}-panel`;
        const directPanel = trigger?.closest?.(`[${panelAttr}]`);
        if (directPanel) return directPanel.closest("[data-modal-window]") || directPanel;

        const idAttribute = resourceType === "actor"
            ? "data-actor-open"
            : resourceType === "item" ? "data-item-open" : "data-journal-id";
        const candidates = resourceId
            ? document.querySelectorAll(`[${idAttribute}="${cssEscape(resourceId)}"]`)
            : document.querySelectorAll(`[${panelAttr}]`);
        for (const candidate of candidates) {
            const panelBody = candidate.matches?.(`[${panelAttr}]`)
                ? candidate
                : candidate.closest(`[${panelAttr}]`);
            if (!panelBody) continue;
            if (campaignId && panelBody.dataset.roomId !== campaignId) continue;
            const panel = panelBody.closest("[data-modal-window]") || panelBody;
            if (!panel.hidden) return panel;
        }
        return null;
    }

    function positionModalNearPanel(modalId, resourceType, options = {}) {
        const modal = document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`);
        const panel = resourcePanel(
            resourceType,
            String(options.campaignId || ""),
            String(options.resourceId || ""),
            options.trigger || null,
        );
        if (!modal || !panel) return;

        window.requestAnimationFrame(() => {
            const layer = modal.closest(".game-modal-layer");
            const panelRect = panel.getBoundingClientRect();
            const layerRect = layer?.getBoundingClientRect();
            if (!layerRect) return;
            const margin = 12;
            const x = modalLayout.clamp(
                panelRect.left - layerRect.left - modal.offsetWidth - margin,
                margin,
                Math.max(margin, layerRect.width - modal.offsetWidth - margin),
            );
            const y = modalLayout.clamp(
                panelRect.top - layerRect.top + 10,
                margin,
                Math.max(margin, layerRect.height - modal.offsetHeight - margin),
            );
            setPosition(modal, x, y);
            saveWindowState(modal);
        });
    }

    async function ensureJournalModal(journalId) {
        return modalRemote.ensureJournalModal(journalId);
    }

    async function ensureJournalCreateModal(campaignId, folderId) {
        return modalRemote.ensureJournalCreateModal(campaignId, folderId);
    }

    async function ensureResourcePermissionsModal(resourceType, resourceId) {
        return modalRemote.ensureResourcePermissionsModal(resourceType, resourceId);
    }

    async function ensureModalReady(modalId) {
        if (!modalId) return false;
        if (document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)) return true;

        const remotePatterns = [
            { prefix: "actor-", ensure: ensureActorSheetModal },
            { prefix: "token-", ensure: ensureTokenSheetModal },
            { prefix: "item-", ensure: ensureItemSheetModal },
            { prefix: "journal-", ensure: ensureJournalModal },
            { prefix: "scene-edit-", ensure: ensureSceneEditModal },
        ];

        for (const pattern of remotePatterns) {
            if (modalId.startsWith(pattern.prefix)) {
                const id = modalId.slice(pattern.prefix.length);
                return id ? pattern.ensure(id) : false;
            }
        }

        if (modalId.startsWith("resource-permissions-")) {
            const [, resourceType, resourceId] = modalId.match(/^resource-permissions-([^-]+)-(.+)$/) || [];
            return resourceType && resourceId
                ? ensureResourcePermissionsModal(resourceType, resourceId)
                : false;
        }

        return false;
    }

    function closeModal(modal) {
        modalActions.close(modal);
    }

    function minimizeModal(modal) {
        modalActions.minimize(modal);
    }

    function topVisibleModal() {
        return modalActions.topVisible();
    }

    function toggleMaximizeModal(modal) {
        modalActions.toggleMaximize(modal);
    }

    function detachModal(modal) {
        modalActions.detach(modal);
    }

    document.addEventListener("click", (event) => {
        const panelTabDetach = event.target.closest("[data-gravewright-panel-tab-detach]");

        if (panelTabDetach) {
            modalDocking.detachGravewrightPanel(panelTabDetach.dataset.gravewrightPanelTabDetach);
            return;
        }

        const panelTabClose = event.target.closest("[data-gravewright-panel-tab-close]");

        if (panelTabClose) {
            removeGravewrightPanel(panelTabClose.dataset.gravewrightPanelTabClose);
            return;
        }

        const panelTab = event.target.closest("[data-gravewright-panel-tab]");

        if (panelTab) {
            const panelId = panelTab.dataset.gravewrightPanelTab;
            const panel = document.querySelector(
                `.game-panel[data-modal-id="${cssEscape(panelId)}"]`
            );
            const group = gravewrightPanelGroup(panel?.dataset.panelRoom);

            if (group?.panelIds.includes(panelId)) {
                activateGravewrightPanel(group, panelId);
            }

            return;
        }

        const panelToggle = event.target.closest("[data-panel-toggle]");

        if (panelToggle) {
            const panelId = panelToggle.dataset.panelToggle;
            const panel = document.querySelector(`[data-modal-id="${panelId}"]`);

            if (!panel) {
                return;
            }

            if (isClassicLayout()) {
                openClassicPanel(panelId);
                return;
            }

            toggleGravewrightPanel(panel);

            return;
        }

        const layoutButton = event.target.closest("[data-layout-mode]");

        if (layoutButton) {
            const currentPanel = layoutButton.closest(".game-panel");
            applyLayoutMode(layoutButton.dataset.layoutMode, currentPanel?.dataset.modalId || null, true);
            return;
        }

        const permissionRow = event.target.closest("[data-checkbox-row]");

        if (permissionRow && !event.target.closest("input, button, a, summary")) {
            event.preventDefault();

            const checkbox = permissionRow.querySelector('input[type="checkbox"]');

            if (checkbox && !checkbox.disabled) {
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event("change", { bubbles: true }));
            }

            return;
        }

        const openButton = event.target.closest("[data-modal-open]");

        if (openButton && !event.target.closest("[data-no-modal]")) {
            const modalId = openButton.dataset.modalOpen;
            if (!document.querySelector(`[data-modal-id="${cssEscape(modalId)}"]`)) {
                const directoryMatch = modalId.match(/^(?:actor|item|journal)(?:-folder)?-create-(.+)$/);
                if (directoryMatch) {
                    event.preventDefault();
                    modalRemote.ensureDirectoryDialogs(directoryMatch[1]).then((ready) => {
                        if (!ready) return;
                        openModal(modalId);
                        const createMatch = modalId.match(/^(actor|item)-create-(.+)$/);
                        if (createMatch) positionModalNearPanel(modalId, createMatch[1], {
                            campaignId: createMatch[2], trigger: openButton,
                        });
                    });
                    return;
                }
                const sceneCreateMatch = modalId.match(/^scene(?:-group)?-create-(.+)$/);
                if (sceneCreateMatch) {
                    event.preventDefault();
                    modalRemote.ensureSceneCreateDialogs(sceneCreateMatch[1]).then((ready) => {
                        if (ready) openModal(modalId);
                    });
                    return;
                }
            }
            openModal(modalId);
            const createMatch = modalId.match(/^(actor|item)-create-(.+)$/);
            if (createMatch) {
                positionModalNearPanel(modalId, createMatch[1], {
                    campaignId: createMatch[2],
                    trigger: openButton,
                });
            }
            return;
        }

        const restoreButton = event.target.closest("[data-modal-restore]");

        if (restoreButton) {
            openModal(restoreButton.dataset.modalRestore);
            return;
        }

        const closeButton = event.target.closest("[data-modal-close]");

        if (closeButton) {
            const modal = closeButton.closest("[data-modal-window]");

            if (modal) {
                closeModal(modal);
            }

            return;
        }

        const minimizeButton = event.target.closest("[data-modal-minimize]");

        if (minimizeButton) {
            const modal = minimizeButton.closest("[data-modal-window]");

            if (modal) {
                minimizeModal(modal);
            }

            return;
        }

        const resourcePermissionsButton = event.target.closest("[data-resource-permissions]");

        if (resourcePermissionsButton) {
            const resourceType = resourcePermissionsButton.dataset.resourcePermissions;
            const resourceId = resourcePermissionsButton.dataset.resourceId;

            if (resourceType && resourceId) {
                ensureResourcePermissionsModal(resourceType, resourceId).then((ready) => {
                    if (ready) {
                        const modalId = `resource-permissions-${resourceType}-${resourceId}`;
                        openModal(modalId);
                        positionModalNearPanel(modalId, resourceType, {
                            resourceId,
                            trigger: resourcePermissionsButton,
                        });
                    }
                });
            }

            return;
        }

        const detachButton = event.target.closest("[data-modal-detach]");

        if (detachButton) {
            const modal = detachButton.closest("[data-modal-window]");

            if (modal) {
                if (modalDocking.toggleGravewrightPanelAttachment(modal)) return;
                detachModal(modal);
            }

            return;
        }

        const popoutButton = event.target.closest("[data-modal-popout]");

        if (popoutButton) {
            const url = popoutButton.dataset.popoutUrl;

            if (url) {
                window.open(url, "_blank", "width=520,height=680,resizable=yes,scrollbars=yes");
            }

            const modal = popoutButton.closest("[data-modal-window]");

            if (modal) {
                minimizeModal(modal);
            }
        }
    });

    document.addEventListener("input", (event) => {
        const slider = event.target.closest("[data-grid-opacity-input]");
        if (!slider) return;
        modalForms.syncGridOpacityOutput(slider);
    });

    document.addEventListener("change", (event) => {
        const input = event.target.closest("[data-warn-on-change]");
        if (!input) return;
        modalForms.syncWarnOnChange(input);
    });

    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-scene-ajax-form]");

        if (!form) {
            return;
        }



        event.preventDefault();
        const submitter = event.submitter;

        if (form.dataset.confirm && !(await window.GravewrightCore.dialog.confirm(form.dataset.confirm))) {
            return;
        }

        if (!(await modalForms.confirmWarnOnChange(form))) {
            return;
        }

        modalForms.submitSceneAjaxForm(form, submitter);
    });

    document.addEventListener("submit", (event) => {
        const form = event.target.closest("[data-panel-ajax-form]");

        if (!form) {
            return;
        }

        event.preventDefault();
        modalForms.submitPanelAjaxForm(form, event.submitter);
    });

    document.addEventListener("submit", async (event) => {
        const form = event.target.closest("[data-table-settings-form]");
        if (!form) return;

        event.preventDefault();
        modalForms.submitTableSettingsForm(form, event.submitter);
    });


    document.addEventListener("submit", async (event) => {
        const form = event.target.closest(".resource-permissions-form");
        if (!form) return;
        event.preventDefault();
        modalForms.submitResourcePermissionsForm(form, event.submitter);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        const modal = topVisibleModal();

        if (!modal) {
            return;
        }

        event.preventDefault();
        closeModal(modal);
    });






    document.addEventListener("pointerdown", (event) => {
        if (event.target.closest(
            "button, a, input, select, textarea, summary, [role=\"button\"], "
            + "[data-journal-select], [data-actor-open], [data-item-open], [data-journal-create-open]"
        )) {
            return;
        }

        const modal = event.target.closest("[data-modal-window]");

        if (modal) {
            bringToFront(modal);
        }
    });

    document.querySelectorAll('input[name="selected-room"]').forEach((radio) => {
        radio.addEventListener("change", () => {
            syncActiveRoomUi(radio.value);
        });
    });

    modalLayout.startResizeObserver();

    document.querySelectorAll("[data-modal-window]").forEach((modal) => {
        observeModal(modal);
    });

    modalForms.applyDotColors(document);
    modalForms.dismissAutoNotices();

    const detachedModalId = document.body.dataset.detachedModal || "";
    const initialModalId = document.body.dataset.openModal || "";
    let savedLayout = DEFAULT_LAYOUT;
    try {
        savedLayout = document.body.dataset.gameLayout
            || window.localStorage.getItem(LAYOUT_STORAGE_KEY)
            || DEFAULT_LAYOUT;
    } catch {
        savedLayout = DEFAULT_LAYOUT;
    }

    if (detachedModalId) {
        savedLayout = DEFAULT_LAYOUT;
    }

    applyLayoutMode(savedLayout);
    syncActiveRoomUi(getActiveRoomId());

    if (detachedModalId) {
        ensureModalReady(detachedModalId).then((ready) => {
            if (ready) openModal(detachedModalId);
        });
    } else if (initialModalId) {
        openModal(initialModalId);
        try {
            const url = new URL(window.location.href);
            url.searchParams.delete("open_modal");
            window.history.replaceState(null, "", url.toString());
        } catch {  }
    }

    document.addEventListener("vtt:open-journal", async (e) => {
        const journalId = e.detail?.journalId;
        if (!journalId) return;
        if (await ensureJournalModal(journalId)) {
            document.querySelectorAll(".journal-card.is-active").forEach((card) => card.classList.remove("is-active"));
            document.querySelectorAll(`.journal-card[data-journal-id="${cssEscape(journalId)}"]`)
                .forEach((card) => card.classList.add("is-active"));
            openModal(`journal-${journalId}`);
            if (e.detail?.edit) {
                window.GravewrightJournalsInternals?.openJournalEditor?.(
                    document.querySelector(`[data-modal-id="journal-${cssEscape(journalId)}"]`),
                );
            }
        }
    });

    async function ensureActorSheetModal(actorId) {
        return modalRemote.ensureActorSheetModal(actorId);
    }

    function uniqueActiveSceneTokenForActor(actorId) {
        const canvas = window.GravewrightMap?.activeCanvas?.()
            || document.querySelector(".room-workspace.is-active [data-map-canvas]");
        if (!canvas || !actorId) return null;
        const store = window.GravewrightMap?.tokenStoreFor?.(canvas);
        if (!store || typeof store.values !== "function") return null;
        const matches = Array.from(store.values()).filter(
            (token) => String(token?.actor_id || "") === String(actorId),
        );
        return matches.length === 1 ? matches[0] : null;
    }

    document.addEventListener("vtt:open-actor-sheet", async (e) => {
        const actorId = e.detail?.actorId;
        if (!actorId) return;
        const token = uniqueActiveSceneTokenForActor(actorId);
        const tokenId = token?.token_id || token?.id || "";
        if (tokenId) {
            if (await ensureTokenSheetModal(tokenId)) openModal(`token-${tokenId}`);
            return;
        }
        if (await ensureActorSheetModal(actorId)) {
            openModal(`actor-${actorId}`);
        }
    });

    document.addEventListener("vtt:open-compendium-entry", async (e) => {
        const { campaignId, packageId, packId, entryId } = e.detail ?? {};
        if (!campaignId || !packageId || !packId || !entryId) return;
        if (await modalRemote.ensureCompendiumEntryModal({ campaignId, packageId, packId, entryId })) {
            openModal(`compendium-${packageId}-${packId}-${entryId}`);
        }
    });

    async function ensureTokenSheetModal(tokenId) {
        return modalRemote.ensureTokenSheetModal(tokenId);
    }

    document.addEventListener("vtt:open-token-sheet", async (e) => {
        const tokenId = e.detail?.tokenId;
        if (!tokenId) return;
        if (await ensureTokenSheetModal(tokenId)) {
            openModal(`token-${tokenId}`);
        }
    });

    async function ensureItemSheetModal(itemId) {
        return modalRemote.ensureItemSheetModal(itemId);
    }

    document.addEventListener("vtt:open-item-sheet", async (e) => {
        const itemId = e.detail?.itemId;
        if (!itemId) return;
        if (await ensureItemSheetModal(itemId)) {
            openModal(`item-${itemId}`);
        }
    });

    async function ensureSceneEditModal(sceneId) {
        return modalRemote.ensureSceneEditModal(sceneId);
    }

    document.addEventListener("click", async (event) => {
        const trigger = event.target.closest("[data-scene-edit]");
        if (!trigger) return;
        event.preventDefault();
        const sceneId = trigger.dataset.sceneEdit;
        if (!sceneId) return;
        if (await ensureSceneEditModal(sceneId)) {
            openModal(`scene-edit-${sceneId}`);
        }
    });

    document.addEventListener("vtt:open-journal-create", async (e) => {
        const { campaignId, folderId } = e.detail ?? {};
        if (!campaignId) return;
        if (await ensureJournalCreateModal(campaignId, folderId)) {
            const modalId = `journal-create-${campaignId}`;
            openModal(modalId);
            positionModalNearPanel(modalId, "journal", { campaignId });
        }
    });

    Object.assign(FI, {
        bringToFront,
        close: closeModal,
        cssEscape,
        defaultY: DEFAULT_Y,
        getPosition,
        isClassicPanel,
        minimize: minimizeModal,
        open: openModal,
        positionNearPanel: positionModalNearPanel,
        saveWindowState,
        setPosition,
        toggleMaximize: toggleMaximizeModal,
    });
})();
