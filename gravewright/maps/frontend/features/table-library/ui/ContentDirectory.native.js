import { text as gwText } from "../../../shared/config/i18n/text.js";
import { ResourceScope } from "../../../shared/lifecycle/scope.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"section","attrs":{"class":"content-directory"},"bind":{"aria-label":"gwText(\"Table compendiums\")"},"events":[],"children":[{"tag":"p","attrs":{"role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"p","attrs":{"class":"content-directory__empty"},"bind":{},"events":[],"children":[{"tag":"PhBooks","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"No active content package.\")"}],"when":"!packages.length && !error"},{"tag":"details","attrs":{"class":"content-directory__package"},"bind":{"key":"item.id"},"events":[{"event":"toggle","code":"$event.target.open && openPackage(item);","mods":[]}],"children":[{"tag":"summary","attrs":{"class":"content-directory__heading"},"bind":{},"events":[],"children":[{"tag":"PhBooks","attrs":{},"bind":{},"events":[],"children":[]},{"value":"item.name || item.id"}]},{"tag":"details","attrs":{"class":"content-directory__pack"},"bind":{"key":"pack.id"},"events":[{"event":"toggle","code":"$event.target.open && openPack(item, pack);","mods":[]}],"children":[{"tag":"summary","attrs":{"class":"content-directory__heading"},"bind":{},"events":[],"children":[{"tag":"PhFolder","attrs":{},"bind":{},"events":[],"children":[]},{"value":"pack.label || pack.name || pack.id"}]},{"tag":"div","attrs":{"class":"content-directory__entry"},"bind":{"key":"entry.id"},"events":[],"children":[{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"entry.name || entry.id"}]},{"tag":"button","attrs":{"class":"content-directory__import","type":"button"},"bind":{"disabled":"!!busy","aria-label":"`Importar ${entry.name || entry.id}`"},"events":[{"event":"click","code":"importEntry(item, pack, entry);","mods":[]}],"children":[{"tag":"PhDownloadSimple","attrs":{},"bind":{},"events":[],"children":[]}]}],"each":{"names":["entry"],"value":"pack.entries"}},{"tag":"p","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Empty package.\")"}],"when":"pack.entries?.length === 0"}],"each":{"names":["pack"],"value":"item.packs"}}],"each":{"names":["item"],"value":"packages"}}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const PhBooks="PhBooks";
const PhFolder="PhFolder";
const PhDownloadSimple="PhDownloadSimple";
const HttpClient=options.HttpClient;
const props = options.props;
const packages = ref([]), error = ref(""), busy = ref("");
const scope = new ResourceScope(), http = new HttpClient(void 0, () => scope.signal);
const query = `?campaign_id=${encodeURIComponent(props.containerId)}`;
async function load() {
  try {
    const data = await http.get(`/game/content/active-packages${query}`);
    if (!scope.closed) packages.value = data.packages;
  } catch {
    if (!scope.closed) error.value = gwText("Could not load compendiums.");
  }
}
async function openPackage(item) {
  if (item.packs) return;
  try {
    const data = await http.get(`/game/content/packs/${encodeURIComponent(item.id)}${query}`);
    if (!scope.closed) item.packs = data.packs;packages.value=[...packages.value];
  } catch {
    if (!scope.closed) error.value = gwText("Could not load packages.");
  }
}
async function openPack(item, pack) {
  if (pack.entries) return;
  try {
    const data = await http.get(`/game/content/pack/${encodeURIComponent(item.id)}/${encodeURIComponent(pack.id)}${query}`);
    if (!scope.closed) pack.entries = data.entries;packages.value=[...packages.value];
  } catch {
    if (!scope.closed) error.value = gwText("Could not load entries.");
  }
}
async function importEntry(item, pack, entry) {
  busy.value = entry.id;
  error.value = "";
  try {
    await http.post(["item_pack", "spell_pack"].includes(pack.type) ? "/game/item/content/import" : "/game/content/import", { campaign_id: props.containerId, package_id: item.id, pack_id: pack.id, entry_id: entry.id });
  } catch {
    if (!scope.closed) error.value = gwText("Could not import this entry.");
  } finally {
    if (!scope.closed) busy.value = "";
  }
}
onMounted(load);
onBeforeUnmount(() => scope.dispose());
return {gwText,PhBooks,PhFolder,PhDownloadSimple,ResourceScope,HttpClient,props,packages,error,busy,scope,http,query,load,openPackage,openPack,importEntry,emit:options.emit};
});
