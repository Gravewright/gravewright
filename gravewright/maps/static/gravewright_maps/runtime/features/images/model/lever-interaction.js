// gravewright/maps/frontend/features/images/model/lever-interaction.js
import { isGMImage as privateLayer, imageInWorkspace } from "./image-layer.js";
function interactiveImageKind(image) {
  if (["off", "on"].includes(image.torch?.state) && typeof image.torch.lit === "boolean") return "torch";
  if (["off", "on"].includes(image.lever?.state)) return "lever";
}
function canInteractWithImage(image, gm = false) {
  return !!image && !!interactiveImageKind(image) && (gm || image.interactionEnabled !== false);
}
function createInteractiveImageHitTest(images, gm, layer) {
  const ordered = images.filter((image) => gm ? layer === void 0 || imageInWorkspace(image, layer) : !privateLayer(image)).map((image, index) => ({ image, index })).sort((a, b) => Number(privateLayer(b.image)) - Number(privateLayer(a.image)) || b.image.z_index - a.image.z_index || b.index - a.index);
  return (point) => {
    for (const { image } of ordered) {
      const width = image.natural_width * image.scale, height = image.natural_height * image.scale;
      if (![image.x, image.y, image.rotation, width, height].every(Number.isFinite) || width <= 0 || height <= 0)
        continue;
      const angle = -image.rotation * Math.PI / 180, dx = point.x - image.x, dy = point.y - image.y;
      if (Math.abs(dx * Math.cos(angle) - dy * Math.sin(angle)) > width / 2 || Math.abs(dx * Math.sin(angle) + dy * Math.cos(angle)) > height / 2)
        continue;
      return canInteractWithImage(image, gm) ? image : void 0;
    }
  };
}
function interactiveImageAt(images, point, gm) {
  return createInteractiveImageHitTest(images, gm)(point);
}
var leverAt = interactiveImageAt;
export {
  canInteractWithImage,
  createInteractiveImageHitTest,
  interactiveImageAt,
  interactiveImageKind,
  leverAt
};
