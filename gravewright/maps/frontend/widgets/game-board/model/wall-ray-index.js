// Separate scalar slabs avoid temporary arrays and closures in the ray hot path.
function entry(node, x, y, dx, dy, distance) {
    let near = 0, far = distance;
    if (Math.abs(dx) < 1e-12) {
        if (x < node.minX || x > node.maxX)
            return Infinity;
    }
    else {
        const a = (node.minX - x) / dx, b = (node.maxX - x) / dx;
        near = Math.max(near, Math.min(a, b));
        far = Math.min(far, Math.max(a, b));
        if (near > far)
            return Infinity;
    }
    if (Math.abs(dy) < 1e-12) {
        if (y < node.minY || y > node.maxY)
            return Infinity;
    }
    else {
        const a = (node.minY - y) / dy, b = (node.maxY - y) / dy;
        near = Math.max(near, Math.min(a, b));
        far = Math.min(far, Math.max(a, b));
        if (near > far)
            return Infinity;
    }
    return near;
}

/** Balanced bounding-volume hierarchy; exact segment hits, early rejection of whole branches. */
export class WallRayIndex {
    root;
    stack = [];
    constructor(walls) { this.root = walls.length ? this.build([...walls]) : undefined; }
    build(walls) {
        const node = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
        for (const w of walls) {
            node.minX = Math.min(node.minX, w.x1, w.x2);
            node.minY = Math.min(node.minY, w.y1, w.y2);
            node.maxX = Math.max(node.maxX, w.x1, w.x2);
            node.maxY = Math.max(node.maxY, w.y1, w.y2);
        }
        if (walls.length <= 8) {
            node.walls = walls;
            return node;
        }
        const x = node.maxX - node.minX >= node.maxY - node.minY;
        walls.sort((a, b) => x ? (a.x1 + a.x2) - (b.x1 + b.x2) : (a.y1 + a.y2) - (b.y1 + b.y2));
        const middle = walls.length >> 1;
        node.left = this.build(walls.slice(0, middle));
        node.right = this.build(walls.slice(middle));
        return node;
    }
    // Supplying elevation permits one index to serve sources at different heights.
    // Omitting it retains the generic, two-dimensional ray-index contract.
    cast(origin, dx, dy, radius, elevation) {
        let distance = radius;
        if (!this.root)
            return distance;
        const x = origin.x, y = origin.y;
        const stack = this.stack;
        let length = 1;
        stack[0] = this.root;
        while (length) {
            const node = stack[--length];
            if (entry(node, x, y, dx, dy, distance) > distance)
                continue;
            if (node.walls) {
                for (const w of node.walls) {
                    if (elevation !== undefined && ((w.vertical_bottom != null && elevation < w.vertical_bottom) || (w.vertical_top != null && elevation > w.vertical_top)))
                        continue;
                    const sx = w.x2 - w.x1, sy = w.y2 - w.y1, den = dx * sy - dy * sx;
                    if (Math.abs(den) < 1e-10)
                        continue;
                    const ox = w.x1 - x, oy = w.y1 - y;
                    const t = (ox * sy - oy * sx) / den, u = (ox * dy - oy * dx) / den;
                    if (t >= 0 && u >= 0 && u <= 1)
                        distance = Math.min(distance, t);
                }
                continue;
            }
            const left = node.left, right = node.right;
            if (entry(left, x, y, dx, dy, distance) <= entry(right, x, y, dx, dy, distance)) {
                stack[length++] = right;
                stack[length++] = left;
            }
            else {
                stack[length++] = left;
                stack[length++] = right;
            }
        }
        return distance;
    }
}
