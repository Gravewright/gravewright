export const PRESENTATION_PROFILES = Object.freeze({
    scope: "player",
    default: "performance",
    profiles: Object.freeze({
        performance: Object.freeze({ backdropBlur: false, motion: "none", postProcessing: false, softShadows: false, particleDensity: .25, resolutionScale: .75 }),
        balanced: Object.freeze({ backdropBlur: true, motion: "reduced", postProcessing: false, softShadows: true, particleDensity: .5, resolutionScale: 1 }),
        quality: Object.freeze({ backdropBlur: true, motion: "full", postProcessing: true, softShadows: true, particleDensity: 1, resolutionScale: 1 }),
    }),
});
