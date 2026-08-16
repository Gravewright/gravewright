# Referência de DTOs e tipos da SDK 1

Estruturas canônicas geradas a partir do registro de DTOs/inputs da SDK 1.

## `ActionDefinitionDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |
| `version` | `number` |
| `reference` | `string` |
| `inputs` | `ActionInputSchema` |
| `requiredCapabilities` | `string[]` |
| `idempotency` | `'IDEMPOTENT' | 'REQUIRES_IDEMPOTENCY_KEY' | 'NOT_DURABLE'` |
| `durability` | `'supported' | 'unsupported'` |
| `limits` | `ActionLimitsDTO` |
| `semantics` | `string[]` |

## `ActionExecuteOptions`

Campos:

| Field | Type |
|---|---|
| `version` | `number` |
| `idempotencyKey` | `string` |

## `ActionExecutionResult`

Campos:

| Field | Type |
|---|---|
| `action` | `string` |
| `version` | `number` |
| `reference` | `string` |
| `executionId` | `string` |
| `result` | `ActionSuccessDTO` |
| `changedResources` | `ChangedResourceDTO[]` |

## `ActionLimitsDTO`

Campos:

| Field | Type |
|---|---|
| `maxSteps` | `number` |

## `ActionReferenceExecuteOptions`

Campos:

| Field | Type |
|---|---|
| `idempotencyKey` | `string` |

## `ActionResolveInput`

Campos:

| Field | Type |
|---|---|
| `provider` | `'active-ruleset'` |
| `semantic` | `string` |

## `ActionSuccessDTO`

Campos:

| Field | Type |
|---|---|
| `ok` | `true` |

## `ActorCreateInput`

Campos:

| Field | Type |
|---|---|
| `systemId` | `string` |
| `type` | `string` |
| `name` | `string` |
| `folderId` | `string` |

## `ActorDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `system_id` | `string` |
| `type` | `string` |
| `name` | `string` |
| `folder_id` | `string | null` |
| `portrait_asset_id` | `string | null` |
| `token_asset_id` | `string | null` |
| `version` | `number` |
| `created_at` | `number` |
| `updated_at` | `number` |

## `ActorDataDTO`

Campos:

| Field | Type |
|---|---|
| `actor_id` | `string` |
| `version` | `number` |
| `data` | `RulesetSheetData` |

## `ActorItemInsertResult`

Campos:

| Field | Type |
|---|---|
| `copy` | `ActorItemCopyDTO` |
| `actorId` | `string` |
| `slot` | `string` |
| `version` | `number` |

## `ActorItemRemoveResult`

Campos:

| Field | Type |
|---|---|
| `removed` | `true` |
| `actorId` | `string` |
| `slot` | `string` |
| `version` | `number` |

## `ActorItemSlotDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `accepts` | `string[]` |
| `duplicatePolicy` | `'allow' | 'rejectSource'` |

## `ActorItemSlotOptions`

Campos:

| Field | Type |
|---|---|
| `slot` | `string` |

## `ActorMutationResult`

Campos:

| Field | Type |
|---|---|
| `actor_id` | `string` |
| `version` | `number` |

## `ActorUpdateInput`

Campos:

| Field | Type |
|---|---|
| `name` | `string` |
| `folderId` | `string` |
| `portraitAssetId` | `string` |
| `tokenAssetId` | `string` |

## `ApplicationDefinition`

Campos:

| Field | Type |
|---|---|
| `parts` | `ApplicationParts` |
| `close` | `(context: ApplicationContext) => void` |
| `rendered` | `(root: HTMLElement, context: ApplicationContext, parts: string[]) => void` |

## `ApplicationInstance`

Campos:

| Field | Type |
|---|---|
| `root` | `HTMLElement` |
| `update` | `(next: ApplicationContext, parts?: string[]) => Promise<ApplicationInstance | null>` |
| `close` | `() => void` |

## `ApplicationRenderOptions`

Campos:

| Field | Type |
|---|---|
| `parts` | `string[]` |

## `AssetCancelResult`

Campos:

| Field | Type |
|---|---|
| `operation` | `AssetOperationDTO` |
| `assetId` | `string` |

## `AssetDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `owner_user_id` | `string` |
| `folder_id` | `string | null` |
| `filename` | `string` |
| `content_type` | `string` |
| `byte_size` | `number` |
| `width` | `number | null` |
| `height` | `number | null` |
| `created_at` | `number` |
| `src` | `string` |
| `kind` | `'image' | 'pdf'` |

## `AssetIngestResult`

Campos:

| Field | Type |
|---|---|
| `operation` | `AssetOperationDTO` |
| `asset` | `AssetDTO` |
| `deduplicated` | `boolean` |

## `AssetListOptions`

Campos:

| Field | Type |
|---|---|
| `campaignId` | `string` |
| `kind` | `'image' | 'pdf'` |

## `AssetOperationDTO`

Campos:

| Field | Type |
|---|---|
| `status` | `'ready'` |
| `progress` | `'ready'` |
| `cancelled` | `boolean` |

## `AutomationAuditDTO`

Campos:

| Field | Type |
|---|---|
| `schemaVersion` | `1` |
| `transition` | `string` |
| `jobId` | `string | null` |
| `campaignId` | `string` |
| `packageId` | `string` |
| `actionRef` | `string` |
| `attempt` | `number` |
| `timestamp` | `number` |
| `semanticReason` | `string` |

## `AutomationCancelResult`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `status` | `'cancelled'` |

## `AutomationJobDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `package_id` | `string` |
| `action_id` | `string` |
| `action_version` | `number` |
| `run_at_utc` | `number` |
| `status` | `'pending' | 'running' | 'succeeded' | 'failed' | 'rejected' | 'cancelled'` |
| `attempts` | `number` |
| `error_code` | `string | null` |
| `causal_depth` | `number` |
| `created_at` | `number` |
| `updated_at` | `number` |

