/** Bounded continuous floor geometry in map cells; saved rings are bbox-local. */
import { terrainBrushAlpha, terrainBrushError } from './terrain-brush.js';
export const floorShapeLimits = Object.freeze({ rings: 128, vertices: 256, points: 4096, documentPoints: 16384,
    minSize: .001, paintPixels: 67108864, edgePixels: 8388608 });
const epsilon = 1e-9;
const tidy = value => Math.round(value * 1e9) / 1e9;
const finite = point => Array.isArray(point) && point.length === 2 && point.every(Number.isFinite);
const rectangle = (x, y, width, height) => [[x, y], [x + width, y], [x + width, y + height], [x, y + height]];
const cross = (a, b, p) => (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
function cleanRing(points) {
    const ring = [];
    for (const point of points) {
        const next = point.map(tidy), last = ring.at(-1);
        if (!last || Math.hypot(next[0] - last[0], next[1] - last[1]) > epsilon) ring.push(next);
    }
    if (ring.length > 1 && Math.hypot(ring[0][0] - ring.at(-1)[0], ring[0][1] - ring.at(-1)[1]) <= epsilon) ring.pop();
    if (ring.length < 3) return [];
    const second = ring.find(point => Math.hypot(point[0] - ring[0][0], point[1] - ring[0][1]) > epsilon);
    return second && ring.some(point => Math.abs(cross(ring[0], second, point)) > epsilon) ? ring : [];
}
/** Clip even concave/self-intersecting rings against an axis-aligned box. */
export function clipFloorRing(ring, bounds) {
    if (!Array.isArray(ring) || !ring.every(finite)) return [];
    let points = ring;
    for (const [axis, edge, direction] of [[0, bounds.x, 1], [0, bounds.x + bounds.width, -1],
        [1, bounds.y, 1], [1, bounds.y + bounds.height, -1]]) {
        const output = [];
        for (let index = 0; index < points.length; index++) {
            const a = points[index], b = points[(index + 1) % points.length];
            const ai = direction * (a[axis] - edge) >= -epsilon, bi = direction * (b[axis] - edge) >= -epsilon;
            if (ai) output.push(a);
            if (ai !== bi) {
                const t = (edge - a[axis]) / (b[axis] - a[axis]);
                const point = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
                point[axis] = edge; output.push(point);
            }
        }
        points = output;
        if (points.length < 3) return [];
    }
    return cleanRing(points);
}
/** Return world-coordinate rings. Each contour is filled independently using even-odd. */
export function floorShapeRings(item, part = 'contours') {
    if (!item.shape) return part === 'contours' ? [rectangle(item.x, item.y, item.width, item.height)] : [];
    return (item.shape[part] || []).map(ring => ring.map(([u, v]) => [item.x + u * item.width, item.y + v * item.height]));
}
function ringContains(ring, x, y, boundary = true) {
    let inside = false;
    for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
        const a = ring[previous], b = ring[index];
        if (Math.abs(cross(a, b, [x, y])) <= epsilon && x >= Math.min(a[0], b[0]) - epsilon
            && x <= Math.max(a[0], b[0]) + epsilon && y >= Math.min(a[1], b[1]) - epsilon
            && y <= Math.max(a[1], b[1]) + epsilon) return boundary;
        if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
    }
    return inside;
}
export function floorContainsPoint(item, point) {
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y) || point.x < item.x - epsilon
        || point.y < item.y - epsilon || point.x > item.x + item.width + epsilon || point.y > item.y + item.height + epsilon) return false;
    if (!item.shape) return !item.brush || terrainBrushAlpha(item, point) > 0;
    const x = (point.x - item.x) / item.width, y = (point.y - item.y) / item.height;
    return item.shape.contours.some(ring => ringContains(ring, x, y))
        && !(item.shape.cuts || []).some(ring => ringContains(ring, x, y))
        && (!item.brush || terrainBrushAlpha(item, point) > 0);
}
function mergeIntervals(values) {
    values.sort((a, b) => a[0] - b[0]);
    const result = [];
    for (const interval of values) {
        const last = result.at(-1);
        if (last && interval[0] <= last[1] + epsilon) last[1] = Math.max(last[1], interval[1]);
        else result.push([...interval]);
    }
    return result;
}
function intervalsAt(rings, y) {
    const result = [];
    for (const ring of rings) {
        const points = [];
        for (let index = 0; index < ring.length; index++) {
            const a = ring[index], b = ring[(index + 1) % ring.length];
            if ((a[1] > y) !== (b[1] > y)) points.push(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]));
        }
        points.sort((a, b) => a - b);
        for (let index = 1; index < points.length; index += 2) if (points[index] - points[index - 1] > epsilon) result.push([points[index - 1], points[index]]);
    }
    return mergeIntervals(result);
}
function subtractIntervals(base, cuts) {
    const result = [];
    for (const [left, right] of base) {
        let cursor = left;
        for (const [a, b] of cuts) {
            if (b <= cursor || a >= right) continue;
            if (a > cursor + epsilon) result.push([cursor, Math.min(a, right)]);
            cursor = Math.max(cursor, b);
        }
        if (cursor < right - epsilon) result.push([cursor, right]);
    }
    return result;
}
function convexRingContainsAll(ring, points) {
    if (new Set(ring.map(point => `${point[0]}:${point[1]}`)).size !== ring.length) return false;
    let sign = 0;
    for (let index = 0; index < ring.length; index++) {
        const value = cross(ring[index], ring[(index + 1) % ring.length], ring[(index + 2) % ring.length]);
        if (Math.abs(value) <= epsilon) continue;
        if (sign && Math.sign(value) !== sign) return false;
        sign = Math.sign(value);
    }
    const contains = point => ring.every((a, index) => sign * cross(a, ring[(index + 1) % ring.length], point) >= -epsilon);
    return sign !== 0 && ring.every(contains) && points.every(contains);
}
/** Test positive area exactly between polygon edges, including unions of overlapping cuts. */
export function floorRegionHasArea(contours, cuts = [], intersect = null) {
    if (!contours.length || intersect?.length === 0) return false;
    // A common full-room erase needs no pairwise edge arrangement. Convexity
    // makes containment of every vertex sufficient for each entire contour.
    if (cuts.some(ring => convexRingContainsAll(ring, contours.flat())
        || intersect && convexRingContainsAll(ring, intersect.flat()))) return false;
    const rings = [...contours, ...cuts, ...(intersect || [])];
    const levels = [...new Set(rings.flatMap(ring => ring.map(point => point[1])))].sort((a, b) => a - b);
    const at = y => {
        const visible = subtractIntervals(intervalsAt(contours, y), intervalsAt(cuts, y));
        if (!intersect) return visible.length > 0;
        const target = intervalsAt(intersect, y);
        return visible.some(([a, b]) => target.some(([c, d]) => Math.min(b, d) - Math.max(a, c) > epsilon));
    };
    const scan = values => values.some((y, index) => index && y - values[index - 1] > epsilon && at((y + values[index - 1]) / 2));
    if (scan(levels)) return true;
    // Edge crossings can open a narrow region between two vertex heights.
    const segments = rings.flatMap(ring => ring.map((a, index) => [a, ring[(index + 1) % ring.length]]));
    const extra = [];
    for (let index = 0; index < segments.length; index++) for (let other = index + 1; other < segments.length; other++) {
        const [a, b] = segments[index], [c, d] = segments[other];
        if (Math.max(Math.min(a[0], b[0]), Math.min(c[0], d[0])) > Math.min(Math.max(a[0], b[0]), Math.max(c[0], d[0])) + epsilon
            || Math.max(Math.min(a[1], b[1]), Math.min(c[1], d[1])) > Math.min(Math.max(a[1], b[1]), Math.max(c[1], d[1])) + epsilon) continue;
        const dx = b[0] - a[0], dy = b[1] - a[1], ex = d[0] - c[0], ey = d[1] - c[1], denominator = dx * ey - dy * ex;
        if (Math.abs(denominator) <= epsilon) continue;
        const t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / denominator;
        const u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / denominator;
        if (t > epsilon && t < 1 - epsilon && u > epsilon && u < 1 - epsilon) extra.push(a[1] + t * dy);
    }
    return extra.length ? scan([...new Set([...levels, ...extra])].sort((a, b) => a - b)) : false;
}
/** Prove that a positive-area footprint sees only matching topmost floors.
 * Floors are ordered bottom-to-top and already restricted to the edited layer.
 * The bounded exact proof throws instead of treating an unknown region as covered.
 */
