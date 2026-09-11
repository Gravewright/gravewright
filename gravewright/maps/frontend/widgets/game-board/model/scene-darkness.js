/** The switch overrides the configured darkness without discarding it. */
export function sceneDarkness(lighting) {
    if (lighting.mode !== 'dynamic' || lighting.lights_out === false)
        return 0;
    const value = lighting.effective_darkness ?? lighting.darkness;
    return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
}
