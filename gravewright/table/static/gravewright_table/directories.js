import { openFormModal, modalText } from './form-modal.js';
import { writeReference } from './references.js';
import { restoreWindow } from './window-controls.js';
import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { executeNative } from '/static/gravewright_modules/domain-api.js';
import { openPermissions } from './permissions.js';
import { initialContent, restoreContent, contentReady } from './content-state.js';
import { mountCompendiums } from './compendiums.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';
const root=document.querySelector('#table-workspace'),table=root?.dataset.tableId,gm=root?.dataset.role==='gm',states={items:initialContent('items')},windows=new Map();let scene=window.gravewrightMaps?.current?.id||null;
const typeTranslator=createTranslator(root?.dataset.systemId||'gravewright');
const modules=['items','combat','compendiums'],pending={};
const itemFolderKey=`gravewright.directory.${table}.items`;
let closedItemFolders=new Set(),itemMenu,itemMenuReturn,itemDirectoryProjection;
try{closedItemFolders=new Set(JSON.parse(localStorage.getItem(itemFolderKey)||'[]'));}catch{}
const panel=name=>document.querySelector(`[data-native-directory="${name}"]`);
function notify(name,error){const node=panel(name)?.querySelector('[data-error]');if(node){node.hidden=!error;node.textContent=error?.message||'';}}
async function refresh(name){const requestedScene=scene;const data=await gravewright[name].state({sceneId:scene});if(name==='combat'&&requestedScene!==scene)return states[name];states[name]=data;render(name);return data;}
async function command(name,action,data){
 if(pending[name])throw Error(modalText('Wait for the current change to finish.','Aguarde a alteração atual terminar.'));
 pending[name]=true;notify(name);
 panel(name)?.querySelectorAll('button,input,select').forEach(el=>el.disabled=true);
 try{const result=await executeNative(gravewright,name,action,{sceneId:scene,...data});await refresh(name);return result;}
 catch(e){notify(name,e);throw e;}
 finally{pending[name]=false;panel(name)?.querySelectorAll('button,input,select').forEach(el=>el.disabled=false);render(name);}
}

function button(text,action){const el=document.createElement('button');el.type='button';el.textContent=text;el.onclick=()=>Promise.resolve().then(action).catch(e=>{const p=el.closest('[role=dialog],aside')?.querySelector('[role=alert]');if(p){p.hidden=false;p.textContent=e.message;}});return el;}
function dialog(title,fields,save,options={}){return openFormModal(title,fields,save,{key:'directory-form:'+fields.map(field=>field.name).join('-'),...options});}

