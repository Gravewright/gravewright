import {sceneObjects,hit,corners,centerOf,transformedPoint} from '../model/objects.js';
import {applySelection,transformMeasures} from '../model/selection-commands.js';
import {effects,translatedCopies} from '../../effects/model/effects.js';

// This controller observes the shared surface in capture phase. Token-only
// gestures continue to reach the existing token controller, including Ctrl paths.
export function createSelection(surface,board,map,gm,api,stateAPI,measurements){
 const abort=new AbortController(),signal=abort.signal,svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.classList.add('selection-workspace');svg.setAttribute('aria-label','Scene object selection');surface.append(svg);
 const notice=document.createElement('p');notice.className='selection-workspace__error';notice.hidden=true;surface.append(notice);
 let state=api.state,selected=[],drag,preview,busy=false,menu,dialog,timer,pingTimer,clipboard=[],lastPoint={x:0,y:0};
 const cell=()=>map.gridSize*map.imageScale,origin=()=>({x:(map.gridOffsetX||0)*map.imageScale,y:(map.gridOffsetY||0)*map.imageScale});
 const active=()=>stateAPI.getPath('_tool')==='select'&&!document.querySelector('.grid-calibration-panel')&&document.querySelector('#table-workspace')?.dataset.role!=='streamer';
 const all=()=>sceneObjects(state,window.gravewrightTokenState?.tokens||[],cell(),gm,measurements.rows(),origin());
 const chosen=()=>all().filter(o=>selected.includes(o.key));
 const mixed=()=>chosen().some(o=>o.kind!=='token');
 const point=e=>{const b=surface.getBoundingClientRect(),v=board.viewport();return {x:(e.clientX-b.left-v.x)/v.scale,y:(e.clientY-b.top-v.y)/v.scale};};
 const pick=p=>all().reverse().find(o=>hit(o,p,5/board.viewport().scale));
 const stop=e=>{e.preventDefault();e.stopImmediatePropagation();};
 function node(tag,attrs){const n=document.createElementNS(svg.namespaceURI,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;}
 function paint(){
  svg.replaceChildren();if(!active())return;
  const v=board.viewport();if(!v)return;
  const group=node('g',{transform:`translate(${v.x} ${v.y}) scale(${v.scale})`});svg.append(group);
  for(const o of all().filter(o=>['light','particle','shader','sound'].includes(o.kind)))group.append(node('circle',{cx:o.x,cy:o.y,r:5/v.scale,fill:o.kind==='sound'?'#65c9b8':'#cda5e8'}));
  for(const o of chosen()){const points=corners(o).map(p=>preview?transformedPoint(p,preview.center,preview.dx,preview.dy,preview.angle):p).map(p=>`${p.x},${p.y}`).join(' ');group.append(node('polygon',{points,fill:'#e1b46608',stroke:'#ffe29a','stroke-width':1.5/v.scale,'stroke-dasharray':`${5/v.scale} ${3/v.scale}`,'data-selected-object':o.key}));}
  if(drag&&!drag.moving){const a=drag.from,b=drag.to;group.append(node('rect',{x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),width:Math.abs(a.x-b.x),height:Math.abs(a.y-b.y),fill:'#e1b46618',stroke:'#e1b466','stroke-width':1/v.scale}));}
 }
 function publish(){const value=preview?{...preview,objects:drag?.objects||chosen()}:undefined;board.previewSelection?.(value);window.dispatchEvent(new CustomEvent('gravewright:selection-preview',{detail:value}));paint();}
 function select(keys){selected=keys;window.dispatchEvent(new CustomEvent('gravewright:mixed-selection',{detail:{ids:chosen().filter(o=>o.kind==='token').map(o=>o.id),mixed:mixed()}}));paint();}
 function cancel(){clearTimeout(timer);clearTimeout(pingTimer);if(drag&&surface.hasPointerCapture(drag.id))surface.releasePointerCapture(drag.id);drag=undefined;preview=undefined;menu?.remove();menu=undefined;publish();}
 const ignored=e=>e.target.closest('button,input,textarea,select,dialog,.gw-window,.directory-context-menu,.game-dock,.door-controls');
 function down(e){
  if(!active()||busy||e.button!==0||ignored(e))return;
  const p=point(e),o=pick(p);
  if((e.ctrlKey&&!mixed())||(o?.kind==='token'&&!mixed()&&!e.shiftKey))return;
  stop(e);cancel();notice.hidden=true;
  if(o)select(e.shiftKey?(selected.includes(o.key)?selected.filter(k=>k!==o.key):[...selected,o.key]):selected.includes(o.key)?selected:[o.key]);
  else if(!e.shiftKey)select([]);
  drag={id:e.pointerId,from:p,to:p,objects:chosen(),additive:[...selected],moving:!!o};
  surface.setPointerCapture(e.pointerId);
  if(!o)pingTimer=setTimeout(()=>{if(drag)window.gravewrightMaps?.ping(p,e.shiftKey);},700);
  paint();
 }
 function move(e){if(!active())return;lastPoint=point(e);if(!drag||drag.id!==e.pointerId)return;stop(e);drag.to=lastPoint;
  if(Math.hypot(lastPoint.x-drag.from.x,lastPoint.y-drag.from.y)*board.viewport().scale>10)clearTimeout(pingTimer);
  if(drag.moving){preview={center:centerOf(drag.objects),dx:lastPoint.x-drag.from.x,dy:lastPoint.y-drag.from.y,angle:0};publish();}
  else{const a=drag.from,b=lastPoint;select([...new Set([...drag.additive,...all().filter(o=>corners(o).every(p=>p.x>=Math.min(a.x,b.x)&&p.x<=Math.max(a.x,b.x)&&p.y>=Math.min(a.y,b.y)&&p.y<=Math.max(a.y,b.y))).map(o=>o.key)])]);}
 }
 function up(e){if(!drag||drag.id!==e.pointerId)return;move(e);stop(e);const t=preview;clearTimeout(pingTimer);if(surface.hasPointerCapture(e.pointerId))surface.releasePointerCapture(e.pointerId);drag=undefined;
  if(t&&Math.abs(t.dx)+Math.abs(t.dy)>.5)void execute('transform',t);else{preview=undefined;publish();}
 }
 const tokenCommand=(action,data)=>window.gravewrightRealtime.resourceCommand('tokens',action,{...data,mapId:map.id});
 const tokenApi={remove:(_,id)=>tokenCommand('remove',{tokenIds:[id]}),move:async(_,id,data)=>{const result=await tokenCommand('move',{id,...data});return result.tokens.find(t=>t.id===id);},command:(_c,_m,action,data)=>tokenCommand(action,data)};
 const adapter={command:(_c,_b,area,action,data)=>['cards','spatial-sounds'].includes(area)?window.gravewrightTableMedia.areaCommand(area,action,data):api.command(area,action,data)};
 async function execute(action,t=preview||{center:chosen().length?centerOf(chosen()):{x:0,y:0},dx:0,dy:0,angle:0}){
  if(busy||!chosen().length)return;clearTimeout(timer);busy=true;menu?.remove();dialog?.close();notice.hidden=true;
  const rows=chosen();try{const result=await applySelection(adapter,tokenApi,map.containerId,map.blockId,map.id,cell(),state,rows,action,t.center,t.dx,t.dy,t.angle,origin());if(signal.aborted)return;
   if(['delete','transform'].includes(action))measurements.replace(transformMeasures(measurements.rows(),rows.filter(o=>o.kind==='measure').map(o=>o.id),action,t.center,t.dx,t.dy,t.angle));
   if(result.failed.length){notice.textContent=`${result.failed.length} object(s) refused. Other changes were applied. Refreshing the scene…`;notice.hidden=false;select(result.failed);}else if(action==='delete')select([]);
   await api.read();
  }catch(error){if(!signal.aborted){notice.textContent=error.message;notice.hidden=false;}}
  finally{busy=false;preview=undefined;if(!signal.aborted)publish();}
 }
 function rotate(angle,defer=false){if(busy||drag||!chosen().length)return;preview={...(preview||{center:centerOf(chosen()),dx:0,dy:0,angle:0}),angle:(preview?.angle||0)+angle};publish();clearTimeout(timer);if(defer)timer=setTimeout(()=>void execute('transform'),180);else void execute('transform');}
 function copy(){clipboard=[...effects(state),...effects(state,'lighting')].filter(o=>selected.includes(o.key));menu?.remove();}
 async function paste(){if(!clipboard.length||busy)return;busy=true;try{for(const area of ['effects','light-selection']){const rows=translatedCopies(clipboard,lastPoint).filter(o=>(o.kind==='light')===(area==='light-selection'));if(rows.length)await api.command(area,'paste',{effects:rows});}await api.read();}catch(error){notice.textContent=error.message;notice.hidden=false;}finally{busy=false;}}
 function confirmDelete(){dialog?.remove();dialog=document.createElement('dialog');dialog.className='directory-dialog';const form=document.createElement('form'),title=document.createElement('h3'),text=document.createElement('p'),remove=document.createElement('button'),close=document.createElement('button');title.textContent='Remove scene objects';text.textContent=`Remove ${chosen().length} object(s)? Cards go to the discard pile; actor and asset definitions are preserved.`;remove.textContent='Remove selection';remove.type='submit';close.textContent='Cancel';close.type='button';close.onclick=()=>dialog.close();form.append(title,text,close,remove);form.onsubmit=e=>{e.preventDefault();void execute('delete');};dialog.append(form);document.body.append(dialog);dialog.onclose=()=>dialog.remove();dialog.showModal();}
 function context(e){if(!active()||ignored(e))return;const o=pick(point(e));if(!o||o.kind==='token'&&!mixed())return;stop(e);cancel();lastPoint=point(e);if(!selected.includes(o.key))select([o.key]);menu=document.createElement('menu');menu.className='directory-context-menu gw-folder-menu';menu.style.position='fixed';menu.style.left=`${e.clientX}px`;menu.style.top=`${e.clientY}px`;
  function add(label,fn){const b=document.createElement('button');b.textContent=label;b.onclick=()=>{menu?.remove();fn();};menu.append(b);}
  if(chosen().some(o=>['light','particle','shader'].includes(o.kind)))add('Copy lights and effects',copy);
  if(clipboard.length)add('Paste lights and effects',()=>void paste());
  if(chosen().length===1&&!['image','card','zone'].includes(o.kind))add('Edit',()=>editObject(o,e));
  add('Rotate selection −90°',()=>rotate(-90));add('Rotate selection +90°',()=>rotate(90));
  if(chosen().some(o=>o.kind==='image')){add('Hide images from players',()=>void execute('hide'));add('Reveal images to players',()=>void execute('show'));}
  if(chosen().some(o=>o.kind==='card'))add('Flip selected cards',()=>void execute('flip'));
  add('Delete selection',confirmDelete);document.body.append(menu);
 }
 function editObject(object,event){window.dispatchEvent(new CustomEvent('gravewright:selection-edit',{detail:{object,event}}));}
 function double(e){if(!active()||ignored(e))return;const o=pick(point(e));if(!o||o.kind==='token')return;stop(e);editObject(o,e);}
 function key(e){if(!active()||e.target.closest?.('input,textarea,select,[contenteditable=true],.directory-dialog')||document.querySelector('dialog[open]'))return;
  const k=e.key.toLowerCase();if((e.ctrlKey||e.metaKey)&&k==='a'){stop(e);select(all().map(o=>o.key));}
  else if(k==='escape'&&(mixed()||drag||preview)){stop(e);cancel();select([]);}
  else if((e.ctrlKey||e.metaKey)&&['c','v'].includes(k)&&(clipboard.length||chosen().some(o=>['light','particle','shader'].includes(o.kind)))){stop(e);if(k==='c')copy();else void paste();}
  else if(k==='f'&&chosen().length&&chosen().every(o=>o.kind==='card')){stop(e);void execute('flip');}
  else if(['delete','backspace'].includes(k)&&mixed()){stop(e);confirmDelete();}
 }
 for(const[event,handler]of [['pointerdown',down],['pointermove',move],['pointerup',up],['pointercancel',cancel],['contextmenu',context],['dblclick',double]])surface.addEventListener(event,handler,{capture:true,signal});
 surface.addEventListener('wheel',e=>{if(active()&&e.shiftKey&&chosen().length){stop(e);rotate(e.deltaY>0?15:-15,true);}},{capture:true,passive:false,signal});
 window.addEventListener('keydown',key,{capture:true,signal});window.addEventListener('blur',cancel,{signal});
 window.addEventListener('gravewright:token-selection',()=>{if(!mixed())select((window.gravewrightTokenSelection||[]).map(id=>'token:'+id));},{signal});
 window.addEventListener('gravewright:map-viewport',paint,{signal});
 return {update(next){state=next;const valid=new Set(all().map(o=>o.key));selected=selected.filter(k=>valid.has(k));if(!active()){cancel();selected=[];}paint();},destroy(){abort.abort();cancel();dialog?.remove();svg.remove();notice.remove();}};
}
