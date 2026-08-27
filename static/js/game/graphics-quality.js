(() => {
    const STORAGE_KEY = "gravewright:graphics-quality";
    const PROFILES = Object.freeze({
        low: Object.freeze({
            id: "low", resolutionScale: 0.75, maxDpr: 1,
            fogScale: 0.5, lightingScale: 0.5, lightBufferScale: 0.35,
            textureCacheBytes: 64 * 1024 * 1024, textureCacheEntries: 96,
            tileBlobCacheBytes: 192 * 1024 * 1024, tileBlobCacheEntries: 1536,
            textureConcurrency: 2, maxShaders: 2, maxParticles: 250,
            animationFps: 24, expensiveFilters: false,
        }),
        medium: Object.freeze({
            id: "medium", resolutionScale: 1, maxDpr: 1.25,
            fogScale: 0.75, lightingScale: 0.75, lightBufferScale: 0.5,
            textureCacheBytes: 128 * 1024 * 1024, textureCacheEntries: 144,
            tileBlobCacheBytes: 384 * 1024 * 1024, tileBlobCacheEntries: 3072,
            textureConcurrency: 3, maxShaders: 4, maxParticles: 600,
            animationFps: 40, expensiveFilters: true,
        }),
        high: Object.freeze({
            id: "high", resolutionScale: 1, maxDpr: 2,
            fogScale: 1, lightingScale: 1, lightBufferScale: 0.5,
            textureCacheBytes: 192 * 1024 * 1024, textureCacheEntries: 192,
            tileBlobCacheBytes: 512 * 1024 * 1024, tileBlobCacheEntries: 4096,
            textureConcurrency: 5, maxShaders: 8, maxParticles: 1200,
            animationFps: 60, expensiveFilters: true,
        }),
    });

    function detectedProfile() {
        const memory = Number(navigator.deviceMemory || 0);
        const cores = Number(navigator.hardwareConcurrency || 0);
        if ((memory && memory <= 4) || (cores && cores <= 4)) return "low";
        if ((memory && memory <= 8) || (cores && cores <= 8)) return "medium";
        return "high";
    }

    function storedChoice() {
        try { return localStorage.getItem(STORAGE_KEY) || "auto"; } catch { return "auto"; }
    }

    let choice = ["auto", ...Object.keys(PROFILES)].includes(storedChoice()) ? storedChoice() : "auto";
    let effective = choice === "auto" ? detectedProfile() : choice;

    function config() { return PROFILES[effective] || PROFILES.medium; }
    function renderResolution() {
        const profile = config();
        return Math.max(0.5, Math.min(profile.maxDpr, (window.devicePixelRatio || 1) * profile.resolutionScale));
    }
    function paint() {
        document.documentElement.dataset.graphicsQuality = effective;
        document.documentElement.dataset.graphicsQualityChoice = choice;
        document.querySelectorAll("select[data-graphics-quality]").forEach((select) => { select.value = choice; });
    }
    function apply(next) {
        const normalized = ["auto", ...Object.keys(PROFILES)].includes(next) ? next : "auto";
        choice = normalized;
        effective = choice === "auto" ? detectedProfile() : choice;
        try { localStorage.setItem(STORAGE_KEY, choice); } catch { }
        paint();
        document.dispatchEvent(new CustomEvent("vtt:graphics-quality-changed", {
            detail: { choice, effective, config: config() },
        }));
        window.GravewrightMap?.redraw?.();
    }

    document.addEventListener("change", (event) => {
        const select = event.target.closest?.("select[data-graphics-quality]");
        if (select) apply(select.value);
    });
    document.addEventListener("DOMContentLoaded", paint, { once: true });
    paint();

    window.GravewrightGraphicsQuality = Object.freeze({
        apply, choice: () => choice, current: () => effective, config, renderResolution,
    });
})();
