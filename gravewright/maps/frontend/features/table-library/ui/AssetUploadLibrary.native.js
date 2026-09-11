import { text as gwText } from '../../../shared/config/i18n/text.js';
import { ResourceScope } from '../../../shared/lifecycle/scope.js';
import DirectoryContextMenu from '../../../shared/ui/directory/DirectoryContextMenu.native.js';
import { IMAGE_ACCEPT, AUDIO_ACCEPT, assetKinds, bytesLabel, uploadError, uploadFile, validateUpload } from '../model/library-upload.js';
const PhImage = "PhImage";
const PhMusicNotes = "PhMusicNotes";
const PhWaveform = "PhWaveform";
const PhFilePdf = "PhFilePdf";
const PhFolder = "PhFolder";
const PhFolderOpen = "PhFolderOpen";
const PhFolderPlus = "PhFolderPlus";
const PhMagnifyingGlass = "PhMagnifyingGlass";
const PhTrash = "PhTrash";
const PhArrowsLeftRight = "PhArrowsLeftRight";
import { widget } from '../../../native/widget.js';
export default widget([{"tag":"section","attrs":{"class":"asset-library"},"bind":{"aria-label":"gwText(\"Table assets\")"},"events":[],"children":[{"tag":"header","attrs":{"class":"asset-library__bar"},"bind":{},"events":[],"children":[{"tag":"div","attrs":{"class":"asset-library__uploads"},"bind":{},"events":[],"children":[{"tag":"label","attrs":{"class":"asset-library__upload"},"bind":{"key":"u.id","class":"({ \"asset-library__upload--disabled\": busy })"},"events":[],"children":[{"tag":"component","attrs":{},"bind":{"is":"u.icon"},"events":[],"children":[]},{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"u.label"}]},{"tag":"input","attrs":{"type":"file","multiple":""},"bind":{"aria-label":"gwText(\"Upload {0}\", u.label)","accept":"u.accept","disabled":"busy"},"events":[{"event":"change","code":"choose($event, u.purpose);","mods":[]}],"children":[]}],"each":{"names":["u"],"value":"uploads"}}],"when":"gm"},{"tag":"label","attrs":{"class":"asset-library__search"},"bind":{},"events":[],"children":[{"tag":"PhMagnifyingGlass","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"input","attrs":{"type":"search"},"bind":{"placeholder":"gwText(\"Search files\")","aria-label":"gwText(\"Search files\")"},"events":[],"children":[],"model":{"path":"(search)","mods":[]}}]},{"tag":"div","attrs":{"class":"asset-library__filters","role":"group"},"bind":{"aria-label":"gwText(\"File type\")"},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"key":"f.id","aria-pressed":"kind === f.id"},"events":[{"event":"click","code":"kind = f.id;","mods":[]}],"children":[{"value":"f.label"},{"text":" "},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"f.count"}]}],"each":{"names":["f"],"value":"filters"}}]}]},{"tag":"p","attrs":{"class":"asset-library__error","role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"div","attrs":{"class":"asset-library__notice","role":"status"},"bind":{},"events":[],"children":[{"value":"notice || gwText(\"Saving\\u2026\")"},{"tag":"progress","attrs":{"max":"100"},"bind":{"value":"progress","aria-label":"gwText(\"Upload progress\")"},"events":[],"children":[],"when":"busy && notice.startsWith(gwText(\"Uploading\"))"}],"when":"busy || notice"},{"tag":"div","attrs":{"class":"asset-library__body"},"bind":{},"events":[],"children":[{"tag":"aside","attrs":{"class":"asset-library__folders"},"bind":{"aria-label":"gwText(\"Asset folders\")"},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"aria-pressed":"!folder"},"events":[{"event":"click","code":"folder = \"\";","mods":[]},{"event":"dragover","code":"","mods":["prevent"]},{"event":"drop","code":"drop($event, \"\");","mods":["stop","prevent"]}],"children":[{"tag":"PhFolderOpen","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Root\")"}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"state.assets.filter((a) => !a.folder_id).length"}]}]},{"tag":"button","attrs":{},"bind":{"key":"f.id","aria-pressed":"folder === f.id"},"events":[{"event":"click","code":"folder = f.id;","mods":[]},{"event":"dragover","code":"","mods":["prevent"]},{"event":"drop","code":"drop($event, f.id);","mods":["stop","prevent"]}],"children":[{"tag":"PhFolder","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"f.name"}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"state.assets.filter((a) => a.folder_id === f.id).length"}]}],"each":{"names":["f"],"value":"state.folders"}},{"tag":"form","attrs":{"class":"asset-library__folder-create"},"bind":{},"events":[{"event":"submit","code":"command(\"folder-create\", { name: folderName.trim() });","mods":["prevent"]}],"children":[{"tag":"input","attrs":{"maxlength":"120","required":""},"bind":{"placeholder":"gwText(\"New folder\")","aria-label":"gwText(\"Folder name\")","disabled":"busy"},"events":[],"children":[],"model":{"path":"(folderName)","mods":[]}},{"tag":"button","attrs":{},"bind":{"disabled":"busy || !folderName.trim()","aria-label":"gwText(\"Create folder\")"},"events":[],"children":[{"tag":"PhFolderPlus","attrs":{},"bind":{},"events":[],"children":[]}]}],"when":"gm"}]},{"tag":"div","attrs":{"class":"asset-library__grid"},"bind":{"class":"({ \"asset-library__grid--drop\": dragging })"},"events":[{"event":"dragover","code":"dragging = true;","mods":["prevent"]},{"event":"dragleave","code":"dragging = false;","mods":["self"]},{"event":"drop","code":"drop($event);","mods":["prevent"]}],"children":[{"tag":"article","attrs":{"class":"asset-library__card"},"bind":{"key":"asset.id","draggable":"gm && !busy","title":"asset.filename"},"events":[{"event":"dragstart","code":"dragAsset($event, asset);","mods":[]},{"event":"contextmenu","code":"openContext($event, asset);","mods":[]}],"children":[{"tag":"div","attrs":{"class":"asset-library__thumb"},"bind":{},"events":[],"children":[{"tag":"img","attrs":{"alt":"","loading":"lazy","draggable":"false"},"bind":{"src":"asset.src"},"events":[],"children":[],"when":"asset.kind === \"image\""},{"tag":"PhFilePdf","attrs":{},"bind":{},"events":[],"children":[],"otherwiseWhen":"asset.kind === \"pdf\""},{"tag":"PhWaveform","attrs":{},"bind":{},"events":[],"children":[],"otherwise":true}]},{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"asset.filename"}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"asset.kind === \"image\" ? `${asset.width} \\xD7 ${asset.height}` : bytesLabel(asset.byte_size)"}]},{"tag":"div","attrs":{"class":"asset-library__actions"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Move file\")"},"events":[{"event":"click","code":"moving = asset;\ntarget = asset.folder_id || \"\";","mods":[]}],"children":[{"tag":"PhArrowsLeftRight","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Delete file\")"},"events":[{"event":"click","code":"removing = asset;","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]}]}],"when":"gm"}],"each":{"names":["asset"],"value":"visible"}},{"tag":"p","attrs":{"class":"asset-library__empty"},"bind":{},"events":[],"children":[{"value":"search ? gwText(\"No files found.\") : gm ? gwText(\"This folder is empty. Upload or drop files here.\") : gwText(\"This folder is empty.\")"}],"when":"!visible.length"}]}]},{"tag":"footer","attrs":{"class":"asset-library__foot"},"bind":{},"events":[],"children":[{"value":"visible.length"},{"text":"/"},{"value":"state.assets.length"},{"text":" · "},{"value":"bytesLabel(visibleBytes)"},{"tag":"span","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Images: 10 MB \\xB7 Audio: 100 MB \\xB7 PDF: 25 MB\")"}]}]},{"tag":"Teleport","attrs":{"to":"body"},"bind":{},"events":[],"children":[{"tag":"DirectoryContextMenu","attrs":{},"bind":{"x":"context.x","y":"context.y","label":"gwText(\"File actions\")"},"events":[{"event":"close","code":"context = void 0;","mods":[]}],"children":[{"tag":"li","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{},"events":[{"event":"click","code":"moving = context.asset;\ntarget = moving.folder_id || \"\";\ncontext = void 0;","mods":[]}],"children":[{"tag":"PhArrowsLeftRight","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Move to folder\")"}]}]},{"tag":"li","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{"class":"is-danger"},"bind":{},"events":[{"event":"click","code":"removing = context.asset;\ncontext = void 0;","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Delete file\")"}]}]}],"when":"context"}]},{"tag":"form","attrs":{"class":"asset-library__dialog","role":"dialog"},"bind":{"aria-label":"moving ? gwText(\"Move file\") : gwText(\"Delete file\")"},"events":[{"event":"submit","code":"moving ? command(\"move\", { asset_id: moving.id, folder_id: target || null }) : command(\"delete\", { asset_id: removing.id });","mods":["prevent"]}],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"moving ? gwText(\"Move\") : gwText(\"Delete\")"},{"text":" "},{"value":"(moving || removing)?.filename"}]},{"tag":"select","attrs":{},"bind":{"aria-label":"gwText(\"Destination folder\")"},"events":[],"children":[{"tag":"option","attrs":{"value":""},"bind":{},"events":[],"children":[{"value":"gwText(\"Root\")"}]},{"tag":"option","attrs":{},"bind":{"key":"f.id","value":"f.id"},"events":[],"children":[{"value":"f.name"}],"each":{"names":["f"],"value":"state.folders"}}],"when":"moving","model":{"path":"(target)","mods":[]}},{"tag":"p","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Delete this file from the library?\")"}],"otherwise":true},{"tag":"footer","attrs":{},"bind":{},"events":[],"children":[{"tag":"button","attrs":{"type":"button"},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"moving = void 0;\nremoving = void 0;","mods":[]}],"children":[{"value":"gwText(\"Cancel\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[],"children":[{"value":"moving ? gwText(\"Move\") : gwText(\"Delete\")"}]}]}],"when":"moving || removing"}]}], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const scope = new ResourceScope(), http = new HttpClient(undefined, () => scope.signal), root = `/api/containers/${encodeURIComponent(props.containerId)}/library`;
    const state = ref({ assets: [], folders: [] }), folder = ref(''), kind = ref(''), search = ref(''), folderName = ref(''), busy = ref(false), error = ref(''), notice = ref(''), progress = ref(0), dragging = ref(false);
    const context = ref(), removing = ref(), moving = ref(), target = ref('');
    const uploads = [{ id: 'image', get label() { return gwText('Images'); }, icon: PhImage, accept: IMAGE_ACCEPT, purpose: '' }, { id: 'ambient', get label() { return gwText('Ambient audio'); }, icon: PhMusicNotes, accept: AUDIO_ACCEPT, purpose: 'ambient' }, { id: 'effect', get label() { return gwText('Sound effect'); }, icon: PhWaveform, accept: AUDIO_ACCEPT, purpose: 'effect' }, { id: 'pdf', label: 'PDFs', icon: PhFilePdf, accept: 'application/pdf', purpose: 'pdf-sheet' }];
    const filters = computed(() => [{ id: '', get label() { return gwText('All'); } }, ...uploads.map(u => ({ id: u.id, label: u.label })), { id: 'audio', get label() { return gwText('Audio'); } }].map(f => ({ ...f, count: state.value.assets.filter(a => !f.id || assetKinds(a).includes(f.id)).length })).filter(f => !f.id || f.count));
    const visible = computed(() => state.value.assets.filter(a => (a.folder_id || '') === folder.value && (!kind.value || assetKinds(a).includes(kind.value)) && a.filename.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())));
    const visibleBytes = computed(() => visible.value.reduce((sum, a) => sum + a.byte_size, 0));
    let refreshId = 0;
    async function refresh() { const id = ++refreshId; try {
        const result = await http.get(root + '/asset-state');
        if (!scope.closed && id === refreshId) {
            state.value = result;
            if (kind.value && !result.assets.some(a => assetKinds(a).includes(kind.value)))
                kind.value = '';
            if (folder.value && !result.folders.some(f => f.id === folder.value))
                folder.value = '';
        }
    }
    catch (e) {
        if (!scope.closed)
            error.value = uploadError(e);
    } }
    async function command(action, data) { if (busy.value)
        return; busy.value = true; error.value = ''; try {
        await http.post(root + '/assets/' + action, data);
        if (!scope.closed) {
            removing.value = undefined;
            moving.value = undefined;
            folderName.value = '';
            await refresh();
        }
    }
    catch (e) {
        if (!scope.closed)
            error.value = uploadError(e);
    }
    finally {
        if (!scope.closed)
            busy.value = false;
    } }
    async function upload(files, purpose = '', destination = folder.value) {
        if (!props.gm || busy.value || !files.length)
            return;
        busy.value = true;
        error.value = '';
        notice.value = '';
        let sent = 0;
        const failures = [];
        try {
            for (const [index, file] of files.entries()) {
                if (scope.closed)
                    break;
                const invalid = validateUpload(file);
                if (invalid) {
                    failures.push(`${file.name}: ${invalid}`);
                    continue;
                }
                notice.value = `Enviando ${index + 1}/${files.length} · ${file.name}`;
                progress.value = 0;
                const form = new FormData();
                form.append('file', uploadFile(file));
                if (destination)
                    form.append('folder_id', destination);
                if (purpose)
                    form.append('purpose', purpose);
                try {
                    await http.upload(root + '/upload', form, p => { if (!scope.closed)
                        progress.value = p; });
                    sent++;
                }
                catch (e) {
                    if (scope.closed)
                        break;
                    failures.push(`${file.name}: ${uploadError(e)}`);
                }
            }
            if (!scope.closed) {
                notice.value = `${sent} arquivo(s) enviado(s).`;
                error.value = failures.join('\n');
                await refresh();
            }
        }
        finally {
            if (!scope.closed) {
                busy.value = false;
                progress.value = 0;
            }
        }
    }
    function choose(event, purpose) { const input = event.target; void upload(Array.from(input.files ?? []), purpose); input.value = ''; }
    function openContext(event, asset) { if (!props.gm || busy.value)
        return; event.preventDefault(); context.value = { x: event.clientX, y: event.clientY, asset }; }
    function dragAsset(event, asset) { event.dataTransfer?.setData('application/x-gravewright-library-asset', asset.id); if (asset.kind === 'image')
        event.dataTransfer?.setData('application/x-gravewright-library-image', asset.id); }
    function drop(event, destination = folder.value) { dragging.value = false; if (!props.gm || busy.value)
        return; const id = event.dataTransfer?.getData('application/x-gravewright-library-asset'); if (id) {
        void command('move', { asset_id: id, folder_id: destination || null });
        return;
    } void upload(Array.from(event.dataTransfer?.files ?? []), '', destination); }
    watch(() => props.revision, () => void refresh());
    onMounted(() => void refresh());
    onBeforeUnmount(() => scope.dispose());
    return { gwText, PhImage, PhMusicNotes, PhWaveform, PhFilePdf, PhFolder, PhFolderOpen, PhFolderPlus, PhMagnifyingGlass, PhTrash, PhArrowsLeftRight, HttpClient, ResourceScope, DirectoryContextMenu, IMAGE_ACCEPT, AUDIO_ACCEPT, assetKinds, bytesLabel, uploadError, uploadFile, validateUpload, scope, http, root, state, folder, kind, search, folderName, busy, error, notice, progress, dragging, context, removing, moving, target, uploads, filters, visible, visibleBytes, refreshId, refresh, command, upload, choose, openContext, dragAsset, drop, emit: options.emit };
});
