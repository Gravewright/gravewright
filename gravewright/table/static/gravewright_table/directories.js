import { openFormModal, modalText } from './form-modal.js';
import { writeReference } from './references.js';
import { restoreWindow } from './window-controls.js';
import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { executeNative } from '/static/gravewright_modules/domain-api.js';
import { openPermissions } from './permissions.js';
import { initialContent, restoreContent, contentReady } from './content-state.js';
import { mountCompendiums } from './compendiums.js';
const root=document.querySelector('#table-workspace'),table=root?.dataset.tableId,gm=root?.dataset.role==='gm',states={items:initialContent('items')},windows=new Map();let scene=window.gravewrightMaps?.current?.id||null;
const modules=['items','combat','compendiums'],pending={};
const panel=name=>document.querySelector(`[data-native-directory="${name}"]`);
function notify(name,error){const node=panel(name)?.querySelector('[data-error]');if(node){node.hidden=!error;node.textContent=error?.message||'';}}
async function refresh(name){const requestedScene=scene;const data=await gravewright[name].state({sceneId:scene});if(name==='combat'&&requestedScene!==scene)return states[name];states[name]=data;render(name);return data;}
async function command(name,action,data){
 if(pending[name])throw Error('Wait for the current change to finish.');
 pending[name]=true;notify(name);
 panel(name)?.querySelectorAll('button,input,select').forEach(el=>el.disabled=true);
 try{const result=await executeNative(gravewright,name,action,{sceneId:scene,...data});await refresh(name);return result;}
 catch(e){notify(name,e);throw e;}
 finally{pending[name]=false;panel(name)?.querySelectorAll('button,input,select').forEach(el=>el.disabled=false);render(name);}
}

function button(text,action){const el=document.createElement('button');el.type='button';el.textContent=text;el.onclick=()=>Promise.resolve().then(action).catch(e=>{const p=el.closest('[role=dialog],aside')?.querySelector('[role=alert]');if(p){p.hidden=false;p.textContent=e.message;}});return el;}
function dialog(title,fields,save,options={}){return openFormModal(title,fields,save,{key:'directory-form:'+fields.map(field=>field.name).join('-'),...options});}

function createItem(item){
 const types=states.items?.types||[];
 const el=dialog(item?item.name:'Create item',[
  {name:'name',label:'Name',value:item?.name},
  {name:'type',label:'Type',value:item?.type||'',options:item?[{value:item.type,label:item.type}]:types.map(t=>({value:t.id,label:t.label}))}
 ],form=>command('items',item?'update':'create',{id:item?.id,version:item?.version,name:form.elements.name.value,type:form.elements.type.value}),{key:item?'item:'+item.id:'item:create'});
 if(item)el.querySelector('[name=type]').disabled=true;
 if(!item&&!types.length){
  const message=document.createElement('p');message.textContent='Enable a system that provides item types to create items.';
  el.querySelector('[data-fields]').append(message);el.querySelector('[type=submit]').disabled=true;
 }
 return el;
}

function itemSheet(item){
 if(item.canOpen===false)return;
 const existing=windows.get(item.id);
 if(existing?.isConnected){existing.focus();return;}
 const sheet=createItem(item);sheet.classList.add('item-sheet');sheet.dataset.itemId=item.id;windows.set(item.id,sheet);
 sheet.addEventListener('close',()=>windows.delete(item.id),{once:true});
 if(!item.canEdit){sheet.querySelector('[name=name]').readOnly=true;sheet.querySelector('[type=submit]').hidden=true;}
}


