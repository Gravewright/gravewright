// Resize proportionally around the opposite corner, in scene coordinates.
export function resizeImage(image, corner, start, point) {
    const angle = image.rotation * Math.PI / 180;
    const cos = Math.cos(angle), sin = Math.sin(angle);
    const dx = point.x - start.x, dy = point.y - start.y;
    const localX = dx * cos + dy * sin, localY = -dx * sin + dy * cos;
    const width = image.natural_width, height = image.natural_height;
    const scale = Math.max(0.001, Math.min(100, image.scale +
        (localX * corner.x * width + localY * corner.y * height) / (width * width + height * height)));
    const halfX = corner.x * width * (scale - image.scale) / 2;
    const halfY = corner.y * height * (scale - image.scale) / 2;
    return { ...image, scale, x: image.x + halfX * cos - halfY * sin,
        y: image.y + halfX * sin + halfY * cos };
}
