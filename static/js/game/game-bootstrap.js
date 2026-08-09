(() => {
    async function bootstrap() {
        const root = document.querySelector("[data-game-root]") || document.querySelector(".game-page");
        const modalLayer = document.querySelector(".game-modal-layer");

        if (!root) {
            console.warn("Gravewright game bootstrap: [data-game-root] not found");
        }
        if (!modalLayer) {
            console.warn("Gravewright game bootstrap: .game-modal-layer not found");
        }

        function sdkPackages() {
            const el = document.getElementById("gravewright-sdk-packages");
            if (!el) return [];
            try {
                const parsed = JSON.parse(el.textContent || "[]");
                return Array.isArray(parsed) ? parsed : [];
            } catch (_err) {
                return [];
            }
        }



        const detail = {
            root,
            modalLayer,
            packages: sdkPackages(),
        };

        document.dispatchEvent(new CustomEvent("vtt:game-ready", { detail }));
    }

    window.GravewrightGameBootstrap = { bootstrap };
})();
