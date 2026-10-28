// features/selection/model/selection-scope.js
import { imageInWorkspace } from "../../images/model/image-layer.js";
function objectInSelectionWorkspace(object, layer = "game") {
  if (object.kind === "token")
    return ["game", "gm"].includes(layer) && (object.data.layer || (object.data.hidden ? "gm" : "game")) === layer;
  if (object.kind === "image")
    return ["composition", "gm"].includes(layer) && imageInWorkspace(object.data, layer);
  const layers = { card: "game", wall: "walls", light: "lighting", particle: "effects", shader: "effects", sound: "audio", zone: "gm" };
  return layers[object.kind] === layer;
}
export {
  objectInSelectionWorkspace
};
