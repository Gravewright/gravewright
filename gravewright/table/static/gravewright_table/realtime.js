let chatMapId = null;
let streamRegion, streamGeneration = 0;
const resourceCommands=new Map();let actorsSubscribed=false,tokenMapId=null;
// Bidirectional table transport. Django owns identity, authorization and rendered content.
import {mergePatch, getPath} from '/static/gravewright_web/vendor/datastar-1.0.3.js';

const root = document.getElementById('table-workspace');
const tableId = root.dataset.tableId;
const detached = root.dataset.detachedChat === 'true';
const log = document.getElementById('chat-log');
const roster = document.getElementById('table-roster');
const emptyRoster = roster?.innerHTML || '';
const messages = new Map();
const rolls = new Map();
const journalCommands = new Map();
const mapCommands = new Map();
const tableCommands = new Map();
const tableSubscriptions = new Map();
let mapsSubscribed = false;
let mapLayerId;
let journalsSubscribed = false;
let socket, retryTimer, watchdog, popup, popupTimer, retry = 500, stopping = false, pending, lastReceived = 0;

function status(presence) {
  mergePatch({_presence: presence});
  if (presence !== 'seated') {
    mergePatch({_onlineCount: 0});
    if (roster) roster.innerHTML = emptyRoster;
  }
}
function send(type, payload = {}) {
  if (socket?.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify({type, payload: {tableId, ...payload}}));
  return true;
}
function renderMessages(entries) {
  const pinned = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
  for (const message of entries) {
    if (message.deleted && message.tableId === tableId) { messages.delete(message.id); continue; }
    if ((!message.sceneId || !chatMapId || message.sceneId === chatMapId) && message.tableId === tableId && /^\d+$/.test(message.id) && typeof message.html === 'string') messages.set(message.id, message);
  }
  const ordered = [...messages.values()].sort((a,b) => Number(a.id)-Number(b.id)).slice(-100);
  const retained = new Set(ordered.map(m => m.id));
  for (const id of messages.keys()) if (!retained.has(id)) messages.delete(id);
  for (const node of [...log.children]) if (!retained.has(node.dataset.messageId)) node.remove();
  for (const entry of ordered) {
    if (!log.querySelector(`[data-message-id="${entry.id}"]`)) {
      const template = document.createElement('template');
      // This is a Jinja2 fragment from our authenticated socket, never raw message text.
      template.innerHTML = entry.html;
      const element = template.content.firstElementChild;
      if (element?.dataset.messageId === entry.id) {
        const next = [...log.children].find(n => Number(n.dataset.messageId) > Number(entry.id));
        if (root.dataset.role === 'gm') {
          const remove = document.createElement('button');
          remove.type = 'button'; remove.className = 'chat-message-delete';
          remove.setAttribute('aria-label', 'Delete message'); remove.title = 'Delete message';
          remove.textContent = '×';
          remove.addEventListener('click', () => moderate('chat.delete', {messageId: entry.id}));
          element.append(remove);
        }
        log.insertBefore(element, next || null);
      }
    }
  }
  mergePatch({_hasChat: ordered.length > 0});
  if (pinned) requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });
}
function receive(event) {
  let message;
  try { message = JSON.parse(event.data); } catch { return; }
  const {type, payload = {}} = message;
  if (payload.tableId && payload.tableId !== tableId) return;
  lastReceived = Date.now();
  window.dispatchEvent(new CustomEvent('gravewright:api-event', { detail: { type, payload: { ...payload, tableId } } }));
  if (type === 'table.joined') {
    retry = 500;
    status('seated');
    send('api.watch');
    send('chat.sync', {mapId:chatMapId});
    if(actorsSubscribed)send('actors.sync');
    if(tokenMapId)send('tokens.sync',{mapId:tokenMapId});
    for(const c of resourceCommands.values())send(c.area+'.command',c.payload);
    if(mapsSubscribed) send('maps.sync');
    if(mapLayerId) send('maps.layers',{mapId:mapLayerId});
    for(const command of mapCommands.values()) send('maps.command',command.payload);
    if (journalsSubscribed) send('journals.sync');
    for (const command of journalCommands.values()) send('journals.command', command.payload);
    for(const [module,subscription] of tableSubscriptions)send('resources.sync',{module,...subscription});
    for(const command of tableCommands.values())send('resources.command',command.payload);
    window.dispatchEvent(new Event('gravewright:connected'));
    if (pending) send('chat.say', pending);
    for (const roll of rolls.values()) send('dice.roll', roll.payload);
  } else if (type === 'session.ping') {
    send('session.pong');
    if (pending) send('chat.say', pending);
    for (const roll of rolls.values()) send('dice.roll', roll.payload);
  } else if (type === 'table.presence') {
    mergePatch({_onlineCount: payload.members.length});
    if (roster && typeof payload.html === 'string') roster.innerHTML = payload.html;
  } else if (type === 'chat.history') {
    messages.clear(); log.replaceChildren(); renderMessages(payload.messages || []);
  } else if (type === 'chat.message') {
    renderMessages([payload]);
  } else if (type === 'chat.ack') {
    renderMessages([payload.message]);
    if (pending?.requestId === payload.requestId) {
      if (getPath('_chatDraft') === pending.text) mergePatch({_chatDraft: ''});
      pending = undefined;
      mergePatch({_chatPending: false, _chatError: ''});
    }
  } else if (['scene.viewport.ready','scene.gm_prefetch.hint'].includes(type)) {
    if (streamRegion && payload.region?.generation === streamRegion.generation && payload.region?.mapId === streamRegion.mapId)
      window.dispatchEvent(new CustomEvent('gravewright:'+type,{detail:payload}));
  } else if (['actors.state','tokens.state','token.drag','handout.presented','modules.updated'].includes(type)) {
    window.dispatchEvent(new CustomEvent('gravewright:'+type,{detail:payload}));
  } else if (['actors.ack','tokens.ack','actors.error','tokens.error'].includes(type)) {
    const c=resourceCommands.get(payload.requestId);
    if(c){resourceCommands.delete(payload.requestId);if(type.endsWith('.ack'))c.resolve(payload.result);else c.reject(Object.assign(new Error(payload.message),{code:payload.code}));}
  } else if (['lobby.state', 'table.search', 'table.tool_error'].includes(type)) {
    window.dispatchEvent(new CustomEvent('gravewright:'+type,{detail:payload}));
  } else if (['zone.entered','zone.left','zone.crossed'].includes(type)) {
    window.dispatchEvent(new CustomEvent('gravewright:'+type,{detail:payload}));
  } else if (type === 'resources.state') {
    window.dispatchEvent(new CustomEvent('gravewright:resources',{detail:payload}));
  } else if (type === 'resources.ack' || type === 'resources.error') {
    const command=tableCommands.get(payload.requestId);
    if(command){tableCommands.delete(payload.requestId);if(type==='resources.ack')command.resolve(payload.result);else command.reject(Object.assign(new Error(payload.message),{code:payload.code}));}
  } else if (type === 'maps.layers') {
    window.dispatchEvent(new CustomEvent('gravewright:map-layers',{detail:payload}));
  } else if (type === 'maps.ping') {
    window.dispatchEvent(new CustomEvent('gravewright:map-ping',{detail:payload}));
  } else if (type === 'maps.state') {
    window.dispatchEvent(new CustomEvent('gravewright:maps', {detail:payload}));
  } else if (type === 'maps.ack' || type === 'maps.error') {
    const command = mapCommands.get(payload.requestId);
    if (command) {
      mapCommands.delete(payload.requestId);
      if (type === 'maps.ack') command.resolve(payload.result);
      else command.reject(Object.assign(new Error(payload.message), {code:payload.code}));
    }
  } else if (type === 'journals.state') {
    window.dispatchEvent(new CustomEvent('gravewright:journals', {detail:payload}));
  } else if (type === 'journals.ack' || type === 'journals.error') {
    const command = journalCommands.get(payload.requestId);
    if (command) {
      journalCommands.delete(payload.requestId);
      if (type === 'journals.ack') command.resolve(payload.result);
      else command.reject(Object.assign(new Error(payload.message), {code:payload.code}));
    }
  } else if (type === 'dice.ack') {
    renderMessages([payload.message]);
    const roll = rolls.get(payload.requestId);
    if (roll) { rolls.delete(payload.requestId); roll.resolve(payload.message); }
  } else if (type === 'dice.error') {
    const roll = rolls.get(payload.requestId);
    if (roll && payload.code !== 'roll_in_progress') { rolls.delete(payload.requestId); roll.reject(new Error(payload.message)); }
  } else if (type === 'error') {
    const errors = {
      gm_required: 'Only the GM can remove chat messages.',
      invalid_chat_command: 'Choose a command from the / menu.',
      invalid_whisper_target: 'Choose a participant: /w Name message.',
      invalid_scene: 'The scene is no longer available.',
      invalid_message: 'Enter a message between 1 and 2000 characters.',
      too_many_messages: 'Too many messages. Please wait a moment and try again.',
      not_a_member: 'You no longer have access to this table.',
    };
    mergePatch({_chatError: errors[payload.code] || 'Could not send the message. Please try again.'});
    if (!payload.requestId || payload.requestId === pending?.requestId) {
      pending = undefined;
      mergePatch({_chatPending: false});
    }
  }
}
function connect() {
  if (stopping) return;
  clearTimeout(retryTimer);
  status('connecting');
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const current = new WebSocket(`${protocol}//${location.host}/ws/tables/${tableId}/`);
  socket = current;
  lastReceived = Date.now();
  current.addEventListener('message', event => { if (socket === current) receive(event); });
  current.addEventListener('error', () => {}); // close owns retry and status.
  current.addEventListener('close', event => {
    if (socket !== current) return;
    status('offline');
    clearInterval(watchdog);
    if (!stopping && ![4401,4403].includes(event.code)) {
      retryTimer = setTimeout(connect, retry);
      retry = Math.min(retry * 2, 10000);
    } else if (!stopping) {
      mergePatch({_chatPending: false, _chatError: 'You no longer have access to this table.'});
      for (const roll of rolls.values()) roll.reject(new Error('You no longer have access to this table.'));
      rolls.clear();
      for (const command of journalCommands.values()) command.reject(new Error('You no longer have access to this table.'));
      journalCommands.clear();
      for(const command of mapCommands.values()) command.reject(new Error('You no longer have access to this table.'));
      mapCommands.clear();
      for(const c of resourceCommands.values())c.reject(new Error('You no longer have access to this table.'));resourceCommands.clear();
      for(const command of tableCommands.values())command.reject(new Error('Access revoked.'));tableCommands.clear();
      window.dispatchEvent(new Event('gravewright:access-revoked'));
    }
  });
  clearInterval(watchdog);
  watchdog = setInterval(() => {
    if (Date.now() - lastReceived > 20000) current.close(4000, 'heartbeat timeout');
  }, 5000);
}
window.gravewrightRealtime = {
  subscribeModule(module,sceneId=null,previewTokenId=null){const subscription={sceneId,previewTokenId};tableSubscriptions.set(module,subscription);send('resources.sync',{module,...subscription});},
  moduleCommand(module,action,data={}){
    if(getPath('_presence')!=='seated')return Promise.reject(new Error('Connect before saving.'));
    const requestId=crypto.randomUUID(),payload={module,action,data,requestId};
    return new Promise((resolve,reject)=>{tableCommands.set(requestId,{payload,resolve,reject});if(!send('resources.command',payload)){tableCommands.delete(requestId);reject(new Error('Connect before saving.'));}});
  },
  tableTool(type, payload = {}) { return send(type, payload); },
  chatScope(mapId) {chatMapId=mapId || null; send('chat.sync',{mapId:chatMapId});},
  sceneViewport(region, signals = {}) {
    if (!streamRegion || Object.keys(region).some(key => region[key] !== streamRegion[key]))
      streamRegion = {...region, generation: ++streamGeneration};
    send('scene.viewport', {...streamRegion, ...signals});
  },
  stopViewport() {streamRegion = undefined; send('scene.viewport.stop');},
  actorsSubscribe(){actorsSubscribed=true;send('actors.sync');},
  tokensSubscribe(mapId){tokenMapId=mapId;send('tokens.sync',{mapId});},
  tokenDrag(payload){send('token.drag',payload);},
  resourceCommand(area,action,data){
    if(getPath('_presence')!=='seated')return Promise.reject(new Error('Connect to the table before saving.'));
    const requestId=crypto.randomUUID(),payload={action,data,requestId};
    return new Promise((resolve,reject)=>{resourceCommands.set(requestId,{area,payload,resolve,reject});if(!send(area+'.command',payload)){resourceCommands.delete(requestId);reject(new Error('Connect to the table before saving.'));}});
  },
  mapLayers(mapId) { mapLayerId=mapId;send('maps.layers',{mapId}); },
  mapPing(payload) { send('maps.ping',payload); },
  mapsSubscribe() { mapsSubscribed = true; send('maps.sync'); },
  mapCommand(action, data) {
    if (getPath('_presence') !== 'seated') return Promise.reject(new Error('Connect to the table before saving.'));
    const requestId = crypto.randomUUID();
    return new Promise((resolve,reject) => {
      const payload = {action,data:{...data,mapId:chatMapId},requestId};
      mapCommands.set(requestId,{payload,resolve,reject});
      if (!send('maps.command',payload)) {
        mapCommands.delete(requestId);reject(new Error('Connect to the table before saving.'));
      }
    });
  },
  journalsSubscribe() { journalsSubscribed = true; send('journals.sync'); },
  journalCommand(action, data) {
    if (getPath('_presence') !== 'seated') return Promise.reject(new Error('Connect to the table before saving.'));
    const requestId = crypto.randomUUID();
    return new Promise((resolve,reject) => {
      const payload = {action,data:{...data,mapId:chatMapId},requestId};
      journalCommands.set(requestId,{payload,resolve,reject});
      if (!send('journals.command',payload)) {
        journalCommands.delete(requestId);reject(new Error('Connect to the table before saving.'));
      }
    });
  },
  roll(payload) {
    if (getPath('_presence') !== 'seated') return Promise.reject(new Error('Connect to the table before rolling.'));
    if (rolls.size) return Promise.reject(new Error('A roll is already in progress.'));
    const requestId = crypto.randomUUID();
    return new Promise((resolve, reject) => {
      rolls.set(requestId, {payload: {...payload, mapId:chatMapId, requestId}, resolve, reject});
      if (!send('dice.roll', {...payload, mapId:chatMapId, requestId})) {
        rolls.delete(requestId); reject(new Error('Connect to the table before rolling.'));
      }
    });
  },
  say(text) {
    if (pending || getPath('_chatPending') || getPath('_presence') !== 'seated' || typeof text !== 'string' || !text.trim()) return;
    const command = text.trim().match(/^\/(roll|r|gmroll)\s+([\s\S]+)$/i);
    if (command) {
      mergePatch({_chatPending: true, _chatError: ''});
      this.roll({expression: command[2], visibility: command[1].toLowerCase()==='gmroll'?'gm':'public'})
        .then(() => { if (getPath('_chatDraft')===text) mergePatch({_chatDraft:''}); })
        .catch(error => mergePatch({_chatError: error.message}))
        .finally(() => mergePatch({_chatPending:false}));
      return;
    }
    pending = {text, mapId:chatMapId, requestId: crypto.randomUUID()};
    mergePatch({_chatPending: true, _chatError: ''});
    if (!send('chat.say', pending)) { pending = undefined; mergePatch({_chatPending: false}); }
  },
  toggleChat() {
    if (popup && !popup.closed) { popup.focus(); return; }
    mergePatch({_chatOpen: !getPath('_chatOpen'), _chatMinimized: false});
    if (getPath('_chatOpen')) requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; });
  },
  closeChat() {
    window.gravewrightDice?.close();
    if (detached) { window.close(); return; }
    popup?.close();
    mergePatch({_chatOpen: false, _chatMinimized: false, _chatDetached: false});
  },
  detach() {
    if (popup && !popup.closed) { popup.focus(); return; }
    popup = window.open(`/game/${tableId}/chat`, `gravewright-${tableId}-chat`, 'popup,width=420,height=760');
    if (!popup) return;
    mergePatch({_chatDetached: true});
    clearInterval(popupTimer);
    popupTimer = setInterval(() => {
      if (popup.closed) { clearInterval(popupTimer); popup = undefined; mergePatch({_chatDetached: false}); }
    }, 300);
  },
};
if (detached) document.body.classList.add('game-detached');
document.addEventListener('click', event => {
  if (!event.target.closest('.game-menubar__roster')) mergePatch({_roster: false});
});
window.addEventListener('pagehide', () => {
  stopping = true;
  clearTimeout(retryTimer); clearInterval(watchdog); clearInterval(popupTimer);
  socket?.close(1000, 'left table'); popup?.close();
});
window.addEventListener('pageshow', event => { if (event.persisted) { stopping = false; connect(); } });
connect();