function render(name){if(name==='combat'&&states.combat){window.gravewrightCombatState={...states.combat,sceneId:scene};window.dispatchEvent(new CustomEvent('gravewright:combat-state',{detail:window.gravewrightCombatState}));}if(name==='items'&&!contentReady()){restoreContent('items',()=>render(name));return;}const target=panel(name),state=states[name];if(!target||!state)return;
 if(name==='compendiums'){if(!target._content)target._content=mountCompendiums(target.querySelector('[data-entries]'),state);else target._content.update(state);return;}
 if(name==='combat'){if(target.contains(document.activeElement)&&document.activeElement.matches('[data-combat-initiative]'))return;target.dataset.selectedTokenCount=String(window.gravewrightTokenSelection?.length||0);window.GravewrightCombatPanel?.renderPanel(target,state);if(pending[name])target.querySelectorAll('button,input').forEach(el=>el.disabled=true);return;}
 const list=target.querySelector('[data-entries]'),query=target.querySelector('input[type=search]').value.toLowerCase();list.replaceChildren();
 if(name==='items'){
  for(const sheet of document.querySelectorAll('.item-sheet[role=dialog]')){const current=state.items.find(item=>item.id===sheet.dataset.itemId);if(!current||current.canOpen===false)sheet.close();else if(!current.canEdit){sheet.querySelector('[name=name]').readOnly=true;sheet.querySelector('[type=submit]').hidden=true;}}
  if(!(state.items||[]).length){const empty=document.createElement('p');empty.className='item-directory__empty';empty.textContent='No items in this table.';list.append(empty);}
  for(const folder of state.folders||[])if(gm){const row=document.createElement('div');row.className='sheet-folder-header';row.textContent=folder.name;row.append(button('Permissions',()=>openPermissions('item-folders',folder.id,{onSave:()=>refresh('items')})),button('Rename',()=>dialog('Rename folder',[{name:'name',label:'Name',value:folder.name}],form=>command('items','folder-update',{id:folder.id,name:form.elements.name.value,parentId:folder.parentId}))),button('Delete',()=>dialog('Delete folder',[],()=>command('items','folder-delete',{id:folder.id}))));list.append(row);}
  for(const item of state.items||[])if(item.name.toLowerCase().includes(query)){const row=document.createElement('div');row.className='directory-entry item-card';row.dataset.itemId=item.id;row.draggable=true;row.addEventListener('dragstart',event=>{event.dataTransfer.effectAllowed='copy';writeReference(event.dataTransfer,{type:'item',id:item.id,title:item.name});event.dataTransfer.setData('application/x-gravewright-item',JSON.stringify({id:item.id,tableId:table}));});row.append(button(item.name,()=>itemSheet(item)));if(item.canEdit)row.append(button('Edit',()=>createItem(item)));if(gm){row.append(button('Duplicate',()=>command('items','duplicate',{id:item.id,version:item.version})),button('Permissions',()=>permission(item)),button('Delete',()=>dialog('Delete '+item.name,[],()=>command('items','delete',{id:item.id,version:item.version}))));}list.append(row);}
 }
}

