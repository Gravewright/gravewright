/** Emission is visual and follows the source; it never creates persistent light rows. */
export function effectLights(state, cell, width, height) {
    return [...state.lights, ...[...state.particles.map(e => ({ ...e, reach: e.scale * cell })), ...state.shaders.map(e => ({ ...e, reach: e.radius > 0 ? e.radius * cell : Math.hypot(width, height) }))].filter(e => e.enabled && (e.light_emission ?? 0) > 0).map(e => ({ id: `emission:${e.id}`, x: e.x, y: e.y, color: e.color, intensity: e.light_emission, bright_radius: e.reach / cell * .15, dim_radius: e.reach / cell, enabled: true, animation: 'none', angle: 360, rotation: 0 }))];
}
