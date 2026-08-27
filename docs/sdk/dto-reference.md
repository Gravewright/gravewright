# SDK 1 DTO and type reference

Canonical structures generated from the SDK 1 DTO/input registry.

## `ActionDefinitionDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `version` | `number` |
| `idempotencyKey` | `string` |

## `ActionExecutionResult`

Fields:

| Field | Type |
|---|---|
| `action` | `string` |
| `version` | `number` |
| `reference` | `string` |
| `executionId` | `string` |
| `result` | `ActionSuccessDTO` |
| `changedResources` | `ChangedResourceDTO[]` |

## `ActionLimitsDTO`

Fields:

| Field | Type |
|---|---|
| `maxSteps` | `number` |

## `ActionReferenceDTO`

Fields:

| Field | Type |
|---|---|
| `provider` | `string` |
| `id` | `string` |
| `version` | `number` |

## `ActionReferenceExecuteOptions`

Fields:

| Field | Type |
|---|---|
| `idempotencyKey` | `string` |

## `ActionResolveInput`

Fields:

| Field | Type |
|---|---|
| `provider` | `'active-ruleset'` |
| `semantic` | `string` |

## `ActionSuccessDTO`

Fields:

| Field | Type |
|---|---|
| `ok` | `true` |

## `ActorCreateInput`

Fields:

| Field | Type |
|---|---|
| `systemId` | `string` |
| `type` | `string` |
| `name` | `string` |
| `folderId` | `string` |

## `ActorDTO`

Fields:

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
| `owner_user_ids` | `string[]` |
| `version` | `number` |
| `created_at` | `number` |
| `updated_at` | `number` |

## `ActorDataDTO`

Fields:

| Field | Type |
|---|---|
| `actor_id` | `string` |
| `version` | `number` |
| `data` | `RulesetSheetData` |

## `ActorItemInsertResult`

Fields:

| Field | Type |
|---|---|
| `copy` | `ActorItemCopyDTO` |
| `actorId` | `string` |
| `slot` | `string` |
| `version` | `number` |

## `ActorItemRemoveResult`

Fields:

| Field | Type |
|---|---|
| `removed` | `true` |
| `actorId` | `string` |
| `slot` | `string` |
| `version` | `number` |

## `ActorItemSlotDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `accepts` | `string[]` |
| `duplicatePolicy` | `'allow' | 'rejectSource'` |

## `ActorItemSlotOptions`

Fields:

| Field | Type |
|---|---|
| `slot` | `string` |

## `ActorMutationResult`

Fields:

| Field | Type |
|---|---|
| `actor_id` | `string` |
| `version` | `number` |

## `ActorUpdateInput`

Fields:

| Field | Type |
|---|---|
| `name` | `string` |
| `folderId` | `string` |
| `portraitAssetId` | `string` |
| `tokenAssetId` | `string` |

## `ApplicationDefinition`

Fields:

| Field | Type |
|---|---|
| `parts` | `ApplicationParts` |
| `close` | `(context: ApplicationContext) => void` |
| `rendered` | `(root: HTMLElement, context: ApplicationContext, parts: string[]) => void` |

## `ApplicationInstance`

Fields:

| Field | Type |
|---|---|
| `root` | `HTMLElement` |
| `update` | `(next: ApplicationContext, parts?: string[]) => Promise<ApplicationInstance | null>` |
| `close` | `() => void` |

## `ApplicationRenderOptions`

Fields:

| Field | Type |
|---|---|
| `parts` | `string[]` |

## `AssetCancelResult`

Fields:

| Field | Type |
|---|---|
| `operation` | `AssetOperationDTO` |
| `assetId` | `string` |

## `AssetDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `operation` | `AssetOperationDTO` |
| `asset` | `AssetDTO` |
| `deduplicated` | `boolean` |

## `AssetListOptions`

Fields:

| Field | Type |
|---|---|
| `campaignId` | `string` |
| `kind` | `'image' | 'pdf' | 'audio'` |

## `AssetOperationDTO`

Fields:

| Field | Type |
|---|---|
| `status` | `'ready'` |
| `progress` | `'ready'` |
| `cancelled` | `boolean` |

## `AssetReferenceDTO`

Fields:

| Field | Type |
|---|---|
| `kind` | `'library-asset' | 'package-asset'` |
| `id` | `string` |

## `AudienceDTO`

Fields:

| Field | Type |
|---|---|
| `kind` | `'self' | 'users' | 'campaign' | 'gm'` |
| `ids` | `string[]` |

## `AudioAssetReferenceDTO`

Fields:

| Field | Type |
|---|---|
| `kind` | `'library-asset' | 'package-asset'` |
| `id` | `string` |

## `AudioListOptions`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |

## `AudioMutationOptions`

Fields:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |
| `fade` | `FadeDTO` |

## `AudioPlayInput`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `gain` | `number` |
| `state` | `'playing' | 'paused'` |
| `loop` | `boolean` |
| `fade` | `FadeDTO` |

## `AutomationAuditDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `status` | `'cancelled'` |

## `AutomationJobDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `version` | `number` |
| `runAtUtc` | `number` |
| `idempotencyKey` | `string` |
| `originExecutionId` | `string` |
| `originJobId` | `string` |
| `causalDepth` | `number` |

## `BlendModeParameterSchemaDTO`

Fields:

| Field | Type |
|---|---|
| `type` | `'enum'` |
| `default` | `'normal'` |
| `options` | `('normal' | 'add' | 'multiply' | 'screen')[]` |

## `BooleanParameterSchemaDTO`

Fields:

| Field | Type |
|---|---|
| `type` | `'boolean'` |
| `default` | `boolean` |

## `BusRequestOptions`

