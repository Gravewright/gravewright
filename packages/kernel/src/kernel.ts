import { access, readFile, realpath } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { createActivationPlan } from "./graph/plan.js";
import { disposeAll } from "./lifecycle.js";
import { isObject, validateManifest } from "./manifest/validate.js";
import type { ActivationPlan, ModuleDefinition, ModuleRecord } from "./types.js";
import {
  type Context,
  type Dispose,
  type DiagnosticReporter,
  type ModuleManifest,
  type ModuleRef,
  type ModuleState,
  STRUCTURAL_EXPORTS,
} from "@gravewright/sdk";

/** Options applied while registering a module definition with the kernel. */
export interface LoadOptions {
  state?: ModuleState;
}

/** Host-provided services used by a kernel instance. */
export interface KernelOptions {
  diagnostic?: DiagnosticReporter;
}

export type { ActivationPlan } from "./types.js";

const FUNCTION_EXPORTS = new Set(["start", "stop", "route", "middleware"]);

/**
 * Validates, instantiates, coordinates, and disposes one Gravewright composition.
 * Structural modules are fixed for a lifecycle; ordinary modules may change at runtime.
 */
export class Kernel {
  readonly #definitions = new Map<string, ModuleDefinition>();
  readonly #modules = new Map<string, ModuleRecord>();
  readonly #diagnostic: DiagnosticReporter;
  #moduleOrder: string[] = [];
  #initialized = false;
  #initializing = false;
  #operations = Promise.resolve();

  constructor(options: KernelOptions = {}) {
    this.#diagnostic = options.diagnostic ?? Object.freeze({ record() {} });
  }

