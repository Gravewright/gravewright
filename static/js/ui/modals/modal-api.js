(() => {
    const FI = window.GravewrightModalInternals || {};

    function modalById(modalOrId) {
        if (modalOrId instanceof Element) return modalOrId;
        if (!modalOrId) return null;
        return document.querySelector(`[data-modal-id="${FI.cssEscape?.(modalOrId) || modalOrId}"]`);
    }

    window.GravewrightModals = {
        open(modalId) {
            FI.open?.(modalId);
        },
        close(modalOrId) {
            const modal = modalById(modalOrId);
            if (modal) FI.close?.(modal);
        },
        focus(modalOrId) {
            const modal = modalById(modalOrId);
            if (modal) FI.bringToFront?.(modal);
        },
        minimize(modalOrId) {
            const modal = modalById(modalOrId);
            if (modal) FI.minimize?.(modal);
        },
        toggleMaximize(modalOrId) {
            const modal = modalById(modalOrId);
            if (modal) FI.toggleMaximize?.(modal);
        },
    };
})();
