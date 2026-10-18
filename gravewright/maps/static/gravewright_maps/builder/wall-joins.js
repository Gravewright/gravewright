/** Derived wall artwork only: source center lines and native collision stay intact. */
const epsilon = 1e-7, binSize = 8, maxWork = 8388608;
const cross = (a, b) => a.x * b.y - a.y * b.x;
const dot = (a, b) => a.x * b.x + a.y * b.y;
const add = (a, b, scale = 1) => ({ x: a.x + b.x * scale, y: a.y + b.y * scale });
const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y });
const pointKey = p => `${Math.round(p.x / epsilon)}:${Math.round(p.y / epsilon)}`;
const first = wall => ({ x: wall.x1, y: wall.y1 });
const last = wall => ({ x: wall.x2, y: wall.y2 });
const same = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) <= epsilon;

function frames(document) {
    const result = new Map(), groups = new Map();
    for (const wall of document.walls) {
        const a = first(wall), b = last(wall), size = Math.hypot(b.x - a.x, b.y - a.y);
        if (size <= epsilon) continue;
        const authored = { x: (b.x - a.x) / size, y: (b.y - a.y) / size };
        result.set(wall.id, { origin: a, direction: authored, phase: 0, polygons: [] });
        const sign = authored.x < -epsilon || Math.abs(authored.x) <= epsilon && authored.y < 0 ? -1 : 1;
        const direction = { x: authored.x * sign, y: authored.y * sign };
        const key = JSON.stringify([wall.layerId ?? null, wall.assetId ?? null, wall.thickness,
            Math.round(direction.x / epsilon), Math.round(direction.y / epsilon), Math.round(cross(direction, a) / epsilon)]);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push({ wall, a, b, direction, from: Math.min(dot(a, direction), dot(b, direction)),
            to: Math.max(dot(a, direction), dot(b, direction)) });
    }
    for (const values of groups.values()) {
        values.sort((a, b) => a.from - b.from || a.to - b.to);
        let component = [], end = -Infinity;
        const flush = () => {
            if (component.length < 2) return;
            const head = component[0], origin = dot(head.a, head.direction) <= dot(head.b, head.direction) ? head.a : head.b;
            for (const entry of component) Object.assign(result.get(entry.wall.id), { origin, direction: head.direction });
        };
        for (const entry of values) {
            if (entry.from > end + epsilon) { flush(); component = []; end = -Infinity; }
            component.push(entry); end = Math.max(end, entry.to);
        }
        flush();
    }
    return result;
}

/** Map wall.id -> local polygons plus a shared collinear texture frame.
 * solidSpans uses {wall,x1,y1,x2,y2}, after the existing independent-door cuts.
 * Combine each entry's polygons into one nonzero path to avoid internal alpha overlap.
 */
