import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { executeNative } from '/static/gravewright_modules/domain-api.js';
const root=document.querySelector('#table-workspace'),table=root?.dataset.tableId,gm=root?.dataset.role==='gm',states={},windows=new Map();let scene;
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

function button(text,action){const el=document.createElement('button');el.type='button';el.textContent=text;el.onclick=()=>Promise.resolve().then(action).catch(e=>{const p=el.closest('dialog,aside')?.querySelector('[role=alert]');if(p){p.hidden=false;p.textContent=e.message;}});return el;}
function dialog(title,fields,save){const el=document.createElement('dialog');el.className='directory-dialog';el.innerHTML='<form><header><strong></strong><button type="button" data-close aria-label="Close">×</button></header><p role="alert" hidden></p><div data-fields></div><footer><button type="submit">Save</button></footer></form>';el.querySelector('strong').textContent=title;const body=el.querySelector('[data-fields]');for(const field of fields){const label=document.createElement('label');label.textContent=field.label;const input=document.createElement(field.options?'select':field.multiline?'textarea':'input');input.name=field.name;if(field.options)for(const o of field.options)input.add(new Option(o.label,o.value));else input.type=field.type||'text';input.value=field.value??'';if(field.type==='checkbox')input.checked=!!field.value;label.append(input);body.append(label);}el.querySelector('[data-close]').onclick=()=>el.close();el.onclose=()=>el.remove();el.querySelector('form').onsubmit=async e=>{e.preventDefault();const submit=el.querySelector('[type=submit]');submit.disabled=true;try{await save(e.target);el.close();}catch(error){const p=el.querySelector('[role=alert]');p.hidden=false;p.textContent=error.message;}finally{submit.disabled=false;}};document.body.append(el);el.showModal();return el;}
function createItem(item){
 const types=states.items?.types||[];
 const el=dialog(item?item.name:'Create item',[
  {name:'name',label:'Name',value:item?.name},
  {name:'type',label:'Type',value:item?.type||'',options:item?[{value:item.type,label:item.type}]:types.map(t=>({value:t.id,label:t.label}))}
 ],form=>command('items',item?'update':'create',{id:item?.id,version:item?.version,name:form.elements.name.value,type:form.elements.type.value}));
 if(item)el.querySelector('[name=type]').disabled=true;
 if(!item&&!types.length){
  const message=document.createElement('p');message.textContent='Enable a system that provides item types to create items.';
  el.querySelector('[data-fields]').append(message);el.querySelector('[type=submit]').disabled=true;
 }
 return el;
}

function itemSheet(item){createItem(item);const sheet=[...document.querySelectorAll('dialog.directory-dialog')].at(-1);if(sheet){sheet.classList.add('item-sheet');sheet.dataset.itemId=item.id;sheet.querySelector('[name=type]').disabled=true;if(!item.canEdit){sheet.querySelector('[name=name]').readOnly=true;sheet.querySelector('[type=submit]').hidden=true;}}}

function render(name){const target=panel(name),state=states[name];if(!target||!state)return;
 if(name==='compendiums'){if(!target._content)target._content=window.gravewrightTableMedia?.mountCompendiums(target.querySelector('[data-entries]'));else target._content.call('load');return;}
 if(name==='combat'){if(target.contains(document.activeElement)&&document.activeElement.matches('[data-combat-initiative]'))return;target.dataset.selectedTokenCount=String(window.gravewrightTokenSelection?.length||0);window.GravewrightCombatPanel?.renderPanel(target,state);if(pending[name])target.querySelectorAll('button,input').forEach(el=>el.disabled=true);return;}
 const list=target.querySelector('[data-entries]'),query=target.querySelector('input[type=search]').value.toLowerCase();list.replaceChildren();
 if(name==='items'){
  if(!(state.items||[]).length){const empty=document.createElement('p');empty.className='item-directory__empty';empty.textContent='No items in this table.';list.append(empty);}
  for(const folder of state.folders||[])if(gm){const row=document.createElement('div');row.className='sheet-folder-header';row.textContent=folder.name;row.append(button('Rename',()=>dialog('Rename folder',[{name:'name',label:'Name',value:folder.name}],form=>command('items','folder-update',{id:folder.id,name:form.elements.name.value,parentId:folder.parentId}))),button('Delete',()=>dialog('Delete folder',[],()=>command('items','folder-delete',{id:folder.id}))));list.append(row);}
  for(const item of state.items||[])if(item.name.toLowerCase().includes(query)){const row=document.createElement('div');row.className='directory-entry item-card';row.dataset.itemId=item.id;row.draggable=true;row.addEventListener('dragstart',event=>{event.dataTransfer.effectAllowed='copy';event.dataTransfer.setData('application/x-gravewright-item',JSON.stringify({id:item.id,tableId:table}));});row.append(button(item.name,()=>itemSheet(item)));if(item.canEdit)row.append(button('Edit',()=>createItem(item)));if(gm){row.append(button('Duplicate',()=>command('items','duplicate',{id:item.id,version:item.version})),button('Permissions',()=>permission(item)),button('Delete',()=>dialog('Delete '+item.name,[],()=>command('items','delete',{id:item.id,version:item.version}))));}list.append(row);}
 }
}