## `AutomationScheduleOptions`

Campos:

| Field | Type |
|---|---|
| `version` | `number` |
| `runAtUtc` | `number` |
| `idempotencyKey` | `string` |
| `originExecutionId` | `string` |
| `originJobId` | `string` |
| `causalDepth` | `number` |

## `BlendModeParameterSchemaDTO`

Campos:

| Field | Type |
|---|---|
| `type` | `'enum'` |
| `default` | `'normal'` |
| `options` | `('normal' | 'add' | 'multiply' | 'screen')[]` |

## `BooleanParameterSchemaDTO`

Campos:

| Field | Type |
|---|---|
| `type` | `'boolean'` |
| `default` | `boolean` |

## `BusRequestOptions`

Campos:

| Field | Type |
|---|---|
| `timeoutMs` | `number` |
| `timeout` | `number` |

## `CameraDTO`

Campos:

| Field | Type |
|---|---|
| `worldX` | `number` |
| `worldY` | `number` |
| `zoom` | `number` |

## `CardDeckMutationResult`

Campos:

| Field | Type |
|---|---|
| `deck_instance_id` | `string` |
| `draw_count` | `number` |

## `CardDefinitionDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |
| `version` | `number` |
| `reference` | `string` |
| `label` | `string` |
| `description` | `string` |
| `metadataSchema` | `CardMetadataSchema` |
| `tags` | `string[]` |
| `cards` | `DeclaredCardDTO[]` |

## `CardDefinitionInstantiateOptions`

Campos:

| Field | Type |
|---|---|
| `version` | `number` |
| `name` | `string` |
| `artwork` | `CardArtworkMap` |
| `metadata` | `CardMetadata` |

## `CardDefinitionInstantiateResult`

Campos:

| Field | Type |
|---|---|
| `deck` | `DeckRuntimeDTO` |
| `definition` | `CardDefinitionDTO` |
| `provenance` | `CardProvenanceDTO` |

## `CardDrawOptions`

Campos:

| Field | Type |
|---|---|
| `count` | `number` |
| `destination` | `'hand' | 'pile' | 'chat' | 'scene' | 'discard' | 'removed'` |
| `mode` | `'top' | 'bottom' | 'random' | 'choose'` |
| `targetPileId` | `string` |
| `reveal` | `boolean` |

## `CardDrawResult`

Campos:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `cards` | `CardRuntimeDTO[]` |
| `target_pile_id` | `string` |

## `CardEventDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `event_type` | `string` |
| `created_at` | `number` |

## `CardIdsResult`

Campos:

| Field | Type |
|---|---|
| `card_ids` | `string[]` |

## `CardPileDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `deck_instance_id` | `string` |
| `kind` | `string` |
| `owner_user_id` | `string | null` |
| `visibility` | `string` |

## `CardPlacementDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `scene_id` | `string` |
| `card_instance_id` | `string` |
| `owner_user_id` | `string | null` |
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `z_index` | `number` |
| `face_state` | `'face_up' | 'face_down'` |
| `visibility` | `string` |
| `locked` | `boolean` |

## `CardPlacementDiscardResult`

Campos:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `card_ids` | `string[]` |

## `CardPlacementPatch`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `zIndex` | `number` |
| `faceState` | `'face_up' | 'face_down'` |

## `CardPlacementResult`

Campos:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `placement` | `CardPlacementDTO` |

## `CardPlayOptions`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `faceUp` | `boolean` |

## `CardPlayResult`

Campos:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `placement` | `CardPlacementDTO` |
| `card` | `CardRuntimeDTO | null` |

## `CardProvenanceDTO`

Campos:

| Field | Type |
|---|---|
| `definition` | `string` |
| `packageId` | `string` |
| `definitionVersion` | `number` |
| `instanceMetadata` | `CardMetadata` |

## `CardResetOptions`

Campos:

| Field | Type |
|---|---|
| `shuffle` | `boolean` |

## `CardStateDTO`

Campos:

| Field | Type |
|---|---|
| `campaign_id` | `string` |
| `decks` | `DeckRuntimeDTO[]` |
| `piles` | `CardPileDTO[]` |
| `scene_placements` | `CardPlacementDTO[]` |
| `cards` | `CardRuntimeDTO[]` |

## `ChangedResourceDTO`

Campos:

| Field | Type |
|---|---|
| `type` | `'actor'` |
| `id` | `string` |
| `version` | `number` |

## `ChatListOptions`

Campos:

| Field | Type |
|---|---|
| `limit` | `number` |

## `ChatMessageDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `author_user_id` | `string` |
| `author_name` | `string` |
| `author_role` | `string` |
| `kind` | `string` |
| `content` | `string` |
| `expression` | `string | null` |
| `groups` | `RollGroupDTO[] | null` |
| `modifier` | `number | null` |
| `total` | `number | null` |
| `visibility` | `string` |
| `metadata` | `ChatMetadata` |
| `created_at` | `number` |

## `ChatSendMessage`

Campos:

| Field | Type |
|---|---|
| `content` | `string` |
| `kind` | `string` |
| `visibility` | `string` |

## `ColorParameterSchemaDTO`

Campos:

| Field | Type |
|---|---|
| `type` | `'color'` |
| `default` | `string` |
| `pattern` | `'^#[0-9a-fA-F]{6}$'` |

## `CombatAddInput`

Campos:

| Field | Type |
|---|---|
| `actorIds` | `string[]` |
| `tokenIds` | `string[]` |

## `CombatBarDTO`

Campos:

| Field | Type |
|---|---|
| `value` | `number` |
| `max` | `number` |
| `percent` | `number | null` |
| `visibility` | `string` |

