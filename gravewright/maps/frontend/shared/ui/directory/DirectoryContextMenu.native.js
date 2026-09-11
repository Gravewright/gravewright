
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"menu","attrs":{"ref":"menu","class":"gw-folder-menu directory-context-menu"},"bind":{"aria-label":"label","style":"{ left: `${position.x}px`, top: `${position.y}px` }"},"events":[{"event":"click","code":"","mods":["stop"]},{"event":"contextmenu","code":"","mods":["prevent","stop"]}],"children":[{"tag":"slot","attrs":{},"bind":{},"events":[],"children":[]}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const props = options.props;
const emit = options.emit;
const menu = ref();
const position = ref({ x: props.x, y: props.y });
function place() {
  const rect = menu.value?.getBoundingClientRect();
  if (rect) position.value = { x: Math.max(8, Math.min(props.x, innerWidth - rect.width - 8)), y: Math.max(8, Math.min(props.y, innerHeight - rect.height - 8)) };
}
function outside(event) {
  if (!menu.value?.contains(event.target)) emit("close");
}
function other(event) {
  if (event.detail !== menu.value) emit("close");
}
function keyboard(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
    return;
  }
  if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
  const buttons = [...menu.value?.querySelectorAll("button:not(:disabled)") ?? []];
  if (!buttons.length) return;
  event.preventDefault();
  const index = buttons.indexOf(document.activeElement);
  buttons[event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : (index + (event.key === "ArrowUp" ? -1 : 1) + buttons.length) % buttons.length]?.focus();
}
watch(() => [props.x, props.y], async () => {
  await nextTick();
  place();
});
onMounted(() => {
  place();
  document.dispatchEvent(new CustomEvent("gravewright:directory-menu", { detail: menu.value }));
  document.addEventListener("gravewright:directory-menu", other);
  document.addEventListener("pointerdown", outside);
  document.addEventListener("contextmenu", outside);
  document.addEventListener("keydown", keyboard);
  window.addEventListener("resize", place);
});
onBeforeUnmount(() => {
  document.removeEventListener("gravewright:directory-menu", other);
  document.removeEventListener("pointerdown", outside);
  document.removeEventListener("contextmenu", outside);
  document.removeEventListener("keydown", keyboard);
  window.removeEventListener("resize", place);
});
return {props,emit,menu,position,place,outside,other,keyboard};
});