async function permission(item){const r=await fetch(`/api/containers/${table}/permissions-members`),data=await r.json();if(!r.ok)throw Error(data.error);dialog('Item permissions',data.members.map(m=>({name:m.id,label:m.name,value:item.permissions[m.id]||'none',options:['none','read','owner'].map(v=>({value:v,label:v}))})),form=>command('items','permissions',{id:item.id,version:item.version,permissions:Object.fromEntries(data.members.map(m=>[m.id,form.elements[m.id].value]))}));}
async function addEntry(pack){const choices=[];for(const [kind,url,key]of [['actor',`/api/containers/${table}/actors`,'actors'],['item',`/api/containers/${table}/modules-native/items`,'items'],['journal',`/api/containers/${table}/journals`,'journals']]){const r=await fetch(url);if(!r.ok)continue;const data=await r.json();for(const row of data[key]||[])choices.push({value:kind+':'+row.id,label:kind+' · '+(row.name||row.title)});}dialog('Add document',[{name:'entry',label:'Document',options:choices}],form=>{const[kind,id]=form.elements.entry.value.split(':');return command('compendiums','add',{packId:pack.id,kind,resourceId:id});});}
for(const name of modules){const el=panel(name);if(!el)continue;el.querySelector('[data-close]').onclick=()=>{el.hidden=true;};el.querySelector('input[type=search]')?.addEventListener('input',()=>render(name));el.querySelector('[data-create]')?.addEventListener('click',()=>name==='items'?createItem():dialog('Create compendium',[{name:'name',label:'Name'}],form=>command(name,'create',{name:form.elements.name.value})));el.querySelector('[data-folder]')?.addEventListener('click',()=>dialog('Create folder',[{name:'name',label:'Name'}],form=>command('items','folder-create',{name:form.elements.name.value})));}
document.addEventListener('click',e=>{const toggle=e.target.closest('[data-native-directory-toggle]');if(toggle){const name=toggle.dataset.nativeDirectoryToggle==='content'?'compendiums':toggle.dataset.nativeDirectoryToggle;panel(name).hidden=!panel(name).hidden;window.gravewrightRealtime.subscribeModule(name,scene);void refresh(name).catch(e=>notify(name,e));}});
window.addEventListener('gravewright:resources',({detail})=>{if(modules.includes(detail.module)&&(detail.module!=='combat'||(detail.sceneId??null)===(scene??null))){states[detail.module]=detail.state;render(detail.module);}});
window.addEventListener('gravewright:connected',()=>{for(const name of modules)window.gravewrightRealtime.subscribeModule(name,scene);});
window.addEventListener('gravewright:module-scene',()=>{scene=window.gravewrightMaps?.current?.id||null;states.combat={active:false,round:0,turn:0,combatants:[],version:0};render('combat');for(const name of modules)window.gravewrightRealtime?.subscribeModule(name,scene);});
window.addEventListener('gravewright:search-open',({detail})=>{if(detail.type==='item')void refresh('items').then(()=>{const item=states.items.items.find(i=>i.id===detail.id);if(item)itemSheet(item);});if(detail.type==='compendium'){panel('compendiums').hidden=false;void refresh('compendiums');}});
const combat=panel('combat');
combat?.addEventListener('change',e=>{if(e.target.dataset.combatInitiative)void command('combat','initiative',{tokenId:e.target.dataset.combatInitiative,value:states.combat.config?.input==='text'?e.target.value:Number(e.target.value),version:Number(e.target.dataset.combatVersion)}).catch(()=>{});});
combat?.querySelector('[data-initiative-config]')?.addEventListener('submit',e=>{e.preventDefault();void command('combat','configure',{formula:e.target.elements.formula.value,version:states.combat?.version||0}).catch(()=>{});});
combat?.addEventListener('click',async e=>{const b=e.target.closest('[data-combat-action]');if(!b)return;const action=b.dataset.combatAction,tokenId=b.dataset.combatantId;try{
 if(action==='combatants/add-actor'){const r=await fetch(`/api/containers/${table}/actors`);if(!r.ok)throw Error('Unable to load actors.');const data=await r.json();dialog('Add actor',[{name:'actor',label:'Actor',options:data.actors.map(a=>({value:a.id,label:a.name}))}],form=>command('combat','add',{actorId:form.elements.actor.value,version:states.combat?.version||0}));return;}
 if(action==='combatants/add-selected'){for(const id of window.gravewrightTokenSelection||[])await command('combat','add',{tokenId:id,version:states.combat?.version||0});return;}
 if(action==='token/sheet'){const token=(window.gravewrightTokenState?.tokens||[]).find(t=>t.id===b.dataset.tokenId);if(token)window.gravewrightActors.open(token.actorId,token);return;}
 if(action==='token/focus'){window.dispatchEvent(new CustomEvent('gravewright:focus-token',{detail:{id:b.dataset.tokenId}}));return;}
 const actions={end:'stop',start:'start','turn/next':'next','turn/previous':'previous','round/next':'next-round','round/previous':'previous-round','turn/set':'set-turn','order/up':'order-up','order/down':'order-down','combatants/remove':'remove','initiative/roll-all':'roll','initiative/roll-npcs':'roll','initiative/roll-missing':'roll','initiative/roll-one':'roll','flags/hidden':'toggle','flags/defeated':'toggle'};
 await command('combat',actions[action],{tokenId,scope:action.startsWith('initiative/roll-')?action.slice('initiative/roll-'.length):undefined,version:states.combat?.version||0,...action==='flags/hidden'?{hidden:b.dataset.value==='1'}:{},...action==='flags/defeated'?{defeated:b.dataset.value==='1'}:{}});
 }catch(error){notify('combat',error);}});
window.addEventListener('gravewright:token-selection',()=>{if(combat&&!combat.hidden&&!combat.contains(document.activeElement))render('combat');});
window.gravewrightItems={open:async id=>{await refresh('items');const item=states.items.items.find(i=>i.id===id);if(item)itemSheet(item);}};
