function fanLayout(count, available) {
  let width = 130, step = width * 0.62;
  if (count > 1 && width + (count - 1) * step > available) step = Math.max(width * 0.26, (available - width) / (count - 1));
  if (count > 1 && width + (count - 1) * step > available) {
    width = Math.max(64, available / (1 + (count - 1) * 0.26));
    step = width * 0.26;
  }
  return { width: Math.round(width), overlap: Math.round(step - width) };
}
function fanPose(index, count) {
  const offset = index - (count - 1) / 2;
  return { rotation: offset * Math.min(7, 22 / Math.max(1, count - 1)), arc: Math.abs(offset) * 5 };
}
function cardFace(card, flipped) {
  return (flipped ? card.backUrl : card.frontUrl) || "";
}
export {
  cardFace,
  fanLayout,
  fanPose
};
