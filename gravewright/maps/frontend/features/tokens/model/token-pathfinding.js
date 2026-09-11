import { movementBlocked } from './token-interaction.js';
import { routeMeasurements } from './token-route.js';
/** A bounded A* search; exact existing movement tests remain authoritative for every edge. */
export function suggestTokenRoute(route, walls, cell, width, height, limits = {}) {
    if (route.length < 2 || !(cell > 0) || !Number.isFinite(width + height + cell))
        return;
    const first = route[0], last = route.at(-1);
    if (!first.length || first.length !== last.length)
        return;
    const anchor = first[0], dx = last[0].gridX - anchor.gridX, dy = last[0].gridY - anchor.gridY;
    // A formation that was independently clamped against map edges cannot share a translation path.
    if (first.some((t, i) => t.id !== last[i].id || Math.abs(last[i].gridX - t.gridX - dx) > 1e-7 || Math.abs(last[i].gridY - t.gridY - dy) > 1e-7))
        return;
    const rows = (x, y) => first.map(t => ({ ...t, gridX: t.gridX + x, gridY: t.gridY + y }));
    const inside = (x, y) => first.every(t => t.gridX + x >= 0 && t.gridY + y >= 0 &&
        t.gridX + x + t.cells <= width / cell && t.gridY + y + (t.heightCells ?? t.cells) <= height / cell);
    if (!inside(0, 0) || !inside(dx, dy))
        return;
    const clear = (x, y, nx, ny) => first.every(t => !movementBlocked({ ...t, gridX: t.gridX + x, gridY: t.gridY + y }, { gridX: t.gridX + nx, gridY: t.gridY + ny }, walls, cell));
    const chosenBlocked = route.slice(1).some((step, i) => step.some((token, j) =>
        movementBlocked(route[i][j], token, walls, cell)));
    // A valid detour is useful even when the drawn straight line cuts through a wall.
    const shorter = (candidate) => candidate.length <= 512 &&
        (chosenBlocked || routeMeasurements(candidate, 1).total + 1e-6 < routeMeasurements(route, 1).total) ? candidate : undefined;
    if (clear(0, 0, dx, dy))
        return shorter([first, last]);
    const heap = [];
    const push = (node) => {
        let i = heap.length;
        heap.push(node);
        while (i) {
            const p = (i - 1) >> 1;
            if (heap[p].f <= node.f)
                break;
            heap[i] = heap[p];
            i = p;
        }
        heap[i] = node;
    };
    const pop = () => {
        const result = heap[0], tail = heap.pop();
        if (heap.length) {
            let i = 0;
            while (i * 2 + 1 < heap.length) {
                let child = i * 2 + 1;
                if (child + 1 < heap.length && heap[child + 1].f < heap[child].f)
                    child++;
                if (heap[child].f >= tail.f)
                    break;
                heap[i] = heap[child];
                i = child;
            }
            heap[i] = tail;
        }
        return result;
    };
    const key = (x, y) => `${x},${y}`;
    const best = new Map([[key(0, 0), 0]]);
    const deadline = performance.now() + (limits.milliseconds ?? 100);
    const budget = limits.nodes ?? 12000;
    push({ x: 0, y: 0, g: 0, f: Math.hypot(dx, dy) });
    let explored = 0;
    while (heap.length && explored++ < budget) {
        if (performance.now() > deadline)
            return;
        const current = pop();
        if (current.g !== best.get(key(current.x, current.y)))
            continue;
        if (current.x === dx && current.y === dy) {
            const points = [];
            for (let n = current; n; n = n.parent)
                points.push(n);
            points.reverse();
            // Collapse only collinear edges: never introduce untested shortcuts through walls.
            const compact = [points[0]];
            for (let i = 1; i < points.length - 1; i++) {
                const a = compact.at(-1), b = points[i], c = points[i + 1];
                if (Math.abs((b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x)) > 1e-8)
                    compact.push(b);
            }
            compact.push(current);
            return shorter(compact.map(n => rows(n.x, n.y)));
        }
        const neighbors = [];
        for (let x = -1; x <= 1; x++)
            for (let y = -1; y <= 1; y++)
                if (x || y)
                    neighbors.push([current.x + x, current.y + y]);
        // Exact final click can be fractional (Alt/no snapping); do not round it away.
        if (Math.hypot(current.x - dx, current.y - dy) <= Math.SQRT2)
            neighbors.push([dx, dy]);
        for (const [x, y] of neighbors) {
            const g = current.g + Math.hypot(x - current.x, y - current.y), id = key(x, y);
            if (g >= (best.get(id) ?? Infinity) || !inside(x, y) || !clear(current.x, current.y, x, y))
                continue;
            best.set(id, g);
            push({ x, y, g, f: g + Math.hypot(dx - x, dy - y), parent: current });
        }
    }
}
