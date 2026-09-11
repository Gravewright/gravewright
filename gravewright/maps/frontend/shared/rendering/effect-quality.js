/** Local rendering budgets; never change persisted scene data or visibility geometry. */
export const EFFECT_QUALITY = {
    performance: { fps: 15, lightFps: 8, particles: .25, particleLimit: 300, lightMap: 256, shaderDetail: 1, shaders: true },
    balanced: { fps: 30, lightFps: 15, particles: .5, particleLimit: 600, lightMap: 512, shaderDetail: 3, shaders: true },
    quality: { fps: 60, lightFps: 30, particles: 1, particleLimit: 1200, lightMap: 1024, shaderDetail: 5, shaders: true },
};
export function effectQuality(profile) { return EFFECT_QUALITY[profile]; }
