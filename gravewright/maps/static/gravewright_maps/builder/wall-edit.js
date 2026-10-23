/** Atomic wall-network edits on schema-three source; doors remain independent. */
import { collinearOverlap, length, objectKinds } from './model.js';
import { floorGeometryError } from './floor-geometry.js';
import { copyWallProperties, wallPropertiesKey } from './wall-properties.js';
import { documentBounds } from './document-bounds.js';

const epsilon = 1e-7;
const minimumLength = .1;
const failure = error => ({ ok: false, changed: false, refs: [], error });
const unchanged = () => ({ ok: true, changed: false, refs: [] });
const reference = wall => ({ kind: 'walls', id: wall.id });
const editable = layer => layer?.visible === true && layer.locked === false;
const finitePoint = point => point && Number.isFinite(point.x) && Number.isFinite(point.y);
const samePoint = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) <= epsilon;
const endpointPoint = (wall, endpoint) => ({ x: wall[`x${endpoint}`], y: wall[`y${endpoint}`] });
const wallError = 'Invalid wall geometry.';
const layerError = 'Choose a visible, unlocked layer before painting.';
const shortError = 'Wall endpoints must differ.';

function inspect(document) {
    if (document?.schemaVersion !== 3 || !Array.isArray(document.layers) || document.layers.length > 32
        || !Array.isArray(document.walls) || !Number.isInteger(document.columns) || document.columns < 1 || document.columns > 200
        || !Number.isInteger(document.rows) || document.rows < 1 || document.rows > 200
        || !Number.isInteger(document.cellSize) || document.cellSize < 16 || document.cellSize > 256) return null;
    const layers = new Map(), identifiers = new Set();
    for (const layer of document.layers) {
        if (!layer || typeof layer.id !== 'string' || !layer.id || layers.has(layer.id)
            || typeof layer.visible !== 'boolean' || typeof layer.locked !== 'boolean') return null;
        layers.set(layer.id, layer);
    }
    let count = 0;
    for (const kind of objectKinds) {
        if (kind in document && !Array.isArray(document[kind])) return null;
        for (const row of document[kind] || []) {
            if (!row || typeof row.id !== 'string' || !row.id || identifiers.has(row.id) || !layers.has(row.layerId) || ++count > 2000) return null;
            identifiers.add(row.id);
        }
    }
    if (document.walls.some(wall => !validWall(document, wall))) return null;
    return { layers, identifiers, count };
}
function inside(document, point) {
    const bounds = documentBounds(document);
    return finitePoint(point) && point.x >= 0 && point.y >= 0 && point.x <= bounds.width && point.y <= bounds.height;
}
function validWall(document, wall) {
    return inside(document, endpointPoint(wall, 1)) && inside(document, endpointPoint(wall, 2))
        && Number.isFinite(wall.thickness) && wall.thickness >= .05 && wall.thickness <= 2 && length(wall) >= minimumLength;
}
function limits(maxObjects) { return Number.isInteger(maxObjects) && maxObjects >= 1 && maxObjects <= 2000; }
function projection(wall, point) {
    const dx = wall.x2 - wall.x1, dy = wall.y2 - wall.y1;
    const t = Math.max(0, Math.min(1, ((point.x - wall.x1) * dx + (point.y - wall.y1) * dy) / (dx * dx + dy * dy)));
    const projected = t === 0 ? endpointPoint(wall, 1) : t === 1 ? endpointPoint(wall, 2)
        : { x: wall.x1 + dx * t, y: wall.y1 + dy * t };
    return { ...projected, offset: t * length(wall), distance: Math.hypot(projected.x - point.x, projected.y - point.y) };
}
function pointAt(wall, offset) {
    const size = length(wall);
    return offset === 0 ? endpointPoint(wall, 1) : offset === size ? endpointPoint(wall, 2)
        : { x: wall.x1 + (wall.x2 - wall.x1) * offset / size, y: wall.y1 + (wall.y2 - wall.y1) * offset / size };
}
function span(wall, from, to) {
    const start = pointAt(wall, from), end = pointAt(wall, to);
    return { ...wall, ...copyWallProperties(wall), x1: start.x, y1: start.y, x2: end.x, y2: end.y };
}
function splitParts(wall, offsets) {
    const size = length(wall), edges = [0];
    for (const offset of offsets.toSorted((a, b) => a - b)) {
        if (offset <= epsilon || offset >= size - epsilon || offset - edges.at(-1) <= epsilon) continue;
        edges.push(offset);
    }
    edges.push(size);
    const parts = [];
    for (let index = 1; index < edges.length; index++) {
        const part = span(wall, edges[index - 1], edges[index]);
        if (length(part) < minimumLength) return null;
        parts.push(part);
    }
    return parts;
}
function idAllocator(context, fragmentIds, makeId) {
    const occupied = new Set(context.identifiers), staged = new Map(fragmentIds);
    return {
        next(key, preferred) {
            const identifier = preferred ?? staged.get(key) ?? makeId();
            if (typeof identifier !== 'string' || !identifier || occupied.has(identifier)) return null;
            occupied.add(identifier);
            if (!preferred) staged.set(key, identifier);
            return identifier;
        },
        commit() { for (const [key, value] of staged) fragmentIds.set(key, value); },
    };
}
const fragmentKey = (wall, part, purpose) => JSON.stringify([purpose, wall.id ?? null, wall.layerId,
    wall.assetId ?? null, wall.thickness, wall.artwork !== false, wallPropertiesKey(wall), part.x1, part.y1, part.x2, part.y2]);