Fields:

| Field | Type |
|---|---|
| `timeoutMs` | `number` |
| `timeout` | `number` |

## `CameraDTO`

Fields:

| Field | Type |
|---|---|
| `worldX` | `number` |
| `worldY` | `number` |
| `zoom` | `number` |

## `CampaignMemberDTO`

Fields:

| Field | Type |
|---|---|
| `userId` | `string` |
| `role` | `string` |
| `name` | `string` |

## `CardDeckMutationResult`

Fields:

| Field | Type |
|---|---|
| `deck_instance_id` | `string` |
| `draw_count` | `number` |

## `CardDefinitionDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `version` | `number` |
| `name` | `string` |
| `artwork` | `CardArtworkMap` |
| `metadata` | `CardMetadata` |

## `CardDefinitionInstantiateResult`

Fields:

| Field | Type |
|---|---|
| `deck` | `DeckRuntimeDTO` |
| `definition` | `CardDefinitionDTO` |
| `provenance` | `CardProvenanceDTO` |

## `CardDrawOptions`

Fields:

| Field | Type |
|---|---|
| `count` | `number` |
| `destination` | `'hand' | 'pile' | 'chat' | 'scene' | 'discard' | 'removed'` |
| `mode` | `'top' | 'bottom' | 'random' | 'choose'` |
| `targetPileId` | `string` |
| `reveal` | `boolean` |

## `CardDrawResult`

Fields:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `cards` | `CardRuntimeDTO[]` |
| `target_pile_id` | `string` |

## `CardEventDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `event_type` | `string` |
| `created_at` | `number` |

## `CardIdsResult`

Fields:

| Field | Type |
|---|---|
| `card_ids` | `string[]` |

## `CardPileDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `campaign_id` | `string` |
| `deck_instance_id` | `string` |
| `kind` | `string` |
| `owner_user_id` | `string | null` |
| `visibility` | `string` |

## `CardPlacementDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `card_ids` | `string[]` |

## `CardPlacementPatch`

Fields:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `zIndex` | `number` |
| `faceState` | `'face_up' | 'face_down'` |

## `CardPlacementResult`

Fields:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `placement` | `CardPlacementDTO` |

## `CardPlayOptions`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `faceUp` | `boolean` |

## `CardPlayResult`

Fields:

| Field | Type |
|---|---|
| `event` | `CardEventDTO` |
| `placement` | `CardPlacementDTO` |
| `card` | `CardRuntimeDTO | null` |

## `CardProvenanceDTO`

Fields:

| Field | Type |
|---|---|
| `definition` | `string` |
| `packageId` | `string` |
| `definitionVersion` | `number` |
| `instanceMetadata` | `CardMetadata` |

## `CardResetOptions`

Fields:

| Field | Type |
|---|---|
| `shuffle` | `boolean` |

## `CardStateDTO`

Fields:

| Field | Type |
|---|---|
| `campaign_id` | `string` |
| `decks` | `DeckRuntimeDTO[]` |
| `piles` | `CardPileDTO[]` |
| `scene_placements` | `CardPlacementDTO[]` |
| `cards` | `CardRuntimeDTO[]` |

## `ChangedResourceDTO`

Fields:

| Field | Type |
|---|---|
| `type` | `'actor'` |
| `id` | `string` |
| `version` | `number` |

## `ChatListOptions`

Fields:

| Field | Type |
|---|---|
| `limit` | `number` |

## `ChatMessageDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `content` | `string` |
| `kind` | `string` |
| `visibility` | `string` |

## `ColorParameterSchemaDTO`

Fields:

| Field | Type |
|---|---|
| `type` | `'color'` |
| `default` | `string` |
| `pattern` | `'^#[0-9a-fA-F]{6}$'` |

## `CombatAddInput`

Fields:

| Field | Type |
|---|---|
| `actorIds` | `string[]` |
| `tokenIds` | `string[]` |

## `CombatBarDTO`

Fields:

| Field | Type |
|---|---|
| `value` | `number` |
| `max` | `number` |
| `percent` | `number | null` |
| `visibility` | `string` |

## `CombatConfigDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `hidden` | `boolean` |
| `defeated` | `boolean` |

## `CombatInitiativeOrderEntry`

Fields:

| Field | Type |
|---|---|
| `combatantId` | `string` |
| `value` | `string` |

## `CombatRollInitiativeOptions`

Fields:

| Field | Type |
|---|---|
| `scope` | `'all' | 'one'` |
| `combatantId` | `string` |

## `CombatStartInput`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |

## `CombatStateDTO`

Fields:

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
| `interrupted` | `boolean` |
| `interrupted_id` | `string` |
| `interrupted_name` | `string` |
| `config` | `CombatConfigDTO` |
| `updated_actors` | `RulesetEffectMutation[]` |
| `expired_effects` | `RulesetEffectMutation[]` |
| `effect_ticks` | `RulesetEffectMutation[]` |

## `CombatantDTO`

Fields:

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
| `holding` | `boolean` |
| `can_move_up` | `boolean` |
| `can_move_down` | `boolean` |
| `portrait_url` | `string` |
| `bar` | `CombatBarDTO | null` |
| `conditions_count` | `number` |
| `effects_count` | `number` |

## `ContentLinkDTO`

Fields:

| Field | Type |
|---|---|
| `type` | `'grave-reference'` |
| `ref` | `string` |
| `label` | `string` |
| `icon` | `string` |

## `ContentLinkOptions`

Fields:

| Field | Type |
|---|---|
| `label` | `string` |
| `icon` | `string` |

## `ContentOpenOptions`

Fields:

| Field | Type |
|---|---|
| `source` | `string` |

