import { WallRayIndex } from "./wall-ray-index.js";
/** Ray/segment intersections, including rays on either side of occluder endpoints. */
export function visibilityPolygon(origin, radius, walls) {
    const segments = walls.filter(w => (w.vertical_bottom == null || (origin.elevation ?? 0) >= w.vertical_bottom) && (w.vertical_top == null || (origin.elevation ?? 0) <= w.vertical_top) && Math.max(w.x1, w.x2) >= origin.x - radius && Math.min(w.x1, w.x2) <= origin.x + radius && Math.max(w.y1, w.y2) >= origin.y - radius && Math.min(w.y1, w.y2) <= origin.y + radius && w.door_state !== "open" && w.blocks_sight !== 0 && w.vision_behavior !== "pass");
    const index = new WallRayIndex(segments);
    const angles = Array.from({ length: 128 }, (_, i) => i * Math.PI * 2 / 128);
    for (const w of segments)
        for (const p of [{ x: w.x1, y: w.y1 }, { x: w.x2, y: w.y2 }]) {
            const a = Math.atan2(p.y - origin.y, p.x - origin.x);
            angles.push(a - 0.00001, a, a + 0.00001);
        }
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
