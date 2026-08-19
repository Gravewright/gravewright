# Referencia de DTOs y tipos de SDK 1

Estructuras canónicas generadas desde el registro de DTOs/inputs de SDK 1.

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

## `ActionReferenceDTO`

Campos:

| Field | Type |
|---|---|
| `provider` | `string` |
| `id` | `string` |
| `version` | `number` |

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
| `kind` | `'image' | 'pdf' | 'audio'` |

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
| `kind` | `'image' | 'pdf' | 'audio'` |

## `AssetOperationDTO`

Campos:

| Field | Type |
|---|---|
| `status` | `'ready'` |
| `progress` | `'ready'` |
| `cancelled` | `boolean` |

## `AssetReferenceDTO`

Campos:

| Field | Type |
|---|---|
| `kind` | `'library-asset' | 'package-asset'` |
| `id` | `string` |

## `AudienceDTO`

Campos:

| Field | Type |
|---|---|
| `kind` | `'self' | 'users' | 'campaign' | 'gm'` |
| `ids` | `string[]` |

## `AudioAssetReferenceDTO`

Campos:

| Field | Type |
|---|---|
| `kind` | `'library-asset' | 'package-asset'` |
| `id` | `string` |

## `AudioListOptions`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |

## `AudioMutationOptions`

Campos:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |
| `fade` | `FadeDTO` |

## `AudioPlayInput`

Campos:

| Field | Type |
|---|---|
| `asset` | `AudioAssetReferenceDTO` |
| `channel` | `'music' | 'ambience' | 'sfx' | 'cinematic'` |
| `loop` | `boolean` |
| `gain` | `number` |
| `audience` | `AudienceDTO` |
| `sceneId` | `string` |
| `worldAnchor` | `SemanticAnchorDTO` |
| `fade` | `FadeDTO` |
| `idempotencyKey` | `string` |

## `AudioPlaybackDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `asset` | `AudioAssetReferenceDTO` |
| `channel` | `'music' | 'ambience' | 'sfx' | 'cinematic'` |
| `state` | `'pending-user-unlock' | 'playing' | 'paused' | 'stopped' | 'failed'` |
| `loop` | `boolean` |
| `gain` | `number` |
| `audience` | `AudienceDTO` |
| `sceneId` | `string | null` |
| `worldAnchor` | `SemanticAnchorDTO | null` |
| `startedAt` | `number` |
| `expiresAt` | `number | null` |
| `fade` | `FadeDTO | null` |
| `version` | `number` |
| `ownerPackageId` | `string` |

## `AudioPlaybackPatch`

Campos:

| Field | Type |
|---|---|
| `gain` | `number` |
| `state` | `'playing' | 'paused'` |
| `loop` | `boolean` |
| `fade` | `FadeDTO` |

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

## `CampaignMemberDTO`

Campos:

| Field | Type |
|---|---|
| `userId` | `string` |
| `role` | `string` |
| `name` | `string` |

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

## `CustomShaderDefinition`

Campos:

| Field | Type |
|---|---|
| `format` | `'gravewright-custom-shader'` |
| `version` | `1` |
| `definition` | `CustomShaderValues` |

## `CustomShaderPreviewResult`

Campos:

| Field | Type |
|---|---|
| `active` | `boolean` |

## `CustomShaderProviderDefinition`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `description` | `string` |
| `open` | `(context: SdkContextDTO) => void | Promise<void>` |

## `CustomShaderUseResult`

Campos:

| Field | Type |
|---|---|
| `accepted` | `true` |

## `CustomShaderValues`

Campos:

| Field | Type |
|---|---|
| `source` | `string` |
| `opacity` | `number` |
| `intensity` | `number` |
| `scale` | `number` |
| `speed` | `number` |
| `rotation` | `number` |
| `radius` | `number` |
| `color` | `string` |
| `blend_mode` | `'normal' | 'add' | 'multiply' | 'screen'` |
| `enabled` | `boolean` |

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

## `DragSourceDefinition`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `referenceKinds` | `string[]` |
| `operations` | `string[]` |
| `schemaVersion` | `1` |