## `ContentPackDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `type` | `string` |
| `label` | `string` |
| `entries` | `ContentPackEntryDTO[]` |

## `ContentPackEntryDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `name` | `string` |
| `label` | `string` |
| `data` | `ContentPackEntryData` |

## `ContentPackSummaryDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `type` | `string` |
| `label` | `string` |

## `ContentRefOptions`

Fields:

| Field | Type |
|---|---|
| `campaignId` | `string` |
| `parentKind` | `string` |
| `parentId` | `string` |
| `page` | `number` |
| `anchor` | `string` |

## `ContentReferenceDTO`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `ref` | `ContentReferenceDTO` |
| `value` | `ContentResolvedValue` |

## `ContentSearchEntryDTO`

Fields:

| Field | Type |
|---|---|
| `ref` | `ContentReferenceDTO` |
| `label` | `string` |
| `kind` | `ContentReferenceDTO['kind']` |

## `ContentSearchOptions`

Fields:

| Field | Type |
|---|---|
| `kinds` | `ContentReferenceDTO['kind'][]` |
| `cursor` | `string` |
| `limit` | `number` |

## `ContentSearchPageDTO`

Fields:

| Field | Type |
|---|---|
| `entries` | `ContentSearchEntryDTO[]` |
| `nextCursor` | `string | null` |

## `CustomShaderDefinition`

Fields:

| Field | Type |
|---|---|
| `format` | `'gravewright-custom-shader'` |
| `version` | `1` |
| `definition` | `CustomShaderValues` |

## `CustomShaderPreviewResult`

Fields:

| Field | Type |
|---|---|
| `active` | `boolean` |

## `CustomShaderProviderDefinition`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `description` | `string` |
| `open` | `(context: SdkContextDTO) => void | Promise<void>` |

## `CustomShaderUseResult`

Fields:

| Field | Type |
|---|---|
| `accepted` | `true` |

## `CustomShaderValues`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `kind` | `'campaign-asset-slot'` |

## `DeclaredCardDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `quantity` | `number` |
| `tags` | `string[]` |
| `metadata` | `CardMetadata` |
| `artwork` | `DeclaredCardArtworkDTO` |

## `DiceRollInput`

Fields:

| Field | Type |
|---|---|
| `formula` | `string` |
| `label` | `string` |
| `actorId` | `string` |

## `DragSourceDefinition`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `referenceKinds` | `string[]` |
| `operations` | `string[]` |
| `schemaVersion` | `1` |

## `DropTargetDefinition`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `typeId` | `string` |

## `EffectStateDTO`

Fields:

| Field | Type |
|---|---|
| `particles` | `ParticleDTO[]` |
| `shaders` | `ShaderMetadataDTO[]` |

## `EntityListQuery`

Fields:

| Field | Type |
|---|---|
| `type` | `string` |
| `folderId` | `string` |
| `cursor` | `string` |
| `limit` | `number` |

## `ExpectedVersionOptions`

Fields:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `FadeDTO`

Fields:

| Field | Type |
|---|---|
| `durationMs` | `number` |
| `curve` | `'linear' | 'ease-in' | 'ease-out'` |

## `FogMutationResult`

Fields:

| Field | Type |
|---|---|
| `scene_id` | `string` |
| `enabled` | `boolean` |
| `baseline` | `'hide_all' | 'reveal_all'` |
| `ops` | `FogOp[]` |
| `new_ops` | `FogOp[]` |
| `version` | `number` |

## `FogPaintOptions`

Fields:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `FogStateDTO`

Fields:

| Field | Type |
|---|---|
| `scene_id` | `string` |
| `enabled` | `boolean` |
| `baseline` | `'hide_all' | 'reveal_all'` |
| `ops` | `FogOp[]` |
| `version` | `number` |

## `GameplayFlowDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `1` |
| `turnModel` | `GameplayTurnModel` |
| `phases` | `GameplayPhaseDTO[]` |
| `packageId` | `string` |

## `GameplayFlowMutationOptions`

Fields:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `GameplayFlowStartInput`

Fields:

| Field | Type |
|---|---|
| `definitionId` | `string` |
| `participants` | `string[]` |
| `sceneId` | `string` |
| `idempotencyKey` | `string` |

## `GameplayPhaseDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `submissionPolicy` | `'all'` |
| `deadlineSeconds` | `number` |

## `GeometryBehaviorDTO`

Fields:

| Field | Type |
|---|---|
| `movement` | `'block' | 'pass'` |
| `vision` | `'block' | 'pass'` |
| `light` | `'block' | 'pass'` |

## `HandoutAudience`

Fields:

| Field | Type |
|---|---|
| `type` | `'all' | 'user' | 'role'` |
| `id` | `string` |

## `HandoutPresentResult`

Fields:

| Field | Type |
|---|---|
| `presented` | `true` |

## `InputBindingDTO`

Fields:

| Field | Type |
|---|---|
| `user_id` | `string` |
| `package_id` | `string` |
| `command_id` | `string` |
| `binding` | `string` |
| `version` | `number` |

## `InputBindingOptions`

Fields:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |

## `InputCommandDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |
| `label` | `string` |
| `contexts` | `string[]` |
| `registeredAction` | `string` |
| `actionInput` | `ActionInput` |

## `InputCommandDefinition`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `commandId` | `string` |
| `packageId` | `string` |
| `source` | `'binding' | 'gesture'` |
| `binding` | `string | null` |
| `context` | `string` |

## `InputGestureDefinition`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `gesture` | `'tap' | 'double-tap' | 'long-press' | 'drag' | 'pan' | 'cancel'` |
| `commandId` | `string` |

## `InteractionChoiceDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |

