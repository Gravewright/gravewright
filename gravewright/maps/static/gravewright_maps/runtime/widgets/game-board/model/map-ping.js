// widgets/game-board/model/map-ping.js
var PING_DURATION = 2e3;
var DEFAULT_PING_COLOR = "#f2c679";
function pingShapes(age, scale, focus, inputColor = DEFAULT_PING_COLOR) {
  const color = /^#[0-9a-f]{6}$/i.test(inputColor) ? inputColor : DEFAULT_PING_COLOR;
  const shapes = [];
  for (let index = 0; index < 3; index++) {
    const progress = Math.max(0, Math.min(1, age * 1.45 - index * 0.18));
    if (progress <= 0 || progress >= 1)
      continue;
    const radius = (18 + 92 * progress) / scale;
    const stroke = { color, width: 4 / scale, alpha: Math.pow(1 - progress, 1.35) };
    shapes.push(focus ? { kind: "polygon", points: [0, -radius, radius, 0, 0, radius, -radius, 0], stroke } : { kind: "circle", radius, stroke });
  }
  const pulse = 1 + 0.24 * Math.sin(age * Math.PI * 8);
  shapes.push({ kind: "circle", radius: 9 * pulse / scale, fill: { color, alpha: Math.max(0.35, 1 - age) }, stroke: { color: "#ffffff", width: 2 / scale, alpha: Math.max(0.2, 0.75 - age) } });
  shapes.push({ kind: "circle", radius: 18 * pulse / scale, stroke: { color, width: 3 / scale, alpha: Math.max(0.18, 0.8 - age) } });
  return shapes;
}
export {
  DEFAULT_PING_COLOR,
  PING_DURATION,
  pingShapes
};