export function floorRegionCoveredBy(contours, orderedFloors, matches) {
    if (!contours.length) return false;
    let work = 0;
    const spend = count => {
        work += count;
        if (work > floorShapeLimits.edgePixels) throw new RangeError('The map floor shapes are too complex.');
    };
    const boundsOf = rings => {
        let left = Infinity, top = Infinity, right = -Infinity, bottom = -Infinity, points = 0;
        for (const ring of rings) for (const [x, y] of ring) {
            spend(1); points++;
            left = Math.min(left, x); top = Math.min(top, y); right = Math.max(right, x); bottom = Math.max(bottom, y);
        }
        return { left, top, right, bottom, points };
    };
    const bounds = boundsOf(contours), rows = [];
    if (!(bounds.right > bounds.left && bounds.bottom > bounds.top)) return false;
    for (const item of orderedFloors) {
        spend(1);
        if (item.paint?.opacity === 0 || item.x >= bounds.right || item.y >= bounds.bottom
            || item.x + item.width <= bounds.left || item.y + item.height <= bounds.top) continue;
        // Radial alpha and ordered erasures cannot prove an opaque material union.
        if (item.brush) return false;
        const fills = floorShapeRings(item), cuts = floorShapeRings(item, 'cuts');
        rows.push({ fills, cuts, bounds: boundsOf(fills), points: fills.reduce((sum, ring) => sum + ring.length, 0)
            + cuts.reduce((sum, ring) => sum + ring.length, 0), matches: matches(item) });
        spend(cuts.reduce((sum, ring) => sum + ring.length, 0));
    }
    if (!rows.length) return false;
    // A convex room or brush underneath only matching surfaces is a frequent
    // repeat; its vertex proof avoids building a quadratic edge arrangement.
    let sameAbove = true;
    const targetPoints = contours.flat();
    const enclosesBounds = box => box.left <= bounds.left + epsilon && box.top <= bounds.top + epsilon
        && box.right >= bounds.right - epsilon && box.bottom >= bounds.bottom - epsilon;
    for (let index = rows.length - 1; index >= 0; index--) {
        const row = rows[index];
        sameAbove &&= row.matches;
        if (!sameAbove || row.cuts.length || !enclosesBounds(row.bounds)) continue;
        for (const ring of row.fills) {
            if (!enclosesBounds(boundsOf([ring]))) continue;
            spend(ring.length * (ring.length + targetPoints.length));
            if (convexRingContainsAll(ring, targetPoints)) return true;
        }
    }
    const rings = [...contours, ...rows.flatMap(row => [...row.fills, ...row.cuts])];
    const levels = new Set([bounds.top, bounds.bottom]), segments = [];
    let axisAligned = true;
    for (const ring of rings) for (let index = 0; index < ring.length; index++) {
        spend(1);
        const a = ring[index], b = ring[(index + 1) % ring.length];
        if (a[1] > bounds.top && a[1] < bounds.bottom) levels.add(a[1]);
        axisAligned &&= a[0] === b[0] || a[1] === b[1];
        // Horizontal intersections occur at vertex levels already in the set.
        if (a[1] !== b[1] && Math.max(a[0], b[0]) >= bounds.left && Math.min(a[0], b[0]) <= bounds.right
            && Math.max(a[1], b[1]) > bounds.top && Math.min(a[1], b[1]) < bounds.bottom) segments.push([a, b]);
    }
    const atIntervals = (values, y, points) => { spend(points); return intervalsAt(values, y); };
    const subtract = (base, cuts) => {
        const result = [];
        let firstCut = 0;
        for (const [left, right] of base) {
            spend(1);
            while (firstCut < cuts.length && cuts[firstCut][1] <= left) { spend(1); firstCut++; }
            let cursor = left;
            for (let index = firstCut; index < cuts.length && cuts[index][0] < right; index++) {
                spend(1);
                const [a, b] = cuts[index];
                if (a > cursor + epsilon) result.push([cursor, Math.min(a, right)]);
                cursor = Math.max(cursor, b);
                if (cursor >= right) break;
            }
            if (cursor < right - epsilon) result.push([cursor, right]);
        }
        return result;
    };
    const overlaps = (first, second) => {
        let a = 0, b = 0;
        while (a < first.length && b < second.length) {
            spend(1);
            if (Math.min(first[a][1], second[b][1]) - Math.max(first[a][0], second[b][0]) > epsilon) return true;
            if (first[a][1] < second[b][1]) a++; else b++;
        }
        return false;
    };
    const checked = new Set();
    const scan = values => {
        for (let index = 1; index < values.length; index++) {
            if (values[index] - values[index - 1] <= epsilon) continue;
            const y = (values[index] + values[index - 1]) / 2;
            if (checked.has(y)) continue;
            let remaining = atIntervals(contours, y, bounds.points);
            for (let rowIndex = rows.length - 1; rowIndex >= 0 && remaining.length; rowIndex--) {
                spend(1);
                const row = rows[rowIndex];
                if (y <= row.bounds.top || y >= row.bounds.bottom) continue;
                spend(row.points);
                const visible = subtract(intervalsAt(row.fills, y), intervalsAt(row.cuts, y));
                if (!row.matches && overlaps(remaining, visible)) return false;
                remaining = subtract(remaining, visible);
            }
            if (remaining.length) return false;
            checked.add(y);
        }
        return true;
    };
    if (!scan([...levels].sort((a, b) => a - b))) return false;
    if (axisAligned) return true;
    // Linear interval ordering changes only at a vertex or an edge crossing.
    // Probe every resulting slab, rather than sampling a fixed grid of points.
    for (let index = 0; index < segments.length; index++) for (let other = index + 1; other < segments.length; other++) {
        spend(1);
        const [a, b] = segments[index], [c, d] = segments[other];
        if (Math.max(Math.min(a[0], b[0]), Math.min(c[0], d[0])) > Math.min(Math.max(a[0], b[0]), Math.max(c[0], d[0])) + epsilon
            || Math.max(Math.min(a[1], b[1]), Math.min(c[1], d[1])) > Math.min(Math.max(a[1], b[1]), Math.max(c[1], d[1])) + epsilon) continue;
        const dx = b[0] - a[0], dy = b[1] - a[1], ex = d[0] - c[0], ey = d[1] - c[1], denominator = dx * ey - dy * ex;
        if (denominator === 0) continue;
        const t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / denominator;
        const u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / denominator;
        if (t <= 0 || t >= 1 || u <= 0 || u >= 1) continue;
        const y = a[1] + t * dy, x = a[0] + t * dx;
        if (x >= bounds.left - epsilon && x <= bounds.right + epsilon && y > bounds.top && y < bounds.bottom) levels.add(y);
    }
    return scan([...levels].sort((a, b) => a - b));
}
export function floorIntersectsRectangle(item, rect) {
    if (rect.width <= epsilon || rect.height <= epsilon) return floorContainsPoint(item, { x: rect.x, y: rect.y });
    if (item.x >= rect.x + rect.width || item.y >= rect.y + rect.height || item.x + item.width <= rect.x || item.y + item.height <= rect.y) return false;
    if (item.brush && !item.brush.points.some(([u, v, alpha]) => {
        if (!alpha) return false;
        const x = item.x + u * item.width, y = item.y + v * item.height;
        const dx = (x - Math.max(rect.x, Math.min(rect.x + rect.width, x))) / (item.width * item.brush.radius[0]);
        const dy = (y - Math.max(rect.y, Math.min(rect.y + rect.height, y))) / (item.height * item.brush.radius[1]);
        return dx * dx + dy * dy < 1;
    })) return false;
    return floorRegionHasArea(floorShapeRings(item), floorShapeRings(item, 'cuts'), [rectangle(rect.x, rect.y, rect.width, rect.height)]);
}
export function floorShapeFromRings(contours) {
    if (contours.length > floorShapeLimits.rings || contours.reduce((sum, ring) => sum + ring.length, 0) > floorShapeLimits.points)
        throw new RangeError('The map floor shapes are too complex.');
    const points = contours.flat();
    if (!points.length) return null;
    const x = Math.min(...points.map(point => point[0])), y = Math.min(...points.map(point => point[1]));
    const width = Math.max(...points.map(point => point[0])) - x, height = Math.max(...points.map(point => point[1])) - y;
    if (width < floorShapeLimits.minSize - epsilon || height < floorShapeLimits.minSize - epsilon) return null;
    return { x, y, width, height, shape: { contours: contours.map(ring => ring.map(([px, py]) => [tidy((px - x) / width), tidy((py - y) / height)])), cuts: [] } };
}
function circleRing(x, y, radius) {
    if (radius <= 0) return [];
    const count = Math.min(248, Math.max(24, Math.ceil(Math.PI / Math.acos(Math.max(-1, 1 - .002 / radius)) / 4) * 4));
    return Array.from({ length: count }, (_, index) => [x + radius * Math.cos(index * 2 * Math.PI / count), y + radius * Math.sin(index * 2 * Math.PI / count)]);
}
function circleRings(x, y, radius) {
    if (radius <= 0) return [];
    const count = Math.max(24, Math.ceil(Math.PI / Math.acos(Math.max(-1, 1 - .002 / radius)) / 4) * 4);
    if (count <= 248) return [circleRing(x, y, radius)];
    if (count > floorShapeLimits.points - 32) throw new RangeError('The map floor shapes are too complex.');
    // Large circles use independently filled sectors so each ring stays bounded
    // while preserving the same chord tolerance as small circles.
    const perSector = Math.ceil(count / Math.ceil(count / 244)), rings = [];
    for (let first = 0; first < count; first += perSector) {
        const ring = [[x, y]];
        for (let index = first; index <= Math.min(count, first + perSector); index++) {
            const angle = index * Math.PI * 2 / count;
            ring.push([x + radius * Math.cos(angle), y + radius * Math.sin(angle)]);
        }
        rings.push(ring);
    }
    return rings;
}
function convexHull(points) {
    const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]), lower = [], upper = [];
    for (const p of sorted) { while (lower.length > 1 && cross(lower.at(-2), lower.at(-1), p) <= epsilon) lower.pop(); lower.push(p); }
    for (const p of sorted.toReversed()) { while (upper.length > 1 && cross(upper.at(-2), upper.at(-1), p) <= epsilon) upper.pop(); upper.push(p); }
    return [...lower.slice(0, -1), ...upper.slice(0, -1)];
}
function sweptRing(a, b, size, shape, anchor) {
    const shift = anchor === 'center' ? -size / 2 : 0;
    if (shape === 'square') return convexHull([...rectangle(a.x + shift, a.y + shift, size, size), ...rectangle(b.x + shift, b.y + shift, size, size)]);
    const radius = size / 2, offset = anchor === 'corner' ? radius : 0;
    if (Math.hypot(b.x - a.x, b.y - a.y) <= epsilon) return circleRing(a.x + offset, a.y + offset, radius);
    const angle = Math.atan2(b.y - a.y, b.x - a.x), steps = Math.min(123, Math.max(12, Math.ceil(circleRing(0, 0, radius).length / 2)));
    const ring = [];
    for (let index = 0; index <= steps; index++) {
        const value = angle - Math.PI / 2 + index * Math.PI / steps;
        ring.push([b.x + offset + radius * Math.cos(value), b.y + offset + radius * Math.sin(value)]);
    }
    for (let index = 0; index <= steps; index++) {
        const value = angle + Math.PI / 2 + index * Math.PI / steps;
        ring.push([a.x + offset + radius * Math.cos(value), a.y + offset + radius * Math.sin(value)]);
    }
    return ring;
}
function simplifyPoints(points, tolerance) {
    if (points.length < 3) return points;
    const a = points[0], b = points.at(-1), dx = b.x - a.x, dy = b.y - a.y, squared = dx * dx + dy * dy;
    let distance = tolerance * tolerance, split = -1;
    for (let index = 1; index < points.length - 1; index++) {
        const point = points[index], t = squared ? Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / squared)) : 0;
        const value = (point.x - a.x - t * dx) ** 2 + (point.y - a.y - t * dy) ** 2;
        if (value > distance) { distance = value; split = index; }
    }
    return split < 0 ? [a, b] : [...simplifyPoints(points.slice(0, split + 1), tolerance).slice(0, -1), ...simplifyPoints(points.slice(split), tolerance)];
}
/** Continuous shape/stroke rings, clipped to the map without any cell enumeration. */
export function floorFreeContours(document, { mode = 'brush', start, end = start, points = [], size = 1,
    shape = 'square', anchor = shape === 'circle' ? 'center' : 'corner' } = {}) {
    if (!start || !end || ![start.x, start.y, end.x, end.y, size].every(Number.isFinite) || size < .05 || size > 20) return [];
    if (points.length > 2000) throw new RangeError('The map floor shapes are too complex.');
    let rings;
    if (mode === 'rectangle') rings = [rectangle(Math.min(start.x, end.x), Math.min(start.y, end.y), Math.abs(end.x - start.x), Math.abs(end.y - start.y))];
    else if (mode === 'circle') rings = circleRings(start.x, start.y, Math.hypot(end.x - start.x, end.y - start.y));
    else if (mode === 'polygon') rings = [points.map(point => [point.x, point.y])];
    else if (mode === 'brush') {
        const path = simplifyPoints(points.length ? points : [start, end], Math.min(.01, size / 20));
        if (path.length > floorShapeLimits.rings + 1) throw new RangeError('The map floor shapes are too complex.');
        rings = path.length < 2 ? [sweptRing(start, start, size, shape, anchor)]
            : path.slice(1).map((point, index) => sweptRing(path[index], point, size, shape, anchor));
    } else return [];
    const bounds = { x: 0, y: 0, width: document.columns, height: document.rows }, unique = new Map();
    let count = 0;
    for (const ring of rings) {
        const clipped = clipFloorRing(ring, bounds);
        const key = JSON.stringify(clipped);
        if (clipped.length && !unique.has(key)) {
            if (clipped.length > floorShapeLimits.vertices || count + clipped.length > floorShapeLimits.points
                || unique.size >= floorShapeLimits.rings) throw new RangeError('The map floor shapes are too complex.');
            count += clipped.length; unique.set(key, clipped);
        }
    }
    return [...unique.values()];
}
/** Return a replacement row, null for complete removal, or the original for a no-op. */
export function cutFloorContours(item, rings) {
    const clipped = rings.map(ring => clipFloorRing(ring, item)).filter(ring => ring.length);
    if (!clipped.length) return item;
    const normalize = ring => ring.map(([x, y]) => [tidy(Math.max(0, Math.min(1, (x - item.x) / item.width))),
        tidy(Math.max(0, Math.min(1, (y - item.y) / item.height)))]);
    const known = new Set((item.shape?.cuts || []).map(ring => JSON.stringify(ring)));
    const additions = clipped.map(normalize).filter(ring => !known.has(JSON.stringify(ring)));
    if (!additions.length) return item;
    const contours = floorShapeRings(item), cuts = floorShapeRings(item, 'cuts');
    if (!floorRegionHasArea(contours, cuts, clipped)) return item;
    const nextCuts = [...new Map([...cuts, ...clipped].map(ring => [JSON.stringify(ring), ring])).values()];
    if (!floorRegionHasArea(contours, nextCuts)) return null;
    return { ...item, shape: { contours: item.shape ? structuredClone(item.shape.contours) : [normalize(contours[0])], cuts: nextCuts.map(normalize) } };
}
function documentJsonSize(document) {
    const source = JSON.stringify(document);
    let size = source.length, quoted = false, escaped = false;
    // Python's json.dumps uses ASCII escapes and spaces after separators.
    // Two spare bytes per numeric token cover its different float exponent form.
    for (let index = 0; index < source.length; index++) {
        const char = source[index];
        if (source.charCodeAt(index) > 127) size += 5;
        if (escaped) { escaped = false; continue; }
        if (char === '\\' && quoted) { escaped = true; continue; }
        if (char === '"') quoted = !quoted;
        else if (!quoted && (char === ',' || char === ':')) size++;
        else if (!quoted && /[0-9-]/.test(char) && (index === 0 || !/[0-9.eE+-]/.test(source[index - 1]))) size += 2;
    }
    return size;
}
/** Match server source/raster budgets before changing any source document. */
export function floorGeometryError(document, floors = document.floors || []) {
    const brushError = terrainBrushError(document, floors);
    if (brushError) return brushError;
    let points = 0, paintPixels = 0, edgePixels = 0;
    const cell = document.cellSize;
    for (const item of floors) {
        paintPixels += item.width * item.height * cell * cell;
        if (!item.shape) continue;
        if (!Array.isArray(item.shape.contours) || !item.shape.contours.length || !Array.isArray(item.shape.cuts)) return 'Invalid floor shape.';
        const rings = [...item.shape.contours, ...(item.shape.cuts || [])];
        const count = rings.reduce((sum, ring) => sum + ring.length, 0);
        if (rings.length > floorShapeLimits.rings) return 'The map floor shapes are too complex.';
        if (count > floorShapeLimits.points || rings.some(ring => ring.length > floorShapeLimits.vertices)) return 'The map has too many floor shape points.';
        if (rings.some(ring => {
            if (ring.length < 3 || !ring.every(point => finite(point) && point.every(value => value >= 0 && value <= 1))) return true;
            const origin = ring[0], second = ring.find(point => point[0] !== origin[0] || point[1] !== origin[1]);
            return !second || !ring.some(point => cross(origin, second, point) !== 0);
        })) return 'Invalid floor shape.';
        points += count;
        for (const ring of floorShapeRings(item).concat(floorShapeRings(item, 'cuts'))) {
            const width = Math.max(1, Math.ceil(Math.max(...ring.map(p => p[0])) * cell) - Math.floor(Math.min(...ring.map(p => p[0])) * cell));
            const height = Math.max(1, Math.ceil(Math.max(...ring.map(p => p[1])) * cell) - Math.floor(Math.min(...ring.map(p => p[1])) * cell));
            paintPixels += width * height;
            edgePixels += ring.length * height;
        }
    }
    for (const wall of document.walls || []) paintPixels += (Math.abs(wall.x2 - wall.x1) + wall.thickness)
        * (Math.abs(wall.y2 - wall.y1) + wall.thickness) * cell * cell;
    if (points > floorShapeLimits.documentPoints) return 'The map has too many floor shape points.';
    if (paintPixels > floorShapeLimits.paintPixels) return 'The map has too many overlapping painted surfaces.';
    if (edgePixels > floorShapeLimits.edgePixels) return 'The map floor shapes are too complex.';
    if (documentJsonSize({ ...document, floors }) > 1000000) return 'The map project is too large.';
    return null;
}
