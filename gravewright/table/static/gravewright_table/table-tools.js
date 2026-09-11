const table = document.querySelector('#table-workspace');
const palette = document.querySelector('[data-command-palette]');
const lobby = document.querySelector('[data-lobby-panel-window]');
const send = (type, value) => window.gravewrightRealtime?.tableTool(type, value);
let selected = 0, results = [], timer, searchId, previousFocus;
const input = palette?.querySelector('input');
const status = palette?.querySelector('[data-command-palette-status]');
const list = palette?.querySelector('[data-command-palette-results]');
function closePalette() { if (!palette) return; palette.hidden = true; previousFocus?.focus(); }
function choose(index) {
  selected = index;
  for (const [i, el] of [...list.children].entries()) el.setAttribute('aria-selected', String(i === selected));
  input.setAttribute('aria-activedescendant', list.children[selected]?.id || '');
}
function openResult(result) {
  closePalette();
  window.dispatchEvent(new CustomEvent('gravewright:search-open', {detail:result}));
}
input?.addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    searchId = crypto.randomUUID();
    status.textContent = 'Searching…';
    if (!send('table.search', {query:input.value, requestId:searchId})) status.textContent = 'Connect to the table to search.';
  }, 180);
});
window.addEventListener('gravewright:table.search', ({detail}) => {
  if (detail.requestId !== searchId) return;
  results = detail.results; list.replaceChildren();
  for (const [i, result] of results.entries()) {
    const button = document.createElement('button'); button.type = 'button';
    button.className = 'command-palette-result'; button.id = 'search-result-'+i; button.role = 'option';
    const title = document.createElement('strong'), subtitle = document.createElement('small');
    title.textContent = result.title; subtitle.textContent = result.type;
    button.append(title, subtitle); button.onclick = () => openResult(result); list.append(button);
  }
  status.textContent = results.length ? '' : 'No results.'; choose(0);
});
palette?.addEventListener('pointerdown', e => { if (e.target === palette) closePalette(); });
window.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && palette) {
    e.preventDefault(); previousFocus = document.activeElement; palette.hidden = false; input.focus(); return;
  }
  if (palette && !palette.hidden) {
    if (e.key === 'Escape') {e.preventDefault();closePalette();}
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {e.preventDefault();if(results.length)choose((selected+(e.key==='ArrowDown'?1:-1)+results.length)%results.length);}
    else if (e.key === 'Enter' && results[selected]) {e.preventDefault();openResult(results[selected]);}
    else if (e.key === 'Tab') {e.preventDefault();input.focus();}
  }
});
function openLobby() { if (lobby) {lobby.hidden = false;send('lobby.sync');} }
window.addEventListener('gravewright:lobby-open', openLobby);
// The original readiness panel is reached from the participants menu.
const roster = document.querySelector('[data-roster]') || document.querySelector('.game-roster');
if (lobby) {
  const button = document.createElement('button');button.type='button';button.textContent='Ready check';button.className='game-modal-control';button.onclick=openLobby;
  (roster || document.querySelector('.house-menu__facts'))?.append(button);
  lobby.querySelector('[data-modal-close]').onclick=()=>{lobby.hidden=true;};
  lobby.querySelector('form').onsubmit=e=>{
    e.preventDefault();const form=e.currentTarget;
    send('lobby.update',{is_ready:form.elements.is_ready.checked, selected_actor_id:form.elements.selected_actor_id.value||null, assets_state:'unknown'});
  };
  window.addEventListener('gravewright:lobby.state', ({detail})=>{
    const form=lobby.querySelector('form'), select=form.elements.selected_actor_id, value=select.value;
    select.replaceChildren(new Option('No character',''));
    for(const actor of detail.actors) select.add(new Option(actor.name,actor.id));
    const own=detail.members.find(m=>m.user_id===table.dataset.profileId);
    select.value=own?.selected_actor_id||value;form.elements.is_ready.checked=own?.is_ready||false;
    lobby.querySelector('[data-lobby-summary]').textContent=`${detail.summary.ready} / ${detail.summary.total}`;
    const rows=lobby.querySelector('[data-lobby-members]');rows.replaceChildren();
    for(const member of detail.members){const row=document.createElement('p');row.className='player-card';row.textContent=`${member.name} · ${member.is_online?'Online':'Offline'} · ${member.is_ready?'Ready':'Not ready'}${member.selected_actor_name?' · '+member.selected_actor_name:''}`;rows.append(row);}
    lobby.querySelector('[data-lobby-notice]').hidden=true;
  });
}
window.addEventListener('gravewright:table.tool_error', ({detail})=>{
  if(detail.tool==='table.search' && detail.requestId===searchId)status.textContent=detail.message;
  else if(detail.tool.startsWith('lobby.') && lobby){const notice=lobby.querySelector('[data-lobby-notice]');notice.hidden=false;notice.textContent=detail.message;}
});
window.addEventListener('gravewright:connected',()=>{if(lobby&&!lobby.hidden)send('lobby.sync');});

window.addEventListener('gravewright:search-open',({detail})=>{
  if(detail.type==='actor')window.gravewrightActors?.open(detail.id);
  else if(detail.type==='journal')window.gravewrightJournals?.open(detail.id);
  else if(detail.type==='scene')window.dispatchEvent(new CustomEvent('gravewright:open-scene',{detail:{id:detail.id}}));
});