function itemTypeLabel(type){
 const descriptor=states.items?.types?.find(entry=>entry.id===type),label=descriptor?.label||type;
 return descriptor?.labelKey&&typeTranslator.has(descriptor.labelKey)?typeTranslator.t(descriptor.labelKey):label;
}
function alphabeticalEntries(entries,label=entry=>entry.name){
 const collator=new Intl.Collator(typeTranslator.locale||'en',{sensitivity:'base',numeric:true});
 return [...entries].sort((left,right)=>collator.compare(String(label(left)||''),String(label(right)||'')));
}
function createItem(item,folderId=''){
 const types=states.items?.types||[];
 let created;
 const el=dialog(item?item.name:modalText('Create item','Criar item'),[
  {name:'name',label:modalText('Name','Nome'),value:item?.name,required:true},
  {name:'type',label:modalText('Type','Tipo'),value:item?.type||types[0]?.id||'',required:true,options:item?[{value:item.type,label:itemTypeLabel(item.type)}]:alphabeticalEntries(types,entry=>itemTypeLabel(entry.id)).map(t=>({value:t.id,label:itemTypeLabel(t.id)}))}
 ],async form=>{const result=await command('items',item?'update':'create',{id:item?.id,version:item?.version,name:form.elements.name.value,type:form.elements.type.value,...(!item?{folderId}:{})});if(!item)created=result.item||states.items.items.find(entry=>entry.id===result.id);},{key:item?'item:'+item.id:'item:create',...(!item?{submitLabel:modalText('Create item','Criar item')}:{})});
 if(!item)el.addEventListener('close',()=>{if(created)itemSheet(created);},{once:true});
 if(item)el.querySelector('[name=type]').disabled=true;
 if(item)el.setDefaultVisible=visible=>{
  el.querySelector('.table-form-modal__body').hidden=!visible;
  el.querySelector(':scope > form > footer').hidden=!visible;
 };
 if(!item&&!types.length){
  const message=document.createElement('p');message.textContent=modalText('Enable a system that provides item types to create items.','Ative um sistema que forneça tipos de itens para criá-los.');
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

function itemIcon(name){
 const icons=document.getElementById('item-directory-icons')?.content.querySelectorAll('[data-item-icon]')||[];
 const source=[...icons].find(icon=>icon.dataset.itemIcon===name)?.firstElementChild||[...icons].find(icon=>icon.dataset.itemIcon==='item')?.firstElementChild;
 return source?.cloneNode(true)||document.createElement('span');
}
function itemGlyph(type){return states.items?.types?.find(entry=>entry.id===type)?.icon||'item';}
function itemIconButton(label,glyph,action){const el=button('',action);el.title=label;el.setAttribute('aria-label',label);el.append(itemIcon(glyph));return el;}
function dismissItemMenu(restore=false){const target=itemMenuReturn;itemMenu?.remove();itemMenu=undefined;itemMenuReturn=undefined;if(restore&&target?.isConnected)target.focus();}
function showItemMenu(event,entries,returnTo){
 event.preventDefault();event.stopPropagation();dismissItemMenu();
 itemMenuReturn=returnTo;itemMenu=document.createElement('menu');itemMenu.className='directory-context-menu item-directory-menu';itemMenu.setAttribute('role','menu');
 for(const [label,glyph,action,danger]of entries){const choice=itemIconButton(label,glyph,async()=>{dismissItemMenu();try{await action();}catch(error){notify('items',error);}});choice.setAttribute('role','menuitem');choice.append(document.createTextNode(label));choice.classList.toggle('item-directory-menu__danger',!!danger);itemMenu.append(choice);}
 const menu=itemMenu;document.body.append(menu);const box=menu.getBoundingClientRect(),anchor=returnTo?.getBoundingClientRect();
 const x=event.clientX||anchor?.left||0,y=event.clientY||anchor?.bottom||0;
 menu.style.left=Math.max(8,Math.min(x,window.innerWidth-box.width-8))+'px';menu.style.top=Math.max(8,Math.min(y,window.innerHeight-box.height-8))+'px';menu.querySelector('button')?.focus();
}
document.addEventListener('click',()=>dismissItemMenu());
document.addEventListener('keydown',event=>{
 if(!itemMenu)return;
 if(event.key==='Escape'){event.preventDefault();event.stopPropagation();dismissItemMenu(true);return;}
 if(!['ArrowDown','ArrowUp','Home','End'].includes(event.key))return;
 event.preventDefault();const choices=[...itemMenu.querySelectorAll('button')],index=choices.indexOf(document.activeElement);
 choices[event.key==='Home'?0:event.key==='End'?choices.length-1:(index+(event.key==='ArrowDown'?1:-1)+choices.length)%choices.length]?.focus();
});
function confirmItemRemoval(item){const modal=dialog(modalText('Delete item','Excluir item'),[],()=>command('items','delete',{id:item.id,version:item.version}),{key:'item:delete:'+item.id,submitLabel:modalText('Delete','Excluir')});const message=document.createElement('p');message.textContent=modalText('Delete this item?','Excluir este item?')+' '+item.name;modal.querySelector('[data-fields]').append(message);}
function folderChoices(){return [{value:'',label:modalText('No folder','Sem pasta')},...alphabeticalEntries(states.items?.folders||[]).map(folder=>({value:folder.id,label:folder.name}))];}
function moveItem(item){return dialog(modalText('Move to folder','Mover para pasta'),[{name:'folder',label:modalText('Folder','Pasta'),value:item.folderId||'',options:folderChoices()}],form=>command('items','update',{id:item.id,version:item.version,folderId:form.elements.folder.value}),{key:'item:move:'+item.id});}
function itemActions(item){
 const entries=[[modalText(item.canEdit?'Edit':'Open item sheet',item.canEdit?'Editar':'Abrir ficha do item'),'edit',()=>itemSheet(item)]];
 if(gm)entries.push([modalText('Duplicate','Duplicar'),'copy',()=>command('items','duplicate',{id:item.id,version:item.version,name:item.name+' '+modalText('copy','cópia')})],[modalText('Move to folder','Mover para pasta'),'move',()=>moveItem(item)],[modalText('Permissions','Permissões'),'permissions',()=>permission(item)],[modalText('Delete','Excluir'),'delete',()=>confirmItemRemoval(item),true]);
 return entries;
}
function itemFolderForm(parentId='',existing){
 return dialog(modalText(existing?'Edit folder':'Create folder',existing?'Editar pasta':'Criar pasta'),[{name:'name',label:modalText('Name','Nome'),value:existing?.name,required:true},{name:'color',label:modalText('Color','Cor'),value:existing?.color||'#c9a44c',type:'color'}],async form=>{
  await command('items',existing?'folder-update':'folder-create',{id:existing?.id,name:form.elements.name.value,color:form.elements.color.value,parentId:existing?.parentId||parentId});
  if(!existing&&parentId){
   closedItemFolders.delete(parentId);
   try{localStorage.setItem(itemFolderKey,JSON.stringify([...closedItemFolders]));}catch{}
   render('items');
  }
 },{key:existing?'item:folder:'+existing.id:'item:folder-create'});
}
function itemFolderActions(folder){return [
 [modalText('Create item','Criar item'),'create',()=>createItem(undefined,folder.id)],
 [modalText('Create subfolder','Criar subpasta'),'folder-create',()=>itemFolderForm(folder.id)],
 [modalText('Edit folder','Editar pasta'),'edit',()=>itemFolderForm('',folder)],
 [modalText('Permissions','Permissões'),'permissions',()=>openPermissions('item-folders',folder.id,{onSave:()=>refresh('items')})],
 [modalText('Delete folder','Excluir pasta'),'delete',()=>{const modal=dialog(modalText('Delete folder','Excluir pasta'),[],()=>command('items','folder-delete',{id:folder.id}),{key:'item:folder-delete:'+folder.id,submitLabel:modalText('Delete','Excluir')});const message=document.createElement('p');message.textContent=modalText('Delete this folder? Its items and subfolders will move to the directory.','Excluir esta pasta? Seus itens e subpastas serão movidos para o diretório.');modal.querySelector('[data-fields]').append(message);},true],
 ];}
function localizeItems(){
 const target=panel('items');if(!target)return;
 const heading=target.querySelector('.game-panel__title');heading?.replaceChildren(itemIcon('item'),document.createTextNode(modalText('Items','Itens')));
 const close=target.querySelector('[data-close]');close?.setAttribute('aria-label',modalText('Close','Fechar'));
 for(const [attribute,label,pt,glyph]of [['data-create','Create item','Criar item','create'],['data-folder','Create folder','Criar pasta','folder-create']])target.querySelector('['+attribute+']')?.replaceChildren(itemIcon(glyph),document.createTextNode(modalText(label,pt)));
 const search=target.querySelector('input[type=search]');if(search){search.placeholder=modalText('Search items','Pesquisar itens');search.setAttribute('aria-label',modalText('Search items','Pesquisar itens'));}
}
function localizeDirectoryTitles(){
 localizeItems();
 for(const [name,en,pt]of [['compendiums','Compendiums','Compêndios'],['combat','Combat','Combate']]){
  const target=panel(name),heading=target?.querySelector('.game-panel__title');
  if(heading)heading.replaceChildren(...heading.children,document.createTextNode(modalText(en,pt)));
  target?.querySelector('[data-close]')?.setAttribute('aria-label',modalText('Close','Fechar'));
 }
}
function renderItems(target,state,list,query){
 const byId=(rows,fields)=>rows.map(fields).sort((left,right)=>left[0].localeCompare(right[0]));
 const projection=JSON.stringify([query,typeTranslator.locale,!!pending.items,
  byId(state.types||[],type=>[type.id,type.icon,itemTypeLabel(type.id)]),
  byId(state.folders||[],folder=>[folder.id,folder.name,folder.parentId,folder.color]),
  byId(state.items||[],item=>[item.id,item.version,item.name,item.type,item.folderId,item.canOpen,item.canEdit])]);
 // Repeated realtime projections must not interrupt an open action menu.
 if(itemMenu&&projection===itemDirectoryProjection)return;
 itemDirectoryProjection=projection;
 dismissItemMenu();list.replaceChildren();localizeItems();
 const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();query=normalize(query);
 const folders=alphabeticalEntries(state.folders||[]),folderMap=new Map(folders.map(folder=>[folder.id,folder])),items=alphabeticalEntries((state.items||[]).filter(item=>normalize(item.name+' '+itemTypeLabel(item.type)).includes(query)));
 const visible=new Set(items.map(item=>item.folderId));
 for(const id of [...visible]){let cursor=folderMap.get(id),seen=new Set();while(cursor?.parentId&&!seen.has(cursor.id)){seen.add(cursor.id);visible.add(cursor.parentId);cursor=folderMap.get(cursor.parentId);}}
 const addItem=(host,item)=>{
  const row=document.createElement('article');row.className='directory-entry item-card item-directory__entry';row.dataset.itemId=item.id;row.draggable=item.canOpen!==false;
  row.addEventListener('dragstart',event=>{if(item.canOpen===false){event.preventDefault();return;}event.dataTransfer.effectAllowed='copy';writeReference(event.dataTransfer,{type:'item',id:item.id,title:item.name});event.dataTransfer.setData('application/x-gravewright-item',JSON.stringify({id:item.id,tableId:table}));});
  const open=button('',()=>itemSheet(item));open.className='item-directory__open';open.disabled=item.canOpen===false;open.append(itemIcon(itemGlyph(item.type)));
  const info=document.createElement('span');info.className='item-directory__info';const name=document.createElement('strong'),type=document.createElement('small');name.textContent=item.name;name.title=item.name;type.textContent=itemTypeLabel(item.type);type.title=type.textContent;info.append(name,type);open.append(info);row.append(open);
  if(item.canOpen!==false){const more=itemIconButton(modalText('Actions','Ações'),'more',()=>{});more.className='item-directory__more';more.setAttribute('aria-haspopup','menu');more.onclick=event=>showItemMenu(event,itemActions(item),more);row.append(more);row.addEventListener('contextmenu',event=>showItemMenu(event,itemActions(item),more));}
  host.append(row);
 };
 const build=(host,parent='',ancestors=new Set())=>{
  host.dataset.itemFolderId=parent;
  for(const folder of folders.filter(folder=>(folderMap.has(folder.parentId)?folder.parentId:'')===parent&&(!query||visible.has(folder.id)))){
   if(ancestors.has(folder.id))continue;
   const section=document.createElement('section');section.className='item-directory__folder';section.style.setProperty('--folder-color',folder.color);section.dataset.itemFolderId=folder.id;
   const header=document.createElement('header'),toggle=button('',()=>{});header.className='item-directory__folder-header';toggle.className='item-directory__folder-toggle';toggle.append(itemIcon('folder'));
   const title=document.createElement('span');title.className='item-directory__folder-name';title.textContent=folder.name;const count=document.createElement('small');count.textContent=String(items.filter(item=>item.folderId===folder.id).length);const caret=itemIcon('caret');caret.classList.add('item-directory__caret');toggle.append(title,count,caret);header.append(toggle);
   const content=document.createElement('div');content.className='item-directory__folder-content';content.hidden=!query&&closedItemFolders.has(folder.id);toggle.setAttribute('aria-expanded',String(!content.hidden));toggle.onclick=()=>{content.hidden=!content.hidden;toggle.setAttribute('aria-expanded',String(!content.hidden));content.hidden?closedItemFolders.add(folder.id):closedItemFolders.delete(folder.id);try{localStorage.setItem(itemFolderKey,JSON.stringify([...closedItemFolders]));}catch{}};
   if(gm){const more=itemIconButton(modalText('Actions','Ações'),'more',()=>{});more.className='item-directory__more';more.setAttribute('aria-haspopup','menu');more.onclick=event=>showItemMenu(event,itemFolderActions(folder),more);header.append(more);header.addEventListener('contextmenu',event=>showItemMenu(event,itemFolderActions(folder),more));}
   build(content,folder.id,new Set([...ancestors,folder.id]));section.append(header,content);host.append(section);
  }
  for(const item of items.filter(item=>(folderMap.has(item.folderId)?item.folderId:'')===parent))addItem(host,item);
 };
 build(list);
 if(!items.length&&(!folders.length||query)){const empty=document.createElement('div');empty.className='item-directory__empty';empty.append(itemIcon(query?'search':'item'));const text=document.createElement('p');text.textContent=query?modalText('No results found.','Nenhum resultado encontrado.'):modalText('No items in this table.','Nenhum item nesta mesa.');empty.append(text);list.append(empty);}
 if(pending.items)target.querySelectorAll('button,input,select').forEach(control=>control.disabled=true);
}


function render(name){if(name==='compendiums'){const show=gm||!!states.compendiums?.packs?.length,toggle=document.querySelector('[data-native-directory-toggle="content"]');if(toggle)toggle.hidden=!show;if(!show&&panel(name))panel(name).hidden=true;}if(name==='combat'&&states.combat){window.gravewrightCombatState={...states.combat,sceneId:scene};window.dispatchEvent(new CustomEvent('gravewright:combat-state',{detail:window.gravewrightCombatState}));}if(name==='items'&&!contentReady()){restoreContent('items',()=>render(name));return;}const target=panel(name),state=states[name];if(!target||!state)return;
 if(name==='compendiums'){if(!target._content)target._content=mountCompendiums(target.querySelector('[data-entries]'),state);else target._content.update(state);return;}
 if(name==='combat'){if(target.contains(document.activeElement)&&document.activeElement.matches('[data-combat-initiative]'))return;target.dataset.selectedTokenCount=String(window.gravewrightTokenSelection?.length||0);window.GravewrightCombatPanel?.renderPanel(target,state);if(pending[name])target.querySelectorAll('button,input').forEach(el=>el.disabled=true);return;}
 const list=target.querySelector('[data-entries]'),query=target.querySelector('input[type=search]').value.toLowerCase();
 if(name==='items'){
  for(const sheet of document.querySelectorAll('.item-sheet[role=dialog]')){const current=state.items.find(item=>item.id===sheet.dataset.itemId);if(!current||current.canOpen===false)sheet.close(true);else if(!current.canEdit){sheet.querySelector('[name=name]').readOnly=true;sheet.querySelector('[type=submit]').hidden=true;}}
  renderItems(target,state,list,query);
 }
}

async function permission(item){return openPermissions('items',item.id,{onSave:()=>refresh('items')});}
async function addEntry(pack){const choices=[];for(const [kind,url,key]of [['actor',`/api/containers/${table}/actors`,'actors'],['item',`/api/containers/${table}/modules-native/items`,'items'],['journal',`/api/containers/${table}/journals`,'journals']]){const r=await fetch(url);if(!r.ok)continue;const data=await r.json();for(const row of data[key]||[])choices.push({value:kind+':'+row.id,label:kind+' · '+(row.name||row.title)});}dialog('Add document',[{name:'entry',label:'Document',options:choices}],form=>{const[kind,id]=form.elements.entry.value.split(':');return command('compendiums','add',{packId:pack.id,kind,resourceId:id});});}
for(const name of modules){const el=panel(name);if(!el)continue;el.querySelector('[data-close]').onclick=()=>{dismissItemMenu();el.hidden=true;};el.querySelector('input[type=search]')?.addEventListener('input',()=>render(name));el.querySelector('[data-create]')?.addEventListener('click',()=>name==='items'?createItem():dialog('Create compendium',[{name:'name',label:'Name'}],form=>command(name,'create',{name:form.elements.name.value})));el.querySelector('[data-folder]')?.addEventListener('click',()=>itemFolderForm());}
localizeDirectoryTitles();
window.addEventListener('gravewright:locale',()=>localizeDirectoryTitles());
typeTranslator.onChange(()=>{
 render('items');
 for(const modal of document.querySelectorAll('.item-sheet,.table-form-modal[data-window-key="item:create"]')){
  const select=modal.querySelector('[name=type]');if(!select)continue;
  const value=select.value;for(const option of select.options)option.textContent=itemTypeLabel(option.value);
  select.replaceChildren(...alphabeticalEntries(select.options,option=>option.textContent));select.value=value;
 }
});
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
