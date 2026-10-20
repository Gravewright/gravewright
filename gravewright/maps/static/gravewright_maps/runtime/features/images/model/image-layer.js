// gravewright/maps/frontend/features/images/model/image-layer.js
function isGMImage(image) {
  return image.empty === true || ["gm", "gm-image-layer"].includes(image.layer);
}
function imageInWorkspace(image, layer = "game") {
  return isGMImage(image) ? layer === "gm" : layer !== "gm";
}
function canMoveImageToGame(image) {
  return image.empty !== true;
}
function imageMarkerVisible(image, layer = "game", gm = true) {
  return !isGMImage(image) || gm;
}
export {
  canMoveImageToGame,
  imageInWorkspace,
  imageMarkerVisible,
  isGMImage
};
