import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { registerEscapeClose } from '/static/gravewright_web/escape.js';
import { modalText } from './form-modal.js';

const text=(en,pt)=>window.gravewrightLocale?.messages?.text?.[en]||modalText(en,pt);
export function mountCommandPalette(palette, table) {
  if(!palette)return;
  const input=palette.querySelector('input'),status=palette.querySelector('[data-command-palette-status]'),list=palette.querySelector('[data-command-palette-results]');
  const key=`gravewright.search.recent.${table.dataset.profileId}.${table.dataset.tableId}`;
  let results=[],selected=0,revision=0,timer,previousFocus,busy=false;
  const categories=[['',text('All','Todos')],['actor',text('Characters','Personagens')],['item',text('Items','Itens')],['journal',text('Journals','Diários')],['quest',text('Quests','Missões')],['quest_board',text('Quest boards','Quadros de missões')],['scene',text('Scenes','Cenas')],['compendium',text('Compendiums','Compêndios')]];
  const filter=document.createElement('select');filter.className='command-palette-filter';filter.setAttribute('aria-label',text('Content type','Tipo de conteúdo'));
  for(const [value,label] of categories)filter.add(new Option(label,value));input.closest('label').after(filter);
  function recent(){try{const value=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(value)?value.filter(v=>v&&['actor','item','journal','scene','compendium'].includes(v.type)&&typeof v.id==='string'&&/^(?:native:)?[0-9a-f-]{36}$/i.test(v.id)).slice(0,12):[];}catch{return [];}}
  function store(refs){try{localStorage.setItem(key,JSON.stringify(refs.map(({id,type})=>({id,type}))));}catch{}}
  function remember(result){store([result,...recent().filter(r=>r.id!==result.id||r.type!==result.type)].slice(0,12));}
  function close(){palette.hidden=true;revision++;clearTimeout(timer);previousFocus?.focus();}
  function show(){previousFocus=document.activeElement;palette.hidden=false;input.focus();void search();}
  document.querySelector('[data-open-command-palette]')?.addEventListener('click',show);
  registerEscapeClose(palette.querySelector('[role=dialog]'),close);
  function choose(index){selected=index;for(const[i,row]of [...list.children].entries()){row.setAttribute('aria-selected',String(i===index));row.classList.toggle('is-selected',i===index);}input.setAttribute('aria-activedescendant',list.children[index]?.id||'');list.children[index]?.scrollIntoView({block:'nearest'});}
  async function open(result,action='open'){
    if(busy)return;busy=true;status.textContent='';const request=revision;
    try{
      const [current]=await gravewright.table.search('',{recent:[{id:result.id,type:result.type}]});
      if(palette.hidden||request!==revision)return;
      if(!current||!current.actions.includes(action)){store(recent().filter(r=>r.id!==result.id||r.type!==result.type));await search();return;}
      if(action==='activate')await gravewright.maps.activate({mapId:current.id});
      remember(current);close();
      if(action==='open')window.dispatchEvent(new CustomEvent('gravewright:search-open',{detail:current}));
    }catch(error){status.textContent=error.message;}finally{busy=false;}
  }
  function render(){
    list.replaceChildren();
    for(const[i,result]of results.entries()){
      const row=document.createElement('div');row.className='command-palette-result';row.id='search-result-'+i;row.setAttribute('role','option');
      const main=document.createElement('button');main.type='button';main.className='command-palette-result-main';main.onclick=()=>void open(result);
      const copy=document.createElement('span');copy.className='command-palette-result-copy';
      const title=document.createElement('strong'),category=document.createElement('small');title.textContent=result.title;category.textContent=categories.find(([value])=>value===(result.kind||result.type))?.[1]||result.type;
      copy.append(title,category);
      if(result.snippet){const snippet=document.createElement('span');snippet.className='command-palette-snippet';snippet.textContent=result.snippet;copy.append(snippet);}
      main.append(copy);row.append(main);
      if(result.actions?.includes('activate')){const action=document.createElement('button');action.type='button';action.className='command-palette-action';action.textContent=text('Activate','Ativar');action.setAttribute('aria-label',text('Activate for players','Ativar para jogadores')+': '+result.title);action.onclick=()=>void open(result,'activate');row.append(action);}
      list.append(row);
    }
    choose(0);
  }
  async function search(){
    const id=++revision,query=input.value.trim(),refs=recent();results=[];list.replaceChildren();input.removeAttribute('aria-activedescendant');
    status.textContent=text('Searching…','Pesquisando…');
    try{
      // Recent titles and excerpts are always obtained from the current server projection.
      const data=await gravewright.table.search(query,{kind:filter.value,...(query.length<2?{recent:refs}: {})});
      if(id!==revision||palette.hidden)return;
      if(query.length<2){
        if(!filter.value)store(data);
        status.textContent=data.length?text('Recent','Recentes'):text('No recent content.','Nenhum conteúdo recente.');
      }else status.textContent=data.length?'':text('No results.','Nenhum resultado.');
      results=data;render();
    }catch(error){if(id===revision)status.textContent=error.message;}
  }
  function schedule(){revision++;results=[];list.replaceChildren();clearTimeout(timer);timer=setTimeout(()=>void search(),180);}
  input.addEventListener('input',schedule);filter.onchange=()=>void search();
  palette.addEventListener('pointerdown',event=>{if(event.target===palette)close();});
  window.addEventListener('keydown',event=>{
    if(palette.hidden)return;
    if(event.key==='Escape'){event.preventDefault();close();}
    else if(event.target===input&&['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();if(results.length)choose((selected+(event.key==='ArrowDown'?1:-1)+results.length)%results.length);}
    else if(event.target===input&&event.key==='Enter'&&results[selected]){event.preventDefault();void open(results[selected]);}
    else if(event.key==='Tab'){
      const controls=[...palette.querySelectorAll('input,select,button')].filter(el=>!el.disabled),first=controls[0],last=controls.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  });
  for(const name of ['gravewright:actors.state','gravewright:journals','gravewright:maps','gravewright:resources'])window.addEventListener(name,()=>{results=[];list.replaceChildren();if(!palette.hidden)schedule();});
}
