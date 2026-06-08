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

        await window.GravewrightModules?.init?.();

        const detail = {
            root,
            modalLayer,
            modules: window.GravewrightModules?.list?.() || [],
        };

        document.dispatchEvent(new CustomEvent("vtt:game-ready", { detail }));
    }

    window.GravewrightGameBootstrap = { bootstrap };
})();