## `DropTargetDefinition`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `surface` | `string` |
| `targetKinds` | `DropTargetKind[]` |
| `worldObjectTypeId` | `string` |
| `operations` | `string[]` |
| `actionReference` | `string` |
| `schemaVersion` | `1` |

## `DropTargetResource`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `typeId` | `string` |

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

## `FadeDTO`

Campos:

| Field | Type |
|---|---|
| `durationMs` | `number` |
| `curve` | `'linear' | 'ease-in' | 'ease-out'` |

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

## `GameplayFlowDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaignId` | `string` |
| `sceneId` | `string | null` |
| `definitionId` | `string` |
| `providerPackageId` | `string` |
| `status` | `'ACTIVE' | 'COMPLETED' | 'CANCELLED'` |
| `phaseId` | `string | null` |
| `round` | `number` |
| `cycle` | `number` |
| `participants` | `string[]` |
| `activeParticipants` | `string[]` |
| `submissions` | `GameplaySubmissions` |
| `revealed` | `boolean` |
| `version` | `number` |

## `GameplayFlowDefinitionDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `1` |
| `turnModel` | `GameplayTurnModel` |
| `phases` | `GameplayPhaseDTO[]` |
| `packageId` | `string` |

## `GameplayFlowMutationOptions`

Campos:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `GameplayFlowStartInput`

Campos:

| Field | Type |
|---|---|
| `definitionId` | `string` |
| `participants` | `string[]` |
| `sceneId` | `string` |
| `idempotencyKey` | `string` |

## `GameplayPhaseDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `submissionPolicy` | `'all'` |
| `deadlineSeconds` | `number` |

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

## `InputBindingDTO`

Campos:

| Field | Type |
|---|---|
| `user_id` | `string` |
| `package_id` | `string` |
| `command_id` | `string` |
| `binding` | `string` |
| `version` | `number` |

## `InputBindingOptions`

Campos:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `InputCommandDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |
| `label` | `string` |
| `contexts` | `string[]` |
| `registeredAction` | `string` |
| `actionInput` | `ActionInput` |

## `InputCommandDefinition`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `description` | `string` |
| `contexts` | `string[]` |
| `registeredAction` | `string` |
| `actionInput` | `ActionInput` |
| `defaultBindings` | `string[]` |

## `InputCommandInvocationDTO`

Campos:

| Field | Type |
|---|---|
| `commandId` | `string` |
| `packageId` | `string` |
| `source` | `'binding' | 'gesture'` |
| `binding` | `string | null` |
| `context` | `string` |

## `InputGestureDefinition`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `gesture` | `'tap' | 'double-tap' | 'long-press' | 'drag' | 'pan' | 'cancel'` |
| `commandId` | `string` |

## `InteractionChoiceDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |

## `InteractionDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `kind` | `string` |
| `schemaVersion` | `1` |
| `requester` | `string` |
| `recipients` | `string[]` |
| `prompt` | `InteractionPromptDTO` |
| `responseSchema` | `InteractionResponseSchema` |
| `visibility` | `'requester' | 'participants' | 'public-after-close'` |
| `deadline` | `number` |
| `status` | `'open' | 'completed' | 'expired' | 'cancelled'` |
| `responses` | `{ [userId: string]: InteractionResponseDTO }` |
| `version` | `number` |
| `origin` | `InteractionOriginDTO` |
| `packageProvenance` | `PackageProvenanceDTO` |
| `createdAt` | `number` |
| `expiresAt` | `number` |

## `InteractionListOptions`

Campos:

| Field | Type |
|---|---|
| `status` | `'open' | 'completed' | 'expired' | 'cancelled'` |
| `recipient` | `'me'` |

## `InteractionMutationOptions`

Campos:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |
| `idempotencyKey` | `string` |

## `InteractionOriginDTO`

Campos:

| Field | Type |
|---|---|
| `originExecutionId` | `string` |
| `originJobId` | `string` |
| `causalDepth` | `number` |
| `resourceRef` | `string` |

## `InteractionPromptDTO`

Campos:

| Field | Type |
|---|---|
| `title` | `string` |
| `text` | `string` |

## `InteractionRequestInput`

Campos:

