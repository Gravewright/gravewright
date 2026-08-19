// Generated SDK 1 declarations. JavaScript remains the runtime requirement.
type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };
export type CardMetadata = JsonObject;
export type CardMetadataSchema = JsonObject;

export type WorkflowStatus = 'RUNNING' | 'WAITING_INTERACTION' | 'WAITING_TIME' | 'COMPLETED' | 'CANCELLED' | 'FAILED';
export type WorkflowStepDTO = { type: 'ACTION'; action: string; input?: ActionInput } | { type: 'INTERACTION'; request: InteractionRequestInput; resultKey?: string } | { type: 'WAIT_UNTIL'; at?: number; delaySeconds?: number } | { type: 'BRANCH'; key: string; equals: JsonValue; then: number; else: number } | { type: 'SET'; key: string; value: JsonValue } | { type: 'COMPLETE'; output?: JsonValue } | { type: 'FAIL'; reason: string };
export type GameplayTurnModel = 'SEQUENTIAL' | 'SIMULTANEOUS' | 'PHASED';
export type GameplaySubmissionValue = boolean | string | number | null | JsonObject | JsonValue[];
export type TimelineCueType = 'ACTION' | 'AUDIO_PLAY' | 'PRESENTATION_SHOW' | 'LIGHT_CREATE' | 'SHADER_PRESET' | 'PARTICLE_CREATE' | 'NAVIGATION';
export type InteractionResponseValue = boolean | string | number | string[];
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
export type InputCommandHandler = (invocation: InputCommandInvocationDTO) => void | Promise<void>;
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

export interface AudioAssetReferenceDTO {
  kind: 'library-asset' | 'package-asset';
  id: string;
}

export interface AudienceDTO {
  kind: 'self' | 'users' | 'campaign' | 'gm';
  ids: string[];
}

export interface SemanticAnchorDTO {
  kind: 'token' | 'scene-object';
  id: string;
  sceneId?: string;
}

export interface FadeDTO {
  durationMs: number;
  curve: 'linear' | 'ease-in' | 'ease-out';
}

export interface AudioPlaybackDTO {
  id: string;
  asset: AudioAssetReferenceDTO;
  channel: 'music' | 'ambience' | 'sfx' | 'cinematic';
  state: 'pending-user-unlock' | 'playing' | 'paused' | 'stopped' | 'failed';
  loop: boolean;
  gain: number;
  audience: AudienceDTO;
  sceneId: string | null;
  worldAnchor: SemanticAnchorDTO | null;
  startedAt: number;
  expiresAt: number | null;
  fade: FadeDTO | null;
  version: number;
  ownerPackageId: string;
}

export interface SceneNavigationDTO {
  sceneId: string;
  recipientIds: string[];
  states: SceneNavigationStateDTO[];
}

export interface SceneNavigationStateDTO {
  campaignId: string;
  userId: string;
  sceneId: string;
  reason: string;
  version: number;
  updatedAt: number;
}

export interface SemanticRegistrationDTO {
  id: string;
  packageId: string;
  schemaVersion: 1;
  operations: string[];
}

export interface SemanticDropResultDTO {
  operation: string;
  targetId: string;
  source: ContentResolutionDTO;
  actionResult: ActionExecutionResult;
}

export interface InputCommandDTO {
  id: string;
  packageId: string;
  label: string;
  contexts: string[];
  registeredAction?: string;
  actionInput?: ActionInput;
}

export interface InputBindingDTO {
  user_id: string;
  package_id: string;
  command_id: string;
  binding: string;
  version: number;
}

export interface AudioPlayInput {
  asset: AudioAssetReferenceDTO;
  channel?: 'music' | 'ambience' | 'sfx' | 'cinematic';
  loop?: boolean;
  gain?: number;
  audience?: AudienceDTO;
  sceneId?: string;
  worldAnchor?: SemanticAnchorDTO;
  fade?: FadeDTO;
  idempotencyKey?: string;
}

