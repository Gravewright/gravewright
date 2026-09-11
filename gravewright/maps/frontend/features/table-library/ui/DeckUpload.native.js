import { text as gwText } from "../../../shared/config/i18n/text.js";
import { ResourceScope } from "../../../shared/lifecycle/scope.js";
import { IMAGE_ACCEPT, uploadError, uploadFile, validateUpload } from "../model/library-upload.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"form","attrs":{"class":"deck-upload"},"bind":{},"events":[{"event":"submit","code":"create;","mods":["prevent"]}],"children":[{"tag":"p","attrs":{"class":"deck-upload__intro"},"bind":{},"events":[],"children":[{"value":"gwText(\"One image per card, with an optional shared back for the deck.\")"}]},{"tag":"fieldset","attrs":{},"bind":{"disabled":"busy || !!definition"},"events":[],"children":[{"tag":"label","attrs":{"class":"deck-upload__field"},"bind":{},"events":[],"children":[{"value":"gwText(\"Deck name\")"},{"tag":"input","attrs":{"name":"name","minlength":"2","maxlength":"120","required":""},"bind":{"placeholder":"gwText(\"Deck name\")"},"events":[],"children":[],"model":{"path":"name","mods":[]}}]},{"tag":"div","attrs":{"class":"deck-upload__files"},"bind":{},"events":[],"children":[{"tag":"label","attrs":{"class":"deck-upload__file"},"bind":{},"events":[],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Card fronts\")"},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"PNG, JPEG or WebP \\xB7 up to 10 MB per image\")"}]}]},{"tag":"input","attrs":{"type":"file","name":"fronts","multiple":""},"bind":{"accept":"IMAGE_ACCEPT","aria-label":"gwText(\"Card fronts\")"},"events":[{"event":"change","code":"files($event, \"front\");","mods":[]}],"children":[]}]},{"tag":"label","attrs":{"class":"deck-upload__file"},"bind":{},"events":[],"children":[{"tag":"img","attrs":{},"bind":{"src":"back.url","alt":"gwText(\"Card back preview\")"},"events":[],"children":[],"when":"back"},{"tag":"PhUploadSimple","attrs":{},"bind":{},"events":[],"children":[],"otherwise":true},{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"back ? back.file.name : gwText(\"Optional back\")"},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Used for all cards\")"}]}]},{"tag":"input","attrs":{"type":"file","name":"back"},"bind":{"accept":"IMAGE_ACCEPT","aria-label":"gwText(\"Card backs\")"},"events":[{"event":"change","code":"files($event, \"back\");","mods":[]}],"children":[]}]}]},{"tag":"button","attrs":{"type":"button","class":"deck-upload__remove-back"},"bind":{},"events":[{"event":"click","code":"dispose(back);\nback = void 0;","mods":[]}],"children":[{"value":"gwText(\"Remove card back\")"}],"when":"back"},{"tag":"div","attrs":{"class":"deck-upload__previews"},"bind":{},"events":[],"children":[{"tag":"article","attrs":{"class":"deck-upload__card"},"bind":{"key":"draft.url"},"events":[],"children":[{"tag":"img","attrs":{"loading":"lazy"},"bind":{"src":"draft.url","alt":"draft.name"},"events":[],"children":[]},{"tag":"button","attrs":{"type":"button"},"bind":{"aria-label":"gwText(\"Remove {0}\", draft.name)"},"events":[{"event":"click","code":"remove(index);","mods":[]}],"children":[{"tag":"PhX","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"input","attrs":{"maxlength":"191","required":""},"bind":{"aria-label":"gwText(\"Card {0} name\", index + 1)"},"events":[],"children":[],"model":{"path":"draft.name","mods":[]}}],"each":{"names":["draft","index"],"value":"fronts"}}],"when":"fronts.length"}]},{"tag":"p","attrs":{"class":"deck-upload__error","role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"p","attrs":{"class":"deck-upload__notice","role":"status"},"bind":{},"events":[],"children":[{"value":"notice"}],"when":"notice"},{"tag":"progress","attrs":{"max":"100"},"bind":{"value":"progress","aria-label":"gwText(\"Card upload progress\")"},"events":[],"children":[],"when":"busy"},{"tag":"footer","attrs":{"class":"deck-upload__footer"},"bind":{},"events":[],"children":[{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"fronts.length"},{"text":" "},{"value":"gwText(\"card(s)\")"}]},{"tag":"button","attrs":{"type":"submit"},"bind":{"disabled":"busy || !fronts.length || name.trim().length < 2"},"events":[],"children":[{"tag":"PhUploadSimple","attrs":{},"bind":{},"events":[],"children":[]},{"value":"busy ? gwText(\"Uploading\\u2026\") : definition ? gwText(\"Add to table\") : gwText(\"Create deck\")"}]}]}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const PhCardsThree="PhCardsThree";
const PhUploadSimple="PhUploadSimple";
const PhX="PhX";
const HttpClient=options.HttpClient;
const props = options.props;
const emit = options.emit;
const scope = new ResourceScope(), http = new HttpClient(void 0, () => scope.signal), root = `/api/containers/${encodeURIComponent(props.containerId)}/library`;
const name = ref(""), fronts = ref([]), back = ref(), busy = ref(false), error = ref(""), notice = ref(""), progress = ref(0), definition = ref();
function dispose(draft) {
  URL.revokeObjectURL(draft.url);
}
function files(event, side) {
  const input = event.target, chosen = Array.from(input.files ?? []);
  input.value = "";
  error.value = "";
  if (busy.value || definition.value) return;
  for (const file of chosen) {
    const invalid = validateUpload(file, true);
    if (invalid) {
      error.value += `${file.name}: ${invalid}
`;
      continue;
    }
    if (side === "front" && fronts.value.length >= 500) {
      error.value += gwText("The deck accepts up to 500 cards.\n");
      break;
    }
    const draft = { file, url: URL.createObjectURL(file), name: file.name.replace(/\.[^.]+$/, "") || gwText("Card") };
    if (side === "back") {
      if (back.value) dispose(back.value);
      back.value = draft;
    } else fronts.value.push(draft);
  }
}
function remove(index) {
  const draft = fronts.value.splice(index, 1)[0];
  if (draft) dispose(draft);
}
function clear() {
  fronts.value.forEach(dispose);
  fronts.value = [];
  if (back.value) dispose(back.value);
  back.value = void 0;
  name.value = "";
  definition.value = void 0;
}
async function upload(draft, purpose) {
  if (draft.assetId) return draft.assetId;
  const form = new FormData();
  form.append("file", uploadFile(draft.file));
  form.append("purpose", purpose);
  progress.value = 0;
  const result = await http.upload(root + "/card-upload", form, (p) => {
    if (!scope.closed) progress.value = p;
  });
  draft.assetId = result.asset_id;
  return result.asset_id;
}
async function create() {
  if (busy.value || name.value.trim().length < 2 || !fronts.value.length) return;
  busy.value = true;
  error.value = "";
  try {
    if (!definition.value) {
      notice.value = gwText("Uploading card back\u2026");
      const backId = back.value ? await upload(back.value, "card_back") : null;
      const cards = [];
      for (const [index, draft] of fronts.value.entries()) {
        scope.signal.throwIfAborted();
        notice.value = `Enviando carta ${index + 1}/${fronts.value.length} \xB7 ${draft.file.name}`;
        cards.push({ name: draft.name, front_asset_id: await upload(draft, "card_front"), back_asset_id: backId });
      }
      notice.value = gwText("Creating deck\u2026");
      const result = await http.post(root + "/cards/define", { name: name.value.trim(), description: "", default_back_asset_id: backId, cards });
      definition.value = result.deck.id;
    }
    notice.value = gwText("Adding deck to the table\u2026");
    await http.post(root + "/cards/instantiate", { deck_definition_id: definition.value });
    if (!scope.closed) {
      const title = name.value;
      clear();
      notice.value = gwText("Deck \u201C{0}\u201D created and available at the table.", title);
      emit("created");
    }
  } catch (e) {
    if (!scope.closed) {
      error.value = uploadError(e);
      notice.value = definition.value ? gwText("The deck was created. Try again to add it to the table.") : gwText("Uploaded files will be reused when you try again.");
    }
  } finally {
    if (!scope.closed) {
      busy.value = false;
      progress.value = 0;
    }
  }
}
onBeforeUnmount(() => {
  scope.dispose();
  clear();
});
return {gwText,PhCardsThree,PhUploadSimple,PhX,HttpClient,ResourceScope,IMAGE_ACCEPT,uploadError,uploadFile,validateUpload,props,emit,scope,http,root,name,fronts,back,busy,error,notice,progress,definition,dispose,files,remove,clear,upload,create};
});