## `InteractionDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `status` | `'open' | 'completed' | 'expired' | 'cancelled'` |
| `recipient` | `'me'` |

## `InteractionMutationOptions`

Fields:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |
| `idempotencyKey` | `string` |

## `InteractionOriginDTO`

Fields:

| Field | Type |
|---|---|
| `originExecutionId` | `string` |
| `originJobId` | `string` |
| `causalDepth` | `number` |
| `resourceRef` | `string` |

## `InteractionPromptDTO`

Fields:

| Field | Type |
|---|---|
| `title` | `string` |
| `text` | `string` |

## `InteractionRequestInput`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `value` | `InteractionResponseValue` |
| `respondedAt` | `number` |
| `idempotencyKey` | `string` |

## `InteractionResponseSchema`

Fields:

| Field | Type |
|---|---|
| `type` | `'boolean' | 'single-choice' | 'multi-choice' | 'number' | 'string'` |
| `choices` | `InteractionChoiceDTO[]` |
| `maxSelections` | `number` |
| `minimum` | `number` |
| `maximum` | `number` |
| `maxLength` | `number` |

## `InteropProviderContext`

Fields:

| Field | Type |
|---|---|
| `callerPackageId` | `string` |
| `providerPackageId` | `string` |
| `userId` | `string | undefined` |
| `campaignId` | `string | undefined` |
| `permissions` | `PermissionContext | null` |

## `ItemCreateInput`

Fields:

| Field | Type |
|---|---|
| `systemId` | `string` |
| `type` | `string` |
| `name` | `string` |
| `folderId` | `string` |

## `ItemDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `item_id` | `string` |
| `version` | `number` |
| `changed_paths` | `string[]` |

## `ItemMutationResult`

Fields:

| Field | Type |
|---|---|
| `item_id` | `string` |
| `version` | `number` |

## `ItemUpdateInput`

Fields:

| Field | Type |
|---|---|
| `name` | `string` |
| `folderId` | `string` |
| `portraitAssetId` | `string` |

## `JournalCreateInput`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `type` | `string` |
| `folderId` | `string` |
| `limit` | `number` |

## `JournalListResult`

Fields:

| Field | Type |
|---|---|
| `journals` | `JournalDTO[]` |

## `JournalMutationResult`

Fields:

| Field | Type |
|---|---|
| `journal_id` | `string` |
| `version` | `number | null` |

## `JournalUpdatePatch`

Fields:

| Field | Type |
|---|---|
| `title` | `string` |
| `folderId` | `string` |
| `visibility` | `string` |
| `contentMarkdown` | `string` |
| `data` | `JournalDataInput` |
| `ownerUserIds` | `string[]` |

## `LightCreateInput`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `light_id` | `string` |
| `scene_id` | `string` |

## `LightResult`

Fields:

| Field | Type |
|---|---|
| `light` | `LightDTO` |

## `LightUpdatePatch`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `from` | `WorldPointDTO` |
| `to` | `WorldPointDTO` |
| `worldDistance` | `number` |
| `gridDistance` | `number | null` |
| `gridSize` | `number | null` |

## `NumberParameterSchemaDTO`

Fields:

| Field | Type |
|---|---|
| `type` | `'number'` |
| `default` | `number` |
| `min` | `number` |
| `max` | `number` |

## `PDFPresentationDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `kind` | `string` |
| `version` | `string` |
| `active` | `true` |
| `interop` | `PackageInteropDTO` |

## `PackageInteropDTO`

Fields:

| Field | Type |
|---|---|
| `emits` | `string[]` |
| `listens` | `string[]` |
| `provides` | `string[]` |
| `requires` | `string[]` |

## `PackageProvenanceDTO`

Fields:

| Field | Type |
|---|---|
| `packageId` | `string` |
| `providerId` | `string | null` |

## `ParticleDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `emitter_id` | `string` |
| `scene_id` | `string` |

## `ParticlePresetDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `parameters` | `ParticleParameterSchemas` |

## `ParticleResultDTO`

Fields:

| Field | Type |
|---|---|
| `emitter` | `ParticleDTO` |

## `ParticleValues`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `annotation_id` | `string` |

## `PdfAnnotationInput`

Fields:

| Field | Type |
|---|---|
| `page` | `number` |
| `region` | `PdfRegionDTO` |
| `text` | `string` |

## `PdfAnnotationResult`

Fields:

| Field | Type |
|---|---|
| `annotation` | `PdfAnnotationDTO` |

## `PdfDocumentDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `filename` | `string` |
| `content_type` | `'application/pdf'` |
| `byte_size` | `number` |
| `created_at` | `number` |
| `url` | `string` |

## `PdfMetadataDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `filename` | `string` |
| `content_type` | `'application/pdf'` |
| `byte_size` | `number` |
| `created_at` | `number` |

## `PdfPresentationStartInput`

Fields:

| Field | Type |
|---|---|
| `audience` | `string[]` |
| `page` | `number` |
| `ttlSeconds` | `number` |

## `PdfRegionDTO`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `action` | `string` |
| `supported` | `boolean` |
| `allowed` | `boolean` |
| `reason` | `'ALLOWED' | 'DENIED' | 'UNKNOWN_ACTION'` |

## `PermissionResource`

Fields:

| Field | Type |
|---|---|
| `actorId` | `string` |
| `itemId` | `string` |
| `tokenId` | `string` |
| `sceneId` | `string` |
| `id` | `string` |

## `PresentationAnchor`

Fields:

| Field | Type |
|---|---|
| `kind` | `'token' | 'scene-object'` |
| `id` | `string` |
| `sceneId` | `string` |

## `PresentationAudience`

Fields:

| Field | Type |
|---|---|
| `kind` | `'self' | 'campaign' | 'gm' | 'users'` |
| `ids` | `string[]` |