function commitWalls(document, walls, refs, allocator) {
    const error = floorGeometryError({ ...document, walls });
    if (error) return failure(error);
    document.walls = walls; allocator?.commit();
    return { ok: true, changed: true, refs };
}

/** Prefer a nearby endpoint, then an interior projection; otherwise retain free coordinates. */
export function snapWallPoint(document, point, { layerId, tolerance = .25, excludeIds = [] } = {}) {
    const original = { x: point?.x, y: point?.y, snapped: false }, context = inspect(document);
    if (!context || !finitePoint(point) || !Number.isFinite(tolerance) || tolerance < 0
        || !editable(context.layers.get(layerId)) || !(Array.isArray(excludeIds) || excludeIds instanceof Set)) return original;
    const excluded = new Set(excludeIds), walls = document.walls.filter(wall => wall.layerId === layerId && !excluded.has(wall.id));
    let closest = tolerance, result;
    for (const wall of walls) for (const endpoint of [1, 2]) {
        const candidate = endpointPoint(wall, endpoint), distance = Math.hypot(point.x - candidate.x, point.y - candidate.y);
        if (distance <= closest && (!result || distance < closest)) {
            closest = distance; result = { ...candidate, snapped: true, wallId: wall.id, endpoint };
        }
    }
    if (result) return result;
    closest = tolerance;
    for (const wall of walls) {
        const candidate = projection(wall, point);
        if (candidate.distance <= closest && (!result || candidate.distance < closest)) {
            closest = candidate.distance; result = { x: candidate.x, y: candidate.y, snapped: true, wallId: wall.id };
        }
    }
    return result || original;
}

/** Endpoint nodes are local to a layer, including joints between different wall materials. */
export function wallNodes(document, { layerId } = {}) {
    const context = inspect(document);
    if (!context) return [];
    const buckets = new Map(), nodes = [];
    for (const wall of document.walls) {
        if (layerId !== undefined && wall.layerId !== layerId || !editable(context.layers.get(wall.layerId))) continue;
        for (const endpoint of [1, 2]) {
            const point = endpointPoint(wall, endpoint), bx = Math.floor(point.x / epsilon), by = Math.floor(point.y / epsilon);
            let current;
            for (let y = by - 1; y <= by + 1; y++) for (let x = bx - 1; x <= bx + 1; x++) {
                const candidate = (buckets.get(`${wall.layerId}:${x}:${y}`) || []).find(node => samePoint(node, point));
                if (candidate && (!current || candidate.key < current.key)) current = candidate;
            }
            if (!current) {
                current = { key: `${wall.layerId}:${Math.round(point.x * 1e9) / 1e9}:${Math.round(point.y * 1e9) / 1e9}`,
                    x: point.x, y: point.y, ends: [] };
                const key = `${wall.layerId}:${bx}:${by}`;
                if (!buckets.has(key)) buckets.set(key, []);
                buckets.get(key).push(current); nodes.push(current);
            }
            current.ends.push({ wallId: wall.id, endpoint });
        }
    }
    return nodes;
}

/** Move every endpoint in a joint, or leave the complete source untouched. */
export function moveWallNode(document, nodeKey, point, { layerId } = {}) {
    const context = inspect(document);
    if (!context || typeof nodeKey !== 'string') return failure(wallError);
    const node = wallNodes(document, { layerId }).find(value => value.key === nodeKey);
    if (!node) return failure(layerError);
    if (!inside(document, point)) return failure('Keep objects inside the map.');
    if (samePoint(node, point)) return unchanged();
    const endpoints = new Map();
    for (const end of node.ends) {
        if (!endpoints.has(end.wallId)) endpoints.set(end.wallId, []);
        endpoints.get(end.wallId).push(end.endpoint);
    }
    const refs = [], walls = document.walls.map(wall => {
        if (!endpoints.has(wall.id)) return wall;
        const next = { ...wall };
        for (const endpoint of endpoints.get(wall.id)) { next[`x${endpoint}`] = point.x; next[`y${endpoint}`] = point.y; }
        refs.push(reference(next)); return next;
    });
    if (walls.some(wall => !validWall(document, wall))) return failure(shortError);
    return commitWalls(document, walls, refs);
}

