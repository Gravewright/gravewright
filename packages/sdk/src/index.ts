/** Supported roles that a Gravewright module can implement. */
export const MODULE_KINDS = [
  "server", "frontend", "backend", "module",
] as const;

/** Identifies the role a module plays in a Gravewright composition. */
export type ModuleKind = (typeof MODULE_KINDS)[number];

/** Supported provenance classifications for module distribution. */
export const MODULE_PROVIDERS = [
  "core", "community", "official", "licensed", "partner",
] as const;

/** Describes the declared provenance of a module. */
export type ModuleProvider = (typeof MODULE_PROVIDERS)[number];
/** Controls whether an installed module participates in the active composition. */
export type ModuleState = "active" | "disabled";

/** Structural roles for which a composition requires exactly one active implementation. */
export type SingletonModuleKind = "server" | "frontend" | "backend";
/** Extensible role for which a composition may contain any number of implementations. */
export type PluralModuleKind = "module";

/** Minimum public exports required from each structural implementation. */
export const STRUCTURAL_EXPORTS = Object.freeze({
  server: ["start", "stop", "http", "route", "middleware"],
  frontend: ["start", "stop"],
  backend: ["start", "stop"],
} as const);

/** Shape used by the typed registry to describe a module's readable API. */
export interface ModuleAPI {
  get: object;
}

type ExportNames<T> = readonly (keyof T & string)[];

/** Authoring definition consumed by {@link defineModule}. */
export interface ModuleDefinition<TInstance extends Record<string, unknown>> {
  name: string;
  kind: ModuleKind;
  provider: ModuleProvider;
  version: string;
  /** Comma-separated discovery tags using lowercase kebab-case identifiers. */
  tags?: string;
  manifest_url?: string;
  download_url?: string;
  download_sha256?: string;
  dependencies?: Record<string, string>;
  tooling?: ModuleTooling;
  exports: { get?: ExportNames<TInstance> };
  create(context: Context): TInstance | Promise<TInstance>;
}

/** Factory returned by {@link defineModule}, including its build-time metadata. */
export type DefinedModule<
  TDefinition extends ModuleDefinition<Record<string, unknown>> = ModuleDefinition<Record<string, unknown>>,
> = ((context: Context) => ReturnType<TDefinition["create"]>) & { readonly definition: TDefinition };

/**
 * Creates a typed module factory and attaches immutable build metadata.
 * The kernel still validates `manifest.json` before importing this factory.
 */
export function defineModule<const TDefinition extends ModuleDefinition<Record<string, unknown>>>(
  definition: TDefinition & ContractDefinition<TDefinition["kind"]>,
): DefinedModule<TDefinition> {
  const factory = ((context: Context) => definition.create(context)) as DefinedModule<TDefinition>;
  Object.defineProperty(factory, "definition", { value: Object.freeze(definition), enumerable: true });
  return factory;
}

/** Derives the public API declared by a module definition. */
export type InferModuleAPI<T> = T extends DefinedModule<infer TDefinition>
  ? {
      get: Pick<Awaited<ReturnType<TDefinition["create"]>>, Extract<TDefinition["exports"]["get"] extends readonly (infer K)[] ? K : never, keyof Awaited<ReturnType<TDefinition["create"]>>>>;
    }
  : never;

/** Registry augmented by generated module type declarations. */
export interface ModuleRegistry {
}

/** Outcome recorded for a diagnostic action. */
export type DiagnosticActionStatus = "success" | "failure";

/** A semantic action accepted by the opt-in diagnostic journal. */
export interface DiagnosticAction {
  event: string;
  actor: string;
  action: string;
  status: DiagnosticActionStatus;
  details?: Record<string, string | number | boolean | null>;
  reason?: string;
}

/** Receives sanitized semantic diagnostic actions from modules. */
export interface DiagnosticReporter {
  record(action: DiagnosticAction): void;
}

/** Transport-neutral request provided by a `server` implementation. */
export interface BaseRequest {
  method: string;
  path: string;
  params: Record<string, string>;
  query: Record<string, string | string[] | undefined>;
  body: unknown;
  headers: Readonly<Record<string, string | undefined>>;
}

/** Transport-neutral response provided by a `server` implementation. */
export interface BaseResponse {
  status(code: number): BaseResponse;
  json(value: unknown): void;
  text(value: string): void;
}

/** Handles one transport-neutral route request. */
export type RouteHandler = (
  request: BaseRequest,
  response: BaseResponse,
) => void | Promise<void>;