## `PresentationButton`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `actionReference` | `string` |

## `PresentationCloseResult`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `status` | `'closed'` |

## `PresentationCompletionPolicy`

Fields:

| Field | Type |
|---|---|
| `policy` | `'server-time' | 'all-connected-recipients'` |
| `timeoutMs` | `number` |

## `PresentationContent`

Fields:

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

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |

## `PresentationPatch`

Fields:

| Field | Type |
|---|---|
| `content` | `PresentationContent` |
| `anchor` | `PresentationAnchor` |

## `PresentationRecipientSummary`

Fields:

| Field | Type |
|---|---|
| `expected` | `number` |
| `completed` | `number` |

## `PresentationWaitOptions`

Fields:

| Field | Type |
|---|---|
| `timeoutMs` | `number` |

## `RollActionDefinition`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `intents` | `string[]` |
| `actionIds` | `string[]` |
| `excludeActionIds` | `string[]` |

## `RollGroupDTO`

Fields:

| Field | Type |
|---|---|
| `faces` | `number` |
| `results` | `number[]` |
| `subtotal` | `number` |

## `RollIntentInput`

Fields:

| Field | Type |
|---|---|
| `actorId` | `string` |
| `actionId` | `string` |
| `itemInstanceId` | `string` |
| `inputs` | `ActionInput` |
| `rollOptions` | `RollOptions` |
| `targetActorId` | `string` |
| `targetTokenId` | `string` |
| `target` | `RollTarget` |

## `RollResultDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `actorId` | `string` |
| `tokenId` | `string` |

## `SceneDTO`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `placement_id` | `string` |
| `scene_id` | `string` |

## `SceneImageListResult`

Fields:

| Field | Type |
|---|---|
| `placements` | `SceneImageDTO[]` |

## `SceneImagePlaceOptions`

Fields:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |
| `rotation` | `number` |
| `scale` | `number` |
| `layer` | `string` |

## `SceneImageResult`

Fields:

| Field | Type |
|---|---|
| `placement` | `SceneImageDTO` |

## `SceneImageUpdatePatch`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `recipientIds` | `string[]` |
| `states` | `SceneNavigationStateDTO[]` |

## `SceneNavigationInput`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `recipients` | `AudienceDTO` |
| `reason` | `string` |
| `idempotencyKey` | `string` |

## `SceneNavigationRecipients`

Fields:

| Field | Type |
|---|---|
| `kind` | `'self' | 'users' | 'gm' | 'campaign'` |
| `ids` | `string[]` |

## `SceneNavigationStateDTO`

Fields:

| Field | Type |
|---|---|
| `campaignId` | `string` |
| `userId` | `string` |
| `sceneId` | `string` |
| `reason` | `string` |
| `version` | `number` |
| `updatedAt` | `number` |

## `SceneObjectAudience`

Fields:

| Field | Type |
|---|---|
| `kind` | `'campaign' | 'gm' | 'users'` |
| `ids` | `string[]` |

## `SceneObjectDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SceneObjectGeometry`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `tolerance` | `number` |

## `SceneObjectInput`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `label` | `string` |
| `actionReference` | `ActionReferenceDTO` |

## `SceneObjectInteractionIntentDTO`

Fields:

| Field | Type |
|---|---|
| `object` | `SceneObjectDTO` |
| `interactionId` | `string` |
| `actionReference` | `ActionReferenceDTO | null` |
| `principal` | `{ userId: string }` |

## `SceneObjectListOptions`

Fields:

| Field | Type |
|---|---|
| `query` | `string` |

## `SceneObjectPatch`

Fields:

| Field | Type |
|---|---|
| `geometry` | `SceneObjectGeometry` |
| `transform` | `Partial<SceneObjectTransform>` |
| `presentation` | `JsonObject` |
| `data` | `JsonObject` |
| `enabled` | `boolean` |

## `SceneObjectTransform`

Fields:

| Field | Type |
|---|---|
| `rotation` | `number` |
| `scale` | `number` |

## `SceneObjectTypeDefinition`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `template_id` | `string` |
| `scene_id` | `string` |
| `version` | `number` |
| `audience` | `'campaign' | 'gm'` |

## `SceneTemplateListResult`

Fields:

| Field | Type |
|---|---|
| `templates` | `SceneTemplateDTO[]` |
| `version` | `number` |

## `SceneTemplateResult`

Fields:

| Field | Type |
|---|---|
| `template` | `SceneTemplateDTO` |

## `SceneTemplateValues`

Fields:

| Field | Type |
|---|---|
| `shape` | `'circle' | 'cone' | 'line' | 'rectangle'` |
| `origin` | `WorldPointDTO` |
| `target` | `WorldPointDTO` |
| `audience` | `'campaign' | 'gm'` |

## `SceneZoneAudience`

Fields:

| Field | Type |
|---|---|
| `kind` | `'campaign' | 'gm' | 'users'` |
| `ids` | `string[]` |

## `SceneZoneDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SceneZoneGeometry`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `geometry` | `SceneZoneGeometry` |
| `enabled` | `boolean` |
| `tags` | `string[]` |

## `SdkContextDTO`

Fields:

| Field | Type |
|---|---|
| `campaign` | `CampaignContext | null` |
| `scene` | `SceneContext | null` |
| `user` | `UserContext | null` |
| `permissions` | `PermissionContext | null` |

## `SemanticAnchorDTO`

Fields:

| Field | Type |
|---|---|
| `kind` | `'token' | 'scene-object'` |
| `id` | `string` |
| `sceneId` | `string` |

## `SemanticDragPayload`

Fields:

| Field | Type |
|---|---|
| `kind` | `string` |
| `reference` | `string` |
| `sourceContext` | `string` |
| `metadata` | `JsonObject` |
| `schemaVersion` | `1` |

## `SemanticDropDestination`

Fields:

| Field | Type |
|---|---|
| `targetDefinitionId` | `string` |
| `kind` | `DropTargetKind` |
| `resource` | `DropTargetResource` |
| `expectedVersion` | `number` |
| `worldPosition` | `WorldPointDTO` |
| `sceneContext` | `string` |

## `SemanticDropInput`

Fields:

| Field | Type |
|---|---|
| `payload` | `SemanticDragPayload` |
| `destination` | `SemanticDropDestination` |
| `operation` | `string` |
| `idempotencyKey` | `string` |

## `SemanticDropResultDTO`

Fields:

| Field | Type |
|---|---|
| `operation` | `string` |
| `targetId` | `string` |
| `source` | `ContentResolutionDTO` |
| `actionResult` | `ActionExecutionResult` |

## `SemanticOriginDTO`

Fields:

| Field | Type |
|---|---|
| `source` | `string` |
| `resourceId` | `string` |
| `executionId` | `string` |

## `SemanticRegistrationDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |
| `schemaVersion` | `1` |
| `operations` | `string[]` |

## `SettingChangeDTO`

Fields:

| Field | Type |
|---|---|
| `packageId` | `string` |
| `key` | `string` |
| `value` | `SettingValue` |
| `previous` | `SettingValue | undefined` |
| `scope` | `SettingScope` |

## `SettingDefinitionDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `campaignId` | `string` |

## `SettingSetResult`

Fields:

| Field | Type |
|---|---|
| `success` | `true` |
| `package_id` | `string` |
| `key` | `string` |
| `value` | `SettingValue` |
| `scope` | `SettingScope` |

## `ShaderApplyInput`

Fields:

| Field | Type |
|---|---|
| `presetId` | `string` |
| `schemaVersion` | `number` |
| `parameters` | `ShaderParameterValues` |

## `ShaderInstanceDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `presetId` | `string` |
| `schemaVersion` | `number` |
| `version` | `number` |
| `parameters` | `ShaderParameterValues` |

## `ShaderMetadataDTO`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `number` |
| `labelKey` | `string` |
| `descriptionKey` | `string` |
| `parameters` | `ShaderPresetParametersDTO` |

## `ShaderPresetParametersDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `instance_id` | `string` |
| `scene_id` | `string` |

## `ShaderUpdateInput`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `points` | `WorldPointDTO[]` |

## `SharedMeasurementOptions`

Fields:

| Field | Type |
|---|---|
| `audience` | `'self' | 'campaign' | 'gm'` |
| `ttlSeconds` | `number` |

## `SheetActionEvent`

Fields:

| Field | Type |
|---|---|
| `name` | `string` |
| `event` | `Event` |
| `element` | `HTMLElement` |

## `SheetController`

Fields:

| Field | Type |
|---|---|
| `setup` | `(context: SheetControllerContext) => void` |
| `mount` | `(context: SheetControllerContext) => void` |
| `update` | `(context: SheetControllerContext) => void` |
| `unmount` | `(context: SheetControllerContext) => void` |
| `onAction` | `(action: SheetActionEvent, context: SheetControllerContext) => boolean | void` |

## `SheetDataPatchResult`

Fields:

| Field | Type |
|---|---|
| `actor_id` | `string` |
| `version` | `number` |
| `changed_paths` | `string[]` |

## `SoundCreateInput`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SoundListOptions`

Fields:

| Field | Type |
|---|---|
| `kind` | `'sound-effect' | 'music' | 'ambience'` |
| `query` | `string` |
| `cursor` | `number` |
| `limit` | `number` |

## `SoundPatch`

Fields:

| Field | Type |
|---|---|
| `name` | `string` |
| `kind` | `'sound-effect' | 'music' | 'ambience'` |
| `tags` | `string[]` |
| `defaultGain` | `number` |
| `defaultLoop` | `boolean` |
| `metadata` | `JsonObject` |

## `SpatialSoundDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `deleted` | `true` |

## `SpatialSoundInput`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |

## `StorageExecuteResult`

Fields:

| Field | Type |
|---|---|
| `success` | `true` |
| `rowcount` | `number` |

## `StorageQueryResult`

Fields:

| Field | Type |
|---|---|
| `success` | `true` |
| `rows` | `StorageRow[]` |

## `StorageStatusDTO`

Fields:

| Field | Type |
|---|---|
| `success` | `true` |
| `scope` | `'campaign' | 'global'` |
| `ready` | `boolean` |
| `size_bytes` | `number` |

## `TimelineCueDTO`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `1` |
| `cues` | `TimelineCueDTO[]` |
| `durationMs` | `number` |
| `packageId` | `string` |

## `TimelineStartInput`

Fields:

| Field | Type |
|---|---|
| `definitionId` | `string` |
| `sceneId` | `string` |
| `audience` | `AudienceDTO` |
| `origin` | `SemanticOriginDTO` |
| `startedAt` | `number` |
| `idempotencyKey` | `string` |

## `ToastHandle`

Fields:

| Field | Type |
|---|---|
| `dismiss` | `() => void` |

## `ToastOptions`

Fields:

| Field | Type |
|---|---|
| `duration` | `number` |
| `id` | `string | null` |
| `onClick` | `(toast: HTMLElement) => void` |

## `TokenCreateInput`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `actorId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |

## `TokenDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |

## `TokenMutationResult`

Fields:

| Field | Type |
|---|---|
| `token` | `TokenDTO | null` |
| `tokens` | `TokenDTO[]` |

