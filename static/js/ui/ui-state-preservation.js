(() => {
    "use strict";
    const storageKey = "gravewright.ui.pending-reload-state.v1";
    const tabAttributes = ["data-tab", "data-journal-diary-tab", "data-quest-tab", "data-sound-view", "data-library-view", "data-settings-section-tab", "data-journal-kind-filter"];

    function capture(reason = "runtime-change") {
        const selector = tabAttributes.map((attribute) => `[${attribute}].is-active,[${attribute}][aria-selected="true"]`).join(",");
        const state = {
            reason,
            roomId: document.querySelector('input[name="selected-room"]:checked')?.value || "",
            openModals: [...document.querySelectorAll("[data-modal-id]:not([hidden])")].map((node) => node.dataset.modalId).filter(Boolean),
            activePanels: [...document.querySelectorAll('[data-panel-toggle][aria-pressed="true"]')].map((node) => node.dataset.panelToggle).filter(Boolean),
            tabs: [...document.querySelectorAll(selector)].map((node) => {
                const attribute = tabAttributes.find((candidate) => node.hasAttribute(candidate));
                return { owner: node.closest("[data-modal-id]")?.dataset.modalId || "", attribute, value: node.getAttribute(attribute) };
            }).filter((entry) => entry.attribute && entry.value !== null),
            scroll: [...document.querySelectorAll("[data-modal-id]:not([hidden])")].map((modal) => ({
                owner: modal.dataset.modalId || "", top: modal.querySelector(".game-modal-body")?.scrollTop || 0,
            })).filter((entry) => entry.owner && entry.top),
        };
        sessionStorage.setItem(storageKey, JSON.stringify(state));
        return state;
    }

    function reload(reason) {
        try { capture(reason); } catch { /* storage may be unavailable */ }
        window.location.reload();
    }

    function restore() {
        let state;
        try { state = JSON.parse(sessionStorage.getItem(storageKey) || "null"); sessionStorage.removeItem(storageKey); }
        catch { return; }
        if (!state) return;
        if (state.roomId) {
            const room = document.querySelector(`input[name="selected-room"][value="${CSS.escape(state.roomId)}"]`);
            if (room && !room.checked) room.click();
        }
        (state.openModals || []).forEach((id) => window.GravewrightModals?.open?.(id));
        (state.activePanels || []).forEach((id) => {
            const button = document.querySelector(`[data-panel-toggle="${CSS.escape(id)}"]`);
            if (button?.getAttribute("aria-pressed") !== "true") button?.click();
        });
        (state.tabs || []).forEach(({ owner, attribute, value }) => {
            if (!tabAttributes.includes(attribute)) return;
            const root = owner ? document.querySelector(`[data-modal-id="${CSS.escape(owner)}"]`) : document;
            root?.querySelector(`[${attribute}="${CSS.escape(value)}"]`)?.click();
        });
        requestAnimationFrame(() => (state.scroll || []).forEach(({ owner, top }) => {
            const body = document.querySelector(`[data-modal-id="${CSS.escape(owner)}"] .game-modal-body`);
            if (body) body.scrollTop = top;
        }));
    }

    window.GravewrightUiState = { capture, reload, restore };
    window.addEventListener("load", () => setTimeout(restore, 0), { once: true });
})();
