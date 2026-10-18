/** Compose an authored map-space material once, retaining the generated alpha mask. */
export function surfaceMaterial(surface, material, mask) {
    const width = mask.width, height = mask.height;
    if (!surface || !['floor', 'wall'].includes(surface.kind) || width * height > 16_777_216
        || width < 1 || height < 1 || ![surface.cellSize, surface.left, surface.top].every(Number.isFinite)
        || surface.cellSize < 16 || surface.cellSize > 256) throw new TypeError('Invalid dynamic surface.');
    const canvas = document.createElement('canvas'); canvas.width = width; canvas.height = height;
    const context = canvas.getContext('2d');
    const tile = document.createElement('canvas');
    let matrix;
    if (surface.kind === 'floor') {
        if (![0, 90, 180, 270].includes(surface.rotation)) throw new TypeError('Invalid dynamic surface.');
        tile.width = tile.height = surface.cellSize;
        const paint = tile.getContext('2d');
        paint.translate(tile.width / 2, tile.height / 2); paint.rotate(surface.rotation * Math.PI / 180);
        paint.drawImage(material, -tile.width / 2, -tile.height / 2, tile.width, tile.height);
        matrix = new DOMMatrix().translate(-surface.left, -surface.top);
    } else {
        const [left, top, right, bottom] = surface.materialCrop || [0, 0, material.width, material.height];
        if (![left, top, right, bottom, surface.thickness, surface.phase, ...surface.origin, ...surface.direction].every(Number.isFinite)
            || left < 0 || top < 0 || right > material.width || bottom > material.height || right <= left || bottom <= top
            || surface.thickness <= 0 || Math.abs(Math.hypot(...surface.direction) - 1) > .000001)
            throw new TypeError('Invalid dynamic surface.');
        tile.width = right - left; tile.height = bottom - top;
        tile.getContext('2d').drawImage(material, left, top, tile.width, tile.height, 0, 0, tile.width, tile.height);
        const [ux, uy] = surface.direction, scale = surface.thickness / tile.height;
        matrix = new DOMMatrix([scale * ux, scale * uy, -scale * uy, scale * ux,
            surface.origin[0] - surface.left - ux * surface.phase + uy * surface.thickness / 2,
            surface.origin[1] - surface.top - uy * surface.phase - ux * surface.thickness / 2]);
    }
    const pattern = context.createPattern(tile, 'repeat'); pattern.setTransform(matrix);
    context.fillStyle = pattern; context.fillRect(0, 0, width, height);
    context.globalCompositeOperation = 'destination-in'; context.drawImage(mask, 0, 0);
    // The retained texture contains the composed canvas, not its temporary tile.
    tile.width = tile.height = 1;
    return canvas;
}