## `TokenOptions`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `expectedVersion` | `number` |
| `originExecutionId` | `string` |
| `originJobId` | `string` |
| `causalDepth` | `number` |

## `TokenReadOptions`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `limit` | `number` |

## `TokenTransferDestination`

Fields:

| Field | Type |
|---|---|
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |

## `TokenTransferManyOptions`

Fields:

| Field | Type |
|---|---|
| `navigateAudience` | `SceneNavigationRecipients` |

## `TokenTransferOptions`

Fields:

| Field | Type |
|---|---|
| `expectedVersion` | `number` |
| `navigateAudience` | `SceneNavigationRecipients` |

## `TokenTransferResultDTO`

Fields:

| Field | Type |
|---|---|
| `tokens` | `TransferredTokenDTO[]` |
| `atomic` | `true` |
| `navigation` | `SceneNavigationDTO | null` |

## `TokenTransferSpec`

Fields:

| Field | Type |
|---|---|
| `tokenId` | `string` |
| `sceneId` | `string` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |
| `expectedVersion` | `number` |

## `TokenVisionDTO`

Fields:

| Field | Type |
|---|---|
| `enabled` | `boolean` |
| `range` | `number | null` |
| `source` | `'token'` |

## `ToolContextDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `packageId` | `string` |

## `ToolDefinition`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `alt` | `boolean` |
| `ctrl` | `boolean` |
| `meta` | `boolean` |
| `shift` | `boolean` |

## `ToolPointerEventDTO`

Fields:

| Field | Type |
|---|---|
| `phase` | `'down' | 'move' | 'up' | 'cancel'` |
| `world` | `WorldPointDTO` |
| `button` | `number` |
| `modifiers` | `ToolModifiersDTO` |

## `TransferredTokenDTO`

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `sceneId` | `string` |
| `actorId` | `string | null` |
| `x` | `number` |
| `y` | `number` |
| `elevation` | `number` |
| `version` | `number` |

## `UserPresentationDTO`

Fields:

| Field | Type |
|---|---|
| `userId` | `string` |
| `color` | `string` |

## `VerticalBoundsDTO`

Fields:

| Field | Type |
|---|---|
| `bottom` | `number | null` |
| `top` | `number | null` |

## `WallCreateInput`

Fields:

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

Fields:

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

Fields:

| Field | Type |
|---|---|
| `wall_id` | `string` |
| `scene_id` | `string` |

## `WallResult`

Fields:

| Field | Type |
|---|---|
| `wall` | `WallDTO` |

## `WallUpdatePatch`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `wall_ids` | `string[]` |
| `scene_id` | `string | null` |

## `WallsResult`

Fields:

| Field | Type |
|---|---|
| `scene_id` | `string` |
| `walls` | `WallDTO[]` |

## `WorkflowDTO`

Fields:

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

Fields:

| Field | Type |
|---|---|
| `id` | `string` |
| `schemaVersion` | `1` |
| `steps` | `WorkflowStepDTO[]` |
| `maxDuration` | `number` |
| `maxSteps` | `number` |
| `packageId` | `string` |

## `WorkflowStartInput`

Fields:

| Field | Type |
|---|---|
| `definitionId` | `string` |
| `input` | `WorkflowContext` |
| `sceneId` | `string` |
| `idempotencyKey` | `string` |
| `origin` | `SemanticOriginDTO` |

## `WorldPointDTO`

Fields:

| Field | Type |
|---|---|
| `x` | `number` |
| `y` | `number` |

## `ActionInput`

Definition: `JsonObject`

## `ActionInputSchema`

Definition: `JsonObject`

## `ActorItemCopyDTO`

Definition: `{ id: string; sourceItemId: string } & RulesetItemCopyFields`

## `ApplicationContext`

Definition: `JsonObject`

## `ApplicationParts`

Definition: `{ [partId: string]: ((context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>) | { render: (context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>; activate?: (root: HTMLElement, context: ApplicationContext) => Disposer | void } }`

## `BusResponse`

Definition: `{ ok: true; value: InteropPayload } | { ok: false; error: { code: string; message: string } }`

## `CampaignContext`

Definition: `JsonObject`

## `CardArtworkMap`

Definition: `{ [cardId: string]: string }`

## `CardRuntimeDTO`

Definition: `JsonObject`

## `ChatMetadata`

Definition: `JsonObject`

## `CombatPanelDefinition`

Definition: `JsonObject`

## `CombatPlugin`

Definition: `JsonObject`

## `CombatProtocolPayload`

Definition: `JsonObject`

## `CommandHandler`

Definition: `(payload: CommandPayload) => void | Promise<void>`

## `CommandPayload`

Definition: `JsonValue`

## `ContentPackEntryData`

Definition: `JsonObject`

## `ContentResolvedValue`

Definition: `ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO`

## `DeckRuntimeDTO`

Definition: `JsonObject`

## `Disposer`

Definition: `() => void`

## `FogOp`

Definition: `{ mode: 'reveal' | 'hide'; shape: 'circle'; geom: { center_x_cells: number; center_y_cells: number; radius_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'square'; geom: { center_x_cells: number; center_y_cells: number; size_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'polygon'; geom: { points_cells: [number, number][] } }`

## `GameplaySubmissionValue`

Definition: `boolean | string | number | null | JsonObject | JsonValue[]`

## `GameplayTurnModel`

Definition: `'SEQUENTIAL' | 'SIMULTANEOUS' | 'PHASED'`

## `InputCommandHandler`

Definition: `(invocation: InputCommandInvocationDTO) => void | Promise<void>`

## `InteractionResponseValue`

Definition: `boolean | string | number | string[]`

## `InteropHandler`

