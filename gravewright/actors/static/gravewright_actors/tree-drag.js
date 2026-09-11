// gravewright/maps/frontend/shared/lib/dom/tree-drag.js
var shallowRef = () => {
  let value;
  return { get value() {
    return value;
  }, set value(next) {
    value = next;
    window.dispatchEvent(new Event("gravewright:tree-drag"));
  } };
};
var pendingDrag;
function cancelTreeDrag(kind) {
  if (!kind || pendingDrag?.kind === kind)
    pendingDrag?.cancel();
}
var THRESHOLD = 5;
var EDGE_BAND = 44;
var EDGE_SPEED = 13;
var OFFSET_X = 14;
var OFFSET_Y = 11;
var draggedItem = shallowRef();
var treeDropTarget = shallowRef();
var pointer = { x: 0, y: 0 };
var preview;
var foreign;
var foreignHandlers = /* @__PURE__ */ new Set();
function onForeignDrop(handler) {
  foreignHandlers.add(handler);
  return () => {
    foreignHandlers.delete(handler);
  };
}
function place(element) {
  element.style.transform = `translate3d(${pointer.x + OFFSET_X}px, ${pointer.y + OFFSET_Y}px, 0)`;
}
function registerTreePreview(element) {
  preview = element;
  if (element)
    place(element);
}
function resolveTarget(accepts) {
  const element = document.elementFromPoint(pointer.x, pointer.y);
  const surface = element?.closest("[data-tree-drop]");
  const directoryKind = surface?.closest("[data-tree-kind]")?.dataset.treeKind;
  const target = surface && (!directoryKind || directoryKind === draggedItem.value?.kind) ? surface.dataset.treeDrop || null : void 0;
  treeDropTarget.value = target !== void 0 && accepts(target) ? target : void 0;
  const outside = treeDropTarget.value === void 0 ? element?.closest("[data-drag-drop]")?.dataset.dragDrop : void 0;
  foreign = outside ? { surface: outside, x: pointer.x, y: pointer.y } : void 0;
}
function scrollEdge(scroller) {
  if (!scroller)
    return;
  const bounds = scroller.getBoundingClientRect();
  const above = pointer.y - bounds.top, below = bounds.bottom - pointer.y;
  if (above < EDGE_BAND)
    scroller.scrollTop -= EDGE_SPEED * (1 - Math.max(0, above) / EDGE_BAND);
  else if (below < EDGE_BAND)
    scroller.scrollTop += EDGE_SPEED * (1 - Math.max(0, below) / EDGE_BAND);
}
function beginTreeDrag(event, subject, accepts, drop) {
  if (event.button !== 0)
    return;
  cancelTreeDrag();
  const origin = { x: event.clientX, y: event.clientY };
  const scroller = event.target?.closest("[data-tree-scroll]") ?? null;
  let active = false, frame = 0;
  const tick = () => {
    frame = requestAnimationFrame(tick);
    scrollEdge(scroller);
    resolveTarget(accepts);
    if (preview)
      place(preview);
  };
  const move = (next) => {
    pointer.x = next.clientX;
    pointer.y = next.clientY;
    if (active || Math.abs(next.clientX - origin.x) + Math.abs(next.clientY - origin.y) < THRESHOLD)
      return;
    active = true;
    draggedItem.value = subject;
    document.body.classList.add("gw-tree-dragging");
    frame = requestAnimationFrame(tick);
  };
  const stop = (commit) => {
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", release);
    document.removeEventListener("pointercancel", cancel);
    document.removeEventListener("keydown", escape);
    cancelAnimationFrame(frame);
    pendingDrag = void 0;
    document.body.classList.remove("gw-tree-dragging");
    const target = treeDropTarget.value;
    const landing = foreign;
    draggedItem.value = void 0;
    treeDropTarget.value = void 0;
    foreign = void 0;
    preview = void 0;
    if (!commit || !active)
      return;
    if (target !== void 0)
      drop(target ?? void 0);
    else if (landing)
      for (const handler of foreignHandlers)
        handler({ subject, ...landing });
  };
  const release = () => stop(true);
  const cancel = () => stop(false);
  const escape = (next) => {
    if (next.key === "Escape")
      stop(false);
  };
  pendingDrag = { kind: subject.kind, cancel };
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", release);
  document.addEventListener("pointercancel", cancel);
  document.addEventListener("keydown", escape);
}
export {
  beginTreeDrag,
  cancelTreeDrag,
  draggedItem,
  onForeignDrop,
  registerTreePreview,
  treeDropTarget
};
