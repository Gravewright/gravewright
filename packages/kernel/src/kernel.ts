import { access, readFile, realpath } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import semver from "semver";
import {
  COMMON_MODULE_EXPORTS,
  MODULE_KINDS,
  MODULE_PROVIDERS,
  ROOM_SLOT_NAMES,
  ROOM_PROTOCOL,
  type Context,
  type Dispose,
  type DiagnosticReporter,
  type ModuleKind,
  type ModuleManifest,
  type ModuleRef,
  type ModuleState,
  type SlotExposure,
} from "@gravewright/sdk";

interface ModuleRecord {
  manifest: ModuleManifest;
  module: Record<string, unknown>;
  resources: Dispose[];
}

interface ModuleDefinition {
  manifest: ModuleManifest;
  entryPath: string;
  state: ModuleState;
}

export interface LoadOptions {
  state?: ModuleState;
}

export interface KernelOptions {
  diagnostic?: DiagnosticReporter;
}

export interface ActivationPlan {
  modules: readonly string[];
  capabilities: Readonly<Record<string, string>>;
  routes: Readonly<Record<string, string>>;
  slots: Readonly<Record<string, readonly string[]>>;
}

const REQUIRED_EXPORTS: Partial<Record<ModuleKind, readonly string[]>> = {
  server: [...COMMON_MODULE_EXPORTS, "start", "stop", "route", "middleware", "slot"],
  room: [...COMMON_MODULE_EXPORTS, "mount", "unmount"],
  ruleset: COMMON_MODULE_EXPORTS,
  addon: COMMON_MODULE_EXPORTS,
  system: COMMON_MODULE_EXPORTS,
};

const REQUIRED_KINDS: readonly ModuleKind[] = ["server"];
const SINGLETON_KINDS: readonly ModuleKind[] = ["server"];

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringArray(value: unknown, field: string): string[] | undefined {
  if (value === undefined) return undefined;
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item)) {
    throw new Error(`Invalid manifest: ${field} must be an array of non-empty strings`);
  }
  return value as string[];
}

function versionMap(value: unknown, field: string, ranges: boolean): Record<string, string> | undefined {
  if (value === undefined) return undefined;
  if (!isObject(value)) throw new Error(`Invalid manifest: ${field} must be an object`);
  const result: Record<string, string> = {};
  for (const [name, version] of Object.entries(value)) {
    if (!/^[a-z0-9]+(?:[.-][a-z0-9]+)*$/.test(name) || typeof version !== "string"
      || (ranges ? semver.validRange(version) === null : semver.valid(version) === null)) {
      throw new Error(`Invalid manifest: ${field} '${name}' has invalid ${ranges ? "SemVer range" : "version"} '${String(version)}'`);
    }
    result[name] = version;
  }
  return result;
}

function slotExposures(value: unknown, kind: ModuleKind): { slots: SlotExposure[] } | undefined {
  if (value === undefined) {
    if (kind === "room") throw new Error("Invalid manifest: room must declare exposes.slots");
    return undefined;
  }
  if (!isObject(value) || !Array.isArray(value.slots)) {
    throw new Error("Invalid manifest: exposes.slots must be an array");
  }
  if (kind !== "room") throw new Error("Invalid manifest: only room modules may declare exposes.slots");
  const slots: SlotExposure[] = [];
  const names = new Set<string>();
  for (const item of value.slots) {
    if (!isObject(item) || typeof item.name !== "string" || !/^gw-[a-z0-9]+(?:-[a-z0-9]+)*$/.test(item.name)) {
      throw new Error("Invalid manifest: exposed slot names must use gw-kebab-case");
    }
    if (names.has(item.name)) throw new Error(`Invalid manifest: duplicate exposed slot '${item.name}'`);
    if (item.mounts !== "one") throw new Error(`Invalid manifest: exposed slot '${item.name}' must use mounts "one"`);
    if (item.contributions !== "one" && item.contributions !== "many") {
      throw new Error(`Invalid manifest: exposed slot '${item.name}' has invalid contribution cardinality`);
    }
    names.add(item.name);
    slots.push({ name: item.name, mounts: "one", contributions: item.contributions });
  }
  if (kind === "room") {
    for (const name of ROOM_SLOT_NAMES) {
      const slot = slots.find((candidate) => candidate.name === name);
      if (!slot) throw new Error(`Invalid manifest: room must expose required slot '${name}'`);
      if (slot.contributions !== "many") {
        throw new Error(`Invalid manifest: required room slot '${name}' must accept many contributions`);
      }
    }
  }
  return { slots };
}