## `CombatConfigDTO`

Campos:

| Field | Type |
|---|---|
| `system_id` | `string` |
| `label` | `string` |
| `input` | `'roll' | 'number' | 'text'` |
| `sort` | `'desc' | 'asc'` |
| `manual_order` | `boolean` |
| `icon` | `string` |
| `accent` | `string` |
| `resources` | `RulesetCombatResources` |

## `CombatFlagsPatch`

Campos:

| Field | Type |
|---|---|
| `hidden` | `boolean` |
| `defeated` | `boolean` |

## `CombatInitiativeOrderEntry`

Campos:

| Field | Type |
|---|---|
| `combatantId` | `string` |
| `value` | `string` |

## `CombatRollInitiativeOptions`

Campos:

| Field | Type |
|---|---|
| `scope` | `'all' | 'one'` |
| `combatantId` | `string` |

## `CombatStartInput`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |

## `CombatStateDTO`

Campos:

| Field | Type |
|---|---|
| `campaign_id` | `string` |
| `combat_id` | `string` |
| `active` | `boolean` |
| `round` | `number` |
| `turn` | `number` |
| `combatants` | `CombatantDTO[]` |
| `current_id` | `string` |
| `current_name` | `string` |
| `next_id` | `string` |
| `next_name` | `string` |
| `config` | `CombatConfigDTO` |
| `updated_actors` | `RulesetEffectMutation[]` |
| `expired_effects` | `RulesetEffectMutation[]` |
| `effect_ticks` | `RulesetEffectMutation[]` |

## `CombatantDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `actor_id` | `string` |
| `token_id` | `string` |
| `name` | `string` |
| `initiative` | `string | null` |
| `hidden` | `boolean` |
| `defeated` | `boolean` |
| `position` | `number` |
| `is_current` | `boolean` |
| `is_next` | `boolean` |
| `has_acted` | `boolean` |
| `can_move_up` | `boolean` |
| `can_move_down` | `boolean` |
| `portrait_url` | `string` |
| `bar` | `CombatBarDTO | null` |
| `conditions_count` | `number` |
| `effects_count` | `number` |

## `ContentLinkDTO`

Campos:

| Field | Type |
|---|---|
| `type` | `'grave-reference'` |
| `ref` | `string` |
| `label` | `string` |
| `icon` | `string` |

## `ContentLinkOptions`

Campos:

| Field | Type |
|---|---|
| `label` | `string` |
| `icon` | `string` |

## `ContentOpenOptions`

Campos:

| Field | Type |
|---|---|
| `source` | `string` |

## `ContentPackDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `type` | `string` |
| `label` | `string` |
| `entries` | `ContentPackEntryDTO[]` |

## `ContentPackEntryDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `name` | `string` |
| `label` | `string` |
| `data` | `ContentPackEntryData` |

## `ContentPackSummaryDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `type` | `string` |
| `label` | `string` |

## `ContentRefOptions`

Campos:

| Field | Type |
|---|---|
| `campaignId` | `string` |
| `parentKind` | `string` |
| `parentId` | `string` |
| `page` | `number` |
| `anchor` | `string` |

## `ContentReferenceDTO`

Campos:

| Field | Type |
|---|---|
| `uri` | `string` |
| `campaignId` | `string` |
| `kind` | `'actor' | 'item' | 'journal' | 'pdf' | 'deck' | 'card' | 'scene' | 'token'` |
| `id` | `string` |
| `parentKind` | `string | null` |
| `parentId` | `string | null` |
| `page` | `number | null` |
| `anchor` | `string | null` |

## `ContentReferenceInput`

Campos:

| Field | Type |
|---|---|
| `kind` | `ContentReferenceDTO['kind']` |
| `id` | `string` |
| `documentId` | `string` |
| `campaignId` | `string` |
| `parentKind` | `string` |
| `parentId` | `string` |
| `page` | `number` |
| `anchor` | `string` |

## `ContentResolutionDTO`

Campos:

| Field | Type |
|---|---|
| `ref` | `ContentReferenceDTO` |
| `value` | `ContentResolvedValue` |

## `ContentSearchEntryDTO`

Campos:

| Field | Type |
|---|---|
| `ref` | `ContentReferenceDTO` |
| `label` | `string` |
| `kind` | `ContentReferenceDTO['kind']` |

## `ContentSearchOptions`

Campos:

| Field | Type |
|---|---|
| `kinds` | `ContentReferenceDTO['kind'][]` |
| `cursor` | `string` |
| `limit` | `number` |

## `ContentSearchPageDTO`

Campos:

| Field | Type |
|---|---|
| `entries` | `ContentSearchEntryDTO[]` |
| `nextCursor` | `string | null` |

## `DeclaredCardArtworkDTO`

Campos:

| Field | Type |
|---|---|
| `kind` | `'campaign-asset-slot'` |

## `DeclaredCardDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `quantity` | `number` |
| `tags` | `string[]` |
| `metadata` | `CardMetadata` |
| `artwork` | `DeclaredCardArtworkDTO` |

## `DiceRollInput`

Campos:

| Field | Type |
|---|---|
| `formula` | `string` |
| `label` | `string` |
| `actorId` | `string` |

## `EffectStateDTO`

Campos:

| Field | Type |
|---|---|
| `particles` | `ParticleDTO[]` |
| `shaders` | `ShaderMetadataDTO[]` |

## `EntityListQuery`

Campos:

| Field | Type |
|---|---|
| `type` | `string` |
| `folderId` | `string` |
| `cursor` | `string` |
| `limit` | `number` |

## `ExpectedVersionOptions`

Campos:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `FogMutationResult`

Campos:

