import ContentDirectory from '../features/table-library/ui/ContentDirectory.native.js';
import DeckUpload from '../features/table-library/ui/DeckUpload.native.js';
import IndividualAudio from '../features/audio/ui/IndividualAudioControl.native.js';
import CardHand from '../features/cards/ui/CardHand.native.js';
import CardPlacement from '../features/cards/ui/CardPlacement.native.js';
import SceneCards from '../features/cards/ui/SceneCardWorkspace.native.js';
import AudioWorkspace from '../features/audio/ui/AudioWorkspace.native.js';
import {getPath,mergePatch} from '/static/gravewright_web/vendor/datastar-1.0.3.js';
import {gravewright} from '/static/gravewright_modules/frontend-api.js';
import {executeNative} from '/static/gravewright_modules/domain-api.js';
const root=document.querySelector('#table-workspace'), campaign=root?.dataset.tableId;
const states={},widgets={},nodes={},media=new Map();let scene=null,revision=0,muted=false,master=.7,unlocked=false,placement,clockOffset=0;
let channels={music:1,ambience:1,sfx:1,cinematic:1};
const map=()=>window.gravewrightMaps?.current;
const rt=()=>window.gravewrightRealtime;
const who=()=>root?.dataset.role==='gm';
const previewToken=()=>who()&&window.gravewrightTokenSelection?.length===1?window.gravewrightTokenSelection[0]:null;
async function fresh(module){const requestedScene=scene;const v=await gravewright[module].state({sceneId:scene,previewTokenId:module==='audio'?previewToken():null});if(['cards','audio'].includes(module)&&requestedScene!==scene)return v;states[module]=v;if(module==='audio'&&v.serverTime)clockOffset=v.serverTime-Date.now()/1000;return v;}
async function command(module,action,data={}){return executeNative(gravewright,module,action,{sceneId:scene,...data});}
function cardById(id){return [...(states.cards?.hand||[]),...(states.cards?.cards||[])].find(c=>c.id===id);}
async function cardCommand(action,data){
 const row=cardById(data.id||data.card_id||data.placement_id);const deck=states.cards?.decks?.find(d=>d.id===data.deck_instance_id);
 const mapped={...data,id:row?.id||data.id||data.card_id||data.placement_id,version:data.expected_version??data.version??row?.version??deck?.version,sceneId:scene};
 if(action==='delete')action=data.deck_instance_id?'delete-deck':'discard';
 if(action==='play')action='place';
 if(action==='update'){if(data.face_state!==undefined)action='flip';else action='move';}
 if(action==='draw')mapped.face_state=data.reveal===false?'face_down':'face_up';
 const result=await command('cards',action,mapped);await fresh('cards');revision++;refresh();return result;
}
function soundLibrary(){const tracks=states.audio?.tracks||[];return {sounds:tracks.map(t=>({id:t.id,name:t.name,kind:t.kind==='effect'?'sound-effect':t.kind,asset_id:t.id})),assets:tracks.map(t=>({id:t.id,name:t.name,filename:t.name,src:t.src,content_type:'audio/mpeg'}))};}
class Client {
 constructor(_base,signal=()=>undefined){this.signal=signal;}
 async get(url){
  if(url.startsWith('/game/content/')){
   const state=await fresh('compendiums'),path=url.split('?')[0].split('/').map(decodeURIComponent);
   if(path[3]==='active-packages')return {packages:state.packs.map(p=>({id:p.id,name:p.name}))};
   const pack=state.packs.find(p=>p.id===path[4]);if(!pack)throw Error('Compendium not found.');
   if(path[3]==='packs')return {packs:[...new Set(pack.entries.map(e=>e.kind))].map(kind=>({id:kind,name:kind,type:kind==='item'?'item_pack':kind+'_pack'}))};
   return {entries:pack.entries.filter(e=>e.kind===path[5])};
  }
  if(url.endsWith('/card-state'))return fresh('cards');
  const state=await fresh('audio');
  if(url.endsWith('/soundtracks'))return {playlists:state.playlists.filter(p=>p.kind==='playlist').map(p=>({...p,entries:p.tracks})),presets:state.playlists.filter(p=>p.kind==='preset').map(p=>({...p,layers:p.tracks}))};
  if(url.endsWith('/soundtrack'))return state.score;
  if(url.endsWith('/library'))return soundLibrary();
  throw Error('Unknown resource.');
 }
 async post(url,data){
  if(url.endsWith('/content/import'))return command('compendiums','import',{packId:data.package_id,id:data.entry_id});
  if(url.includes('/cards/'))return cardCommand(url.split('/').at(-1),data);
  if(url.endsWith('/soundtracks')){const result=await command('audio','playlist-create',{name:data.name,tracks:data.entries,kind:data.kind,mode:data.mode,fade:data.fade});await fresh('audio');return result;}
  if(url.includes('/soundtrack/')){const result=await command('audio','score-'+url.split('/').at(-1),data);await fresh('audio');return result;}
  if(url.endsWith('/sounds/create')){const row=states.audio.tracks.find(t=>t.id===data.assetId);return command('audio','track-update',{id:row.id,version:row.version,kind:data.kind==='sound-effect'?'effect':data.kind,name:data.name});}
  throw Error('Unknown command.');
 }
 async upload(url,body,progress){
  const endpoint=url.endsWith('/card-upload')?'card-asset':'audio';
  const {token,header}=await (await fetch('/__gravewright/csrf')).json();
  const r=await fetch(`/api/containers/${campaign}/media/${endpoint}`,{method:'POST',body,signal:this.signal(),headers:{[header||'x-csrf-token']:token}});const value=await r.json();if(!r.ok)throw Error(value.error);progress?.(100);return value;
 }
}
async function areaCommand(area,action,data={}){
 if(area==='cards')return cardCommand(action,data);
 if(area==='spatial-sounds'){
  const values=data.patch||data,id=data.rid||data.id,row=states.audio.spatialSounds.find(s=>s.id===id),m=map(),factor=(m?.gridSize||70)*(m?.imageScale||1)/(m?.measureValue||1);
  const patch={...values,id,version:data.expected_version??row?.version,trackId:values.soundId||row?.trackId,occlusion:values.constrainedByWalls??row?.occlusion};
  if(values.radius!==undefined)patch.radius=values.radius/factor;
  const result=await command('audio','spatial-'+action,patch);await fresh('audio');refresh();return result;
 }
 if(area==='playbacks'){
  const patch=data.patch||{},row=states.audio.playback.ambient.find(p=>p.trackId===data.playback_id);
  if(!row)throw Error('Playback not found.');
  action=action==='stop'?'stop':patch.state==='playing'?'play':patch.state==='paused'?'pause':'volume';
  data={trackId:row.trackId,volume:patch.gain,version:data.expected_version};
 }
 const trackId=data.trackId||data.soundId||data.sound_id||data.id;
 const result=await command('audio',action,{...data,trackId,version:states.audio?.version||0});await fresh('audio');refresh();return result;
}
function options(props,emit){return {props,emit,HttpClient:Client,command:areaCommand,read:()=>fresh('cards')};}
function host(name){if(!nodes[name]){nodes[name]=document.createElement('div');nodes[name].style.display='contents';(['cards','placement','audio'].includes(name)?document.querySelector('.game-board__surface')||document.body:document.body).append(nodes[name]);}return nodes[name];}
function close(name){widgets[name]?.destroy();delete widgets[name];nodes[name]?.remove();delete nodes[name];}
function cardProjection(c){return {id:c.id,x:c.x,y:c.y,rotation:c.rotation,scale:c.scale,z_index:c.z_index,width:56,height:80,version:c.version,card:{...c,src:c.face_state==='face_up'?c.frontUrl:c.backUrl},can_manage:c.canControl,can_move:c.canControl,can_reveal:c.canControl};}
function audioProjection(){const m=map(),factor=(m?.gridSize||70)*(m?.imageScale||1)/(m?.measureValue||1);return {spatialSounds:(states.audio?.spatialSounds||[]).map(s=>({...s,sound_id:s.trackId,radius:s.radius*factor,constrained_by_walls:s.occlusion})),audio:(states.audio?.playback?.ambient||[]).map(s=>({...s,id:s.trackId,state:s.status,sound_id:s.trackId,asset:{id:s.trackId},version:states.audio.version,gain:s.volume,baseGain:s.volume}))};}
function base(){const m=map();return {containerId:campaign,blockId:m?.blockId,gm:who(),revision,viewport:window.gravewrightMaps?.board?.viewport(),cell:(m?.gridSize||70)*(m?.imageScale||1),measureValue:m?.measureValue||1,unit:m?.measureUnit||'m',tool:getPath('_tool')};}
function refresh(){
 const props=base();widgets.hand?.update(props);
 const surface=document.querySelector('.map-surface')||document.querySelector('[data-map-surface]')||window.gravewrightMaps?.board?.surface;
 if(widgets.audio)widgets.audio.update({...props,state:audioProjection(),tool:'sound'});
 if(widgets.cards)widgets.cards.update({...props,cards:(states.cards?.cards||[]).map(cardProjection),active:true});
 if(widgets.placement)widgets.placement.update({...props,cards:placement.cards,reveal:placement.reveal});
 syncAudio();
}
function showHand(){if(widgets.hand){close('hand');return;}widgets.hand=CardHand(host('hand'),options(base(),(event,cards,reveal)=>{
 if(event==='place'&&scene){placement={cards,reveal};close('placement');widgets.placement=CardPlacement(host('placement'),options({...base(),...placement},type=>{if(type==='close')close('placement');if(type==='refresh')void fresh('cards').then(refresh);}));}
}));}
function showAudio(){if(!scene)return;if(widgets.audio){close('audio');return;}widgets.audio=AudioWorkspace(host('audio'),options({...base(),state:audioProjection(),tool:'sound'},(event,value)=>{
 if(event==='unlock'){unlocked=true;syncAudio();}else if(event==='tool'&&value==='select')close('audio');else if(event==='refresh')void fresh('audio').then(refresh);
}));}
function syncAudio(){
 const state=states.audio;if(!state)return;const now=Date.now()/1000+clockOffset,desired=new Map(),tracks=new Map((state.tracks||[]).map(t=>[t.id,t]));
 for(const p of state.playback?.ambient||[])if(p.status!=='stopped')desired.set('ambient-'+p.trackId+'-'+(p.playId||'initial'),{trackId:p.trackId,playing:p.status==='playing',offset:p.position+(p.status==='playing'?now-p.startedAt:0),gain:p.volume,loop:p.loop});
 for(const s of state.spatialSounds||[])if(s.enabled)desired.set('spatial-'+s.id,{trackId:s.trackId,playing:true,offset:0,gain:s.effectiveGain,loop:s.loop,spatial:true});
 for(const p of state.score?.playbacks||[]){const elapsed=now-p.startedAt;let gain=p.gain;if(p.fadeIn)gain*=Math.max(0,Math.min(1,elapsed/p.fadeIn));if(p.fadeOut)gain*=Math.max(0,Math.min(1,(p.duration-elapsed)/p.fadeOut));if(p.fade)gain*=Math.max(0,1-(now*1000-p.fade.startedAt)/p.fade.durationMs);desired.set(p.id,{trackId:p.asset.id,playing:p.state==='playing'&&elapsed>=0,offset:p.position??Math.max(0,elapsed),gain,loop:p.loop});}
 for(const [id,row] of media)if(!desired.has(id)||!tracks.has(desired.get(id).trackId)){row.audio.pause();row.audio.removeAttribute('src');row.audio.load();media.delete(id);}
 for(const [id,p] of desired){const track=tracks.get(p.trackId);if(!track)continue;let row=media.get(id);if(!row){row={audio:new Audio(track.src)};row.audio.preload='auto';media.set(id,row);}const a=row.audio;a.loop=p.loop;a.volume=Math.max(0,Math.min(1,p.gain*master*(channels[track.kind==='effect'?'sfx':track.kind]??1)));a.muted=muted;
  if(!p.spatial&&a.readyState&&Number.isFinite(a.duration)&&a.duration>0){const offset=p.loop?p.offset%a.duration:Math.min(p.offset,a.duration);if(Math.abs(a.currentTime-offset)>.5)a.currentTime=offset;}
  if(unlocked&&p.playing&&(p.loop||!Number.isFinite(a.duration)||p.spatial&&!a.ended||p.offset<a.duration)){if(a.paused&&!a.ended)void a.play().catch(()=>{});}else a.pause();
 }
}
window.addEventListener('gravewright:resources',({detail})=>{if((detail.module==='cards'||detail.module==='audio')&&(detail.sceneId??null)===scene){states[detail.module]=detail.state;if(detail.module==='audio'&&detail.state.serverTime)clockOffset=detail.state.serverTime-Date.now()/1000;revision++;refresh();}});
window.addEventListener('gravewright:connected',()=>{for(const module of ['cards','audio'])rt().subscribeModule(module,scene,module==='audio'?previewToken():null);});
window.addEventListener('gravewright:module-scene',()=>{scene=map()?.id||null;delete states.cards;delete states.audio;for(const row of media.values()){row.audio.pause();row.audio.removeAttribute('src');row.audio.load();}media.clear();for(const module of ['cards','audio'])rt()?.subscribeModule(module,scene);close('cards');close('placement');close('audio');if(scene){widgets.cards=SceneCards(host('cards'),options({...base(),cards:[],active:true},(event,value)=>{if(event==='refresh')void fresh('cards').then(refresh);if(event==='preview')window.gravewrightMaps?.board?.previewCard(value);}));}refresh();});
window.addEventListener('gravewright:selection-edit',({detail:{object}})=>{if(object.kind==='sound'){if(!widgets.audio)showAudio();widgets.audio?.call('edit',object.id);}});
window.addEventListener('gravewright:map-viewport',refresh);
window.addEventListener('gravewright:selection-preview',({detail})=>{widgets.audio?.update({selectionPreview:detail});});
window.addEventListener('gravewright:cards-drop',({detail})=>{void cardCommand('play',{card_id:detail.cardId,...detail}).catch(console.error);});
document.addEventListener('click',e=>{const button=e.target.closest('button');if(!button)return;if(button.dataset.dockTool==='cards'){e.stopImmediatePropagation();showHand();}if(['sound','sounds'].includes(button.dataset.dockTool)){e.stopImmediatePropagation();showAudio();}},true);
window.gravewrightTableMedia={areaCommand,showHand,showAudio,mountCompendiums:mount=>ContentDirectory(mount,options(base(),()=>{})),mountDecks:mount=>DeckUpload(mount,options(base(),()=>{void fresh('cards').then(refresh);})),upload:async(file)=>{const body=new FormData();body.append('file',file);body.append('name',file.name);await new Client().upload('/audio',body);await fresh('audio');refresh();},setMuted(value){muted=value;syncAudio();},setVolume(value){master=value;syncAudio();},unlock(){unlocked=true;syncAudio();}};
setInterval(()=>{if(scene&&unlocked)void fresh('audio').then(syncAudio).catch(()=>{});},2000);
window.addEventListener('pagehide',()=>{for(const row of media.values()){row.audio.pause();row.audio.removeAttribute('src');}for(const name of Object.keys(widgets))close(name);});

