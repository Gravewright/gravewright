import { text as gwText } from "../../../shared/config/i18n/text.js";
import { cardFace } from "../model/hand.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"svg","attrs":{"ref":"root","class":"card-placement"},"bind":{},"events":[{"event":"pointermove","code":"move;","mods":["stop"]},{"event":"pointerdown","code":"place;","mods":["stop","prevent"]},{"event":"pointerup","code":"","mods":["stop"]},{"event":"contextmenu","code":"!busy && emit(\"close\");","mods":["stop","prevent"]}],"children":[{"tag":"g","attrs":{"opacity":".75"},"bind":{"transform":"`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale}) translate(${point.x} ${point.y})`"},"events":[],"children":[{"tag":"rect","attrs":{"x":"-28","y":"-40","width":"56","height":"80","rx":"5","fill":"#182328","stroke":"#c09a5a"},"bind":{},"events":[],"children":[]},{"tag":"image","attrs":{"x":"-28","y":"-40","width":"56","height":"80"},"bind":{"href":"cardFace(cards[index], !reveal)"},"events":[],"children":[]}],"when":"point && cards[index]"}]},{"tag":"p","attrs":{"class":"card-placement__hint","role":"status"},"bind":{},"events":[],"children":[{"value":"error || (busy ? gwText(\"Playing card\\u2026\") : gwText(\"Click to play {0}/{1}. Esc cancels; remaining cards stay in your hand.\", index + 1, cards.length))"}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const BlockStateApi=class {command(c,b,area,action,data){return options.command(area,action,data)}state(){return options.read()}};
const HttpClient=options.HttpClient;
const props = options.props;
const emit = options.emit;
const root = ref(), point = ref(), busy = ref(false), index = ref(0), error = ref("");
const abort = new AbortController(), api = new BlockStateApi(new HttpClient(void 0, () => abort.signal));
function move(e) {
  const box = root.value.getBoundingClientRect();
  point.value = { x: (e.clientX - box.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - box.top - props.viewport.y) / props.viewport.scale };
}
async function place(e) {
  if (e.button !== 0 || busy.value) return;
  e.stopPropagation();
  move(e);
  const card = props.cards[index.value];
  if (!card || !point.value) return;
  busy.value = true;
  try {
    await api.command(props.containerId, props.blockId, "cards", "play", { card_id: card.id, ...point.value, reveal: props.reveal });
    if (abort.signal.aborted) return;
    emit("refresh");
    index.value++;
    if (index.value >= props.cards.length) emit("close");
  } catch {
    if (!abort.signal.aborted) error.value = gwText("Could not play the card. Try again.");
  } finally {
    busy.value = false;
  }
}
function cancel(e) {
  if (e.key === "Escape" && !busy.value) {
    e.stopPropagation();
    emit("close");
  }
}
onMounted(() => window.addEventListener("keydown", cancel));
onBeforeUnmount(() => {
  abort.abort();
  window.removeEventListener("keydown", cancel);
});
return {gwText,BlockStateApi,HttpClient,cardFace,props,emit,root,point,busy,index,error,abort,api,move,place,cancel};
});
