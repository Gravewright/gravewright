const shallowRef = () => { let value; return { get value() { return value; }, set value(next) { value = next; window.dispatchEvent(new Event('gravewright:tree-drag')); } }; };
let pendingDrag;
export function cancelTreeDrag(kind) { if (!kind || pendingDrag?.kind === kind)
    pendingDrag?.cancel(); }
const THRESHOLD = 5;
const EDGE_BAND = 44;
const EDGE_SPEED = 13;
const OFFSET_X = 14;
const OFFSET_Y = 11;
/** The subject under the pointer, or undefined when no drag is running. */
export const draggedItem = shallowRef();
/** Folder id under the pointer, `null` for the tree root, undefined when the drop is not allowed. */
export const treeDropTarget = shallowRef();
const pointer = { x: 0, y: 0 };
let preview;
let foreign;
const foreignHandlers = new Set();
/**
 * Listens for drags released on a surface marked `data-drag-drop="<name>"` outside every tree.
 * A tree drop always wins when the two overlap; the returned function unsubscribes.
 */
export function onForeignDrop(handler) {
    foreignHandlers.add(handler);
    return () => { foreignHandlers.delete(handler); };
}
function place(element) { element.style.transform = `translate3d(${pointer.x + OFFSET_X}px, ${pointer.y + OFFSET_Y}px, 0)`; }
// Positioned on registration as well: the chip mounts a frame after the drag starts and would
// otherwise paint once at the viewport origin before the first animation frame moves it.
export function registerTreePreview(element) { preview = element; if (element)
    place(element); }
function resolveTarget(accepts) {
    const element = document.elementFromPoint(pointer.x, pointer.y);
    const surface = element?.closest("[data-tree-drop]");
    const directoryKind = surface?.closest('[data-tree-kind]')?.dataset.treeKind;
    const target = surface && (!directoryKind || directoryKind === draggedItem.value?.kind) ? surface.dataset.treeDrop || null : undefined;
    treeDropTarget.value = target !== undefined && accepts(target) ? target : undefined;
    const outside = treeDropTarget.value === undefined ? element?.closest("[data-drag-drop]")?.dataset.dragDrop : undefined;
    foreign = outside ? { surface: outside, x: pointer.x, y: pointer.y } : undefined;
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
export function beginTreeDrag(event, subject, accepts, drop) {
    if (event.button !== 0)
        return;
    cancelTreeDrag();
    const origin = { x: event.clientX, y: event.clientY };
    const scroller = event.target?.closest("[data-tree-scroll]") ?? null;
    let active = false, frame = 0;
    // Everything positional runs on one animation frame instead of per pointermove, so edge scrolling
    // keeps working while the pointer is held still and no reactive state churns during the drag.
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
        pendingDrag = undefined;
        document.body.classList.remove("gw-tree-dragging");
        const target = treeDropTarget.value;
        const landing = foreign;
        draggedItem.value = undefined;
        treeDropTarget.value = undefined;
        foreign = undefined;
        preview = undefined;
        if (!commit || !active)
            return;
        if (target !== undefined)
            drop(target ?? undefined);
        else if (landing)
            for (const handler of foreignHandlers)
                handler({ subject, ...landing });
    };
    const release = () => stop(true);
    const cancel = () => stop(false);
    const escape = (next) => { if (next.key === "Escape")
        stop(false); };
    pendingDrag = { kind: subject.kind, cancel };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", release);
    document.addEventListener("pointercancel", cancel);
    document.addEventListener("keydown", escape);
}