| Field | Type |
|---|---|
| `scene_id` | `string` |
| `enabled` | `boolean` |
| `baseline` | `'hide_all' | 'reveal_all'` |
| `ops` | `FogOp[]` |
| `new_ops` | `FogOp[]` |
| `version` | `number` |

## `FogPaintOptions`

Campos:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `FogStateDTO`

Campos:

| Field | Type |
|---|---|
| `scene_id` | `string` |
| `enabled` | `boolean` |
| `baseline` | `'hide_all' | 'reveal_all'` |
| `ops` | `FogOp[]` |
| `version` | `number` |

## `GeometryBehaviorDTO`

Campos:

| Field | Type |
|---|---|
| `movement` | `'block' | 'pass'` |
| `vision` | `'block' | 'pass'` |
| `light` | `'block' | 'pass'` |

## `HandoutAudience`

Campos:

| Field | Type |
|---|---|
| `type` | `'all' | 'user' | 'role'` |
| `id` | `string` |

## `HandoutPresentResult`

Campos:

| Field | Type |
|---|---|
| `presented` | `true` |

## `InteropProviderContext`

Campos:

| Field | Type |
|---|---|
| `callerPackageId` | `string` |
| `providerPackageId` | `string` |
| `userId` | `string | undefined` |
| `campaignId` | `string | undefined` |
| `permissions` | `PermissionContext | null` |

## `ItemCreateInput`

Campos:

| Field | Type |
|---|---|
| `systemId` | `string` |
| `type` | `string` |
| `name` | `string` |
| `folderId` | `string` |

## `ItemDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `system_id` | `string` |
| `type` | `string` |
| `name` | `string` |
| `folder_id` | `string | null` |
| `portrait_asset_id` | `string | null` |
| `version` | `number` |
| `created_at` | `number` |
| `updated_at` | `number` |

## `ItemDataPatchResult`

Campos:

| Field | Type |
|---|---|
| `item_id` | `string` |
| `version` | `number` |
| `changed_paths` | `string[]` |

## `ItemMutationResult`

Campos:

| Field | Type |
|---|---|
| `item_id` | `string` |
| `version` | `number` |

## `ItemUpdateInput`

Campos:

| Field | Type |
|---|---|
| `name` | `string` |
| `folderId` | `string` |
| `portraitAssetId` | `string` |

## `JournalCreateInput`

Campos:

| Field | Type |
|---|---|
| `type` | `string` |
| `title` | `string` |
| `folderId` | `string` |
| `visibility` | `string` |
| `contentMarkdown` | `string` |
| `data` | `JournalDataInput` |
| `ownerUserIds` | `string[]` |

## `JournalDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `title` | `string` |
| `type` | `string` |
| `folder_id` | `string | null` |
| `visibility` | `string` |
| `version` | `number` |
| `view` | `JournalView` |

## `JournalListOptions`

Campos:

| Field | Type |
|---|---|
| `type` | `string` |
| `folderId` | `string` |
| `limit` | `number` |

## `JournalListResult`

Campos:

| Field | Type |
|---|---|
| `journals` | `JournalDTO[]` |

## `JournalMutationResult`

Campos:

| Field | Type |
|---|---|
| `journal_id` | `string` |
| `version` | `number | null` |

## `JournalUpdatePatch`

Campos:

| Field | Type |
|---|---|
| `title` | `string` |
| `folderId` | `string` |
| `visibility` | `string` |
| `contentMarkdown` | `string` |
| `data` | `JournalDataInput` |
| `ownerUserIds` | `string[]` |

## `LightCreateInput`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |
| `bright_radius` | `number` |
| `dim_radius` | `number` |
| `color` | `string` |
| `intensity` | `number` |
| `animation` | `string` |
| `angle` | `number` |
| `rotation` | `number` |
| `enabled` | `boolean` |

## `LightDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `scene_id` | `string` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |
| `bright_radius` | `number` |
| `dim_radius` | `number` |
| `color` | `string` |
| `intensity` | `number` |
| `animation` | `string` |
| `angle` | `number` |
| `rotation` | `number` |
| `enabled` | `boolean` |
| `updated_at` | `number` |

## `LightDeleteResult`

Campos:

| Field | Type |
|---|---|
| `light_id` | `string` |
| `scene_id` | `string` |

## `LightResult`

Campos:

| Field | Type |
|---|---|
| `light` | `LightDTO` |

## `LightUpdatePatch`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |
| `bright_radius` | `number` |
| `dim_radius` | `number` |
| `color` | `string` |
| `intensity` | `number` |
| `animation` | `string` |
| `angle` | `number` |
| `rotation` | `number` |
| `enabled` | `boolean` |

## `MeasurementResultDTO`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `from` | `WorldPointDTO` |
| `to` | `WorldPointDTO` |
| `worldDistance` | `number` |
| `gridDistance` | `number | null` |
| `gridSize` | `number | null` |

## `NumberParameterSchemaDTO`

Campos:

| Field | Type |
|---|---|
| `type` | `'number'` |
| `default` | `number` |
| `min` | `number` |
| `max` | `number` |

## `PDFPresentationDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `presenter` | `string` |
| `documentId` | `string` |
| `audience` | `string[]` |
| `page` | `number` |
| `version` | `number` |
| `status` | `string` |
| `expiresAt` | `number` |

## `PackageDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `kind` | `string` |
| `version` | `string` |
| `active` | `true` |
| `interop` | `PackageInteropDTO` |

## `PackageInteropDTO`

Campos:

| Field | Type |
|---|---|
| `emits` | `string[]` |
| `listens` | `string[]` |
| `provides` | `string[]` |
| `requires` | `string[]` |

## `ParticleDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `scene_id` | `string` |
| `x` | `number` |
| `y` | `number` |
| `kind` | `string` |
| `scale` | `number` |
| `density` | `number` |
| `color` | `string` |
| `enabled` | `boolean` |
| `updated_at` | `number` |

