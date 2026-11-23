// Transport bookkeeping stays separate from the public native and SDK payloads.
export function createCommandRecovery({send, fail, schedule = setTimeout, cancel = clearTimeout}) {
  const commands = new Map();
  function complete(requestId) {
    const command = commands.get(requestId);
    if (!command) return;
    cancel(command.deadline);
    cancel(command.retryTimer);
    commands.delete(requestId);
  }
  return {
    sent(type, payload) {
      if (!payload.requestId || commands.has(payload.requestId)) return;
      const command = {type, payload, attempts: 0};
      command.deadline = schedule(() => fail(), 45000);
      commands.set(payload.requestId, command);
    },
    retry(requestId) {
      const command = commands.get(requestId);
      if (!command) return false;
      if (command.retryTimer !== undefined) return true;
      const delay = Math.min(1000 * 2 ** command.attempts++, 8000);
      command.retryTimer = schedule(() => {
        command.retryTimer = undefined;
        if (commands.has(requestId)) send(command.type, command.payload);
      }, delay);
      return true;
    },
    complete,
    clear() {
      for (const requestId of commands.keys()) complete(requestId);
    },
  };
}

export function createProjectionState() {
  const states = new Map();
  function merge(key, payload) {
    if (!payload.delta) {
      states.set(key, structuredClone(payload));
      return payload;
    }
    const previous = states.get(key);
    if (!previous) return null;
    const {delta, upserts = {}, removes = {}, order = {}, unset = [], ...metadata} = payload;
    // The merge replaces collection arrays and top-level fields; it never edits
    // cached rows. Keep one private copy before exposing the complete result.
    const result = {...previous, ...metadata};
    for (const field of unset) delete result[field];
    for (const field of new Set([...Object.keys(upserts), ...Object.keys(removes), ...Object.keys(order)])) {
      const rows = new Map((previous[field] || []).map(row => [String(row.id), row]));
      for (const id of removes[field] || []) rows.delete(String(id));
      for (const row of upserts[field] || []) rows.set(String(row.id), row);
      if (order[field]) {
        const ids = order[field].map(String);
        if (ids.length !== rows.size || new Set(ids).size !== rows.size || ids.some(id => !rows.has(id))) {
          states.delete(key);
          return null;
        }
        result[field] = ids.map(id => rows.get(id));
      } else result[field] = [...rows.values()];
    }
    states.set(key, structuredClone(result));
    return result;
  }
  return {
    clear() { states.clear(); },
    forgetResource(module) {
      for (const key of states.keys()) {
        if (key.startsWith(`resources.state:${module}:`)) states.delete(key);
      }
    },
    receive(type, payload) {
      if (type === 'resources.state' && payload.module === 'audio') {
        const key = `${type}:audio:${payload.sceneId}`;
        if (payload.unavailable) {
          states.delete(key);
          return payload;
        }
        const state = merge(key, payload.state);
        return state ? {...payload, state} : null;
      }
      if (!['tokens.state', 'maps.layers'].includes(type)) return payload;
      return merge(`${type}:${type === 'tokens.state' ? payload.mapId : payload.sceneId}`, payload);
    },
  };
}
