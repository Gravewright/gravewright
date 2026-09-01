export const MODULE_KINDS = [
  "server", "room", "ruleset", "chat", "dice-engine", "assets", "storage", "backend", "addon",
] as const;

export type ModuleKind = (typeof MODULE_KINDS)[number];

export const MODULE_PROVIDERS = [
  "core", "community", "official", "licensed", "partner",
] as const;

export type ModuleProvider = (typeof MODULE_PROVIDERS)[number];
export type ModuleState = "active" | "disabled";

export type KindUse = "required" | "optional";
export type SingletonModuleKind = "server" | "room" | "ruleset" | "chat" | "dice-engine" | "assets" | "storage";
export type PluralModuleKind = "backend" | "addon";

export const ROOM_SLOT_NAMES = [
  "gw-toolbar", "gw-main", "gw-sidebar", "gw-chat", "gw-overlay", "gw-grid",
] as const;

export const ROOM_PROTOCOL = "gravewright.room/v1" as const;

export type RoomSlotName = (typeof ROOM_SLOT_NAMES)[number];
export type SlotMountCardinality = "one";
export type SlotContributionCardinality = "one" | "many";

export interface RoomSlotContract {
  name: RoomSlotName;
  description: string;
  multiplicity: "multiple";
  ordering: "ordered";
}

export const ROOM_SLOT_CONTRACTS: readonly RoomSlotContract[] = Object.freeze([
  { name: "gw-toolbar", description: "Primary and contextual actions", multiplicity: "multiple", ordering: "ordered" },
  { name: "gw-main", description: "Primary room content", multiplicity: "multiple", ordering: "ordered" },
  { name: "gw-sidebar", description: "Secondary contextual content", multiplicity: "multiple", ordering: "ordered" },
  { name: "gw-chat", description: "Conversation and message interfaces", multiplicity: "multiple", ordering: "ordered" },
  { name: "gw-overlay", description: "Content layered above the room", multiplicity: "multiple", ordering: "ordered" },
  { name: "gw-grid", description: "Tabletop and spatial content", multiplicity: "multiple", ordering: "ordered" },
]);

export interface SlotExposure {
  name: string;
  mounts: SlotMountCardinality;
  contributions: SlotContributionCardinality;
}

export interface SlotContribution {
  id: string;
  order?: number;
  mount(container: HTMLElement): void | Dispose | Promise<void | Dispose>;
}

export interface ResolvedSlotContribution {
  module: string;
  slot: string;
  contribution: SlotContribution;
}

/** Mounts visual contributions only after the room has rendered its declared regions. */
export async function composeRoomSlots(
  root: HTMLElement,
  exposures: readonly SlotExposure[],
  entries: readonly ResolvedSlotContribution[],
): Promise<Dispose> {
  const targets = new Map<string, HTMLElement>();
  for (const exposure of exposures) {
    const matches = root.querySelectorAll<HTMLElement>(`.${exposure.name}`);
    if (matches.length !== 1) {
      throw new Error(`Room slot '${exposure.name}' must render exactly once; found ${matches.length}`);
    }
    targets.set(exposure.name, matches[0]!);
  }
  for (const name of ROOM_SLOT_NAMES) {
    if (!targets.has(name)) throw new Error(`Room does not expose required slot '${name}'`);
  }

  const ordered = [...entries].sort((left, right) =>
    left.slot.localeCompare(right.slot)
    || (left.contribution.order ?? 0) - (right.contribution.order ?? 0)
    || left.module.localeCompare(right.module)
    || left.contribution.id.localeCompare(right.contribution.id));
  const seen = new Set<string>();
  const mounted: Array<{ child: HTMLElement; dispose?: Dispose }> = [];
  try {
    for (const entry of ordered) {
      const exposure = exposures.find(({ name }) => name === entry.slot);
      const target = targets.get(entry.slot);
      if (!exposure || !target) throw new Error(`Contribution targets unknown room slot '${entry.slot}'`);
      if (!entry.contribution.id) throw new Error(`Contribution from '${entry.module}' must have an id`);
      if (entry.contribution.order !== undefined && !Number.isFinite(entry.contribution.order)) {
        throw new Error(`Contribution '${entry.module}/${entry.contribution.id}' has an invalid order`);
      }
      const key = `${entry.slot}\0${entry.module}\0${entry.contribution.id}`;
      if (seen.has(key)) throw new Error(`Duplicate slot contribution '${entry.module}/${entry.contribution.id}'`);
      seen.add(key);
      if (exposure.contributions === "one" && mounted.some(({ child }) => child.dataset.gwSlot === entry.slot)) {
        throw new Error(`Room slot '${entry.slot}' accepts only one contribution`);
      }
      const child = root.ownerDocument.createElement("div");
      child.dataset.gwSlot = entry.slot;
      child.dataset.gwModule = entry.module;
      child.dataset.gwContribution = entry.contribution.id;
      target.append(child);
      const mountedEntry: { child: HTMLElement; dispose?: Dispose } = { child };
      mounted.push(mountedEntry);
      const dispose = await entry.contribution.mount(child);
      if (typeof dispose === "function") mountedEntry.dispose = dispose;
    }
  } catch (error) {
    for (const item of mounted.reverse()) { try { await item.dispose?.(); } finally { item.child.remove(); } }
    throw error;
  }
  return async () => {
    const errors: unknown[] = [];
    for (const item of mounted.reverse()) {
      try { await item.dispose?.(); } catch (error) { errors.push(error); }
      item.child.remove();
    }
    if (errors.length === 1) throw errors[0];
    if (errors.length > 1) throw new AggregateError(errors, "Multiple room slot contributions failed to unmount");
  };
}

