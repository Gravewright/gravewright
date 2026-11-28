// widgets/game-board/model/light-polygons.js
import { VisibilityJobs } from "./visibility-jobs.js";
function lightRadius(light, cell, width, height) {
  return light.dim_radius === 0 ? Math.hypot(width, height) * 2 : Math.max(light.dim_radius, light.bright_radius) * cell;
}
function lightWalls(walls) {
  return walls.filter((w) => w.blocks_light !== 0 && w.light_behavior !== "pass").map((w) => ({ ...w, blocks_sight: w.blocks_light, vision_behavior: w.light_behavior }));
}
var geometryOf = (light, radius) => JSON.stringify([
  light.x,
  light.y,
  radius,
  light.elevation ?? 0,
  light.angle ?? 360,
  light.rotation ?? 0
]);
function changedWalls(previous, next) {
  const counts = /* @__PURE__ */ new Map();
  for (const key of previous) counts.set(key, (counts.get(key) ?? 0) + 1);
  const changed = [];
  for (const [index, key] of next.entries()) {
    const count = counts.get(key) ?? 0;
    if (count > 0) counts.set(key, count - 1);
    else changed.push(index);
  }
  return { added: changed, removed: [...counts].filter(([, count]) => count > 0).map(([key]) => key) };
}
var box = (w) => [Math.min(w.x1, w.x2), Math.min(w.y1, w.y2), Math.max(w.x1, w.x2), Math.max(w.y1, w.y2)];
var reaches = (entry, [left, top, right, bottom]) => right >= entry.x - entry.radius && left <= entry.x + entry.radius && bottom >= entry.y - entry.radius && top <= entry.y + entry.radius;
var LightPolygons = class {
  #entries = /* @__PURE__ */ new Map();
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
  constructor({ onUpdate, createJobs = (walls) => new VisibilityJobs(walls) } = {}) {
    this.#onUpdate = onUpdate;
    this.#createJobs = createJobs;
  }
  /** True while a worker result for the current lights is outstanding. */
  get pending() {
    return this.#pending;
  }
  /** Returns `{ light, radius, polygon }` rows for every enabled light, in order. */
  update(lights, walls, cell, width, height) {
    if (this.#closed) return [];
    if (walls !== this.#walls) this.#setWalls(walls);
    const sources = [], wanted = /* @__PURE__ */ new Set();
    this.#lights = [];
    for (const light of lights) {
      wanted.add(light.id);
      if (!light.enabled) continue;
      const radius = lightRadius(light, cell, width, height);
      if (!(radius > 0)) continue;
      const geometry = geometryOf(light, radius);
      this.#lights.push({ light, radius, geometry });
      const entry = this.#entries.get(light.id);
      if (entry?.valid && entry.geometry === geometry) continue;
      sources.push({
        id: light.id,
        geometry,
        x: light.x,
        y: light.y,
        radius,
        elevation: light.elevation ?? 0,
        angle: light.angle ?? 360,
        rotation: light.rotation ?? 0
      });
    }
    for (const id of this.#entries.keys()) if (!wanted.has(id)) this.#entries.delete(id);
    const request = ++this.#request;
    this.#pending = sources.length > 0;
    if (sources.length) {
      this.#jobs ??= this.#createJobs(this.#walls);
      this.#updating = true;
      try {
        this.#jobs.request(sources.map(({ x, y, radius, elevation, angle, rotation }) => ({ x, y, radius, elevation, angle, rotation })), 0, (polygons) => this.#store(request, sources, polygons));
      } finally {
        this.#updating = false;
      }
    }
    return this.rows();
  }
  #store(request, sources, polygons) {
    if (this.#closed) return;
    this.calculated += sources.length;
    sources.forEach((source, index) => {
      const polygon = polygons[index];
      if (polygon) this.#entries.set(source.id, {
        geometry: source.geometry,
        x: source.x,
        y: source.y,
        radius: source.radius,
        polygon,
        valid: true
      });
    });
    if (request === this.#request) this.#pending = false;
    if (!this.#updating) this.#onUpdate?.(this.rows());
  }
  #setWalls(walls) {
    const keys = walls.map((wall) => JSON.stringify(wall));
    if (this.#walls !== void 0) {
      const { added, removed } = changedWalls(this.#wallKeys, keys);
      const boxes = [...added.map((index) => box(walls[index])), ...removed.map((key) => box(JSON.parse(key)))];
      if (boxes.length) {
        for (const entry of this.#entries.values())
          if (entry.valid && boxes.some((bounds) => reaches(entry, bounds))) entry.valid = false;
      }
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
    this.#jobs = void 0;
    this.#entries.clear();
    this.#lights = [];
  }
};
export {
  LightPolygons,
  lightRadius,
  lightWalls
};
