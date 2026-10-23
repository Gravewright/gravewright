import { HttpClient } from './http-client.js';
import { Lifetime, ModuleError } from './lifetime.js';
import { createDomainApi, createEvents } from './domain-api.js';
import { SurfaceRegistry } from './surface-registry.js';
import { createTranslator } from './i18n.js';
import { mountModal } from '/static/gravewright_table/modal.js';
import { createUiApi, setModalHost } from './modal-api.js';
import { createFileCaller, domainTiming } from './file-api.js';
import { createGlobalApi } from './global-api.js';

setModalHost(mountModal, document);

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
    if (!sceneId && !Object.hasOwn(payload, 'sceneId') && !Object.hasOwn(payload, 'mapId') && currentScene)
      payload = { ...payload, sceneId: currentScene, mapId: currentScene };
    if (sceneId) {
      if (domain === 'maps' && method === 'navigate' && ['sceneId', 'mapId'].some(key => Object.hasOwn(payload, key) && payload[key] == null))
        throw new ModuleError('stale_context');
      if (['sceneId', 'mapId'].some(key => payload[key] && payload[key] !== sceneId)) throw new ModuleError('stale_context');
      payload = { ...payload, sceneId, mapId: sceneId };
    }
    const result = await http.post(`/api/tables/${segment(tableId)}/api`, {
      domain, method, payload, requestId: options.requestId ?? crypto.randomUUID(),
    }, { signal, ...domainTiming(domain, method, options) });
    return result.value;
  }, options.signal);
  const files = createFileCaller({ http, life, identity: context, path: `/api/tables/${segment(tableId)}/files`,
    ensure: () => { if (!tableId) throw new ModuleError('stale_context'); } });
  return createDomainApi(call, { context, files, i18n: createTranslator('gravewright', life), events: createEvents(window, life, context,
    domain => call(domain === 'maps.layers' ? 'maps' : domain, domain === 'maps.layers' ? 'layers' : 'state', {}, {})), ui: createUiApi(life, registry.public) });
}

const globalApi = createGlobalApi(http, page);
const tableId = document.querySelector('#table-workspace')?.dataset.tableId;
export const gravewright = Object.freeze({
  ...tableApi(tableId), forTable: (id, { sceneId } = {}) => tableApi(id, sceneId),
  ...globalApi,
});
Object.defineProperty(window, 'gravewright', { value: gravewright, configurable: true });
export function attachSurface(element, domain, context = {}) { return registry.attach(element, domain, context); }
const shell = document.querySelector('#app');
if (shell) attachSurface(shell, 'app.shell', { tableId });
if (location.pathname === '/inside' && shell) attachSurface(shell, 'inside.content', {});
window.addEventListener('pagehide', () => { registry.close(); void page.close(); }, { once: true });
window.addEventListener('gravewright:access-revoked', () => { registry.close(); void page.close(); }, { once: true });
