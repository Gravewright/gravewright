import { mountModal } from './modal.js';
import { modalText } from './form-modal.js';
import {mergePatch} from '/static/gravewright_web/vendor/datastar-1.0.3.js';
const root=document.querySelector('#table-workspace'),campaign=root?.dataset.tableId,role=root?.dataset.detachedChat==='true'?null:root?.dataset.role;
async function request(path,data){const csrf=data===undefined?null:await(await fetch('/__gravewright/csrf')).json();const response=await fetch(`/api/containers/${campaign}/${path}`,{method:data===undefined?'GET':'POST',headers:csrf?{'Content-Type':'application/json',[csrf.header||'X-CSRF-Token']:csrf.token}:{},body:data===undefined?undefined:JSON.stringify(data)});const value=await response.json();if(!response.ok)throw Error(value.error||'Could not save the change.');return value;}
function modal(title) {
  const dialog = document.createElement('section');
  dialog.className = 'table-modal-window';
  dialog.dataset.movable = '';
  dialog.dataset.windowKey = 'campaign-control';
  const heading = document.createElement('header'), h = document.createElement('strong');
  heading.dataset.moveHandle = '';
  h.id = 'campaign-modal-' + crypto.randomUUID();
  h.textContent = title;
  dialog.setAttribute('aria-labelledby', h.id);
  const close = document.createElement('button');
  close.type = 'button'; close.dataset.close = ''; close.textContent = '\u00d7';
  close.setAttribute('aria-label', modalText('Close', 'Fechar'));
  const body = document.createElement('div'), error = document.createElement('p'), footer = document.createElement('footer');
  body.className = 'table-modal-body';
  error.hidden = true; error.setAttribute('role', 'alert');
  heading.append(h, close); dialog.append(heading, body, error, footer);
  let busy = false;
  close.onclick = () => { if (!busy) dialog.close(); };
  function button(label, action) {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = label;
    b.onclick = async () => {
      if (busy) return;
      busy = true; error.hidden = true;
      for (const control of dialog.querySelectorAll('button')) control.disabled = true;
      try { await action(); }
      catch (e) { error.hidden = false; error.textContent = e.message; }
      finally {
        busy = false;
        for (const control of dialog.querySelectorAll('button')) control.disabled = false;
      }
    };
    footer.append(b); return b;
  }
  button(modalText('Close', 'Fechar'), () => dialog.close());
  mountModal(dialog, {canClose: () => !busy});
  return {dialog, body, button};
}
root?.querySelector('[data-campaign-help]')?.addEventListener('click',()=>mergePatch({_house:true,_houseSection:'preferences'}));
root?.querySelector('[data-streamer-link]')?.addEventListener('click',async()=>{const view=modal('Streamer link');try{const link=await request('streamer-link',{}),input=document.createElement('textarea'),note=document.createElement('p');input.readOnly=true;input.value=link.url;input.setAttribute('aria-label','Read-only streamer link');note.textContent='Read-only access. This link expires in 24 hours. Revoking it also disconnects current viewers.';view.body.append(note,input);view.button('Copy link',()=>navigator.clipboard.writeText(link.url));}catch(e){view.body.textContent=e.message;}});
root?.querySelector('[data-streamer-revoke]')?.addEventListener('click',async()=>{const view=modal('Revoke streamer link');view.body.textContent='Disconnect viewers and invalidate the current streamer link?';view.button('Revoke',async()=>{await request('streamer-link/revoke',{});view.dialog.close();});});
if(role==='gm')root.addEventListener('contextmenu',e=>{const member=e.target.closest('[data-member-id]');if(!member||member.dataset.memberRole==='gm')return;e.preventDefault();const view=modal('Remove participant');view.body.textContent=`Remove ${member.querySelector('strong').textContent} from this campaign?`;view.button('Remove participant',async()=>{await request('members/ban',{user_id:member.dataset.memberId});view.dialog.close();});});
if(role==='gm')root.dataset.onboardingReady='true';
if(role==='player')void request('onboarding/claim',{}).then(value=>{if(value.show)mergePatch({_house:true,_houseSection:'preferences'});}).catch(()=>{}).finally(()=>root.dataset.onboardingReady='true');
if(role==='streamer'){
 root.dataset.readOnly='true';
 const style=document.createElement('style');style.textContent='[data-read-only="true"] .chat-panel__composer,[data-read-only="true"] [data-campaign-help]{display:none}';document.head.append(style);
}
