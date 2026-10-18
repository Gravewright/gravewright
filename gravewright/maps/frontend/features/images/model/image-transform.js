// Resize proportionally around the opposite corner, in scene coordinates.
export function resizeImage(image, corner, start, point) {
    const angle = image.rotation * Math.PI / 180;
    const cos = Math.cos(angle), sin = Math.sin(angle);
    const dx = point.x - start.x, dy = point.y - start.y;
    const localX = dx * cos + dy * sin, localY = -dx * sin + dy * cos;
    const width = image.natural_width, height = image.natural_height;
    const requested = image.scale +
        (localX * corner.x * width + localY * corner.y * height) / (width * width + height * height);
    let scale;
    const box = image.torch ?? image.lever;
    if (box && [box.width, box.height].every(value => Number.isFinite(value) && value > 0)) {
        // A state's artwork fits the Smart Object's authored box, so a tiny image can
        // legitimately have a large scale. Resize that full box proportionally.
        const minimum = Math.max(1e-12, image.scale * Math.max(.001 / box.width, .001 / box.height));
        const maximum = Math.min(1e6, image.scale * Math.min(1e6 / box.width, 1e6 / box.height));
        // Stay just inside a clamped box boundary: the server recomputes its
        // dimensions by a scale ratio, whose rounding must not exceed a limit.
        scale = minimum >= maximum ? image.scale
            : requested < minimum ? Math.min(maximum, minimum * (1 + 4 * Number.EPSILON))
            : requested > maximum ? Math.max(minimum, maximum * (1 - 4 * Number.EPSILON)) : requested;
    } else scale = Math.max(0.001, Math.min(100, requested));
    const halfX = corner.x * width * (scale - image.scale) / 2;
    const halfY = corner.y * height * (scale - image.scale) / 2;
    return { ...image, scale, x: image.x + halfX * cos - halfY * sin,
        y: image.y + halfX * sin + halfY * cos };
}
