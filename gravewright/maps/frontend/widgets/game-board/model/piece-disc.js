/** Outline vertices; after clipping to the art (at most eight more) the mesh stays under Pixi's 100-vertex batch limit. */
export const DISC_SEGMENTS = 64;

/** Keep the side of the line `nx * x + ny * y = d` where the expression is at most `d`. */
function clip(points, nx, ny, d) {
    const out = [];
    for (let i = 0; i < points.length; i++) {
        const a = points[i], b = points[(i + 1) % points.length];
        const da = nx * a[0] + ny * a[1] - d, db = nx * b[0] + ny * b[1] - d;
        if (da <= 0) out.push(a);
        if ((da <= 0) !== (db <= 0)) {
            const t = da / (da - db);
            out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
        }
    }
    return out;
}

/**
 * A piece's art as a mesh rather than a masked sprite: the token ellipse, which stays
 * upright, clipped to the art rectangle, which is centred, `artWidth` x `artHeight`
 * and turned by `degrees`. UVs place the art exactly where the rotated sprite was,
 * so the visible pixels match the former stencil mask without a stencil pass.
 */
export function pieceDisc(radiusX, radiusY, artWidth, artHeight, degrees = 0, segments = DISC_SEGMENTS) {
    const theta = degrees * Math.PI / 180, cos = Math.cos(theta), sin = Math.sin(theta);
    const halfWidth = artWidth / 2, halfHeight = artHeight / 2;
    if (!(radiusX > 0 && radiusY > 0 && halfWidth > 0 && halfHeight > 0))
        return { positions: new Float32Array(0), uvs: new Float32Array(0), indices: new Uint32Array(0) };
    // Work in art space, where the art rectangle is axis-aligned.
    let outline = [];
    for (let i = 0; i < segments; i++) {
        const angle = i / segments * Math.PI * 2, x = radiusX * Math.cos(angle), y = radiusY * Math.sin(angle);
        outline.push([x * cos + y * sin, -x * sin + y * cos]);
    }
    outline = clip(clip(clip(clip(outline, 1, 0, halfWidth), -1, 0, halfWidth), 0, 1, halfHeight), 0, -1, halfHeight);
    const count = outline.length >= 3 ? outline.length : 0;
    const positions = new Float32Array(count * 2), uvs = new Float32Array(count * 2);
    for (let i = 0; i < count; i++) {
        const [x, y] = outline[i];
        positions[i * 2] = x * cos - y * sin;
        positions[i * 2 + 1] = x * sin + y * cos;
        uvs[i * 2] = x / artWidth + .5;
        uvs[i * 2 + 1] = y / artHeight + .5;
    }
    // The ellipse and the rectangle are convex, so their intersection is a fan.
    const indices = new Uint32Array(Math.max(0, count - 2) * 3);
    for (let i = 1; i < count - 1; i++) indices.set([0, i, i + 1], (i - 1) * 3);
    return { positions, uvs, indices };
}
