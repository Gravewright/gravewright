/** Editable cell-space geometry. This module has no browser or scene dependency. */
import { sameDocument } from './asset-removal.js';
import { floorContainsPoint, floorShapeRings, floorFreeContours, floorShapeFromRings, cutFloorContours,
    floorGeometryError, floorIntersectsRectangle, floorShapeLimits, clipFloorRing, floorRegionHasArea,
    floorRegionCoveredBy } from './floor-geometry.js';
import { terrainBrushAlpha, terrainBrushLimits } from './terrain-brush.js';
import { expandTorchSelection, torchChildren, torchOwner, torchComponentState, torchSourcePoint } from './torch-model.js';
import { validateRegionGeometry } from './region-model.js';
import { upgradeBlueprint, validateBlueprintImageTargets } from './blueprint-model.js';
export { floorContainsPoint, floorShapeRings, floorFreeContours, floorShapeLimits } from './floor-geometry.js';

export const clone = value => structuredClone(value);
export const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
export const round = value => Math.round(value * 1000) / 1000;
export const length = wall => Math.hypot(wall.x2 - wall.x1, wall.y2 - wall.y1);
const geometryEpsilon = 1e-7;
export const objectKinds = Object.freeze(['floors', 'walls', 'doors', 'decorations', 'lights', 'particles', 'shaders', 'regions']);
const pointKinds = new Set(['lights', 'particles', 'shaders']);
const mapLimits = Object.freeze({ maxColumns: 200, maxRows: 200, minCellSize: 16, maxCellSize: 256, maxPixels: 16_777_216 });
const imageIdentifier = value => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
    && value.length === 36;
