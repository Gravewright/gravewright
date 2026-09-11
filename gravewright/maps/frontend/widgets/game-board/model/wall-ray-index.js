/** Balanced bounding-volume hierarchy; exact segment hits, early rejection of whole branches. */
export class WallRayIndex {
    root;
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
    cast(origin, dx, dy, radius) {
        let distance = radius;
        const entry = (n) => { let near = 0, far = distance; for (const [p, d, min, max] of [[origin.x, dx, n.minX, n.maxX], [origin.y, dy, n.minY, n.maxY]]) {
            if (Math.abs(d) < 1e-12) {
                if (p < min || p > max)
                    return Infinity;
                continue;
            }
            const a = (min - p) / d, b = (max - p) / d;
            near = Math.max(near, Math.min(a, b));
            far = Math.min(far, Math.max(a, b));
            if (near > far)
                return Infinity;
        } return near; };
        const visit = (node) => {
            if (entry(node) > distance)
                return;
            if (node.walls) {
                for (const w of node.walls) {
                    const sx = w.x2 - w.x1, sy = w.y2 - w.y1, den = dx * sy - dy * sx;
                    if (Math.abs(den) < 1e-10)
                        continue;
                    const ox = w.x1 - origin.x, oy = w.y1 - origin.y;
                    const t = (ox * sy - oy * sx) / den, u = (ox * dy - oy * dx) / den;
                    if (t >= 0 && u >= 0 && u <= 1)
                        distance = Math.min(distance, t);
                }
                return;
            }
            const left = node.left, right = node.right;
            if (entry(left) <= entry(right)) {
                visit(left);
                visit(right);
            }
            else {
                visit(right);
                visit(left);
            }
        };
        if (this.root)
            visit(this.root);
        return distance;
    }
}
