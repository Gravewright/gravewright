/** Native editors use the same authorized HTTP API without joining a table. */
export function managementTransport({ api, execute, authorize, publish, revoked, report = () => {} }) {
  const scope = new AbortController(), reads = new Map(), subscriptions = new Map();
  const states = new Map(), revisions = new Map(), signatures = new Map();
  let access;
  const options = extra => ({ ...extra, signal: scope.signal });
  async function check() {
    scope.signal.throwIfAborted();
    if (!access) access = Promise.resolve().then(() => authorize(scope.signal)).catch(error => {
      if (error.status === 401 || error.status === 403 || error.status === 404 || error.code === 'permission_denied') {
        scope.abort(); states.clear(); revoked(error);
      }
      throw error;
    }).finally(() => { access = undefined; });
    const value = await access;
    scope.signal.throwIfAborted();
    return value;
  }
  function read(domain) {
    if (scope.signal.aborted) return Promise.reject(scope.signal.reason);
    if (reads.has(domain)) return reads.get(domain);
    const task = (async () => {
      let revision, value;
      do {
        revision = revisions.get(domain) || 0;
        value = await api[domain].state(subscriptions.get(domain) || {}, options());
        scope.signal.throwIfAborted();
      } while (revision !== (revisions.get(domain) || 0));
      states.set(domain, value);
      const signature = JSON.stringify([subscriptions.get(domain) || {}, value]);
      if (signatures.get(domain) !== signature) {
        signatures.set(domain, signature);
        publish(domain, value, subscriptions.get(domain) || {});
      }
      return value;
    })().finally(() => { if (reads.get(domain) === task) reads.delete(domain); });
    reads.set(domain, task);
    return task;
  }
  const invalidate = domain => revisions.set(domain, (revisions.get(domain) || 0) + 1);
  function subscribe(domain, sceneId = null, previewTokenId = null) {
    const next = { sceneId, ...(previewTokenId ? { previewTokenId } : {}) };
    if (JSON.stringify(subscriptions.get(domain)) !== JSON.stringify(next)) invalidate(domain);
    subscriptions.set(domain, next);
    return read(domain).catch(error => { if (!scope.signal.aborted) report(error); });
  }
  async function command(domain, action, data, extra = {}) {
    await check();
    const result = await execute(api, domain, action, data, options(extra));
    scope.signal.throwIfAborted();
    invalidate(domain);
    await read(domain);
    return result;
  }
  return {
    signal: scope.signal, states, check, read, subscribe, invalidate,
    journalCommand: (action, data, extra) => command('journals', action, data, extra),
    resourceCommand: command,
    actorsSubscribe: () => subscribe('actors'),
    journalsSubscribe: () => subscribe('journals'),
    subscribeModule: subscribe,
    // Document pickers use this instead of the table socket's search tool.
    async search(query) {
      await check();
      return api.table.search(query, options());
    },
    async roll(payload, { requestId = crypto.randomUUID(), mapId } = {}) {
      await check();
      return api.dice.roll(payload.expression, { ...payload, sceneId: mapId }, options({ requestId }));
    },
    async refresh() {
      await check();
      const results = await Promise.allSettled([...subscriptions.keys()].map(read));
      for (const result of results) if (result.status === 'rejected' && !scope.signal.aborted) report(result.reason);
    },
    close() { scope.abort(); subscriptions.clear(); states.clear(); signatures.clear(); },
  };
}
