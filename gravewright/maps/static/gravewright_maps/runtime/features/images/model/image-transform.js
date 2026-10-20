// gravewright/maps/frontend/features/images/model/image-transform.js
function resizeImage(image, corner, start, point) {
  const angle = image.rotation * Math.PI / 180;
  const cos = Math.cos(angle), sin = Math.sin(angle);
  const dx = point.x - start.x, dy = point.y - start.y;
  const localX = dx * cos + dy * sin, localY = -dx * sin + dy * cos;
  const width = image.natural_width, height = image.natural_height;
  const requested = image.scale + (localX * corner.x * width + localY * corner.y * height) / (width * width + height * height);
  let scale;
  const box = image.torch ?? image.lever;
  if (box && [box.width, box.height].every((value) => Number.isFinite(value) && value > 0)) {
    const minimum = Math.max(1e-12, image.scale * Math.max(1e-3 / box.width, 1e-3 / box.height));
    const maximum = Math.min(1e6, image.scale * Math.min(1e6 / box.width, 1e6 / box.height));
    scale = minimum >= maximum ? image.scale : requested < minimum ? Math.min(maximum, minimum * (1 + 4 * Number.EPSILON)) : requested > maximum ? Math.max(minimum, maximum * (1 - 4 * Number.EPSILON)) : requested;
  } else scale = Math.max(1e-3, Math.min(100, requested));
  const halfX = corner.x * width * (scale - image.scale) / 2;
  const halfY = corner.y * height * (scale - image.scale) / 2;
  return {
    ...image,
    scale,
    x: image.x + halfX * cos - halfY * sin,
    y: image.y + halfX * sin + halfY * cos
  };
}
export {
  resizeImage
};
