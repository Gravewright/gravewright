import { gravewright } from '/static/gravewright_modules/frontend-api.js';
import { openFormModal, modalText } from '/static/gravewright_table/form-modal.js';
import { writeReference } from '/static/gravewright_table/references.js';
import { rpgIcon } from '/static/gravewright_web/rpg-icons.js';

const label = (en, pt) => window.gravewrightLocale?.messages?.text?.[en] || modalText(en, pt);
const statuses = ['available','active','completed','draft','failed','archived'];
const names = () => ({available:label('Available','Disponível'),active:label('In progress','Em andamento'),completed:label('Completed','Concluída'),draft:label('Draft','Rascunho'),failed:label('Failed','Fracassada'),archived:label('Archived','Arquivada')});
const node = (tag, cls, value) => { const el=document.createElement(tag);el.className=cls||'';if(value!==undefined)el.textContent=value;return el; };
const button = (title, fn) => {const el=node('button','journal-button',title);el.type='button';el.onclick=fn;return el;};

export function renderBoard(w, host, state, open) {
    const editable = w.draft.can_edit && !w.draft.presentation_ticket;
    const entries = (state.is_gm ? w.draft.board_entries : w.draft.board_display_entries) || [];
    const labels=names();let pending=false;
    host.replaceChildren();host.classList.add('quest-board--compact');
    async function run(action, data={}) {
        if(pending)return false;
        pending=true;host.setAttribute('aria-busy','true');
        try {return await w.perform(action,data);}
        finally {pending=false;host.removeAttribute('aria-busy');}
    }
    const header=node('header','quest-board__toolbar');
    if(editable){
        header.append(button(label('New quest','Nova missão'),()=>{
            openFormModal(label('New quest','Nova missão'),[{name:'title',label:label('Name','Nome'),required:true,maxlength:120}],async form=>{
                const result=await run('board-create',{title:form.elements.title.value});
                if(!result)throw Error(label('Could not create the quest.','Não foi possível criar a missão.'));
                open(result.created_quest_id);
            },{key:'board-new-quest:'+w.draft.id});
        }));
        if(w.editing){
            const select=node('select','journal-input');select.setAttribute('aria-label',label('Link existing quest','Vincular missão existente'));
            select.add(new Option(label('Choose a quest','Escolher missão'),''));
            for(const quest of state.journals.filter(q=>q.type==='quest'&&q.can_open!==false&&!entries.some(e=>e.quest_id===q.id)))select.add(new Option(quest.title,quest.id));
            const link=button(label('Link','Vincular'),()=>void run('board-add',{quest_id:select.value}));link.disabled=true;
            select.onchange=()=>link.disabled=!select.value;header.append(select,link);
        }
    }
    host.append(header);
    if(!entries.length){
        const empty=node('div','quest-board__empty');empty.setAttribute('role','status');
        empty.append(node('strong','',label('No quests yet','Nenhuma missão por aqui')));
        if(editable)empty.append(node('p','',label('Create a quest to add it to this board.','Crie uma missão para adicioná-la a este quadro.')));
        else empty.append(node('p','',label('Quests will appear here when available.','As missões aparecerão aqui quando estiverem disponíveis.')));
        empty.prepend(rpgIcon('quest'));host.append(empty);return;
    }
    const wall=node('div','quest-board__wall');host.append(wall);
    for(const entry of entries){
        const card=entry.card,canEdit=editable&&entry.can_edit;
        const el=node('article','quest-board__card quest-board__compact');el.dataset.status=card.status;el.dataset.questId=entry.quest_id;
        el.classList.toggle('quest-board__card--pinned',entry.pinned);
        el.draggable=true;
        el.ondragstart=event=>{
            writeReference(event.dataTransfer,{type:'journal',id:entry.quest_id,title:card.title});
            event.dataTransfer.effectAllowed='copy';
        };
        wall.append(el);
        const body=node('div','quest-board__paper');el.append(body);
        const heading=node('header','quest-board__identity');body.append(heading);
        if(card.image.src){
            const cover=button('',()=>open(entry.quest_id));cover.className='quest-board__cover';cover.setAttribute('aria-label',card.title);
            const img=node('img');img.src=card.image.src;img.alt='';img.loading='lazy';cover.append(img);heading.append(cover);
        }
        const title=button(card.title,()=>open(entry.quest_id));title.className='quest-board__title';heading.append(title);
        if(canEdit){
            const select=node('select','journal-input quest-board__status-control');select.setAttribute('aria-label',label('Quest status','Estado da missão'));
            for(const status of statuses)select.add(new Option(labels[status],status));select.value=card.status;
            select.onchange=async()=>{select.disabled=true;const result=await run('status',{journal_id:entry.quest_id,status:select.value,version:entry.version});if(!result){select.value=card.status;select.disabled=false;}};heading.append(select);
        }else heading.append(node('small','quest-board__status-badge',labels[card.status]||card.status));
        if(entry.pinned)body.append(node('small','',label('Pinned','Fixada')));
        if(card.summary)body.append(node('p','quest-board__summary',card.summary));
        const facts=[card.location,card.giver].filter(Boolean);if(facts.length)body.append(node('small','quest-board__metadata',facts.join(' · ')));
        if(card.objectives.length){
            const completed=card.objectives.filter(o=>o.completed).length;
            const progress=node('div','quest-board__progress');progress.append(node('strong','',label('Objectives','Objetivos')),node('span','',`${completed}/${card.objectives.length}`));body.append(progress);
            const meter=node('progress','quest-board__meter');meter.max=card.objectives.length;meter.value=completed;meter.setAttribute('aria-label',label('Objectives','Objetivos'));body.append(meter);
            const list=node('ul','quest-board__objectives');body.append(list);
            for(const objective of card.objectives){
                const li=node('li');li.classList.toggle('quest-board__objective--done',objective.completed);
                const field=node('label','quest-board__objective');const check=node('input');check.type='checkbox';check.checked=objective.completed;check.disabled=!canEdit;
                check.onchange=async()=>{check.disabled=true;const result=await run('objective',{journal_id:entry.quest_id,version:entry.version,objective_id:objective.id,completed:check.checked});if(!result){check.checked=objective.completed;check.disabled=!canEdit;}};
                field.append(check,node('span','',objective.text));li.append(field);list.append(li);
            }
        }
        const assigned=node('div','quest-board__assignees');body.append(assigned);
        for(const actor of card.assignees||[])assigned.append(button(actor.name,()=>window.gravewrightActors?.open(actor.id)));
        const actions=node('footer','quest-board__quick-actions');body.append(actions);
        if(canEdit){
            actions.append(button(label('Assign characters','Responsáveis'),async()=>{
                try{
                    const data=await gravewright.actors.state();const actors=data.actors.filter(a=>a.canOpen!==false);
                    const modal=openFormModal(label('Assign characters','Responsáveis'),actors.map((a,i)=>({name:'actor_'+i,type:'checkbox',label:a.name,value:(card.assignees||[]).some(v=>v.id===a.id)})),async form=>{
                        const result=await run('assign',{journal_id:entry.quest_id,version:entry.version,assignees:actors.filter((_,i)=>form.elements['actor_'+i].checked).map(a=>a.id)});
                        if(!result)throw Error(label('Could not save the change.','Não foi possível salvar a alteração.'));
                    },{key:'quest-assignees:'+entry.quest_id});
                    modal.classList.add('quest-assignees-modal');
                }catch(error){w.error(error.message);}
            }));
        }
        for(const location of card.locations||[]){
            const locate=button(label('Locate on map','Localizar no mapa'),()=>window.dispatchEvent(new CustomEvent('gravewright:locate-journal-marker',{detail:{sceneId:location.sceneId,pinId:location.pinId}})));
            locate.title=location.sceneName;actions.append(locate);
        }
        if(w.editing&&editable){
            actions.append(button(entry.pinned?label('Unpin','Desafixar'):label('Pin','Fixar'),()=>void run('board-pin',{quest_id:entry.quest_id,pinned:!entry.pinned})));
            actions.append(button(label('Unlink','Desvincular'),()=>void run('board-remove',{quest_id:entry.quest_id})));
        }
        const assignButton=actions.querySelector('button');
        if(canEdit&&assignButton)assignButton.prepend(rpgIcon('assignees'));
        for(const locate of actions.querySelectorAll('button[title]'))locate.prepend(rpgIcon('map'));
    }
}