  #contextFor(manifest: ModuleManifest, resources: Dispose[]): Context {
    const dependencies = new Set(Object.keys(manifest.dependencies ?? {}));
    return Object.freeze({
      use: (name: string) => {
        if (!dependencies.has(name)) {
          throw new Error(`Module "${manifest.name}" cannot use undeclared dependency "${name}"`);
        }
        return this.#reference(name, manifest.name);
      },
      onDispose: (disposer: Dispose) => {
        if (typeof disposer !== "function") throw new TypeError("onDispose requires a function");
        resources.push(disposer);
      },
      diagnostic: this.#diagnostic,
    }) as Context;
  }

  /** Registers and validates a module without executing its factory. */
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

  #reference(name: string, consumer?: string): ModuleRef {
    if (!this.#modules.has(name)) {
      throw new Error(consumer
        ? `Module "${consumer}" cannot use dependency "${name}": dependency is not active`
        : `Module "${name}" is not active`);
    }

    const resolve = (): ModuleRecord => {
      const record = this.#modules.get(name);
      if (!record) throw new Error(consumer
        ? `Module "${consumer}" cannot use dependency "${name}": dependency is not active`
        : `Module "${name}" is not active`);
      return record;
    };

    return Object.freeze({
      get<T = unknown>(property: string): T {
        const record = resolve();
        const readable = new Set(record.manifest.exports.get ?? []);
        if (!readable.has(property)) {
          const publicExports = [...readable].sort();
          throw new Error([
            `Module "${consumer ?? "<host>"}" cannot access export "${property}" from module "${name}".`,
            `Requested export: ${property}`,
            `Public exports: ${publicExports.length ? publicExports.join(", ") : "(none)"}`,
          ].join("\n"));
        }
        return record.module[property] as T;
      },
    });
  }

  /** Resolves a public reference to an active module. */
  use(name: string): ModuleRef {
    return this.#reference(name);
  }

  /** Invokes an administrative operation explicitly enabled by a module manifest. */
  async tooling(name: string, operation: "read" | "write" | "stat", ...args: unknown[]): Promise<unknown> {
    const record = this.#modules.get(name);
    if (!record) throw new Error(`Module "${name}" is not active`);
    if (record.manifest.tooling?.[operation] !== true) throw new Error(`Tooling operation not declared: ${name}.${operation}`);
    return (record.module[operation] as (...values: unknown[]) => unknown)(...args);
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
    const structuralExports = manifest.kind === "module" ? [] : STRUCTURAL_EXPORTS[manifest.kind];
    for (const required of structuralExports) {
      if (!readable.has(required)) {
        throw new Error(`Minimum contract not satisfied for ${manifest.kind}: '${required}' must be declared in exports.get`);
      }
      if (FUNCTION_EXPORTS.has(required) && typeof instance[required] !== "function") {
        throw new Error(`Minimum contract not satisfied for ${manifest.kind}: '${required}' must be a function`);
      }
    }
    for (const operation of Object.keys(manifest.tooling ?? {})) if (typeof instance[operation] !== "function") {
      throw new Error(`Declared tooling operation does not exist: ${manifest.name}.${operation}`);
    }
    if (manifest.kind === "server" && readable.has("realtime")) {
      const realtime = instance.realtime;
      if (!isObject(realtime) || ["toRoom", "toGM", "toWhisper"].some((name) => typeof realtime[name] !== "function")) {
        throw new Error(`Minimum contract not satisfied for server: optional 'realtime' must provide toRoom, toGM and toWhisper`);
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

  async #dispose(disposers: Dispose[]): Promise<void> {
    await disposeAll(disposers);
  }

  async #releaseModule(name: string): Promise<void> {
    await this.#dispose(this.#modules.get(name)?.resources ?? []);
  }

  /** Validates the active composition and returns dependency-safe module order. */
  plan(): ActivationPlan {
    return createActivationPlan(this.#definitions.values());
  }

  /** Instantiates active modules and starts backend, frontend, then server. */
  async initialize(): Promise<void> {
    if (this.#initialized || this.#initializing) throw new Error("Kernel already initialized or initializing");
    const plan = this.plan();
    const order = plan.modules.map((name) => this.#definitions.get(name)!);
    const servers = order.filter(({ manifest }) => manifest.kind === "server");
    const frontends = order.filter(({ manifest }) => manifest.kind === "frontend");
    const backends = order.filter(({ manifest }) => manifest.kind === "backend");
    let backendStarted = false;
    let frontendStarted = false;
    let serverStartAttempted = false;

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
      await (this.use(backends[0]!.manifest.name).get("start") as () => void | Promise<void>)();
      backendStarted = true;
      await (this.use(frontends[0]!.manifest.name).get("start") as () => void | Promise<void>)();
      frontendStarted = true;
      const start = server.get("start");
      serverStartAttempted = true;
      await (start as () => void | Promise<void>)();
      this.#initialized = true;
    } catch (error) {
      const cleanupErrors: unknown[] = [];
      const serverRecord = this.#modules.get(servers[0]?.manifest.name ?? "");
      if (serverStartAttempted && serverRecord && typeof serverRecord.module.stop === "function") {
        try { await (serverRecord.module.stop as () => void | Promise<void>)(); } catch (cleanupError) { cleanupErrors.push(cleanupError); }
      }
      const frontendRecord = this.#modules.get(frontends[0]?.manifest.name ?? "");
      if (frontendStarted && frontendRecord && typeof frontendRecord.module.stop === "function") {
        try { await (frontendRecord.module.stop as () => void | Promise<void>)(); } catch (cleanupError) { cleanupErrors.push(cleanupError); }
      }
      const backendRecord = this.#modules.get(backends[0]?.manifest.name ?? "");
      if (backendStarted && backendRecord && typeof backendRecord.module.stop === "function") {
        try { await (backendRecord.module.stop as () => void | Promise<void>)(); } catch (cleanupError) { cleanupErrors.push(cleanupError); }
      }
      for (const name of [...this.#moduleOrder].reverse()) {
        try { await this.#dispose(this.#modules.get(name)?.resources ?? []); } catch (cleanupError) { cleanupErrors.push(cleanupError); }
      }
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

  /** Activates an ordinary module after initialization. */
  activate(name: string): Promise<void> {
    return this.#enqueue(() => this.#activate(name));
  }

  async #activate(name: string): Promise<void> {
    if (!this.#initialized) throw new Error("Cannot activate modules before kernel initialization");
    const definition = this.#definitions.get(name);
    if (!definition) throw new Error(`Module not found: ${name}`);
    if (definition.manifest.kind !== "module") {
      throw new Error(`Structural implementation "${name}" cannot be activated at runtime. Restart with a different composition instead.`);
    }
    if (definition.state === "active") return;
    definition.state = "active";
    try { this.plan(); } catch (error) { definition.state = "disabled"; throw error; }
    try {
      const record = await this.#instantiate(definition);
      this.#modules.set(name, record);
      this.#moduleOrder.push(name);
    } catch (error) {
      this.#modules.delete(name);
      definition.state = "disabled";
      this.plan();
      throw error;
    }
  }

  /** Disables an ordinary module when no active module depends on it. */
  disable(name: string): Promise<void> {
    return this.#enqueue(() => this.#disable(name));
  }

  async #disable(name: string): Promise<void> {
    if (!this.#initialized) throw new Error("Cannot disable modules before kernel initialization");
    const definition = this.#definitions.get(name);
    if (!definition) throw new Error(`Module not found: ${name}`);
    if (definition.manifest.kind !== "module") {
      throw new Error(`Structural implementation "${name}" cannot be disabled at runtime. Restart with a different composition instead.`);
    }
    if (definition.state === "disabled") return;

    const dependent = [...this.#definitions.values()].find(({ manifest, state }) =>
      state === "active" && Object.prototype.hasOwnProperty.call(manifest.dependencies ?? {}, name),
    );
    if (dependent) throw new Error(`Cannot disable "${name}": active module "${dependent.manifest.name}" depends on it`);
    definition.state = "disabled";
    try { this.plan(); } catch (error) { definition.state = "active"; throw error; }
    let cleanupError: unknown;
    try { await this.#releaseModule(name); }
    catch (error) { cleanupError = error; }
    finally {
      this.#modules.delete(name);
      this.#moduleOrder = this.#moduleOrder.filter((moduleName) => moduleName !== name);
    }
    if (cleanupError !== undefined) throw cleanupError;
  }

  /** Stops structural modules and disposes all resources in reverse order. */
  shutdown(): Promise<void> {
    return this.#enqueue(async () => {
      if (!this.#initialized) return;
      const errors: unknown[] = [];
      try {
        const stop = this.#serverRef().get("stop") as () => void | Promise<void>;
        await stop();
      } catch (error) { errors.push(error); }
      try {
        const frontend = [...this.#definitions.values()].find(({ manifest, state }) => manifest.kind === "frontend" && state === "active");
        if (frontend) await (this.use(frontend.manifest.name).get("stop") as () => void | Promise<void>)();
      } catch (error) { errors.push(error); }
      try {
        const backend = [...this.#definitions.values()].find(({ manifest, state }) => manifest.kind === "backend" && state === "active");
        if (backend) await (this.use(backend.manifest.name).get("stop") as () => void | Promise<void>)();
      } catch (error) { errors.push(error); }
      for (const name of [...this.#moduleOrder].reverse()) {
        try { await this.#releaseModule(name); } catch (error) { errors.push(error); }
      }
      this.#modules.clear(); this.#moduleOrder = [];
      this.#initialized = false;
      if (errors.length === 1) throw errors[0];
      if (errors.length > 1) throw new AggregateError(errors, "Kernel shutdown completed with errors");
    });
  }
}