Definition: `(payload: InteropPayload, context: InteropProviderContext) => InteropPayload | Promise<InteropPayload>`

## `InteropPayload`

Definition: `JsonValue`

## `InteropSubscriber`

Definition: `(payload: InteropPayload) => void`

## `JournalDataInput`

Definition: `JsonObject`

## `JournalView`

Definition: `JsonObject`

## `PackageLifecyclePayload`

Definition: `JsonObject`

## `ParticleParameterSchemas`

Definition: `JsonObject`

## `PdfSearchMatch`

Definition: `JsonObject`

## `PdfViewerHostState`

Definition: `JsonObject`

## `PdfViewerOpenResult`

Definition: `PdfDocumentDTO & PdfViewerHostState & { page: number }`

## `PermissionContext`

Definition: `JsonObject`

## `RollActionHandler`

Definition: `(message: ChatMessageDTO) => void | Promise<void>`

## `RollAppliedMutation`

Definition: `JsonObject`

## `RollMetadata`

Definition: `JsonObject`

## `RollOptions`

Definition: `JsonObject`

## `RulesetCombatResources`

Definition: `JsonObject`

## `RulesetEffectMutation`

Definition: `JsonObject`

## `RulesetItemCopyFields`

Definition: `JsonObject`

## `RulesetSheetData`

Definition: `JsonObject`

## `SceneContext`

Definition: `JsonObject`

## `SceneImageMetadata`

Definition: `JsonObject`

## `SdkEvent`

Definition: `Readonly<{ type: SdkEventName; version: number; resourceId?: string; sceneId?: string }>`

## `SdkEventHandler`

Definition: `(event: SdkEvent) => void`

## `SdkEventName`

Definition: `string`

## `SettingChangeHandler`

Definition: `(change: SettingChangeDTO) => void`

## `SettingScope`

Definition: `'client' | 'campaign' | 'package'`

## `SettingValue`

Definition: `string | number | boolean | null | string[]`

## `SettingValues`

Definition: `{ [key: string]: SettingValue }`

## `SheetControllerContext`

Definition: `JsonObject`

## `SheetHelpers`

Definition: `{ el: (tag: string, attributes?: JsonObject, ...children: (Node | string)[]) => HTMLElement; phIcon: (name: string) => HTMLElement; getPath: (value: JsonObject, path: string) => SheetValue | undefined; formatMod: (value: number) => string; cssIdent: (value: string) => string; nonEmptyParts: (...parts: string[]) => string[]; closeFloatingSheetMenus: () => void; postJSON: (url: string, payload: JsonObject) => Promise<SheetHttpResult>; refresh: (root: HTMLElement) => Promise<void>; getContext: (root: HTMLElement) => SheetControllerContext | undefined; getLabels: (systemId: string) => JsonObject }`

## `SheetHttpResult`

Definition: `JsonValue`

## `SheetPlugin`

Definition: `JsonObject`

## `SheetValue`

Definition: `JsonValue`

## `SlotRenderCallback`

Definition: `(host: HTMLElement, context: SdkContextDTO) => void`

## `StorageParams`

Definition: `JsonObject`

## `StorageRow`

Definition: `JsonObject`

## `TimelineCueType`

Definition: `'ACTION' | 'AUDIO_PLAY' | 'PRESENTATION_SHOW' | 'LIGHT_CREATE' | 'SHADER_PRESET' | 'PARTICLE_CREATE' | 'NAVIGATION'`

## `TokenOverrides`

Definition: `JsonObject`

## `UserContext`

Definition: `JsonObject`

## `WorkflowStatus`

Definition: `'RUNNING' | 'WAITING_INTERACTION' | 'WAITING_TIME' | 'COMPLETED' | 'CANCELLED' | 'FAILED'`

## `WorkflowStepDTO`

Definition: `{ type: 'ACTION'; action: string; input?: ActionInput } | { type: 'INTERACTION'; request: InteractionRequestInput; resultKey?: string } | { type: 'WAIT_UNTIL'; at?: number; delaySeconds?: number } | { type: 'BRANCH'; key: string; equals: JsonValue; then: number; else: number } | { type: 'SET'; key: string; value: JsonValue } | { type: 'COMPLETE'; output?: JsonValue } | { type: 'FAIL'; reason: string }`

# Extensible semantic types

## `ActionInput`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `ActionInputSchema`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `ApplicationContext`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `ApplicationParts`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CampaignContext`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CardArtworkMap`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CardMetadata`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CardMetadataSchema`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CardRuntimeDTO`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `ChatMetadata`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CombatPanelDefinition`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CombatPlugin`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CombatProtocolPayload`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `CommandPayload`

Definition: `JsonValue`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `ContentPackEntryData`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `ContentResolvedValue`

Definition: `ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `DeckRuntimeDTO`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `DropTargetKind`

Definition: `'actor' | 'scene-object' | 'scene-surface'`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `GameplaySubmissions`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `JournalDataInput`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `JournalView`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `PackageLifecyclePayload`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `ParticleParameterSchemas`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `PdfSearchMatch`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `PdfViewerHostState`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `PermissionContext`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `RollAppliedMutation`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `RollMetadata`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `RollOptions`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `RulesetCombatResources`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `RulesetEffectMutation`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `RulesetItemCopyFields`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `RulesetSheetData`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `SceneContext`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `SceneImageMetadata`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `SettingValues`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `SheetControllerContext`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `SheetHttpResult`

Definition: `JsonValue`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `SheetPlugin`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `SheetValue`

Definition: `JsonValue`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `StorageParams`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `StorageRow`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `TimelineParameters`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `TokenOverrides`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `UserContext`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.

## `WorkflowContext`

Definition: `JsonObject`

This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.