async function permission(item){return openPermissions('items',item.id,{onSave:()=>refresh('items')});}
async function addEntry(pack){const choices=[];for(const [kind,url,key]of [['actor',`/api/containers/${table}/actors`,'actors'],['item',`/api/containers/${table}/modules-native/items`,'items'],['journal',`/api/containers/${table}/journals`,'journals']]){const r=await fetch(url);if(!r.ok)continue;const data=await r.json();for(const row of data[key]||[])choices.push({value:kind+':'+row.id,label:kind+' · '+(row.name||row.title)});}dialog('Add document',[{name:'entry',label:'Document',options:choices}],form=>{const[kind,id]=form.elements.entry.value.split(':');return command('compendiums','add',{packId:pack.id,kind,resourceId:id});});}
for(const name of modules){const el=panel(name);if(!el)continue;el.querySelector('[data-close]').onclick=()=>{el.hidden=true;};el.querySelector('input[type=search]')?.addEventListener('input',()=>render(name));el.querySelector('[data-create]')?.addEventListener('click',()=>name==='items'?createItem():dialog('Create compendium',[{name:'name',label:'Name'}],form=>command(name,'create',{name:form.elements.name.value})));el.querySelector('[data-folder]')?.addEventListener('click',()=>dialog('Create folder',[{name:'name',label:'Name'}],form=>command('items','folder-create',{name:form.elements.name.value})));}
document.addEventListener('click',e=>{const toggle=e.target.closest('[data-native-directory-toggle]');if(toggle){const name=toggle.dataset.nativeDirectoryToggle==='content'?'compendiums':toggle.dataset.nativeDirectoryToggle;const target=panel(name);if(target.hasAttribute('data-window-minimized')){restoreWindow(target);target.hidden=false;}else target.hidden=!target.hidden;window.gravewrightRealtime.subscribeModule(name,scene);void refresh(name).catch(e=>notify(name,e));}});
window.addEventListener('gravewright:resources',({detail})=>{if(modules.includes(detail.module)&&(detail.module!=='combat'||(detail.sceneId??null)===(scene??null))){states[detail.module]=detail.state;render(detail.module);}});
restoreContent('items', () => render('items'));
window.addEventListener('gravewright:connected',()=>{for(const name of modules)window.gravewrightRealtime.subscribeModule(name,scene);});
window.addEventListener('gravewright:module-scene',()=>{const next=window.gravewrightMaps?.current?.id||null;if(next===scene)return;scene=next;states.combat={active:false,round:0,turn:0,combatants:[],version:0};render('combat');for(const name of modules)window.gravewrightRealtime?.subscribeModule(name,scene);});
window.addEventListener('gravewright:search-open',({detail})=>{if(detail.type==='item')void refresh('items').then(()=>{const item=states.items.items.find(i=>i.id===detail.id);if(item)itemSheet(item);});if(detail.type==='compendium'){panel('compendiums').hidden=false;void refresh('compendiums');}});
const combat=panel('combat');
function combatantIdentity(id){const entry=states.combat?.combatants.find(row=>row.id===id);return entry?.token_id?{tokenId:entry.token_id}:{actorId:entry?.actor_id};}
combat?.addEventListener('change',e=>{if(e.target.dataset.combatInitiative)void command('combat','initiative',{...combatantIdentity(e.target.dataset.combatInitiative),value:states.combat.config?.input==='text'?e.target.value:Number(e.target.value),version:Number(e.target.dataset.combatVersion)}).catch(()=>{});});
combat?.querySelector('[data-initiative-config]')?.addEventListener('submit',e=>{e.preventDefault();void command('combat','configure',{formula:e.target.elements.formula.value,version:states.combat?.version||0}).catch(()=>{});});
combat?.addEventListener('click',async e=>{const b=e.target.closest('[data-combat-action]');if(!b)return;const action=b.dataset.combatAction,tokenId=b.dataset.combatantId;try{
 if(action==='resource/edit'){
  const entry=states.combat?.combatants.find(row=>row.id===tokenId),slot=b.dataset.resourceSlot;
  if(!entry?.canControl||!['bar_1','bar_2'].includes(slot))return;
  const resource=entry.bars?.find(bar=>bar.slot===slot)||entry.bar;
  const label=slot==='bar_2'?modalText('Bar 2','Barra 2'):modalText('Bar 1','Barra 1');
  dialog(`${entry.name} · ${label}`,[{name:'value',label:modalText('Value (+3, -5 or 10)','Valor (+3, -5 ou 10)'),value:String(resource.value),required:true}],async form=>{
   const raw=form.elements.value.value.trim().replace(',','.');
   if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw))throw Error(modalText('Enter a valid number.','Informe um número válido.'));
   const response=await fetch(`/api/containers/${table}/actors/${entry.actor_id}/sheet${entry.token_id?'?tokenId='+encodeURIComponent(entry.token_id):''}`,{cache:'no-store'});
   if(!response.ok)throw Error(modalText('Resource unavailable.','Recurso indisponível.'));
   const sheet=await response.json(),bar=sheet.data?.bars?.[slot];
   if(!sheet.canEdit||!bar||!Number.isFinite(bar.value)||!(bar.max>0))throw Error(modalText('Resource unavailable.','Recurso indisponível.'));
   const value=/^[+-]/.test(raw)?bar.value+Number(raw):Number(raw);
   if(!Number.isFinite(value))throw Error(modalText('Enter a valid number.','Informe um número válido.'));
   bar.value=value;
   await gravewright.actors.saveSheet({actorId:entry.actor_id,tokenId:entry.token_id||undefined,name:sheet.name,version:sheet.version,sheetVersion:sheet.sheetVersion,data:sheet.data});
   await refresh('combat');
  },{key:`combat:resource:${tokenId}:${slot}`});return;
 }
 if(action==='initiative/configure'){dialog(modalText('Combat initiative','Iniciativa do combate'),[{name:'formula',label:modalText('Roll formula (leave empty for manual initiative)','Fórmula de rolagem (deixe vazio para iniciativa manual)'),value:states.combat?.config?.formula||''}],form=>command('combat','configure',{formula:form.elements.formula.value,version:states.combat?.version||0}),{key:'combat:initiative'});return;}
 if(action==='combatants/add-actor'){const r=await fetch(`/api/containers/${table}/actors`);if(!r.ok)throw Error('Unable to load actors.');const data=await r.json();dialog(modalText('Add character','Adicionar personagem'),[{name:'actor',label:modalText('Character','Personagem'),options:data.actors.map(a=>({value:a.id,label:a.name}))}],form=>command('combat','add',{actorId:form.elements.actor.value,version:states.combat?.version||0}));return;}
 if(action==='combatants/add-selected'){for(const id of [...(window.gravewrightTokenSelection||[])])await command('combat','add',{tokenId:id,version:states.combat?.version||0});return;}
 if(action==='token/sheet'){const token=(window.gravewrightTokenState?.tokens||[]).find(t=>t.id===b.dataset.tokenId);if(token)window.gravewrightActors.open(token.actorId,token);return;}
 if(action==='token/focus'){window.dispatchEvent(new CustomEvent('gravewright:focus-token',{detail:{id:b.dataset.tokenId}}));return;}
 const actions={end:'stop',start:'start','turn/next':'next','turn/previous':'previous','round/next':'next-round','round/previous':'previous-round','turn/set':'set-turn','order/up':'order-up','order/down':'order-down','combatants/remove':'remove','initiative/roll-all':'roll','initiative/roll-npcs':'roll','initiative/roll-missing':'roll','initiative/roll-one':'roll','flags/hidden':'toggle','flags/defeated':'toggle'};
 await command('combat',actions[action],{...combatantIdentity(tokenId),scope:action.startsWith('initiative/roll-')?action.slice('initiative/roll-'.length):undefined,version:states.combat?.version||0,...action==='flags/hidden'?{hidden:b.dataset.value==='1'}:{},...action==='flags/defeated'?{defeated:b.dataset.value==='1'}:{}});
 }catch(error){notify('combat',error);}});
window.addEventListener('gravewright:token-selection',()=>{if(combat&&!combat.hidden&&!combat.contains(document.activeElement))render('combat');});
window.gravewrightItems={open:async id=>{await refresh('items');const item=states.items.items.find(i=>i.id===id);if(item)itemSheet(item);}};