| Field | Type |
|---|---|
| `kind` | `string` |
| `recipients` | `string[]` |
| `title` | `string` |
| `text` | `string` |
| `responseSchema` | `InteractionResponseSchema` |
| `visibility` | `'requester' | 'participants' | 'public-after-close'` |
| `deadline` | `number` |
| `responsePolicy` | `'immutable' | 'replace'` |
| `origin` | `InteractionOriginDTO` |

## `InteractionResponseDTO`

Campos:

| Field | Type |
|---|---|
| `value` | `InteractionResponseValue` |
| `respondedAt` | `number` |
| `idempotencyKey` | `string` |

## `InteractionResponseSchema`

Campos:

| Field | Type |
|---|---|
| `type` | `'boolean' | 'single-choice' | 'multi-choice' | 'number' | 'string'` |
| `choices` | `InteractionChoiceDTO[]` |
| `maxSelections` | `number` |
| `minimum` | `number` |
| `maximum` | `number` |
| `maxLength` | `number` |

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

## `PackageProvenanceDTO`

Campos:

| Field | Type |
|---|---|
| `packageId` | `string` |
| `providerId` | `string | null` |

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

## `PresentationAnchor`

Campos:

| Field | Type |
|---|---|
| `kind` | `'token' | 'scene-object'` |
| `id` | `string` |
| `sceneId` | `string` |

## `PresentationAudience`

Campos:

| Field | Type |
|---|---|
| `kind` | `'self' | 'campaign' | 'gm' | 'users'` |
| `ids` | `string[]` |

## `PresentationButton`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `actionReference` | `string` |

## `PresentationCloseResult`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `status` | `'closed'` |

## `PresentationCompletionPolicy`

Campos:

| Field | Type |
|---|---|
| `policy` | `'server-time' | 'all-connected-recipients'` |
| `timeoutMs` | `number` |

## `PresentationContent`

Campos:

| Field | Type |
|---|---|
| `title` | `string` |
| `subtitle` | `string` |
| `text` | `string` |
| `label` | `string` |
| `icon` | `string` |
| `asset` | `AssetReferenceDTO` |
| `progress` | `number` |
| `value` | `number` |
| `preset` | `string` |
| `buttons` | `PresentationButton[]` |

## `PresentationDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaignId` | `string` |
| `packageId` | `string` |
| `ownerUserId` | `string` |
| `sceneId` | `string | null` |
| `mode` | `'world-anchor' | 'screen-overlay' | 'title-card' | 'countdown' | 'fade'` |
| `content` | `PresentationContent` |
| `audience` | `PresentationAudience` |
| `anchor` | `PresentationAnchor | null` |
| `deadline` | `number | null` |
| `status` | `'active' | 'completed' | 'closed' | 'cancelled'` |
| `startedAt` | `number` |
| `endsAt` | `number` |
| `completedAt` | `number | null` |
| `completionReason` | `'server-time' | 'recipients' | 'timeout' | 'closed' | 'package-unload' | null` |
| `completionPolicy` | `PresentationCompletionPolicy` |
| `recipientSummary` | `PresentationRecipientSummary` |
| `version` | `number` |
| `createdAt` | `number` |
| `updatedAt` | `number` |
| `expiresAt` | `number` |

## `PresentationInput`

Campos:

| Field | Type |
|---|---|
| `mode` | `'world-anchor' | 'screen-overlay' | 'title-card' | 'countdown' | 'fade'` |
| `content` | `PresentationContent` |
| `audience` | `PresentationAudience` |
| `anchor` | `PresentationAnchor` |
| `sceneId` | `string` |
| `duration` | `number` |
| `deadline` | `number` |
| `completion` | `PresentationCompletionPolicy` |

## `PresentationListOptions`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |

## `PresentationPatch`

Campos:

| Field | Type |
|---|---|
| `content` | `PresentationContent` |
| `anchor` | `PresentationAnchor` |

## `PresentationRecipientSummary`

Campos:

| Field | Type |
|---|---|
| `expected` | `number` |
| `completed` | `number` |

## `PresentationWaitOptions`

Campos:

| Field | Type |
|---|---|
| `timeoutMs` | `number` |

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

## `SceneNavigationDTO`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `recipientIds` | `string[]` |
| `states` | `SceneNavigationStateDTO[]` |

## `SceneNavigationInput`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `recipients` | `AudienceDTO` |
| `reason` | `string` |
| `idempotencyKey` | `string` |

