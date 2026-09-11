import { HttpClient } from './http-client.js';
import { Lifetime, ModuleError } from './lifetime.js';
import { createDomainApi, createEvents } from './domain-api.js';
import { SurfaceRegistry } from './surface-registry.js';

// Host-page API lifetime. Signed modules receive a separately leased adapter
// from BrowserBridge instead of using this global page-owned object.
const page = new Lifetime();
const http = new HttpClient(undefined, () => page.signal);
const segment = value => encodeURIComponent(value);
const registry = new SurfaceRegistry((context, life) => tableApi(context.tableId, context.sceneId, life));

export function tableApi(tableId, sceneId, life = page) {
  // Binding another table enables HTTP reads/writes; it does not open its socket.
  const context = { tableId, ...(sceneId ? { sceneId } : {}) };
  const call = (domain, method, payload, options) => life.wait(async signal => {
    if (!tableId) throw new ModuleError('stale_context', 'Choose a table with gravewright.forTable(tableId).');
    const currentScene = tableId === document.querySelector('#table-workspace')?.dataset.tableId
      ? window.gravewrightMaps?.current?.id : undefined;
    if (!sceneId && !payload.sceneId && !payload.mapId && currentScene) payload = { ...payload, sceneId: currentScene, mapId: currentScene };
    if (sceneId) {
      if (['sceneId', 'mapId'].some(key => payload[key] && payload[key] !== sceneId)) throw new ModuleError('stale_context');
      payload = { ...payload, sceneId };
    }
    const result = await http.post(`/api/tables/${segment(tableId)}/api`, {
      domain, method, payload, requestId: options.requestId ?? crypto.randomUUID(),
    }, { signal });
    return result.value;
  }, options.signal);
  return createDomainApi(call, { context, events: createEvents(window, life, context,
    domain => call(domain === 'maps.layers' ? 'maps' : domain, domain === 'maps.layers' ? 'layers' : 'state', {}, {})), ui: registry.public });
}

// These adapters reuse the site's authenticated endpoints, including server-side owner checks.
const accounts = {
  status: () => http.get('/api/auth/status'),
  session: () => http.get('/api/auth/session'),
  login: payload => http.post('/api/auth/login', payload),
  register: payload => http.post('/api/auth/register', payload),
  setup: payload => http.post('/api/auth/setup', payload),
  logout: () => http.post('/api/auth/logout', {}),
  update: payload => http.post('/api/auth/account', payload),
};
const campaigns = {
  list: () => http.get('/api/containers'),
  create: payload => http.post('/api/containers', payload),
  update: (id, payload) => http.post(`/api/containers/${segment(id)}`, payload),
  join: code => http.post('/api/containers/join', { code }),
  remove: (id, code) => http.post(`/api/containers/${segment(id)}/remove`, { code }),
  invite: (id, payload = {}) => http.post(`/api/containers/${segment(id)}/invitation`, payload),
  rulesets: () => http.get('/api/rulesets'),
};
const administration = {
  status: () => http.get('/api/admin/status'),
  diagnostics: () => http.get('/api/admin/diagnostics'),
  settings: () => http.get('/api/admin/settings'),
  updateSettings: (section, payload) => http.post(`/api/admin/settings/${segment(section)}`, payload),
};
const modules = {
  list: () => http.get('/api/module-packages'),
  catalog: () => http.get('/api/marketplace'),
  status: () => http.get('/api/marketplace/status'),
  install: payload => http.post('/api/marketplace/install', payload),
  state: id => http.get(`/api/tables/${segment(id)}/modules`),
  configure: (id, payload) => http.post(`/api/tables/${segment(id)}/modules`, payload),
};
const tableId = document.querySelector('#table-workspace')?.dataset.tableId;
export const gravewright = Object.freeze({
  ...tableApi(tableId), forTable: (id, { sceneId } = {}) => tableApi(id, sceneId),
  accounts: Object.freeze(accounts), campaigns: Object.freeze(campaigns),
  administration: Object.freeze(administration), modules: Object.freeze(modules),
});
Object.defineProperty(window, 'gravewright', { value: gravewright, configurable: true });
export function attachSurface(element, domain, context = {}) { return registry.attach(element, domain, context); }
const shell = document.querySelector('#app');
if (shell) attachSurface(shell, 'app.shell', { tableId });
if (location.pathname === '/inside' && shell) attachSurface(shell, 'inside.content', {});
window.addEventListener('pagehide', () => { registry.close(); void page.close(); }, { once: true });
window.addEventListener('gravewright:access-revoked', () => { registry.close(); void page.close(); }, { once: true });