function validateManifest(value: unknown): ModuleManifest {
  if (!isObject(value)) throw new Error("Invalid manifest: expected an object");
  for (const field of ["name", "version", "entry"] as const) {
    if (typeof value[field] !== "string" || value[field].length === 0) {
      throw new Error(`Invalid manifest: ${field} must be a non-empty string`);
    }
  }
  if (!MODULE_KINDS.includes(value.kind as ModuleKind)) {
    throw new Error(`Invalid kind: ${String(value.kind)}`);
  }
  if (!MODULE_PROVIDERS.includes(value.provider as ModuleManifest["provider"])) {
    throw new Error(`Invalid provider: ${String(value.provider)}`);
  }
  if (!isObject(value.exports)) throw new Error("Invalid manifest: exports must be an object");
  if (value.exports.set !== undefined || value.exports.prop !== undefined) {
    throw new Error("Invalid manifest: only exports.get is supported");
  }
  if (!semver.valid(value.version as string)) {
    throw new Error(`Invalid manifest: version '${String(value.version)}' is not valid SemVer`);
  }

  let dependencies: Record<string, string> | undefined;
  if (value.dependencies !== undefined) {
    if (!isObject(value.dependencies)) {
      throw new Error("Invalid manifest: dependencies must be an object");
    }
    dependencies = {};
    for (const [name, range] of Object.entries(value.dependencies)) {
      if (!name || typeof range !== "string" || semver.validRange(range) === null) {
        throw new Error(`Invalid manifest: dependency '${name}' has invalid SemVer range '${String(range)}'`);
      }
      dependencies[name] = range;
    }
  }
  const exposes = slotExposures(value.exposes, value.kind as ModuleKind);
  const requires = versionMap(value.requires, "requires", true);
  const provides = versionMap(value.provides, "provides", false);
  if (value.kind === "room" && value.room_protocol !== ROOM_PROTOCOL) {
    throw new Error(`Invalid manifest: room_protocol must be '${ROOM_PROTOCOL}'`);
  }
  if (value.kind !== "room" && value.room_protocol !== undefined) {
    throw new Error("Invalid manifest: only room modules may declare room_protocol");
  }

  let routes: Record<string, string> | undefined;
  if (value.routes !== undefined) {
    if (!isObject(value.routes)) throw new Error("Invalid manifest: routes must be an object");
    routes = {};
    for (const [mount, exportName] of Object.entries(value.routes)) {
      if (!mount) throw new Error("Invalid manifest: route mounts must be non-empty strings");
      if (typeof exportName !== "string" || !exportName) {
        throw new Error(`Invalid manifest: route export for mount '${mount}' must be a non-empty string`);
      }
      routes[mount] = exportName;
    }
  }
  let middleware: Record<string, string[]> | undefined;
  if (value.middleware !== undefined) {
    if (!isObject(value.middleware)) throw new Error("Invalid manifest: middleware must be an object");
    middleware = {};
    for (const [mount, exports] of Object.entries(value.middleware)) {
      if (!mount) throw new Error("Invalid manifest: middleware mounts must be non-empty strings");
      const names = stringArray(exports, `middleware.${mount}`)!;
      if (new Set(names).size !== names.length) {
        throw new Error(`Invalid manifest: middleware mount '${mount}' must not contain duplicate names`);
      }
      middleware[mount] = names;
    }
  }
  let slots: Record<string, string[]> | undefined;
  if (value.slots !== undefined) {
    if (!isObject(value.slots)) throw new Error("Invalid manifest: slots must be an object");
    slots = {};
    for (const [slotName, exports] of Object.entries(value.slots)) {
      if (!slotName) throw new Error("Invalid manifest: slot names must be non-empty strings");
      const names = stringArray(exports, `slots.${slotName}`)!;
      if (new Set(names).size !== names.length) {
        throw new Error(`Invalid manifest: slot '${slotName}' must not contain duplicate names`);
      }
      slots[slotName] = names;
    }
  }

  const manifest = {
    name: value.name,
    kind: value.kind,
    provider: value.provider,
    version: value.version,
    entry: value.entry,
    ...(value.types === undefined ? {} : { types: value.types }),
    ...(dependencies === undefined ? {} : { dependencies }),
    ...(requires === undefined ? {} : { requires }),
    ...(provides === undefined ? {} : { provides }),
    ...(value.room_protocol === undefined ? {} : { room_protocol: value.room_protocol }),
    ...(exposes === undefined ? {} : { exposes }),
    ...(routes === undefined ? {} : { routes }),
    ...(middleware === undefined ? {} : { middleware }),
    ...(slots === undefined ? {} : { slots }),
    exports: {
      get: stringArray(value.exports.get, "exports.get"),
    },
    ...(value.manifest_url === undefined ? {} : { manifest_url: value.manifest_url }),
    ...(value.download_url === undefined ? {} : { download_url: value.download_url }),
    ...(value.download_sha256 === undefined ? {} : { download_sha256: value.download_sha256 }),
  } as ModuleManifest;

  if (manifest.manifest_url !== undefined && typeof manifest.manifest_url !== "string") {
    throw new Error("Invalid manifest: manifest_url must be a string");
  }
  if (manifest.download_url !== undefined && typeof manifest.download_url !== "string") {
    throw new Error("Invalid manifest: download_url must be a string");
  }
  if (manifest.download_sha256 !== undefined && (typeof manifest.download_sha256 !== "string" || !/^[a-f0-9]{64}$/i.test(manifest.download_sha256))) {
    throw new Error("Invalid manifest: download_sha256 must be a hexadecimal SHA-256");
  }
  if (manifest.types !== undefined && (typeof manifest.types !== "string" || !manifest.types)) {
    throw new Error("Invalid manifest: types must be a non-empty string");
  }

  const exported = new Set<string>();
  for (const name of manifest.exports.get ?? []) {
    if (exported.has(name)) {
      throw new Error(`Invalid manifest: duplicate export '${name}' in exports.get`);
    }
    exported.add(name);
  }
  return manifest;
}