const muteButton=document.querySelector('[data-audio-control="mute"]');
const volume=document.querySelector('[data-audio-control="volume"]');
const mixer=document.querySelector('[data-audio-control="mixer"]');
try {master=Number(localStorage.getItem('gravewright.audio.volume')||1);muted=localStorage.getItem('gravewright.audio.muted')==='true';channels={...channels,...JSON.parse(localStorage.getItem('gravewright.audio.channels')||'{}')};}catch{}
if(volume){volume.value=String(master*100);volume.oninput=()=>{master=Number(volume.value)/100;volume.setAttribute('aria-valuetext',Math.round(master*100)+'%');try{localStorage.setItem('gravewright.audio.volume',String(master));}catch{}syncAudio();};}
if(muteButton)muteButton.onclick=()=>{if(!unlocked){unlocked=true;muted=false;}else muted=!muted;muteButton.setAttribute('aria-pressed',String(!muted));muteButton.setAttribute('aria-label',muted?'Enable audio':'Mute audio');try{localStorage.setItem('gravewright.audio.muted',String(muted));}catch{}syncAudio();};
const individual=mixer?.closest('.individual-audio');
if(individual){
 const mount=document.createElement('div');mount.style.display='contents';individual.replaceWith(mount);nodes.individual=mount;
 widgets.individual=IndividualAudio(mount,options({enabled:unlocked&&!muted,volume:master,channels},(event,value)=>{
  if(event==='toggle'){if(!unlocked){unlocked=true;muted=false;}else muted=!muted;}
  if(event==='volume')master=value;
  if(event==='channels')channels=value;
  try{localStorage.setItem('gravewright.audio.volume',String(master));localStorage.setItem('gravewright.audio.channels',JSON.stringify(channels));localStorage.setItem('gravewright.audio.muted',String(muted));}catch{}
  widgets.individual?.update({enabled:unlocked&&!muted,volume:master,channels});syncAudio();
 }));
}
const fadeTimer=setInterval(()=>{if(unlocked)syncAudio();},100);
window.addEventListener('pagehide',()=>clearInterval(fadeTimer));

window.addEventListener('gravewright:token-selection',()=>{if(scene&&who()){rt()?.subscribeModule('audio',scene,previewToken());void fresh('audio').then(syncAudio).catch(()=>{});}});
