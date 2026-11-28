import { VisibilityJobs } from './visibility-jobs.js';

/** World radius a light reaches; an unlimited light covers the whole scene. */
export function lightRadius(light, cell, width, height) {
    return light.dim_radius === 0 ? Math.hypot(width, height) * 2 : Math.max(light.dim_radius, light.bright_radius) * cell;
}

/** Light occluders, expressed with the field names the visibility polygon reads. */
export function lightWalls(walls) {
    return walls.filter(w => w.blocks_light !== 0 && w.light_behavior !== 'pass')
        .map(w => ({ ...w, blocks_sight: w.blocks_light, vision_behavior: w.light_behavior }));
}

const geometryOf = (light, radius) => JSON.stringify([light.x, light.y, radius, light.elevation ?? 0,
    light.angle ?? 360, light.rotation ?? 0]);

/** Walls present in only one of two snapshots, as bounding boxes. */
function changedWalls(previous, next) {
    const counts = new Map();
    for (const key of previous) counts.set(key, (counts.get(key) ?? 0) + 1);
    const changed = [];
    for (const [index, key] of next.entries()) {
        const count = counts.get(key) ?? 0;
        if (count > 0) counts.set(key, count - 1);
        else changed.push(index);
    }
    return { added: changed, removed: [...counts].filter(([, count]) => count > 0).map(([key]) => key) };
}
const box = w => [Math.min(w.x1, w.x2), Math.min(w.y1, w.y2), Math.max(w.x1, w.x2), Math.max(w.y1, w.y2)];
// visibilityPolygon ignores every wall outside this square, so a wall change
// outside it cannot alter the polygon.
const reaches = (entry, [left, top, right, bottom]) => right >= entry.x - entry.radius && left <= entry.x + entry.radius
    && bottom >= entry.y - entry.radius && top <= entry.y + entry.radius;

/**
 * Per-light visibility polygons for one mounted scene.
 *
 * A polygon is reused while its light keeps the same position, reach and cone,
 * and no wall inside its reach changes. Misses go to the shared visibility
 * worker when the scene has enough walls for it; meanwhile a light keeps its
 * previous polygon (translated if the light moved), so a door or a drag never
 * blanks the light, and a light that never had one appears when it is ready.
 */
export class LightPolygons {
    #entries = new Map();
    #walls;
    #wallKeys = [];
    #jobs;
    #createJobs;
    #onUpdate;
    #lights = [];
    #request = 0;
    #pending = false;
    #updating = false;
    #closed = false;
    calculated = 0;
    constructor({ onUpdate, createJobs = walls => new VisibilityJobs(walls) } = {}) {
        this.#onUpdate = onUpdate;
        this.#createJobs = createJobs;
    }
    /** True while a worker result for the current lights is outstanding. */
    get pending() { return this.#pending; }
    /** Returns `{ light, radius, polygon }` rows for every enabled light, in order. */
    update(lights, walls, cell, width, height) {
        if (this.#closed) return [];
        if (walls !== this.#walls) this.#setWalls(walls);
        const sources = [], wanted = new Set();
        this.#lights = [];
        for (const light of lights) {
            // A switched-off light keeps its cached polygon for when it is switched on again.
            wanted.add(light.id);
            if (!light.enabled) continue;
            const radius = lightRadius(light, cell, width, height);
            if (!(radius > 0)) continue;
            const geometry = geometryOf(light, radius);
            this.#lights.push({ light, radius, geometry });
            const entry = this.#entries.get(light.id);
            if (entry?.valid && entry.geometry === geometry) continue;
            sources.push({ id: light.id, geometry, x: light.x, y: light.y, radius, elevation: light.elevation ?? 0,
                angle: light.angle ?? 360, rotation: light.rotation ?? 0 });
        }
        for (const id of this.#entries.keys()) if (!wanted.has(id)) this.#entries.delete(id);
        const request = ++this.#request;
        this.#pending = sources.length > 0;
        if (sources.length) {
            this.#jobs ??= this.#createJobs(this.#walls);
            this.#updating = true;
            try {
                this.#jobs.request(sources.map(({ x, y, radius, elevation, angle, rotation }) =>
                    ({ x, y, radius, elevation, angle, rotation })), 0, polygons => this.#store(request, sources, polygons));
            } finally { this.#updating = false; }
        }
        return this.rows();
    }
    #store(request, sources, polygons) {
        if (this.#closed) return;
        this.calculated += sources.length;
        sources.forEach((source, index) => {
            const polygon = polygons[index];
            if (polygon) this.#entries.set(source.id, { geometry: source.geometry, x: source.x, y: source.y,
                radius: source.radius, polygon, valid: true });
        });
        // An older request that was already running still answers with walls
        // that are current (a wall change revokes it); only the newest request
        // carries every miss of the current lights.
        if (request === this.#request) this.#pending = false;
        if (!this.#updating) this.#onUpdate?.(this.rows());
    }
    #setWalls(walls) {
        const keys = walls.map(wall => JSON.stringify(wall));
        if (this.#walls !== undefined) {
            const { added, removed } = changedWalls(this.#wallKeys, keys);
            const boxes = [...added.map(index => box(walls[index])), ...removed.map(key => box(JSON.parse(key)))];
            if (boxes.length) for (const entry of this.#entries.values())
                if (entry.valid && boxes.some(bounds => reaches(entry, bounds))) entry.valid = false;
        }
        this.#walls = walls;
        this.#wallKeys = keys;
        this.#jobs?.setWalls(walls);
    }
    rows() {
        const rows = [];
        for (const { light, radius, geometry } of this.#lights) {
            const entry = this.#entries.get(light.id);
            if (!entry) continue;
            let polygon = entry.polygon;
            if (entry.geometry !== geometry && (entry.x !== light.x || entry.y !== light.y)) {
                const dx = light.x - entry.x, dy = light.y - entry.y;
                polygon = Float64Array.from(polygon, (value, index) => value + (index % 2 ? dy : dx));
            }
            rows.push({ light, radius, polygon });
        }
        return rows;
    }
    dispose() {
        this.#closed = true;
        this.#jobs?.dispose();
        this.#jobs = undefined;
        this.#entries.clear();
        this.#lights = [];
    }
}