/** Releases a resource owned by a module; it may complete asynchronously. */
export type Dispose = () => void | Promise<void>;
/** Registers a route and returns the function that removes it. */
export type RouteRegistrar = (mount: string, handler: RouteHandler) => Dispose;
/** Handles completion of middleware registered by a server implementation. */
export type MiddlewareNext = () => void;
/** Handles one transport-neutral middleware request. */
export type MiddlewareHandler = (
  request: BaseRequest,
  response: BaseResponse,
  next: MiddlewareNext,
) => void | Promise<void>;
/** Registers middleware and returns the function that removes it. */
export type MiddlewareRegistrar = (mount: string, handler: MiddlewareHandler) => Dispose;
/** Describes a browser contribution mounted into a named frontend slot. */
export interface FrontendSlotContribution {
  id: string;
  order?: number;
  mount(container: HTMLElement): void | Dispose | Promise<void | Dispose>;
}
/** Registers a browser contribution under a named frontend slot. */
export type FrontendSlotRegistrar = (name: string, module: string, contribution: FrontendSlotContribution) => Dispose;

/** Browser-side interface implemented by the frontend client bundle. */
export interface ClientFrontend {
  mount(root: HTMLElement): void | Promise<void>;
  unmount(): void | Promise<void>;
  slot: FrontendSlotRegistrar;
}

/** Transport-neutral envelope delivered by a server's realtime adapter. */
export interface ServerMessage {
  type: string;
  payload: unknown;
}

/** Sends transport-neutral realtime messages to supported audiences. */
export interface ServerRealtime {
  toRoom(roomId: string, message: ServerMessage): void | Promise<void>;
  toGM(roomId: string, message: ServerMessage): void | Promise<void>;
  toWhisper(userId: string, message: ServerMessage): void | Promise<void>;
}

/** Minimum runtime surface implemented by a server module. */
export interface ServerContract { start: () => void | Promise<void>; stop: () => void | Promise<void>; http: unknown; route: RouteRegistrar; middleware: MiddlewareRegistrar; realtime?: ServerRealtime }
/** Node-side lifecycle used by the host to make the frontend bundle available. */
export interface FrontendContract { start: () => void | Promise<void>; stop: () => void | Promise<void> }
/** Minimum lifecycle implemented by a backend module. */
export interface BackendContract { start: () => void | Promise<void>; stop: () => void | Promise<void> }
/** Maps a module kind to the minimum instance contract enforced for that kind. */
export type ContractDefinition<K extends ModuleKind> = K extends "server"
  ? { create(context: Context): (Record<string, unknown> & ServerContract) | Promise<Record<string, unknown> & ServerContract> }
  : K extends "frontend"
    ? { create(context: Context): (Record<string, unknown> & FrontendContract) | Promise<Record<string, unknown> & FrontendContract> }
    : K extends "backend"
      ? { create(context: Context): (Record<string, unknown> & BackendContract) | Promise<Record<string, unknown> & BackendContract> }
      : object;
/** Optional administrative operations exposed separately from product exports. */
export interface ModuleTooling { read?: boolean; write?: boolean; stat?: boolean }

/** Validated on-disk description of an installed module. */
export interface ModuleManifest {
  name: string;
  kind: ModuleKind;
  provider: ModuleProvider;
  version: string;
  /** Comma-separated discovery tags using lowercase kebab-case identifiers. */
  tags?: string;
  entry: string;
  types?: string;
  dependencies?: Record<string, string>;
  tooling?: ModuleTooling;
  exports: {
    get?: string[];
  };
  manifest_url?: string;
  /** Stable HTTPS URL that always describes the latest release. */
  download_url?: string;
  /** Hexadecimal SHA-256 digest of the archive identified by `download_url`. */
  download_sha256?: string;
}

/** Read-only handle to a module's declared public exports. */
export interface ModuleRef<T extends ModuleAPI = { get: Record<string, unknown> }> {
  get<K extends keyof T["get"] & string>(name: K): T["get"][K];
}

/** Restricted services supplied to a module factory by the kernel. */
export interface Context<R extends ModuleRegistry = ModuleRegistry> {
  use<K extends keyof R & string>(name: K): ModuleRef<R[K] extends ModuleAPI ? R[K] : never>;
  onDispose(disposer: Dispose): void;
  /** No-op reporter when the host has not enabled diagnostic journaling. */
  diagnostic: DiagnosticReporter;
}

/** Deliberate fallback for hosts whose modules are unknown at compile time. */
export interface DynamicContext {
  use(name: string): ModuleRef;
  onDispose(disposer: Dispose): void;
  /** No-op reporter when the host has not enabled diagnostic journaling. */
  diagnostic: DiagnosticReporter;
}
