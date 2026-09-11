import { text as gwText } from "../../../shared/config/i18n/text.js";
import SoundtrackPanel from "./SoundtrackPanel.native.js";
import { transformedPoint } from "../../selection/model/objects.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"svg","attrs":{"ref":"root","class":"audio-workspace"},"bind":{"class":"({ \"audio-workspace--placing\": placing })"},"events":[{"event":"pointermove","code":"move;","mods":[]},{"event":"pointerdown","code":"place;","mods":[]}],"children":[{"tag":"g","attrs":{},"bind":{"transform":"`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`"},"events":[],"children":[{"tag":"g","attrs":{},"bind":{"key":"source.id","transform":"sourceTransform(source)"},"events":[],"children":[{"tag":"circle","attrs":{"fill":"#65c9b808","stroke":"#65c9b8"},"bind":{"cx":"source.x","cy":"source.y","r":"source.radius","stroke-opacity":"0.35","stroke-width":"1 / viewport.scale"},"events":[],"children":[]},{"tag":"circle","attrs":{"class":"audio-workspace__source"},"bind":{"cx":"source.x","cy":"source.y","r":"9 / viewport.scale","fill":"source.enabled ? \"#65c9b8\" : \"#777\""},"events":[{"event":"dblclick","code":"edit(source.id);","mods":["stop"]}],"children":[]},{"tag":"text","attrs":{"fill":"#b1e7dc"},"bind":{"x":"source.x + 13 / viewport.scale","y":"source.y","font-size":"11 / viewport.scale"},"events":[],"children":[{"value":"library.sounds.find((s) => s.id === source.sound_id)?.name || gwText(\"Audio source\")"}]}],"each":{"names":["source"],"value":"state.spatialSounds"}},{"tag":"circle","attrs":{"fill":"#65c9b822","stroke":"#65c9b8"},"bind":{"cx":"position.x","cy":"position.y","r":"radius * toPixels","stroke-width":"2 / viewport.scale"},"events":[],"children":[],"when":"placing && position"}]}],"when":"viewport && !embedded"},{"tag":"Teleport","attrs":{"to":"body"},"bind":{"disabled":"embedded"},"events":[],"children":[{"tag":"section","attrs":{"class":"audio-panel"},"bind":{"class":"({ \"audio-panel--embedded\": embedded })","aria-label":"gwText(\"Scene audio\")"},"events":[],"children":[{"tag":"header","attrs":{},"bind":{},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"tag":"PhWaveform","attrs":{},"bind":{},"events":[],"children":[]},{"value":"editor ? gwText(\"Edit source\") : gwText(\"Scene audio\")"}]},{"tag":"button","attrs":{},"bind":{"aria-label":"gwText(\"Close audio\")"},"events":[{"event":"click","code":"close;","mods":[]}],"children":[{"tag":"PhX","attrs":{},"bind":{},"events":[],"children":[]}],"when":"!embedded"}]},{"tag":"p","attrs":{"role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"button","attrs":{},"bind":{},"events":[{"event":"click","code":"emit(\"unlock\");","mods":[]}],"children":[{"tag":"PhSpeakerHigh","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Play this scene's audio\")"}]},{"tag":"template","attrs":{},"bind":{},"events":[],"children":[{"tag":"form","attrs":{"class":"audio-panel__editor"},"bind":{},"events":[{"event":"submit","code":"save;","mods":["prevent"]}],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"library.sounds.find((s) => s.id === chosen)?.name"}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Range (\")"},{"value":"unit"},{"text":")"},{"tag":"input","attrs":{"type":"number","min":"0.01","max":"100000","step":"any","required":""},"bind":{},"events":[],"children":[],"model":{"path":"radius","mods":["number"]}}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"text":"Volume "},{"value":"Math.round(gain * 100)"},{"text":"%"},{"tag":"input","attrs":{"type":"range","min":"0","max":"1","step":"0.01"},"bind":{},"events":[],"children":[],"model":{"path":"gain","mods":["number"]}}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Volume falloff\")"},{"tag":"select","attrs":{},"bind":{},"events":[],"children":[{"tag":"option","attrs":{"value":"smooth"},"bind":{},"events":[],"children":[{"value":"gwText(\"Smooth\")"}]},{"tag":"option","attrs":{"value":"linear"},"bind":{},"events":[],"children":[{"text":"Linear"}]}],"model":{"path":"falloff","mods":[]}}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"tag":"input","attrs":{"type":"checkbox"},"bind":{},"events":[],"children":[],"model":{"path":"loop","mods":[]}},{"value":"gwText(\"Loop\")"}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"tag":"input","attrs":{"type":"checkbox"},"bind":{},"events":[],"children":[],"model":{"path":"walls","mods":[]}},{"value":"gwText(\"Respect walls\")"}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"tag":"input","attrs":{"type":"checkbox"},"bind":{},"events":[],"children":[],"model":{"path":"enabled","mods":[]}},{"value":"gwText(\"Active\")"}]},{"tag":"button","attrs":{"type":"submit"},"bind":{"disabled":"busy"},"events":[],"children":[{"value":"gwText(\"Save source\")"}],"when":"editor"},{"tag":"p","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Click the map to place the source. Esc cancels.\")"}],"otherwise":true}],"when":"editor || placing"},{"tag":"template","attrs":{},"bind":{},"events":[],"children":[{"tag":"input","attrs":{},"bind":{"aria-label":"gwText(\"Search audio\")","placeholder":"gwText(\"Search the table library\")"},"events":[],"children":[],"model":{"path":"query","mods":[]}},{"tag":"div","attrs":{"class":"audio-panel__list"},"bind":{},"events":[],"children":[{"tag":"article","attrs":{},"bind":{"key":"sound.id"},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"sound.name"},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"sound.kind === \"music\" ? gwText(\"Music\") : sound.kind === \"ambience\" ? gwText(\"Ambience\") : gwText(\"Effect\")"}]}]},{"tag":"div","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"title":"gwText(\"Local preview\")","aria-label":"gwText(\"Local preview\")"},"events":[{"event":"click","code":"listen(sound);","mods":[]}],"children":[{"tag":"PhSpeakerHigh","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"command(\"audio\", \"play\", { sound_id: sound.id });","mods":[]}],"children":[{"tag":"PhPlay","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Scene\")"}],"when":"sound.kind !== \"sound-effect\""},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"select(sound);","mods":[]}],"children":[{"value":"gwText(\"Place\")"}],"when":"viewport"}]}],"each":{"names":["sound"],"value":"sounds"}}]},{"tag":"details","attrs":{},"bind":{},"events":[],"children":[{"tag":"summary","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Add library file\")"}]},{"tag":"label","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Category\")"},{"tag":"select","attrs":{},"bind":{},"events":[],"children":[{"tag":"option","attrs":{"value":"music"},"bind":{},"events":[],"children":[{"value":"gwText(\"Music\")"}]},{"tag":"option","attrs":{"value":"ambience"},"bind":{},"events":[],"children":[{"value":"gwText(\"Ambience\")"}]},{"tag":"option","attrs":{"value":"sound-effect"},"bind":{},"events":[],"children":[{"value":"gwText(\"Effect\")"}]}],"model":{"path":"category","mods":[]}}]},{"tag":"article","attrs":{},"bind":{"key":"asset.id"},"events":[],"children":[{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"asset.name || asset.filename"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"register(asset);","mods":[]}],"children":[{"value":"gwText(\"Add\")"}]}],"each":{"names":["asset"],"value":"library.assets.filter((a) => a.content_type.startsWith(\"audio/\"))"}},{"tag":"p","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Upload files through Library at the top.\")"}]}]}],"otherwise":true},{"tag":"SoundtrackPanel","attrs":{},"bind":{"key":"blockId","container-id":"containerId","block-id":"blockId","sounds":"library.sounds","assets":"library.assets"},"events":[{"event":"refresh","code":"emit(\"refresh\");","mods":[]}],"children":[]},{"tag":"h4","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Playback in this scene\")"}]},{"tag":"article","attrs":{},"bind":{"key":"playback.id"},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"library.sounds.find((s) => s.asset_id === playback.asset.id)?.name || playback.channel"},{"tag":"input","attrs":{"type":"range","min":"0","max":"1","step":"0.01"},"bind":{"aria-label":"gwText(\"Track volume\")","value":"playback.baseGain ?? playback.gain","disabled":"busy"},"events":[{"event":"change","code":"command(\"playbacks\", \"update\", { playback_id: playback.id, expected_version: playback.version, patch: { gain: Number($event.target.value) } });","mods":[]}],"children":[]}]},{"tag":"div","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Play\")"},"events":[{"event":"click","code":"command(\"playbacks\", \"update\", { playback_id: playback.id, expected_version: playback.version, patch: { state: \"playing\" } });","mods":[]}],"children":[{"tag":"PhPlay","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Pause\")"},"events":[{"event":"click","code":"command(\"playbacks\", \"update\", { playback_id: playback.id, expected_version: playback.version, patch: { state: \"paused\" } });","mods":[]}],"children":[{"tag":"PhPause","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Stop\")"},"events":[{"event":"click","code":"command(\"playbacks\", \"stop\", { playback_id: playback.id, expected_version: playback.version });","mods":[]}],"children":[{"tag":"PhStop","attrs":{},"bind":{},"events":[],"children":[]}]}]}],"each":{"names":["playback"],"value":"state.audio.filter((a) => a.state !== \"stopped\")"}},{"tag":"h4","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Spatial sources\")"}]},{"tag":"article","attrs":{},"bind":{"key":"source.id"},"events":[],"children":[{"tag":"button","attrs":{},"bind":{},"events":[{"event":"click","code":"edit(source.id);","mods":[]}],"children":[{"value":"library.sounds.find((s) => s.id === source.sound_id)?.name || gwText(\"Source\")"},{"text":" · "},{"value":"source.enabled ? gwText(\"active\") : gwText(\"off\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"command(\"spatial-sounds\", \"update\", { rid: source.id, expected_version: source.version, patch: { enabled: !source.enabled } });","mods":[]}],"children":[{"tag":"component","attrs":{},"bind":{"is":"source.enabled ? PhPause : PhPlay"},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Delete source\")"},"events":[{"event":"click","code":"command(\"spatial-sounds\", \"delete\", { rid: source.id, expected_version: source.version });","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]}]}],"each":{"names":["source"],"value":"state.spatialSounds"}}],"when":"gm"},{"tag":"p","attrs":{"class":"audio-panel__hint"},"bind":{},"events":[],"children":[{"value":"gwText(\"Table library \\xB7 Playback and sources for this scene. Spatial audio uses controlled tokens as listeners.\")"}]}],"when":"panel"}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const PhWaveform="PhWaveform";
const PhPlay="PhPlay";
const PhPause="PhPause";
const PhStop="PhStop";
const PhX="PhX";
const PhSpeakerHigh="PhSpeakerHigh";
const PhTrash="PhTrash";
const HttpClient=options.HttpClient;
const BlockStateApi=class {command(c,b,area,action,data){return options.command(area,action,data)}state(){return options.read()}};
const props = options.props;
const emit = options.emit;
const abort = new AbortController(), http = new HttpClient(void 0, () => abort.signal), api = new BlockStateApi(http), root = ref();
const library = ref({ sounds: [], assets: [] }), query = ref(""), busy = ref(false), error = ref(""), editor = ref(""), chosen = ref(""), placing = ref(false), position = ref();
const radius = ref(25), gain = ref(0.7), loop = ref(true), walls = ref(true), enabled = ref(true), falloff = ref("smooth"), category = ref("ambience");
let preview;
function sourceTransform(source) {
  const p = props.selectionPreview;
  if (!p?.objects.some((o) => o.key === "sound:" + source.id)) return "";
  const next = transformedPoint(source, p.center, p.dx, p.dy, p.angle);
  return "translate(" + (next.x - source.x) + " " + (next.y - source.y) + ")";
}
const sounds = computed(() => library.value.sounds.filter((s) => s.name.toLowerCase().includes(query.value.toLowerCase())));
const panel = computed(() => props.embedded || props.tool === "sound" || !!editor.value);
const toPixels = computed(() => props.cell / (props.measureValue || 1));
async function refresh() {
  try {
    const value = await http.get(`/api/containers/${props.containerId}/library`);
    if (!abort.signal.aborted) library.value = value;
  } catch {
    if (!abort.signal.aborted) error.value = gwText("Could not load the audio library.");
  }
}
async function command(area, action, data) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await api.command(props.containerId, props.blockId, area, action, data);
    if (!abort.signal.aborted) emit("refresh");
  } catch {
    if (!abort.signal.aborted) {
      error.value = gwText("The audio change was refused. Refreshing the scene\u2026");
      emit("refresh");
    }
  } finally {
    if (!abort.signal.aborted) busy.value = false;
  }
}
async function register(asset) {
  busy.value = true;
  try {
    await http.post(`/api/containers/${props.containerId}/library/sounds/create`, { name: asset.name || asset.filename, assetId: asset.id, kind: category.value, defaultGain: 0.7, defaultLoop: true });
    await refresh();
  } catch {
    error.value = gwText("Could not add the audio.");
  } finally {
    busy.value = false;
  }
}
function select(sound) {
  stopPreview();
  editor.value = "";
  chosen.value = sound.id;
  placing.value = !!props.viewport;
  position.value = void 0;
  if (!props.viewport) error.value = gwText("Open the Audio layer to place a source on the map.");
}
function edit(id) {
  const row = props.state.spatialSounds.find((s) => s.id === id);
  if (!row) return;
  placing.value = false;
  editor.value = id;
  chosen.value = row.sound_id || "";
  radius.value = row.radius / toPixels.value;
  gain.value = row.gain ?? 0.7;
  loop.value = row.loop ?? true;
  walls.value = row.constrained_by_walls ?? true;
  enabled.value = row.enabled;
  falloff.value = row.falloff ?? "smooth";
}
function move(e) {
  if (!root.value || !props.viewport) return;
  const b = root.value.getBoundingClientRect();
  position.value = { x: (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - b.top - props.viewport.y) / props.viewport.scale };
}
async function place(e) {
  if (e.button !== 0 || !placing.value || busy.value) return;
  e.preventDefault();
  e.stopPropagation();
  move(e);
  await command("spatial-sounds", "create", { soundId: chosen.value, ...position.value, radius: radius.value * toPixels.value, gain: gain.value, loop: loop.value, enabled: enabled.value, falloff: falloff.value, constrainedByWalls: walls.value, audience: { kind: "campaign" } });
  if (!error.value) {
    placing.value = false;
    emit("tool", "select");
  }
}
async function save() {
  const row = props.state.spatialSounds.find((s) => s.id === editor.value);
  if (!row) return;
  await command("spatial-sounds", "update", { rid: row.id, expected_version: row.version, patch: { radius: radius.value * toPixels.value, gain: gain.value, loop: loop.value, enabled: enabled.value, falloff: falloff.value, constrainedByWalls: walls.value } });
  if (!error.value) editor.value = "";
}
function stopPreview() {
  if (preview) {
    preview.pause();
    preview.removeAttribute("src");
    preview.load();
    preview = void 0;
  }
}
async function listen(sound) {
  stopPreview();
  const asset = library.value.assets.find((a) => a.id === sound.asset_id);
  if (!asset) return;
  preview = new Audio(asset.src);
  preview.volume = 0.5;
  try {
    await preview.play();
  } catch {
    if (!abort.signal.aborted) error.value = gwText("Click again to listen to the preview.");
  }
}
function close() {
  stopPreview();
  placing.value = false;
  editor.value = "";
  emit("tool", "select");
}
function key(e) {
  if (e.key === "Escape" && (placing.value || editor.value)) {
    e.stopImmediatePropagation();
    close();
  }
}
watch(() => props.revision, refresh);
watch(() => props.tool, (tool) => {
  if (tool !== "sound") {
    placing.value = false;
    stopPreview();
  }
});
onMounted(() => {
  void refresh();
  window.addEventListener("keydown", key, true);
});
onBeforeUnmount(() => {
  abort.abort();
  stopPreview();
  window.removeEventListener("keydown", key, true);
});
defineExpose({ edit });
return {gwText,SoundtrackPanel,transformedPoint,PhWaveform,PhPlay,PhPause,PhStop,PhX,PhSpeakerHigh,PhTrash,HttpClient,BlockStateApi,props,emit,abort,http,api,root,library,query,busy,error,editor,chosen,placing,position,radius,gain,loop,walls,enabled,falloff,category,preview,sourceTransform,sounds,panel,toPixels,refresh,command,register,select,edit,move,place,save,stopPreview,listen,close,key};
});