/** Add only uncovered collinear spans, optionally joining new endpoints into existing segments. */
export function addWall(document, wall, { maxObjects = 2000, makeId = () => crypto.randomUUID(), fragmentIds = new Map(), connect = true } = {}) {
    const context = inspect(document);
    if (!context || !wall || !limits(maxObjects) || !(fragmentIds instanceof Map) || typeof makeId !== 'function'
        || typeof connect !== 'boolean') return failure(wallError);
    if (!editable(context.layers.get(wall.layerId))) return failure(layerError);
    if (!validWall(document, wall)) return failure(shortError);
    const size = length(wall), overlaps = [], propertiesKey = wallPropertiesKey(wall);
    for (const other of document.walls) if (other.layerId === wall.layerId && (other.assetId ?? null) === (wall.assetId ?? null)
        && other.thickness === wall.thickness && (other.artwork !== false) === (wall.artwork !== false) && wallPropertiesKey(other) === propertiesKey) {
        const overlap = collinearOverlap(wall, other);
        if (overlap) overlaps.push(overlap);
    }
    const intervals = [];
    let cursor = 0;
    for (const [from, to] of overlaps.sort((a, b) => a[0] - b[0])) {
        if (from > cursor + epsilon) intervals.push([cursor, from]);
        cursor = Math.max(cursor, to);
    }
    if (cursor < size - epsilon) intervals.push([cursor, size]);
    if (!intervals.length) return unchanged();
    const additions = intervals.map(([from, to]) => span(wall, from, to));
    if (additions.some(part => length(part) < minimumLength)) return failure(shortError);
    if (context.count + additions.length > maxObjects) return failure('This map has reached the object limit.');
    const attached = additions.flatMap(part => [endpointPoint(part, 1), endpointPoint(part, 2)]), split = new Map();
    let extra = additions.length;
    if (connect) for (const other of document.walls) if (other.layerId === wall.layerId) {
        const offsets = attached.map(point => projection(other, point)).filter(candidate => candidate.distance <= epsilon
            && candidate.offset > epsilon && candidate.offset < length(other) - epsilon)
            .map(candidate => candidate.offset);
        if (!offsets.length) continue;
        const parts = splitParts(other, offsets);
        if (!parts) return failure(shortError);
        if (parts.length > 1) { split.set(other.id, parts); extra += parts.length - 1; }
    }
    if (context.count + extra > maxObjects) return failure('This map has reached the object limit.');
    const allocator = idAllocator(context, fragmentIds, makeId), walls = [], refs = [];
    for (const other of document.walls) {
        const parts = split.get(other.id);
        if (!parts) { walls.push(other); continue; }
        for (const [index, part] of parts.entries()) {
            const id = index ? allocator.next(fragmentKey(other, part, 'join')) : other.id;
            if (!id) return failure(wallError);
            const next = { ...part, id }; walls.push(next); refs.push(reference(next));
        }
    }
    for (const [index, part] of additions.entries()) {
        const id = allocator.next(fragmentKey(wall, part, 'add'), index === 0 ? wall.id : undefined);
        if (!id) return failure(wallError);
        const next = { ...part, id }; walls.push(next); refs.push(reference(next));
    }
    return commitWalls(document, walls, refs, allocator);
}

/** Split only the selected wall; its first half retains its identity and authored art. */
export function splitWall(document, wallId, point, { maxObjects = 2000, makeId = () => crypto.randomUUID(),
    fragmentIds = new Map(), tolerance = .25 } = {}) {
    const context = inspect(document), wall = context && document.walls.find(value => value.id === wallId);
    if (!context || !wall || !limits(maxObjects) || !(fragmentIds instanceof Map) || typeof makeId !== 'function'
        || !inside(document, point) || !Number.isFinite(tolerance) || tolerance < 0) return failure(wallError);
    if (!editable(context.layers.get(wall.layerId))) return failure(layerError);
    const projected = projection(wall, point);
    if (projected.distance > tolerance) return failure(wallError);
    const parts = splitParts(wall, [projected.offset]);
    if (!parts) return failure(shortError);
    if (parts.length === 1) return unchanged();
    if (context.count + 1 > maxObjects) return failure('This map has reached the object limit.');
    const allocator = idAllocator(context, fragmentIds, makeId), id = allocator.next(fragmentKey(wall, parts[1], 'split'));
    if (!id) return failure(wallError);
    parts[0].id = wall.id; parts[1].id = id;
    return commitWalls(document, document.walls.flatMap(other => other.id === wall.id ? parts : [other]), parts.map(reference), allocator);
}

/** Start a distinct segment from either endpoint, retaining source material and thickness. */
export function extendWall(document, wallId, endpoint, point, options = {}) {
    const context = inspect(document), wall = context && document.walls.find(value => value.id === wallId);
    if (!context || !wall || ![1, 2].includes(endpoint) || !finitePoint(point)) return failure(wallError);
    if (!editable(context.layers.get(wall.layerId))) return failure(layerError);
    const start = endpointPoint(wall, endpoint);
    if (samePoint(start, point)) return unchanged();
    const addition = { id: options.id, layerId: wall.layerId, assetId: wall.assetId ?? null, thickness: wall.thickness,
        x1: start.x, y1: start.y, x2: point.x, y2: point.y, ...copyWallProperties(wall),
        ...(Object.hasOwn(wall, 'artwork') ? { artwork: wall.artwork } : {}) };
    return addWall(document, addition, options);
}
