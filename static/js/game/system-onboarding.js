(() => {
    const STORAGE_PREFIX = "gravewright.systemOnboarding.seen";

    function storageKey(modal) {
        const userId = document.body.dataset.currentUserId || "anonymous";
        const roomId = modal.dataset.roomId || "unknown";
        return `${STORAGE_PREFIX}.${userId}.${roomId}`;
    }

    function hasSeen(modal) {
        try {
            return window.localStorage.getItem(storageKey(modal)) === "1";
        } catch {
            return false;
        }
    }

    function markSeen(modal) {
        try {
            window.localStorage.setItem(storageKey(modal), "1");
        } catch {
            
        }
    }

    function activeRoomId() {
        return document.querySelector('input[name="selected-room"]:checked')?.value || "";
    }

    function showInitialPrompt() {
        const roomId = activeRoomId();
        // Only prompt for the active room. No fallback to "any" onboarding modal:
        // a GM of a systemless table must not get the prompt while viewing a
        // different table where they are only a player.
        const modal = Array.from(document.querySelectorAll("[data-system-onboarding-modal]"))
            .find((candidate) => candidate.dataset.roomId === roomId);

        if (!modal || hasSeen(modal)) return;

        markSeen(modal);
        window.GravewrightModals?.open?.(modal.dataset.modalId || "");
    }

    document.addEventListener("vtt:game-ready", showInitialPrompt, { once: true });

    document.addEventListener("submit", (event) => {
        const form = event.target.closest("[data-system-onboarding-form]");
        if (!form) return;
        const modal = form.closest("[data-system-onboarding-modal]");
        if (modal) markSeen(modal);
    });
})();