export interface ModuleAPI {
  get: object;
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
  uses?: Partial<Record<ModuleKind, KindUse>>;
  requires?: Record<string, string>;
  provides?: Record<string, string>;
  room_protocol?: typeof ROOM_PROTOCOL;
  exposes?: { slots?: readonly SlotExposure[] };
  routes?: Record<string, keyof TInstance & string>;
  middleware?: Record<string, readonly (keyof TInstance & string)[]>;
  slots?: Record<string, readonly (keyof TInstance & string)[]>;
  tooling?: ModuleTooling;
  exports: { get?: ExportNames<TInstance> };
  create(context: Context): TInstance | Promise<TInstance>;
}

export type DefinedModule<
  TDefinition extends ModuleDefinition<Record<string, unknown>> = ModuleDefinition<Record<string, unknown>>,
> = ((context: Context) => ReturnType<TDefinition["create"]>) & { readonly definition: TDefinition };

/** Helper de autoria. O kernel continua validando manifest.json antes de importar esta factory. */
export function defineModule<
  const TKind extends ModuleKind,
  const TDefinition extends ModuleDefinition<Record<string, unknown>>,
>(definition: TDefinition & {
  kind: TKind;
  create(context: Context): (Record<string, unknown> & KindRegistry[TKind]["get"]) | Promise<Record<string, unknown> & KindRegistry[TKind]["get"]>;
}): DefinedModule<TDefinition> {
  const factory = ((context: Context) => definition.create(context)) as DefinedModule<TDefinition>;
  Object.defineProperty(factory, "definition", { value: Object.freeze(definition), enumerable: true });
  return factory;
}

export type InferModuleAPI<T> = T extends DefinedModule<infer TDefinition>
  ? {
      get: Pick<Awaited<ReturnType<TDefinition["create"]>>, Extract<TDefinition["exports"]["get"] extends readonly (infer K)[] ? K : never, keyof Awaited<ReturnType<TDefinition["create"]>>>>;
    }
  : never;

export interface ModuleRegistry {
}

