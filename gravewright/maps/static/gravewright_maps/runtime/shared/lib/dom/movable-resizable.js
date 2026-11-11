// shared/lib/dom/movable-resizable.js
var cleanups = /* @__PURE__ */ new WeakMap();
var windows = /* @__PURE__ */ new Set();
function mount(element) {
  const doc = element.ownerDocument, view = doc.defaultView;
  const originalZ = element.style.zIndex;
  const entry = { element, base: Number.parseInt(view.getComputedStyle(element).zIndex) || 7 };
  windows.add(entry);
  function raise() {
    const doc2 = element.ownerDocument;
    const peers = [...windows].filter((w) => w.element.ownerDocument === doc2 && w.base === entry.base);
    windows.delete(entry);
    windows.add(entry);
    for (const peer of peers)
      peer.element.classList.toggle("gw-window--focused", peer === entry);
    [...windows].filter((w) => w.element.ownerDocument === doc2 && w.base === entry.base).forEach((w, index) => {
      w.element.style.zIndex = String(w.base + index);
    });
  }
  element.classList.add("gw-movable-resizable");
  const handle = element.querySelector("[data-move-handle]") ?? element;
  handle.classList.add("gw-move-handle");
  let stopDrag = () => {
  };
  const pointerDown = (event) => {
    if (event.button !== 0 || event.target.closest("button,input,select,textarea,a,[data-no-move]"))
      return;
    stopDrag();
    const doc2 = element.ownerDocument, view2 = doc2.defaultView;
    const bounds = element.getBoundingClientRect(), offsetX = event.clientX - bounds.left, offsetY = event.clientY - bounds.top;
    Object.assign(element.style, { position: "fixed", width: `${bounds.width}px`, height: `${bounds.height}px`, left: `${bounds.left}px`, top: `${bounds.top}px`, right: "auto", bottom: "auto" });
    const move = (next) => {
      if (next.pointerId !== event.pointerId)
        return;
      element.style.left = `${Math.min(view2.innerWidth - 55, Math.max(55 - element.offsetWidth, next.clientX - offsetX))}px`;
      element.style.top = `${Math.min(view2.innerHeight - 55, Math.max(0, next.clientY - offsetY))}px`;
    };
    const up = () => {
      doc2.removeEventListener("pointermove", move);
      doc2.removeEventListener("pointerup", up);
      doc2.removeEventListener("pointercancel", up);
      view2.removeEventListener("blur", up);
      handle.classList.remove("gw-move-handle--active");
      stopDrag = () => {
      };
    };
    stopDrag = up;
    handle.classList.add("gw-move-handle--active");
    doc2.addEventListener("pointermove", move);
    doc2.addEventListener("pointerup", up);
    doc2.addEventListener("pointercancel", up);
    view2.addEventListener("blur", up);
    event.preventDefault();
  };
  const resize = () => {
    const box = element.getBoundingClientRect();
    if (box.top > view.innerHeight - 55)
      element.style.top = `${Math.max(0, view.innerHeight - 55)}px`;
    if (box.left > view.innerWidth - 55) {
      element.style.left = `${Math.max(0, view.innerWidth - 55)}px`;
      element.style.right = "auto";
    }
  };
  element.addEventListener("pointerdown", raise, true);
  element.addEventListener("focusin", raise);
  handle.addEventListener("pointerdown", pointerDown);
  view.addEventListener("resize", resize);
  raise();
  cleanups.set(element, () => {
    stopDrag();
    windows.delete(entry);
    element.style.zIndex = originalZ;
    element.classList.remove("gw-window--focused");
    element.removeEventListener("pointerdown", raise, true);
    element.removeEventListener("focusin", raise);
    handle.removeEventListener("pointerdown", pointerDown);
    view.removeEventListener("resize", resize);
  });
}
var vMovableResizable = { mounted: mount, unmounted(element) {
  cleanups.get(element)?.();
  cleanups.delete(element);
} };
export {
  vMovableResizable
};