## `SceneNavigationRecipients`

Campos:

| Field | Type |
|---|---|
| `kind` | `'self' | 'users' | 'gm' | 'campaign'` |
| `ids` | `string[]` |

## `SceneNavigationStateDTO`

Campos:

| Field | Type |
|---|---|
| `campaignId` | `string` |
| `userId` | `string` |
| `sceneId` | `string` |
| `reason` | `string` |
| `version` | `number` |
| `updatedAt` | `number` |

## `SceneObjectAudience`

Campos:

| Field | Type |
|---|---|
| `kind` | `'campaign' | 'gm' | 'users'` |
| `ids` | `string[]` |

## `SceneObjectDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `typeId` | `string` |
| `providerPackageId` | `string` |
| `schemaVersion` | `number` |
| `geometry` | `SceneObjectGeometry` |
| `transform` | `SceneObjectTransform` |
| `presentation` | `JsonObject` |
| `interactions` | `SceneObjectInteractionDefinition[]` |
| `editor` | `JsonObject` |
| `dataSchema` | `ActionInputSchema` |
| `data` | `JsonObject` |
| `audience` | `SceneObjectAudience` |
| `enabled` | `boolean` |
| `providerAvailable` | `boolean` |
| `providerStatus` | `'available' | 'unavailable' | 'outdated'` |
| `version` | `number` |
| `createdAt` | `number` |
| `updatedAt` | `number` |

## `SceneObjectDeleteResult`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SceneObjectGeometry`

Campos:

| Field | Type |
|---|---|
| `kind` | `'point' | 'rect' | 'circle' | 'polygon' | 'polyline'` |
| `x` | `number` |
| `y` | `number` |
| `radius` | `number` |
| `width` | `number` |
| `height` | `number` |
| `points` | `WorldPointDTO[]` |

## `SceneObjectHitTestOptions`

Campos:

| Field | Type |
|---|---|
| `tolerance` | `number` |

## `SceneObjectInput`

Campos:

| Field | Type |
|---|---|
| `typeId` | `string` |
| `geometry` | `SceneObjectGeometry` |
| `transform` | `Partial<SceneObjectTransform>` |
| `presentation` | `JsonObject` |
| `data` | `JsonObject` |
| `audience` | `SceneObjectAudience` |
| `enabled` | `boolean` |

## `SceneObjectInteractionDefinition`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `actionReference` | `ActionReferenceDTO` |

## `SceneObjectInteractionIntentDTO`

Campos:

| Field | Type |
|---|---|
| `object` | `SceneObjectDTO` |
| `interactionId` | `string` |
| `actionReference` | `ActionReferenceDTO | null` |
| `principal` | `{ userId: string }` |

## `SceneObjectListOptions`

Campos:

| Field | Type |
|---|---|
| `query` | `string` |

## `SceneObjectPatch`

Campos:

| Field | Type |
|---|---|
| `geometry` | `SceneObjectGeometry` |
| `transform` | `Partial<SceneObjectTransform>` |
| `presentation` | `JsonObject` |
| `data` | `JsonObject` |
| `enabled` | `boolean` |

## `SceneObjectTransform`

Campos:

| Field | Type |
|---|---|
| `rotation` | `number` |
| `scale` | `number` |

## `SceneObjectTypeDefinition`

Campos:

| Field | Type |
|---|---|
| `typeId` | `string` |
| `schemaVersion` | `number` |
| `displayName` | `string` |
| `dataSchema` | `ActionInputSchema` |
| `geometryKinds` | `Array<'point' | 'rect' | 'circle' | 'polygon' | 'polyline'>` |
| `visualDefinition` | `JsonObject[]` |
| `interactionDefinitions` | `SceneObjectInteractionDefinition[]` |
| `editorDefinition` | `JsonObject` |
| `searchableFields` | `string[]` |

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

## `SceneZoneAudience`

Campos:

| Field | Type |
|---|---|
| `kind` | `'campaign' | 'gm' | 'users'` |
| `ids` | `string[]` |

