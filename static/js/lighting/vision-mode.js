(() => {












    const MODES = new Set(["classic", "cinematic"]);
    const DEFAULT_MODE = "cinematic";
    const STORAGE_KEY = "gravewright:vision-mode";

    function normalize(value) {
        const mode = String(value || "").trim().toLowerCase();
        return MODES.has(mode) ? mode : DEFAULT_MODE;
    }




    function stored() {
        try {
            return window.localStorage.getItem(STORAGE_KEY);
        } catch {
            return null;
        }
    }

    let current = normalize(document.body?.dataset?.visionMode || stored());

    function paintButtons() {
        document.querySelectorAll("[data-vision-mode-choice]").forEach((button) => {
            const selected = button.dataset.visionModeChoice === current;
            button.setAttribute("aria-pressed", selected ? "true" : "false");
            button.classList.toggle("is-active", selected);
        });
    }

    async function persist(mode) {
        try {
            await fetch("/game/preferences/vision", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    Accept: "application/json",
                },
                body: new URLSearchParams({
                    csrf_token: document.body?.dataset?.presenceCsrfToken || "",
                    vision_mode: mode,
                }),
                credentials: "same-origin",
            });
        } catch {


        }
    }

    function apply(value, { persist: shouldPersist = false } = {}) {
        const mode = normalize(value);
        const changed = mode !== current;
        current = mode;
        if (document.body) document.body.dataset.visionMode = mode;
        try {
            window.localStorage.setItem(STORAGE_KEY, mode);
        } catch {

        }
        paintButtons();
        if (shouldPersist) void persist(mode);
        if (!changed) return mode;




        window.GravewrightLighting?.invalidateAll?.();
        window.GravewrightMap?.redraw?.();
        return mode;
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-vision-mode-choice]");
        if (!button) return;
        event.preventDefault();
        apply(button.dataset.visionModeChoice, { persist: true });
    });

    document.addEventListener("DOMContentLoaded", () => apply(current), { once: true });
    paintButtons();

    window.GravewrightVisionMode = {
        DEFAULT_MODE,
        current: () => current,
        isClassic: () => current === "classic",
        apply,
    };
})();
