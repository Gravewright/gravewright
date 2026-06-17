(() => {
    function start() {
        window.GravewrightGameBootstrap?.bootstrap?.();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
