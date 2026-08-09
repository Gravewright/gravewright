(() => {










    const STORAGE_KEY = "gravewright:shaders-enabled";
    let enabled = read();

    function read() {
        try {
            return window.localStorage.getItem(STORAGE_KEY) !== "off";
        } catch {
            return true;
        }
    }

    function paintButtons() {
        document.querySelectorAll("[data-shader-toggle]").forEach((button) => {
            button.setAttribute("aria-pressed", enabled ? "true" : "false");
            button.classList.toggle("is-active", enabled);
        });
    }

    function set(next) {
        const value = Boolean(next);
        if (value === enabled) return enabled;
        enabled = value;
        try {
            window.localStorage.setItem(STORAGE_KEY, enabled ? "on" : "off");
        } catch {


        }
        paintButtons();


        document.dispatchEvent(new CustomEvent("vtt:shaders-toggled", { detail: { enabled } }));
        return enabled;
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest?.("[data-shader-toggle]");
        if (!button) return;
        event.preventDefault();
        set(!enabled);
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", paintButtons);
    } else {
        paintButtons();
    }

    window.GravewrightShaderPreference = {
        enabled: () => enabled,
        set,
        toggle: () => set(!enabled),
    };
})();
