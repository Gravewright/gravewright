/** Deterministic radial terrain masks. Source coordinates are floor-bbox local. */
export const terrainBrushLimits = Object.freeze({ dabs: 2048, documentDabs: 8192,
    workPixels: 67108864, minSize: .001, maxRadius: 10000, holdMilliseconds: 50, spacing: .2 });
const invalid = 'Invalid floor brush.';
const tooMany = 'The map has too many terrain brush dabs.';
const tooComplex = 'The map terrain brushes are too complex.';
const finite = value => typeof value === 'number' && Number.isFinite(value);

function structureError(item) {
    const brush = item.brush;
    if (!brush || typeof brush !== 'object' || Array.isArray(brush)
        || Object.keys(brush).length !== 4 || !['operation', 'points', 'radius', 'hardness'].every(key => Object.hasOwn(brush, key))
        || !['paint', 'erase'].includes(brush.operation) || !finite(brush.hardness) || brush.hardness < 0 || brush.hardness > 1
        || !Array.isArray(brush.radius) || brush.radius.length !== 2
        || !brush.radius.every(value => finite(value) && value > 0 && value <= terrainBrushLimits.maxRadius)
        || !Array.isArray(brush.points) || !brush.points.length
        || ![item.x, item.y, item.width, item.height].every(finite)
        || item.width < terrainBrushLimits.minSize || item.height < terrainBrushLimits.minSize
        || brush.operation === 'erase' && item.assetId !== null) return invalid;
    if (brush.points.length > terrainBrushLimits.dabs) return tooMany;
    if (brush.points.some(point => !Array.isArray(point) || point.length !== 3
        || !point.every(value => finite(value) && value >= 0 && value <= 1))) return invalid;
    return null;
}

/** Integer raster bounds use absolute pixel centers, matching the server renderer. */
export function terrainBrushBounds(item, cellSize) {
    const left = Math.floor(item.x * cellSize), top = Math.floor(item.y * cellSize);
    return { left, top, width: Math.max(0, Math.ceil((item.x + item.width) * cellSize) - left),
        height: Math.max(0, Math.ceil((item.y + item.height) * cellSize) - top) };
}
function dabBounds(item, point, cellSize, bounds) {
    const x = (item.x + point[0] * item.width) * cellSize;
    const y = (item.y + point[1] * item.height) * cellSize;
    const rx = item.brush.radius[0] * item.width * cellSize, ry = item.brush.radius[1] * item.height * cellSize;
    return { x, y, rx, ry, left: Math.max(bounds.left, Math.floor(x - rx)), top: Math.max(bounds.top, Math.floor(y - ry)),
        right: Math.min(bounds.left + bounds.width, Math.ceil(x + rx)), bottom: Math.min(bounds.top + bounds.height, Math.ceil(y + ry)) };
}
/** Validate source and bound the actual dab loops before allocating a raster. */
export function terrainBrushError(document, floors = document.floors || []) {
    if (!finite(document.cellSize) || document.cellSize <= 0) return invalid;
    let count = 0, work = 0;
    for (const item of floors) {
        if (item.brush === undefined) continue;
        const error = structureError(item);
        if (error) return error;
        count += item.brush.points.length;
        if (count > terrainBrushLimits.documentDabs) return tooMany;
        const bounds = terrainBrushBounds(item, document.cellSize);
        for (const point of item.brush.points) {
            if (point[2] === 0) continue;
            const dab = dabBounds(item, point, document.cellSize, bounds);
            work += Math.max(0, dab.right - dab.left) * Math.max(0, dab.bottom - dab.top);
            if (work > terrainBrushLimits.workPixels) return tooComplex;
        }
    }
    return null;
}
const sourceAlpha = (distance, hardness, strength) => distance >= 1 ? 0
    : Math.floor(255 * strength * (distance <= hardness ? 1 : (1 - distance) / (1 - hardness)) + .5);
const over = (destination, source) => Math.floor((source * 255 + destination * (255 - source) + 127) / 255);

/** Radial coverage only. Existing shape/cuts and paint opacity multiply it separately. */
export function terrainBrushAlpha(item, point) {
    if (!item.brush) return 1;
    const brush = item.brush, x = (point.x - item.x) / item.width, y = (point.y - item.y) / item.height;
    let alpha = 0;
    for (const [u, v, strength] of brush.points) {
        const value = sourceAlpha(Math.hypot((x - u) / brush.radius[0], (y - v) / brush.radius[1]), brush.hardness, strength);
        if (value) alpha = over(alpha, value);
        if (alpha === 255) break;
    }
    return alpha / 255;
}

/** One byte per pixel; both renderers use the same integer source-over rounding. */
export function terrainBrushMask(item, cellSize) {
    const error = terrainBrushError({ cellSize }, [item]);
    if (error) throw new RangeError(error);
    if (!finite(cellSize) || cellSize <= 0) throw new RangeError(invalid);
    const bounds = terrainBrushBounds(item, cellSize);
    if (bounds.width * bounds.height > terrainBrushLimits.workPixels) throw new RangeError(tooComplex);
    const alpha = new Uint8ClampedArray(bounds.width * bounds.height);
    for (const point of item.brush.points) {
        if (!point[2]) continue;
        const dab = dabBounds(item, point, cellSize, bounds), ix = 1 / dab.rx, iy = 1 / dab.ry;
        for (let y = dab.top; y < dab.bottom; y++) {
            const dy = (y + .5 - dab.y) * iy, yy = dy * dy;
            for (let x = dab.left; x < dab.right; x++) {
                const dx = (x + .5 - dab.x) * ix;
                const source = sourceAlpha(Math.sqrt(dx * dx + yy), item.brush.hardness, point[2]);
                if (!source) continue;
                const index = (y - bounds.top) * bounds.width + x - bounds.left;
                alpha[index] = over(alpha[index], source);
            }
        }
    }
    return { ...bounds, alpha };
}
