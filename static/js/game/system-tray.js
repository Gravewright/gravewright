(() => {
    function activeRoomId() {
        return document.querySelector('input[name="selected-room"]:checked')?.value || "";
    }

    function syncRoom() {
        const roomId = activeRoomId();
        document.querySelectorAll("[data-system-tray-room]").forEach(panel => {
            panel.hidden = panel.dataset.systemTrayRoom !== roomId;
        });
    }

    function closeUsers() {
        const panel = document.querySelector('[data-system-tray-panel="users"]');
        const toggle = document.querySelector('[data-system-tray-toggle="users"]');
        if (panel) panel.hidden = true;
        toggle?.setAttribute("aria-expanded", "false");
    }

    document.addEventListener("click", event => {
        const usersToggle = event.target.closest?.('[data-system-tray-toggle="users"]');
        if (usersToggle) {
            const panel = document.querySelector('[data-system-tray-panel="users"]');
            const sound = document.querySelector("[data-personal-audio-popover]");
            const soundToggle = document.querySelector("[data-personal-audio-toggle]");
            if (!panel) return;
            const open = panel.hidden;
            panel.hidden = !open;
            usersToggle.setAttribute("aria-expanded", String(open));
            if (sound) sound.hidden = true;
            soundToggle?.setAttribute("aria-expanded", "false");
            syncRoom();
            return;
        }
        if (event.target.closest?.("[data-personal-audio-toggle]")) { closeUsers(); return; }
        if (event.target.closest?.("[data-system-tray-close]")) { closeUsers(); return; }
        if (!event.target.closest?.("[data-system-tray]")) closeUsers();
    }, true);

    document.addEventListener("change", event => {
        if (event.target.matches?.('input[name="selected-room"]')) syncRoom();
        const color = event.target.closest?.("[data-player-identity-color]");
        if (color?.value) paintIdentity(color.dataset.playerIdentityColor, color.value);
    });
    function paintIdentity(userId, color) {
        if (!userId || !/^#[0-9a-f]{6}$/i.test(String(color || ""))) return;
        document.querySelectorAll(`[data-player-identity-color="${CSS.escape(userId)}"]`).forEach(node => {
            if (node instanceof HTMLInputElement) node.value = color;
            else node.style.setProperty("--player-identity-color", color);
        });
    }
    document.addEventListener("vtt:transport-event", event => {
        if (event.detail?.event !== "user.presentation.changed") return;
        paintIdentity(String(event.detail.payload?.user_id || ""), event.detail.payload?.color);
    });
    document.addEventListener("DOMContentLoaded", syncRoom, { once: true });
})();
