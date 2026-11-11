// features/images/model/image-components.js
var kinds = { lights: "light", particles: "particle", shaders: "shader" };
function imageComponentKeys(image) {
  return Object.entries(image.torch?.components ?? {}).flatMap(([kind, component]) => kinds[kind] && typeof component?.id === "string" ? [`${kinds[kind]}:${component.id}`] : []);
}
function imageComponentTransform(original, next, base, component = original) {
  if (!(original.scale > 0) || !Number.isFinite(next.scale) || next.scale <= 0) return;
  const ratio = next.scale / original.scale, angle = next.rotation - original.rotation;
  const radians = angle * Math.PI / 180, cos = Math.cos(radians), sin = Math.sin(radians);
  const dx = component.x - original.x, dy = component.y - original.y;
  const sourceX = next.x + (dx * cos - dy * sin) * ratio;
  const sourceY = next.y + (dx * sin + dy * cos) * ratio;
  const localX = base.x - component.x, localY = base.y - component.y;
  return {
    x: sourceX + localX * cos - localY * sin,
    y: sourceY + localX * sin + localY * cos,
    angle: base.angle + angle,
    scaleX: base.scaleX ?? 1,
    scaleY: base.scaleY ?? 1
  };
}
export {
  imageComponentKeys,
  imageComponentTransform
};
