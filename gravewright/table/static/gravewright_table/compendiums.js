import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { mountModal } from './modal.js';
import { modalText } from './form-modal.js';
import { openPermissions } from './permissions.js';

const mime = 'application/x-gravewright-compendium';
const targets = {actor:'#actors-panel',item:'#items-panel',journal:'#journals-panel',scene:'#maps-panel',deck:'.deck-upload'};
const text = (en,pt) => window.gravewrightLocale?.messages?.text?.[en] || modalText(en,pt);
const nameOf = kind => ({actor:text('Characters','Personagens'),item:text('Items','Itens'),journal:text('Journals','Diários'),scene:text('Scenes','Cenas'),deck:text('Decks','Baralhos')})[kind] || kind;
const node = (tag,cls,value) => {const el=document.createElement(tag);el.className=cls||'';if(value!=null)el.textContent=value;return el;};
const normalized = value => String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function plain(value, budget={remaining:12000}) {
  if(budget.remaining<=0||!value)return '';
  if(typeof value==='string'){const result=value.slice(0,budget.remaining);budget.remaining-=result.length;return result;}
  if(Array.isArray(value))return value.map(item=>plain(item,budget)).filter(Boolean).join('\n');
  if(typeof value==='object')return plain(value.text||value.doc||value.content||'',budget);
  return '';
}
function description(entry) {
  const data=entry.data?.data||entry.data||{};
  return [data.description,data.bio,data.notes,data.summary,data.sections?.map(section=>({content:section.content})),entry.content_markdown,entry.content]
    .map(value=>plain(value)).filter(Boolean).join('\n\n').slice(0,12000);
}

