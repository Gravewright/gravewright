import { text as gwText } from "../../../shared/config/i18n/text.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"section","attrs":{"class":"soundtrack-panel"},"bind":{},"events":[],"children":[{"tag":"header","attrs":{},"bind":{},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Soundtracks and ambience\")"}]},{"tag":"button","attrs":{},"bind":{},"events":[{"event":"click","code":"create(\"playlist\");","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]},{"text":"Playlist"}]},{"tag":"button","attrs":{},"bind":{},"events":[{"event":"click","code":"create(\"preset\");","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]},{"text":"Preset"}]}]},{"tag":"p","attrs":{"role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"form","attrs":{},"bind":{},"events":[{"event":"submit","code":"save;","mods":["prevent"]}],"children":[{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Name\")"},{"tag":"input","attrs":{"required":"","maxlength":"80"},"bind":{},"events":[],"children":[],"model":{"path":"name","mods":[]}}]},{"tag":"div","attrs":{"class":"soundtrack-panel__row"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{"type":"button"},"bind":{"key":"label"},"events":[{"event":"click","code":"name = label;","mods":[]}],"children":[{"value":"label"}],"each":{"names":["label"],"value":"[gwText(\"Exploration\"), gwText(\"Tavern\"), gwText(\"Combat\")]"}}],"when":"kind === \"preset\""},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Order\")"},{"tag":"select","attrs":{},"bind":{},"events":[],"children":[{"tag":"option","attrs":{"value":"sequential"},"bind":{},"events":[],"children":[{"value":"gwText(\"Sequential\")"}]},{"tag":"option","attrs":{"value":"shuffle"},"bind":{},"events":[],"children":[{"value":"gwText(\"Random\")"}]}],"model":{"path":"mode","mods":[]}}],"when":"kind === \"playlist\""},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Transition (seconds)\")"},{"tag":"input","attrs":{"type":"number","min":"0","max":"30","step":"0.5","required":""},"bind":{},"events":[],"children":[],"model":{"path":"fade","mods":["number"]}}]},{"tag":"div","attrs":{"class":"soundtrack-panel__row"},"bind":{},"events":[],"children":[{"tag":"select","attrs":{},"bind":{"aria-label":"gwText(\"Add track\")"},"events":[],"children":[{"tag":"option","attrs":{"value":""},"bind":{},"events":[],"children":[{"value":"gwText(\"Choose a sound\")"}]},{"tag":"option","attrs":{},"bind":{"key":"s.id","value":"s.id"},"events":[],"children":[{"value":"s.name"}],"each":{"names":["s"],"value":"sounds"}}],"model":{"path":"chosen","mods":[]}},{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"busy || !chosen || entries.length >= 64"},"events":[{"event":"click","code":"add;","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]}]}]},{"tag":"ol","attrs":{},"bind":{},"events":[],"children":[{"tag":"li","attrs":{},"bind":{"key":"index"},"events":[],"children":[{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"sounds.find((s) => s.id === entry.soundId)?.name"},{"text":" "},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"time(entry.duration)"}]},{"tag":"input","attrs":{"type":"range","min":"0","max":"1","step":"0.01"},"bind":{"aria-label":"gwText(\"Layer volume\")"},"events":[],"children":[],"model":{"path":"entry.gain","mods":["number"]}}]},{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"index === 0","aria-label":"gwText(\"Move track up\")"},"events":[{"event":"click","code":"entries.splice(index - 1, 0, entries.splice(index, 1)[0]);","mods":[]}],"children":[{"tag":"PhArrowUp","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"index === entries.length - 1","aria-label":"gwText(\"Move track down\")"},"events":[{"event":"click","code":"entries.splice(index + 1, 0, entries.splice(index, 1)[0]);","mods":[]}],"children":[{"tag":"PhArrowDown","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{"type":"button"},"bind":{"aria-label":"gwText(\"Remove track\")"},"events":[{"event":"click","code":"entries.splice(index, 1);","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]}]}],"each":{"names":["entry","index"],"value":"entries"}}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"kind === \"preset\" ? gwText(\"Layers play together and loop.\") : gwText(\"Tracks advance automatically with crossfades.\")"}]},{"tag":"div","attrs":{"class":"soundtrack-panel__row"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{"type":"submit"},"bind":{"disabled":"busy || !entries.length"},"events":[],"children":[{"value":"gwText(\"Save\")"}]},{"tag":"button","attrs":{"type":"button"},"bind":{},"events":[{"event":"click","code":"editing = false;","mods":[]}],"children":[{"value":"gwText(\"Cancel\")"}]}]}],"when":"editing"},{"tag":"template","attrs":{},"bind":{},"events":[],"children":[{"tag":"label","attrs":{"class":"soundtrack-panel__repeat"},"bind":{},"events":[],"children":[{"tag":"input","attrs":{"type":"checkbox"},"bind":{},"events":[],"children":[],"model":{"path":"repeat","mods":[]}},{"value":"gwText(\"Loop playlist\")"}]},{"tag":"article","attrs":{},"bind":{"key":"item.id"},"events":[],"children":[{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"item.name"},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"item.kind === \"preset\" ? gwText(\"Ambience\") : item.playback_mode === \"shuffle\" ? gwText(\"Shuffled playlist\") : gwText(\"Sequential playlist\")"}]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Play composition\")"},"events":[{"event":"click","code":"command(\"start\", { id: item.id, kind: item.kind, repeat });","mods":[]}],"children":[{"tag":"PhPlay","attrs":{},"bind":{},"events":[],"children":[]}]}],"each":{"names":["item"],"value":"[...lists.playlists.map((x) => ({ ...x, kind: \"playlist\" })), ...lists.presets.map((x) => ({ ...x, kind: \"preset\" }))]"}}],"otherwise":true},{"tag":"div","attrs":{"class":"soundtrack-panel__transport"},"bind":{},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"state.name"}]},{"tag":"span","attrs":{},"bind":{"key":"track.id"},"events":[],"children":[{"value":"track.name"},{"text":" · "},{"value":"time(track.position ?? Date.now() / 1e3 - track.startedAt)"},{"text":" / "},{"value":"time(track.duration)"}],"each":{"names":["track"],"value":"state.playbacks.filter((t) => t.startedAt <= Date.now() / 1e3 && !t.fade)"}},{"tag":"div","attrs":{"class":"soundtrack-panel__row"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"aria-label":"gwText(\"Previous track\")","disabled":"busy"},"events":[{"event":"click","code":"command(\"previous\");","mods":[]}],"children":[{"tag":"PhSkipBack","attrs":{},"bind":{},"events":[],"children":[]}],"when":"state.kind === \"playlist\""},{"tag":"button","attrs":{},"bind":{"aria-label":"state.state === \"paused\" ? gwText(\"Resume\") : gwText(\"Pause\")","disabled":"busy"},"events":[{"event":"click","code":"command(state.state === \"paused\" ? \"resume\" : \"pause\");","mods":[]}],"children":[{"tag":"component","attrs":{},"bind":{"is":"state.state === \"paused\" ? PhPlay : PhPause"},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"aria-label":"gwText(\"Stop composition\")","disabled":"busy"},"events":[{"event":"click","code":"command(\"stop\");","mods":[]}],"children":[{"tag":"PhStop","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"aria-label":"gwText(\"Next track\")","disabled":"busy"},"events":[{"event":"click","code":"command(\"next\");","mods":[]}],"children":[{"tag":"PhSkipForward","attrs":{},"bind":{},"events":[],"children":[]}],"when":"state.kind === \"playlist\""}]}],"when":"state.state !== \"stopped\""}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const PhPlay="PhPlay";
const PhPause="PhPause";
const PhStop="PhStop";
const PhSkipForward="PhSkipForward";
const PhSkipBack="PhSkipBack";
const PhPlus="PhPlus";
const PhTrash="PhTrash";
const PhArrowUp="PhArrowUp";
const PhArrowDown="PhArrowDown";
const HttpClient=options.HttpClient;
const props = options.props;
const emit = options.emit;
const scope = new AbortController(), http = new HttpClient(void 0, () => scope.signal), base = `/api/containers/${props.containerId}`;
const lists = ref({ playlists: [], presets: [] }), state = ref({ state: "stopped", version: 0, playbacks: [] });
const editing = ref(false), kind = ref("playlist"), name = ref(""), mode = ref("sequential"), fade = ref(2), repeat = ref(true), chosen = ref(""), busy = ref(false), error = ref("");
const entries = ref([]);
let timer;
const probes = /* @__PURE__ */ new Set();
const time = (seconds) => `${Math.floor(Math.max(0, seconds) / 60)}:${String(Math.floor(Math.max(0, seconds) % 60)).padStart(2, "0")}`;
async function refresh() {
  try {
    state.value = await http.get(base + `/blocks/${props.blockId}/soundtrack`);
  } catch {
    if (!scope.signal.aborted) error.value = gwText("Could not update playback.");
  }
}
async function definitions() {
  lists.value = await http.get(base + "/soundtracks");
}
async function add() {
  if (!chosen.value || busy.value) return;
  const sound = props.sounds.find((s) => s.id === chosen.value), asset = props.assets.find((a) => a.id === sound?.asset_id);
  if (!sound || !asset) return;
  busy.value = true;
  error.value = "";
  const audio = new Audio();
  probes.add(audio);
  try {
    const duration = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => finish(new Error(gwText("Could not read the file duration."))), 8e3);
      const finish = (error2) => {
        clearTimeout(timeout);
        scope.signal.removeEventListener("abort", cancel);
        audio.onloadedmetadata = null;
        audio.onerror = null;
        error2 ? reject(error2) : resolve(audio.duration);
      };
      const cancel = () => finish(new Error("cancelled"));
      scope.signal.addEventListener("abort", cancel, { once: true });
      audio.onloadedmetadata = () => Number.isFinite(audio.duration) && audio.duration >= 1 ? finish() : finish(new Error(gwText("Invalid duration.")));
      audio.onerror = () => finish(new Error(gwText("Could not open the audio.")));
      audio.preload = "metadata";
      audio.src = asset.src;
    });
    if (!scope.signal.aborted) entries.value.push({ soundId: sound.id, duration, gain: 1 });
  } catch (e) {
    if (!scope.signal.aborted) error.value = e.message;
  } finally {
    audio.removeAttribute("src");
    audio.load();
    probes.delete(audio);
    busy.value = false;
  }
}
async function save() {
  busy.value = true;
  error.value = "";
  try {
    await http.post(base + "/soundtracks", { kind: kind.value, name: name.value, mode: mode.value, fade: fade.value, entries: entries.value });
    await definitions();
    editing.value = false;
  } catch {
    error.value = gwText("Could not save the composition.");
  } finally {
    busy.value = false;
  }
}
async function command(action, data = {}) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    state.value = await http.post(base + `/blocks/${props.blockId}/soundtrack/${action}`, { ...data, expectedVersion: state.value.version });
    emit("refresh");
  } catch {
    if (!scope.signal.aborted) {
      error.value = gwText("Playback changed or the action was refused. Try again.");
      await refresh();
    }
  } finally {
    busy.value = false;
  }
}
function create(type, label = "") {
  kind.value = type;
  name.value = label;
  entries.value = [];
  editing.value = true;
}
onMounted(() => {
  void definitions().catch(() => error.value = gwText("Could not load compositions."));
  void refresh();
  timer = setInterval(() => {
    if (!busy.value) void refresh();
  }, 1e3);
});
onBeforeUnmount(() => {
  scope.abort();
  clearInterval(timer);
  for (const audio of probes) {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
  }
});
return {gwText,PhPlay,PhPause,PhStop,PhSkipForward,PhSkipBack,PhPlus,PhTrash,PhArrowUp,PhArrowDown,HttpClient,props,emit,scope,http,base,lists,state,editing,kind,name,mode,fade,repeat,chosen,busy,error,entries,timer,probes,time,refresh,definitions,add,save,command,create};
});