function moderate(type, payload = {}) {
  if (root.dataset.role !== 'gm') return;
  if (!confirm(type === 'chat.clear' ? 'Delete all messages from this campaign, including other scenes? This cannot be undone.' : 'Delete this message for everyone?')) return;
  if (!send(type, payload)) mergePatch({_chatError: 'Connect to the table before deleting messages.'});
}
root.querySelector('[data-chat-clear]')?.addEventListener('click', () => moderate('chat.clear'));
const composer = document.querySelector('#chat-form textarea');
if (composer && root.dataset.role !== 'streamer') {
  const menu = document.createElement('div');
  menu.className = 'chat-command-menu'; menu.hidden = true;
  menu.setAttribute('role', 'listbox'); menu.id = 'chat-command-menu';
  menu.setAttribute('aria-label', 'Chat commands');
  composer.setAttribute('aria-controls', menu.id);
  composer.setAttribute('aria-autocomplete', 'list');
  composer.before(menu);
  const commands = [
    ['/roll', 'Roll dice · /roll 2d6+1'], ['/gmroll', 'Roll to GM · /gmroll 2d6'],
    ['/w', 'Whisper · /w Name message'], ['/me', 'Describe an action'],
    ['/gm', 'Send a message to the GM'],
  ];
  let selected = 0, matches = [];
  function hide() { menu.hidden = true; composer.removeAttribute('aria-activedescendant'); }
  function highlight() {
    [...menu.children].forEach((button, index) => button.setAttribute('aria-selected', String(index === selected)));
    composer.setAttribute('aria-activedescendant', `chat-command-${selected}`);
  }
  function choose(index) {
    const value = matches[index][0] + ' ';
    composer.value = value; mergePatch({_chatDraft: value}); hide(); composer.focus();
    composer.setSelectionRange(value.length, value.length);
  }
  composer.addEventListener('input', () => {
    const value = composer.value;
    matches = /^\/\S*$/.test(value) ? commands.filter(([token]) => token.startsWith(value.toLowerCase())) : [];
    menu.replaceChildren(); selected = 0;
    if (!matches.length) { hide(); return; }
    matches.forEach(([token, description], index) => {
      const button = document.createElement('button'); button.type = 'button';
      button.id = `chat-command-${index}`; button.setAttribute('role', 'option');
      const title = document.createElement('strong'), detail = document.createElement('span');
      title.textContent = token; detail.textContent = description; button.append(title, detail);
      button.addEventListener('mousedown', event => event.preventDefault());
      button.addEventListener('click', () => choose(index)); menu.append(button);
    });
    menu.hidden = false; highlight();
  });
  composer.addEventListener('keydown', event => {
    if (menu.hidden || event.isComposing) return;
    if (['ArrowDown', 'ArrowUp', 'Enter', 'Tab', 'Escape'].includes(event.key)) {
      event.preventDefault(); event.stopImmediatePropagation();
      if (event.key === 'Escape') hide();
      else if (event.key === 'Enter' || event.key === 'Tab') choose(selected);
      else { selected = (selected + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length; highlight(); }
    }
  }, true);
  composer.addEventListener('blur', hide);
}