export function wallJoinGeometry(document, solidSpans) {
    const result = frames(document), spans = [], nodes = new Map(), bins = new Map();
    let work = 0;
    const spend = () => { if (++work > maxWork) throw new RangeError('The map produces too many wall segments.'); };
    const layerKey = wall => wall.layerId ?? null;
    const blocked = (wall, p) => {
        if (!same(p, first(wall)) && !same(p, last(wall))) return true;
        for (const door of document.doors || []) {
            spend();
            const a = first(door), b = last(door), line = sub(b, a), size = Math.hypot(line.x, line.y);
            if (!size) continue;
            const source = sub(last(wall), first(wall)), sourceSize = Math.hypot(source.x, source.y);
            const sourceUnit = { x: source.x / sourceSize, y: source.y / sourceSize };
            if (Math.abs(cross(sub(a, first(wall)), sourceUnit)) > epsilon
                || Math.abs(cross(sub(b, first(wall)), sourceUnit)) > epsilon) continue;
            const unit = { x: line.x / size, y: line.y / size }, offset = sub(p, a), t = dot(offset, unit);
            if (Math.abs(cross(offset, unit)) <= epsilon && t >= -epsilon && t <= size + epsilon) return true;
        }
        return false;
    };
    const node = (p, wall) => {
        const key = `${layerKey(wall)}:${pointKey(p)}`;
        if (!nodes.has(key)) {
            const value = { p, layer: layerKey(wall), rays: [] };
            nodes.set(key, value);
            const bin = `${value.layer}:${Math.floor(p.x / binSize)}:${Math.floor(p.y / binSize)}`;
            if (!bins.has(bin)) bins.set(bin, []);
            bins.get(bin).push(value);
        }
        return nodes.get(key);
    };
    const occupied = new Map();
    for (const span of solidSpans) {
        spend();
        if (!result.has(span.wall.id)) continue;
        const a = first(span), b = last(span), size = Math.hypot(b.x - a.x, b.y - a.y);
        if (size <= epsilon) continue;
        const frame = result.get(span.wall.id), from = dot(sub(a, frame.origin), frame.direction), to = dot(sub(b, frame.origin), frame.direction);
        const low = Math.min(from, to), high = Math.max(from, to);
        const key = JSON.stringify([layerKey(span.wall), span.wall.assetId ?? null, span.wall.thickness,
            frame.origin, frame.direction]), known = occupied.get(key) || [], remaining = [];
        let cursor = low;
        for (const [left, right] of known) {
            spend();
            if (right <= cursor || left >= high) continue;
            if (left > cursor + epsilon) remaining.push([cursor, Math.min(left, high)]);
            cursor = Math.max(cursor, right);
        }
        if (cursor < high - epsilon) remaining.push([cursor, high]);
        const ranges = [...known, [low, high]].sort((one, two) => one[0] - two[0]), merged = [];
        for (const interval of ranges) {
            const previous = merged.at(-1);
            if (previous && interval[0] <= previous[1] + epsilon) previous[1] = Math.max(previous[1], interval[1]);
            else merged.push([...interval]);
        }
        occupied.set(key, merged);
        const hardA = blocked(span.wall, a), hardB = blocked(span.wall, b);
        for (const [left, right] of remaining) {
            const p = add(frame.origin, frame.direction, from <= to ? left : right), q = add(frame.origin, frame.direction, from <= to ? right : left);
            const hard = point => same(point, a) ? hardA : same(point, b) ? hardB : false;
            spans.push({ wall: span.wall, a: p, b: q, size: right - left,
                start: hard(p) ? null : node(p, span.wall), end: hard(q) ? null : node(q, span.wall) });
        }
    }
    const pieces = [];
    for (const span of spans) {
        const direction = { x: (span.b.x - span.a.x) / span.size, y: (span.b.y - span.a.y) / span.size };
        const splits = [{ t: 0, p: span.a, node: span.start }, { t: span.size, p: span.b, node: span.end }];
        for (let y = Math.floor(Math.min(span.a.y, span.b.y) / binSize); y <= Math.floor(Math.max(span.a.y, span.b.y) / binSize); y++)
            for (let x = Math.floor(Math.min(span.a.x, span.b.x) / binSize); x <= Math.floor(Math.max(span.a.x, span.b.x) / binSize); x++) {
                spend();
                for (const value of bins.get(`${layerKey(span.wall)}:${x}:${y}`) || []) {
                    spend();
                    const offset = sub(value.p, span.a), t = dot(offset, direction);
                    if (t > epsilon && t < span.size - epsilon && Math.abs(cross(offset, direction)) <= epsilon)
                        splits.push({ t, p: value.p, node: value });
                }
            }
        splits.sort((a, b) => a.t - b.t);
        for (let index = 1; index < splits.length; index++) {
            const a = splits[index - 1], b = splits[index];
            if (b.t - a.t <= epsilon) continue;
            const half = span.wall.thickness / 2, normal = { x: -direction.y * half, y: direction.x * half };
            const piece = { wall: span.wall, a: a.p, b: b.p, direction, half,
                al: add(a.p, normal), ar: add(a.p, normal, -1), bl: add(b.p, normal), br: add(b.p, normal, -1) };
            pieces.push(piece);
            if (a.node) a.node.rays.push({ piece, atStart: true, d: direction, half });
            if (b.node) b.node.rays.push({ piece, atStart: false, d: { x: -direction.x, y: -direction.y }, half });
        }
    }
    const polygons = new Map([...result.keys()].map(id => [id, []]));
    const put = (wall, points) => {
        let area = 0;
        for (let index = 0; index < points.length; index++) area += cross(points[index], points[(index + 1) % points.length]);
        if (Math.abs(area) > epsilon * epsilon) polygons.get(wall.id).push(area > 0 ? points : points.toReversed());
    };
    const corner = (ray, side, p) => {
        ray.piece[ray.atStart ? side === 'left' ? 'al' : 'ar' : side === 'left' ? 'br' : 'bl'] = p;
        ray[side] = p;
    };
    for (const value of nodes.values()) {
        const rays = value.rays.sort((a, b) => Math.atan2(a.d.y, a.d.x) - Math.atan2(b.d.y, b.d.x));
        if (rays.length < 2) continue;
        for (let index = 0; index < rays.length; index++) {
            spend();
            const a = rays[index], b = rays[(index + 1) % rays.length];
            const pa = add(value.p, { x: -a.d.y, y: a.d.x }, a.half), pb = add(value.p, { x: b.d.y, y: -b.d.x }, b.half);
            const denominator = cross(a.d, b.d);
            let joint = null;
            if (Math.abs(denominator) > epsilon) {
                const q = add(pa, a.d, cross(sub(pb, pa), b.d) / denominator);
                if (Math.hypot(q.x - value.p.x, q.y - value.p.y) <= 4 * Math.max(a.half, b.half)) joint = q;
            } else if (dot(a.d, b.d) < 0 && same(pa, pb)) joint = pa;
            if (joint) { corner(a, 'left', joint); corner(b, 'right', joint); }
            else {
                corner(a, 'left', pa); corner(b, 'right', pb);
                // Split the bevel in the overlap of both local texture strips.
                let low = 0, high = 1;
                for (const ray of [a, b]) {
                    const normal = { x: -ray.d.y, y: ray.d.x }, start = dot(sub(pa, value.p), normal), delta = dot(sub(pb, pa), normal);
                    if (Math.abs(delta) <= epsilon) continue;
                    const one = (-ray.half - start) / delta, two = (ray.half - start) / delta;
                    low = Math.max(low, Math.min(one, two)); high = Math.min(high, Math.max(one, two));
                }
                const middle = add(pa, sub(pb, pa), Math.max(0, Math.min(1, (low + high) / 2)));
                put(a.piece.wall, [value.p, pa, middle]); put(b.piece.wall, [value.p, middle, pb]);
            }
        }
        for (const ray of rays) put(ray.piece.wall, [value.p, ray.left, ray.right]);
    }
    for (const piece of pieces) put(piece.wall, [piece.al, piece.bl, piece.br, piece.ar]);
    for (const [id, values] of polygons) {
        const frame = result.get(id), normal = { x: -frame.direction.y, y: frame.direction.x };
        frame.polygons = values.map(points => points.map(p => { const offset = sub(p, frame.origin); return [dot(offset, frame.direction), dot(offset, normal)]; }));
    }
    return result;
}