## `ParticleDeleteResult`

Campos:

| Field | Type |
|---|---|
| `emitter_id` | `string` |
| `scene_id` | `string` |

## `ParticlePresetDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `parameters` | `ParticleParameterSchemas` |

## `ParticleResultDTO`

Campos:

| Field | Type |
|---|---|
| `emitter` | `ParticleDTO` |

## `ParticleValues`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `kind` | `string` |
| `scale` | `number` |
| `density` | `number` |
| `color` | `string` |
| `enabled` | `boolean` |

## `PdfAnnotationDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `document_id` | `string` |
| `author_user_id` | `string` |
| `page` | `number` |
| `region` | `PdfRegionDTO` |
| `text` | `string` |
| `created_at` | `number` |
| `updated_at` | `number` |

## `PdfAnnotationDeleteResult`

Campos:

| Field | Type |
|---|---|
| `annotation_id` | `string` |

## `PdfAnnotationInput`

Campos:

| Field | Type |
|---|---|
| `page` | `number` |
| `region` | `PdfRegionDTO` |
| `text` | `string` |

## `PdfAnnotationResult`

Campos:

| Field | Type |
|---|---|
| `annotation` | `PdfAnnotationDTO` |

## `PdfDocumentDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `filename` | `string` |
| `content_type` | `'application/pdf'` |
| `byte_size` | `number` |
| `created_at` | `number` |
| `url` | `string` |

## `PdfMetadataDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `filename` | `string` |
| `content_type` | `'application/pdf'` |
| `byte_size` | `number` |
| `created_at` | `number` |

## `PdfPresentationStartInput`

Campos:

| Field | Type |
|---|---|
| `audience` | `string[]` |
| `page` | `number` |
| `ttlSeconds` | `number` |

## `PdfRegionDTO`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `width` | `number` |
| `height` | `number` |
| `x1` | `number` |
| `y1` | `number` |
| `x2` | `number` |
| `y2` | `number` |

## `PdfViewerOpenOptions`

Campos:

| Field | Type |
|---|---|
| `host` | `HTMLElement` |
| `assetUrl` | `string` |
| `page` | `number` |
| `zoom` | `number` |
| `spread` | `boolean` |
| `anchor` | `string` |
| `onPageChange` | `(page: number) => void` |

## `PermissionCheckDTO`

Campos:

| Field | Type |
|---|---|
| `action` | `string` |
| `supported` | `boolean` |
| `allowed` | `boolean` |
| `reason` | `'ALLOWED' | 'DENIED' | 'UNKNOWN_ACTION'` |

## `PermissionResource`

Campos:

| Field | Type |
|---|---|
| `actorId` | `string` |
| `itemId` | `string` |
| `tokenId` | `string` |
| `sceneId` | `string` |
| `id` | `string` |

## `RollGroupDTO`

Campos:

| Field | Type |
|---|---|
| `faces` | `number` |
| `results` | `number[]` |
| `subtotal` | `number` |

## `RollIntentInput`

Campos:

| Field | Type |
|---|---|
| `actorId` | `string` |
| `actionId` | `string` |
| `inputs` | `ActionInput` |
| `rollOptions` | `RollOptions` |
| `targetActorId` | `string` |
| `targetTokenId` | `string` |
| `target` | `RollTarget` |

## `RollResultDTO`

Campos:

| Field | Type |
|---|---|
| `actor_id` | `string` |
| `type` | `string` |
| `label` | `string` |
| `expression` | `string` |
| `groups` | `RollGroupDTO[]` |
| `modifier` | `number` |
| `total` | `number` |
| `visibility` | `string` |
| `metadata` | `RollMetadata` |
| `applied` | `RollAppliedMutation[]` |

## `RollTarget`

Campos:

| Field | Type |
|---|---|
| `actorId` | `string` |
| `tokenId` | `string` |

## `SceneDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `name` | `string` |
| `width` | `number` |
| `height` | `number` |
| `version` | `number` |
| `scene_epoch` | `number` |
| `tile_table_version` | `number` |
| `grid_size` | `number` |
| `raster_tile_size` | `number` |
| `chunk_span` | `number` |
| `grid_visible` | `boolean` |
| `grid_color` | `string` |
| `grid_opacity` | `number` |
| `darkness` | `number` |
| `start_world_x` | `number` |
| `start_world_y` | `number` |
| `start_zoom` | `number` |

## `SceneImageDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `scene_id` | `string` |
| `asset_id` | `string` |
| `owner_user_id` | `string | null` |
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `z_index` | `number` |
| `natural_width` | `number` |
| `natural_height` | `number` |
| `version` | `number` |
| `locked` | `boolean` |
| `gm_only` | `boolean` |
| `layer` | `string` |
| `metadata` | `SceneImageMetadata` |
| `created_at` | `number` |
| `updated_at` | `number` |
| `src` | `string` |

## `SceneImageDeleteResult`

Campos:

| Field | Type |
|---|---|
| `placement_id` | `string` |
| `scene_id` | `string` |

## `SceneImageListResult`

Campos:

| Field | Type |
|---|---|
| `placements` | `SceneImageDTO[]` |

## `SceneImagePlaceOptions`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `layer` | `string` |

## `SceneImageResult`

Campos:

| Field | Type |
|---|---|
| `placement` | `SceneImageDTO` |

## `SceneImageUpdatePatch`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `zIndex` | `number` |
| `layer` | `string` |
| `assetId` | `string` |

## `SceneTemplateDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `shape` | `'circle' | 'cone' | 'line' | 'rectangle'` |
| `origin` | `WorldPointDTO` |
| `target` | `WorldPointDTO` |
| `creatorId` | `string` |
| `audience` | `'campaign' | 'gm'` |
| `persistence` | `'persistent'` |
| `version` | `number` |