## `SceneZoneDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `type` | `string` |
| `geometry` | `SceneZoneGeometry` |
| `vertical` | `VerticalBoundsDTO` |
| `audience` | `SceneZoneAudience` |
| `enabled` | `boolean` |
| `tags` | `string[]` |
| `packageProvenance` | `PackageProvenanceDTO` |
| `version` | `number` |

## `SceneZoneDeleteResult`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SceneZoneGeometry`

Campos:

| Field | Type |
|---|---|
| `shape` | `'circle' | 'rect' | 'polygon'` |
| `x` | `number` |
| `y` | `number` |
| `radius` | `number` |
| `width` | `number` |
| `height` | `number` |
| `points` | `WorldPointDTO[]` |

## `SceneZoneInput`

Campos:

| Field | Type |
|---|---|
| `type` | `string` |
| `geometry` | `SceneZoneGeometry` |
| `vertical` | `VerticalBoundsDTO` |
| `audience` | `SceneZoneAudience` |
| `enabled` | `boolean` |
| `tags` | `string[]` |
| `providerId` | `string` |

## `SceneZonePatch`

Campos:

| Field | Type |
|---|---|
| `geometry` | `SceneZoneGeometry` |
| `enabled` | `boolean` |
| `tags` | `string[]` |

## `SdkContextDTO`

Campos:

| Field | Type |
|---|---|
| `campaign` | `CampaignContext | null` |
| `scene` | `SceneContext | null` |
| `user` | `UserContext | null` |
| `permissions` | `PermissionContext | null` |

## `SemanticAnchorDTO`

Campos:

| Field | Type |
|---|---|
| `kind` | `'token' | 'scene-object'` |
| `id` | `string` |
| `sceneId` | `string` |

## `SemanticDragPayload`

Campos:

| Field | Type |
|---|---|
| `kind` | `string` |
| `reference` | `string` |
| `sourceContext` | `string` |
| `metadata` | `JsonObject` |
| `schemaVersion` | `1` |

## `SemanticDropDestination`

Campos:

| Field | Type |
|---|---|
| `targetDefinitionId` | `string` |
| `kind` | `DropTargetKind` |
| `resource` | `DropTargetResource` |
| `expectedVersion` | `number` |
| `worldPosition` | `WorldPointDTO` |
| `sceneContext` | `string` |

## `SemanticDropInput`

Campos:

| Field | Type |
|---|---|
| `payload` | `SemanticDragPayload` |
| `destination` | `SemanticDropDestination` |
| `operation` | `string` |
| `idempotencyKey` | `string` |

## `SemanticDropResultDTO`

Campos:

| Field | Type |
|---|---|
| `operation` | `string` |
| `targetId` | `string` |
| `source` | `ContentResolutionDTO` |
| `actionResult` | `ActionExecutionResult` |

## `SemanticOriginDTO`

Campos:

| Field | Type |
|---|---|
| `source` | `string` |
| `resourceId` | `string` |
| `executionId` | `string` |

## `SemanticRegistrationDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |
| `schemaVersion` | `1` |
| `operations` | `string[]` |

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

## `SoundCreateInput`

Campos:

| Field | Type |
|---|---|
| `name` | `string` |
| `asset` | `AudioAssetReferenceDTO` |
| `kind` | `'sound-effect' | 'music' | 'ambience'` |
| `tags` | `string[]` |
| `defaultGain` | `number` |
| `defaultLoop` | `boolean` |
| `metadata` | `JsonObject` |

## `SoundDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaignId` | `string` |
| `name` | `string` |
| `asset` | `AudioAssetReferenceDTO` |
| `kind` | `'sound-effect' | 'music' | 'ambience'` |
| `tags` | `string[]` |
| `defaultGain` | `number` |
| `defaultLoop` | `boolean` |
| `metadata` | `JsonObject` |
| `version` | `number` |

## `SoundDeleteResult`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SoundListOptions`

Campos:

| Field | Type |
|---|---|
| `kind` | `'sound-effect' | 'music' | 'ambience'` |
| `query` | `string` |
| `cursor` | `number` |
| `limit` | `number` |

## `SoundPatch`

Campos:

| Field | Type |
|---|---|
| `name` | `string` |
| `kind` | `'sound-effect' | 'music' | 'ambience'` |
| `tags` | `string[]` |
| `defaultGain` | `number` |
| `defaultLoop` | `boolean` |
| `metadata` | `JsonObject` |

