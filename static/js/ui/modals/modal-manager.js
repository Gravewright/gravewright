(() => {
    const FI = (window.GravewrightModalInternals = window.GravewrightModalInternals || {});
    const DEFAULT_X = 22;
    const DEFAULT_Y = 22;
    const PANEL_DEFAULT_WIDTH = 340;
    const DOCK_CLEARANCE = 64; 
    const LAYOUT_STORAGE_KEY = "gravewright.game.layout";
    const DEFAULT_LAYOUT = "gravewright";
    const CLASSIC_LAYOUT = "classic";
    const MAXIMIZED_MARGIN = 14;
    const AUTO_FIT_PADDING = 10;
    const AUTO_FIT_MARGIN = 10;
    const MIN_WINDOW_WIDTH = 260;
    const MIN_WINDOW_HEIGHT = 180;

    const DEFAULT_FIT_HEIGHT = 520;
    const modalLayout = window.GravewrightModalLayout.createModalLayout({
        autoFitMargin: AUTO_FIT_MARGIN,
        autoFitPadding: AUTO_FIT_PADDING,
        cssEscape,
        defaultFitHeight: DEFAULT_FIT_HEIGHT,
        defaultX: DEFAULT_X,
        defaultY: DEFAULT_Y,
        isClassicPanel,
        isGravewrightPanel,
        minWindowHeight: MIN_WINDOW_HEIGHT,
        minWindowWidth: MIN_WINDOW_WIDTH,
        windowStoragePrefix: "gravewright.game.window.",
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
            openModal(openButton.dataset.modalOpen);
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
                        openModal(`resource-permissions-${resourceType}-${resourceId}`);
                    }
                });
            }

            return;
        }

        const detachButton = event.target.closest("[data-modal-detach]");

        if (detachButton) {
            const modal = detachButton.closest("[data-modal-window]");

            if (modal) {
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

    document.addEventListener("submit", (event) => {
        const form = event.target.closest("[data-scene-ajax-form]");

        if (!form) {
            return;
        }

        if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
            event.preventDefault();
            return;
        }

        if (!modalForms.confirmWarnOnChange(form)) {
            event.preventDefault();
            return;
        }

        event.preventDefault();
        modalForms.submitSceneAjaxForm(form, event.submitter);
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
            openModal(`journal-${journalId}`);
        }
    });

    async function ensureActorSheetModal(actorId) {
        return modalRemote.ensureActorSheetModal(actorId);
    }

    document.addEventListener("vtt:open-actor-sheet", async (e) => {
        const actorId = e.detail?.actorId;
        if (!actorId) return;
        if (await ensureActorSheetModal(actorId)) {
            openModal(`actor-${actorId}`);
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
            openModal(`journal-create-${campaignId}`);
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
        saveWindowState,
        setPosition,
        toggleMaximize: toggleMaximizeModal,
    });
})();