export interface AudioListOptions {
  sceneId?: string;
}

export interface AudioPlaybackPatch {
  gain?: number;
  state?: 'playing' | 'paused';
  loop?: boolean;
  fade?: FadeDTO;
}

export interface AudioMutationOptions {
  expectedVersion?: number;
  fade?: FadeDTO;
}

export interface SpatialSoundPositionDTO {
  x: number;
  y: number;
}

export interface SpatialSoundDTO {
  id: string;
  sceneId: string;
  soundId: string;
  position: SpatialSoundPositionDTO;
  radius: number;
  gain: number;
  falloff: 'linear' | 'smooth';
  loop: boolean;
  enabled: boolean;
  audience: AudienceDTO;
  constrainedByWalls: boolean;
  version: number;
}

export interface SpatialSoundInput {
  soundId: string;
  position: SpatialSoundPositionDTO;
  radius: number;
  gain?: number;
  falloff?: 'linear' | 'smooth';
  loop?: boolean;
  enabled?: boolean;
  audience?: AudienceDTO;
  constrainedByWalls?: boolean;
}

export interface SpatialSoundPatch {
  position?: SpatialSoundPositionDTO;
  radius?: number;
  gain?: number;
  falloff?: 'linear' | 'smooth';
  loop?: boolean;
  enabled?: boolean;
  constrainedByWalls?: boolean;
}

export interface SpatialSoundDeleteResult {
  id: string;
  deleted: true;
}

export interface SoundDTO {
  id: string;
  campaignId: string;
  name: string;
  asset: AudioAssetReferenceDTO;
  kind: 'sound-effect' | 'music' | 'ambience';
  tags: string[];
  defaultGain: number;
  defaultLoop: boolean;
  metadata: JsonObject;
  version: number;
}

export interface SoundCreateInput {
  name: string;
  asset: AudioAssetReferenceDTO;
  kind: 'sound-effect' | 'music' | 'ambience';
  tags?: string[];
  defaultGain?: number;
  defaultLoop?: boolean;
  metadata?: JsonObject;
}

export interface SoundPatch {
  name?: string;
  kind?: 'sound-effect' | 'music' | 'ambience';
  tags?: string[];
  defaultGain?: number;
  defaultLoop?: boolean;
  metadata?: JsonObject;
}

export interface SoundListOptions {
  kind?: 'sound-effect' | 'music' | 'ambience';
  query?: string;
  cursor?: number;
  limit?: number;
}

export interface SoundDeleteResult {
  id: string;
  deleted: true;
}

export interface SceneNavigationInput {
  sceneId: string;
  recipients?: AudienceDTO;
  reason?: string;
  idempotencyKey?: string;
}

export interface DragSourceDefinition {
  id: string;
  referenceKinds: string[];
  operations: string[];
  schemaVersion: 1;
}

export interface DropTargetDefinition {
  id: string;
  surface: string;
  targetKinds: DropTargetKind[];
  worldObjectTypeId?: string;
  operations: string[];
  actionReference: string;
  schemaVersion: 1;
}

export interface SemanticDropInput {
  payload: SemanticDragPayload;
  destination: SemanticDropDestination;
  operation: string;
  idempotencyKey?: string;
}

export interface SemanticDropDestination {
  targetDefinitionId: string;
  kind: DropTargetKind;
  resource: DropTargetResource;
  expectedVersion?: number;
  worldPosition?: WorldPointDTO;
  sceneContext?: string;
}

export interface DropTargetResource {
  id: string;
  sceneId?: string;
  typeId?: string;
}

export interface SemanticDragPayload {
  kind: string;
  reference: string;
  sourceContext?: string;
  metadata?: JsonObject;
  schemaVersion: 1;
}

export interface InputCommandDefinition {
  id: string;
  label: string;
  description?: string;
  contexts: string[];
  registeredAction?: string;
  actionInput?: ActionInput;
  defaultBindings?: string[];
}