## `SpatialSoundDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `soundId` | `string` |
| `position` | `SpatialSoundPositionDTO` |
| `radius` | `number` |
| `gain` | `number` |
| `falloff` | `'linear' | 'smooth'` |
| `loop` | `boolean` |
| `enabled` | `boolean` |
| `audience` | `AudienceDTO` |
| `constrainedByWalls` | `boolean` |
| `version` | `number` |

## `SpatialSoundDeleteResult`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SpatialSoundInput`

Campos:

| Field | Type |
|---|---|
| `soundId` | `string` |
| `position` | `SpatialSoundPositionDTO` |
| `radius` | `number` |
| `gain` | `number` |
| `falloff` | `'linear' | 'smooth'` |
| `loop` | `boolean` |
| `enabled` | `boolean` |
| `audience` | `AudienceDTO` |
| `constrainedByWalls` | `boolean` |

## `SpatialSoundPatch`

Campos:

| Field | Type |
|---|---|
| `position` | `SpatialSoundPositionDTO` |
| `radius` | `number` |
| `gain` | `number` |
| `falloff` | `'linear' | 'smooth'` |
| `loop` | `boolean` |
| `enabled` | `boolean` |
| `constrainedByWalls` | `boolean` |

## `SpatialSoundPositionDTO`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |

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

## `TimelineCueDTO`

Campos:

| Field | Type |
|---|---|
| `cueId` | `string` |
| `offsetMs` | `number` |
| `type` | `TimelineCueType` |
| `action` | `string` |
| `parameters` | `TimelineParameters` |
| `cleanupAction` | `string` |
| `cleanupInput` | `ActionInput` |

## `TimelineDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `definitionId` | `string` |
| `providerPackageId` | `string` |
| `campaignId` | `string` |
| `sceneId` | `string | null` |
| `status` | `'RUNNING' | 'COMPLETED' | 'CANCELLED' | 'FAILED'` |
| `startedAt` | `number` |
| `audience` | `AudienceDTO` |
| `origin` | `SemanticOriginDTO` |
| `executedCueIds` | `string[]` |
| `completionReason` | `string | null` |
| `version` | `number` |

## `TimelineDefinitionDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `1` |
| `cues` | `TimelineCueDTO[]` |
| `durationMs` | `number` |
| `packageId` | `string` |

## `TimelineStartInput`

Campos:

| Field | Type |
|---|---|
| `definitionId` | `string` |
| `sceneId` | `string` |
| `audience` | `AudienceDTO` |
| `origin` | `SemanticOriginDTO` |
| `startedAt` | `number` |
| `idempotencyKey` | `string` |

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
| `controllers` | `string[]` |
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
| `originExecutionId` | `string` |
| `originJobId` | `string` |
| `causalDepth` | `number` |

## `TokenReadOptions`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `limit` | `number` |

## `TokenTransferDestination`

Campos:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |

## `TokenTransferManyOptions`

Campos:

| Field | Type |
|---|---|
| `navigateAudience` | `SceneNavigationRecipients` |

## `TokenTransferOptions`

Campos:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |
| `navigateAudience` | `SceneNavigationRecipients` |

## `TokenTransferResultDTO`

Campos:

| Field | Type |
|---|---|
| `tokens` | `TransferredTokenDTO[]` |
| `atomic` | `true` |
| `navigation` | `SceneNavigationDTO | null` |

## `TokenTransferSpec`

Campos:

| Field | Type |
|---|---|
| `tokenId` | `string` |
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |
| `expectedVersion` | `number` |

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

## `TransferredTokenDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `actorId` | `string | null` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |
| `version` | `number` |

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

## `WorkflowDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `definitionId` | `string` |
| `providerPackageId` | `string` |
| `campaignId` | `string` |
| `sceneId` | `string | null` |
| `status` | `WorkflowStatus` |
| `currentStep` | `number` |
| `context` | `WorkflowContext` |
| `origin` | `SemanticOriginDTO` |
| `createdBy` | `string` |
| `startedAt` | `number` |
| `wakeAt` | `number | null` |
| `waitingOn` | `string | null` |
| `completionReason` | `string | null` |
| `version` | `number` |

