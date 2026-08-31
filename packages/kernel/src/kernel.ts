import { access, readFile, realpath } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import semver from "semver";
import { createActivationPlan, REQUIRED_KINDS, SINGLETON_KINDS } from "./graph/plan.js";
import { disposeAll } from "./lifecycle.js";
import { isObject, validateManifest } from "./manifest/validate.js";
import type { ActivationPlan, ModuleDefinition, ModuleRecord } from "./types.js";
import {
  COMMON_MODULE_EXPORTS,
  type Context,
  type Dispose,
  type DiagnosticReporter,
  type ModuleKind,
  type ModuleManifest,
  type ModuleRef,
  type ModuleState,
} from "@gravewright/sdk";

export interface LoadOptions {
  state?: ModuleState;
}

export interface KernelOptions {
  diagnostic?: DiagnosticReporter;
}

export type { ActivationPlan } from "./types.js";

const REQUIRED_EXPORTS: Partial<Record<ModuleKind, readonly string[]>> = {
  server: [...COMMON_MODULE_EXPORTS, "start", "stop", "route", "middleware", "slot"],
  room: [...COMMON_MODULE_EXPORTS, "mount", "unmount"],
  ruleset: COMMON_MODULE_EXPORTS,
  addon: COMMON_MODULE_EXPORTS,
  system: COMMON_MODULE_EXPORTS,
};

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
    await disposeAll(disposers);
  }

  async #releaseModule(name: string): Promise<void> {
    const errors: unknown[] = [];
    try { await this.#dispose(this.#disposers.get(name) ?? []); } catch (error) { errors.push(error); }
    try { await this.#dispose(this.#modules.get(name)?.resources ?? []); } catch (error) { errors.push(error); }
    if (errors.length === 1) throw errors[0];
    if (errors.length > 1) throw new AggregateError(errors, `Multiple disposers failed for module "${name}"`);
  }

  plan(): ActivationPlan {
    return createActivationPlan(this.#definitions.values());
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
    this.#capabilityProviders.clear();
    for (const [capability, provider] of Object.entries(plan.capabilities)) this.#capabilityProviders.set(capability, provider);
    let cleanupError: unknown;
    try { await this.#releaseModule(name); }
    catch (error) { cleanupError = error; }
    finally {
      this.#disposers.delete(name);
      this.#modules.delete(name);
      this.#moduleOrder = this.#moduleOrder.filter((moduleName) => moduleName !== name);
    }
    if (cleanupError !== undefined) throw cleanupError;
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
