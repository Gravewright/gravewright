export const MODULE_KINDS = [
  "server", "campaign", "room", "marketplace", "ruleset", "addon", "asset", "ui",
] as const;

export type ModuleKind = (typeof MODULE_KINDS)[number];

export const MODULE_PROVIDERS = [
  "core", "community", "official", "licensed", "partner",
] as const;

export type ModuleProvider = (typeof MODULE_PROVIDERS)[number];
export type ModuleState = "active" | "disabled";

export interface ModuleAPI {
  get: object;
  set: object;
  prop: object;
}

type ExportNames<T> = readonly (keyof T & string)[];

export interface ModuleDefinition<TInstance extends Record<string, unknown>> {
  name: string;
  kind: ModuleKind;
  provider: ModuleProvider;
  version: string;
  manifest_url?: string;
  download_url?: string;
  download_sha256?: string;
  dependencies?: Record<string, string>;
  routes?: Record<string, keyof TInstance & string>;
  middleware?: Record<string, readonly (keyof TInstance & string)[]>;
  slots?: Record<string, readonly (keyof TInstance & string)[]>;
  exports: {
    get?: ExportNames<TInstance>;
    /** @deprecated Prefira comandos explícitos publicados em exports.get. */
    set?: ExportNames<TInstance>;
    prop?: ExportNames<TInstance>;
  };
  create(context: Context): TInstance;
}

export type DefinedModule<
  TDefinition extends ModuleDefinition<Record<string, unknown>> = ModuleDefinition<Record<string, unknown>>,
> = ((context: Context) => ReturnType<TDefinition["create"]>) & { readonly definition: TDefinition };

/** Helper de autoria. O kernel continua validando manifest.json antes de importar esta factory. */
export function defineModule<
  const TDefinition extends ModuleDefinition<Record<string, unknown>>,
>(definition: TDefinition): DefinedModule<TDefinition> {
  const factory = ((context: Context) => definition.create(context)) as DefinedModule<TDefinition>;
  Object.defineProperty(factory, "definition", { value: Object.freeze(definition), enumerable: true });
  return factory;
}

export type InferModuleAPI<T> = T extends DefinedModule<infer TDefinition>
  ? {
      get: Pick<ReturnType<TDefinition["create"]>, Extract<TDefinition["exports"]["get"] extends readonly (infer K)[] ? K : never, keyof ReturnType<TDefinition["create"]>>>;
      set: Pick<ReturnType<TDefinition["create"]>, Extract<TDefinition["exports"]["set"] extends readonly (infer K)[] ? K : never, keyof ReturnType<TDefinition["create"]>>>;
      prop: Pick<ReturnType<TDefinition["create"]>, Extract<TDefinition["exports"]["prop"] extends readonly (infer K)[] ? K : never, keyof ReturnType<TDefinition["create"]>>>;
    }
  : never;

export type Readable<T extends ModuleAPI> = T["get"] & T["prop"];
export type Writable<T extends ModuleAPI> = T["set"] & T["prop"];

export interface ModuleRegistry {
}

export type DiagnosticActionStatus = "success" | "failure";

/** Ação semântica e segura para o diário opt-in iniciado por `grave run --diagnostic`. */
export interface DiagnosticAction {
  event: string;
  actor: string;
  action: string;
  status: DiagnosticActionStatus;
  details?: Record<string, string | number | boolean | null>;
  reason?: string;
}

export interface DiagnosticReporter {
  record(action: DiagnosticAction): void;
}

/** Request neutro de transporte fornecido por um módulo `server`. */
export interface BaseRequest {
  method: string;
  path: string;
  params: Record<string, string>;
  query: Record<string, string | string[] | undefined>;
  body: unknown;
  headers: Readonly<Record<string, string | undefined>>;
}

/** Response neutro de transporte fornecido por um módulo `server`. */
export interface BaseResponse {
  status(code: number): BaseResponse;
  json(value: unknown): void;
  text(value: string): void;
}

export type RouteHandler = (
  request: BaseRequest,
  response: BaseResponse,
) => void | Promise<void>;

export type Dispose = () => void | Promise<void>;
export type RouteRegistrar = (mount: string, handler: RouteHandler) => Dispose;
export type MiddlewareNext = () => void;
export type MiddlewareHandler = (
  request: BaseRequest,
  response: BaseResponse,
  next: MiddlewareNext,
) => void | Promise<void>;
export type MiddlewareRegistrar = (mount: string, handler: MiddlewareHandler) => Dispose;
export type SlotRegistrar = (name: string, value: unknown) => Dispose;

export interface ModuleManifest {
  name: string;
  kind: ModuleKind;
  provider: ModuleProvider;
  version: string;
  entry: string;
  types?: string;
  dependencies?: Record<string, string>;
  routes?: Record<string, string>;
  middleware?: Record<string, string[]>;
  slots?: Record<string, string[]>;
  exports: {
    get?: string[];
    set?: string[];
    prop?: string[];
  };
  manifest_url?: string;
  /** URL HTTPS estável que descreve sempre a release mais recente. */
  download_url?: string;
  /** SHA-256 hexadecimal do ZIP indicado por download_url. */
  download_sha256?: string;
}

export interface ModuleRef<T extends ModuleAPI = {
  get: Record<string, unknown>;
  set: Record<string, unknown>;
  prop: Record<string, unknown>;
}> {
  get<K extends keyof Readable<T> & string>(name: K): Readable<T>[K];
  /** @deprecated Prefira comandos explícitos obtidos por get(). */
  set<K extends keyof Writable<T> & string>(name: K, value: Writable<T>[K]): void;
}

export interface Context<R extends ModuleRegistry = ModuleRegistry> {
  use<K extends keyof R & string>(name: K): ModuleRef<R[K] extends ModuleAPI ? R[K] : never>;
  /** No-op quando o diário de diagnóstico não foi habilitado pelo host. */
  diagnostic: DiagnosticReporter;
}

/** Fallback deliberado para hosts que resolvem módulos desconhecidos em compile time. */
export interface DynamicContext {
  use(name: string): ModuleRef;
}
