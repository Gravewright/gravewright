import { mountModal } from '/static/gravewright_table/modal.js';
import { HttpClient } from '/static/gravewright_modules/http-client.js';
import { organizeSelection, groupSelection, selectionBundle, placeBundle, objectBrushSamples, scatterObject } from './productivity-model.js';
import { objectKinds, sampleAssetId } from './model.js';

export function createProductivity({root,state,t,signal,base,refs,select,commit,render,setTool,brushAssets,notify,remember,isBusy,playerTest}) {
    const http=new HttpClient(), svgNS='http://www.w3.org/2000/svg';
    let modal, pending, stroke, saving=false;
    state.objectBrush={enabled:false,spacing:1,scaleVariation:.2,rotationVariation:180,...state.objectBrush};
    const areas=document.createElementNS(svgNS,'g');areas.dataset.builderAllAreas='';areas.setAttribute('pointer-events','none');
    root.querySelector('[data-builder-guides]').append(areas);
    const make=(tag,text,attrs={})=>{const el=document.createElement(tag);if(text)el.textContent=t(text);for(const [k,v]of Object.entries(attrs))el.setAttribute(k,v);return el;};
    const button=(text,run,attrs={})=>{const el=make('button',text,{type:'button',...attrs});el.onclick=()=>void run();return el;};
    const fail=error=>notify(t(error.message||'Could not complete this action.'),[],'error');
    function apply(next,selection) {
        if(!next)throw Error('The selection cannot be changed. Check bounds, locks and door overlaps.');
        state.document=next;if(selection)select(selection);commit();render();
    }
    function drawAreas() {
        areas.replaceChildren();
        if(!state.showObjectAreas||state.preview)return;
        const visible=new Set(state.document.layers.filter(layer=>layer.visible&&(!state.soloLayer||state.soloLayer===layer.id)).map(layer=>layer.id));
        const matrix=root.querySelector('[data-builder-canvas]').getScreenCTM();
        const scale=Math.max(.001,matrix?Math.hypot(matrix.a,matrix.b):1);
        const items=[...state.document.decorations.filter(item=>Number.isFinite(item.presenceRadius)&&state.layers.decorations),...state.document.regions.filter(item=>state.layers.regions)];
        for(const item of items)if(visible.has(item.layerId)){
            const group=document.createElementNS(svgNS,'g'),color=item.torch?'#79c39a':item.lever?'#c09a5a':'#86bde8';
            const circular=Number.isFinite(item.presenceRadius),circle=document.createElementNS(svgNS,circular?'circle':'rect');
            const geometry=circular?{cx:item.x+item.width/2,cy:item.y+item.height/2,r:item.presenceRadius}:{x:item.x,y:item.y,width:item.width,height:item.height};
            for(const [key,value]of Object.entries({...geometry,fill:color,'fill-opacity':.08,stroke:color,'stroke-width':1.5,'vector-effect':'non-scaling-stroke','data-builder-area-overview':item.id}))circle.setAttribute(key,value);
            const name=document.createElementNS(svgNS,'text');
            for(const [key,value]of Object.entries({x:item.x+item.width/2,y:item.y+item.height/2+(circular?item.presenceRadius:item.height/2),fill:color,'text-anchor':'middle','font-size':12/scale,'paint-order':'stroke',stroke:'#10151b','stroke-width':3/scale,translate:'no'}))name.setAttribute(key,value);
            name.textContent=item.name||t('Object');group.append(circle,name);areas.append(group);
        }
    }
    function field(parent,label,input){const el=make('label',label);el.append(input);parent.append(el);return input;}
    function section(body,label){const el=make('section');el.append(make('h3',label));body.append(el);return el;}
    async function open() {
        if(isBusy()||state.preview||modal)return;
        modal=make('section',null,{class:'builder-productivity','aria-label':t('Builder tools'),'data-builder-productivity':''});
        const abort=new AbortController();let requestKey,requestId;
        const header=make('header');header.append(make('strong','Builder tools'),button('Close',()=>modal.close()));
        const body=make('div',null,{class:'builder-productivity__body'}),error=make('p',null,{role:'alert'});
        const guarded=task=>async()=>{if(saving)return;error.textContent='';try{await task();}catch(cause){error.textContent=t(cause.message);}};
        const organization=section(body,'Organize selection');
        const layerName=field(organization,'Group name',make('input',null,{type:'text',maxlength:'80',translate:'no','data-builder-group-name':''}));
        organization.append(button('Group selection in a layer',guarded(()=>{const result=groupSelection(state.document,refs(),layerName.value);if(!result)throw Error('Select objects and enter a group name.');state.activeLayer=result.layerId;apply(result.document);}),{'data-builder-group-selection':''}));
        organization.append(make('p','Use Project layers to hide, lock or move the group.'));
        const arrangement=section(body,'Align and distribute'),actions=make('div',null,{class:'builder-productivity__actions'});
        for(const [value,label]of [['left','Align left'],['center','Center horizontally'],['right','Align right'],['top','Align top'],['middle','Center vertically'],['bottom','Align bottom'],['distribute-x','Distribute horizontally'],['distribute-y','Distribute vertically']]){
            actions.append(button(label,guarded(()=>apply(organizeSelection(state.document,refs(),value))),{'data-builder-arrange':value}));
        }
        arrangement.append(actions);
        const angle=field(arrangement,'Rotation (degrees)',make('input',null,{type:'number',min:'-360',max:'360',value:'90',required:''}));
        arrangement.append(button('Rotate selection',guarded(()=>{if(!angle.checkValidity())return;apply(organizeSelection(state.document,refs(),'rotate',Number(angle.value)));})));
        const display=section(body,'Activation areas');
        const show=field(display,'Show all object activation areas',make('input',null,{type:'checkbox','data-builder-show-areas':''}));show.checked=!!state.showObjectAreas;
        show.onchange=()=>{state.showObjectAreas=show.checked;remember();drawAreas();};
        const paint=section(body,'Object brush');
        const enabled=field(paint,'Paint multiple objects',make('input',null,{type:'checkbox','data-builder-object-brush':''}));enabled.checked=state.objectBrush.enabled;
        enabled.onchange=()=>{state.objectBrush.enabled=enabled.checked;if(enabled.checked)setTool('decoration');remember();};
        for(const [key,label,min,max,step,multiplier]of [['spacing','Spacing (cells)',.1,20,.1,1],['scaleVariation','Size variation (%)',0,90,1,100],['rotationVariation','Rotation variation (degrees)',0,180,1,1]]){
            const input=field(paint,label,make('input',null,{type:'number',min,max,step,required:'',value:state.objectBrush[key]*multiplier,'data-builder-scatter-option':key}));
            input.onchange=()=>{if(input.checkValidity()){state.objectBrush[key]=Number(input.value)/multiplier;remember();}};
        }
        paint.append(make('p','Choose an uploaded object or family in the library, then drag on the map. Each stroke is one undo step.'));
        const library=section(body,'My objects');
        const name=field(library,'Preset name',make('input',null,{type:'text',maxlength:'120',translate:'no','data-builder-preset-name':''}));
        const list=make('div',null,{'data-builder-object-presets':''});
        const refresh=async()=>{
            const result=await http.get(base+'/object-presets',{signal:abort.signal});
            if(abort.signal.aborted)return;
            list.replaceChildren();
            if(!result.presets.length)list.append(make('p','No saved objects yet.'));
            for(const preset of result.presets){
                const row=make('div',null,{class:'builder-productivity__preset'}),label=make('strong');label.textContent=preset.name;label.translate=false;
                row.append(label,button('Place',guarded(async()=>{const data=await http.get(base+'/object-presets/'+preset.id,{signal:abort.signal});const catalog=await http.get(base,{signal:abort.signal});state.assets=catalog.assets;pending=data.document;state.objectBrush.enabled=false;setTool('select');modal.close();notify(t('Click on the map to place the saved objects. Escape cancels.'));}),{'data-builder-place-preset':preset.id}),
                    button('Delete',guarded(async()=>{await http.delete(base+'/object-presets/'+preset.id,{}, {signal:abort.signal});await refresh();}),{'data-builder-delete-preset':preset.id}));list.append(row);
            }
        };
        library.append(button('Save selection to My objects',guarded(async()=>{
            if(!name.value.trim())throw Error('Enter a preset name.');
            const document=selectionBundle(state.document,refs()),key=JSON.stringify([name.value,document]);
            if(key!==requestKey){requestKey=key;requestId=crypto.randomUUID();}
            saving=true;
            try{await http.post(base+'/object-presets',{request_id:requestId,name:name.value,document},{signal:abort.signal});requestKey=undefined;await refresh();}
            finally{saving=false;}
        }),{'data-builder-save-preset':''}),list);
        const test=section(body,'Test as player');
        test.append(make('p','Walk through the draft to test vision, collisions and activation areas. The live scene is not changed.'));
        test.append(button('Test as player',()=>{modal.close();playerTest();},{'data-builder-player-test':''}));
        body.append(error);modal.append(header,body);
        modal.addEventListener('close',()=>{abort.abort();modal.remove();modal=undefined;},{once:true});
        mountModal(modal,{canClose:()=>!saving});
        try{await refresh();}catch(cause){if(!abort.signal.aborted)error.textContent=t(cause.message);}
    }
    function place(point) {
        if(!pending)return false;
        try{const result=placeBundle(state.document,pending,point,state.activeLayer,state.limits.maxObjects||2000);if(!result)throw Error('The saved objects do not fit here. Choose a visible, unlocked layer and check object limits.');apply(result.document,result.refs);pending=undefined;}
        catch(error){fail(error);}
        return true;
    }
    function stamp(point) {
        if(objectKinds.reduce((sum,kind)=>sum+(state.document[kind]?.length||0),0)>=(state.limits.maxObjects||2000))return false;
        const item=scatterObject(state.document,point,{...state.brush,...state.objectBrush,layerId:state.activeLayer,assetId:sampleAssetId(brushAssets('decoration'))});
        if(item){state.document.decorations.push(item);stroke.refs.push({kind:'decorations',id:item.id});return true;}return false;
    }
    function startBrush(point){
        if(!state.objectBrush.enabled||state.tool!=='decoration')return false;
        if(!brushAssets('decoration').some(Boolean)){notify(t('Choose an uploaded object before painting.'),[],'error');stroke={point,carry:0,refs:[]};return true;}
        stroke={point,carry:0,refs:[]};stamp(point);return true;
    }
    function paint(point){
        if(!stroke)return;
        const {samples,carry}=objectBrushSamples(stroke.point,point,state.objectBrush.spacing,stroke.carry);let changed=false;
        for(const sample of samples)changed=stamp(sample)||changed;
        stroke.point=point;stroke.carry=carry;if(changed)render();
    }
    function finishBrush(){const result=stroke?.refs||[];stroke=undefined;select(result);return result.length>0;}
    root.querySelector('[data-builder-productivity-open]').addEventListener('click',open,{signal});
    document.addEventListener('keydown',event=>{if(event.key==='Escape')pending=undefined;},{signal,capture:true});
    signal.addEventListener('abort',()=>{modal?.close(true);areas.remove();pending=stroke=undefined;},{once:true});
    return {drawAreas,place,startBrush,paint,finishBrush};
}
