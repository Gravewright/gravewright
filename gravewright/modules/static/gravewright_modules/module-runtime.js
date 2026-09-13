import { DOMAIN_NAMES } from "./generated.js";
import { Lifetime, ModuleError, boundedCleanup } from "./lifetime.js";
/**
 * Own signed-package activations and their visual mounts. Imports run in the
 * main page, without JavaScript isolation; the bridge enforces server contexts.
 * Lifecycle declarations are synchronous, while start/mount/stop may await work.
 */
class ModuleRuntime {
  constructor(bridge, report = console.error, importer = (url) => import(
    /* @vite-ignore */
    url
  ), domains = DOMAIN_NAMES) {
    this.bridge = bridge;
    this.report = report;
    this.importer = importer;
    this.domains = domains;
  }
  bridge;
  report;
  importer;
  domains;
  active = [];
  declarations = [];
  surfaces = /* @__PURE__ */ new Map();
  state;
  queue = Promise.resolve();
  closed = false;
  generation = 0;
  canCustomize(id) {
    return this.active.some(module => module.descriptor.id === id && !module.life.signal.aborted && typeof module.api.customize === "function");
  }
  async customize(id) {
    const module = this.active.find(module => module.descriptor.id === id);
    if (!module || !this.canCustomize(id)) throw new ModuleError("stale_context");
    return module.life.wait(() => module.api.customize(module.context));
  }
  serial(job) {
    const next = this.queue.then(job);
    this.queue = next.catch(this.report);
    return next;
  }
  invalidate() {
    for (const active of this.active) void active.life.close();
    for (const lives of this.surfaces.values()) for (const life of lives) void life.close();
  }
  reconcile(state) {
    // Invalidate immediately, before queued teardown can await module cleanups.
    const generation = ++this.generation;
    for (const active of this.active) void active.life.close();
    for (const lives of this.surfaces.values()) for (const life of lives) void life.close();
    return this.serial(async () => {
      if (this.closed || generation !== this.generation) throw new ModuleError("stale_context");
      await this.stopAll();
      this.state = structuredClone(state);
      try {
        for (const descriptor of state.modules) {
          const life = new Lifetime(this.report);
          let active;
          try {
            const base = new URL(descriptor.baseUrl, location.origin);
            if (base.origin !== location.origin || !base.pathname.startsWith("/api/module-packages/")) throw new ModuleError("invalid_data", "Invalid package URL");
            const url = new URL(descriptor.entry, base);
            if (!url.href.startsWith(base.href) || url.search || url.hash) throw new ModuleError("invalid_data");
            const { default: candidate } = await this.importer(url.href);
            if (this.closed || generation !== this.generation) throw new ModuleError("stale_context");
            if (!candidate || typeof candidate !== "object" || !["start", "register", "stop"].every((k) => typeof candidate[k] === "function") || "execute" in candidate) throw new ModuleError("invalid_data", "Expected start/register/stop lifecycle");
            const api = candidate;
            const identity = { moduleId: descriptor.id, tableId: state.tableId, moduleSetRevision: state.moduleSetRevision, mountId: crypto.randomUUID() };
            const context = this.bridge.context(descriptor, identity, life);
            active = { descriptor, api, life, context };
            this.active.push(active);
            await life.wait(async () => api.start(context));
            let registering = true;
            const registration = { register: (domain, value) => {
              life.check();
              if (!registering || !this.domains.includes(domain)) throw new ModuleError("invalid_data", "Unknown domain or late registration");
              const declaration = typeof value === "function" ? { mode: "augment", mount: value } : value;
              if (!declaration || !["augment", "replace"].includes(declaration.mode ?? "augment") || typeof declaration.mount !== "function") throw new ModuleError("invalid_data");
              if (this.declarations.some((d) => d.module === active && d.domain === domain)) throw new ModuleError("conflict", "Duplicate domain registration");
              this.declarations.push({ module: active, domain, ...declaration, mode: declaration.mode ?? "augment" });
            } };
            try {
              const result = api.register({ ...registration, api: this.bridge.api?.(identity, life, { register: registration.register }) });
              if (result && typeof result.then === "function") {
                Promise.resolve(result).catch(this.report);
                throw new ModuleError("invalid_data", "register must be synchronous");
              }
            } finally {
              registering = false;
            }
          } catch (error) {
            await life.close();
            throw error;
          }
        }
        for (const surface of this.surfaces.keys()) await this.mountSurface(surface);
        await this.bridge.acknowledge(state.moduleSetRevision);
      } catch (error) {
        await this.stopAll();
        for (const surface of this.surfaces.keys()) await surface.defaultVisible(true);
        throw error;
      }
    });
  }
  attach(surface) {
    if (this.closed) throw new ModuleError("stale_context");
    this.surfaces.set(surface, []);
    void this.serial(async () => {
      if (this.surfaces.has(surface)) await this.mountSurface(surface);
    });
    return () => {
      const lives = this.surfaces.get(surface) ?? [];
      this.surfaces.delete(surface);
      for (const life of lives) void life.close();
    };
  }
  async mountSurface(surface) {
    const old = this.surfaces.get(surface);
    if (!old) return;
    await Promise.all(old.map((life) => life.close()));
    const lives = [];
    this.surfaces.set(surface, lives);
    const candidates = this.declarations.filter((d) => d.domain === surface.domain && d.mode === "replace");
    // Competing replacements need a table choice; augmentations always remain.
    const preference = this.state?.replacements[surface.domain];
    const selected = candidates.length === 1 ? candidates[0] : candidates.find((d) => d.module.descriptor.id === preference);
    await surface.defaultVisible(!selected);
    for (const declaration of this.declarations.filter((d) => d.domain === surface.domain && (d.mode === "augment" || d === selected))) {
      if (!this.surfaces.has(surface)) return;
      const life = new Lifetime(this.report);
      lives.push(life);
      const root = (surface.root.ownerDocument ?? document).createElement("div");
      root.className = "gw-module-root";
      root.dataset.moduleId = declaration.module.descriptor.id;
      surface.root.append(root);
      life.onDispose(() => root.remove());
      const unlink = declaration.module.life.link(() => life.close());
      life.onDispose(unlink);
      const identity = { moduleId: declaration.module.descriptor.id, tableId: this.state.tableId, moduleSetRevision: this.state.moduleSetRevision, mountId: crypto.randomUUID(), ..."sceneId" in surface.context ? { sceneId: surface.context.sceneId } : {} };
      const context = freezeContext({ ...structuredClone(surface.context), role: this.state?.role ?? "player", mountId: identity.mountId, moduleSetRevision: identity.moduleSetRevision });
      const block = {
        ...this.bridge.context(declaration.module.descriptor, identity, life),
        root,
        context,
        viewport: surface.viewport ? {
          sceneToViewport: (point) => {
            life.check();
            return surface.viewport.sceneToViewport(validPoint(point));
          },
          viewportToScene: (point) => {
            life.check();
            return surface.viewport.viewportToScene(validPoint(point));
          }
        } : void 0,
        host: this.bridge.host(identity, life),
        events: this.bridge.events(identity, life)
      };
      block.api = this.bridge.api?.(identity, life);
      try {
        await life.wait(async () => declaration.mount(block));
      } catch (error) {
        await life.close();
        this.report(error);
        if (declaration === selected) await surface.defaultVisible(true);
      }
    }
  }
  async stopAll() {
    for (const lives of this.surfaces.values()) await Promise.all(lives.map((life) => life.close()));
    this.declarations = [];
    for (const active of this.active.splice(0).reverse()) {
      await active.life.close();
      try {
        await boundedCleanup(Promise.resolve(active.api.stop(active.context)));
      } catch (error) {
        this.report(error);
      }
    }
  }
  close() {
    this.closed = true;
    ++this.generation;
    for (const active of this.active) void active.life.close();
    for (const lives of this.surfaces.values()) for (const life of lives) void life.close();
    return this.serial(async () => {
      await this.stopAll();
      this.surfaces.clear();
    });
  }
}
function freezeContext(value) {
  if (value && typeof value === "object") {
    for (const child of Object.values(value)) freezeContext(child);
    Object.freeze(value);
  }
  return value;
}
function validPoint(point) {
  if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) throw new ModuleError("invalid_data");
  return point;
}
export {
  ModuleRuntime
};
