import { WallRayIndex } from "./wall-ray-index.js";
const baseAngles = Array.from({ length: 128 }, (_, i) => i * Math.PI * 2 / 128);

/** Prepare once for a stable wall snapshot; rebuild after geometry or blocking changes. */
export function createVisibilityContext(walls) {
    const segments = walls.filter(w => w.door_state !== "open" && w.blocks_sight !== 0 && w.vision_behavior !== "pass");
    let index;
    return { walls: segments, get index() { return index ??= new WallRayIndex(segments); }, subsets: new Map() };
}

/** Ray/segment intersections, including rays on either side of occluder endpoints. */
export function visibilityPolygon(origin, radius, walls, context = createVisibilityContext(walls)) {
    const elevation = origin.elevation ?? 0;
    const angles = baseAngles.slice(), selected = [];
    for (let i = 0; i < context.walls.length; i++) {
        const w = context.walls[i];
        if ((w.vertical_bottom != null && elevation < w.vertical_bottom) || (w.vertical_top != null && elevation > w.vertical_top) || Math.max(w.x1, w.x2) < origin.x - radius || Math.min(w.x1, w.x2) > origin.x + radius || Math.max(w.y1, w.y2) < origin.y - radius || Math.min(w.y1, w.y2) > origin.y + radius)
            continue;
        selected.push(i);
        const a = Math.atan2(w.y1 - origin.y, w.x1 - origin.x), b = Math.atan2(w.y2 - origin.y, w.x2 - origin.x);
        angles.push(a - 0.00001, a, a + 0.00001, b - 0.00001, b, b + 0.00001);
    }
    let index;
    if (selected.length !== context.walls.length) {
        // Preserve the original tree membership as well as the intersections:
        // changing it can alter rounding at rays through coincident endpoints.
        const key = selected.join(",");
        index = context.subsets.get(key);
        if (!index) {
            index = new WallRayIndex(selected.map(i => context.walls[i]));
            if (context.subsets.size >= 8)
                context.subsets.delete(context.subsets.keys().next().value);
            context.subsets.set(key, index);
        }
    }
    else
        index = context.index;
    const cone = (origin.angle ?? 360) < 360, direction = (origin.rotation ?? 0) * Math.PI / 180, half = (origin.angle ?? 360) * Math.PI / 360;
    const relative = (angle) => Math.atan2(Math.sin(angle - direction), Math.cos(angle - direction));
    if (cone)
        angles.push(direction - half, direction + half);
    const rays = angles.filter(a => !cone || Math.abs(relative(a)) <= half + 1e-9);
    const points = rays.map(a => (a + Math.PI * 2) % (Math.PI * 2)).sort((a, b) => cone ? relative(a) - relative(b) : a - b).map(angle => {
        const dx = Math.cos(angle), dy = Math.sin(angle);
        const distance = index.cast(origin, dx, dy, radius);
        return { x: origin.x + dx * distance, y: origin.y + dy * distance };
    });
    return cone ? [{ x: origin.x, y: origin.y }, ...points, { x: origin.x, y: origin.y }] : points;
}