## `SceneTemplateDeleteResult`

Campos:

| Field | Type |
|---|---|
| `template_id` | `string` |
| `scene_id` | `string` |
| `version` | `number` |
| `audience` | `'campaign' | 'gm'` |

## `SceneTemplateListResult`

Campos:

| Field | Type |
|---|---|
| `templates` | `SceneTemplateDTO[]` |
| `version` | `number` |

## `SceneTemplateResult`

Campos:

| Field | Type |
|---|---|
| `template` | `SceneTemplateDTO` |

## `SceneTemplateValues`

Campos:

| Field | Type |
|---|---|
| `shape` | `'circle' | 'cone' | 'line' | 'rectangle'` |
| `origin` | `WorldPointDTO` |
| `target` | `WorldPointDTO` |
| `audience` | `'campaign' | 'gm'` |

## `SdkContextDTO`

Campos:

| Field | Type |
|---|---|
| `campaign` | `CampaignContext | null` |
| `scene` | `SceneContext | null` |
| `user` | `UserContext | null` |
| `permissions` | `PermissionContext | null` |

## `SettingChangeDTO`

Campos:

| Field | Type |
|---|---|
| `packageId` | `string` |
| `key` | `string` |
| `value` | `SettingValue` |
| `previous` | `SettingValue | undefined` |
| `scope` | `SettingScope` |

## `SettingDefinitionDTO`

Campos:

| Field | Type |
|---|---|
| `key` | `string` |
| `scope` | `SettingScope` |
| `type` | `string` |
| `default` | `SettingValue` |
| `label` | `string` |
| `options` | `SettingValue[]` |
| `minimum` | `number | null` |
| `maximum` | `number | null` |
| `pattern` | `string` |

## `SettingSetOptions`

Campos:

| Field | Type |
|---|---|
| `campaignId` | `string` |

## `SettingSetResult`

Campos:

| Field | Type |
|---|---|
| `success` | `true` |
| `package_id` | `string` |
| `key` | `string` |
| `value` | `SettingValue` |
| `scope` | `SettingScope` |

## `ShaderApplyInput`

Campos:

| Field | Type |
|---|---|
| `presetId` | `string` |
| `schemaVersion` | `number` |
| `parameters` | `ShaderParameterValues` |

## `ShaderInstanceDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `presetId` | `string` |
| `schemaVersion` | `number` |
| `version` | `number` |
| `parameters` | `ShaderParameterValues` |

## `ShaderMetadataDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `scene_id` | `string` |
| `name` | `string` |
| `x` | `number` |
| `y` | `number` |
| `radius` | `number` |
| `rotation` | `number` |
| `blend_mode` | `string` |
| `opacity` | `number` |
| `intensity` | `number` |
| `scale` | `number` |
| `speed` | `number` |
| `color` | `string` |
| `enabled` | `boolean` |
| `updated_at` | `number` |

## `ShaderParameterValues`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `radius` | `number` |
| `rotation` | `number` |
| `opacity` | `number` |
| `intensity` | `number` |
| `scale` | `number` |
| `speed` | `number` |
| `color` | `string` |
| `blendMode` | `'normal' | 'add' | 'multiply' | 'screen'` |
| `enabled` | `boolean` |

## `ShaderPresetDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `number` |
| `labelKey` | `string` |
| `descriptionKey` | `string` |
| `parameters` | `ShaderPresetParametersDTO` |

## `ShaderPresetParametersDTO`

Campos:

| Field | Type |
|---|---|
| `x` | `NumberParameterSchemaDTO` |
| `y` | `NumberParameterSchemaDTO` |
| `radius` | `NumberParameterSchemaDTO` |
| `rotation` | `NumberParameterSchemaDTO` |
| `opacity` | `NumberParameterSchemaDTO` |
| `intensity` | `NumberParameterSchemaDTO` |
| `scale` | `NumberParameterSchemaDTO` |
| `speed` | `NumberParameterSchemaDTO` |
| `color` | `ColorParameterSchemaDTO` |
| `blendMode` | `BlendModeParameterSchemaDTO` |
| `enabled` | `BooleanParameterSchemaDTO` |

## `ShaderRemovalResult`

Campos:

| Field | Type |
|---|---|
| `instance_id` | `string` |
| `scene_id` | `string` |

## `ShaderUpdateInput`

Campos:

| Field | Type |
|---|---|
| `parameters` | `ShaderParameterValues` |
| `x` | `number` |
| `y` | `number` |
| `radius` | `number` |
| `rotation` | `number` |
| `opacity` | `number` |
| `intensity` | `number` |
| `scale` | `number` |
| `speed` | `number` |
| `color` | `string` |
| `blendMode` | `'normal' | 'add' | 'multiply' | 'screen'` |
| `enabled` | `boolean` |

## `SharedMeasurementDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `creator` | `string` |
| `sceneId` | `string` |
| `geometry` | `SharedMeasurementGeometry` |
| `audience` | `'self' | 'campaign' | 'gm'` |
| `expiresAt` | `number` |
| `version` | `number` |

## `SharedMeasurementGeometry`

Campos:

| Field | Type |
|---|---|
| `points` | `WorldPointDTO[]` |

## `SharedMeasurementOptions`

Campos:

| Field | Type |
|---|---|
| `audience` | `'self' | 'campaign' | 'gm'` |
| `ttlSeconds` | `number` |

## `SheetActionEvent`

Campos:

| Field | Type |
|---|---|
| `name` | `string` |
| `event` | `Event` |
| `element` | `HTMLElement` |

## `SheetController`

Campos:

