import {createSelection} from '../features/selection/ui/selection-workspace.js';
import Drawing from '../features/drawing/ui/DrawingWorkspace.native.js';
import Measurement from '../features/measurement/ui/MeasurementWorkspace.native.js';
import Images from '../features/images/ui/ImageWorkspace.native.js';
import Sources from '../features/scene-layers/ui/SceneSourcesWorkspace.native.js';
import Library from '../features/table-library/ui/AssetUploadLibrary.native.js';
import { vMovableResizable } from '../shared/lib/dom/movable-resizable.js';
class HttpClient {
    signal;
    constructor(_base, signal = () => undefined) {
        this.signal = signal;
    }
    async request(url, body) {
        const csrf = body === undefined ? {} : await (await fetch('/__gravewright/csrf', {signal: this.signal()})).json();
        const response = await fetch(url, { method: body === undefined ? 'GET' : 'POST', signal: this.signal(), headers: body === undefined ? {} : { [csrf.header || 'X-CSRF-Token']: csrf.token, ...(body instanceof FormData ? {} : { 'Content-Type': 'application/json' }) }, body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body) });
        const value = await response.json();
        if (!response.ok)
            throw Error(value.error || 'Could not save the change.');
        return value;
    }
    get(url) { return this.request(url); }
    post(url, body) { return this.request(url, body); }
    upload(url, body, progress) { progress?.(0); return this.request(url, body).then(value => { progress?.(100); return value; }); }
}
export function createTools(surface, board, map, gm, api, stateAPI) {
    let state = api.state, drawing, images, effects, library, libraryHost, closed = false;
    const hosts = { drawing: document.createElement('div'), images: document.createElement('div'), effects: document.createElement('div'), measurement: document.createElement('div'), markers: document.createElement('div') };
    for (const host of Object.values(hosts)) {
        host.style.display = 'contents';
        surface.append(host);
    }
    const common = { HttpClient, command: api.command, read: api.read };
    const base = () => ({ viewport: board.viewport(), containerId: map.containerId, blockId: map.blockId, cell: map.gridSize * map.imageScale, grid: map.gridVisible });
    let measureRows=[],selection;
    const measurement = Measurement(hosts.measurement, { ...common, props: { ...base(), active: false, maxRows: state.capabilities?.maxMeasurements, measureValue: map.measureValue, measureUnit: map.measureUnit }, emit(type, value) { if(type==='change')measureRows=value; if (type === 'close') {
            stateAPI.mergePatch({ _tool: 'select' });
            sync();
        } } });
    let markerQueue=Promise.resolve();
    const markerKeys=['id','kind','origin','length','width','direction','angle','color'];
    const clean=rows=>rows.map(row=>Object.fromEntries(markerKeys.map(k=>[k,row[k]])));
    const markers=Measurement(hosts.markers,{...common,props:{...base(),active:false,shared:true,rows:state.markers||[],maxRows:state.capabilities?.maxMarkers,measureValue:map.measureValue,measureUnit:map.measureUnit},emit(type,rows){
        if(type==='close'){stateAPI.mergePatch({_tool:'select'});sync();}
        if(type!=='change'||JSON.stringify(clean(rows))===JSON.stringify(clean(state.markers||[])))return;
        const expected=state.version;
        markerQueue=markerQueue.then(()=>api.command('markers','replace',{rows:clean(rows),expected_version:expected})).catch(error=>{window.dispatchEvent(new CustomEvent('gravewright:tool-error',{detail:{message:error.message}}));return api.read();});
    }});
    selection=createSelection(surface,board,map,gm,api,stateAPI,{rows:()=>measureRows,replace:rows=>measurement.call('replace',rows)});
    function sync() {
        if (closed || !board.viewport())
            return;
        const layer = stateAPI.getPath('_layer'), tool = stateAPI.getPath('_tool');
        selection?.update(state);
        const measure = ['measure', 'templates'].includes(tool);
        markers.update({...base(),active:tool==='templates',shared:true,rows:state.markers||[],maxRows:state.capabilities?.maxMarkers,measureValue:map.measureValue,measureUnit:map.measureUnit});
        measurement.update({ ...base(), active: tool==='measure', maxRows: state.capabilities?.maxMeasurements, measureValue: map.measureValue, measureUnit: map.measureUnit });
        const draw = gm && tool === 'draw' && ['game', 'gm'].includes(layer);
        if (draw && !drawing)
            drawing = Drawing(hosts.drawing, { ...common, props: { ...base(), document: state.drawings, audience: layer === 'gm' ? 'gm' : 'campaign' }, emit(type) { if (type === 'refresh')
                    void api.read(); if (type === 'close') {
                    stateAPI.mergePatch({ _tool: 'select' });
                    sync();
                } } });
        else if (!draw && drawing) {
            drawing.destroy();
            drawing = undefined;
        }
        else
            drawing?.update({ ...base(), document: state.drawings, audience: layer === 'gm' ? 'gm' : 'campaign' });
        const compose = gm && layer === 'composition' && !measure;
        if (compose && !images)
            images = Images(hosts.images, { ...common, props: { ...base(), images: state.images, tool }, emit(type, value) { if (type === 'refresh')
                    void api.read(); if (type === 'preview')
                    void board.update({ state: value ? { ...state, images: state.images.map(i => i.id === value.id ? value : i) } : state }); } });
        else if (!compose && images) {
            images.destroy();
            images = undefined;
        }
        else
            images?.update({ ...base(), images: state.images, tool });
        const effect = gm && layer === 'effects' && !measure;
        if (effect && !effects)
            effects = Sources(hosts.effects, { ...common, props: { ...base(), state, layer: 'effects', tool }, emit(type, value) { if (type === 'changed')
                    update(value); if (type === 'preview')
                    void board.update({ state: value || state }); if (type === 'tool') {
                    stateAPI.mergePatch({ _tool: value });
                    sync();
                } } });
        else if (!effect && effects) {
            effects.destroy();
            effects = undefined;
        }
        else
            effects?.update({ ...base(), state, tool });
    }
    function update(next) { state = next; sync(); }
    function openLibrary() {
        if (library) {
            library.destroy();
            library = undefined;
            vMovableResizable.unmounted(libraryHost);
            libraryHost.remove();
            return;
        }
        const template = document.querySelector('#map-image-library');
        libraryHost = template.content.firstElementChild.cloneNode(true);
        document.body.append(libraryHost);
        libraryHost.querySelector('[aria-label="Close library"]').onclick = openLibrary;
        library = Library(libraryHost.querySelector('[data-library-body]'), { ...common, props: { containerId: map.containerId, gm, revision: 0 }, emit() { } });
        library.update({ revision: 1 });
        const tabs=libraryHost.querySelectorAll('.upload-library__tabs button');
        if(gm&&tabs[1]){tabs[1].disabled=false;tabs[1].removeAttribute('aria-disabled');}
        tabs.forEach((tab,index)=>tab.onclick=()=>{
            if(index===1&&!gm)return;
            library?.destroy();
            const body=libraryHost.querySelector('[data-library-body]');body.replaceChildren();
            library=index===1?window.gravewrightTableMedia.mountDecks(body):Library(body,{...common,props:{containerId:map.containerId,gm,revision:0},emit(){}});
            tabs.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
        });
        vMovableResizable.mounted(libraryHost);
    }
    function editSelection({detail:{object,event}}){
        if(object.kind==='drawing'){stateAPI.mergePatch({_layer:object.data.audience==='gm'?'gm':'game',_tool:'draw'});sync();drawing?.call('editId',object.id);}
        if(object.kind==='measure'){stateAPI.mergePatch({_layer:'game',_tool:'measure'});sync();measurement.call('editId',object.id);}
        if(['shader','particle'].includes(object.kind)){stateAPI.mergePatch({_layer:'effects',_tool:'select'});sync();effects?.call('doubleClick',event);}
    }
    window.addEventListener('gravewright:selection-edit',editSelection);
    function click(event) {
        // Editors own their input events; refreshing them during a checkbox's
        // click would reset its checked state before the browser emits change.
        if (event.target.closest('input,textarea,select,.gw-window,.effect-picker'))
            return;
        sync();
        const button = event.target.closest('[data-native-tool],.game-menubar__library');
        if (!button)
            return;
        if (button.matches('.game-menubar__library') || button.dataset.nativeTool === 'images')
            openLibrary();
        else if (effects) {
            const tool = button.dataset.nativeTool;
            if (['particle', 'shader'].includes(tool)) {
                stateAPI.mergePatch({ _tool: tool });
                sync();
            }
            effects.call('action', tool);
        }
    }
    window.addEventListener('click', click);
    window.addEventListener('gravewright:map-viewport', sync);
    sync();
    return { update, setMap(next) { Object.assign(map, next); sync(); }, destroy() { closed = true; window.removeEventListener('gravewright:selection-edit',editSelection); selection?.destroy(); drawing?.destroy(); images?.destroy(); effects?.destroy(); measurement.destroy();markers.destroy(); library?.destroy(); if (libraryHost) {
            vMovableResizable.unmounted(libraryHost);
            libraryHost.remove();
        } for (const host of Object.values(hosts))
            host.remove(); window.removeEventListener('click', click); window.removeEventListener('gravewright:map-viewport', sync); } };
}
