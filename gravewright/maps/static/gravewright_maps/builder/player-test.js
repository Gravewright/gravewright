import { mountModal } from '/static/gravewright_table/modal.js';
import { movementBlocked, visibilityPolygon } from '../builder-player-test.js';
import { playerWalls, playerDocument, areaEvents, authoredTestDocument } from './player-test-model.js';
import { projectTestDocument } from './playtest-model.js';
import { documentBounds } from './model.js';
import { defaultBlueprint, eventGraph, connectNodes, canInteractWithBlueprintDoor } from './blueprint-model.js';

export function openPlayerTest({source,actors,t,preview,execute,onClose}) {
    const abort=new AbortController(),{signal}=abort,NS='http://www.w3.org/2000/svg';
    const make=(tag,text,attrs={})=>{const el=document.createElement(tag);if(text)el.textContent=t(text);for(const[key,value]of Object.entries(attrs))el.setAttribute(key,value);return el;};
    const svg=(tag,attrs={})=>{const el=document.createElementNS(NS,tag);for(const[key,value]of Object.entries(attrs))el.setAttribute(key,value);return el;};
    const modal=make('section',null,{class:'builder-productivity builder-player-test','aria-label':t('Test as player'),'data-builder-player-simulation':''}),header=make('header');
    const close=make('button','Close',{type:'button'});close.onclick=()=>modal.close();header.append(make('strong','Test as player'),close);
    const body=make('div',null,{class:'builder-productivity__body'}),note=make('p','Click or use arrow keys to walk. Interact with nearby objects. Timers do not advance and no effects are sent to players.');
    const actor=make('select',null,{'aria-label':t('Test actor')}),radius=make('input',null,{type:'number',min:1,max:200,value:8,'aria-label':t('Vision radius (cells)')});
    actor.append(new Option(t('No triggering token'),''));for(const row of actors)actor.append(new Option(row.name,row.id));
    if(actors.length)actor.value=actors[0].id;
    for(const[label,control]of [['Test actor',actor],['Vision radius (cells)',radius]]){const field=make('label',label);field.append(control);body.append(field);}
    const map=make('div',null,{class:'builder-player-test__map',tabindex:0,'aria-label':t('Player test map'),'data-builder-player-test-map':''});
    const status=make('p',null,{role:'status','aria-live':'polite'}),log=make('ul',null,{'data-builder-player-test-log':''}),interact=make('button','Interact',{type:'button','data-builder-test-interact':''}),reset=make('button','Reset test',{type:'button'});
    body.append(note,map,status,interact,reset,log);modal.append(header,body);
    let draft=structuredClone(source),point={x:.5,y:.5},disposePreview,busy=false,revision=0,paintedRevision=-1;
    const bounds=documentBounds(source);point={x:Math.min(1.5,bounds.width-.5),y:Math.min(1.5,bounds.height-.5)};
    const initial={...point};
    function logEvent(message){const li=make('li');li.textContent=message;log.prepend(li);while(log.children.length>100)log.lastChild.remove();}
    function decorate(){
        if(signal.aborted||!map.isConnected)return;
        const canvas=map.querySelector('svg');if(!canvas)return;
        for(const node of canvas.querySelectorAll('[data-builder-test-fog],[data-builder-test-pawn]'))node.remove();
        canvas.removeAttribute('aria-hidden');canvas.setAttribute('aria-label',t('Player test map'));
        const vision=visibilityPolygon(point,Math.max(1,Math.min(200,Number(radius.value)||8)),playerWalls(draft));
        const fog=svg('path',{d:`M0 0H${bounds.width}V${bounds.height}H0Z M${vision.map(p=>`${p.x} ${p.y}`).join('L')}Z`,fill:'#10151b','fill-rule':'evenodd','pointer-events':'none','data-builder-test-fog':''});
        canvas.append(fog,svg('circle',{cx:point.x,cy:point.y,r:.3,fill:'#86d8ca',stroke:'#fff','stroke-width':.05,'data-builder-test-pawn':''}));
        const effects=map.querySelector('.playtest__effects');
        if(effects){const matrix=canvas.getScreenCTM(),box=map.getBoundingClientRect();effects.style.clipPath=`polygon(${vision.map(p=>{const q=new DOMPoint(p.x,p.y).matrixTransform(matrix);return `${q.x-box.x}px ${q.y-box.y}px`;}).join(',')})`;}
    }
    function draw(){
        if(disposePreview&&paintedRevision===revision){decorate();return;}
        disposePreview?.();disposePreview=preview(map,playerDocument(draft),decorate);paintedRevision=revision;
    }
    async function trigger(id,event,location){
        const owner=[...draft.decorations,...draft.doors,...draft.regions].find(item=>item.id===id);
        const document=authoredTestDocument(draft);
        const entry=[...document.decorations,...document.doors,...document.regions].find(item=>item.id===id);
        if(!entry?.blueprint?.graphs?.[event]){
            if(event!=='interact'){logEvent(`${owner?.name||t('Object')} · ${t(event==='presence:enter'?'On area enter':'On area exit')}`);return;}
            const kind=entry.torch?'torch':entry.lever?'lever':'door';
            if(kind==='door'&&!canInteractWithBlueprintDoor({...entry,kind:'door'}))throw Error('This door is locked.');
            const graph=eventGraph(event),state=kind==='door'?entry.state:entry[kind].state;
            graph.nodes.push({id:'native-toggle',type:'state',targetState:kind==='door'?(state==='open'?'closed':'open'):(state==='on'?'off':'on'),x:320,y:60});
            connectNodes(graph,'event','next','native-toggle');
            entry.blueprint||=defaultBlueprint(kind);entry.blueprint.graphs[event]=graph;
        }
        const result=await execute(document,id,event,actor.value,location,signal);
        if(signal.aborted)return;
        if(result.error)throw Error(result.error.message);
        const moved=result.changes?.tokens?.find(change=>change.id===result.testTokenId&&change.after);
        if(moved)point={x:moved.after.grid_x+.5,y:moved.after.grid_y+.5};
        draft=projectTestDocument(draft,result);if(result.changes?.elements?.length)revision++;
        logEvent(`${owner?.name||t('Object')} · ${t(event==='interact'?'Interact':event==='presence:enter'?'On area enter':'On area exit')}`);
        for(const emission of result.emissions||[])if(emission.text)logEvent(String(emission.text));
    }
    async function walk(to){
        if(busy||to.x<.5||to.y<.5||to.x>bounds.width-.5||to.y>bounds.height-.5)return;
        const token={gridX:point.x-.5,gridY:point.y-.5,cells:1};
        if(movementBlocked(token,{gridX:to.x-.5,gridY:to.y-.5},playerWalls(draft),1)){status.textContent=t('Movement blocked by a wall.');return;}
        const previous=point;point=to;busy=true;status.textContent='';
        try{for(const event of areaEvents(draft,previous,to,{actorId:actor.value,disposition:'neutral',hidden:false}))await trigger(event.id,event.event,event.point);}
        catch(error){if(!signal.aborted)status.textContent=t(error.message);}
        finally{busy=false;if(!signal.aborted)draw();}
    }
    map.addEventListener('click',event=>{const canvas=map.querySelector('svg');if(!canvas||!canvas.getScreenCTM())return;map.focus();const q=new DOMPoint(event.clientX,event.clientY).matrixTransform(canvas.getScreenCTM().inverse());void walk({x:q.x,y:q.y});},{signal});
    map.addEventListener('keydown',event=>{const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];if(delta){event.preventDefault();void walk({x:point.x+delta[0],y:point.y+delta[1]});}},{signal});
    radius.onchange=()=>{if(radius.checkValidity())draw();};
    interact.onclick=async()=>{if(busy)return;busy=true;try{
        const nearby=[...draft.decorations.filter(item=>item.lever||item.torch),...draft.doors].map(item=>({item,distance:Math.hypot(point.x-(item.x!==undefined?item.x+item.width/2:(item.x1+item.x2)/2),point.y-(item.y!==undefined?item.y+item.height/2:(item.y1+item.y2)/2))})).filter(entry=>entry.distance<=1.5).sort((a,b)=>a.distance-b.distance)[0];
        if(!nearby){status.textContent=t('Move closer to an interactive object.');return;}await trigger(nearby.item.id,'interact',point);draw();
    }catch(error){if(!signal.aborted)status.textContent=t(error.message);}finally{busy=false;}};
    reset.onclick=()=>{if(busy)return;draft=structuredClone(source);point={...initial};revision++;log.replaceChildren();status.textContent='';draw();};
    const resize=new ResizeObserver(()=>decorate());resize.observe(map);
    modal.addEventListener('close',()=>{abort.abort();resize.disconnect();disposePreview?.();modal.remove();onClose();},{once:true});
    mountModal(modal,{canClose:()=>!busy});draw();map.focus();return modal;
}