| Field | Type |
|---|---|
| `setup` | `(context: SheetControllerContext) => void` |
| `mount` | `(context: SheetControllerContext) => void` |
| `update` | `(context: SheetControllerContext) => void` |
| `unmount` | `(context: SheetControllerContext) => void` |
| `onAction` | `(action: SheetActionEvent, context: SheetControllerContext) => boolean | void` |

## `SheetDataPatchResult`

Campos:

| Field | Type |
|---|---|
| `actor_id` | `string` |
| `version` | `number` |
| `changed_paths` | `string[]` |

## `StorageExecuteResult`

Campos:

| Field | Type |
|---|---|
| `success` | `true` |
| `rowcount` | `number` |

## `StorageQueryResult`

Campos:

| Field | Type |
|---|---|
| `success` | `true` |
| `rows` | `StorageRow[]` |

## `StorageStatusDTO`

Campos:

| Field | Type |
|---|---|
| `success` | `true` |
| `scope` | `'campaign' | 'global'` |
| `ready` | `boolean` |
| `size_bytes` | `number` |

## `ToastHandle`

Campos:

| Field | Type |
|---|---|
| `dismiss` | `() => void` |

## `ToastOptions`

Campos:

| Field | Type |
|---|---|
| `duration` | `number` |
| `id` | `string | null` |
| `onClick` | `(toast: HTMLElement) => void` |

## `TokenCreateInput`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `actorId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |

## `TokenDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `scene_id` | `string` |
| `actor_id` | `string | null` |
| `grid_x` | `number` |
| `grid_y` | `number` |
| `elevation` | `number` |
| `width_cells` | `number` |
| `height_cells` | `number` |
| `rotation` | `number` |
| `name` | `string | null` |
| `token_asset_url` | `string | null` |
| `visible` | `boolean` |
| `hidden` | `boolean` |
| `locked` | `boolean` |
| `disposition` | `string` |
| `vision` | `TokenVisionDTO` |
| `updated_at` | `number` |

## `TokenMoveInput`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |

## `TokenMutationResult`

Campos:

| Field | Type |
|---|---|
| `token` | `TokenDTO | null` |
| `tokens` | `TokenDTO[]` |

## `TokenOptions`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `expectedVersion` | `number` |

## `TokenReadOptions`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `limit` | `number` |

## `TokenVisionDTO`

Campos:

| Field | Type |
|---|---|
| `enabled` | `boolean` |
| `range` | `number | null` |
| `source` | `'token'` |

## `ToolContextDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |

## `ToolDefinition`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `icon` | `string` |
| `cursor` | `string` |
| `capability` | `string` |
| `when` | `(context: SdkContextDTO) => boolean` |
| `activate` | `(context: ToolContextDTO) => void` |
| `deactivate` | `(context: ToolContextDTO) => void` |
| `pointer` | `(event: ToolPointerEventDTO) => void` |

## `ToolModifiersDTO`

Campos:

| Field | Type |
|---|---|
| `alt` | `boolean` |
| `ctrl` | `boolean` |
| `meta` | `boolean` |
| `shift` | `boolean` |

## `ToolPointerEventDTO`

Campos:

| Field | Type |
|---|---|
| `phase` | `'down' | 'move' | 'up' | 'cancel'` |
| `world` | `WorldPointDTO` |
| `button` | `number` |
| `modifiers` | `ToolModifiersDTO` |

## `VerticalBoundsDTO`

Campos:

| Field | Type |
|---|---|
| `bottom` | `number | null` |
| `top` | `number | null` |

## `WallCreateInput`

Campos:

| Field | Type |
|---|---|
| `kind` | `'wall' | 'door'` |
| `x1` | `number` |
| `y1` | `number` |
| `x2` | `number` |
| `y2` | `number` |
| `behavior` | `GeometryBehaviorDTO` |
| `presentation` | `string` |
| `vertical` | `VerticalBoundsDTO` |

## `WallDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `scene_id` | `string` |
| `kind` | `string` |
| `door_state` | `string | null` |
| `x1` | `number` |
| `y1` | `number` |
| `x2` | `number` |
| `y2` | `number` |
| `presentation` | `string | null` |
| `discovered` | `boolean` |
| `behavior` | `GeometryBehaviorDTO` |
| `vertical` | `VerticalBoundsDTO` |
| `updated_at` | `number` |

## `WallDeleteResult`

Campos:

| Field | Type |
|---|---|
| `wall_id` | `string` |
| `scene_id` | `string` |

## `WallResult`

Campos:

| Field | Type |
|---|---|
| `wall` | `WallDTO` |

## `WallUpdatePatch`

Campos:

| Field | Type |
|---|---|
| `kind` | `'wall' | 'door'` |
| `door_state` | `string | null` |
| `x1` | `number` |
| `y1` | `number` |
| `x2` | `number` |
| `y2` | `number` |
| `behavior` | `GeometryBehaviorDTO` |
| `presentation` | `string` |
| `discovered` | `boolean` |
| `vertical` | `VerticalBoundsDTO` |

## `WallsDeleteResult`

Campos:

| Field | Type |
|---|---|
| `wall_ids` | `string[]` |
| `scene_id` | `string | null` |

## `WallsResult`

Campos:

| Field | Type |
|---|---|
| `scene_id` | `string` |
| `walls` | `WallDTO[]` |

## `WorldPointDTO`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |

## `ActionInput`

Definição: `JsonObject`

## `ActionInputSchema`

Definição: `JsonObject`

## `ActorItemCopyDTO`

Definição: `{ id: string; sourceItemId: string } & RulesetItemCopyFields`

## `ApplicationContext`

Definição: `JsonObject`

## `ApplicationParts`

Definição: `{ [partId: string]: ((context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>) | { render: (context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>; activate?: (root: HTMLElement, context: ApplicationContext) => Disposer | void } }`

