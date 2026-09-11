import { text as gwText } from "../../../shared/config/i18n/text.js";
import DirectoryContextMenu from "../../../shared/ui/directory/DirectoryContextMenu.native.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"svg","attrs":{"ref":"root","class":"scene-cards"},"bind":{},"events":[{"event":"pointermove","code":"move;","mods":[]},{"event":"pointerup","code":"up;","mods":[]},{"event":"pointercancel","code":"cancel;","mods":[]}],"children":[{"tag":"g","attrs":{},"bind":{"transform":"`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`"},"events":[],"children":[{"tag":"g","attrs":{},"bind":{"key":"card.id","transform":"`translate(${card.x} ${card.y}) rotate(${card.rotation}) scale(${card.scale || 1})`"},"events":[],"children":[{"tag":"rect","attrs":{"class":"scene-cards__hit","x":"-28","y":"-40","width":"56","height":"80","rx":"5","fill":"transparent","role":"button"},"bind":{"class":"({ \"scene-cards__hit--enabled\": tool === \"select\" && card.can_manage })","stroke":"selected === card.id ? \"#ffe29a\" : \"none\"","stroke-width":"2 / (viewport.scale * (card.scale || 1))","tabindex":"tool === \"select\" && card.can_manage ? 0 : -1","aria-label":"card.card?.face_state === \"face_up\" ? card.card?.name || gwText(\"Card on the table\") : gwText(\"Face-down card\")","aria-pressed":"selected === card.id"},"events":[{"event":"pointerdown","code":"down($event, card);","mods":[]},{"event":"contextmenu","code":"context($event, card);","mods":[]},{"event":"wheel","code":"wheel($event, card);","mods":[]},{"event":"keydown","code":"selected = card.id;","mods":["enter","stop"]}],"children":[]}],"each":{"names":["card"],"value":"rows"}}]}]},{"tag":"p","attrs":{"class":"scene-cards__hint"},"bind":{"role":"error ? \"alert\" : \"status\""},"events":[],"children":[{"value":"error || (busy ? gwText(\"Saving card\\u2026\") : gwText(\"Drag to move \\xB7 Shift + wheel to rotate \\xB7 F to flip \\xB7 Delete to discard\"))"}],"when":"error || busy || selected"},{"tag":"Teleport","attrs":{"to":"body"},"bind":{},"events":[],"children":[{"tag":"DirectoryContextMenu","attrs":{},"bind":{"x":"menu.x","y":"menu.y","label":"gwText(\"Card on the table\")"},"events":[{"event":"close","code":"menu = void 0;","mods":[]}],"children":[{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"flip;","mods":[]}],"children":[{"tag":"PhArrowsClockwise","attrs":{},"bind":{},"events":[],"children":[]},{"value":"current.card?.face_state === \"face_up\" ? gwText(\"Flip face down\") : gwText(\"Flip face up\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"rotate(-90);","mods":[]}],"children":[{"tag":"PhArrowCounterClockwise","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Rotate 90\\xB0 left\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"rotate(90);","mods":[]}],"children":[{"tag":"PhArrowClockwise","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Rotate 90\\xB0 right\")"}]},{"tag":"button","attrs":{"class":"gw-folder-menu__danger"},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"remove;","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Remove from table (discard)\")"}]}],"when":"menu && current"}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const PhArrowsClockwise="PhArrowsClockwise";
const PhArrowClockwise="PhArrowClockwise";
const PhArrowCounterClockwise="PhArrowCounterClockwise";
const PhTrash="PhTrash";
const BlockStateApi=class {command(c,b,area,action,data){return options.command(area,action,data)}state(){return options.read()}};
const HttpClient=options.HttpClient;
const props = options.props;
const emit = options.emit;
const root = ref(), selected = ref(""), preview = ref(), busy = ref(false), error = ref(""), menu = ref();
const abort = new AbortController(), api = new BlockStateApi(new HttpClient(void 0, () => abort.signal));
const rows = computed(() => [...props.cards].sort((a, b) => (a.z_index ?? 0) - (b.z_index ?? 0)).map((c) => preview.value?.id === c.id ? preview.value : c));
const current = computed(() => rows.value.find((c) => c.id === selected.value));
let drag, rotationTimer;
function show(card) {
  preview.value = card;
  emit("preview", card);
}
function point(e) {
  const b = root.value.getBoundingClientRect();
  return { x: (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - b.top - props.viewport.y) / props.viewport.scale };
}
function release() {
  if (drag && root.value?.hasPointerCapture(drag.pointer)) root.value.releasePointerCapture(drag.pointer);
  drag = void 0;
}
function cancel() {
  release();
  clearTimeout(rotationTimer);
  rotationTimer = void 0;
  show();
  menu.value = void 0;
}
function down(e, card) {
  if (e.button !== 0 || props.tool !== "select" || busy.value || !card.can_manage) return;
  e.preventDefault();
  e.stopPropagation();
  clearTimeout(rotationTimer);
  rotationTimer = void 0;
  selected.value = card.id;
  menu.value = void 0;
  error.value = "";
  drag = { pointer: e.pointerId, point: point(e), card: { ...card } };
  root.value?.setPointerCapture(e.pointerId);
}
function move(e) {
  if (!drag || e.pointerId !== drag.pointer) return;
  e.stopPropagation();
  const p = point(e);
  show({ ...drag.card, x: drag.card.x + p.x - drag.point.x, y: drag.card.y + p.y - drag.point.y });
}
async function command(action, data) {
  if (busy.value || !current.value?.can_manage) return;
  busy.value = true;
  menu.value = void 0;
  error.value = "";
  try {
    await api.command(props.containerId, props.blockId, "cards", action, { placement_id: selected.value, ...data });
    if (!abort.signal.aborted) emit("refresh");
  } catch {
    if (!abort.signal.aborted) {
      show();
      error.value = gwText("Could not change the card. Refreshing the scene\u2026");
      emit("refresh");
    }
  } finally {
    if (!abort.signal.aborted) busy.value = false;
  }
}
function up(e) {
  if (!drag || drag.pointer !== e.pointerId) return;
  move(e);
  e.stopPropagation();
  const original = drag.card, next = preview.value;
  release();
  if (next && (next.x !== original.x || next.y !== original.y)) void command("update", { x: next.x, y: next.y, rotation: next.rotation });
  else show();
}
function context(e, card) {
  if (props.tool !== "select" || !card.can_manage) return;
  e.preventDefault();
  e.stopPropagation();
  cancel();
  selected.value = card.id;
  menu.value = { x: e.clientX, y: e.clientY };
}
function rotate(degrees, defer = false) {
  if (busy.value || drag || !current.value?.can_manage) return;
  const c = { ...current.value, rotation: ((current.value.rotation + degrees) % 360 + 360) % 360 };
  show(c);
  clearTimeout(rotationTimer);
  const save = () => {
    rotationTimer = void 0;
    void command("update", { rotation: c.rotation });
  };
  if (defer) rotationTimer = setTimeout(save, 180);
  else save();
}
function wheel(e, card) {
  if (props.tool !== "select" || !e.shiftKey || !card.can_manage) return;
  e.preventDefault();
  e.stopPropagation();
  if (selected.value !== card.id) {
    cancel();
    selected.value = card.id;
  }
  rotate(e.deltaY > 0 ? 15 : -15, true);
}
function flip() {
  cancel();
  void command("update", { face_state: current.value?.card?.face_state === "face_up" ? "face_down" : "face_up" });
}
function remove() {
  cancel();
  void command("delete", {});
}
function outside(e) {
  if (e.target instanceof Element && (e.target.closest(".scene-cards__hit") || menu.value && e.target.closest(".directory-context-menu"))) return;
  if (!drag) {
    cancel();
    selected.value = "";
  }
}
function key(e) {
  if (props.tool !== "select" || !selected.value || e.target instanceof Element && e.target.closest("input,textarea,select,[contenteditable=true]")) return;
  if (e.key === "Escape") {
    e.stopImmediatePropagation();
    cancel();
    selected.value = "";
  } else if (["Delete", "Backspace", "f", "F"].includes(e.key)) {
    e.preventDefault();
    e.stopImmediatePropagation();
    if (!busy.value) {
      if (e.key.toLowerCase() === "f") flip();
      else remove();
    }
  }
}
watch(() => props.cards, (cards) => {
  if (drag && !cards.some((c) => c.id === drag.card.id && c.x === drag.card.x && c.y === drag.card.y && c.rotation === drag.card.rotation)) cancel();
  if (!drag && !rotationTimer) show();
  if (!cards.some((c) => c.id === selected.value && c.can_manage)) selected.value = "";
});
watch(() => props.tool, () => {
  cancel();
  selected.value = "";
});
onMounted(() => {
  document.addEventListener("pointerdown", outside, true);
  window.addEventListener("keydown", key, true);
  window.addEventListener("blur", cancel);
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", outside, true);
  abort.abort();
  cancel();
  window.removeEventListener("keydown", key, true);
  window.removeEventListener("blur", cancel);
});
return {gwText,PhArrowsClockwise,PhArrowClockwise,PhArrowCounterClockwise,PhTrash,BlockStateApi,HttpClient,DirectoryContextMenu,props,emit,root,selected,preview,busy,error,menu,abort,api,rows,current,drag,rotationTimer,show,point,release,cancel,down,move,command,up,context,rotate,wheel,flip,remove,outside,key};
});
