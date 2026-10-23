/** Project cell coordinates projected into the unchanged native scene contract. */
import { wallSegments } from './model.js';
import { effectLights } from '../builder-catalog.js';
import { nativeWallProperties } from './wall-properties.js';
import { torchComponentState } from './torch-model.js';

export function nativeEffectState(document) {
    const cell = document.cellSize, width = document.sceneGeometry?.width || document.columns * cell,
        height = document.sceneGeometry?.height || document.rows * cell;
    const rangeScale = (document.sceneGeometry?.gridSize || cell) * (document.sceneGeometry?.imageScale ?? 1) / cell;
    const shown = item => document.layers?.find(layer => layer.id === item.layerId)?.visible !== false;
    const point = item => ({ ...item, x: item.x * cell, y: item.y * cell });
    const doors = (document.doors || []).filter(shown), geometry = { ...document, doors };
    const walls = (document.walls || []).filter(shown).flatMap(wall => wallSegments(geometry, wall).map(segment => ({
        ...segment, ...nativeWallProperties(wall), kind: 'wall' })));
    walls.push(...doors.map(door => ({ x1: door.x1, y1: door.y1, x2: door.x2, y2: door.y2,
        ...nativeWallProperties(door), kind: 'door', door_state: door.state })));
    const lights = (document.lights || []).filter(shown).map(item => torchComponentState(document, 'lights', item))
        .filter(light => light.enabled && light.intensity > 0).map(light => ({
        ...point(light), bright_radius: light.brightRadius * rangeScale, dim_radius: light.dimRadius * rangeScale,
    }));
    const particles = [], shaders = [], invisible = { lights: [], particles: [], shaders: [] };
    for (const [kind, rows] of [['particles', particles], ['shaders', shaders]]) {
        for (const original of (document[kind] || []).filter(shown).map(item => torchComponentState(document, kind, item))) {
            if (!original.enabled) continue;
            const record = point(original);
            if (kind === 'particles') record.scale *= rangeScale;
            else record.radius *= rangeScale;
            // The native wrapper always applies opacity; custom shader code
            // decides whether to use intensity, so zero intensity is drawable.
            const visible = kind === 'particles' ? record.density > 0 : record.opacity > 0;
            if (visible) rows.push(record);
            else if (record.light_emission > 0) {
                // Invisible sources can still emit light. Keep that native
                // emission without running a shader/particle animation loop.
                invisible[kind].push(record);
            }
        }
    }
    lights.push(...effectLights(invisible, cell, width, height));
    return { cell, width, height, state: {
        sceneId: 'map-builder-preview', images: [], cards: [], zones: [], vision: [], spatialSounds: [],
        drawings: { rows: [] }, fog: { enabled: false, ops: [] },
        lighting: { mode: 'none', darkness: 0, lights_out: false }, lights, particles, shaders,
        walls: walls.map(wall => ({ ...wall, x1: wall.x1 * cell, y1: wall.y1 * cell, x2: wall.x2 * cell, y2: wall.y2 * cell })),
    } };
}
export function hasNativeEffects(projected) {
    return ['lights', 'particles', 'shaders'].some(kind => projected.state[kind].length > 0);
}