## `WorkflowDefinitionDTO`

Campos:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `1` |
| `steps` | `WorkflowStepDTO[]` |
| `maxDuration` | `number` |
| `maxSteps` | `number` |
| `packageId` | `string` |

## `WorkflowStartInput`

Campos:

| Field | Type |
|---|---|
| `definitionId` | `string` |
| `input` | `WorkflowContext` |
| `sceneId` | `string` |
| `idempotencyKey` | `string` |
| `origin` | `SemanticOriginDTO` |

## `WorldPointDTO`

Campos:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |

## `ActionInput`

Definición: `JsonObject`

## `ActionInputSchema`

Definición: `JsonObject`

## `ActorItemCopyDTO`

Definición: `{ id: string; sourceItemId: string } & RulesetItemCopyFields`

## `ApplicationContext`

Definición: `JsonObject`

## `ApplicationParts`

Definición: `{ [partId: string]: ((context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>) | { render: (context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>; activate?: (root: HTMLElement, context: ApplicationContext) => Disposer | void } }`

## `BusResponse`

Definición: `{ ok: true; value: InteropPayload } | { ok: false; error: { code: string; message: string } }`

## `CampaignContext`

Definición: `JsonObject`

## `CardArtworkMap`

Definición: `{ [cardId: string]: string }`

## `CardRuntimeDTO`

Definición: `JsonObject`

## `ChatMetadata`

Definición: `JsonObject`

## `CombatPanelDefinition`

Definición: `JsonObject`

## `CombatPlugin`

Definición: `JsonObject`

## `CombatProtocolPayload`

Definición: `JsonObject`

## `CommandHandler`

Definición: `(payload: CommandPayload) => void | Promise<void>`

## `CommandPayload`

Definición: `JsonValue`

## `ContentPackEntryData`

Definición: `JsonObject`

## `ContentResolvedValue`

Definición: `ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO`

## `DeckRuntimeDTO`

Definición: `JsonObject`

## `Disposer`

Definición: `() => void`

## `FogOp`

Definición: `{ mode: 'reveal' | 'hide'; shape: 'circle'; geom: { center_x_cells: number; center_y_cells: number; radius_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'square'; geom: { center_x_cells: number; center_y_cells: number; size_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'polygon'; geom: { points_cells: [number, number][] } }`

## `GameplaySubmissionValue`

Definición: `boolean | string | number | null | JsonObject | JsonValue[]`

## `GameplayTurnModel`

Definición: `'SEQUENTIAL' | 'SIMULTANEOUS' | 'PHASED'`

## `InputCommandHandler`

Definición: `(invocation: InputCommandInvocationDTO) => void | Promise<void>`

## `InteractionResponseValue`

Definición: `boolean | string | number | string[]`

## `InteropHandler`

Definición: `(payload: InteropPayload, context: InteropProviderContext) => InteropPayload | Promise<InteropPayload>`

## `InteropPayload`

Definición: `JsonValue`

## `InteropSubscriber`

Definición: `(payload: InteropPayload) => void`

## `JournalDataInput`

Definición: `JsonObject`

## `JournalView`

Definición: `JsonObject`

## `PackageLifecyclePayload`

Definición: `JsonObject`

## `ParticleParameterSchemas`

Definición: `JsonObject`

## `PdfSearchMatch`

Definición: `JsonObject`

## `PdfViewerHostState`

Definición: `JsonObject`

## `PdfViewerOpenResult`

Definición: `PdfDocumentDTO & PdfViewerHostState & { page: number }`

## `PermissionContext`

Definición: `JsonObject`

## `RollAppliedMutation`

Definición: `JsonObject`

## `RollMetadata`

Definición: `JsonObject`

## `RollOptions`

Definición: `JsonObject`

## `RulesetCombatResources`

Definición: `JsonObject`

## `RulesetEffectMutation`

Definición: `JsonObject`

## `RulesetItemCopyFields`

Definición: `JsonObject`

## `RulesetSheetData`

Definición: `JsonObject`

## `SceneContext`

Definición: `JsonObject`

## `SceneImageMetadata`

Definición: `JsonObject`

## `SdkEvent`