function mapGeometry(value, limits = {}) {
    const bounds = { ...mapLimits, ...limits };
    if (!Number.isInteger(value.columns) || value.columns < 1 || value.columns > bounds.maxColumns
        || !Number.isInteger(value.rows) || value.rows < 1 || value.rows > bounds.maxRows
        || !Number.isInteger(value.cellSize) || value.cellSize < bounds.minCellSize || value.cellSize > bounds.maxCellSize
        || value.columns * value.rows * value.cellSize ** 2 > bounds.maxPixels) throw new TypeError('Invalid map dimensions.');
    return { columns: value.columns, rows: value.rows, cellSize: value.cellSize };
}
/** Suggest a bounded grid while retaining the uploaded map's aspect ratio. */
export function readyMapGeometry(asset, cellSize = 70, limits = {}) {
    const bounds = { ...mapLimits, ...limits };
    if (![asset?.width, asset?.height].every(value => Number.isInteger(value) && value > 0)
        || !Number.isInteger(cellSize) || cellSize < bounds.minCellSize || cellSize > bounds.maxCellSize
        || !Number.isFinite(bounds.maxPixels) || bounds.maxPixels < cellSize ** 2) throw new TypeError('Invalid map image dimensions.');
    const scale = Math.min(1, bounds.maxColumns * cellSize / asset.width, bounds.maxRows * cellSize / asset.height,
        Math.sqrt(bounds.maxPixels / (asset.width * asset.height)));
    let columns = Math.max(1, Math.round(asset.width * scale / cellSize));
    let rows = Math.max(1, Math.round(asset.height * scale / cellSize));
    while (columns * rows * cellSize ** 2 > bounds.maxPixels) {
        if (columns > 1 && (rows === 1 || columns / asset.width >= rows / asset.height)) columns--;
        else rows--;
    }
    return mapGeometry({ columns, rows, cellSize }, bounds);
}
/** Apply one background/geometry edit atomically, preserving every authored object. */
export function setBackgroundImage(document, assetId, geometry = {}, limits = {}) {
    if (document.schemaVersion !== 3 || assetId !== null && !imageIdentifier(assetId)) throw new TypeError('Choose a map image.');
    const next = mapGeometry({ ...document, ...geometry }, limits), candidate = { ...document, ...next };
    if (!fitsBounds(candidate)) throw new TypeError('Objects would lie outside the map.');
    if (sameDocument(next, { columns: document.columns, rows: document.rows, cellSize: document.cellSize })
        && (assetId === null ? document.backgroundImage === undefined : document.backgroundImage?.assetId === assetId)) return false;
    Object.assign(document, next);
    if (assetId === null) delete document.backgroundImage; else document.backgroundImage = { assetId };
    return true;
}
/** An Empty Object has native object geometry and behavior, but never an image. */
export function createEmptyObject(document, { x, y, width = 1, height = 1, rotation = 0,
    layerId = document.layers?.[0]?.id, id = crypto.randomUUID(), name = 'Empty Object' } = {}) {
    const layer = document.layers?.find(row => row.id === layerId);
    if (document.schemaVersion !== 3 || !layer || layer.visible === false || layer.locked === true
        || ![x, y, width, height, rotation].every(Number.isFinite) || width < .05 || height < .05
        || Math.abs(rotation) > 36000 || typeof name !== 'string' || !name.trim() || Array.from(name).length > 120
        || name.includes('\0') || !imageIdentifier(id) || objectKinds.some(kind => document[kind]?.some(row => row.id === id))) throw new TypeError('Invalid Empty Object.');
    const item = { id, layerId, name: name.trim(), empty: true, assetId: null, x, y, width, height,
        rotation: (rotation % 360 + 360) % 360, lever: { state: 'off' } };
    if (!fitsBounds({ ...document, decorations: [item] })) throw new TypeError('Objects would lie outside the map.');
    return item;
}
export function defaultLayers() {
    return [{ id: '00000000-0000-4000-8000-000000000001', name: 'Base', visible: true, locked: false }];
}
export function newDocument(name = 'Untitled map', { layerName = 'Layer 1' } = {}) {
    return { schemaVersion: 3, name, columns: 40, rows: 30, cellSize: 70, background: '#253038',
        layers: [{ id: crypto.randomUUID(), name: layerName, visible: true, locked: false }],
        floors: [], walls: [], doors: [], decorations: [], lights: [], particles: [], shaders: [], regions: [], assets: [] };
}
/** An omitted mode keeps older projects byte-for-byte unchanged on opening. */
export function documentEditingMode(document) {
    return document.editingMode ?? 'tiles';
}
export function setEditingMode(document, mode) {
    if (document.schemaVersion !== 3 || !['tiles', 'paint'].includes(mode) || documentEditingMode(document) === mode) return false;
    document.editingMode = mode;
    return true;
}
/** Promotion is explicit; older sources retain their omitted flag. */
export function setDynamicSurface(document, kind, id, enabled) {
    const item = ['floors', 'walls'].includes(kind) && document[kind]?.find(row => row.id === id);
    if (document.schemaVersion !== 3 || !item || typeof enabled !== 'boolean'
        || enabled && item.brush?.operation === 'erase' || (item.dynamic === true) === enabled) return false;
    if (enabled) item.dynamic = true; else delete item.dynamic;
    return true;
}
export function normalizeFloorPaint(value = { color: null, opacity: 1 }) {
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length !== 2
        || !Object.hasOwn(value, 'color') || !Object.hasOwn(value, 'opacity')
        || !(value.color === null || typeof value.color === 'string' && /^#[0-9a-fA-F]{6}$/.test(value.color))
        || !Number.isFinite(value.opacity) || value.opacity < 0 || value.opacity > 1) throw new TypeError('Invalid floor paint.');
    return { color: value.color?.toLowerCase() ?? null, opacity: value.opacity };
}
const paintSignature = item => JSON.stringify([item.paint?.color?.toLowerCase() ?? null, item.paint?.opacity ?? 1]);
function floorMaterialMatches(item, assetId, rotation, paint) {
    return !item.brush && item.assetId === assetId && (item.rotation || 0) === rotation && paintSignature(item) === paintSignature({ paint });
}
function floorBrushMatches(assetIds, rotation, paint) {
    const eligible = new Set(assetIds), signature = paintSignature({ paint }), cache = new WeakMap();
    return item => {
        if (!cache.has(item)) cache.set(item, !item.brush && eligible.has(item.assetId ?? null) && (item.rotation || 0) === rotation && paintSignature(item) === signature);
        return cache.get(item);
    };
}
export function normalizeDocument(document) {
    const result = clone(document);
    if (![1, 2, 3].includes(result.schemaVersion)) throw new TypeError('Unsupported Map Builder document version.');
    for (const kind of objectKinds) for (const item of result[kind] || []) {
        if (Object.hasOwn(item, 'name') && (typeof item.name !== 'string' || !item.name.trim()
            || Array.from(item.name).length > 120 || item.name.includes('\0'))) throw new TypeError('Use a name with 1 to 120 characters.');
    }
    if (Object.hasOwn(result, 'backgroundImage') && (result.schemaVersion !== 3 || !result.backgroundImage
        || Object.keys(result.backgroundImage).length !== 1 || !imageIdentifier(result.backgroundImage.assetId))) throw new TypeError('Choose a map image.');
    for (const item of result.decorations || []) if (Object.hasOwn(item, 'empty')) {
        if (result.schemaVersion !== 3 || item.empty !== true || item.assetId !== null || item.torch
            || !item.lever || !['off', 'on'].includes(item.lever.state)) throw new TypeError('Invalid Empty Object.');
    }
    for (const kind of ['doors', 'decorations', 'regions']) for (const item of result[kind] || []) {
        if (item.blueprint) item.blueprint = upgradeBlueprint(item.blueprint);
        if (item.blueprint && item.empty === true) validateBlueprintImageTargets(item.blueprint, item);
    }
    if (result.editingMode !== undefined && (result.schemaVersion !== 3 || !['tiles', 'paint'].includes(result.editingMode)))
        throw new TypeError('Invalid map editing mode.');
    for (const kind of ['doors', 'decorations']) for (const item of result[kind] || []) {
        if (Object.hasOwn(item, 'interactionEnabled') && typeof item.interactionEnabled !== 'boolean') throw new TypeError('Invalid element interaction setting.');
    }
    for (const kind of ['floors', 'walls']) for (const item of result[kind] || []) {
        if (Object.hasOwn(item, 'dynamic') && (result.schemaVersion !== 3 || typeof item.dynamic !== 'boolean'
            || item.dynamic && item.brush?.operation === 'erase')) throw new TypeError('Invalid dynamic surface.');
    }
    // Keep omitted effect arrays omitted when opening earlier schema-three
    // projects. Saving without an edit must not introduce a document change.
    if (result.schemaVersion === 3) return result;
    if (result.schemaVersion === 1) result.doors = result.doors.map(door => {
        const wall = result.walls.find(item => item.id === door.wallId);
        const size = wall && length(wall);
        if (!size || !Number.isFinite(door.offset) || !Number.isFinite(door.width)) {
            throw new TypeError('The saved door geometry is invalid.');
        }
        const dx = (wall.x2 - wall.x1) / size, dy = (wall.y2 - wall.y1) / size;
        const end = Math.min(size, door.offset + door.width);
        return { id: door.id, assetId: door.assetId, ...(Object.hasOwn(door, 'name') ? { name: door.name } : {}),
            x1: clamp(wall.x1 + dx * door.offset, 0, result.columns), y1: clamp(wall.y1 + dy * door.offset, 0, result.rows),
            x2: clamp(wall.x1 + dx * end, 0, result.columns), y2: clamp(wall.y1 + dy * end, 0, result.rows),
            thickness: wall.thickness, state: door.state };
    });
    result.layers = defaultLayers();
    for (const kind of objectKinds.filter(kind => !['particles', 'shaders', 'regions'].includes(kind))) {
        result[kind] ??= [];
        for (const item of result[kind]) {
            item.layerId = result.layers[0].id;
            if (kind === 'floors') item.rotation = 0;
        }
    }
    result.schemaVersion = 3;
    return result;
}
export function familyAssetIds(document, role, familyName) {
    if (typeof familyName !== 'string' || !familyName) return [];
    return [...new Set((document.assets || []).filter(asset => asset.role === role && asset.family === familyName)
        .map(asset => asset.assetId))];
}
export function sampleAssetId(assetIds, random = Math.random) {
    if (!assetIds.length) return null;
    return assetIds[clamp(Math.floor(random() * assetIds.length), 0, assetIds.length - 1)];
}
/** Draw new walls on cell boundaries; disabling snap retains free segment geometry. */
export function snapWallSegment(document, start, end, { snap = true } = {}) {
    const coordinate = snap ? Math.round : round;
    const x1 = clamp(coordinate(start.x), 0, document.columns), y1 = clamp(coordinate(start.y), 0, document.rows);
    let x2 = clamp(coordinate(end.x), 0, document.columns), y2 = clamp(coordinate(end.y), 0, document.rows);
    if (snap) {
        if (Math.abs(end.x - x1) >= Math.abs(end.y - y1)) y2 = y1;
        else x2 = x1;
    }
    return { x1, y1, x2, y2 };
}
function floorGrid(document) {
    return Number.isInteger(document.columns) && document.columns > 0 && document.columns <= 200
        && Number.isInteger(document.rows) && document.rows > 0 && document.rows <= 200;
}
function finitePoint(point) {
    return point && Number.isFinite(point.x) && Number.isFinite(point.y);
}
function cellKey(cell) { return `${cell.x}:${cell.y}`; }
/** Enumerate a cell brush along the segment, including cells crossed between pointer events. */
export function floorBrushCells(document, start, end = start, size = 1, { shape = 'square', anchor = 'corner' } = {}) {
    if (!floorGrid(document) || !finitePoint(start) || !finitePoint(end) || !Number.isFinite(size)
        || !['square', 'circle'].includes(shape) || !['corner', 'center'].includes(anchor)) return [];
    size = clamp(Math.floor(size), 1, 200);
    const cells = new Map();
    function stamp(x, y) {
        const left = x - (anchor === 'center' ? Math.floor(size / 2) : 0);
        const top = y - (anchor === 'center' ? Math.floor(size / 2) : 0);
        const cx = left + size / 2, cy = top + size / 2;
        for (let row = Math.max(0, top); row < Math.min(document.rows, top + size); row++) {
            for (let column = Math.max(0, left); column < Math.min(document.columns, left + size); column++) {
                if (shape === 'circle' && Math.hypot(column + .5 - cx, row + .5 - cy) > size / 2 + geometryEpsilon) continue;
                const cell = { x: column, y: row }; cells.set(cellKey(cell), cell);
            }
        }
    }
    const sx = clamp(start.x, 0, document.columns - geometryEpsilon), sy = clamp(start.y, 0, document.rows - geometryEpsilon);
    const ex = clamp(end.x, 0, document.columns - geometryEpsilon), ey = clamp(end.y, 0, document.rows - geometryEpsilon);
    const dx = ex - sx, dy = ey - sy, stepX = Math.sign(dx), stepY = Math.sign(dy);
    let x = Math.floor(sx), y = Math.floor(sy);
    const lastX = Math.floor(ex), lastY = Math.floor(ey);
    const deltaX = dx ? 1 / Math.abs(dx) : Infinity, deltaY = dy ? 1 / Math.abs(dy) : Infinity;
    let nextX = dx ? (stepX > 0 ? x + 1 - sx : sx - x) / Math.abs(dx) : Infinity;
    let nextY = dy ? (stepY > 0 ? y + 1 - sy : sy - y) / Math.abs(dy) : Infinity;
    stamp(x, y);
    while (x !== lastX || y !== lastY) {
        // An endpoint exactly on a grid edge must not step past its destination cell.
        if (x === lastX) nextX = Infinity;
        if (y === lastY) nextY = Infinity;
        if (Math.abs(nextX - nextY) < 1e-12) {
            // Cover both sides of a grid corner, so fast diagonal strokes stay connected.
            stamp(x + stepX, y); stamp(x, y + stepY);
            x += stepX; y += stepY; nextX += deltaX; nextY += deltaY;
        } else if (nextX < nextY) { x += stepX; nextX += deltaX; }
        else { y += stepY; nextY += deltaY; }
        stamp(x, y);
    }
    return [...cells.values()];
}
export function floorRectangleCells(document, start, end = start, size = 1) {
    if (!floorGrid(document) || !finitePoint(start) || !finitePoint(end) || !Number.isFinite(size)) return [];
    const x = clamp(Math.floor(Math.min(start.x, end.x)), 0, document.columns - 1);
    const y = clamp(Math.floor(Math.min(start.y, end.y)), 0, document.rows - 1);
    const right = Math.min(document.columns, x + Math.max(1, Math.floor(size), Math.ceil(Math.max(start.x, end.x)) - x));
    const bottom = Math.min(document.rows, y + Math.max(1, Math.floor(size), Math.ceil(Math.max(start.y, end.y)) - y));
    const cells = [];
    for (let row = y; row < bottom; row++) for (let column = x; column < right; column++) cells.push({ x: column, y: row });
    return cells;
}
/** The initial point is the center; the current point defines the radius in cells. */
export function floorCircleCells(document, start, end) {
    if (!floorGrid(document) || !finitePoint(start) || !finitePoint(end)) return [];
    const radius = Math.hypot(end.x - start.x, end.y - start.y), cells = [];
    if (!Number.isFinite(radius)) return [];
    const left = Math.max(0, Math.floor(start.x - radius)), right = Math.min(document.columns, Math.ceil(start.x + radius));
    const top = Math.max(0, Math.floor(start.y - radius)), bottom = Math.min(document.rows, Math.ceil(start.y + radius));
    for (let y = top; y < bottom; y++) for (let x = left; x < right; x++) {
        if (Math.hypot(x + .5 - start.x, y + .5 - start.y) <= radius + geometryEpsilon) cells.push({ x, y });
    }
    return cells.length ? cells : floorBrushCells(document, start);
}
export function floorPolygonCells(document, points) {
    if (!floorGrid(document) || !Array.isArray(points) || points.length < 3 || points.length > 2000
        || !points.every(finitePoint)) return [];
    const area = points.reduce((sum, point, index) => {
        const next = points[(index + 1) % points.length];
        return sum + point.x * next.y - next.x * point.y;
    }, 0);
    if (Math.abs(area) <= geometryEpsilon) return [];
    const cells = [], left = Math.max(0, Math.floor(Math.min(...points.map(point => point.x))));
    const right = Math.min(document.columns, Math.ceil(Math.max(...points.map(point => point.x))));
    const top = Math.max(0, Math.floor(Math.min(...points.map(point => point.y))));
    const bottom = Math.min(document.rows, Math.ceil(Math.max(...points.map(point => point.y))));
    function contains(x, y) {
        let inside = false;
        for (let index = 0, previous = points.length - 1; index < points.length; previous = index++) {
            const a = points[previous], b = points[index], cross = (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x);
            if (Math.abs(cross) <= geometryEpsilon && x >= Math.min(a.x, b.x) && x <= Math.max(a.x, b.x)
                && y >= Math.min(a.y, b.y) && y <= Math.max(a.y, b.y)) return true;
            if ((a.y > y) !== (b.y > y) && x < (b.x - a.x) * (y - a.y) / (b.y - a.y) + a.x) inside = !inside;
        }
        return inside;
    }
    for (let y = top; y < bottom; y++) for (let x = left; x < right; x++) if (contains(x + .5, y + .5)) cells.push({ x, y });
    return cells;
}
function paintRows(cells) {
    const rows = new Map();
    for (const { x, y } of cells) {
        if (!rows.has(y)) rows.set(y, []);
        rows.get(y).push(x);
    }
    for (const [y, columns] of rows) {
        const intervals = [];
        for (const x of columns.sort((a, b) => a - b)) {
            const previous = intervals.at(-1);
            if (previous && previous[1] === x) previous[1] = x + 1;
            else intervals.push([x, x + 1]);
        }
        rows.set(y, intervals);
    }
    return rows;
}
function cellContours(rows) {
    const pieces = [], previous = new Map();
    for (const [y, intervals] of [...rows].sort(([a], [b]) => a - b)) {
        const current = new Map();
        for (const [x, right] of intervals) {
            const key = `${x}:${right}`, last = previous.get(key);
            const piece = last && last.y + last.height === y ? last : { x, y, width: right - x, height: 0 };
            piece.height++; if (piece !== last) pieces.push(piece); current.set(key, piece);
        }
        previous.clear(); for (const [key, piece] of current) previous.set(key, piece);
    }
    return pieces.map(item => [[item.x, item.y], [item.x + item.width, item.y],
        [item.x + item.width, item.y + item.height], [item.x, item.y + item.height]]);
}
function floorRemainders(item, rows, strict = false, contours) {
    const maskedRemainder = () => {
        const result = cutFloorContours(item, contours || cellContours(rows));
        return result === item ? null : result ? [result] : [];
    };
    if (item.shape || item.brush) return maskedRemainder();
    const right = item.x + item.width, bottom = item.y + item.height, cuts = new Set([item.y, bottom]);
    let overlaps = false;
    for (const [y, intervals] of rows) {
        if (y >= bottom || y + 1 <= item.y || !intervals.some(([a, b]) => a < right && b > item.x)) continue;
        overlaps = true; cuts.add(Math.max(item.y, y)); cuts.add(Math.min(bottom, y + 1));
    }
    if (!overlaps) return null;
    const edges = [...cuts].sort((a, b) => a - b), pieces = [];
    let previous = new Map();
    for (let index = 1; index < edges.length; index++) {
        const y = edges[index - 1], height = edges[index] - y, intervals = rows.get(Math.floor(y + height / 2)) || [];
        let cursor = item.x;
        const spans = [];
        for (const [a, b] of intervals) {
            if (b <= cursor || a >= right) continue;
            if (a > cursor) spans.push([cursor, Math.min(a, right)]);
            cursor = Math.max(cursor, Math.min(b, right));
        }
        if (cursor < right) spans.push([cursor, right]);
        const current = new Map();
        for (const [x, end] of spans) {
            const key = `${x}:${end}`;
            let piece = previous.get(key);
            if (piece && Math.abs(piece.y + piece.height - y) <= geometryEpsilon) piece.height += height;
            else { piece = { ...item, x, y, width: end - x, height }; pieces.push(piece); }
            current.set(key, piece);
        }
        previous = current;
    }
    // A vector cut keeps tiny authored slivers without leaving backing under the new tile.
    if (pieces.some(piece => piece.width < .05 || piece.height < .05)) return strict ? false : maskedRemainder();
    return pieces;
}
function matchingFloorCells(document, active, matches) {
    const tiles = new Map(), bins = new Map(), binSize = 8;
    for (const [index, item] of active.entries()) {
        if (item.paint?.opacity === 0) continue;
        const entry = { item, index };
        if (!item.shape && !item.brush && Number.isInteger(item.x) && Number.isInteger(item.y) && item.width === 1 && item.height === 1) {
            tiles.set(cellKey(item), entry); continue;
        }
        const left = Math.max(0, Math.floor(item.x / binSize)), top = Math.max(0, Math.floor(item.y / binSize));
        const right = Math.min(Math.ceil(document.columns / binSize), Math.ceil((item.x + item.width) / binSize));
        const bottom = Math.min(Math.ceil(document.rows / binSize), Math.ceil((item.y + item.height) / binSize));
        for (let y = top; y < bottom; y++) for (let x = left; x < right; x++) {
            const key = `${x}:${y}`;
            if (!bins.has(key)) bins.set(key, []);
            bins.get(key).push(entry);
        }
    }
    return cell => {
        const tile = tiles.get(cellKey(cell)), candidates = tile ? [tile.item] : [];
        for (const entry of bins.get(`${Math.floor(cell.x / binSize)}:${Math.floor(cell.y / binSize)}`) || []) {
            const item = entry.item;
            if ((!tile || entry.index > tile.index) && item.x < cell.x + 1 && item.x + item.width > cell.x
                && item.y < cell.y + 1 && item.y + item.height > cell.y) candidates.push(item);
        }
        if (!candidates.length) return false;
        const top = candidates.at(-1);
        if (!top.shape && !top.brush && top.x <= cell.x && top.y <= cell.y && top.x + top.width >= cell.x + 1 && top.y + top.height >= cell.y + 1)
            return matches(top);
        return floorRegionCoveredBy([[[cell.x, cell.y], [cell.x + 1, cell.y], [cell.x + 1, cell.y + 1], [cell.x, cell.y + 1]]], candidates, matches);
    };
}
function fragmentId(item, piece, index, ids, makeId) {
    if (!index) return item.id;
    const key = JSON.stringify([item.id, piece.x, piece.y, piece.width, piece.height]);
    if (!ids.has(key)) ids.set(key, makeId());
    return ids.get(key);
}
function floorLayer(document, layerId) {
    const layer = document.layers?.find(value => value.id === layerId);
    return layer && layer.visible !== false && !layer.locked ? layer : null;
}
/** Read the topmost floor on the active layer without exposing mutable source data. */
export function sampleFloor(document, point, { layerId } = {}) {
    if (!floorGrid(document) || !finitePoint(point) || !floorLayer(document, layerId)
        || point.x < 0 || point.y < 0 || point.x >= document.columns || point.y >= document.rows) return null;
    let remaining = 1;
    for (let index = (document.floors || []).length - 1; index >= 0; index--) {
        const item = document.floors[index];
        if ((item.layerId || document.layers[0].id) !== layerId || item.paint?.opacity === 0 || !floorContainsPoint(item, point)) continue;
        const alpha = terrainBrushAlpha(item, point) * (item.paint?.opacity ?? 1);
        if (item.brush?.operation === 'erase') {
            remaining *= 1 - alpha;
            if (!remaining) return null;
        } else if (alpha * remaining >= .5 / 255) return clone(item);
    }
    return null;
}
/** Four-neighbor bucket area, comparing the topmost floor family/material and texture rotation. */
export function floodFloorCells(document, point, { layerId } = {}) {
    if (!floorGrid(document) || !finitePoint(point) || !floorLayer(document, layerId)
        || point.x < 0 || point.y < 0 || point.x >= document.columns || point.y >= document.rows) return [];
    const { columns, rows } = document, grid = new Uint16Array(columns * rows), signatures = new Map();
    const families = new Map((document.assets || []).filter(asset => asset.role === 'floor' && typeof asset.family === 'string' && asset.family)
        .map(asset => [asset.assetId, asset.family]));
    for (const item of document.floors || []) {
        if ((item.layerId || document.layers[0].id) !== layerId) continue;
        if (item.paint?.opacity === 0) continue;
        const signature = JSON.stringify([families.has(item.assetId) ? ['family', families.get(item.assetId)] : ['asset', item.assetId ?? null],
            item.rotation || 0, paintSignature(item)]);
        if (!signatures.has(signature)) signatures.set(signature, signatures.size + 1);
        const left = Math.max(0, Math.ceil(item.x - .5)), right = Math.min(columns, Math.ceil(item.x + item.width - .5));
        const top = Math.max(0, Math.ceil(item.y - .5)), bottom = Math.min(rows, Math.ceil(item.y + item.height - .5));
        for (let y = top; y < bottom; y++) {
            if (!item.shape && !item.brush) grid.fill(signatures.get(signature), y * columns + left, y * columns + right);
            else for (let x = left; x < right; x++) if (floorContainsPoint(item, { x: x + .5, y: y + .5 })) {
                if (item.brush?.operation !== 'erase') grid[y * columns + x] = signatures.get(signature);
                else if (terrainBrushAlpha(item, { x: x + .5, y: y + .5 }) * (item.paint?.opacity ?? 1) === 1) grid[y * columns + x] = 0;
            }
        }
    }
    const first = Math.floor(point.y) * columns + Math.floor(point.x), target = grid[first];
    const visited = new Uint8Array(grid.length), queue = [first], cells = [];
    visited[first] = 1;
    for (let index = 0; index < queue.length; index++) {
        const offset = queue[index], x = offset % columns, y = Math.floor(offset / columns);
        cells.push({ x, y });
        for (const next of [x > 0 ? offset - 1 : -1, x + 1 < columns ? offset + 1 : -1,
            y > 0 ? offset - columns : -1, y + 1 < rows ? offset + columns : -1]) {
            if (next < 0 || visited[next] || grid[next] !== target) continue;
            visited[next] = 1; queue.push(next);
        }
    }
    return cells;
}
/** Erase cell areas atomically, preserving all content outside the active layer. */
export function eraseFloorCells(document, cells, { layerId, maxObjects = 2000, fragmentIds = new Map(),
    makeId = () => crypto.randomUUID() } = {}) {
    const failure = error => ({ ok: false, changed: false, error });
    if (!floorGrid(document) || !Array.isArray(cells) || !Number.isInteger(maxObjects) || maxObjects < 1 || maxObjects > 2000)
        return failure('Invalid floor erase area.');
    if (!floorLayer(document, layerId)) return failure('Choose a visible, unlocked layer before painting.');
    const unique = new Map();
    for (const cell of cells) {
        if (!cell || !Number.isInteger(cell.x) || !Number.isInteger(cell.y) || cell.x < 0 || cell.y < 0
            || cell.x >= document.columns || cell.y >= document.rows) return failure('Invalid floor erase area.');
        unique.set(cellKey(cell), cell);
    }
    if (!unique.size) return { ok: true, changed: false };
    const countOther = objectKinds.filter(kind => kind !== 'floors').reduce((sum, kind) => sum + (document[kind]?.length || 0), 0);
    const rows = paintRows(unique.values()), contours = cellContours(rows), floors = [], ids = new Map(fragmentIds);
    let changed = false;
    for (const item of document.floors || []) {
        const pieces = (item.layerId || document.layers[0].id) === layerId ? floorRemainders(item, rows, true, contours) : null;
        if (pieces === false) return failure('This erase would leave a floor fragment smaller than 0.05 cells.');
        if (pieces === null) floors.push(item);
        else { changed = true; pieces.forEach((piece, index) => floors.push({ ...piece, id: fragmentId(item, piece, index, ids, makeId) })); }
        if (countOther + floors.length > maxObjects) return failure('This map has reached the object limit.');
    }
    if (countOther + floors.length > maxObjects) return failure('This map has reached the object limit.');
    const error = floors.some(item => item.shape) && floorGeometryError(document, floors);
    if (error) return failure(error);
    if (changed) {
        document.floors = floors;
        for (const [key, value] of ids) fragmentIds.set(key, value);
    }
    return { ok: true, changed };
}
/** Apply concrete tile choices atomically; callers retain choices across gesture previews. */
export function paintFloorCells(document, cells, { layerId, assetIds = [null], rotation = 0, choices = new Map(),
    random = Math.random, maxObjects = 2000, fragmentIds = new Map(), onError, makeId = () => crypto.randomUUID() } = {}) {
    if (!floorGrid(document) || !Array.isArray(cells) || !assetIds.length || ![0, 90, 180, 270].includes(rotation)
        || !Number.isInteger(maxObjects) || maxObjects < 1 || maxObjects > 2000) return false;
    const layer = document.layers?.find(value => value.id === layerId);
    if (!layer || layer.locked || layer.visible === false) return false;
    const unique = new Map();
    for (const cell of cells) {
        if (!cell || !Number.isInteger(cell.x) || !Number.isInteger(cell.y) || cell.x < 0 || cell.y < 0
            || cell.x >= document.columns || cell.y >= document.rows) return false;
        unique.set(cellKey(cell), cell);
    }
    if (!unique.size) return false;
    const active = (document.floors || []).filter(item => (item.layerId || document.layers[0].id) === layerId);
    const matches = floorBrushMatches(assetIds, rotation);
    if (active.some(matches)) {
        const covered = matchingFloorCells(document, active, matches);
        try { for (const [key, cell] of unique) if (covered(cell)) unique.delete(key); }
        catch (cause) {
            if (!(cause instanceof RangeError) || cause.message !== 'The map floor shapes are too complex.') throw cause;
            onError?.(cause.message); return false;
        }
    }
    if (!unique.size) return true;
    if (unique.size > maxObjects) return false;
    const countOther = objectKinds.filter(kind => kind !== 'floors').reduce((sum, kind) => sum + (document[kind]?.length || 0), 0);
    if (countOther + unique.size > maxObjects) return false;
    const rows = paintRows(unique.values()), contours = cellContours(rows), floors = [], ids = new Map(fragmentIds);
    for (const item of document.floors || []) {
        const pieces = (item.layerId || document.layers[0].id) === layerId ? floorRemainders(item, rows, false, contours) : null;
        if (pieces === null) floors.push(item);
        else pieces.forEach((piece, index) => floors.push({ ...piece, id: fragmentId(item, piece, index, ids, makeId) }));
        if (countOther + floors.length + unique.size > maxObjects) return false;
    }
    const additions = new Map();
    for (const [key, cell] of unique) {
        const choice = choices.get(key) || { id: makeId(), assetId: sampleAssetId(assetIds, random) };
        additions.set(key, choice);
        floors.push({ id: choice.id, layerId, assetId: choice.assetId, ...cell, width: 1, height: 1, rotation });
    }
    const geometryError = floors.some(item => item.shape) && floorGeometryError(document, floors);
    if (geometryError) { onError?.(geometryError); return false; }
    document.floors = floors;
    for (const [key, value] of ids) fragmentIds.set(key, value);
    for (const [key, choice] of additions) choices.set(key, choice);
    return true;
}
/** Paint/erase exact continuous contours in one atomic, bounded operation. */
export function applyFloorContours(document, contours, { layerId, operation = 'paint', assetIds = [null], rotation = 0,
    editingMode = documentEditingMode(document), paint, choices = new Map(), random = Math.random,
    maxObjects = 2000, makeId = () => crypto.randomUUID() } = {}) {
    const failure = error => ({ ok: false, changed: false, refs: [], error });
    if (!floorGrid(document) || !floorLayer(document, layerId)) return failure('Choose a visible, unlocked layer before painting.');
    if (!Array.isArray(contours) || !['paint', 'erase'].includes(operation) || !assetIds.length || ![0, 90, 180, 270].includes(rotation)
        || !Number.isInteger(maxObjects) || maxObjects < 1 || maxObjects > 2000) return failure('Invalid floor shape.');
    if (!['tiles', 'paint'].includes(editingMode)) return failure('Invalid map editing mode.');
    let profile;
    if (editingMode === 'paint' && operation === 'paint') {
        try { profile = normalizeFloorPaint(paint); } catch (cause) { return failure(cause.message); }
        if (profile.opacity === 0) return { ok: true, changed: false, refs: [] };
    }
    if (contours.length > floorShapeLimits.rings || contours.reduce((sum, ring) => sum + (ring?.length || 0), 0) > floorShapeLimits.points
        || contours.some(ring => !Array.isArray(ring) || ring.length > floorShapeLimits.vertices
            || !ring.every(point => Array.isArray(point) && point.length === 2 && point.every(Number.isFinite)))) return failure('The map floor shapes are too complex.');
    const bounds = { x: 0, y: 0, width: document.columns, height: document.rows };
    contours = contours.map(ring => clipFloorRing(ring, bounds)).filter(ring => ring.length);
    const geometry = floorShapeFromRings(contours);
    if (!geometry || !floorRegionHasArea(contours)) return { ok: true, changed: false, refs: [] };
    if (operation === 'paint' && editingMode === 'tiles') {
        const active = (document.floors || []).filter(item => (item.layerId || document.layers[0].id) === layerId);
        const matches = floorBrushMatches(assetIds, rotation);
        try {
            if (active.some(matches) && floorRegionCoveredBy(contours, active, matches))
                return { ok: true, changed: false, refs: [] };
        } catch (cause) {
            if (!(cause instanceof RangeError) || cause.message !== 'The map floor shapes are too complex.') throw cause;
            return failure(cause.message);
        }
    }
    const choice = operation === 'paint' ? choices.get('free') || { id: makeId(), assetId: profile?.color ? null : sampleAssetId(assetIds, random) } : null;
    if (choice && editingMode === 'paint' && profile.opacity === 1 && (profile.color !== null || choice.assetId === null)) {
        const active = (document.floors || []).filter(item => (item.layerId || document.layers[0].id) === layerId);
        // A stroke entirely on one visible material should not allocate a new
        // floor or erase hidden backing merely because the pointer moved.
        for (let index = active.length - 1; index >= 0; index--) {
            const item = active[index];
            if (!floorMaterialMatches(item, choice.assetId, rotation, profile)) continue;
            if (floorRegionHasArea(contours, floorShapeRings(item))
                || floorRegionHasArea(contours, [], floorShapeRings(item, 'cuts'))) continue;
            if (active.slice(index + 1).some(above => !floorMaterialMatches(above, choice.assetId, rotation, profile)
                && floorRegionHasArea(floorShapeRings(above), floorShapeRings(above, 'cuts'), contours))) continue;
            choices.set('free', choice);
            return { ok: true, changed: false, refs: [] };
        }
    }
    const floors = [];
    let changed = false;
    for (const item of document.floors || []) {
        const next = (operation === 'erase' || editingMode !== 'paint') && (item.layerId || document.layers[0].id) === layerId
            ? cutFloorContours(item, contours) : item;
        if (next !== item) changed = true;
        if (next) floors.push(next);
    }
    if (operation === 'paint') {
        floors.push({ id: choice.id, layerId, assetId: choice.assetId, ...geometry, rotation, ...(profile ? { paint: profile } : {}) }); changed = true;
    }
    if (!changed) return { ok: true, changed: false, refs: [] };
    const countOther = objectKinds.filter(kind => kind !== 'floors').reduce((sum, kind) => sum + (document[kind]?.length || 0), 0);
    if (countOther + floors.length > maxObjects) return failure('This map has reached the object limit.');
    const error = floorGeometryError(document, floors);
    if (error) return failure(error);
    document.floors = floors;
    if (choice) choices.set('free', choice);
    return { ok: true, changed: true, refs: choice ? [{ kind: 'floors', id: choice.id }] : [] };
}
/** Without snapping, the bucket recolors the clicked shape without changing its geometry. */
export function fillFloorShape(document, point, { layerId, assetIds = [null], rotation = 0, editingMode = documentEditingMode(document),
    paint, choices = new Map(), random = Math.random } = {}) {
    const item = sampleFloor(document, point, { layerId });
    if (!item) return { ok: false, changed: false, refs: [], error: 'Choose a painted floor to fill without grid snapping.' };
    if (!assetIds.length || ![0, 90, 180, 270].includes(rotation)) return { ok: false, changed: false, refs: [], error: 'Invalid floor shape.' };
    if (!['tiles', 'paint'].includes(editingMode)) return { ok: false, changed: false, refs: [], error: 'Invalid map editing mode.' };
    let profile;
    if (editingMode === 'paint') {
        try { profile = normalizeFloorPaint(paint); } catch (cause) { return { ok: false, changed: false, refs: [], error: cause.message }; }
    }
    if (editingMode === 'tiles' && floorBrushMatches(assetIds, rotation)(item)) return { ok: true, changed: false, refs: [{ kind: 'floors', id: item.id }] };
    const choice = choices.get('fill') || { assetId: profile?.color ? null : sampleAssetId(assetIds, random) };
    const replacement = { ...item, assetId: choice.assetId, rotation };
    if (profile) replacement.paint = profile; else delete replacement.paint;
    const changed = JSON.stringify(item) !== JSON.stringify(replacement);
    if (changed) {
        const floors = document.floors.map(value => value.id === item.id ? replacement : value);
        const error = floorGeometryError(document, floors);
        if (error) return { ok: false, changed: false, refs: [], error };
        const target = document.floors.find(value => value.id === item.id);
        target.assetId = choice.assetId; target.rotation = rotation;
        if (profile) target.paint = profile; else delete target.paint;
    }
    choices.set('fill', choice);
    return { ok: true, changed, refs: [{ kind: 'floors', id: item.id }] };
}
/** Append one radial paint/erase operator. Earlier rows stay intact for layer compositing. */
export function applyTerrainStroke(document, points, { layerId, size = 1, hardness = .5, intensity = 1, operation = 'paint',
    assetIds = [null], rotation = 0, paint, choices = new Map(), random = Math.random,
    maxObjects = 2000, makeId = () => crypto.randomUUID() } = {}) {
    const failure = error => ({ ok: false, changed: false, refs: [], error });
    if (document?.schemaVersion !== 3 || !Array.isArray(document.layers) || !Array.isArray(document.floors)
        || objectKinds.some(kind => kind in document && !Array.isArray(document[kind]))
        || !floorGrid(document) || !floorLayer(document, layerId))
        return failure('Choose a visible, unlocked layer before painting.');
    if (!Array.isArray(points) || !Number.isFinite(size) || size < .05 || size > 20
        || !Number.isFinite(hardness) || hardness < 0 || hardness > 1 || !Number.isFinite(intensity) || intensity < 0 || intensity > 1
        || !['paint', 'erase'].includes(operation) || !Array.isArray(assetIds) || !assetIds.length
        || ![0, 90, 180, 270].includes(rotation) || !(choices instanceof Map)
        || !Number.isInteger(maxObjects) || maxObjects < 1 || maxObjects > 2000 || typeof makeId !== 'function') return failure('Invalid floor brush.');
    if (points.length > terrainBrushLimits.dabs) return failure('The map has too many terrain brush dabs.');
    if (points.some(point => !finitePoint(point))) return failure('Invalid floor brush.');
    if (!points.length || intensity < .5 / 255) return { ok: true, changed: false, refs: [] };
    let profile;
    if (paint !== undefined) {
        try { profile = normalizeFloorPaint(paint); } catch (cause) { return failure(cause.message); }
        if (profile.opacity === 0) return { ok: true, changed: false, refs: [] };
    }
    const radius = size / 2, stamps = points.map(point => ({ x: clamp(point.x, 0, document.columns), y: clamp(point.y, 0, document.rows) }));
    let left = document.columns, top = document.rows, right = 0, bottom = 0;
    for (const point of stamps) {
        left = Math.min(left, point.x - radius); top = Math.min(top, point.y - radius);
        right = Math.max(right, point.x + radius); bottom = Math.max(bottom, point.y + radius);
    }
    left = Math.max(0, left); top = Math.max(0, top); right = Math.min(document.columns, right); bottom = Math.min(document.rows, bottom);
    const width = right - left, height = bottom - top;
    if (width < terrainBrushLimits.minSize || height < terrainBrushLimits.minSize) return { ok: true, changed: false, refs: [] };
    if (operation === 'erase' && !(document.floors || []).some(item => item.layerId === layerId
        && item.brush?.operation !== 'erase' && item.paint?.opacity !== 0
        && item.x < right && item.y < bottom && item.x + item.width > left && item.y + item.height > top))
        return { ok: true, changed: false, refs: [] };
    const count = objectKinds.reduce((sum, kind) => sum + (document[kind]?.length || 0), 0);
    if (count >= maxObjects) return failure('This map has reached the object limit.');
    const cached = choices.get('terrain'), identifiers = new Set(objectKinds.flatMap(kind => (document[kind] || []).map(item => item.id)));
    const choice = cached || { id: makeId(), assetId: operation === 'erase' || profile?.color ? null : sampleAssetId(assetIds, random) };
    if (typeof choice.id !== 'string' || !choice.id || identifiers.has(choice.id)) return failure('Invalid floor brush.');
    const local = value => Math.max(0, Math.min(1, value));
    const brush = { operation, points: stamps.map(point => [local((point.x - left) / width), local((point.y - top) / height), intensity]),
        radius: [radius / width, radius / height], hardness };
    const row = { id: choice.id, layerId, assetId: operation === 'erase' ? null : choice.assetId,
        x: left, y: top, width, height, rotation, brush, ...(profile ? { paint: profile } : {}) };
    const floors = [...document.floors || [], row], error = floorGeometryError(document, floors);
    if (error) return failure(error);
    document.floors = floors; choices.set('terrain', choice);
    return { ok: true, changed: true, refs: [{ kind: 'floors', id: row.id }] };
}
export function projectPoint(wall, point) {
    const dx = wall.x2 - wall.x1, dy = wall.y2 - wall.y1, size = length(wall);
    if (!size) return { distance: Infinity, offset: 0 };
    const offset = clamp(((point.x - wall.x1) * dx + (point.y - wall.y1) * dy) / size, 0, size);
    const x = wall.x1 + dx * offset / size, y = wall.y1 + dy * offset / size;
    return { x, y, offset, distance: Math.hypot(point.x - x, point.y - y) };
}
export function nearestWall(document, point, tolerance = .5) {
    let result;
    for (const wall of document.walls) {
        const projection = projectPoint(wall, point);
        if (projection.distance <= tolerance && (!result || projection.distance < result.distance)) result = { wall, ...projection };
    }
    return result;
}
export function collinearOverlap(base, other) {
    const size = length(base);
    if (!size) return undefined;
    const dx = (base.x2 - base.x1) / size, dy = (base.y2 - base.y1) / size;
    const project = (x, y) => ({ offset: (x - base.x1) * dx + (y - base.y1) * dy,
        distance: Math.abs((x - base.x1) * dy - (y - base.y1) * dx) });
    const start = project(other.x1, other.y1), end = project(other.x2, other.y2);
    if (start.distance > geometryEpsilon || end.distance > geometryEpsilon) return undefined;
    const from = clamp(Math.min(start.offset, end.offset), 0, size), to = clamp(Math.max(start.offset, end.offset), 0, size);
    return to - from > geometryEpsilon ? [from, to] : undefined;
}
export function doorFits(document, door, ignoreId = door.id) {
    if (!['x1', 'y1', 'x2', 'y2', 'thickness'].every(key => Number.isFinite(door[key]))
        || length(door) < .25 - geometryEpsilon || length(door) > 20 + geometryEpsilon || door.thickness < .05 || door.thickness > 2
        || !segmentFitsBounds(document, door)) return false;
    return !document.doors.some(item => item.id !== ignoreId && collinearOverlap(door, item));
}
export function doorSegment(_document, door) {
    return { x1: door.x1, y1: door.y1, x2: door.x2, y2: door.y2,
        angle: Math.atan2(door.y2 - door.y1, door.x2 - door.x1) * 180 / Math.PI, thickness: door.thickness };
}
export function wallSegments(document, wall) {
    const size = length(wall), pieces = [];
    if (!size) return pieces;
    const openings = document.doors.map(door => collinearOverlap(wall, door)).filter(Boolean).sort((a, b) => a[0] - b[0]);
    let cursor = 0;
    function span(start, end) {
        if (end - start < .00001) return;
        pieces.push({ x1: wall.x1 + (wall.x2 - wall.x1) * start / size, y1: wall.y1 + (wall.y2 - wall.y1) * start / size,
            x2: wall.x1 + (wall.x2 - wall.x1) * end / size, y2: wall.y1 + (wall.y2 - wall.y1) * end / size });
    }
    for (const [start, end] of openings) { span(cursor, start); cursor = Math.max(cursor, end); }
    span(cursor, size); return pieces;
}
export { removeObject } from './object-removal.js';
function segmentFitsBounds(document, item) {
    return [item.x1, item.x2].every(x => Number.isFinite(x) && x >= -geometryEpsilon && x <= document.columns + geometryEpsilon)
        && [item.y1, item.y2].every(y => Number.isFinite(y) && y >= -geometryEpsilon && y <= document.rows + geometryEpsilon);
}
export function fitsBounds(document) {
    return objectKinds.every(kind => (document[kind] || []).every(item => {
        if (kind === 'walls' || kind === 'doors') return segmentFitsBounds(document, item);
        if (kind === 'regions') return validateRegionGeometry(document, item);
        // Both authored offsets and the current mechanism projection must fit.
        if (pointKinds.has(kind) && (![item.x, item.y].every(Number.isFinite) || item.x < -geometryEpsilon
            || item.y < -geometryEpsilon || item.x > document.columns + geometryEpsilon || item.y > document.rows + geometryEpsilon)) return false;
        if (kind === 'decorations' && item.torch && !decorationCorners({ ...item, torch: undefined }).every(point =>
            point.x >= -geometryEpsilon && point.x <= document.columns + geometryEpsilon
            && point.y >= -geometryEpsilon && point.y <= document.rows + geometryEpsilon)) return false;
        const bounds = objectBounds(kind, item, document);
        return bounds && [bounds.x, bounds.y, bounds.width, bounds.height].every(Number.isFinite)
            && bounds.x >= -geometryEpsilon && bounds.y >= -geometryEpsilon
            && bounds.x + bounds.width <= document.columns + geometryEpsilon
            && bounds.y + bounds.height <= document.rows + geometryEpsilon;
    }));
}
export function translateObject(document, kind, id, dx, dy) {
    return translateSelection(document, [{ kind, id }], dx, dy);
}
function layerFor(document, item) {
    return document.layers?.find(layer => layer.id === item.layerId) || (!item.layerId ? document.layers?.[0] : null);
}
function objectLookup(document) {
    const kinds = new Map();
    return (kind, id) => {
        if (!kinds.has(kind)) {
            const items = new Map();
            for (const item of document[kind] || []) if (!items.has(item.id)) items.set(item.id, item);
            kinds.set(kind, items);
        }
        return kinds.get(kind).get(id);
    };
}
function selectedItems(document, refs) {
    if (!Array.isArray(refs)) return [];
    const seen = new Set(), items = [], find = objectLookup(document);
    for (const ref of expandTorchSelection(document, refs)) {
        if (!ref || !objectKinds.includes(ref.kind)) return [];
        const key = `${ref.kind}:${ref.id}`;
        if (seen.has(key)) continue;
        const item = find(ref.kind, ref.id);
        if (!item) return [];
        seen.add(key); items.push({ kind: ref.kind, item });
    }
    return items;
}
function rotationPoint(point, center, angle) {
    const turns = ((angle % 360) + 360) % 360;
    const x = point.x - center.x, y = point.y - center.y;
    // Exact quarter turns preserve legacy collinear wall/door endpoints.
    if (turns === 0) return { ...point };
    if (turns === 90) return { x: center.x - y, y: center.y + x };
    if (turns === 180) return { x: center.x - x, y: center.y - y };
    if (turns === 270) return { x: center.x + y, y: center.y - x };
    const radians = turns * Math.PI / 180;
    return { x: center.x + x * Math.cos(radians) - y * Math.sin(radians),
        y: center.y + x * Math.sin(radians) + y * Math.cos(radians) };
}
export function decorationCorners(item) {
    const center = { x: item.x + item.width / 2, y: item.y + item.height / 2 };
    return [{ x: item.x, y: item.y }, { x: item.x + item.width, y: item.y },
        { x: item.x + item.width, y: item.y + item.height }, { x: item.x, y: item.y + item.height }]
        .map(point => rotationPoint(point, center, (item.rotation || 0) + (item.torch?.state === 'on' ? 90 : 0)));
}
function pointsBounds(points) {
    const x = Math.min(...points.map(point => point.x)), y = Math.min(...points.map(point => point.y));
    return { x, y, width: Math.max(...points.map(point => point.x)) - x,
        height: Math.max(...points.map(point => point.y)) - y };
}
function objectBounds(kind, item, document) {
    if (kind === 'walls' || kind === 'doors') return pointsBounds([{ x: item.x1, y: item.y1 }, { x: item.x2, y: item.y2 }]);
    if (kind === 'decorations') return pointsBounds(decorationCorners(item));
    if (pointKinds.has(kind)) {
        const point = document ? torchComponentState(document, kind, item) : item;
        return { x: point.x, y: point.y, width: 0, height: 0 };
    }
    return { x: item.x, y: item.y, width: item.width, height: item.height };
}
export function selectionBounds(document, refs) {
    return itemsBounds(selectedItems(document, refs), document);
}
function itemsBounds(items, document) {
    if (!items.length) return null;
    return pointsBounds(items.flatMap(({ kind, item }) => {
        const bounds = objectBounds(kind, item, document);
        return [{ x: bounds.x, y: bounds.y }, { x: bounds.x + bounds.width, y: bounds.y + bounds.height }];
    }));
}
function validGeometry(document, candidates) {
    return fitsBounds(document) && candidates.filter(({ kind }) => kind === 'doors').every(({ item }) => doorFits(document, item));
}
function applyItems(document, items) {
    // Mutate existing objects only after every candidate has passed validation.
    const find = objectLookup(document);
    for (const { kind, item } of items) Object.assign(find(kind, item.id), item);
}
function mutableSelection(document, refs) {
    const items = selectedItems(document, refs);
    return items.some(({ item }) => layerFor(document, item)?.locked) ? [] : items;
}
export function translateSelection(document, refs, dx, dy, { snapStep = 0 } = {}) {
    const items = mutableSelection(document, refs), bounds = itemsBounds(items, document);
    if (!items.length || !bounds || !Number.isFinite(dx) || !Number.isFinite(dy)
        || !Number.isFinite(snapStep) || snapStep < 0
        || bounds.width > document.columns || bounds.height > document.rows) return false;
    let minDx = -bounds.x, maxDx = document.columns - bounds.x - bounds.width;
    let minDy = -bounds.y, maxDy = document.rows - bounds.y - bounds.height;
    const owners = new Set(items.filter(({ kind }) => kind === 'decorations').map(({ item }) => item.id));
    for (const { kind, item } of items) {
        const owner = torchOwner(document, kind, item.id);
        if (owner?.torch.state === 'on' && !owners.has(owner.id)) {
            minDx = Math.max(minDx, item.y - document.rows); maxDx = Math.min(maxDx, item.y);
            minDy = Math.max(minDy, -item.x); maxDy = Math.min(maxDy, document.columns - item.x);
        } else {
            const raw = objectBounds(kind, item.torch ? { ...item, torch: undefined } : item);
            minDx = Math.max(minDx, -raw.x); maxDx = Math.min(maxDx, document.columns - raw.x - raw.width);
            minDy = Math.max(minDy, -raw.y); maxDy = Math.min(maxDy, document.rows - raw.y - raw.height);
        }
    }
    if (snapStep) {
        // Clamp the displacement in steps so fractional group edges cannot move walls off the grid.
        const minX = Math.ceil((minDx - geometryEpsilon) / snapStep);
        const maxX = Math.floor((maxDx + geometryEpsilon) / snapStep);
        const minY = Math.ceil((minDy - geometryEpsilon) / snapStep);
        const maxY = Math.floor((maxDy + geometryEpsilon) / snapStep);
        if (minX > maxX || minY > maxY) return false;
        dx = clamp(Math.round(dx / snapStep), minX, maxX) * snapStep;
        dy = clamp(Math.round(dy / snapStep), minY, maxY) * snapStep;
    } else {
        dx = clamp(dx, minDx, maxDx);
        dy = clamp(dy, minDy, maxDy);
    }
    if (!dx && !dy) return false;
    const next = clone(document), candidates = selectedItems(next, refs);
    const parents = new Set(candidates.filter(({ kind }) => kind === 'decorations').map(({ item }) => item.id));
    for (const { kind, item } of candidates) {
        if (kind === 'walls' || kind === 'doors') {
            for (const key of ['x1', 'x2']) item[key] += dx;
            for (const key of ['y1', 'y2']) item[key] += dy;
        } else {
            const owner = torchOwner(document, kind, item.id);
            if (owner && !parents.has(owner.id)) {
                const point = torchComponentState(document, kind, item);
                Object.assign(item, torchSourcePoint(document, kind, item.id, { x: point.x + dx, y: point.y + dy }));
            } else { item.x += dx; item.y += dy; }
        }
    }
    if (!validGeometry(next, candidates)) return false;
    applyItems(document, candidates); return true;
}
export function rotateSelection(document, refs, angle = 90) {
    const items = mutableSelection(document, refs), bounds = itemsBounds(items, document);
    if (!items.length || !bounds || !Number.isFinite(angle) || angle % 360 === 0
        || (items.some(({ kind }) => ['floors', 'regions'].includes(kind)) && angle % 90 !== 0)) return false;
    const selectedParents = new Set(refs.filter(ref => ref.kind === 'decorations').map(ref => ref.id));
    const roots = refs.filter(ref => {
        const owner = torchOwner(document, ref.kind, ref.id);
        return !owner || !selectedParents.has(owner.id);
    });
    const parent = roots.length === 1 && roots[0].kind === 'decorations'
        ? document.decorations.find(item => item.id === roots[0].id && item.torch) : null;
    const center = parent ? { x: parent.x + parent.width / 2, y: parent.y + parent.height / 2 }
        : { x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2 };
    const next = clone(document), candidates = selectedItems(next, refs);
    const parents = new Set(candidates.filter(({ kind }) => kind === 'decorations').map(({ item }) => item.id));
    for (const { kind, item } of candidates) {
        if (kind === 'walls' || kind === 'doors') {
            const a = rotationPoint({ x: item.x1, y: item.y1 }, center, angle);
            const b = rotationPoint({ x: item.x2, y: item.y2 }, center, angle);
            Object.assign(item, { x1: a.x, y1: a.y, x2: b.x, y2: b.y });
        } else if (pointKinds.has(kind)) {
            const owner = torchOwner(document, kind, item.id);
            const point = owner && !parents.has(owner.id) ? torchComponentState(document, kind, item) : item;
            const rotated = rotationPoint(point, center, angle);
            Object.assign(item, owner && !parents.has(owner.id) ? torchSourcePoint(document, kind, item.id, rotated) : rotated);
            if (item.rotation !== undefined) item.rotation = ((item.rotation + angle) % 360 + 360) % 360;
        } else {
            const point = rotationPoint({ x: item.x + item.width / 2, y: item.y + item.height / 2 }, center, angle);
            if (['floors', 'regions'].includes(kind) && Math.abs(angle / 90) % 2 === 1) [item.width, item.height] = [item.height, item.width];
            if (kind === 'floors' && item.shape) {
                const turns = ((angle / 90) % 4 + 4) % 4;
                for (const part of ['contours', 'cuts']) item.shape[part] = item.shape[part].map(ring => ring.map(([u, v]) => {
                    for (let turn = 0; turn < turns; turn++) [u, v] = [1 - v, u];
                    return [Math.round(u * 1e9) / 1e9, Math.round(v * 1e9) / 1e9];
                }));
            }
            if (kind === 'floors' && item.brush) {
                const turns = ((angle / 90) % 4 + 4) % 4;
                for (let turn = 0; turn < turns; turn++) {
                    item.brush.points = item.brush.points.map(([u, v, alpha]) => [Math.max(0, Math.min(1, 1 - v)), u, alpha]);
                    item.brush.radius.reverse();
                }
            }
            item.x = point.x - item.width / 2; item.y = point.y - item.height / 2;
            if (kind !== 'regions') item.rotation = (((item.rotation || 0) + angle) % 360 + 360) % 360;
        }
    }
    if (!validGeometry(next, candidates)) return false;
    applyItems(document, candidates); return true;
}
/** Change the parent geometry and its component offsets as one validated operation. */
export function updateTorchGeometry(document, id, patch) {
    const parent = document.decorations?.find(item => item.id === id);
    if (!parent?.torch || !patch || Object.keys(patch).some(key => !['x', 'y', 'width', 'height', 'rotation'].includes(key))
        || Object.values(patch).some(value => !Number.isFinite(value)) || layerFor(document, parent)?.locked
        || layerFor(document, parent)?.visible === false) return false;
    const updated = { ...parent, ...patch };
    if (updated.width < .05 || updated.height < .05 || sameDocument(parent, updated)) return false;
    const next = clone(document), candidate = next.decorations.find(item => item.id === id);
    Object.assign(candidate, patch);
    const oldCenter = { x: parent.x + parent.width / 2, y: parent.y + parent.height / 2 };
    const center = { x: updated.x + updated.width / 2, y: updated.y + updated.height / 2 };
    const angle = (updated.rotation || 0) - (parent.rotation || 0);
    for (const ref of torchChildren(next, candidate)) {
        const item = next[ref.kind].find(row => row.id === ref.id);
        const local = rotationPoint(item, oldCenter, -(parent.rotation || 0));
        const point = rotationPoint({ x: center.x + (local.x - oldCenter.x) * updated.width / parent.width,
            y: center.y + (local.y - oldCenter.y) * updated.height / parent.height }, center, updated.rotation || 0);
        item.x = point.x; item.y = point.y;
        if (angle) item.rotation = (((item.rotation || 0) + angle) % 360 + 360) % 360;
    }
    if (!fitsBounds(next)) return false;
    applyItems(document, selectedItems(next, [{ kind: 'decorations', id }]));
    return true;
}
export function duplicateSelection(document, refs, dx = 1, dy = 1, { includeComponents = false } = {}) {
    const items = mutableSelection(document, refs);
    if (!items.length || objectKinds.reduce((total, kind) => total + (document[kind]?.length || 0), 0) + items.length > 2000
        || (document.regions?.length || 0) + items.filter(({ kind }) => kind === 'regions').length > 128
        || !Number.isFinite(dx) || !Number.isFinite(dy)) return [];
    const next = clone(document), copies = [], componentCopies = new Map(), lightCopies = new Map(), elementCopies = new Map();
    const parents = new Set(items.filter(({ kind }) => kind === 'decorations').map(({ item }) => item.id));
    for (const { kind, item } of items) {
        const owner = torchOwner(document, kind, item.id);
        const source = owner && !parents.has(owner.id) ? torchComponentState(document, kind, item) : item;
        const copy = { ...clone(source), id: crypto.randomUUID() };
        next[kind] ??= []; next[kind].push(copy); copies.push({ kind, id: copy.id });
        componentCopies.set(item.id, copy.id);
        if (kind === 'lights') lightCopies.set(item.id, copy.id);
        if (kind === 'doors' || kind === 'regions' || kind === 'decorations' || item.dynamic === true) elementCopies.set(item.id, copy.id);
    }
    // Targets copied in the same group follow their copies; others stay shared.
    for (const { kind, item } of selectedItems(next, copies)) if (kind === 'doors' || kind === 'decorations' || kind === 'regions') {
        if (item.torch) for (const field of ['lightId', 'particleId', 'shaderId']) {
            if (componentCopies.has(item.torch[field])) item.torch[field] = componentCopies.get(item.torch[field]);
        }
        for (const graph of Object.values(item.blueprint?.graphs || {})) for (const node of graph.nodes) {
            if (['light', 'lightReference'].includes(node.type) && lightCopies.has(node.targetId)) node.targetId = lightCopies.get(node.targetId);
            if (node.type === 'reference' && elementCopies.has(node.targetId)) node.targetId = elementCopies.get(node.targetId);
            if (node.type === 'elementGroup' && node.memberType !== 'sound') {
                const mapping = node.memberType === 'light' ? lightCopies : elementCopies;
                node.targetIds = node.targetIds.map(id => mapping.get(id) || id);
            }
        }
    }
    // A zero displacement is useful for decoration copies; overlapping doors remain invalid.
    if (dx || dy) translateSelection(next, copies, dx, dy);
    const candidates = selectedItems(next, copies);
    if (!validGeometry(next, candidates)) return [];
    for (const { kind, item } of candidates) {
        document[kind] ??= [];
        document[kind].push(item);
    }
    if (includeComponents) return copies;
    const explicitParents = new Set(refs.filter(ref => ref.kind === 'decorations').map(ref => ref.id)), seen = new Set();
    return refs.flatMap(ref => {
        const owner = torchOwner(document, ref.kind, ref.id), id = componentCopies.get(ref.id);
        if (!id || seen.has(id) || owner && explicitParents.has(owner.id)) return [];
        seen.add(id); return [{ kind: ref.kind, id }];
    });
}
function pointInside(point, rect) {
    return point.x >= rect.x - geometryEpsilon && point.x <= rect.x + rect.width + geometryEpsilon
        && point.y >= rect.y - geometryEpsilon && point.y <= rect.y + rect.height + geometryEpsilon;
}
function segmentsIntersect(a, b, c, d) {
    const cross = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
    const abC = cross(a, b, c), abD = cross(a, b, d), cdA = cross(c, d, a), cdB = cross(c, d, b);
    if (Math.abs(abC) <= geometryEpsilon && Math.abs(abD) <= geometryEpsilon) {
        return Math.max(Math.min(a.x, b.x), Math.min(c.x, d.x)) <= Math.min(Math.max(a.x, b.x), Math.max(c.x, d.x)) + geometryEpsilon
            && Math.max(Math.min(a.y, b.y), Math.min(c.y, d.y)) <= Math.min(Math.max(a.y, b.y), Math.max(c.y, d.y)) + geometryEpsilon;
    }
    return abC * abD <= geometryEpsilon ** 2 && cdA * cdB <= geometryEpsilon ** 2;
}
function polygonIntersectsRectangle(points, rect) {
    const corners = [{ x: rect.x, y: rect.y }, { x: rect.x + rect.width, y: rect.y },
        { x: rect.x + rect.width, y: rect.y + rect.height }, { x: rect.x, y: rect.y + rect.height }];
    if (points.some(point => pointInside(point, rect))) return true;
    if (points.length > 2 && corners.some(point => {
        let sign = 0;
        for (let index = 0; index < points.length; index++) {
            const a = points[index], b = points[(index + 1) % points.length];
            const cross = (b.x - a.x) * (point.y - a.y) - (b.y - a.y) * (point.x - a.x);
            if (Math.abs(cross) <= geometryEpsilon) continue;
            if (sign && Math.sign(cross) !== sign) return false;
            sign = Math.sign(cross);
        }
        return true;
    })) return true;
    for (let index = 0; index < points.length - (points.length === 2 ? 1 : 0); index++) {
        const a = points[index], b = points[(index + 1) % points.length];
        for (let edge = 0; edge < corners.length; edge++) {
            if (segmentsIntersect(a, b, corners[edge], corners[(edge + 1) % corners.length])) return true;
        }
    }
    return false;
}
export function objectsInRectangle(document, rectangle) {
    if (!rectangle || !['x', 'y', 'width', 'height'].every(key => Number.isFinite(rectangle[key]))) return [];
    const rect = { x: Math.min(rectangle.x, rectangle.x + rectangle.width), y: Math.min(rectangle.y, rectangle.y + rectangle.height),
        width: Math.abs(rectangle.width), height: Math.abs(rectangle.height) };
    const refs = [];
    for (const kind of objectKinds) for (const item of document[kind] || []) {
        const layer = layerFor(document, item);
        if (layer?.locked || layer?.visible === false) continue;
        if (kind === 'floors' && item.shape) {
            if (floorIntersectsRectangle(item, rect)) refs.push({ kind, id: item.id });
            continue;
        }
        let points;
        if (pointKinds.has(kind)) {
            const point = torchComponentState(document, kind, item);
            points = [{ x: point.x, y: point.y }];
        }
        else if (kind === 'walls' || kind === 'doors') points = [{ x: item.x1, y: item.y1 }, { x: item.x2, y: item.y2 }];
        else if (kind === 'decorations') points = decorationCorners(item);
        else points = [{ x: item.x, y: item.y }, { x: item.x + item.width, y: item.y },
            { x: item.x + item.width, y: item.y + item.height }, { x: item.x, y: item.y + item.height }];
        if (polygonIntersectsRectangle(points, rect)) refs.push({ kind, id: item.id });
    }
    return refs;
}
export function history(initial, limit = 60) {
    let past = [], future = [], current = clone(initial);
    return {
        get canUndo() { return past.length > 0; }, get canRedo() { return future.length > 0; },
        commit(value) {
            if (JSON.stringify(value) === JSON.stringify(current)) return false;
            past.push(current); if (past.length > limit) past.shift();
            current = clone(value); future = []; return true;
        },
        reset(value) { current = clone(value); past = []; future = []; },
        rebase(transform) {
            // Permanent resource removal also applies to old snapshots. Keep
            // unrelated edits undoable, while removing steps that became equal.
            const apply = value => clone(transform(clone(value)));
            const compact = values => values.filter((value, index) => !index || !sameDocument(value, values[index - 1]));
            const nextCurrent = apply(current), nextPast = compact(past.map(apply)), nextFuture = compact(future.map(apply));
            while (nextPast.length && sameDocument(nextPast.at(-1), nextCurrent)) nextPast.pop();
            while (nextFuture.length && sameDocument(nextFuture.at(-1), nextCurrent)) nextFuture.pop();
            current = nextCurrent; past = nextPast; future = nextFuture;
            return clone(current);
        },
        undo() { if (!past.length) return clone(current); future.push(current); current = past.pop(); return clone(current); },
        redo() { if (!future.length) return clone(current); past.push(current); current = future.pop(); return clone(current); },
    };
}