export interface InputCommandInvocationDTO {
  commandId: string;
  packageId: string;
  source: 'binding' | 'gesture';
  binding: string | null;
  context: string;
}

export interface InputGestureDefinition {
  id: string;
  gesture: 'tap' | 'double-tap' | 'long-press' | 'drag' | 'pan' | 'cancel';
  commandId: string;
}

export interface InputBindingOptions {
  expectedVersion?: number;
}

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

export interface CampaignMemberDTO {
  userId: string;
  role: string;
  name: string;
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
  controllers: string[];
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

export interface CustomShaderDefinition {
  format: 'gravewright-custom-shader';
  version: 1;
  definition: CustomShaderValues;
}

export interface CustomShaderValues {
  source: string;
  opacity: number;
  intensity: number;
  scale: number;
  speed: number;
  rotation: number;
  radius: number;
  color: string;
  blend_mode: 'normal' | 'add' | 'multiply' | 'screen';
  enabled: boolean;
}

export interface CustomShaderProviderDefinition {
  id: string;
  label: string;
  description?: string;
  open: (context: SdkContextDTO) => void | Promise<void>;
}

export interface CustomShaderUseResult {
  accepted: true;
}

export interface CustomShaderPreviewResult {
  active: boolean;
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
  kind: 'image' | 'pdf' | 'audio';
}

export interface AssetListOptions {
  campaignId?: string;
  kind?: 'image' | 'pdf' | 'audio';
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
  originExecutionId?: string;
  originJobId?: string;
  causalDepth?: number;
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

export interface SceneZoneGeometry {
  shape: 'circle' | 'rect' | 'polygon';
  x?: number;
  y?: number;
  radius?: number;
  width?: number;
  height?: number;
  points?: WorldPointDTO[];
}

export interface SceneZoneAudience {
  kind: 'campaign' | 'gm' | 'users';
  ids?: string[];
}

export interface SceneZoneDTO {
  id: string;
  sceneId: string;
  type: string;
  geometry: SceneZoneGeometry;
  vertical: VerticalBoundsDTO;
  audience: SceneZoneAudience;
  enabled: boolean;
  tags: string[];
  packageProvenance: PackageProvenanceDTO;
  version: number;
}

export interface PackageProvenanceDTO {
  packageId: string;
  providerId: string | null;
}

export interface SceneZoneInput {
  type?: string;
  geometry: SceneZoneGeometry;
  vertical?: VerticalBoundsDTO;
  audience?: SceneZoneAudience;
  enabled?: boolean;
  tags?: string[];
  providerId?: string;
}

export interface SceneZonePatch {
  geometry?: SceneZoneGeometry;
  enabled?: boolean;
  tags?: string[];
}

export interface SceneZoneDeleteResult {
  id: string;
  deleted: true;
}

export interface SceneObjectGeometry {
  kind: 'point' | 'rect' | 'circle' | 'polygon' | 'polyline';
  x?: number;
  y?: number;
  radius?: number;
  width?: number;
  height?: number;
  points?: WorldPointDTO[];
}

export interface SceneObjectAudience {
  kind: 'campaign' | 'gm' | 'users';
  ids?: string[];
}

export interface ActionReferenceDTO {
  provider: string;
  id: string;
  version: number;
}

export interface AssetReferenceDTO {
  kind: 'library-asset' | 'package-asset';
  id: string;
}

export interface SceneObjectInteractionDefinition {
  id: string;
  label: string;
  actionReference?: ActionReferenceDTO;
}

export interface SceneObjectTypeDefinition {
  typeId: string;
  schemaVersion: number;
  displayName: string;
  dataSchema: ActionInputSchema;
  geometryKinds: Array<'point' | 'rect' | 'circle' | 'polygon' | 'polyline'>;
  visualDefinition: JsonObject[];
  interactionDefinitions: SceneObjectInteractionDefinition[];
  editorDefinition?: JsonObject;
  searchableFields?: string[];
}

export interface SceneObjectDTO {
  id: string;
  sceneId: string;
  typeId: string;
  providerPackageId: string;
  schemaVersion: number;
  geometry: SceneObjectGeometry;
  transform: SceneObjectTransform;
  presentation: JsonObject;
  interactions: SceneObjectInteractionDefinition[];
  editor: JsonObject;
  dataSchema: ActionInputSchema;
  data: JsonObject;
  audience: SceneObjectAudience;
  enabled: boolean;
  providerAvailable: boolean;
  providerStatus: 'available' | 'unavailable' | 'outdated';
  version: number;
  createdAt: number;
  updatedAt: number;
}

export interface SceneObjectTransform {
  rotation: number;
  scale: number;
}

export interface SceneObjectInput {
  typeId: string;
  geometry: SceneObjectGeometry;
  transform?: Partial<SceneObjectTransform>;
  presentation?: JsonObject;
  data?: JsonObject;
  audience?: SceneObjectAudience;
  enabled?: boolean;
}

export interface SceneObjectPatch {
  geometry?: SceneObjectGeometry;
  transform?: Partial<SceneObjectTransform>;
  presentation?: JsonObject;
  data?: JsonObject;
  enabled?: boolean;
}

export interface SceneObjectListOptions {
  query?: string;
}

export interface SceneObjectHitTestOptions {
  tolerance?: number;
}

export interface SceneObjectInteractionIntentDTO {
  object: SceneObjectDTO;
  interactionId: string;
  actionReference: ActionReferenceDTO | null;
  principal: { userId: string };
}

export interface SceneObjectDeleteResult {
  id: string;
  deleted: true;
}

export interface PresentationAudience {
  kind: 'self' | 'campaign' | 'gm' | 'users';
  ids?: string[];
}

export interface PresentationAnchor {
  kind: 'token' | 'scene-object';
  id: string;
  sceneId?: string;
}

export interface PresentationContent {
  title?: string;
  subtitle?: string;
  text?: string;
  label?: string;
  icon?: string;
  asset?: AssetReferenceDTO;
  progress?: number;
  value?: number;
  preset?: string;
  buttons?: PresentationButton[];
}

export interface PresentationButton {
  id: string;
  label: string;
  actionReference: string;
}

export interface PresentationCompletionPolicy {
  policy: 'server-time' | 'all-connected-recipients';
  timeoutMs?: number;
}

export interface PresentationRecipientSummary {
  expected: number;
  completed: number;
}

export interface PresentationWaitOptions {
  timeoutMs?: number;
}

export interface PresentationInput {
  mode: 'world-anchor' | 'screen-overlay' | 'title-card' | 'countdown' | 'fade';
  content: PresentationContent;
  audience?: PresentationAudience;
  anchor?: PresentationAnchor;
  sceneId?: string;
  duration?: number;
  deadline?: number;
  completion?: PresentationCompletionPolicy;
}

export interface PresentationPatch {
  content?: PresentationContent;
  anchor?: PresentationAnchor;
}

export interface PresentationListOptions {
  sceneId?: string;
}

export interface PresentationDTO {
  id: string;
  campaignId: string;
  packageId: string;
  ownerUserId: string;
  sceneId: string | null;
  mode: 'world-anchor' | 'screen-overlay' | 'title-card' | 'countdown' | 'fade';
  content: PresentationContent;
  audience: PresentationAudience;
  anchor: PresentationAnchor | null;
  deadline: number | null;
  status: 'active' | 'completed' | 'closed' | 'cancelled';
  startedAt: number;
  endsAt: number;
  completedAt: number | null;
  completionReason: 'server-time' | 'recipients' | 'timeout' | 'closed' | 'package-unload' | null;
  completionPolicy: PresentationCompletionPolicy;
  recipientSummary: PresentationRecipientSummary;
  version: number;
  createdAt: number;
  updatedAt: number;
  expiresAt: number;
}

export interface PresentationCloseResult {
  id: string;
  status: 'closed';
}

export interface InteractionPromptDTO {
  title: string;
  text: string;
}

export interface InteractionChoiceDTO {
  id: string;
  label: string;
}

export interface InteractionResponseSchema {
  type: 'boolean' | 'single-choice' | 'multi-choice' | 'number' | 'string';
  choices?: InteractionChoiceDTO[];
  maxSelections?: number;
  minimum?: number;
  maximum?: number;
  maxLength?: number;
}

export interface InteractionOriginDTO {
  originExecutionId?: string;
  originJobId?: string;
  causalDepth?: number;
  resourceRef?: string;
}

export interface InteractionRequestInput {
  kind?: string;
  recipients: string[];
  title: string;
  text: string;
  responseSchema: InteractionResponseSchema;
  visibility?: 'requester' | 'participants' | 'public-after-close';
  deadline: number;
  responsePolicy?: 'immutable' | 'replace';
  origin?: InteractionOriginDTO;
}

export interface InteractionResponseDTO {
  value: InteractionResponseValue;
  respondedAt: number;
  idempotencyKey: string;
}

export interface InteractionDTO {
  id: string;
  kind: string;
  schemaVersion: 1;
  requester: string;
  recipients: string[];
  prompt: InteractionPromptDTO;
  responseSchema: InteractionResponseSchema;
  visibility: 'requester' | 'participants' | 'public-after-close';
  deadline: number;
  status: 'open' | 'completed' | 'expired' | 'cancelled';
  responses: { [userId: string]: InteractionResponseDTO };
  version: number;
  origin: InteractionOriginDTO;
  packageProvenance: PackageProvenanceDTO;
  createdAt: number;
  expiresAt: number;
}

export interface InteractionListOptions {
  status?: 'open' | 'completed' | 'expired' | 'cancelled';
  recipient?: 'me';
}

export interface InteractionMutationOptions {
  expectedVersion?: number;
  idempotencyKey?: string;
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

export interface WorkflowDefinitionDTO {
  id: string;
  schemaVersion: 1;
  steps: WorkflowStepDTO[];
  maxDuration: number;
  maxSteps: number;
  packageId?: string;
}

export interface WorkflowStartInput {
  definitionId: string;
  input?: WorkflowContext;
  sceneId?: string;
  idempotencyKey: string;
  origin?: SemanticOriginDTO;
}

export interface WorkflowDTO {
  id: string;
  definitionId: string;
  providerPackageId: string;
  campaignId: string;
  sceneId: string | null;
  status: WorkflowStatus;
  currentStep: number;
  context: WorkflowContext;
  origin: SemanticOriginDTO;
  createdBy: string;
  startedAt: number;
  wakeAt: number | null;
  waitingOn: string | null;
  completionReason: string | null;
  version: number;
}

export interface GameplayFlowDefinitionDTO {
  id: string;
  schemaVersion: 1;
  turnModel: GameplayTurnModel;
  phases: GameplayPhaseDTO[];
  packageId?: string;
}

export interface GameplayPhaseDTO {
  id: string;
  label: string;
  submissionPolicy: 'all';
  deadlineSeconds?: number;
}

export interface GameplayFlowStartInput {
  definitionId: string;
  participants: string[];
  sceneId?: string;
  idempotencyKey: string;
}

export interface GameplayFlowDTO {
  id: string;
  campaignId: string;
  sceneId: string | null;
  definitionId: string;
  providerPackageId: string;
  status: 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
  phaseId: string | null;
  round: number;
  cycle: number;
  participants: string[];
  activeParticipants: string[];
  submissions: GameplaySubmissions;
  revealed: boolean;
  version: number;
}

export interface GameplayFlowMutationOptions {
  expectedVersion?: number;
}

export interface TokenTransferDestination {
  sceneId: string;
  x: number;
  y: number;
  elevation?: number;
}

export interface TokenTransferSpec {
  tokenId: string;
  sceneId: string;
  x: number;
  y: number;
  elevation?: number;
  expectedVersion?: number;
}

export interface TokenTransferOptions {
  expectedVersion?: number;
  navigateAudience?: SceneNavigationRecipients;
}

export interface TokenTransferManyOptions {
  navigateAudience?: SceneNavigationRecipients;
}

export interface TransferredTokenDTO {
  id: string;
  sceneId: string;
  actorId: string | null;
  x: number;
  y: number;
  elevation: number;
  version: number;
}

export interface TokenTransferResultDTO {
  tokens: TransferredTokenDTO[];
  atomic: true;
  navigation: SceneNavigationDTO | null;
}

export interface TimelineDefinitionDTO {
  id: string;
  schemaVersion: 1;
  cues: TimelineCueDTO[];
  durationMs: number;
  packageId?: string;
}

export interface TimelineCueDTO {
  cueId: string;
  offsetMs: number;
  type: TimelineCueType;
  action?: string;
  parameters?: TimelineParameters;
  cleanupAction?: string;
  cleanupInput?: ActionInput;
}

export interface TimelineStartInput {
  definitionId: string;
  sceneId?: string;
  audience?: AudienceDTO;
  origin?: SemanticOriginDTO;
  startedAt?: number;
  idempotencyKey: string;
}

export interface TimelineDTO {
  id: string;
  definitionId: string;
  providerPackageId: string;
  campaignId: string;
  sceneId: string | null;
  status: 'RUNNING' | 'COMPLETED' | 'CANCELLED' | 'FAILED';
  startedAt: number;
  audience: AudienceDTO;
  origin: SemanticOriginDTO;
  executedCueIds: string[];
  completionReason: string | null;
  version: number;
}

export interface SemanticOriginDTO {
  source?: string;
  resourceId?: string;
  executionId?: string;
}

export interface SceneNavigationRecipients {
  kind: 'self' | 'users' | 'gm' | 'campaign';
  ids?: string[];
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
  readonly audio: {
    get(id: string): Promise<AudioPlaybackDTO | null>;
    list(options?: AudioListOptions): Promise<AudioPlaybackDTO[]>;
    play(input?: AudioPlayInput): Promise<AudioPlaybackDTO>;
    stop(id: string, options?: AudioMutationOptions): Promise<AudioPlaybackDTO>;
    update(id: string, patch?: AudioPlaybackPatch, options?: AudioMutationOptions): Promise<AudioPlaybackDTO>;
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
  readonly campaign: {
    members(): Promise<CampaignMemberDTO[]>;
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
  readonly gameplay: {
    readonly flows: {
      advance(id: string, options?: GameplayFlowMutationOptions): Promise<GameplayFlowDTO>;
      get(id: string): Promise<GameplayFlowDTO | null>;
      list(): Promise<GameplayFlowDTO[]>;
      register(definition?: GameplayFlowDefinitionDTO): Promise<GameplayFlowDefinitionDTO>;
      start(input?: GameplayFlowStartInput): Promise<GameplayFlowDTO>;
      submit(id: string, value: GameplaySubmissionValue, options?: GameplayFlowMutationOptions): Promise<GameplayFlowDTO>;
    };
  };
  readonly handouts: {
    present(resourceType: string, resourceId: string, audience?: HandoutAudience): Promise<HandoutPresentResult>;
  };
  readonly i18n: {
    t(key: string, fallback: string): string;
  };
  readonly input: {
    readonly bindings: {
      get(): Promise<InputBindingDTO[]>;
      set(commandId: string, binding: string, options?: InputBindingOptions): Promise<InputBindingDTO>;
    };
    readonly commands: {
      execute(commandId: string, inputs?: ActionInput): Promise<ActionExecutionResult>;
      list(): Promise<InputCommandDTO[]>;
      register(definition?: InputCommandDefinition, handler?: InputCommandHandler): Promise<Promise<Disposer>>;
    };
    readonly gestures: {
      register(definition?: InputGestureDefinition, handler?: InputCommandHandler): Promise<Promise<Disposer>>;
    };
  };
  readonly interactions: {
    cancel(id: string, options?: ExpectedVersionOptions): Promise<InteractionDTO>;
    get(id: string): Promise<InteractionDTO | null>;
    list(options?: InteractionListOptions): Promise<InteractionDTO[]>;
    request(input?: InteractionRequestInput): Promise<InteractionDTO>;
    respond(id: string, response: InteractionResponseValue, options?: InteractionMutationOptions): Promise<InteractionDTO>;
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
  readonly navigation: {
    readonly scene: {
      getState(): Promise<SceneNavigationStateDTO | null>;
      go(input?: SceneNavigationInput): Promise<SceneNavigationDTO>;
    };
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
    readonly objectTypes: {
      register(definition?: SceneObjectTypeDefinition): Promise<Promise<Disposer>>;
    };
    readonly objects: {
      create(sceneId: string, input?: SceneObjectInput): Promise<SceneObjectDTO>;
      delete(id: string, options?: ExpectedVersionOptions): Promise<SceneObjectDeleteResult>;
      get(id: string): Promise<SceneObjectDTO | null>;
      hitTest(sceneId: string, point: WorldPointDTO, options?: SceneObjectHitTestOptions): Promise<SceneObjectDTO[]>;
      interact(id: string, interactionId: string, options?: ExpectedVersionOptions): Promise<SceneObjectInteractionIntentDTO>;
      list(sceneId?: string, options?: SceneObjectListOptions): Promise<SceneObjectDTO[]>;
      update(id: string, patch?: SceneObjectPatch, options?: ExpectedVersionOptions): Promise<SceneObjectDTO>;
    };
    readonly shaders: {
      apply(sceneId: string, input?: ShaderApplyInput): Promise<ShaderInstanceDTO>;
      readonly customLibrary: {
        clearPreview(): CustomShaderPreviewResult;
        openEditor(definition?: CustomShaderDefinition | null): Promise<CustomShaderDefinition | null>;
        preview(definition: CustomShaderDefinition): CustomShaderPreviewResult;
        registerProvider(definition?: CustomShaderProviderDefinition): Disposer;
        use(definition: CustomShaderDefinition): Promise<CustomShaderUseResult>;
      };
      enable(id: string, enabled: boolean, options?: ExpectedVersionOptions): Promise<ShaderInstanceDTO>;
      getPreset(presetId: string): Promise<ShaderPresetDTO | null>;
      list(sceneId?: string): Promise<ShaderInstanceDTO[]>;
      presets(): Promise<ShaderPresetDTO[]>;
      remove(id: string): Promise<ShaderRemovalResult>;
      update(id: string, patch?: ShaderUpdateInput, options?: ExpectedVersionOptions): Promise<ShaderInstanceDTO>;
    };
    readonly spatialSounds: {
      create(sceneId: string, input?: SpatialSoundInput): Promise<SpatialSoundDTO>;
      delete(id: string, options?: ExpectedVersionOptions): Promise<SpatialSoundDeleteResult>;
      get(id: string): Promise<SpatialSoundDTO | null>;
      list(sceneId?: string): Promise<SpatialSoundDTO[]>;
      update(id: string, patch?: SpatialSoundPatch, options?: ExpectedVersionOptions): Promise<SpatialSoundDTO>;
    };
    readonly templates: {
      create(sceneId: string, values?: SceneTemplateValues): Promise<SceneTemplateResult>;
      delete(templateId: string, options?: ExpectedVersionOptions): Promise<SceneTemplateDeleteResult>;
      get(sceneId: string, templateId: string): Promise<SceneTemplateDTO | null>;
      list(sceneId?: string): Promise<SceneTemplateListResult>;
      update(templateId: string, patch?: Partial<SceneTemplateValues>, options?: ExpectedVersionOptions): Promise<SceneTemplateResult>;
    };
    readonly zones: {
      create(sceneId: string, input?: SceneZoneInput): Promise<SceneZoneDTO>;
      delete(id: string, options?: ExpectedVersionOptions): Promise<SceneZoneDeleteResult>;
      get(id: string): Promise<SceneZoneDTO | null>;
      list(sceneId?: string): Promise<SceneZoneDTO[]>;
      members(id: string): Promise<string[]>;
      update(id: string, patch?: SceneZonePatch, options?: ExpectedVersionOptions): Promise<SceneZoneDTO>;
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
  readonly sounds: {
    create(input?: SoundCreateInput): Promise<SoundDTO>;
    delete(id: string, options?: ExpectedVersionOptions): Promise<SoundDeleteResult>;
    get(id: string): Promise<SoundDTO | null>;
    list(options?: SoundListOptions): Promise<SoundDTO[]>;
    update(id: string, patch?: SoundPatch, options?: ExpectedVersionOptions): Promise<SoundDTO>;
  };
  readonly storage: {
    readonly sqlite: {
      execute(scope: string, name: string, params?: StorageParams): Promise<StorageExecuteResult>;
      query(scope: string, name: string, params?: StorageParams): Promise<StorageQueryResult>;
      status(scope: string): Promise<StorageStatusDTO>;
    };
  };
  readonly timelines: {
    cancel(id: string, options?: ExpectedVersionOptions): Promise<TimelineDTO>;
    get(id: string): Promise<TimelineDTO | null>;
    list(): Promise<TimelineDTO[]>;
    register(definition?: TimelineDefinitionDTO): Promise<TimelineDefinitionDTO>;
    start(input?: TimelineStartInput): Promise<TimelineDTO>;
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
    transfer(tokenId: string, destination?: TokenTransferDestination, options?: TokenTransferOptions): Promise<TokenTransferResultDTO>;
    transferMany(transfers?: TokenTransferSpec[], options?: TokenTransferManyOptions): Promise<TokenTransferResultDTO>;
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
    readonly dragDrop: {
      drop(input?: SemanticDropInput): Promise<SemanticDropResultDTO>;
      registerSource(definition?: DragSourceDefinition): Promise<Promise<Disposer>>;
      registerTarget(definition?: DropTargetDefinition): Promise<Promise<Disposer>>;
      sources(): Promise<SemanticRegistrationDTO[]>;
      targets(): Promise<SemanticRegistrationDTO[]>;
    };
    openModal(modalId: string): void;
    readonly presentations: {
      close(id: string, options?: ExpectedVersionOptions): Promise<PresentationCloseResult>;
      get(id: string): Promise<PresentationDTO | null>;
      list(options?: PresentationListOptions): Promise<PresentationDTO[]>;
      show(input?: PresentationInput): Promise<PresentationDTO>;
      update(id: string, patch?: PresentationPatch, options?: ExpectedVersionOptions): Promise<PresentationDTO>;
      wait(id: string, options?: PresentationWaitOptions): Promise<PresentationDTO | null>;
    };
    readonly slots: {
      available(): string[];
      register(slotId: string, render: SlotRenderCallback): Disposer;
    };
    toast(message: string, options: ToastOptions): ToastHandle | undefined;
  };
  readonly workflows: {
    cancel(id: string, options?: ExpectedVersionOptions): Promise<WorkflowDTO>;
    get(id: string): Promise<WorkflowDTO | null>;
    list(): Promise<WorkflowDTO[]>;
    register(definition?: WorkflowDefinitionDTO): Promise<WorkflowDefinitionDTO>;
    start(input?: WorkflowStartInput): Promise<WorkflowDTO>;
  };
}

declare global { interface Window { GravewrightSDK: { register(definition: { id: string; setup?(sdk: GravewrightSDK, payload: PackageLifecyclePayload): void; ready?(sdk: GravewrightSDK, payload: PackageLifecyclePayload): void; unload?(): void }): void } } }