Definición: `Readonly<{ type: SdkEventName; version: number; resourceId?: string; sceneId?: string }>`

## `SdkEventHandler`

Definición: `(event: SdkEvent) => void`

## `SdkEventName`

Definición: `string`

## `SettingChangeHandler`

Definición: `(change: SettingChangeDTO) => void`

## `SettingScope`

Definición: `'client' | 'campaign' | 'package'`

## `SettingValue`

Definición: `string | number | boolean | null | string[]`

## `SettingValues`

Definición: `{ [key: string]: SettingValue }`

## `SheetControllerContext`

Definición: `JsonObject`

## `SheetHelpers`

Definición: `{ el: (tag: string, attributes?: JsonObject, ...children: (Node | string)[]) => HTMLElement; phIcon: (name: string) => HTMLElement; getPath: (value: JsonObject, path: string) => SheetValue | undefined; formatMod: (value: number) => string; cssIdent: (value: string) => string; nonEmptyParts: (...parts: string[]) => string[]; closeFloatingSheetMenus: () => void; postJSON: (url: string, payload: JsonObject) => Promise<SheetHttpResult>; refresh: (root: HTMLElement) => Promise<void>; getContext: (root: HTMLElement) => SheetControllerContext | undefined; getLabels: (systemId: string) => JsonObject }`

## `SheetHttpResult`

Definición: `JsonValue`

## `SheetPlugin`

Definición: `JsonObject`

## `SheetValue`

Definición: `JsonValue`

## `SlotRenderCallback`

Definición: `(host: HTMLElement, context: SdkContextDTO) => void`

## `StorageParams`

Definición: `JsonObject`

## `StorageRow`

Definición: `JsonObject`

## `TimelineCueType`

Definición: `'ACTION' | 'AUDIO_PLAY' | 'PRESENTATION_SHOW' | 'LIGHT_CREATE' | 'SHADER_PRESET' | 'PARTICLE_CREATE' | 'NAVIGATION'`

## `TokenOverrides`

Definición: `JsonObject`

## `UserContext`

Definición: `JsonObject`

## `WorkflowStatus`

Definición: `'RUNNING' | 'WAITING_INTERACTION' | 'WAITING_TIME' | 'COMPLETED' | 'CANCELLED' | 'FAILED'`

## `WorkflowStepDTO`

Definición: `{ type: 'ACTION'; action: string; input?: ActionInput } | { type: 'INTERACTION'; request: InteractionRequestInput; resultKey?: string } | { type: 'WAIT_UNTIL'; at?: number; delaySeconds?: number } | { type: 'BRANCH'; key: string; equals: JsonValue; then: number; else: number } | { type: 'SET'; key: string; value: JsonValue } | { type: 'COMPLETE'; output?: JsonValue } | { type: 'FAIL'; reason: string }`

# Tipos semánticos extensibles

## `ActionInput`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `ActionInputSchema`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `ApplicationContext`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `ApplicationParts`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CampaignContext`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CardArtworkMap`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CardMetadata`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CardMetadataSchema`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CardRuntimeDTO`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `ChatMetadata`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CombatPanelDefinition`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CombatPlugin`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CombatProtocolPayload`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `CommandPayload`

Definición: `JsonValue`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `ContentPackEntryData`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `ContentResolvedValue`

Definición: `ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `DeckRuntimeDTO`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `DropTargetKind`

Definición: `'actor' | 'scene-object' | 'scene-surface'`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `GameplaySubmissions`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `JournalDataInput`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `JournalView`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `PackageLifecyclePayload`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `ParticleParameterSchemas`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `PdfSearchMatch`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `PdfViewerHostState`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `PermissionContext`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `RollAppliedMutation`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `RollMetadata`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `RollOptions`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `RulesetCombatResources`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `RulesetEffectMutation`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `RulesetItemCopyFields`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `RulesetSheetData`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `SceneContext`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `SceneImageMetadata`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `SettingValues`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `SheetControllerContext`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `SheetHttpResult`

Definición: `JsonValue`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `SheetPlugin`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `SheetValue`

Definición: `JsonValue`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `StorageParams`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `StorageRow`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `TimelineParameters`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `TokenOverrides`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `UserContext`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.

## `WorkflowContext`

Definición: `JsonObject`

Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.