export class Kernel {
  readonly #definitions = new Map<string, ModuleDefinition>();
  readonly #modules = new Map<string, ModuleRecord>();
  readonly #diagnostic: DiagnosticReporter;
  readonly #disposers = new Map<string, Dispose[]>();
  readonly #capabilityProviders = new Map<string, string>();
  #moduleOrder: string[] = [];
  #initialized = false;
  #initializing = false;
  #operations = Promise.resolve();

  constructor(options: KernelOptions = {}) {
    this.#diagnostic = options.diagnostic ?? Object.freeze({ record() {} });
  }

  #contextFor(manifest: ModuleManifest, resources: Dispose[]): Context {
    const dependencies = new Set(Object.keys(manifest.dependencies ?? {}));
    const capabilities = new Set(Object.keys(manifest.requires ?? {}));
    return Object.freeze({
      use: (name: string) => {
        if (!dependencies.has(name)) {
          throw new Error(`Module "${manifest.name}" cannot use undeclared dependency "${name}"`);
        }
        return this.use(name);
      },
      capability: (name: string) => {
        if (!capabilities.has(name)) throw new Error(`Module "${manifest.name}" cannot use undeclared capability "${name}"`);
        const provider = this.#capabilityProviders.get(name);
        if (!provider) throw new Error(`Capability "${name}" is not available`);
        return this.use(provider);
      },
      onDispose: (disposer: Dispose) => {
        if (typeof disposer !== "function") throw new TypeError("onDispose requires a function");
        resources.push(disposer);
      },
      diagnostic: this.#diagnostic,
    }) as Context;
  }

  async load(moduleDirectory: string, options: LoadOptions = {}): Promise<void> {
    if (this.#initialized || this.#initializing) throw new Error("Cannot load modules after kernel initialization has started");
    const requestedDirectory = path.resolve(moduleDirectory);
    let directory: string;
    try {
      directory = await realpath(requestedDirectory);
    } catch {
      throw new Error(`Invalid manifest: cannot read ${path.join(requestedDirectory, "manifest.json")}`);
    }
    const requestedManifestPath = path.join(directory, "manifest.json");
    let manifestPath: string;
    let raw: string;
    try {
      manifestPath = await realpath(requestedManifestPath);
      const relativeManifest = path.relative(directory, manifestPath);
      if (relativeManifest.startsWith("..") || path.isAbsolute(relativeManifest)) {
        throw new Error("manifest escapes module directory");
      }
      raw = await readFile(manifestPath, "utf8");
    } catch {
      throw new Error(`Invalid manifest: cannot read ${requestedManifestPath}`);
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      throw new Error(`Invalid manifest: malformed JSON in ${manifestPath}`);
    }
    const manifest = validateManifest(parsed);
    if (this.#definitions.has(manifest.name)) throw new Error(`Duplicate module: ${manifest.name}`);

    const requestedEntryPath = path.resolve(directory, manifest.entry);
    const relativeEntry = path.relative(directory, requestedEntryPath);
    if (relativeEntry.startsWith("..") || path.isAbsolute(relativeEntry)) {
      throw new Error(`Invalid manifest: entry must stay inside the module directory`);
    }
    let entryPath: string;
    try {
      await access(requestedEntryPath);
      entryPath = await realpath(requestedEntryPath);
    } catch {
      throw new Error(`Entry does not exist: ${requestedEntryPath}`);
    }
    const relativeRealEntry = path.relative(directory, entryPath);
    if (relativeRealEntry.startsWith("..") || path.isAbsolute(relativeRealEntry)) {
      throw new Error("Invalid manifest: entry must stay inside the module directory");
    }

    const state = options.state ?? "disabled";
    if (state !== "active" && state !== "disabled") throw new Error(`Invalid module state: ${String(state)}`);
    this.#definitions.set(manifest.name, { manifest, entryPath, state });
  }

  use(name: string): ModuleRef {
    if (!this.#modules.has(name)) throw new Error(`Module "${name}" is not active`);

    const resolve = (): ModuleRecord => {
      const record = this.#modules.get(name);
      if (!record) throw new Error(`Module "${name}" is not active`);
      return record;
    };

    return Object.freeze({
      get<T = unknown>(property: string): T {
        const record = resolve();
        const readable = new Set(record.manifest.exports.get ?? []);
        if (!readable.has(property)) throw new Error(`Get not authorized: ${name}.${property}`);
        return record.module[property] as T;
      },
    });
  }

  async #instantiate(definition: ModuleDefinition): Promise<ModuleRecord> {
    const { manifest, entryPath } = definition;
    const entry: Record<string, unknown> = await import(pathToFileURL(entryPath).href);
    if (typeof entry.default !== "function") throw new Error(`Module entry must default-export a factory: ${manifest.name}`);
    const resources: Dispose[] = [];
    let instance: unknown;
    try {
      instance = await entry.default(this.#contextFor(manifest, resources));
    } catch (error) {
      try { await this.#dispose(resources); }
      catch (cleanup) { throw new AggregateError([error, cleanup], `Creation of "${manifest.name}" failed and cleanup also failed`, { cause: error }); }
      throw error;
    }
    try {
    if (!isObject(instance)) throw new Error(`Module factory must return an object: ${manifest.name}`);

    const names = new Set(manifest.exports.get ?? []);
    for (const name of names) {
      if (!Object.prototype.hasOwnProperty.call(instance, name)) {
        throw new Error(`Declared export does not exist: ${manifest.name}.${name}`);
      }
    }
    const readable = new Set(manifest.exports.get ?? []);
    for (const required of REQUIRED_EXPORTS[manifest.kind] ?? []) {
      if (!readable.has(required)) {
        throw new Error(`Minimum contract not satisfied for ${manifest.kind}: '${required}' must be declared in exports.get`);
      }
      if (typeof instance[required] !== "function") {
        throw new Error(`Minimum contract not satisfied for ${manifest.kind}: '${required}' must be a function`);
      }
    }
    for (const exportName of Object.values(manifest.routes ?? {})) {
      if (!readable.has(exportName)) throw new Error(`Invalid route in ${manifest.name}: '${exportName}' must be declared in exports.get`);
      if (typeof instance[exportName] !== "function") throw new Error(`Invalid route in ${manifest.name}: '${exportName}' must be a function`);
    }
    for (const exportNames of Object.values(manifest.middleware ?? {})) {
      for (const exportName of exportNames) {
        if (!readable.has(exportName)) throw new Error(`Invalid middleware in ${manifest.name}: '${exportName}' must be declared in exports.get`);
        if (typeof instance[exportName] !== "function") throw new Error(`Invalid middleware in ${manifest.name}: '${exportName}' must be a function`);
      }
    }
    for (const [slotName, exportNames] of Object.entries(manifest.slots ?? {})) {
      for (const exportName of exportNames) {
        if (!readable.has(exportName)) throw new Error(`Invalid slot '${slotName}' in ${manifest.name}: '${exportName}' must be declared in exports.get`);
        if (slotName.startsWith("gw-")) {
          const contribution = instance[exportName];
          if (!isObject(contribution) || typeof contribution.id !== "string" || !contribution.id || typeof contribution.mount !== "function") {
            throw new Error(`Invalid visual slot '${slotName}' in ${manifest.name}: '${exportName}' must provide id and mount(container)`);
          }
          if (contribution.order !== undefined && (typeof contribution.order !== "number" || !Number.isFinite(contribution.order))) {
            throw new Error(`Invalid visual slot '${slotName}' in ${manifest.name}: '${exportName}' has an invalid order`);
          }
        }
      }
    }
    return { manifest, module: instance, resources };
    } catch (error) {
      try { await this.#dispose(resources); }
      catch (cleanup) { throw new AggregateError([error, cleanup], `Validation of "${manifest.name}" failed and cleanup also failed`, { cause: error }); }
      throw error;
    }
  }

  #serverRef(): ModuleRef {
    const server = [...this.#definitions.values()].find(({ manifest, state }) => manifest.kind === "server" && state === "active");
    if (!server) throw new Error("Missing active module for required kind \"server\"");
    return this.use(server.manifest.name);
  }

  #composeMiddleware(record: ModuleRecord, server: ModuleRef, disposers: Dispose[]): void {
    const register = server.get("middleware") as (mount: string, handler: (...args: unknown[]) => unknown) => Dispose;
    const ref = this.use(record.manifest.name);
    for (const [mount, exportNames] of Object.entries(record.manifest.middleware ?? {})) {
      for (const exportName of exportNames) {
        const dispose = register(mount, ref.get(exportName) as (...args: unknown[]) => unknown);
        if (typeof dispose !== "function") throw new Error(`Base middleware registrar did not return a disposer for ${record.manifest.name}.${exportName}`);
        disposers.push(dispose);
      }
    }
  }

  #composeRoutes(record: ModuleRecord, server: ModuleRef, disposers: Dispose[]): void {
    const register = server.get("route") as (mount: string, handler: (...args: unknown[]) => unknown) => Dispose;
    const ref = this.use(record.manifest.name);
    for (const [mount, exportName] of Object.entries(record.manifest.routes ?? {})) {
      const dispose = register(mount, ref.get(exportName) as (...args: unknown[]) => unknown);
      if (typeof dispose !== "function") throw new Error(`Base route registrar did not return a disposer for ${record.manifest.name}.${exportName}`);
      disposers.push(dispose);
    }
  }

  #composeSlots(record: ModuleRecord, server: ModuleRef, disposers: Dispose[]): void {
    const register = server.get("slot") as (name: string, value: unknown) => Dispose;
    const ref = this.use(record.manifest.name);
    for (const [slotName, exportNames] of Object.entries(record.manifest.slots ?? {})) {
      for (const exportName of exportNames) {
        const dispose = register(slotName, ref.get(exportName));
        if (typeof dispose !== "function") throw new Error(`Base slot registrar did not return a disposer for ${record.manifest.name}.${exportName}`);
        disposers.push(dispose);
      }
    }
  }

  async #dispose(disposers: Dispose[]): Promise<void> {
    const errors: unknown[] = [];
    for (const dispose of [...disposers].reverse()) {
      try { await dispose(); } catch (error) { errors.push(error); }
    }
    if (errors.length === 1) throw errors[0];
    if (errors.length > 1) throw new AggregateError(errors, "Multiple composition disposers failed");
  }

  async #releaseModule(name: string): Promise<void> {
    const errors: unknown[] = [];
    try { await this.#dispose(this.#disposers.get(name) ?? []); } catch (error) { errors.push(error); }
    try { await this.#dispose(this.#modules.get(name)?.resources ?? []); } catch (error) { errors.push(error); }
    if (errors.length === 1) throw errors[0];
    if (errors.length > 1) throw new AggregateError(errors, `Multiple disposers failed for module "${name}"`);
  }

  plan(): ActivationPlan {
    const active = new Map([...this.#definitions].filter(([, definition]) => definition.state === "active"));
    for (const { manifest } of active.values()) {
      for (const [dependencyName, range] of Object.entries(manifest.dependencies ?? {})) {
        if (dependencyName === manifest.name) throw new Error(`Module "${manifest.name}" cannot depend on itself`);
        const dependency = this.#definitions.get(dependencyName);
        if (!dependency) throw new Error(`Module "${manifest.name}" requires missing dependency "${dependencyName}"`);
        if (dependency.state === "disabled") throw new Error(`Module "${manifest.name}" requires dependency "${dependencyName}", but "${dependencyName}" is disabled`);
        if (!semver.satisfies(dependency.manifest.version, range)) throw new Error(`Module "${manifest.name}" requires "${dependencyName}" ${range}, but ${dependency.manifest.version} is loaded`);
      }
    }
    const capabilities: Record<string, string> = {};
    const capabilityVersions = new Map<string, string>();
    for (const { manifest } of active.values()) for (const [name, version] of Object.entries(manifest.provides ?? {})) {
      if (capabilities[name]) throw new Error(`Capability "${name}" has multiple active providers: ${capabilities[name]}, ${manifest.name}`);
      capabilities[name] = manifest.name;
      capabilityVersions.set(name, version);
    }
    for (const { manifest } of active.values()) for (const [name, range] of Object.entries(manifest.requires ?? {})) {
      const version = capabilityVersions.get(name);
      if (!version) throw new Error(`Module "${manifest.name}" requires missing capability "${name}"`);
      if (!semver.satisfies(version, range)) throw new Error(`Module "${manifest.name}" requires capability "${name}" ${range}, but ${version} is provided`);
    }
    const routes: Record<string, string> = {};
    for (const { manifest } of active.values()) for (const mount of Object.keys(manifest.routes ?? {})) {
      if (routes[mount]) throw new Error(`Route conflict at ${JSON.stringify(mount)} between ${routes[mount]} and ${manifest.name}`);
      routes[mount] = manifest.name;
    }
    const visualSlots = new Map<string, "one" | "many">();
    for (const { manifest } of active.values()) for (const exposure of manifest.exposes?.slots ?? []) {
      const previous = visualSlots.get(exposure.name);
      if (previous && previous !== exposure.contributions) throw new Error(`Room slot '${exposure.name}' has incompatible contribution cardinality`);
      visualSlots.set(exposure.name, exposure.contributions);
    }
    const contributionCounts = new Map<string, number>();
    const slots: Record<string, string[]> = {};
    for (const { manifest } of active.values()) for (const [slot, exports] of Object.entries(manifest.slots ?? {})) {
      slots[slot] ??= [];
      slots[slot].push(...exports.map((name) => `${manifest.name}.${name}`));
      if (!slot.startsWith("gw-")) continue;
      if (!visualSlots.has(slot)) throw new Error(`Module "${manifest.name}" contributes to unknown room slot '${slot}'`);
      contributionCounts.set(slot, (contributionCounts.get(slot) ?? 0) + exports.length);
    }
    for (const [slot, count] of contributionCounts) if (visualSlots.get(slot) === "one" && count > 1) throw new Error(`Room slot '${slot}' accepts only one contribution`);
    const order: ModuleDefinition[] = [];
    const complete = new Set<string>(); const visiting = new Set<string>(); const trail: string[] = [];
    const visit = (name: string): void => {
      if (complete.has(name)) return;
      if (visiting.has(name)) { const start = trail.indexOf(name); throw new Error(`Circular dependency detected: ${[...trail.slice(start), name].join(" -> ")}`); }
      visiting.add(name); trail.push(name);
      const definition = active.get(name)!;
      for (const dependency of Object.keys(definition.manifest.dependencies ?? {})) visit(dependency);
      for (const capability of Object.keys(definition.manifest.requires ?? {})) visit(capabilities[capability]!);
      trail.pop(); visiting.delete(name); complete.add(name); order.push(definition);
    };
    for (const name of active.keys()) visit(name);
    const available = new Set([...active.values()].map(({ manifest }) => manifest.kind));
    const missing = REQUIRED_KINDS.filter((kind) => !available.has(kind));
    if (missing.length) throw new Error(`Missing active module for required kind "${missing.join("\", \"")}"`);
    for (const kind of SINGLETON_KINDS) {
      const implementations = [...active.values()].filter(({ manifest }) => manifest.kind === kind);
      if (implementations.length > 1) throw new Error(`Multiple active modules implement singleton kind "${kind}": ${implementations.map(({ manifest }) => manifest.name).join(", ")}`);
    }
    const frozenSlots = Object.fromEntries(Object.entries(slots).map(([name, values]) => [name, Object.freeze(values)]));
    return Object.freeze({ modules: Object.freeze(order.map(({ manifest }) => manifest.name)), capabilities: Object.freeze(capabilities), routes: Object.freeze(routes), slots: Object.freeze(frozenSlots) });
  }

  async initialize(): Promise<void> {
    if (this.#initialized || this.#initializing) throw new Error("Kernel already initialized or initializing");
    const plan = this.plan();
    const order = plan.modules.map((name) => this.#definitions.get(name)!);
    this.#capabilityProviders.clear();
    for (const [name, provider] of Object.entries(plan.capabilities)) this.#capabilityProviders.set(name, provider);
    const servers = order.filter(({ manifest }) => manifest.kind === "server");

    this.#initializing = true;
    try {
      this.#modules.clear();
      this.#moduleOrder = [];
      for (const definition of order) {
        const record = await this.#instantiate(definition);
        this.#modules.set(record.manifest.name, record);
        this.#moduleOrder.push(record.manifest.name);
      }
      const serverName = servers[0]!.manifest.name;
      const server = this.use(serverName);
      for (const record of this.#modules.values()) {
        const disposers: Dispose[] = [];
        this.#composeMiddleware(record, server, disposers);
        this.#disposers.set(record.manifest.name, disposers);
      }
      for (const record of this.#modules.values()) this.#composeRoutes(record, server, this.#disposers.get(record.manifest.name)!);
      for (const record of this.#modules.values()) this.#composeSlots(record, server, this.#disposers.get(record.manifest.name)!);
      const start = server.get("start");
      await (start as () => void | Promise<void>)();
      this.#initialized = true;
    } catch (error) {
      const cleanupErrors: unknown[] = [];
      const serverRecord = this.#modules.get(servers[0]?.manifest.name ?? "");
      if (serverRecord && typeof serverRecord.module.stop === "function") {
        try { await (serverRecord.module.stop as () => void | Promise<void>)(); } catch (cleanupError) { cleanupErrors.push(cleanupError); }
      }
      for (const disposers of [...this.#disposers.values()].reverse()) {
        try { await this.#dispose(disposers); } catch (cleanupError) { cleanupErrors.push(cleanupError); }
      }
      for (const name of [...this.#moduleOrder].reverse()) {
        try { await this.#dispose(this.#modules.get(name)?.resources ?? []); } catch (cleanupError) { cleanupErrors.push(cleanupError); }
      }
      this.#disposers.clear();
      this.#modules.clear();
      this.#moduleOrder = [];
      if (cleanupErrors.length) {
        throw new AggregateError([error, ...cleanupErrors], "Kernel initialization failed and cleanup also failed", { cause: error });
      }
      throw error;
    } finally {
      this.#initializing = false;
    }
  }

  #enqueue(operation: () => Promise<void>): Promise<void> {
    const result = this.#operations.then(operation, operation);
    this.#operations = result.then(() => undefined, () => undefined);
    return result;
  }

  activate(name: string): Promise<void> {
    return this.#enqueue(() => this.#activate(name));
  }

  async #activate(name: string): Promise<void> {
    if (!this.#initialized) throw new Error("Cannot activate modules before kernel initialization");
    const definition = this.#definitions.get(name);
    if (!definition) throw new Error(`Module not found: ${name}`);
    if (definition.state === "active") return;
    if (definition.manifest.kind === "server") throw new Error("Cannot activate another server while the kernel is running");
    if ((SINGLETON_KINDS as readonly ModuleKind[]).includes(definition.manifest.kind)) {
      const active = [...this.#definitions.values()].find(({ manifest, state }) =>
        state === "active" && manifest.kind === definition.manifest.kind,
      );
      if (active) throw new Error(`Cannot activate "${name}": singleton kind "${definition.manifest.kind}" is already implemented by "${active.manifest.name}"`);
    }
    for (const [dependencyName, range] of Object.entries(definition.manifest.dependencies ?? {})) {
      const dependency = this.#definitions.get(dependencyName);
      if (!dependency) throw new Error(`Module "${name}" requires missing dependency "${dependencyName}"`);
      if (dependency.state === "disabled") {
        throw new Error(`Module "${name}" requires dependency "${dependencyName}", but "${dependencyName}" is disabled`);
      }
      if (!semver.satisfies(dependency.manifest.version, range)) {
        throw new Error(`Module "${name}" requires "${dependencyName}" ${range}, but ${dependency.manifest.version} is loaded`);
      }
    }

    definition.state = "active";
    let plan: ActivationPlan;
    try { plan = this.plan(); } catch (error) { definition.state = "disabled"; throw error; }
    this.#capabilityProviders.clear();
    for (const [capability, provider] of Object.entries(plan.capabilities)) this.#capabilityProviders.set(capability, provider);
    const disposers: Dispose[] = [];
    let record: ModuleRecord | undefined;
    try {
      record = await this.#instantiate(definition);
      this.#modules.set(name, record);
      const server = this.#serverRef();
      this.#composeMiddleware(record, server, disposers);
      this.#composeRoutes(record, server, disposers);
      this.#composeSlots(record, server, disposers);
      this.#disposers.set(name, disposers);
      this.#moduleOrder.push(name);
    } catch (error) {
      let cleanupError: unknown;
      try { await this.#dispose(disposers); } catch (caught) { cleanupError = caught; }
      this.#disposers.delete(name);
      this.#modules.delete(name);
      if (record) { try { await this.#dispose(record.resources); } catch (caught) { cleanupError = cleanupError ? new AggregateError([cleanupError, caught]) : caught; } }
      definition.state = "disabled";
      const restored = this.plan();
      this.#capabilityProviders.clear();
      for (const [capability, provider] of Object.entries(restored.capabilities)) this.#capabilityProviders.set(capability, provider);
      if (cleanupError !== undefined) {
        throw new AggregateError([error, cleanupError], `Activation of "${name}" failed and cleanup also failed`, { cause: error });
      }
      throw error;
    }
  }

  disable(name: string): Promise<void> {
    return this.#enqueue(() => this.#disable(name));
  }

  async #disable(name: string): Promise<void> {
    if (!this.#initialized) throw new Error("Cannot disable modules before kernel initialization");
    const definition = this.#definitions.get(name);
    if (!definition) throw new Error(`Module not found: ${name}`);
    if (definition.state === "disabled") return;
    if (definition.manifest.kind === "server") throw new Error("Cannot disable the active server while the kernel is running");

    const dependent = [...this.#definitions.values()].find(({ manifest, state }) =>
      state === "active" && Object.prototype.hasOwnProperty.call(manifest.dependencies ?? {}, name),
    );
    if (dependent) throw new Error(`Cannot disable "${name}": active module "${dependent.manifest.name}" depends on it`);
    for (const capability of Object.keys(definition.manifest.provides ?? {})) {
      const consumer = [...this.#definitions.values()].find(({ manifest, state }) => state === "active" && manifest.name !== name && Object.prototype.hasOwnProperty.call(manifest.requires ?? {}, capability));
      if (consumer) throw new Error(`Cannot disable "${name}": active module "${consumer.manifest.name}" requires capability "${capability}"`);
    }

    if ((REQUIRED_KINDS as readonly ModuleKind[]).includes(definition.manifest.kind)) {
      const activeOfKind = [...this.#definitions.values()].filter(({ manifest, state }) =>
        state === "active" && manifest.kind === definition.manifest.kind,
      );
      if (activeOfKind.length === 1) {
        throw new Error(`Cannot disable "${name}": it is the last active module for required kind "${definition.manifest.kind}"`);
      }
    }

    definition.state = "disabled";
    let plan: ActivationPlan;
    try { plan = this.plan(); } catch (error) { definition.state = "active"; throw error; }
    try { await this.#releaseModule(name); }
    catch (error) { definition.state = "active"; throw error; }
    this.#disposers.delete(name);
    this.#modules.delete(name);
    this.#moduleOrder = this.#moduleOrder.filter((moduleName) => moduleName !== name);
    this.#capabilityProviders.clear();
    for (const [capability, provider] of Object.entries(plan.capabilities)) this.#capabilityProviders.set(capability, provider);
  }

  shutdown(): Promise<void> {
    return this.#enqueue(async () => {
      if (!this.#initialized) return;
      const errors: unknown[] = [];
      try {
        const stop = this.#serverRef().get("stop") as () => void | Promise<void>;
        await stop();
      } catch (error) { errors.push(error); }
      for (const name of [...this.#moduleOrder].reverse()) {
        try { await this.#releaseModule(name); } catch (error) { errors.push(error); }
      }
      this.#disposers.clear(); this.#modules.clear(); this.#moduleOrder = [];
      this.#capabilityProviders.clear(); this.#initialized = false;
      if (errors.length === 1) throw errors[0];
      if (errors.length > 1) throw new AggregateError(errors, "Kernel shutdown completed with errors");
    });
  }
}