export function mountCompendiums(root, initial) {
  const campaign=document.getElementById('table-workspace').dataset.tableId;
  const gm=document.getElementById('table-workspace').dataset.role==='gm';
  let state=initial, query='', kind='', source='', busy=new Set(), dragged, highlighted;
  const opened=new Set(), container=node('section','gw-compendiums');
  const filters=node('div','gw-compendiums__filters'),search=node('input'),type=node('select'),pack=node('select');
  search.type='search';search.placeholder=text('Search compendiums','Pesquisar compêndios');search.setAttribute('aria-label',search.placeholder);
  type.setAttribute('aria-label',text('Content type','Tipo de conteúdo'));pack.setAttribute('aria-label',text('Compendium','Compêndio'));
  type.add(new Option(text('All types','Todos os tipos'),''));
  for(const value of Object.keys(targets))type.add(new Option(nameOf(value),value));
  const error=node('p','gw-compendiums__error');error.setAttribute('role','alert');error.hidden=true;
  const list=node('div','gw-compendiums__list');filters.append(type,pack);container.append(search,filters,error,list);root.replaceChildren(container);
  function fail(cause){error.textContent=cause.message;error.hidden=false;}
  function button(label,action){const b=node('button','',label);b.type='button';b.onclick=()=>Promise.resolve().then(action).catch(fail);return b;}
  async function importEntry(packId,id){
    const key=packId+':'+id;if(!gm||busy.has(key))return;
    busy.add(key);error.hidden=true;paint();
    try{return await gravewright.compendiums.import({packId,id});}
    finally{busy.delete(key);paint();}
  }
  async function preview(p,e){
    const modal=node('section','table-modal-window gw-compendium-preview');modal.dataset.movable='';
    const header=node('header');header.dataset.moveHandle='';const title=node('strong','',e.name);title.id='compendium-preview-'+crypto.randomUUID();modal.setAttribute('aria-labelledby',title.id);
    const close=button('×',()=>modal.close());close.dataset.close='';close.setAttribute('aria-label',text('Close','Fechar'));header.append(title,close);
    const body=node('div','table-modal-body');body.append(node('p','gw-compendium-preview__type',nameOf(e.kind)),node('p','',text('Loading…','Carregando…')));
    modal.append(header,body);mountModal(modal);
    try{
      const value=await gravewright.compendiums.read({packId:p.id,id:e.id});if(!modal.isConnected)return;
      body.replaceChildren(node('p','gw-compendium-preview__type',nameOf(e.kind)),node('div','gw-compendium-preview__text',description(value)||text('No description.','Sem descrição.')));
      if(gm){const footer=node('footer');const add=button(text('Import','Importar'),async()=>{add.disabled=true;try{await importEntry(p.id,e.id);modal.close();}catch(cause){add.disabled=false;const alert=node('p','',cause.message);alert.setAttribute('role','alert');body.append(alert);}});footer.append(add);modal.append(footer);}
    }catch(cause){if(modal.isConnected){body.replaceChildren(node('p','',cause.message));body.firstChild.setAttribute('role','alert');}}
  }
  function paint(){
    list.replaceChildren();let matches=0;
    for(const p of state?.packs||[]){
      if(source&&source!==p.id)continue;
      const entries=p.entries.filter(e=>(!kind||e.kind===kind)&&(!query||normalized(e.name+' '+p.name).includes(normalized(query))));
      if(!entries.length)continue;matches+=entries.length;
      const group=node('details','gw-compendiums__pack');group.open=!!query||!!kind||!!source||opened.has(p.id);
      group.ontoggle=()=>{if(group.open)opened.add(p.id);else opened.delete(p.id);};
      const heading=node('summary','',p.name);heading.append(node('small','',entries.length));group.append(heading);
      if(gm)group.append(button(text('Permissions','Permissões'),()=>openPermissions('compendiums',p.id)));
      for(const e of entries){
        const row=node('div','gw-compendiums__entry');row.dataset.compendiumEntry=e.id;row.draggable=gm&&!busy.has(p.id+':'+e.id);
        row.ondragstart=event=>{if(!row.draggable){event.preventDefault();return;}dragged={campaign,packId:p.id,id:e.id,kind:e.kind};event.dataTransfer.setData(mime,JSON.stringify(dragged));event.dataTransfer.effectAllowed='copy';};
        row.ondragend=clearDrag;
        const label=button(e.name,()=>preview(p,e));label.className='gw-compendiums__name';label.title=text('Preview','Prévia');
        row.append(label,node('small','',nameOf(e.kind)));
        if(gm){const add=button(text('Import','Importar'),()=>importEntry(p.id,e.id));add.disabled=busy.has(p.id+':'+e.id);add.setAttribute('aria-label',text('Import','Importar')+' '+e.name);row.append(add);}
        group.append(row);
      }
      list.append(group);
    }
    if(!matches)list.append(node('p','gw-compendiums__empty',text('No matching content.','Nenhum conteúdo encontrado.')));
  }
  function update(next){state=next;const previous=pack.value;pack.replaceChildren(new Option(text('All compendiums','Todos os compêndios'),''));for(const p of state?.packs||[])pack.add(new Option(p.name,p.id));pack.value=previous;source=pack.value;paint();}
  search.oninput=()=>{query=search.value;paint();};type.onchange=()=>{kind=type.value;paint();};pack.onchange=()=>{source=pack.value;paint();};
  function clearDrag(){highlighted?.classList.remove('gw-compendium-drop');highlighted=undefined;dragged=undefined;}
  function destination(event,data){return data?.campaign===campaign&&targets[data.kind]?event.target.closest(targets[data.kind]):null;}
  document.addEventListener('dragover',event=>{
    if(!gm||!event.dataTransfer.types.includes(mime))return;
    const target=destination(event,dragged);highlighted?.classList.remove('gw-compendium-drop');highlighted=target;
    if(target){event.preventDefault();event.stopPropagation();event.dataTransfer.dropEffect='copy';target.classList.add('gw-compendium-drop');}
  },true);
  document.addEventListener('drop',event=>{
    if(!gm||!event.dataTransfer.types.includes(mime))return;
    let data;try{data=JSON.parse(event.dataTransfer.getData(mime));}catch{clearDrag();return;}
    const target=destination(event,data);clearDrag();if(!target)return;
    event.preventDefault();event.stopPropagation();
    const p=state?.packs.find(p=>p.id===data.packId),e=p?.entries.find(e=>e.id===data.id&&e.kind===data.kind);
    if(e)void importEntry(p.id,e.id).catch(fail);
  },true);
  update(initial);
  return {update};
}
