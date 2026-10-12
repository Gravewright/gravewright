import { openPermissions } from "/static/gravewright_table/permissions.js";
import { text as gwText } from "../../../shared/config/i18n/text.js";
import { ResourceScope } from "../../../shared/lifecycle/scope.js";
import DeckUpload from "../../table-library/ui/DeckUpload.native.js";
import { cardFace, fanLayout, fanPose } from "../model/hand.js";
import {widget} from "../../../native/widget.js";
export default widget([{"tag":"section","attrs":{"ref":"host","class":"card-hand"},"bind":{"aria-label":"gwText(\"Your hand\")"},"events":[],"children":[{"tag":"header","attrs":{"class":"card-hand__bar"},"bind":{},"events":[],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"select","attrs":{},"bind":{"aria-label":"gwText(\"Deck\")","disabled":"!state.decks.length"},"events":[],"children":[{"tag":"option","attrs":{"value":""},"bind":{},"events":[],"children":[{"value":"gwText(\"No deck available\")"}],"when":"!state.decks.length"},{"tag":"option","attrs":{},"bind":{"key":"d.id","value":"d.id"},"events":[],"children":[{"value":"d.name"}],"each":{"names":["d"],"value":"state.decks"}}],"model":{"path":"deckId","mods":[]}},{"tag":"button","attrs":{},"bind":{"disabled":"busy || !deck?.draw_count"},"events":[{"event":"click","code":"deck && openDraw(deck);","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Draw cards\")"}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"deck?.draw_count ?? 0"},{"text":" "},{"value":"gwText(\"cards remaining\")"}]},{"tag":"button","attrs":{},"bind":{"aria-pressed":"manage"},"events":[{"event":"click","code":"manage = !manage;","mods":[]}],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"value":"manage ? gwText(\"Hand\") : gwText(\"Decks\")"}],"when":"gm"}]},{"tag":"p","attrs":{"class":"card-hand__error","role":"alert"},"bind":{},"events":[],"children":[{"value":"error"}],"when":"error"},{"tag":"div","attrs":{"class":"card-hand__fan"},"bind":{"style":"({ \"--card-width\": `${layout.width}px`, \"--overlap\": `${layout.overlap}px` })"},"events":[],"children":[{"tag":"p","attrs":{"class":"card-hand__empty"},"bind":{},"events":[],"children":[{"value":"gwText(\"Your hand is empty. Draw a card.\")"}],"when":"!cards.length"},{"tag":"article","attrs":{"class":"card-hand__card","tabindex":"0"},"bind":{"key":"card.id","style":"pose(index)","draggable":"!busy","aria-label":"card.name","title":"gwText(\"Drag to the table\")"},"events":[{"event":"dragstart","code":"drag($event, card);","mods":[]},{"event":"dblclick","code":"openPreview(card);","mods":[]},{"event":"keydown","code":"openPreview(card);","mods":["enter","prevent"]}],"children":[{"tag":"img","attrs":{"draggable":"false"},"bind":{"src":"cardFace(card, flipped.has(card.id))","alt":"flipped.has(card.id) ? gwText(\"Card back\") : card.name"},"events":[],"children":[],"when":"cardFace(card, flipped.has(card.id))"},{"tag":"PhCardsThree","attrs":{"class":"card-hand__back"},"bind":{},"events":[],"children":[],"otherwise":true},{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"card.name"}]},{"tag":"div","attrs":{"class":"card-hand__actions"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"aria-label":"gwText(\"Preview: {0}\", card.name)"},"events":[{"event":"click","code":"openPreview(card);","mods":[]}],"children":[{"tag":"PhMagnifyingGlassPlus","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"aria-label":"flipped.has(card.id) ? gwText(\"Show front\") : gwText(\"Show back\")"},"events":[{"event":"click","code":"flip(card);","mods":[]}],"children":[{"tag":"PhArrowsClockwise","attrs":{},"bind":{},"events":[],"children":[]}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy","aria-label":"gwText(\"Discard card\")"},"events":[{"event":"click","code":"command(\"discard\", { card_ids: [card.id] });","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]}]}]}],"each":{"names":["card","index"],"value":"cards"}}],"when":"!manage"},{"tag":"div","attrs":{"class":"card-hand__decks"},"bind":{},"events":[],"children":[{"tag":"details","attrs":{},"bind":{},"events":[],"children":[{"tag":"summary","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"Create deck\")"}]},{"tag":"DeckUpload","attrs":{},"bind":{"container-id":"containerId"},"events":[{"event":"created","code":"refresh;","mods":[]}],"children":[]}]},{"tag":"p","attrs":{},"bind":{},"events":[],"children":[{"value":"gwText(\"No deck in play.\")"}],"when":"!state.decks.length"},{"tag":"article","attrs":{"class":"card-hand__deck"},"bind":{"key":"d.id"},"events":[],"children":[{"tag":"PhCardsThree","attrs":{},"bind":{},"events":[],"children":[]},{"tag":"div","attrs":{},"bind":{},"events":[],"children":[{"tag":"strong","attrs":{},"bind":{},"events":[],"children":[{"value":"d.name"}]},{"tag":"small","attrs":{},"bind":{},"events":[],"children":[{"value":"d.draw_count"},{"text":" "},{"value":"gwText(\"cards remaining\")"}]}]},{"tag":"div","attrs":{"class":"card-hand__deck-actions"},"bind":{},"events":[],"children":[{"tag":"button","attrs":{},"bind":{"disabled":"busy || !d.draw_count"},"events":[{"event":"click","code":"openDraw(d);","mods":[]}],"children":[{"tag":"PhPlus","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Draw cards\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"command(\"shuffle\", { deck_instance_id: d.id });","mods":[]}],"children":[{"tag":"PhShuffle","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Shuffle\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"command(\"reset\", { deck_instance_id: d.id });","mods":[]}],"children":[{"tag":"PhArrowsClockwise","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Recall\")"}]},{"tag":"button","attrs":{},"bind":{"disabled":"busy"},"events":[{"event":"click","code":"openDelete(d);","mods":[]}],"children":[{"tag":"PhTrash","attrs":{},"bind":{},"events":[],"children":[]},{"value":"gwText(\"Remove\")"}]},{"tag":"button","attrs":{"type":"button"},"bind":{},"events":[{"event":"click","code":"permissions(d);","mods":["stop","prevent"]}],"children":[{"value":"gwText(\"Permissions\")"}],"when":"props.gm"}]}],"each":{"names":["d"],"value":"state.decks"}}],"otherwise":true}]}],(options,{ref,computed,watch,onMounted,onBeforeUnmount,nextTick,defineExpose})=>{
const PhCardsThree='PhCardsThree', PhPlus='PhPlus', PhMagnifyingGlassPlus='PhMagnifyingGlassPlus', PhArrowsClockwise='PhArrowsClockwise', PhTrash='PhTrash', PhShuffle='PhShuffle';
const props=options.props, emit=options.emit;
const scope=new ResourceScope(), http=new options.HttpClient(undefined,()=>scope.signal), root=`/api/containers/${encodeURIComponent(props.containerId)}/library`;
const state=ref({decks:[],hand:[]}),deckId=ref(''),manage=ref(false),busy=ref(false),error=ref(''),flipped=ref(new Set());
const host=ref(),available=ref(550),count=ref(1),destination=ref('hand'),face=ref('face_up');
let observer,visit=0,childModal,preview,drawDeck;
const deck=computed(()=>state.value.decks.find(d=>d.id===deckId.value));
const cards=computed(()=>state.value.hand.filter(c=>c.deck_instance_id===deckId.value));
const layout=computed(()=>fanLayout(cards.value.length,available.value-42));
function pose(index){const p=fanPose(index,cards.value.length);return {'--rotation':`${p.rotation}deg`,'--arc':`${p.arc}px`,'--order':index+1};}
async function permissions(item){try{await openPermissions('cards',item.id,{onSave:refresh,nested:true});}catch(cause){error.value=cause.message;}}
async function refresh(){
 const id=++visit;
 try{
  const next=await http.get(root+'/card-state');if(scope.closed||id!==visit)return;
  state.value=next;
  if(!next.decks.some(d=>d.id===deckId.value))deckId.value=next.decks[0]?.id??'';
  flipped.value=new Set([...flipped.value].filter(id=>next.hand.some(c=>c.id===id)));
  if(preview&&!next.hand.some(c=>c.id===preview.id))closeChild();
  syncChild();
 }catch{if(!scope.closed)error.value=gwText('Could not load your cards.');}
}
async function command(action,data){
 if(busy.value)return;busy.value=true;error.value='';
 try{const result=await http.post(root+'/cards/'+action,data);await refresh();return result;}
 catch{if(!scope.closed)error.value=gwText('Could not complete the action. The deck may have changed or the action is not allowed.');}
 finally{if(!scope.closed)busy.value=false;}
}
function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
function glyph(name){return document.querySelector('#map-native-icons')?.content.querySelector(`[data-icon="${name}"][data-weight="regular"]`)?.firstElementChild?.cloneNode(true);}
function control(label,action,icon){
 const node=element('button');node.type='button';
 if(icon){node.setAttribute('aria-label',label);const svg=glyph(icon);if(svg)node.append(svg);else node.textContent=label;}
 else node.textContent=label;
 node.onclick=action;return node;
}
function closeChild(force=false){childModal?.close(force);}
function openChild(kind,title){
 if(busy.value)return;closeChild();error.value='';
 const modal=options.openModal(title,{kind,canClose:()=>!busy.value});childModal=modal;
 modal.addEventListener('close',()=>{if(childModal!==modal)return;childModal=undefined;preview=drawDeck=undefined;},{once:true});
 return modal;
}
function syncChild(){
 const modal=childModal;if(!modal)return;
 for(const node of modal.querySelectorAll('button,input,fieldset'))node.disabled=busy.value;
 const alert=modal.querySelector('[role="alert"]');if(alert){alert.textContent=error.value;alert.hidden=!error.value;}
 if(!drawDeck)return;
 drawDeck=state.value.decks.find(item=>item.id===drawDeck.id)||drawDeck;
 const amount=modal.querySelector('[name="count"]');
 if(amount){amount.max=drawDeck.draw_count;if(document.activeElement!==amount)amount.value=count.value;}
 for(const node of modal.querySelectorAll('[name="destination"]'))node.checked=node.value===destination.value;
 for(const node of modal.querySelectorAll('[name="face"]'))node.checked=node.value===face.value;
 const decrease=modal.querySelector('[data-quantity="decrease"]'),increase=modal.querySelector('[data-quantity="increase"]');
 if(decrease)decrease.disabled=busy.value||count.value<=1;
 if(increase)increase.disabled=busy.value||count.value>=drawDeck.draw_count;
 const submit=modal.querySelector('[type="submit"]');if(submit)submit.disabled=busy.value||!drawDeck.draw_count;
 const remaining=modal.querySelector('[data-remaining]');if(remaining)remaining.textContent=`${drawDeck.draw_count} ${gwText('cards remaining')}`;
}
function openPreview(card){
 const modal=openChild('preview',flipped.value.has(card.id)?gwText('Card back'):card.name);if(!modal)return;preview=card;
 const src=cardFace(card,flipped.value.has(card.id));
 if(src){const image=element('img');image.src=src;image.alt=flipped.value.has(card.id)?gwText('Card back'):card.name;image.draggable=false;modal.body.append(image);}
 else{const icon=glyph('PhCardsThree');if(icon)modal.body.append(icon);}
}
function openDraw(target){
 const modal=openChild('draw',gwText('Draw cards'));if(!modal)return;drawDeck=target;count.value=1;
 try{destination.value=sessionStorage.getItem('gravewright.cards.draw.destination')||'hand';face.value=sessionStorage.getItem('gravewright.cards.draw.face')||'face_up';}catch{}
 if(!['hand','table','chat'].includes(destination.value))destination.value='hand';if(!['face_up','face_down'].includes(face.value))face.value='face_up';
 const form=element('form');form.id='cards-draw-'+crypto.randomUUID();form.onsubmit=event=>{event.preventDefault();void draw();};
 const choices=element('div','card-hand__choices');
 function choiceGroup(name,title,values,selected){
  const group=element('fieldset');group.append(element('legend','',title));
  for(const [value,label,icon] of values){
   const choice=element('label'),input=element('input');input.type='radio';input.name=name;input.value=value;input.checked=selected.value===value;
   input.onchange=()=>{selected.value=value;syncChild();};choice.append(input);const svg=glyph(icon);if(svg)choice.append(svg);
   choice.append(document.createTextNode(label));group.append(choice);
  }
  choices.append(group);
 }
 choiceGroup('destination',gwText('Destination'),[['hand',gwText('Hand'),'PhHand'],['table',gwText('Table'),'PhMapTrifold'],['chat',gwText('Chat'),'PhChatCircleText']],destination);
 choiceGroup('face',gwText('Face'),[['face_up',gwText('Face up'),'PhEye'],['face_down',gwText('Face down'),'PhEyeSlash']],face);
 const quantity=element('label','card-hand__quantity',gwText('Quantity')),stepper=element('span'),amount=element('input');
 amount.type='number';amount.name='count';amount.min='1';amount.step='1';amount.required=true;amount.max=target.draw_count;amount.value='1';
 amount.oninput=()=>{count.value=amount.valueAsNumber;syncChild();};
 const decrease=control(gwText('Decrease quantity'),()=>{count.value=Math.max(1,count.value-1);syncChild();},'PhMinus');
 const increase=control(gwText('Increase quantity'),()=>{count.value=Math.min(drawDeck.draw_count,count.value+1);syncChild();},'PhPlus');
 decrease.dataset.quantity='decrease';increase.dataset.quantity='increase';stepper.append(decrease,amount,increase);
 const remaining=element('small');remaining.dataset.remaining='';quantity.append(stepper,remaining);
 const alert=element('p','card-hand__error');alert.setAttribute('role','alert');alert.hidden=true;form.append(choices,quantity,alert);
 modal.body.append(element('small','card-modal__subtitle',target.name),form);
 const cancel=control(gwText('Cancel'),()=>closeChild()),submit=element('button','',gwText('Draw cards'));submit.type='submit';submit.setAttribute('form',form.id);
 modal.footer.append(cancel,submit);syncChild();amount.focus();
}
function openDelete(target){
 const modal=openChild('remove',gwText('Remove deck'));if(!modal)return;
 modal.body.append(element('strong','',`${gwText('Remove')} ${target.name}?`),element('p','',gwText("This deck's cards in hands, the discard pile, and the table will be removed.")));
 const alert=element('p','card-hand__error');alert.setAttribute('role','alert');alert.hidden=true;modal.body.append(alert);
 const cancel=control(gwText('Cancel'),()=>closeChild());
 const remove=control(gwText('Remove'),async()=>{const result=await command('delete',{deck_instance_id:target.id});if(result&&childModal===modal)closeChild();});
 remove.classList.add('card-modal__danger');modal.footer.append(cancel,remove);cancel.focus();
}
async function draw(){
 if(!drawDeck||busy.value)return;
 if(destination.value!=='hand'&&!props.blockId){error.value=gwText('Open a scene to use this destination.');syncChild();return;}
 const selectedDestination=destination.value,reveal=face.value==='face_up';
 const result=await command('draw',{deck_instance_id:drawDeck.id,count:count.value,destination:selectedDestination==='table'?'hand':selectedDestination,reveal,...(selectedDestination==='chat'?{block_id:props.blockId}:{})});
 if(!result||scope.closed)return;
 try{sessionStorage.setItem('gravewright.cards.draw.destination',selectedDestination);sessionStorage.setItem('gravewright.cards.draw.face',face.value);}catch{}
 closeChild();if(selectedDestination==='table')emit('place',result.cards??[],reveal);
}
function flip(card){const next=new Set(flipped.value);if(next.has(card.id))next.delete(card.id);else next.add(card.id);flipped.value=next;}
function drag(event,card){
 if(busy.value){event.preventDefault();return;}
 event.dataTransfer?.setData('application/x-gravewright-hand-card',JSON.stringify({cardId:card.id,reveal:!flipped.value.has(card.id)}));
 if(event.dataTransfer)event.dataTransfer.effectAllowed='move';emit('dragstart');
}
watch(()=>props.revision,()=>void refresh());
watch(()=>busy.value,value=>{emit('busy',value);syncChild();});
watch(()=>error.value,syncChild);
defineExpose({canClose:()=>!busy.value});
onMounted(()=>{void refresh();observer=new ResizeObserver(entries=>{available.value=entries[0]?.contentRect.width??550;});if(host.value)observer.observe(host.value);});
onBeforeUnmount(()=>{closeChild(true);scope.dispose();observer?.disconnect();});
return {permissions,gwText,PhCardsThree,PhPlus,PhMagnifyingGlassPlus,PhArrowsClockwise,PhTrash,PhShuffle,DeckUpload,cardFace,props,emit,state,deckId,manage,busy,error,flipped,host,available,deck,cards,layout,pose,refresh,command,openPreview,openDelete,openDraw,draw,flip,drag};
});
