import { Lifetime, ModuleError } from './lifetime.js';
import { DOMAIN_NAMES } from './generated.js';

/** Host UI extensions. Module registrations remain owned by ModuleRuntime. */
export class SurfaceRegistry {
  registrations = new Map();
  surfaces = new Set();
  closed = false;
  constructor(createApi, report = console.error) {
    this.createApi = createApi;
    this.report = report;
    this.public = Object.freeze({ register: this.register.bind(this) });
  }
  register(domain, declaration) {
    if (this.closed) throw new ModuleError('stale_context');
    if (![...DOMAIN_NAMES, 'app.shell', 'inside.content'].includes(domain)) throw new ModuleError('invalid_data');
    const entry = typeof declaration === 'function' ? { mount: declaration } : { ...declaration };
    entry.mode ??= 'augment';
    if (typeof entry.mount !== 'function' || !['augment', 'replace'].includes(entry.mode)) throw new ModuleError('invalid_data');
    const entries = this.registrations.get(domain) ?? new Set();
    if (entry.mode === 'replace' && [...entries].some(e => e.mode === 'replace')) throw new ModuleError('conflict');
    entries.add(entry);
    this.registrations.set(domain, entries);
    for (const surface of this.surfaces) if (surface.domain === domain) this.mount(surface, entry);
    return () => {
      entries.delete(entry);
      if (!entries.size) this.registrations.delete(domain);
      for (const surface of this.surfaces) {
        void surface.mounts.get(entry)?.close();
        surface.mounts.delete(entry);
      }
    };
  }
  attach(element, domain, context) {
    if (this.closed) throw new ModuleError('stale_context');
    const surface = { element, domain, context: structuredClone(context), mounts: new Map() };
    this.surfaces.add(surface);
    for (const entry of this.registrations.get(domain) ?? []) this.mount(surface, entry);
    return () => {
      this.surfaces.delete(surface);
      for (const life of surface.mounts.values()) void life.close();
      surface.mounts.clear();
    };
  }
  mount(surface, entry) {
    const life = new Lifetime(this.report);
    surface.mounts.set(entry, life);
    const root = surface.element.ownerDocument.createElement('div');
    root.className = 'gw-api-surface';
    const native = [...surface.element.children].filter(el => !el.classList.contains('gw-api-surface'));
    const hidden = native.map(el => el.hidden);
    if (entry.mode === 'replace') native.forEach(el => { el.hidden = true; });
    surface.element.append(root);
    life.onDispose(() => {
      root.remove();
      if (entry.mode === 'replace') native.forEach((el, i) => { el.hidden = hidden[i]; });
    });
    const api = this.createApi(surface.context, life);
    void life.wait(() => entry.mount({ root, context: Object.freeze({ ...surface.context }), api,
      signal: life.signal, onDispose: life.onDispose })).catch(error => {
      void life.close();
      if (error.code !== 'stale_context') this.report(error);
    });
  }
  close() {
    this.closed = true;
    for (const surface of this.surfaces) for (const life of surface.mounts.values()) void life.close();
    this.surfaces.clear();
    this.registrations.clear();
  }
}