/** Capability contracts are augmented by protocol packages, independently of providers. */
export interface CapabilityRegistry {
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
export type RoomSlotRegistrar = (name: string, module: string, value: unknown) => Dispose;

export interface ServerKindAPI extends ModuleAPI { get: { start: () => void | Promise<void>; stop: () => void | Promise<void>; http: unknown; route: RouteRegistrar; middleware: MiddlewareRegistrar; realtime?: unknown } }
export interface RoomKindAPI extends ModuleAPI { get: { mount: (root: HTMLElement) => unknown; unmount: () => unknown; slots: RoomSlotRegistrar } }
export interface RulesetKindAPI extends ModuleAPI { get: Record<string, unknown> }
export interface ChatKindAPI extends ModuleAPI { get: { send: (message: string) => string | Promise<string>; erase: (messageId: string) => void | Promise<void> } }
export interface DiceEngineKindAPI extends ModuleAPI { get: { roll: (expression: string) => number | Promise<number> } }
export interface AssetInput { data: Uint8Array; mimeType: string; name?: string }
export interface AssetsKindAPI extends ModuleAPI { get: { store: (asset: AssetInput) => string | Promise<string>; resolve: (id: string) => Uint8Array | undefined | Promise<Uint8Array | undefined>; mimeTypeAllowed: (mimeType: string) => boolean | Promise<boolean>; remove: (id: string) => void | Promise<void> } }
export interface StorageKindAPI extends ModuleAPI { get: { create: (collection: string, value: unknown) => unknown | Promise<unknown>; find: (collection: string, id: string) => unknown | Promise<unknown>; where: (collection: string, filters: Record<string, unknown>) => unknown[] | Promise<unknown[]>; update: (collection: string, id: string, value: unknown) => unknown | Promise<unknown>; delete: (collection: string, id: string) => void | Promise<void> } }
export interface BackendKindAPI extends ModuleAPI { get: Record<string, unknown> }
export interface AddonKindAPI extends ModuleAPI { get: Record<string, unknown> }
export interface KindRegistry { server: ServerKindAPI; room: RoomKindAPI; ruleset: RulesetKindAPI; chat: ChatKindAPI; "dice-engine": DiceEngineKindAPI; assets: AssetsKindAPI; storage: StorageKindAPI; backend: BackendKindAPI; addon: AddonKindAPI }
export interface ModuleTooling { read?: boolean; write?: boolean; stat?: boolean }

export interface ModuleManifest {
  name: string;
  kind: ModuleKind;
  provider: ModuleProvider;
  version: string;
  entry: string;
  types?: string;
  dependencies?: Record<string, string>;
  uses?: Partial<Record<ModuleKind, KindUse>>;
  requires?: Record<string, string>;
  provides?: Record<string, string>;
  room_protocol?: typeof ROOM_PROTOCOL;
  exposes?: { slots?: SlotExposure[] };
  routes?: Record<string, string>;
  middleware?: Record<string, string[]>;
  slots?: Record<string, string[]>;
  tooling?: ModuleTooling;
  exports: {
    get?: string[];
  };
  manifest_url?: string;
  /** URL HTTPS estável que descreve sempre a release mais recente. */
  download_url?: string;
  /** SHA-256 hexadecimal do ZIP indicado por download_url. */
  download_sha256?: string;
}

export interface ModuleRef<T extends ModuleAPI = { get: Record<string, unknown> }> {
  get<K extends keyof T["get"] & string>(name: K): T["get"][K];
}

export type KindResolution<K extends ModuleKind> = K extends PluralModuleKind
  ? readonly ModuleRef<KindRegistry[K]>[]
  : K extends "server"
    ? ModuleRef<KindRegistry[K]>
    : ModuleRef<KindRegistry[K]> | undefined;

export interface Context<R extends ModuleRegistry = ModuleRegistry, C extends CapabilityRegistry = CapabilityRegistry> {
  use<K extends keyof R & string>(name: K): ModuleRef<R[K] extends ModuleAPI ? R[K] : never>;
  kind<K extends ModuleKind>(kind: K): KindResolution<K>;
  capability<K extends keyof C & string>(name: K): ModuleRef<C[K] extends ModuleAPI ? C[K] : never>;
  onDispose(disposer: Dispose): void;
  /** No-op quando o diário de diagnóstico não foi habilitado pelo host. */
  diagnostic: DiagnosticReporter;
}

/** Fallback deliberado para hosts que resolvem módulos desconhecidos em compile time. */
export interface DynamicContext {
  use(name: string): ModuleRef;
  kind<K extends ModuleKind>(kind: K): KindResolution<K>;
  capability(name: string): ModuleRef;
  onDispose(disposer: Dispose): void;
  /** No-op quando o diário de diagnóstico não foi habilitado pelo host. */
  diagnostic: DiagnosticReporter;
}