## `BusResponse`

Definição: `{ ok: true; value: InteropPayload } | { ok: false; error: { code: string; message: string } }`

## `CampaignContext`

Definição: `JsonObject`

## `CardArtworkMap`

Definição: `{ [cardId: string]: string }`

## `CardRuntimeDTO`

Definição: `JsonObject`

## `ChatMetadata`

Definição: `JsonObject`

## `CombatPanelDefinition`

Definição: `JsonObject`

## `CombatPlugin`

Definição: `JsonObject`

## `CombatProtocolPayload`

Definição: `JsonObject`

## `CommandHandler`

Definição: `(payload: CommandPayload) => void | Promise<void>`

## `CommandPayload`

Definição: `JsonValue`

## `ContentPackEntryData`

Definição: `JsonObject`

## `ContentResolvedValue`

Definição: `ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO`

## `DeckRuntimeDTO`

Definição: `JsonObject`

## `Disposer`

Definição: `() => void`

## `FogOp`

Definição: `{ mode: 'reveal' | 'hide'; shape: 'circle'; geom: { center_x_cells: number; center_y_cells: number; radius_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'square'; geom: { center_x_cells: number; center_y_cells: number; size_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'polygon'; geom: { points_cells: [number, number][] } }`

## `InteropHandler`

Definição: `(payload: InteropPayload, context: InteropProviderContext) => InteropPayload | Promise<InteropPayload>`

## `InteropPayload`

Definição: `JsonValue`

## `InteropSubscriber`

Definição: `(payload: InteropPayload) => void`

## `JournalDataInput`

Definição: `JsonObject`

## `JournalView`

Definição: `JsonObject`

## `PackageLifecyclePayload`

Definição: `JsonObject`

## `ParticleParameterSchemas`

Definição: `JsonObject`

## `PdfSearchMatch`

Definição: `JsonObject`

## `PdfViewerHostState`

Definição: `JsonObject`

## `PdfViewerOpenResult`

Definição: `PdfDocumentDTO & PdfViewerHostState & { page: number }`

## `PermissionContext`

Definição: `JsonObject`

## `RollAppliedMutation`

Definição: `JsonObject`

## `RollMetadata`

Definição: `JsonObject`

## `RollOptions`

Definição: `JsonObject`

## `RulesetCombatResources`

Definição: `JsonObject`

## `RulesetEffectMutation`

Definição: `JsonObject`

## `RulesetItemCopyFields`

Definição: `JsonObject`

## `RulesetSheetData`

Definição: `JsonObject`

## `SceneContext`

Definição: `JsonObject`

## `SceneImageMetadata`

Definição: `JsonObject`

## `SdkEvent`

Definição: `Readonly<{ type: SdkEventName; version: number; resourceId?: string; sceneId?: string }>`

## `SdkEventHandler`

Definição: `(event: SdkEvent) => void`

## `SdkEventName`

Definição: `string`

## `SettingChangeHandler`

Definição: `(change: SettingChangeDTO) => void`

## `SettingScope`

Definição: `'client' | 'campaign' | 'package'`

## `SettingValue`

Definição: `string | number | boolean | null | string[]`

## `SettingValues`

Definição: `{ [key: string]: SettingValue }`

## `SheetControllerContext`

Definição: `JsonObject`

## `SheetHelpers`

Definição: `{ el: (tag: string, attributes?: JsonObject, ...children: (Node | string)[]) => HTMLElement; phIcon: (name: string) => HTMLElement; getPath: (value: JsonObject, path: string) => SheetValue | undefined; formatMod: (value: number) => string; cssIdent: (value: string) => string; nonEmptyParts: (...parts: string[]) => string[]; closeFloatingSheetMenus: () => void; postJSON: (url: string, payload: JsonObject) => Promise<SheetHttpResult>; refresh: (root: HTMLElement) => Promise<void>; getContext: (root: HTMLElement) => SheetControllerContext | undefined; getLabels: (systemId: string) => JsonObject }`

## `SheetHttpResult`

Definição: `JsonValue`

## `SheetPlugin`

Definição: `JsonObject`

## `SheetValue`

Definição: `JsonValue`

## `SlotRenderCallback`

Definição: `(host: HTMLElement, context: SdkContextDTO) => void`

## `StorageParams`

Definição: `JsonObject`

## `StorageRow`

Definição: `JsonObject`

## `TokenOverrides`

Definição: `JsonObject`

## `UserContext`

Definição: `JsonObject`

# Tipos semânticos extensíveis

## `ActionInput`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `ActionInputSchema`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `ApplicationContext`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `ApplicationParts`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CampaignContext`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CardArtworkMap`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CardMetadata`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CardMetadataSchema`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CardRuntimeDTO`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `ChatMetadata`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CombatPanelDefinition`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CombatPlugin`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CombatProtocolPayload`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `CommandPayload`

Definição: `JsonValue`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `ContentPackEntryData`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `ContentResolvedValue`

Definição: `ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `DeckRuntimeDTO`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `JournalDataInput`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `JournalView`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `PackageLifecyclePayload`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `ParticleParameterSchemas`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `PdfSearchMatch`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `PdfViewerHostState`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `PermissionContext`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `RollAppliedMutation`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `RollMetadata`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `RollOptions`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `RulesetCombatResources`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `RulesetEffectMutation`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `RulesetItemCopyFields`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `RulesetSheetData`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `SceneContext`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `SceneImageMetadata`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `SettingValues`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `SheetControllerContext`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `SheetHttpResult`

Definição: `JsonValue`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `SheetPlugin`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `SheetValue`

Definição: `JsonValue`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `StorageParams`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `StorageRow`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `TokenOverrides`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.

## `UserContext`

Definição: `JsonObject`

Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.
