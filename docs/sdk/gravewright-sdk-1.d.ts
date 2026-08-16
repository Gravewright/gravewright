// Generated SDK 1 declarations. JavaScript remains the runtime requirement.
type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };
export type CardMetadata = JsonObject;
export type CardMetadataSchema = JsonObject;

export type Disposer = () => void;
export type SdkEventName = string;
export type SdkEvent = Readonly<{ type: SdkEventName; version: number; resourceId?: string; sceneId?: string }>;
export type SdkEventHandler = (event: SdkEvent) => void;
export type InteropPayload = JsonValue;
export type InteropHandler = (payload: InteropPayload, context: InteropProviderContext) => InteropPayload | Promise<InteropPayload>;
export type InteropSubscriber = (payload: InteropPayload) => void;
export type BusResponse = { ok: true; value: InteropPayload } | { ok: false; error: { code: string; message: string } };
export type CommandHandler = (payload: CommandPayload) => void | Promise<void>;
export type SettingValue = string | number | boolean | null | string[];
export type SettingScope = 'client' | 'campaign' | 'package';
export type SettingChangeHandler = (change: SettingChangeDTO) => void;
export type SlotRenderCallback = (host: HTMLElement, context: SdkContextDTO) => void;
export type CampaignContext = JsonObject;
export type SceneContext = JsonObject;
export type UserContext = JsonObject;
export type PermissionContext = JsonObject;
export type RulesetSheetData = JsonObject;
export type RulesetItemCopyFields = JsonObject;
export type ActionInput = JsonObject;
export type ChatMetadata = JsonObject;
export type RulesetCombatResources = JsonObject;
export type RulesetEffectMutation = JsonObject;
export type CombatPlugin = JsonObject;
export type CombatProtocolPayload = JsonObject;
export type CombatPanelDefinition = JsonObject;
export type ContentResolvedValue = ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO;
export type JournalView = JsonObject;
export type CardRuntimeDTO = JsonObject;
export type DeckRuntimeDTO = JsonObject;
export type JournalDataInput = JsonObject;
export type ActionInputSchema = JsonObject;
export type PdfViewerHostState = JsonObject;
export type PdfViewerOpenResult = PdfDocumentDTO & PdfViewerHostState & { page: number };
export type PdfSearchMatch = JsonObject;
export type ParticleParameterSchemas = JsonObject;
export type SceneImageMetadata = JsonObject;
export type FogOp = { mode: 'reveal' | 'hide'; shape: 'circle'; geom: { center_x_cells: number; center_y_cells: number; radius_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'square'; geom: { center_x_cells: number; center_y_cells: number; size_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'polygon'; geom: { points_cells: [number, number][] } };
export type RollOptions = JsonObject;
export type RollMetadata = JsonObject;
export type RollAppliedMutation = JsonObject;
export type StorageParams = JsonObject;
export type StorageRow = JsonObject;
export type SettingValues = { [key: string]: SettingValue };
export type CardArtworkMap = { [cardId: string]: string };
export type ApplicationContext = JsonObject;
export type ApplicationParts = { [partId: string]: ((context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>) | { render: (context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>; activate?: (root: HTMLElement, context: ApplicationContext) => Disposer | void } };
export type SheetPlugin = JsonObject;
export type SheetControllerContext = JsonObject;
export type ContentPackEntryData = JsonObject;
export type TokenOverrides = JsonObject;
export type PackageLifecyclePayload = JsonObject;
export type CommandPayload = JsonValue;
export type SheetValue = JsonValue;
export type SheetHttpResult = JsonValue;
export type SheetHelpers = { el: (tag: string, attributes?: JsonObject, ...children: (Node | string)[]) => HTMLElement; phIcon: (name: string) => HTMLElement; getPath: (value: JsonObject, path: string) => SheetValue | undefined; formatMod: (value: number) => string; cssIdent: (value: string) => string; nonEmptyParts: (...parts: string[]) => string[]; closeFloatingSheetMenus: () => void; postJSON: (url: string, payload: JsonObject) => Promise<SheetHttpResult>; refresh: (root: HTMLElement) => Promise<void>; getContext: (root: HTMLElement) => SheetControllerContext | undefined; getLabels: (systemId: string) => JsonObject };
export type ActorItemCopyDTO = { id: string; sourceItemId: string } & RulesetItemCopyFields;

export interface ActorDTO {
  id: string;
  campaign_id: string;
  system_id: string;
  type: string;
  name: string;
  folder_id: string | null;
  portrait_asset_id: string | null;
  token_asset_id: string | null;
  version: number;
  created_at: number;
  updated_at: number;
}

export interface ItemDTO {
  id: string;
  campaign_id: string;
  system_id: string;
  type: string;
  name: string;
  folder_id: string | null;
  portrait_asset_id: string | null;
  version: number;
  created_at: number;
  updated_at: number;
}

export interface SceneDTO {
  id: string;
  campaign_id: string;
  name: string;
  width: number;
  height: number;
  version: number;
  scene_epoch: number;
  tile_table_version: number;
  grid_size: number;
  raster_tile_size: number;
  chunk_span: number;
  grid_visible: boolean;
  grid_color: string;
  grid_opacity: number;
  darkness: number;
  start_world_x: number;
  start_world_y: number;
  start_zoom: number;
}

export interface WallDTO {
  id: string;
  scene_id: string;
  kind: string;
  door_state: string | null;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  presentation: string | null;
  discovered: boolean;
  behavior: GeometryBehaviorDTO;
  vertical: VerticalBoundsDTO;
  updated_at: number;
}

export interface LightDTO {
  id: string;
  scene_id: string;
  x: number;
  y: number;
  elevation: number;
  bright_radius: number;
  dim_radius: number;
  color: string;
  intensity: number;
  animation: string;
  angle: number;
  rotation: number;
  enabled: boolean;
  updated_at: number;
}

export interface TokenDTO {
  id: string;
  scene_id: string;
  actor_id: string | null;
  grid_x: number;
  grid_y: number;
  elevation: number;
  width_cells: number;
  height_cells: number;
  rotation: number;
  name: string | null;
  token_asset_url: string | null;
  visible: boolean;
  hidden: boolean;
  locked: boolean;
  disposition: string;
  vision: TokenVisionDTO;
  updated_at: number;
}

export interface GeometryBehaviorDTO {
  movement: 'block' | 'pass';
  vision: 'block' | 'pass';
  light: 'block' | 'pass';
}

export interface VerticalBoundsDTO {
  bottom: number | null;
  top: number | null;
}

export interface TokenVisionDTO {
  enabled: boolean;
  range: number | null;
  source: 'token';
}

export interface ShaderPresetDTO {
  id: string;
  schemaVersion: number;
  labelKey: string;
  descriptionKey: string;
  parameters: ShaderPresetParametersDTO;
}

export interface ShaderInstanceDTO {
  id: string;
  sceneId: string;
  presetId: string;
  schemaVersion: number;
  version: number;
  parameters: ShaderParameterValues;
}

export interface DeclaredCardArtworkDTO {
  kind: 'campaign-asset-slot';
}

export interface DeclaredCardDTO {
  id: string;
  label: string;
  quantity: number;
  tags: string[];
  metadata: CardMetadata;
  artwork: DeclaredCardArtworkDTO;
}

export interface CardDefinitionDTO {
  id: string;
  packageId: string;
  version: number;
  reference: string;
  label: string;
  description: string;
  metadataSchema: CardMetadataSchema;
  tags: string[];
  cards: DeclaredCardDTO[];
}

export interface AutomationJobDTO {
  id: string;
  package_id: string;
  action_id: string;
  action_version: number;
  run_at_utc: number;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'rejected' | 'cancelled';
  attempts: number;
  error_code: string | null;
  causal_depth: number;
  created_at: number;
  updated_at: number;
}

export interface AutomationAuditDTO {
  schemaVersion: 1;
  transition: string;
  jobId: string | null;
  campaignId: string;
  packageId: string;
  actionRef: string;
  attempt: number;
  timestamp: number;
  semanticReason?: string;
}

export interface AutomationScheduleOptions {
  version: number;
  runAtUtc: number;
  idempotencyKey: string;
  originExecutionId?: string;
  originJobId?: string;
  causalDepth?: number;
}

export interface AutomationCancelResult {
  id: string;
  status: 'cancelled';
}

export interface AssetDTO {
  id: string;
  campaign_id: string;
  owner_user_id: string;
  folder_id: string | null;
  filename: string;
  content_type: string;
  byte_size: number;
  width: number | null;
  height: number | null;
  created_at: number;
  src: string;
  kind: 'image' | 'pdf';
}

export interface AssetListOptions {
  campaignId?: string;
  kind?: 'image' | 'pdf';
}

export interface AssetOperationDTO {
  status: 'ready';
  progress?: 'ready';
  cancelled?: boolean;
}

export interface AssetIngestResult {
  operation: AssetOperationDTO;
  asset: AssetDTO;
  deduplicated: boolean;
}

export interface AssetCancelResult {
  operation: AssetOperationDTO;
  assetId: string;
}

export interface PackageDTO {
  id: string;
  kind: string;
  version: string;
  active: true;
  interop: PackageInteropDTO;
}

export interface PackageInteropDTO {
  emits?: string[];
  listens?: string[];
  provides?: string[];
  requires?: string[];
}

export interface PermissionCheckDTO {
  action: string;
  supported: boolean;
  allowed: boolean;
  reason: 'ALLOWED' | 'DENIED' | 'UNKNOWN_ACTION';
}

export interface ChatMessageDTO {
  id: string;
  campaign_id: string;
  author_user_id: string;
  author_name: string;
  author_role: string;
  kind: string;
  content: string;
  expression: string | null;
  groups: RollGroupDTO[] | null;
  modifier: number | null;
  total: number | null;
  visibility: string;
  metadata: ChatMetadata;
  created_at: number;
}

export interface RollGroupDTO {
  faces: number;
  results: number[];
  subtotal: number;
}

export interface WorldPointDTO {
  x: number;
  y: number;
}

export interface MeasurementResultDTO {
  sceneId: string;
  from: WorldPointDTO;
  to: WorldPointDTO;
  worldDistance: number;
  gridDistance: number | null;
  gridSize: number | null;
}

export interface SharedMeasurementGeometry {
  points: WorldPointDTO[];
}

export interface SharedMeasurementOptions {
  audience?: 'self' | 'campaign' | 'gm';
  ttlSeconds?: number;
}

export interface SharedMeasurementDTO {
  id: string;
  creator: string;
  sceneId: string;
  geometry: SharedMeasurementGeometry;
  audience: 'self' | 'campaign' | 'gm';
  expiresAt: number;
  version: number;
}

export interface PdfPresentationStartInput {
  audience: string[];
  page: number;
  ttlSeconds?: number;
}

export interface ChatListOptions {
  limit?: number;
}

export interface PermissionResource {
  actorId?: string;
  itemId?: string;
  tokenId?: string;
  sceneId?: string;
  id?: string;
}

export interface WallCreateInput {
  kind?: 'wall' | 'door';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  behavior?: GeometryBehaviorDTO;
  presentation?: string;
  vertical?: VerticalBoundsDTO;
}

export interface WallUpdatePatch {
  kind?: 'wall' | 'door';
  door_state?: string | null;
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  behavior?: GeometryBehaviorDTO;
  presentation?: string;
  discovered?: boolean;
  vertical?: VerticalBoundsDTO;
}

export interface WallResult {
  wall: WallDTO;
}

export interface WallsResult {
  scene_id: string;
  walls: WallDTO[];
}

export interface WallDeleteResult {
  wall_id: string;
  scene_id: string;
}

export interface WallsDeleteResult {
  wall_ids: string[];
  scene_id: string | null;
}

export interface LightCreateInput {
  x: number;
  y: number;
  elevation?: number;
  bright_radius?: number;
  dim_radius?: number;
  color?: string;
  intensity?: number;
  animation?: string;
  angle?: number;
  rotation?: number;
  enabled?: boolean;
}

export interface LightUpdatePatch {
  x?: number;
  y?: number;
  elevation?: number;
  bright_radius?: number;
  dim_radius?: number;
  color?: string;
  intensity?: number;
  animation?: string;
  angle?: number;
  rotation?: number;
  enabled?: boolean;
}

export interface LightResult {
  light: LightDTO;
}

export interface LightDeleteResult {
  light_id: string;
  scene_id: string;
}

export interface TokenMutationResult {
  token: TokenDTO | null;
  tokens: TokenDTO[];
}

export interface TokenCreateInput {
  sceneId: string;
  actorId: string;
  x: number;
  y: number;
  elevation?: number;
}

export interface TokenMoveInput {
  sceneId?: string;
  x: number;
  y: number;
}

export interface TokenOptions {
  sceneId?: string;
  expectedVersion?: number;
}

export interface CombatBarDTO {
  value: number;
  max: number;
  percent: number | null;
  visibility: string;
}

export interface CombatantDTO {
  id: string;
  actor_id: string;
  token_id: string;
  name: string;
  initiative: string | null;
  hidden: boolean;
  defeated: boolean;
  position: number;
  is_current: boolean;
  is_next: boolean;
  has_acted: boolean;
  can_move_up: boolean;
  can_move_down: boolean;
  portrait_url: string;
  bar: CombatBarDTO | null;
  conditions_count: number;
  effects_count: number;
}

export interface CombatConfigDTO {
  system_id: string;
  label: string;
  input: 'roll' | 'number' | 'text';
  sort: 'desc' | 'asc';
  manual_order: boolean;
  icon: string;
  accent: string;
  resources: RulesetCombatResources;
}

export interface CombatStateDTO {
  campaign_id: string;
  combat_id: string;
  active: boolean;
  round: number;
  turn: number;
  combatants: CombatantDTO[];
  current_id: string;
  current_name: string;
  next_id: string;
  next_name: string;
  config: CombatConfigDTO;
  updated_actors: RulesetEffectMutation[];
  expired_effects: RulesetEffectMutation[];
  effect_ticks: RulesetEffectMutation[];
}

export interface CombatStartInput {
  sceneId?: string;
}

export interface CombatAddInput {
  actorIds?: string[];
  tokenIds?: string[];
}

export interface CombatFlagsPatch {
  hidden?: boolean;
  defeated?: boolean;
}

export interface CombatRollInitiativeOptions {
  scope?: 'all' | 'one';
  combatantId?: string;
}

export interface CombatInitiativeOrderEntry {
  combatantId: string;
  value?: string;
}

export interface ContentReferenceDTO {
  uri: string;
  campaignId: string;
  kind: 'actor' | 'item' | 'journal' | 'pdf' | 'deck' | 'card' | 'scene' | 'token';
  id: string;
  parentKind: string | null;
  parentId: string | null;
  page: number | null;
  anchor: string | null;
}

export interface ContentReferenceInput {
  kind: ContentReferenceDTO['kind'];
  id?: string;
  documentId?: string;
  campaignId?: string;
  parentKind?: string;
  parentId?: string;
  page?: number;
  anchor?: string;
}

export interface ContentRefOptions {
  campaignId?: string;
  parentKind?: string;
  parentId?: string;
  page?: number;
  anchor?: string;
}

export interface ContentOpenOptions {
  source?: string;
}

export interface ContentLinkOptions {
  label?: string;
  icon?: string;
}

export interface ContentLinkDTO {
  type: 'grave-reference';
  ref: string;
  label: string;
  icon: string;
}

export interface ContentResolutionDTO {
  ref: ContentReferenceDTO;
  value: ContentResolvedValue;
}

export interface ContentSearchOptions {
  kinds?: ContentReferenceDTO['kind'][];
  cursor?: string;
  limit?: number;
}

export interface ContentSearchEntryDTO {
  ref: ContentReferenceDTO;
  label: string;
  kind: ContentReferenceDTO['kind'];
}

export interface ContentSearchPageDTO {
  entries: ContentSearchEntryDTO[];
  nextCursor: string | null;
}

export interface JournalDTO {
  id: string;
  title: string;
  type: string;
  folder_id: string | null;
  visibility: string;
  version: number;
  view: JournalView;
}

export interface PdfDocumentDTO {
  id: string;
  filename: string;
  content_type: 'application/pdf';
  byte_size: number;
  created_at: number;
  url: string;
}

export interface PdfMetadataDTO {
  id: string;
  filename: string;
  content_type: 'application/pdf';
  byte_size: number;
  created_at: number;
}

export interface JournalCreateInput {
  type?: string;
  title: string;
  folderId?: string;
  visibility?: string;
  contentMarkdown?: string;
  data?: JournalDataInput;
  ownerUserIds?: string[];
}

export interface JournalUpdatePatch {
  title?: string;
  folderId?: string;
  visibility?: string;
  contentMarkdown?: string;
  data?: JournalDataInput;
  ownerUserIds?: string[];
}

export interface JournalListOptions {
  type?: string;
  folderId?: string;
  limit?: number;
}

export interface JournalMutationResult {
  journal_id: string;
  version: number | null;
}

export interface JournalListResult {
  journals: JournalDTO[];
}

export interface PdfRegionDTO {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
}

export interface PdfAnnotationInput {
  page: number;
  region: PdfRegionDTO;
  text: string;
}

export interface PdfAnnotationDTO {
  id: string;
  document_id: string;
  author_user_id: string;
  page: number;
  region: PdfRegionDTO;
  text: string;
  created_at: number;
  updated_at: number;
}

export interface PdfAnnotationResult {
  annotation: PdfAnnotationDTO;
}

export interface PdfAnnotationDeleteResult {
  annotation_id: string;
}

export interface PdfViewerOpenOptions {
  host?: HTMLElement;
  assetUrl?: string;
  page?: number;
  zoom?: number;
  spread?: boolean;
  anchor?: string;
  onPageChange?: (page: number) => void;
}

export interface ActionDefinitionDTO {
  id: string;
  packageId: string;
  version: number;
  reference: string;
  inputs: ActionInputSchema;
  requiredCapabilities: string[];
  idempotency: 'IDEMPOTENT' | 'REQUIRES_IDEMPOTENCY_KEY' | 'NOT_DURABLE';
  durability: 'supported' | 'unsupported';
  limits: ActionLimitsDTO;
  semantics: string[];
}

export interface ActionLimitsDTO {
  maxSteps: number;
}

export interface ActionExecuteOptions {
  version?: number;
  idempotencyKey?: string;
}

export interface ActionReferenceExecuteOptions {
  idempotencyKey?: string;
}

export interface ActionResolveInput {
  provider: 'active-ruleset';
  semantic: string;
}

export interface ChangedResourceDTO {
  type: 'actor';
  id: string;
  version: number;
}

export interface ActionExecutionResult {
  action: string;
  version: number;
  reference: string;
  executionId: string;
  result: ActionSuccessDTO;
  changedResources: ChangedResourceDTO[];
}

export interface ActionSuccessDTO {
  ok: true;
}

export interface ParticleDTO {
  id: string;
  scene_id: string;
  x: number;
  y: number;
  kind: string;
  scale: number;
  density: number;
  color: string;
  enabled: boolean;
  updated_at: number;
}

export interface ParticleValues {
  x?: number;
  y?: number;
  kind?: string;
  scale?: number;
  density?: number;
  color?: string;
  enabled?: boolean;
}

export interface ParticleResultDTO {
  emitter: ParticleDTO;
}

export interface ParticleDeleteResult {
  emitter_id: string;
  scene_id: string;
}

export interface EffectStateDTO {
  particles: ParticleDTO[];
  shaders: ShaderMetadataDTO[];
}

export interface ShaderMetadataDTO {
  id: string;
  scene_id: string;
  name: string;
  x: number;
  y: number;
  radius: number;
  rotation: number;
  blend_mode: string;
  opacity: number;
  intensity: number;
  scale: number;
  speed: number;
  color: string;
  enabled: boolean;
  updated_at: number;
}

export interface ParticlePresetDTO {
  id: string;
  label: string;
  parameters: ParticleParameterSchemas;
}

export interface FogStateDTO {
  scene_id: string;
  enabled: boolean;
  baseline: 'hide_all' | 'reveal_all';
  ops: FogOp[];
  version: number;
}

export interface FogMutationResult {
  scene_id: string;
  enabled: boolean;
  baseline: 'hide_all' | 'reveal_all';
  ops: FogOp[];
  new_ops: FogOp[];
  version: number;
}

export interface FogPaintOptions {
  expectedVersion?: number;
}

export interface SceneImageDTO {
  id: string;
  campaign_id: string;
  scene_id: string;
  asset_id: string;
  owner_user_id: string | null;
  x: number;
  y: number;
  rotation: number;
  scale: number;
  z_index: number;
  natural_width: number;
  natural_height: number;
  version: number;
  locked: boolean;
  gm_only: boolean;
  layer: string;
  metadata: SceneImageMetadata;
  created_at: number;
  updated_at: number;
  src: string;
}

export interface SceneImageListResult {
  placements: SceneImageDTO[];
}

export interface SceneImagePlaceOptions {
  x?: number;
  y?: number;
  rotation?: number;
  scale?: number;
  layer?: string;
}

export interface SceneImageUpdatePatch {
  x?: number;
  y?: number;
  rotation?: number;
  scale?: number;
  zIndex?: number;
  layer?: string;
  assetId?: string;
}

export interface SceneImageResult {
  placement: SceneImageDTO;
}

export interface SceneImageDeleteResult {
  placement_id: string;
  scene_id: string;
}

export interface SceneTemplateDTO {
  id: string;
  sceneId: string;
  shape: 'circle' | 'cone' | 'line' | 'rectangle';
  origin: WorldPointDTO;
  target: WorldPointDTO;
  creatorId: string;
  audience: 'campaign' | 'gm';
  persistence: 'persistent';
  version: number;
}

export interface SceneTemplateValues {
  shape: 'circle' | 'cone' | 'line' | 'rectangle';
  origin: WorldPointDTO;
  target: WorldPointDTO;
  audience?: 'campaign' | 'gm';
}

export interface SceneTemplateListResult {
  templates: SceneTemplateDTO[];
  version: number;
}

export interface SceneTemplateResult {
  template: SceneTemplateDTO;
}

export interface SceneTemplateDeleteResult {
  template_id: string;
  scene_id: string;
  version: number;
  audience: 'campaign' | 'gm';
}

export interface BusRequestOptions {
  timeoutMs?: number;
  timeout?: number;
}

export interface ChatSendMessage {
  content: string;
  kind?: string;
  visibility?: string;
}

export interface DiceRollInput {
  formula: string;
  label?: string;
  actorId?: string;
}

export interface RollIntentInput {
  actorId: string;
  actionId: string;
  inputs?: ActionInput;
  rollOptions?: RollOptions;
  targetActorId?: string;
  targetTokenId?: string;
  target?: RollTarget;
}

export interface RollTarget {
  actorId?: string;
  tokenId?: string;
}

export interface RollResultDTO {
  actor_id: string;
  type: string;
  label: string;
  expression: string;
  groups: RollGroupDTO[];
  modifier: number;
  total: number;
  visibility: string;
  metadata: RollMetadata;
  applied: RollAppliedMutation[];
}

export interface HandoutAudience {
  type?: 'all' | 'user' | 'role';
  id?: string;
}

export interface HandoutPresentResult {
  presented: true;
}

export interface SettingDefinitionDTO {
  key: string;
  scope: SettingScope;
  type: string;
  default: SettingValue;
  label: string;
  options: SettingValue[];
  minimum: number | null;
  maximum: number | null;
  pattern: string;
}

export interface SettingSetOptions {
  campaignId?: string;
}

export interface SettingSetResult {
  success: true;
  package_id: string;
  key: string;
  value: SettingValue;
  scope?: SettingScope;
}

export interface StorageQueryResult {
  success: true;
  rows: StorageRow[];
}

export interface StorageExecuteResult {
  success: true;
  rowcount: number;
}

export interface StorageStatusDTO {
  success: true;
  scope: 'campaign' | 'global';
  ready: boolean;
  size_bytes: number;
}

export interface TokenReadOptions {
  sceneId?: string;
  limit?: number;
}

export interface CardStateDTO {
  campaign_id: string;
  decks: DeckRuntimeDTO[];
  piles: CardPileDTO[];
  scene_placements: CardPlacementDTO[];
  cards: CardRuntimeDTO[];
}

export interface CardPileDTO {
  id: string;
  campaign_id: string;
  deck_instance_id: string;
  kind: string;
  owner_user_id: string | null;
  visibility: string;
}

export interface CardPlacementDTO {
  id: string;
  campaign_id: string;
  scene_id: string;
  card_instance_id: string;
  owner_user_id: string | null;
  x: number;
  y: number;
  rotation: number;
  scale: number;
  z_index: number;
  face_state: 'face_up' | 'face_down';
  visibility: string;
  locked: boolean;
}

export interface CardEventDTO {
  id: string;
  campaign_id: string;
  event_type: string;
  created_at: number;
}

export interface CardDefinitionInstantiateOptions {
  version?: number;
  name?: string;
  artwork: CardArtworkMap;
  metadata?: CardMetadata;
}

export interface CardDrawOptions {
  count?: number;
  destination?: 'hand' | 'pile' | 'chat' | 'scene' | 'discard' | 'removed';
  mode?: 'top' | 'bottom' | 'random' | 'choose';
  targetPileId?: string;
  reveal?: boolean;
}

export interface CardResetOptions {
  shuffle?: boolean;
}

export interface CardPlayOptions {
  sceneId?: string;
  x?: number;
  y?: number;
  rotation?: number;
  scale?: number;
  faceUp?: boolean;
}

export interface CardPlacementPatch {
  x?: number;
  y?: number;
  rotation?: number;
  scale?: number;
  zIndex?: number;
  faceState?: 'face_up' | 'face_down';
}

export interface CardDeckMutationResult {
  deck_instance_id: string;
  draw_count?: number;
}

export interface CardIdsResult {
  card_ids: string[];
}

export interface CardDrawResult {
  event: CardEventDTO;
  cards: CardRuntimeDTO[];
  target_pile_id: string;
}

export interface CardPlayResult {
  event: CardEventDTO;
  placement: CardPlacementDTO;
  card: CardRuntimeDTO | null;
}

export interface CardPlacementResult {
  event: CardEventDTO;
  placement: CardPlacementDTO;
}

export interface CardPlacementDiscardResult {
  event: CardEventDTO;
  card_ids: string[];
}

export interface CardDefinitionInstantiateResult {
  deck: DeckRuntimeDTO;
  definition: CardDefinitionDTO;
  provenance: CardProvenanceDTO;
}

export interface CardProvenanceDTO {
  definition: string;
  packageId: string;
  definitionVersion: number;
  instanceMetadata: CardMetadata;
}

export interface CameraDTO {
  worldX: number;
  worldY: number;
  zoom: number;
}

export interface ToolDefinition {
  id: string;
  label?: string;
  icon?: string;
  cursor?: string;
  capability?: string;
  when?: (context: SdkContextDTO) => boolean;
  activate?: (context: ToolContextDTO) => void;
  deactivate?: (context: ToolContextDTO) => void;
  pointer?: (event: ToolPointerEventDTO) => void;
}

export interface ToolContextDTO {
  id: string;
  packageId: string;
}

export interface ToolPointerEventDTO {
  phase: 'down' | 'move' | 'up' | 'cancel';
  world: WorldPointDTO;
  button: number;
  modifiers: ToolModifiersDTO;
}

export interface ToolModifiersDTO {
  alt: boolean;
  ctrl: boolean;
  meta: boolean;
  shift: boolean;
}

export interface ToastOptions {
  duration?: number;
  id?: string | null;
  onClick?: (toast: HTMLElement) => void;
}

export interface ToastHandle {
  dismiss: () => void;
}

export interface ApplicationDefinition {
  parts: ApplicationParts;
  close?: (context: ApplicationContext) => void;
  rendered?: (root: HTMLElement, context: ApplicationContext, parts: string[]) => void;
}

export interface ApplicationRenderOptions {
  parts?: string[];
}

export interface ApplicationInstance {
  root: HTMLElement;
  update: (next: ApplicationContext, parts?: string[]) => Promise<ApplicationInstance | null>;
  close: () => void;
}

export interface SheetController {
  setup?: (context: SheetControllerContext) => void;
  mount?: (context: SheetControllerContext) => void;
  update?: (context: SheetControllerContext) => void;
  unmount?: (context: SheetControllerContext) => void;
  onAction?: (action: SheetActionEvent, context: SheetControllerContext) => boolean | void;
}

export interface SheetActionEvent {
  name: string;
  event: Event;
  element: HTMLElement;
}

export interface ContentPackSummaryDTO {
  id: string;
  type: string;
  label: string;
}

export interface ContentPackDTO {
  id: string;
  type: string;
  label: string;
  entries: ContentPackEntryDTO[];
}

export interface ContentPackEntryDTO {
  id: string;
  name?: string;
  label?: string;
  data: ContentPackEntryData;
}

export interface PDFPresentationDTO {
  id: string;
  presenter: string;
  documentId: string;
  audience: string[];
  page: number;
  version: number;
  status: string;
  expiresAt: number;
}

export interface NumberParameterSchemaDTO {
  type: 'number';
  default: number;
  min: number;
  max: number;
}

export interface BooleanParameterSchemaDTO {
  type: 'boolean';
  default: boolean;
}

export interface ColorParameterSchemaDTO {
  type: 'color';
  default: string;
  pattern: '^#[0-9a-fA-F]{6}$';
}

export interface BlendModeParameterSchemaDTO {
  type: 'enum';
  default: 'normal';
  options: ('normal' | 'add' | 'multiply' | 'screen')[];
}

export interface ShaderPresetParametersDTO {
  x: NumberParameterSchemaDTO;
  y: NumberParameterSchemaDTO;
  radius: NumberParameterSchemaDTO;
  rotation: NumberParameterSchemaDTO;
  opacity: NumberParameterSchemaDTO;
  intensity: NumberParameterSchemaDTO;
  scale: NumberParameterSchemaDTO;
  speed: NumberParameterSchemaDTO;
  color: ColorParameterSchemaDTO;
  blendMode: BlendModeParameterSchemaDTO;
  enabled: BooleanParameterSchemaDTO;
}

export interface ActorMutationResult {
  actor_id: string;
  version: number;
}

export interface ItemMutationResult {
  item_id: string;
  version: number;
}

export interface ActorCreateInput {
  systemId: string;
  type: string;
  name: string;
  folderId?: string;
}

export interface ActorUpdateInput {
  name?: string;
  folderId?: string;
  portraitAssetId?: string;
  tokenAssetId?: string;
}

export interface ItemCreateInput {
  systemId: string;
  type: string;
  name: string;
  folderId?: string;
}

export interface ItemUpdateInput {
  name?: string;
  folderId?: string;
  portraitAssetId?: string;
}

export interface EntityListQuery {
  type?: string;
  folderId?: string;
  cursor?: string;
  limit?: number;
}

export interface ExpectedVersionOptions {
  expectedVersion?: number;
}

export interface ShaderApplyInput {
  presetId: string;
  schemaVersion?: number;
  parameters?: ShaderParameterValues;
}

export interface ShaderUpdateInput {
  parameters?: ShaderParameterValues;
  x?: number;
  y?: number;
  radius?: number;
  rotation?: number;
  opacity?: number;
  intensity?: number;
  scale?: number;
  speed?: number;
  color?: string;
  blendMode?: 'normal' | 'add' | 'multiply' | 'screen';
  enabled?: boolean;
}

export interface ShaderParameterValues {
  x?: number;
  y?: number;
  radius?: number;
  rotation?: number;
  opacity?: number;
  intensity?: number;
  scale?: number;
  speed?: number;
  color?: string;
  blendMode?: 'normal' | 'add' | 'multiply' | 'screen';
  enabled?: boolean;
}

export interface ShaderRemovalResult {
  instance_id: string;
  scene_id: string;
}

export interface InteropProviderContext {
  callerPackageId: string;
  providerPackageId: string;
  userId: string | undefined;
  campaignId: string | undefined;
  permissions: PermissionContext | null;
}

export interface SettingChangeDTO {
  packageId: string;
  key: string;
  value: SettingValue;
  previous: SettingValue | undefined;
  scope: SettingScope;
}

export interface SdkContextDTO {
  campaign: CampaignContext | null;
  scene: SceneContext | null;
  user: UserContext | null;
  permissions: PermissionContext | null;
}

export interface ActorDataDTO {
  actor_id: string;
  version: number;
  data: RulesetSheetData;
}

export interface SheetDataPatchResult {
  actor_id: string;
  version: number;
  changed_paths: string[];
}

export interface ItemDataPatchResult {
  item_id: string;
  version: number;
  changed_paths: string[];
}

export interface ActorItemSlotDTO {
  id: string;
  accepts: string[];
  duplicatePolicy: 'allow' | 'rejectSource';
}

export interface ActorItemInsertResult {
  copy: ActorItemCopyDTO;
  actorId: string;
  slot: string;
  version: number;
}

export interface ActorItemRemoveResult {
  removed: true;
  actorId: string;
  slot: string;
  version: number;
}

export interface ActorItemSlotOptions {
  slot: string;
}

export interface GravewrightSDK {
  readonly version: '1';
  readonly package: Readonly<{ id: string; kind: string; version: string }>;
  readonly kind: string;
  readonly capabilities: { has(capability: string): boolean; require(capability: string, apiName?: string): void; list(): readonly string[] };
  context(): Readonly<SdkContextDTO>;
  readonly actors: {
    create(input?: ActorCreateInput): Promise<ActorMutationResult>;
    data(actorId: string): Promise<ActorDataDTO>;
    delete(actorId: string): Promise<ActorMutationResult>;
    get(actorId: string): Promise<ActorDTO | null>;
    readonly items: {
      insertCopy(actorId: string, sourceItemId: string, options?: ActorItemSlotOptions): Promise<ActorItemInsertResult>;
      listCopies(actorId: string, options?: ActorItemSlotOptions): Promise<ActorItemCopyDTO[]>;
      removeCopy(actorId: string, localInstanceId: string, options?: ActorItemSlotOptions): Promise<ActorItemRemoveResult>;
      slots(actorId: string): Promise<ActorItemSlotDTO[]>;
    };
    list(query?: EntityListQuery): Promise<ActorDTO[]>;
    patchData(actorId: string, patch?: RulesetSheetData): Promise<SheetDataPatchResult>;
    update(actorId: string, patch?: ActorUpdateInput, options?: ExpectedVersionOptions): Promise<ActorMutationResult>;
  };
  readonly assets: {
    cancelImport(assetId: string): Promise<AssetCancelResult>;
    ingest(file: File): Promise<AssetIngestResult>;
    list(options?: AssetListOptions): Promise<AssetDTO[]>;
  };
  readonly automation: {
    audit(): Promise<AutomationAuditDTO[]>;
    cancel(jobId: string): Promise<AutomationCancelResult>;
    get(jobId: string): Promise<AutomationJobDTO | null>;
    list(): Promise<AutomationJobDTO[]>;
    schedule(actionId: string, input?: ActionInput, options?: AutomationScheduleOptions): Promise<AutomationJobDTO>;
  };
  readonly bus: {
    provide(method: string, handler: InteropHandler): Disposer;
    publish(name: string, payload: InteropPayload): void;
    request(method: string, payload: InteropPayload, options: BusRequestOptions): Promise<BusResponse>;
    subscribe(name: string, fn: InteropSubscriber): Disposer;
  };
  readonly cards: {
    readonly definitions: {
      get(id: string, version: number): Promise<CardDefinitionDTO | null>;
      instantiate(id: string, options?: CardDefinitionInstantiateOptions): Promise<CardDefinitionInstantiateResult>;
      list(): Promise<CardDefinitionDTO[]>;
    };
    discard(cardIds: string[]): Promise<CardIdsResult>;
    discardPlacement(placementId: string): Promise<CardPlacementDiscardResult>;
    draw(deckId: string, options?: CardDrawOptions): Promise<CardDrawResult>;
    play(cardId: string, options?: CardPlayOptions): Promise<CardPlayResult>;
    reset(deckId: string, options?: CardResetOptions): Promise<CardDeckMutationResult>;
    reveal(cardIds: string[]): Promise<CardIdsResult>;
    shuffle(deckId: string): Promise<CardDeckMutationResult>;
    state(): Promise<CardStateDTO>;
    updatePlacement(placementId: string, patch?: CardPlacementPatch): Promise<CardPlacementResult>;
  };
  readonly chat: {
    get(messageId: string): Promise<ChatMessageDTO | null>;
    list(options?: ChatListOptions): Promise<ChatMessageDTO[]>;
    send(message: string | ChatSendMessage): void;
  };
  readonly combat: {
    add(input?: CombatAddInput): Promise<CombatStateDTO>;
    advance(delta?: number): Promise<CombatStateDTO>;
    advanceRound(delta?: number): Promise<CombatStateDTO>;
    combatants(): Promise<CombatantDTO[]>;
    current(): Promise<CombatStateDTO>;
    dispatch(name: string, payload: CombatProtocolPayload): CombatProtocolPayload | undefined;
    end(): Promise<CombatStateDTO>;
    moveCombatant(combatantId: string, delta: number): Promise<CombatStateDTO>;
    register(plugin: CombatPlugin): boolean;
    registerPanel(panel: CombatPanelDefinition): boolean;
    remove(combatantId: string): Promise<CombatStateDTO>;
    renderSlot(name: string, payload: CombatProtocolPayload): Node[];
    rollInitiative(options?: CombatRollInitiativeOptions): Promise<CombatStateDTO>;
    setFlags(combatantId: string, flags?: CombatFlagsPatch): Promise<CombatStateDTO>;
    setInitiative(combatantId: string, value: number): Promise<CombatStateDTO>;
    setInitiativeOrder(entries: CombatInitiativeOrderEntry[]): Promise<CombatStateDTO>;
    setTurn(combatantId: string): Promise<CombatStateDTO>;
    start(input?: CombatStartInput): Promise<CombatStateDTO>;
  };
  readonly commands: {
    register(name: string, handler: CommandHandler): void;
  };
  readonly content: {
    can(reference: string | ContentReferenceInput, action?: string): Promise<boolean>;
    get(reference: string | ContentReferenceInput): Promise<ContentResolvedValue>;
    link(reference: string | ContentReferenceInput, options?: ContentLinkOptions): ContentLinkDTO;
    open(reference: string | ContentReferenceInput, options?: ContentOpenOptions): Promise<ContentResolutionDTO>;
    pack(packId: string): Promise<ContentPackDTO | null>;
    packs(): Promise<ContentPackSummaryDTO[]>;
    ref(kind: string, resourceId: string, options?: ContentRefOptions): string;
    resolve(reference: string | ContentReferenceInput): Promise<ContentResolutionDTO>;
    search(query?: string, options?: ContentSearchOptions): Promise<ContentSearchPageDTO>;
  };
  readonly dice: {
    roll(input?: DiceRollInput): Promise<RollResultDTO>;
  };
  readonly events: {
    available(): SdkEventName[];
    on(event: string, handler: SdkEventHandler): Disposer;
    once(event: string, handler: SdkEventHandler): Disposer;
  };
  readonly handouts: {
    present(resourceType: string, resourceId: string, audience?: HandoutAudience): Promise<HandoutPresentResult>;
  };
  readonly i18n: {
    t(key: string, fallback: string): string;
  };
  readonly items: {
    create(input?: ItemCreateInput): Promise<ItemMutationResult>;
    delete(itemId: string): Promise<ItemMutationResult>;
    get(itemId: string): Promise<ItemDTO | null>;
    list(query?: EntityListQuery): Promise<ItemDTO[]>;
    patchData(itemId: string, patch?: RulesetSheetData): Promise<ItemDataPatchResult>;
    update(itemId: string, patch?: ItemUpdateInput, options?: ExpectedVersionOptions): Promise<ItemMutationResult>;
  };
  readonly journals: {
    create(input?: JournalCreateInput): Promise<JournalMutationResult>;
    delete(journalId: string): Promise<JournalMutationResult>;
    get(journalId: string): Promise<JournalDTO | null>;
    list(options?: JournalListOptions): Promise<JournalListResult>;
    update(journalId: string, patch?: JournalUpdatePatch): Promise<JournalMutationResult>;
  };
  readonly packages: {
    get(packageId: string): Promise<PackageDTO | null>;
    has(packageId: string): Promise<boolean>;
  };
  readonly pdf: {
    readonly annotations: {
      create(documentId: string, annotation?: PdfAnnotationInput): Promise<PdfAnnotationResult>;
      delete(documentId: string, annotationId: string): Promise<PdfAnnotationDeleteResult>;
      list(documentId: string): Promise<PdfAnnotationDTO[]>;
      update(documentId: string, annotationId: string, annotation?: PdfAnnotationInput): Promise<PdfAnnotationResult>;
    };
    get(documentId: string): Promise<PdfDocumentDTO>;
    metadata(documentId: string): Promise<PdfMetadataDTO>;
    readonly presentation: {
      current(documentId: string): Promise<PDFPresentationDTO | null>;
      end(documentId: string): Promise<PDFPresentationDTO>;
      start(documentId: string, input?: PdfPresentationStartInput): Promise<PDFPresentationDTO>;
      update(documentId: string, page: number, options?: ExpectedVersionOptions): Promise<PDFPresentationDTO>;
    };
    readonly viewer: {
      currentPage(documentId: string): number | null;
      goToPage(documentId: string, page: number): Promise<number>;
      open(reference: string, options?: PdfViewerOpenOptions): Promise<PdfViewerOpenResult>;
      search(documentId: string, query: string): Promise<PdfSearchMatch[]>;
    };
  };
  readonly permissions: {
    can(action: string, resource?: PermissionResource): Promise<boolean>;
    check(action: string, resource?: PermissionResource): Promise<PermissionCheckDTO>;
  };
  readonly rolls: {
    intent(payload?: RollIntentInput): Promise<RollResultDTO | SheetDataPatchResult>;
  };
  readonly rules: {
    readonly actions: {
      execute(actionId: string, input?: ActionInput, options?: ActionExecuteOptions): Promise<ActionExecutionResult>;
      executeReference(reference: string, input?: ActionInput, options?: ActionReferenceExecuteOptions): Promise<ActionExecutionResult>;
      get(actionId: string): Promise<ActionDefinitionDTO>;
      list(): Promise<ActionDefinitionDTO[]>;
      resolve(input?: ActionResolveInput): Promise<ActionDefinitionDTO>;
    };
  };
  readonly scene: {
    active(): Promise<SceneDTO | null>;
    activeCameraForScene(sceneId: string): CameraDTO | null;
    activeCanvas(): HTMLElement | null;
    readonly effects: {
      create(sceneId: string, kind: string, values?: ParticleValues): Promise<ParticleResultDTO>;
      delete(effectId: string, kind: string): Promise<ParticleDeleteResult>;
      list(sceneId?: string): Promise<EffectStateDTO>;
      presets(): Promise<ParticlePresetDTO[]>;
      update(effectId: string, kind: string, values?: ParticleValues): Promise<ParticleResultDTO>;
    };
    readonly fog: {
      disable(sceneId?: string): Promise<FogMutationResult>;
      enable(sceneId?: string, initial?: string): Promise<FogMutationResult>;
      paint(sceneId?: string, ops?: FogOp[], options?: FogPaintOptions): Promise<FogMutationResult>;
      reset(sceneId?: string, to?: string): Promise<FogMutationResult>;
      state(sceneId?: string): Promise<FogStateDTO>;
    };
    readonly geometry: {
      createLight(sceneId: string, input?: LightCreateInput): Promise<LightResult>;
      createWall(sceneId: string, input?: WallCreateInput): Promise<WallResult>;
      deleteLight(lightId: string): Promise<LightDeleteResult>;
      deleteWall(wallId: string): Promise<WallDeleteResult>;
      deleteWalls(wallIds: string[]): Promise<WallsDeleteResult>;
      lights(sceneId?: string): Promise<LightDTO[]>;
      moveWallNode(sceneId: string, from: WorldPointDTO, to: WorldPointDTO): Promise<WallsResult>;
      moveWalls(sceneId: string, wallIds: string[], delta: WorldPointDTO): Promise<WallsResult>;
      setDoorState(wallId: string, state: string): Promise<WallResult>;
      splitWall(wallId: string, x: number, y: number): Promise<WallsResult>;
      updateLight(lightId: string, patch?: LightUpdatePatch): Promise<LightResult>;
      updateWall(wallId: string, patch?: WallUpdatePatch): Promise<WallResult>;
      walls(sceneId?: string): Promise<WallDTO[]>;
    };
    get(sceneId: string): Promise<SceneDTO | null>;
    readonly images: {
      delete(placementId: string): Promise<SceneImageDeleteResult>;
      list(sceneId?: string): Promise<SceneImageListResult>;
      place(sceneId: string, assetId: string, options?: SceneImagePlaceOptions): Promise<SceneImageResult>;
      update(placementId: string, patch?: SceneImageUpdatePatch, options?: ExpectedVersionOptions): Promise<SceneImageResult>;
    };
    list(): Promise<SceneDTO[]>;
    readonly measurements: {
      cancel(sceneId: string, measurementId: string): Promise<SharedMeasurementDTO>;
      listShared(sceneId?: string): Promise<SharedMeasurementDTO[]>;
      measure(sceneId: string, from: WorldPointDTO, to: WorldPointDTO): Promise<MeasurementResultDTO>;
      share(sceneId: string, geometry: SharedMeasurementGeometry, options?: SharedMeasurementOptions): Promise<SharedMeasurementDTO>;
    };
    readonly shaders: {
      apply(sceneId: string, input?: ShaderApplyInput): Promise<ShaderInstanceDTO>;
      enable(id: string, enabled: boolean, options?: ExpectedVersionOptions): Promise<ShaderInstanceDTO>;
      getPreset(presetId: string): Promise<ShaderPresetDTO | null>;
      list(sceneId?: string): Promise<ShaderInstanceDTO[]>;
      presets(): Promise<ShaderPresetDTO[]>;
      remove(id: string): Promise<ShaderRemovalResult>;
      update(id: string, patch?: ShaderUpdateInput, options?: ExpectedVersionOptions): Promise<ShaderInstanceDTO>;
    };
    readonly templates: {
      create(sceneId: string, values?: SceneTemplateValues): Promise<SceneTemplateResult>;
      delete(templateId: string, options?: ExpectedVersionOptions): Promise<SceneTemplateDeleteResult>;
      get(sceneId: string, templateId: string): Promise<SceneTemplateDTO | null>;
      list(sceneId?: string): Promise<SceneTemplateListResult>;
      update(templateId: string, patch?: Partial<SceneTemplateValues>, options?: ExpectedVersionOptions): Promise<SceneTemplateResult>;
    };
  };
  readonly settings: {
    all(): SettingValues;
    definitions(): SettingDefinitionDTO[];
    get(key: string, fallback?: string): SettingValue | undefined;
    onChange(key: string, handler: SettingChangeHandler): Disposer;
    scope(key: string): SettingScope | null;
    set(key: string, value: number, options?: SettingSetOptions): Promise<SettingSetResult>;
  };
  readonly sheets: {
    helpers(): SheetHelpers;
    register(plugin: SheetPlugin): void;
    registerController(sheetType: string, controller: SheetController): boolean;
  };
  readonly storage: {
    readonly sqlite: {
      execute(scope: string, name: string, params?: StorageParams): Promise<StorageExecuteResult>;
      query(scope: string, name: string, params?: StorageParams): Promise<StorageQueryResult>;
      status(scope: string): Promise<StorageStatusDTO>;
    };
  };
  readonly tokens: {
    centerOn(tokenId: string): void;
    create(input?: TokenCreateInput): Promise<TokenMutationResult>;
    delete(tokenId: string, options?: TokenOptions): Promise<TokenMutationResult>;
    get(tokenId: string, options?: TokenReadOptions): Promise<TokenDTO | null>;
    list(options?: TokenReadOptions): Promise<TokenDTO[]>;
    move(tokenId: string, position?: TokenMoveInput, options?: TokenOptions): Promise<TokenMutationResult>;
    readonly targets: {
      clear(sceneId?: string): Promise<string[]>;
      list(sceneId?: string): Promise<string[]>;
      set(ids: string[], sceneId?: string): Promise<string[]>;
    };
    update(tokenId: string, patch?: TokenOverrides, options?: TokenOptions): Promise<TokenMutationResult>;
  };
  readonly tools: {
    activeTool(): string;
    register(definition?: ToolDefinition): Disposer;
  };
  readonly ui: {
    readonly applications: {
      close(applicationId: string): void;
      register(applicationId: string, definition: ApplicationDefinition): Disposer;
      render(applicationId: string, host: HTMLElement, appContext?: ApplicationContext, options?: ApplicationRenderOptions): Promise<ApplicationInstance | null>;
    };
    closeModal(modalOrId: string): void;
    openModal(modalId: string): void;
    readonly slots: {
      available(): string[];
      register(slotId: string, render: SlotRenderCallback): Disposer;
    };
    toast(message: string, options: ToastOptions): ToastHandle | undefined;
  };
}

declare global { interface Window { GravewrightSDK: { register(definition: { id: string; setup?(sdk: GravewrightSDK, payload: PackageLifecyclePayload): void; ready?(sdk: GravewrightSDK, payload: PackageLifecyclePayload): void; unload?(): void }): void } } }
