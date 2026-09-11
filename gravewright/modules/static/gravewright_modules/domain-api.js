import { FRONTEND_CONTRACT } from './frontend-contract.js';
import { ModuleError } from './lifetime.js';

const collections = { actors: 'actors', tokens: 'tokens', maps: 'maps', journals: 'journals', items: 'items' };

/**
 * Public domain methods shared by native pages and installed modules. The call
 * adapter permanently owns table/module/scene identity; payloads cannot grant it.
 * frontend-contract.js is generated from contracts/frontend.json, while result
 * projection and command validation stay in each native Python service.
 */
export function createDomainApi(call, { events, ui, context = {} } = {}) {
  const api = { version: FRONTEND_CONTRACT.version, context: Object.freeze({ ...context }) };
  const request = (domain, method, payload = {}, options = {}) => {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return Promise.reject(new ModuleError('invalid_data'));
    return call(domain, method, payload, options);
  };
  for (const [domain, methods] of Object.entries(FRONTEND_CONTRACT.domains)) {
    const resource = { state: (payload = {}, options) => request(domain, 'state', payload, options) };
    for (const method of Object.keys(methods)) {
      resource[method] = (payload = {}, options) => request(domain, method, payload, options);
    }
    if (collections[domain]) {
      resource.list = async (payload = {}, options) => (await resource.state(payload, options))[collections[domain]];
      resource.get = async (id, payload = {}, options) => {
        const value = (await resource.list(payload, options)).find(row => row.id === id);
        if (!value) throw new ModuleError('not_found');
        return value;
      };
    }
    api[domain] = resource;
  }
  // Accept the concise actor.update(id, changes, options) form as well as native payloads.
  const updateActor = api.actors.update;
  api.actors.update = async (id, changes = {}, options) => {
    if (typeof id !== 'string') return updateActor(id, changes);
    const version = changes.version ?? (await api.actors.get(id, {}, options)).version;
    return updateActor({ ...changes, version, id }, options);
  };
  for (const method of ['nextTurn', 'previousTurn', 'nextRound', 'previousRound', 'start', 'stop']) {
    const execute = api.combat[method];
    api.combat[method] = async (payload = {}, options) => {
      const version = payload.version ?? (await api.combat.state(payload, options)).version;
      return execute({ ...payload, version }, options);
    };
  }
  api.actors.sheet = (id, payload = {}, options) => request('actors', 'sheet', { ...payload, id }, options);
  api.maps.layers = (payload = {}, options) => request('maps', 'layers', payload, options);
  api.chat = {
    history: (payload = {}, options) => request('chat', 'history', payload, options),
    send: (payload, options) => request('chat', 'send', payload, options),
    remove: (id, options) => request('chat', 'remove', { id }, options),
    clear: (options) => request('chat', 'clear', {}, options),
  };
  api.dice = { roll: (expression, payload = {}, options) => request('dice', 'roll', { ...payload, expression }, options) };
  api.table = {
    search: (query, options) => request('table', 'search', { query }, options),
    lobby: (options) => request('table', 'lobby', {}, options),
    updateLobby: (payload, options) => request('table', 'updateLobby', payload, options),
  };
  if (events) api.events = events;
  if (ui) api.ui = ui;
  for (const value of Object.values(api)) if (value && typeof value === 'object') Object.freeze(value);
  return Object.freeze(api);
}

/** Compatibility for native controls that still store action names in HTML. */
export function executeNative(api, domain, action, payload, options) {
  const method = Object.entries(FRONTEND_CONTRACT.domains[domain] ?? {}).find(([, value]) => value === action)?.[0];
  if (!method) return Promise.reject(new ModuleError('unavailable'));
  return api[domain][method](payload, options);
}

const eventTypes = {
  'actors.changed': 'actors.state', 'tokens.changed': 'tokens.state',
  'maps.changed': 'maps.state', 'maps.layersChanged': 'maps.layers',
  'journals.changed': 'journals.state', 'chat.changed': 'chat.history',
  'chat.message': 'chat.message', 'table.presence': 'table.presence',
  'table.lobbyChanged': 'lobby.state',
  ...Object.fromEntries(['items','combat','cards','audio','compendiums'].map(name => [name + '.changed', 'resources.state'])),
};

/**
 * Project socket invalidations through authenticated reads, coalescing overlapping
 * refreshes. Reconnect re-reads collection state; this is not a mutation log.
 * Chat/presence/lobby events instead forward their authorized socket payloads.
 */
export function createEvents(target, life, identity = {}, read) {
  return Object.freeze({ on(name, handler) {
    life.check();
    if (!(name in eventTypes) || typeof handler !== 'function') throw new ModuleError('invalid_data');
    const domain = name === 'maps.layersChanged' ? 'maps.layers' : name.split('.')[0];
    const projected = read && (name.endsWith('.changed') && domain !== 'chat' || name === 'maps.layersChanged');
    let active = true, reading = false, dirty = false;
    const refresh = async () => {
      if (!active || life.signal.aborted) return;
      if (reading) { dirty = true; return; }
      reading = true;
      try {
        const value = await read(domain);
        if (active && !life.signal.aborted) {
          const payload = eventTypes[name] === 'resources.state'
            ? { module: domain, state: value } : value;
          handler({ ...payload, tableId: identity.tableId, ...(identity.sceneId ? { sceneId: identity.sceneId } : {}) });
        }
      } catch (error) {
        if (active && !life.signal.aborted) console.error(error);
      } finally {
        reading = false;
        if (dirty) { dirty = false; void refresh(); }
      }
    };
    const callback = ({ detail }) => {
      if (life.signal.aborted) return;
      const payload = detail.payload;
      if (identity.tableId && payload.tableId !== identity.tableId) return;
      if (projected) {
        if (detail.type === 'api.changed' && payload.domain === domain) void refresh();
        return;
      }
      if (detail.type !== eventTypes[name]) return;
      const scene = payload.sceneId ?? payload.mapId;
      if (identity.sceneId && scene && scene !== identity.sceneId) return;
      if (detail.type === 'resources.state' && name !== payload.module + '.changed') return;
      try { handler(structuredClone(payload)); } catch (error) { console.error(error); }
    };
    target.addEventListener('gravewright:api-event', callback);
    if (projected) { target.addEventListener('gravewright:connected', refresh); void refresh(); }
    const dispose = () => {
      if (!active) return;
      active = false;
      target.removeEventListener('gravewright:api-event', callback);
      target.removeEventListener('gravewright:connected', refresh);
      unlink();
    };
    const unlink = life.link(dispose);
    return dispose;
  } });
}
