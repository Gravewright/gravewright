import { registerEscapeClose } from '/static/gravewright_web/escape.js';
import { mountCommandPalette } from './command-palette.js';

const table = document.querySelector('#table-workspace');
const dock = table?.querySelector('.game-dock');
if (dock) {
  let previousHeight;
  const observer = new ResizeObserver(() => {
    const height = Math.ceil(dock.getBoundingClientRect().height);
    if (height === previousHeight) return;
    previousHeight = height;
    table.style.setProperty('--game-dock-height', `${height}px`);
    window.dispatchEvent(new Event('gravewright:dock-resize'));
  });
  observer.observe(dock);
  window.addEventListener('pagehide', () => observer.disconnect(), { once: true });
}
const palette = document.querySelector('[data-command-palette]');
const lobby = document.querySelector('[data-lobby-panel-window]');
const send = (type, value) => window.gravewrightRealtime?.tableTool(type, value);
mountCommandPalette(palette,table);
const house = document.querySelector('.house-menu');
if (house) {
  house.setAttribute('aria-modal', 'true');
  registerEscapeClose(house, () => document.querySelector('.game-menubar__logo').click());
}
const participants = document.querySelector('.game-roster');
if (participants) registerEscapeClose(participants, () => document.querySelector('.game-menubar__roster > button').click());
function openLobby() {
  if (!lobby) return;
  const rosterToggle = document.querySelector('.game-menubar__roster > button');
  if (rosterToggle?.getAttribute('aria-expanded') === 'true') rosterToggle.click();
  lobby.hidden = false; send('lobby.sync');
}
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
  if(detail.tool.startsWith('lobby.') && lobby){const notice=lobby.querySelector('[data-lobby-notice]');notice.hidden=false;notice.textContent=detail.message;}
});
window.addEventListener('gravewright:connected',()=>{if(lobby&&!lobby.hidden)send('lobby.sync');});

window.addEventListener('gravewright:search-open',({detail})=>{
  if(detail.type==='actor')window.gravewrightActors?.open(detail.id);
  else if(detail.type==='journal')window.gravewrightJournals?.open(detail.id);
  else if(detail.type==='scene')window.dispatchEvent(new CustomEvent('gravewright:open-scene',{detail:{id:detail.id}}));
});
