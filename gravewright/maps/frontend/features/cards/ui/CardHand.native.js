import { text as gwText } from "../../../shared/config/i18n/text.js";
import { ResourceScope } from "../../../shared/lifecycle/scope.js";
import DeckUpload from "../../table-library/ui/DeckUpload.native.js";
import { cardFace, fanLayout, fanPose } from "../model/hand.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"section","attrs":{"ref":"host","class":"card-hand"},"bind":{"aria-label":"gwText(\"Your hand\")"},"events":[],"children":[{"tag":"header","attrs":{"class":"card-hand__bar"},"bind":{},"events":[],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"select","attrs":{},"bind":{"aria-label":"gwText(\"Deck\")","disabled":"!state.decks.length"},"events":[],"children":[{"tag":"option","attrs":{"value":""},"bind":{},"events":[],"children":[{"value":"gwText(\"No deck available\")"}],"when":"!state.decks.length"},{"tag":"option","attrs":{},"bind":{"key":"d.id","value":"d.id"},"events":[],"children":[{"value":"d.name"}],"each":{"names":["d"],"value":"state.decks"}}],"model":{"path":"deckId","mods":[]}},{"tag":"button","attrs":{},"bind":{"disabled":"busy || !deck?.draw_count"},"events":[{"event":"click","code":"deck && openDraw(deck);","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Draw\")"}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"deck?.draw_count ?? 0"},{"text":" "},{"value":"gwText(\"remaining\")"}]},{"tag":"button","attrs":{},"bind":{"aria-pressed":"manage"},"events":[{"event":"click","code":"manage = !manage;","mods":[]}],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"value":"manage ? gwText(\"Hand\") : gwText(\"Decks\")"}],"when":"gm"}]},{"tag":"p","attrs":{"class":"card-hand__error","role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"div","attrs":{"class":"card-hand__fan"},"bind":{"style":"({ \"--card-width\": `${layout.width}px`, \"--overlap\": `${layout.overlap}px` })"},"events":[],"children":[{"tag":"p","attrs":{"class":"card-hand__empty"},"bind":{},"events":[],"children":[{"value":"gwText(\"Your hand is empty. Draw a card.\")"}],"when":"!cards.length"},{"tag":"article","attrs":{"class":"card-hand__card","tabindex":"0"},"bind":{"key":"card.id","style":"pose(index)","draggable":"!busy","aria-label":"card.name","title":"gwText(\"Drag to the table\")"},"events":[{"event":"dragstart","code":"drag($event, card);","mods":[]},{"event":"dblclick","code":"preview = card;","mods":[]},{"event":"keydown","code":"preview = card;","mods":["enter","prevent"]}],"children":[{"tag":"img","attrs":{"draggable":"false"},"bind":{"src":"cardFace(card, flipped.has(card.id))","alt":"flipped.has(card.id) ? gwText(\"Back\") : card.name"},"events":[],"children":[],"when":"cardFace(card, flipped.has(card.id))"},{"tag":"PhCardsThree","attrs":{"class":"card-hand__back"},"bind":{},"events":[],"children":[],"otherwise":true},{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"card.name"}]},{"tag":"div","attrs":{"class":"card-hand__actions"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"aria-label":"`Ampliar ${card.name}`"},"events":[{"event":"click","code":"preview = card;","mods":[]}],"children":[{"tag":"PhMagnifyingGlassPlus","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"aria-label":"flipped.has(card.id) ? gwText(\"Show front\") : gwText(\"Show back\")"},"events":[{"event":"click","code":"flip(card);","mods":[]}],"children":[{"tag":"PhArrowsClockwise","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Discard card\")"},"events":[{"event":"click","code":"command(\"discard\", { card_ids: [card.id] });","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]}]}]}],"each":{"names":["card","index"],"value":"cards"}}],"when":"!manage"},{"tag":"div","attrs":{"class":"card-hand__decks"},"bind":{},"events":[],"children":[{"tag":"details","attrs":{},"bind":{},"events":[],"children":[{"tag":"summary","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Create deck\")"}]},{"tag":"DeckUpload","attrs":{},"bind":{"container-id":"containerId"},"events":[{"event":"created","code":"refresh;","mods":[]}],"children":[]}]},{"tag":"p","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"No deck in play.\")"}],"when":"!state.decks.length"},{"tag":"article","attrs":{"class":"card-hand__deck"},"bind":{"key":"d.id"},"events":[],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"div","attrs":{},"bind":{},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"d.name"}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"d.draw_count"},{"text":" "},{"value":"gwText(\"cards remaining\")"}]}]},{"tag":"div","attrs":{"class":"card-hand__deck-actions"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"disabled":"busy || !d.draw_count"},"events":[{"event":"click","code":"openDraw(d);","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Draw\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"command(\"shuffle\", { deck_instance_id: d.id });","mods":[]}],"children":[{"tag":"PhShuffle","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Shuffle\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"command(\"reset\", { deck_instance_id: d.id });","mods":[]}],"children":[{"tag":"PhArrowsClockwise","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Recall\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"deleteDeck = d;","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Remove\")"}]}]}],"each":{"names":["d"],"value":"state.decks"}}],"otherwise":true},{"tag":"Teleport","attrs":{"to":"body"},"bind":{},"events":[],"children":[{"tag":"div","attrs":{"class":"card-hand__veil"},"bind":{},"events":[{"event":"keydown","code":"","mods":["stop"]},{"event":"click","code":"preview = void 0;","mods":["self"]},{"event":"keydown","code":"preview = void 0;","mods":["esc","stop"]}],"children":[{"tag":"section","attrs":{"class":"card-hand__preview","role":"dialog","aria-modal":"true"},"bind":{"aria-label":"preview.name"},"events":[],"children":[{"tag":"header","attrs":{},"bind":{},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"flipped.has(preview.id) ? gwText(\"Back\") : preview.name"}]},{"tag":"button","attrs":{"autofocus":""},"bind":{"aria-label":"gwText(\"Close preview\")"},"events":[{"event":"click","code":"preview = void 0;","mods":[]}],"children":[{"tag":"PhX","attrs":{},"bind":{},"events":[],"children":[]}]}]},{"tag":"img","attrs":{},"bind":{"src":"cardFace(preview, flipped.has(preview.id))","alt":"preview.name"},"events":[],"children":[],"when":"cardFace(preview, flipped.has(preview.id))"},{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[],"otherwise":true}]}],"when":"preview"},{"tag":"div","attrs":{"class":"card-hand__veil"},"bind":{},"events":[{"event":"keydown","code":"","mods":["stop"]},{"event":"click","code":"!busy && (drawDeck = void 0);","mods":["self"]},{"event":"keydown","code":"!busy && (drawDeck = void 0);","mods":["esc","stop"]}],"children":[{"tag":"form","attrs":{"class":"card-hand__draw","role":"dialog","aria-modal":"true"},"bind":{"aria-label":"gwText(\"Draw cards\")"},"events":[{"event":"submit","code":"draw;","mods":["prevent"]}],"children":[{"tag":"header","attrs":{},"bind":{},"events":[],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"div","attrs":{},"bind":{},"events":[],"children":[{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"drawDeck.name"}]},{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Draw cards\")"}]}]},{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"busy","aria-label":"gwText(\"Close draw dialog\")"},"events":[{"event":"click","code":"drawDeck = void 0;","mods":[]}],"children":[{"tag":"PhX","attrs":{},"bind":{},"events":[],"children":[]}]}]},{"tag":"div","attrs":{"class":"card-hand__choices"},"bind":{},"events":[],"children":[{"tag":"fieldset","attrs":{},"bind":{"disabled":"busy"},"events":[],"children":[{"tag":"legend","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Destination\")"}]},{"tag":"label","attrs":{},"bind":{"key":"choice.id"},"events":[],"children":[{"tag":"input","attrs":{"type":"radio"},"bind":{"value":"choice.id"},"events":[],"children":[],"model":{"path":"destination","mods":[]}},{"tag":"component","attrs":{},"bind":{"is":"choice.icon"},"events":[],"children":[]},{"value":"choice.label"}],"each":{"names":["choice"],"value":"[{ id: \"hand\", label: gwText(\"Hand\"), icon: PhHand }, { id: \"table\", label: gwText(\"Table\"), icon: PhMapTrifold }, { id: \"chat\", label: \"Chat\", icon: PhChatCircleText }]"}}]},{"tag":"fieldset","attrs":{},"bind":{"disabled":"busy"},"events":[],"children":[{"tag":"legend","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"State\")"}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"tag":"input","attrs":{"type":"radio","value":"face_up"},"bind":{},"events":[],"children":[],"model":{"path":"face","mods":[]}},{"tag":"PhEye","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Front\")"}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"tag":"input","attrs":{"type":"radio","value":"face_down"},"bind":{},"events":[],"children":[],"model":{"path":"face","mods":[]}},{"tag":"PhEyeSlash","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Back\")"}]}]}]},{"tag":"label","attrs":{"class":"card-hand__quantity"},"bind":{},"events":[],"children":[{"value":"gwText(\"Quantity\")"},{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"busy || count <= 1","aria-label":"gwText(\"Decrease quantity\")"},"events":[{"event":"click","code":"count--;","mods":[]}],"children":[{"tag":"PhMinus","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"input","attrs":{"type":"number","min":"1","step":"1","required":""},"bind":{"max":"drawDeck.draw_count","disabled":"busy"},"events":[],"children":[],"model":{"path":"count","mods":["number"]}},{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"busy || count >= drawDeck.draw_count","aria-label":"gwText(\"Increase quantity\")"},"events":[{"event":"click","code":"count++;","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]}]}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"drawDeck.draw_count"},{"value":"gwText(\" available\")"}]}]},{"tag":"p","attrs":{"class":"card-hand__error","role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"footer","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"drawDeck = void 0;","mods":[]}],"children":[{"value":"gwText(\"Cancel\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[],"children":[{"value":"busy ? gwText(\"Drawing\\u2026\") : gwText(\"Draw\")"}]}]}]}],"when":"drawDeck"},{"tag":"div","attrs":{"class":"card-hand__veil"},"bind":{},"events":[{"event":"keydown","code":"","mods":["stop"]}],"children":[{"tag":"section","attrs":{"class":"card-hand__draw","role":"dialog"},"bind":{"aria-label":"gwText(\"Remove deck\")"},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Remove \")"},{"value":"deleteDeck.name"},{"text":"?"}]},{"tag":"p","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"This deck's cards in hands, the discard pile, and the table will be removed.\")"}]},{"tag":"footer","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"deleteDeck = void 0;","mods":[]}],"children":[{"value":"gwText(\"Cancel\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"command(\"delete\", { deck_instance_id: deleteDeck.id }).then((result) => {\n  if (result) deleteDeck = void 0;\n});","mods":[]}],"children":[{"value":"gwText(\"Remove\")"}]}]}]}],"when":"deleteDeck"}]}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const PhCardsThree="PhCardsThree";
const PhPlus="PhPlus";
const PhMinus="PhMinus";
const PhMagnifyingGlassPlus="PhMagnifyingGlassPlus";
const PhArrowsClockwise="PhArrowsClockwise";
const PhTrash="PhTrash";
const PhShuffle="PhShuffle";
const PhX="PhX";
const PhHand="PhHand";
const PhEye="PhEye";
const PhEyeSlash="PhEyeSlash";
const PhChatCircleText="PhChatCircleText";
const PhMapTrifold="PhMapTrifold";
const HttpClient=options.HttpClient;
const props = options.props;
const emit = options.emit;
const scope = new ResourceScope(), http = new HttpClient(void 0, () => scope.signal), root = `/api/containers/${encodeURIComponent(props.containerId)}/library`;
const state = ref({ decks: [], hand: [] }), deckId = ref(""), manage = ref(false), busy = ref(false), error = ref(""), flipped = ref(/* @__PURE__ */ new Set()), preview = ref(), drawDeck = ref(), count = ref(1), destination = ref("hand"), face = ref("face_up"), deleteDeck = ref();
const host = ref(), available = ref(550);
let observer, visit = 0;
const deck = computed(() => state.value.decks.find((d) => d.id === deckId.value));
const cards = computed(() => state.value.hand.filter((c) => c.deck_instance_id === deckId.value));
const layout = computed(() => fanLayout(cards.value.length, available.value - 42));
function pose(index) {
  const p = fanPose(index, cards.value.length);
  return { "--rotation": `${p.rotation}deg`, "--arc": `${p.arc}px`, "--order": index + 1 };
}
async function refresh() {
  const id = ++visit;
  try {
    const next = await http.get(root + "/card-state");
    if (scope.closed || id !== visit) return;
    state.value = next;
    if (!next.decks.some((d) => d.id === deckId.value)) deckId.value = next.decks[0]?.id ?? "";
    flipped.value = new Set([...flipped.value].filter((id2) => next.hand.some((c) => c.id === id2)));
    if (preview.value && !next.hand.some((c) => c.id === preview.value.id)) preview.value = void 0;
  } catch {
    if (!scope.closed) error.value = gwText("Could not load your cards.");
  }
}
async function command(action, data) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const result = await http.post(root + "/cards/" + action, data);
    await refresh();
    return result;
  } catch {
    if (!scope.closed) error.value = gwText("Could not complete the action. The deck may have changed or the action is not allowed.");
  } finally {
    if (!scope.closed) busy.value = false;
  }
}
function openDraw(target) {
  drawDeck.value = target;
  count.value = 1;
  try {
    destination.value = sessionStorage.getItem("gravewright.cards.draw.destination") || "hand";
    face.value = sessionStorage.getItem("gravewright.cards.draw.face") || "face_up";
  } catch {
  }
  if (!["hand", "table", "chat"].includes(destination.value)) destination.value = "hand";
  if (!["face_up", "face_down"].includes(face.value)) face.value = "face_up";
}
async function draw() {
  if (!drawDeck.value || busy.value) return;
  if (destination.value !== "hand" && !props.blockId) {
    error.value = gwText("Open a scene to use this destination.");
    return;
  }
  const result = await command("draw", { deck_instance_id: drawDeck.value.id, count: count.value, destination: destination.value === "table" ? "hand" : destination.value, reveal: face.value === "face_up", ...destination.value === "chat" ? { block_id: props.blockId } : {} });
  if (!result || scope.closed) return;
  try {
    sessionStorage.setItem("gravewright.cards.draw.destination", destination.value);
    sessionStorage.setItem("gravewright.cards.draw.face", face.value);
  } catch {
  }
  drawDeck.value = void 0;
  if (destination.value === "table") emit("place", result.cards ?? [], face.value === "face_up");
}
function flip(card) {
  const next = new Set(flipped.value);
  if (next.has(card.id)) next.delete(card.id);
  else next.add(card.id);
  flipped.value = next;
}
function drag(event, card) {
  if (busy.value) {
    event.preventDefault();
    return;
  }
  event.dataTransfer?.setData("application/x-gravewright-hand-card", JSON.stringify({ cardId: card.id, reveal: !flipped.value.has(card.id) }));
}
watch(() => props.revision, () => void refresh());
function escape(event) {
  if (event.key === "Escape" && !busy.value) {
    preview.value = void 0;
    drawDeck.value = void 0;
    deleteDeck.value = void 0;
  }
}
onMounted(() => {
  window.addEventListener("keydown", escape);
  void refresh();
  observer = new ResizeObserver((entries) => {
    available.value = entries[0]?.contentRect.width ?? 550;
  });
  if (host.value) observer.observe(host.value);
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", escape);
  scope.dispose();
  observer?.disconnect();
});
return {gwText,PhCardsThree,PhPlus,PhMinus,PhMagnifyingGlassPlus,PhArrowsClockwise,PhTrash,PhShuffle,PhX,PhHand,PhEye,PhEyeSlash,PhChatCircleText,PhMapTrifold,HttpClient,ResourceScope,DeckUpload,cardFace,fanLayout,fanPose,props,emit,scope,http,root,state,deckId,manage,busy,error,flipped,preview,drawDeck,count,destination,face,deleteDeck,host,available,observer,visit,deck,cards,layout,pose,refresh,command,openDraw,draw,flip,drag,escape};
});
