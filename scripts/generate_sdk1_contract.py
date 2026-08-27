"""Generate the frozen SDK 1 tool contract, method reference, and declarations."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "app/engine/sdk/capabilities.json"
MANIFEST = ROOT / "schemas/gravewright-package-v1.schema.json"
RUNTIME = ROOT / "static/js/sdk/gravewright-sdk.js"
OUTPUT = ROOT / "docs/sdk/_data/gravewright-sdk-1.json"
DECLARATIONS = ROOT / "docs/sdk/gravewright-sdk-1.d.ts"
LOCALE_DOCS = {"en": ROOT / "docs/sdk", "pt-br": ROOT / "docs/pt-br/sdk", "es": ROOT / "docs/es/sdk"}

ERRORS = ["CAPABILITY_REQUIRED", "PERMISSION_DENIED", "NOT_FOUND", "VALIDATION_FAILED", "STALE_VERSION", "IDEMPOTENCY_CONFLICT", "ALREADY_SUBMITTED", "NOT_ACTIVE_PARTICIPANT", "LIMIT_EXCEEDED", "UNKNOWN_ACTION", "ALREADY_RESPONDED", "INTERACTION_EXPIRED", "INTERACTION_CANCELLED", "UNKNOWN_OBJECT_TYPE", "PROVIDER_UNAVAILABLE", "INVALID_GEOMETRY", "INVALID_OBJECT_DATA", "INVALID_PRESENTATION", "INVALID_ANCHOR", "ANCHOR_NOT_VISIBLE", "NOT_AUTHORIZED", "PACKAGE_INACTIVE", "UNKNOWN_INTERACTION", "UNSUPPORTED_PRESENTATION_MODE", "RESOURCE_IN_USE"]

DTOS = {
    "AudioAssetReferenceDTO": {"kind":"'library-asset' | 'package-asset'","id":"string"},
    "AudienceDTO": {"kind":"'self' | 'users' | 'campaign' | 'gm'","ids":"string[]"},
    "SemanticAnchorDTO": {"kind":"'token' | 'scene-object'","id":"string","sceneId?":"string"},
    "FadeDTO": {"durationMs":"number","curve":"'linear' | 'ease-in' | 'ease-out'"},
    "AudioPlaybackDTO": {"id":"string","asset":"AudioAssetReferenceDTO","channel":"'music' | 'ambience' | 'sfx' | 'cinematic'","state":"'pending-user-unlock' | 'playing' | 'paused' | 'stopped' | 'failed'","loop":"boolean","gain":"number","audience":"AudienceDTO","sceneId":"string | null","worldAnchor":"SemanticAnchorDTO | null","startedAt":"number","expiresAt":"number | null","fade":"FadeDTO | null","version":"number","ownerPackageId":"string"},
    "SceneNavigationDTO": {"sceneId":"string","recipientIds":"string[]","states":"SceneNavigationStateDTO[]"},
    "SceneNavigationStateDTO": {"campaignId":"string","userId":"string","sceneId":"string","reason":"string","version":"number","updatedAt":"number"},
    "SemanticRegistrationDTO": {"id":"string","packageId":"string","schemaVersion":"1","operations":"string[]"},
    "SemanticDropResultDTO": {"operation":"string","targetId":"string","source":"ContentResolutionDTO","actionResult":"ActionExecutionResult"},
    "InputCommandDTO": {"id":"string","packageId":"string","label":"string","contexts":"string[]","registeredAction?":"string","actionInput?":"ActionInput"},
    "InputBindingDTO": {"user_id":"string","package_id":"string","command_id":"string","binding":"string","version":"number"},
    "AudioPlayInput": {"asset":"AudioAssetReferenceDTO","channel?":"'music' | 'ambience' | 'sfx' | 'cinematic'","loop?":"boolean","gain?":"number","audience?":"AudienceDTO","sceneId?":"string","worldAnchor?":"SemanticAnchorDTO","fade?":"FadeDTO","idempotencyKey?":"string"},
    "AudioListOptions": {"sceneId?":"string"},
    "AudioPlaybackPatch": {"gain?":"number","state?":"'playing' | 'paused'","loop?":"boolean","fade?":"FadeDTO"},
    "AudioMutationOptions": {"expectedVersion?":"number","fade?":"FadeDTO"},
    "SpatialSoundPositionDTO": {"x":"number","y":"number"},
    "SpatialSoundDTO": {"id":"string","sceneId":"string","soundId":"string","position":"SpatialSoundPositionDTO","radius":"number","gain":"number","falloff":"'linear' | 'smooth'","loop":"boolean","enabled":"boolean","audience":"AudienceDTO","constrainedByWalls":"boolean","version":"number"},
    "SpatialSoundInput": {"soundId":"string","position":"SpatialSoundPositionDTO","radius":"number","gain?":"number","falloff?":"'linear' | 'smooth'","loop?":"boolean","enabled?":"boolean","audience?":"AudienceDTO","constrainedByWalls?":"boolean"},
    "SpatialSoundPatch": {"position?":"SpatialSoundPositionDTO","radius?":"number","gain?":"number","falloff?":"'linear' | 'smooth'","loop?":"boolean","enabled?":"boolean","constrainedByWalls?":"boolean"},
    "SpatialSoundDeleteResult": {"id":"string","deleted":"true"},
    "SoundDTO": {"id":"string","campaignId":"string","name":"string","asset":"AudioAssetReferenceDTO","kind":"'sound-effect' | 'music' | 'ambience'","tags":"string[]","defaultGain":"number","defaultLoop":"boolean","metadata":"JsonObject","version":"number"},
    "SoundCreateInput": {"name":"string","asset":"AudioAssetReferenceDTO","kind":"'sound-effect' | 'music' | 'ambience'","tags?":"string[]","defaultGain?":"number","defaultLoop?":"boolean","metadata?":"JsonObject"},
    "SoundPatch": {"name?":"string","kind?":"'sound-effect' | 'music' | 'ambience'","tags?":"string[]","defaultGain?":"number","defaultLoop?":"boolean","metadata?":"JsonObject"},
    "SoundListOptions": {"kind?":"'sound-effect' | 'music' | 'ambience'","query?":"string","cursor?":"number","limit?":"number"},
    "SoundDeleteResult": {"id":"string","deleted":"true"},
    "SceneNavigationInput": {"sceneId":"string","recipients?":"AudienceDTO","reason?":"string","idempotencyKey?":"string"},
    "DragSourceDefinition": {"id":"string","referenceKinds":"string[]","operations":"string[]","schemaVersion":"1"},
    "DropTargetDefinition": {"id":"string","surface":"string","targetKinds":"DropTargetKind[]","worldObjectTypeId?":"string","operations":"string[]","actionReference":"string","schemaVersion":"1"},
    "SemanticDropInput": {"payload":"SemanticDragPayload","destination":"SemanticDropDestination","operation":"string","idempotencyKey?":"string"},
    "SemanticDropDestination": {"targetDefinitionId":"string","kind":"DropTargetKind","resource":"DropTargetResource","expectedVersion?":"number","worldPosition?":"WorldPointDTO","sceneContext?":"string"},
    "DropTargetResource": {"id":"string","sceneId?":"string","typeId?":"string"},
    "SemanticDragPayload": {"kind":"string","reference":"string","sourceContext?":"string","metadata?":"JsonObject","schemaVersion":"1"},
    "InputCommandDefinition": {"id":"string","label":"string","description?":"string","contexts":"string[]","registeredAction?":"string","actionInput?":"ActionInput","defaultBindings?":"string[]"},
    "InputCommandInvocationDTO": {"commandId":"string","packageId":"string","source":"'binding' | 'gesture'","binding":"string | null","context":"string"},
    "InputGestureDefinition": {"id":"string","gesture":"'tap' | 'double-tap' | 'long-press' | 'drag' | 'pan' | 'cancel'","commandId":"string"},
    "InputBindingOptions": {"expectedVersion?":"number"},
    "ActorDTO": {"id":"string","campaign_id":"string","system_id":"string","type":"string","name":"string","folder_id":"string | null","portrait_asset_id":"string | null","token_asset_id":"string | null","owner_user_ids?":"string[]","version":"number","created_at":"number","updated_at":"number"},
    "ItemDTO": {"id":"string","campaign_id":"string","system_id":"string","type":"string","name":"string","folder_id":"string | null","portrait_asset_id":"string | null","version":"number","created_at":"number","updated_at":"number"},
    "SceneDTO": {"id":"string","campaign_id":"string","name":"string","width":"number","height":"number","version":"number","scene_epoch":"number","tile_table_version":"number","grid_size":"number","raster_tile_size":"number","chunk_span":"number","grid_visible":"boolean","grid_color":"string","grid_opacity":"number","darkness":"number","start_world_x":"number","start_world_y":"number","start_zoom":"number"},
    "WallDTO": {"id":"string","scene_id":"string","kind":"string","door_state":"string | null","x1":"number","y1":"number","x2":"number","y2":"number","presentation":"string | null","discovered":"boolean","behavior":"GeometryBehaviorDTO","vertical":"VerticalBoundsDTO","updated_at":"number"},
    "LightDTO": {"id":"string","scene_id":"string","x":"number","y":"number","elevation":"number","bright_radius":"number","dim_radius":"number","color":"string","intensity":"number","animation":"string","angle":"number","rotation":"number","enabled":"boolean","updated_at":"number"},
    "CampaignMemberDTO": {"userId":"string","role":"string","name":"string"},
    "UserPresentationDTO": {"userId":"string","color":"string"},
    "TokenDTO": {"id":"string","scene_id":"string","actor_id":"string | null","grid_x":"number","grid_y":"number","elevation":"number","width_cells":"number","height_cells":"number","rotation":"number","name":"string | null","token_asset_url":"string | null","visible":"boolean","hidden":"boolean","locked":"boolean","disposition":"string","vision":"TokenVisionDTO","controllers":"string[]","updated_at":"number"},
    "GeometryBehaviorDTO": {"movement":"'block' | 'pass'","vision":"'block' | 'pass'","light":"'block' | 'pass'"},
    "VerticalBoundsDTO": {"bottom":"number | null","top":"number | null"},
    "TokenVisionDTO": {"enabled":"boolean","range":"number | null","source":"'token'"},
    "ShaderPresetDTO": {"id":"string","schemaVersion":"number","labelKey":"string","descriptionKey":"string","parameters":"ShaderPresetParametersDTO"},
    "ShaderInstanceDTO": {"id":"string","sceneId":"string","presetId":"string","schemaVersion":"number","version":"number","parameters":"ShaderParameterValues"},
    "CustomShaderDefinition": {"format":"'gravewright-custom-shader'","version":"1","definition":"CustomShaderValues"},
    "CustomShaderValues": {"source":"string","opacity":"number","intensity":"number","scale":"number","speed":"number","rotation":"number","radius":"number","color":"string","blend_mode":"'normal' | 'add' | 'multiply' | 'screen'","enabled":"boolean"},
    "CustomShaderProviderDefinition": {"id":"string","label":"string","description?":"string","open":"(context: SdkContextDTO) => void | Promise<void>"},
    "CustomShaderUseResult": {"accepted":"true"},
    "CustomShaderPreviewResult": {"active":"boolean"},
    "DeclaredCardArtworkDTO": {"kind":"'campaign-asset-slot'"},
    "DeclaredCardDTO": {"id":"string","label":"string","quantity":"number","tags":"string[]","metadata":"CardMetadata","artwork":"DeclaredCardArtworkDTO"},
    "CardDefinitionDTO": {"id":"string","packageId":"string","version":"number","reference":"string","label":"string","description":"string","metadataSchema":"CardMetadataSchema","tags":"string[]","cards":"DeclaredCardDTO[]"},
    "AutomationJobDTO": {"id":"string","package_id":"string","action_id":"string","action_version":"number","run_at_utc":"number","status":"'pending' | 'running' | 'succeeded' | 'failed' | 'rejected' | 'cancelled'","attempts":"number","error_code":"string | null","causal_depth":"number","created_at":"number","updated_at":"number"},
    "AutomationAuditDTO": {"schemaVersion":"1","transition":"string","jobId":"string | null","campaignId":"string","packageId":"string","actionRef":"string","attempt":"number","timestamp":"number","semanticReason?":"string"},
    "AutomationScheduleOptions": {"version":"number","runAtUtc":"number","idempotencyKey":"string","originExecutionId?":"string","originJobId?":"string","causalDepth?":"number"},
    "AutomationCancelResult": {"id":"string","status":"'cancelled'"},
    "AssetDTO": {"id":"string","campaign_id":"string","owner_user_id":"string","folder_id":"string | null","filename":"string","content_type":"string","byte_size":"number","width":"number | null","height":"number | null","created_at":"number","src":"string","kind":"'image' | 'pdf' | 'audio'"},
    "AssetListOptions": {"campaignId?":"string","kind?":"'image' | 'pdf' | 'audio'"},
    "AssetOperationDTO": {"status":"'ready'","progress?":"'ready'","cancelled?":"boolean"},
    "AssetIngestResult": {"operation":"AssetOperationDTO","asset":"AssetDTO","deduplicated":"boolean"},
    "AssetCancelResult": {"operation":"AssetOperationDTO","assetId":"string"},
    "PackageDTO": {"id":"string","kind":"string","version":"string","active":"true","interop":"PackageInteropDTO"},
    "PackageInteropDTO": {"emits?":"string[]","listens?":"string[]","provides?":"string[]","requires?":"string[]"},
    "PermissionCheckDTO": {"action":"string","supported":"boolean","allowed":"boolean","reason":"'ALLOWED' | 'DENIED' | 'UNKNOWN_ACTION'"},
    "ChatMessageDTO": {"id":"string","campaign_id":"string","author_user_id":"string","author_name":"string","author_role":"string","kind":"string","content":"string","expression":"string | null","groups":"RollGroupDTO[] | null","modifier":"number | null","total":"number | null","visibility":"string","metadata":"ChatMetadata","created_at":"number"},
    "RollGroupDTO": {"faces":"number","results":"number[]","subtotal":"number"},
    "WorldPointDTO": {"x":"number","y":"number"},
    "MeasurementResultDTO": {"sceneId":"string","from":"WorldPointDTO","to":"WorldPointDTO","worldDistance":"number","gridDistance":"number | null","gridSize":"number | null"},
    "SharedMeasurementGeometry": {"points":"WorldPointDTO[]"},
    "SharedMeasurementOptions": {"audience?":"'self' | 'campaign' | 'gm'","ttlSeconds?":"number"},
    "SharedMeasurementDTO": {"id":"string","creator":"string","sceneId":"string","geometry":"SharedMeasurementGeometry","audience":"'self' | 'campaign' | 'gm'","expiresAt":"number","version":"number"},
    "PdfPresentationStartInput": {"audience":"string[]","page":"number","ttlSeconds?":"number"},
    "ChatListOptions": {"limit?":"number"},
    "PermissionResource": {"actorId?":"string","itemId?":"string","tokenId?":"string","sceneId?":"string","id?":"string"},
    "WallCreateInput": {"kind?":"'wall' | 'door'","x1":"number","y1":"number","x2":"number","y2":"number","behavior?":"GeometryBehaviorDTO","presentation?":"string","vertical?":"VerticalBoundsDTO"},
    "WallUpdatePatch": {"kind?":"'wall' | 'door'","door_state?":"string | null","x1?":"number","y1?":"number","x2?":"number","y2?":"number","behavior?":"GeometryBehaviorDTO","presentation?":"string","discovered?":"boolean","vertical?":"VerticalBoundsDTO"},
    "WallResult": {"wall":"WallDTO"},
    "WallsResult": {"scene_id":"string","walls":"WallDTO[]"},
    "WallDeleteResult": {"wall_id":"string","scene_id":"string"},
    "WallsDeleteResult": {"wall_ids":"string[]","scene_id":"string | null"},
    "LightCreateInput": {"x":"number","y":"number","elevation?":"number","bright_radius?":"number","dim_radius?":"number","color?":"string","intensity?":"number","animation?":"string","angle?":"number","rotation?":"number","enabled?":"boolean"},
    "LightUpdatePatch": {"x?":"number","y?":"number","elevation?":"number","bright_radius?":"number","dim_radius?":"number","color?":"string","intensity?":"number","animation?":"string","angle?":"number","rotation?":"number","enabled?":"boolean"},
    "LightResult": {"light":"LightDTO"},
    "LightDeleteResult": {"light_id":"string","scene_id":"string"},
    "TokenMutationResult": {"token":"TokenDTO | null","tokens":"TokenDTO[]"},
    "TokenCreateInput": {"sceneId":"string","actorId":"string","x":"number","y":"number","elevation?":"number"},
    "TokenMoveInput": {"sceneId?":"string","x":"number","y":"number"},
    "TokenOptions": {"sceneId?":"string","expectedVersion?":"number","originExecutionId?":"string","originJobId?":"string","causalDepth?":"number"},
    "CombatBarDTO": {"value":"number","max":"number","percent":"number | null","visibility":"string"},
    "CombatantDTO": {"id":"string","actor_id":"string","token_id":"string","name":"string","initiative":"string | null","hidden":"boolean","defeated":"boolean","position":"number","is_current":"boolean","is_next":"boolean","has_acted":"boolean","holding?":"boolean","can_move_up":"boolean","can_move_down":"boolean","portrait_url":"string","bar":"CombatBarDTO | null","conditions_count":"number","effects_count":"number"},
    "CombatConfigDTO": {"system_id":"string","label":"string","input":"'roll' | 'number' | 'text'","sort":"'desc' | 'asc'","manual_order":"boolean","icon":"string","accent":"string","resources":"RulesetCombatResources"},
    "CombatStateDTO": {"campaign_id":"string","combat_id":"string","active":"boolean","round":"number","turn":"number","combatants":"CombatantDTO[]","current_id":"string","current_name":"string","next_id":"string","next_name":"string","interrupted?":"boolean","interrupted_id?":"string","interrupted_name?":"string","config":"CombatConfigDTO","updated_actors":"RulesetEffectMutation[]","expired_effects":"RulesetEffectMutation[]","effect_ticks":"RulesetEffectMutation[]"},
    "CombatStartInput": {"sceneId?":"string"},
    "CombatAddInput": {"actorIds?":"string[]","tokenIds?":"string[]"},
    "CombatFlagsPatch": {"hidden?":"boolean","defeated?":"boolean"},
    "CombatRollInitiativeOptions": {"scope?":"'all' | 'one'","combatantId?":"string"},
    "CombatInitiativeOrderEntry": {"combatantId":"string","value?":"string"},
    "ContentReferenceDTO": {"uri":"string","campaignId":"string","kind":"'actor' | 'item' | 'journal' | 'pdf' | 'deck' | 'card' | 'scene' | 'token'","id":"string","parentKind":"string | null","parentId":"string | null","page":"number | null","anchor":"string | null"},
    "ContentReferenceInput": {"kind":"ContentReferenceDTO['kind']","id?":"string","documentId?":"string","campaignId?":"string","parentKind?":"string","parentId?":"string","page?":"number","anchor?":"string"},
    "ContentRefOptions": {"campaignId?":"string","parentKind?":"string","parentId?":"string","page?":"number","anchor?":"string"},
    "ContentOpenOptions": {"source?":"string"},
    "ContentLinkOptions": {"label?":"string","icon?":"string"},
    "ContentLinkDTO": {"type":"'grave-reference'","ref":"string","label":"string","icon":"string"},
    "ContentResolutionDTO": {"ref":"ContentReferenceDTO","value":"ContentResolvedValue"},
    "ContentSearchOptions": {"kinds?":"ContentReferenceDTO['kind'][]","cursor?":"string","limit?":"number"},
    "ContentSearchEntryDTO": {"ref":"ContentReferenceDTO","label":"string","kind":"ContentReferenceDTO['kind']"},
    "ContentSearchPageDTO": {"entries":"ContentSearchEntryDTO[]","nextCursor":"string | null"},
    "JournalDTO": {"id":"string","title":"string","type":"string","folder_id":"string | null","visibility":"string","version":"number","view":"JournalView"},
    "PdfDocumentDTO": {"id":"string","filename":"string","content_type":"'application/pdf'","byte_size":"number","created_at":"number","url":"string"},
    "PdfMetadataDTO": {"id":"string","filename":"string","content_type":"'application/pdf'","byte_size":"number","created_at":"number"},
    "JournalCreateInput": {"type?":"string","title":"string","folderId?":"string","visibility?":"string","contentMarkdown?":"string","data?":"JournalDataInput","ownerUserIds?":"string[]"},
    "JournalUpdatePatch": {"title?":"string","folderId?":"string","visibility?":"string","contentMarkdown?":"string","data?":"JournalDataInput","ownerUserIds?":"string[]"},
    "JournalListOptions": {"type?":"string","folderId?":"string","limit?":"number"},
    "JournalMutationResult": {"journal_id":"string","version":"number | null"},
    "JournalListResult": {"journals":"JournalDTO[]"},
    "PdfRegionDTO": {"x?":"number","y?":"number","width?":"number","height?":"number","x1?":"number","y1?":"number","x2?":"number","y2?":"number"},
    "PdfAnnotationInput": {"page":"number","region":"PdfRegionDTO","text":"string"},
    "PdfAnnotationDTO": {"id":"string","document_id":"string","author_user_id":"string","page":"number","region":"PdfRegionDTO","text":"string","created_at":"number","updated_at":"number"},
    "PdfAnnotationResult": {"annotation":"PdfAnnotationDTO"},
    "PdfAnnotationDeleteResult": {"annotation_id":"string"},
    "PdfViewerOpenOptions": {"host?":"HTMLElement","assetUrl?":"string","page?":"number","zoom?":"number","spread?":"boolean","anchor?":"string","onPageChange?":"(page: number) => void"},
    "ActionDefinitionDTO": {"id":"string","packageId":"string","version":"number","reference":"string","inputs":"ActionInputSchema","requiredCapabilities":"string[]","idempotency":"'IDEMPOTENT' | 'REQUIRES_IDEMPOTENCY_KEY' | 'NOT_DURABLE'","durability":"'supported' | 'unsupported'","limits":"ActionLimitsDTO","semantics":"string[]"},
    "ActionLimitsDTO": {"maxSteps":"number"},
    "ActionExecuteOptions": {"version?":"number","idempotencyKey?":"string"},
    "ActionReferenceExecuteOptions": {"idempotencyKey?":"string"},
    "ActionResolveInput": {"provider":"'active-ruleset'","semantic":"string"},
    "ChangedResourceDTO": {"type":"'actor'","id":"string","version":"number"},
    "ActionExecutionResult": {"action":"string","version":"number","reference":"string","executionId":"string","result":"ActionSuccessDTO","changedResources":"ChangedResourceDTO[]"},
    "ActionSuccessDTO": {"ok":"true"},
    "ParticleDTO": {"id":"string","scene_id":"string","x":"number","y":"number","kind":"string","scale":"number","density":"number","color":"string","enabled":"boolean","updated_at":"number"},
    "ParticleValues": {"x?":"number","y?":"number","kind?":"string","scale?":"number","density?":"number","color?":"string","enabled?":"boolean"},
    "ParticleResultDTO": {"emitter":"ParticleDTO"},
    "ParticleDeleteResult": {"emitter_id":"string","scene_id":"string"},
    "EffectStateDTO": {"particles":"ParticleDTO[]","shaders":"ShaderMetadataDTO[]"},
    "ShaderMetadataDTO": {"id":"string","scene_id":"string","name":"string","x":"number","y":"number","radius":"number","rotation":"number","blend_mode":"string","opacity":"number","intensity":"number","scale":"number","speed":"number","color":"string","enabled":"boolean","updated_at":"number"},
    "ParticlePresetDTO": {"id":"string","label":"string","parameters":"ParticleParameterSchemas"},
    "FogStateDTO": {"scene_id":"string","enabled":"boolean","baseline":"'hide_all' | 'reveal_all'","ops":"FogOp[]","version":"number"},
    "FogMutationResult": {"scene_id":"string","enabled":"boolean","baseline":"'hide_all' | 'reveal_all'","ops":"FogOp[]","new_ops":"FogOp[]","version":"number"},
    "FogPaintOptions": {"expectedVersion?":"number"},
    "SceneImageDTO": {"id":"string","campaign_id":"string","scene_id":"string","asset_id":"string","owner_user_id":"string | null","x":"number","y":"number","rotation":"number","scale":"number","z_index":"number","natural_width":"number","natural_height":"number","version":"number","locked":"boolean","gm_only":"boolean","layer":"string","metadata":"SceneImageMetadata","created_at":"number","updated_at":"number","src":"string"},
    "SceneImageListResult": {"placements":"SceneImageDTO[]"},
    "SceneImagePlaceOptions": {"x?":"number","y?":"number","rotation?":"number","scale?":"number","layer?":"string"},
    "SceneImageUpdatePatch": {"x?":"number","y?":"number","rotation?":"number","scale?":"number","zIndex?":"number","layer?":"string","assetId?":"string"},
    "SceneImageResult": {"placement":"SceneImageDTO"},
    "SceneImageDeleteResult": {"placement_id":"string","scene_id":"string"},
    "SceneTemplateDTO": {"id":"string","sceneId":"string","shape":"'circle' | 'cone' | 'line' | 'rectangle'","origin":"WorldPointDTO","target":"WorldPointDTO","creatorId":"string","audience":"'campaign' | 'gm'","persistence":"'persistent'","version":"number"},
    "SceneTemplateValues": {"shape":"'circle' | 'cone' | 'line' | 'rectangle'","origin":"WorldPointDTO","target":"WorldPointDTO","audience?":"'campaign' | 'gm'"},
    "SceneTemplateListResult": {"templates":"SceneTemplateDTO[]","version":"number"},
    "SceneTemplateResult": {"template":"SceneTemplateDTO"},
    "SceneTemplateDeleteResult": {"template_id":"string","scene_id":"string","version":"number","audience":"'campaign' | 'gm'"},
    "SceneZoneGeometry": {"shape":"'circle' | 'rect' | 'polygon'","x?":"number","y?":"number","radius?":"number","width?":"number","height?":"number","points?":"WorldPointDTO[]"},
    "SceneZoneAudience": {"kind":"'campaign' | 'gm' | 'users'","ids?":"string[]"},
    "SceneZoneDTO": {"id":"string","sceneId":"string","type":"string","geometry":"SceneZoneGeometry","vertical":"VerticalBoundsDTO","audience":"SceneZoneAudience","enabled":"boolean","tags":"string[]","packageProvenance":"PackageProvenanceDTO","version":"number"},
    "PackageProvenanceDTO": {"packageId":"string","providerId":"string | null"},
    "SceneZoneInput": {"type?":"string","geometry":"SceneZoneGeometry","vertical?":"VerticalBoundsDTO","audience?":"SceneZoneAudience","enabled?":"boolean","tags?":"string[]","providerId?":"string"},
    "SceneZonePatch": {"geometry?":"SceneZoneGeometry","enabled?":"boolean","tags?":"string[]"},
    "SceneZoneDeleteResult": {"id":"string","deleted":"true"},
    "SceneObjectGeometry": {"kind":"'point' | 'rect' | 'circle' | 'polygon' | 'polyline'","x?":"number","y?":"number","radius?":"number","width?":"number","height?":"number","points?":"WorldPointDTO[]"},
    "SceneObjectAudience": {"kind":"'campaign' | 'gm' | 'users'","ids?":"string[]"},
    "ActionReferenceDTO": {"provider":"string","id":"string","version":"number"},
    "AssetReferenceDTO": {"kind":"'library-asset' | 'package-asset'","id":"string"},
    "SceneObjectInteractionDefinition": {"id":"string","label":"string","actionReference?":"ActionReferenceDTO"},
    "SceneObjectTypeDefinition": {"typeId":"string","schemaVersion":"number","displayName":"string","dataSchema":"ActionInputSchema","geometryKinds":"Array<'point' | 'rect' | 'circle' | 'polygon' | 'polyline'>","visualDefinition":"JsonObject[]","interactionDefinitions":"SceneObjectInteractionDefinition[]","editorDefinition?":"JsonObject","searchableFields?":"string[]"},
    "SceneObjectDTO": {"id":"string","sceneId":"string","typeId":"string","providerPackageId":"string","schemaVersion":"number","geometry":"SceneObjectGeometry","transform":"SceneObjectTransform","presentation":"JsonObject","interactions":"SceneObjectInteractionDefinition[]","editor":"JsonObject","dataSchema":"ActionInputSchema","data":"JsonObject","audience":"SceneObjectAudience","enabled":"boolean","providerAvailable":"boolean","providerStatus":"'available' | 'unavailable' | 'outdated'","version":"number","createdAt":"number","updatedAt":"number"},
    "SceneObjectTransform": {"rotation":"number","scale":"number"},
    "SceneObjectInput": {"typeId":"string","geometry":"SceneObjectGeometry","transform?":"Partial<SceneObjectTransform>","presentation?":"JsonObject","data?":"JsonObject","audience?":"SceneObjectAudience","enabled?":"boolean"},
    "SceneObjectPatch": {"geometry?":"SceneObjectGeometry","transform?":"Partial<SceneObjectTransform>","presentation?":"JsonObject","data?":"JsonObject","enabled?":"boolean"},
    "SceneObjectListOptions": {"query?":"string"},
    "SceneObjectHitTestOptions": {"tolerance?":"number"},
    "SceneObjectInteractionIntentDTO": {"object":"SceneObjectDTO","interactionId":"string","actionReference":"ActionReferenceDTO | null","principal":"{ userId: string }"},
    "SceneObjectDeleteResult": {"id":"string","deleted":"true"},
    "PresentationAudience": {"kind":"'self' | 'campaign' | 'gm' | 'users'","ids?":"string[]"},
    "PresentationAnchor": {"kind":"'token' | 'scene-object'","id":"string","sceneId?":"string"},
    "PresentationContent": {"title?":"string","subtitle?":"string","text?":"string","label?":"string","icon?":"string","asset?":"AssetReferenceDTO","progress?":"number","value?":"number","preset?":"string","buttons?":"PresentationButton[]"},
    "PresentationButton": {"id":"string","label":"string","actionReference":"string"},
    "PresentationCompletionPolicy": {"policy":"'server-time' | 'all-connected-recipients'","timeoutMs?":"number"},
    "PresentationRecipientSummary": {"expected":"number","completed":"number"},
    "PresentationWaitOptions": {"timeoutMs?":"number"},
    "PresentationInput": {"mode":"'world-anchor' | 'screen-overlay' | 'title-card' | 'countdown' | 'fade'","content":"PresentationContent","audience?":"PresentationAudience","anchor?":"PresentationAnchor","sceneId?":"string","duration?":"number","deadline?":"number","completion?":"PresentationCompletionPolicy"},
    "PresentationPatch": {"content?":"PresentationContent","anchor?":"PresentationAnchor"},
    "PresentationListOptions": {"sceneId?":"string"},
    "PresentationDTO": {"id":"string","campaignId":"string","packageId":"string","ownerUserId":"string","sceneId":"string | null","mode":"'world-anchor' | 'screen-overlay' | 'title-card' | 'countdown' | 'fade'","content":"PresentationContent","audience":"PresentationAudience","anchor":"PresentationAnchor | null","deadline":"number | null","status":"'active' | 'completed' | 'closed' | 'cancelled'","startedAt":"number","endsAt":"number","completedAt":"number | null","completionReason":"'server-time' | 'recipients' | 'timeout' | 'closed' | 'package-unload' | null","completionPolicy":"PresentationCompletionPolicy","recipientSummary":"PresentationRecipientSummary","version":"number","createdAt":"number","updatedAt":"number","expiresAt":"number"},
    "PresentationCloseResult": {"id":"string","status":"'closed'"},
    "InteractionPromptDTO": {"title":"string","text":"string"},
    "InteractionChoiceDTO": {"id":"string","label":"string"},
    "InteractionResponseSchema": {"type":"'boolean' | 'single-choice' | 'multi-choice' | 'number' | 'string'","choices?":"InteractionChoiceDTO[]","maxSelections?":"number","minimum?":"number","maximum?":"number","maxLength?":"number"},
    "InteractionOriginDTO": {"originExecutionId?":"string","originJobId?":"string","causalDepth?":"number","resourceRef?":"string"},
    "InteractionRequestInput": {"kind?":"string","recipients":"string[]","title":"string","text":"string","responseSchema":"InteractionResponseSchema","visibility?":"'requester' | 'participants' | 'public-after-close'","deadline":"number","responsePolicy?":"'immutable' | 'replace'","origin?":"InteractionOriginDTO"},
    "InteractionResponseDTO": {"value":"InteractionResponseValue","respondedAt":"number","idempotencyKey":"string"},
    "InteractionDTO": {"id":"string","kind":"string","schemaVersion":"1","requester":"string","recipients":"string[]","prompt":"InteractionPromptDTO","responseSchema":"InteractionResponseSchema","visibility":"'requester' | 'participants' | 'public-after-close'","deadline":"number","status":"'open' | 'completed' | 'expired' | 'cancelled'","responses":"{ [userId: string]: InteractionResponseDTO }","version":"number","origin":"InteractionOriginDTO","packageProvenance":"PackageProvenanceDTO","createdAt":"number","expiresAt":"number"},
    "InteractionListOptions": {"status?":"'open' | 'completed' | 'expired' | 'cancelled'","recipient?":"'me'"},
    "InteractionMutationOptions": {"expectedVersion?":"number","idempotencyKey?":"string"},
    "BusRequestOptions": {"timeoutMs?":"number","timeout?":"number"},
    "ChatSendMessage": {"content":"string","kind?":"string","visibility?":"string"},
    "DiceRollInput": {"formula":"string","label?":"string","actorId?":"string"},
    "RollIntentInput": {"actorId":"string","actionId":"string","itemInstanceId?":"string","inputs?":"ActionInput","rollOptions?":"RollOptions","targetActorId?":"string","targetTokenId?":"string","target?":"RollTarget"},
    "RollActionDefinition": {"id":"string","label":"string","intents?":"string[]","actionIds?":"string[]","excludeActionIds?":"string[]"},
    "RollTarget": {"actorId?":"string","tokenId?":"string"},
    "RollResultDTO": {"actor_id":"string","type":"string","label":"string","expression":"string","groups":"RollGroupDTO[]","modifier":"number","total":"number","visibility":"string","metadata":"RollMetadata","applied":"RollAppliedMutation[]"},
    "HandoutAudience": {"type?":"'all' | 'user' | 'role'","id?":"string"},
    "HandoutPresentResult": {"presented":"true"},
    "SettingDefinitionDTO": {"key":"string","scope":"SettingScope","type":"string","default":"SettingValue","label":"string","options":"SettingValue[]","minimum":"number | null","maximum":"number | null","pattern":"string"},
    "SettingSetOptions": {"campaignId?":"string"},
    "SettingSetResult": {"success":"true","package_id":"string","key":"string","value":"SettingValue","scope?":"SettingScope"},
    "StorageQueryResult": {"success":"true","rows":"StorageRow[]"},
    "StorageExecuteResult": {"success":"true","rowcount":"number"},
    "StorageStatusDTO": {"success":"true","scope":"'campaign' | 'global'","ready":"boolean","size_bytes":"number"},
    "TokenReadOptions": {"sceneId?":"string","limit?":"number"},
    "CardStateDTO": {"campaign_id":"string","decks":"DeckRuntimeDTO[]","piles":"CardPileDTO[]","scene_placements":"CardPlacementDTO[]","cards":"CardRuntimeDTO[]"},
    "CardPileDTO": {"id":"string","campaign_id":"string","deck_instance_id":"string","kind":"string","owner_user_id":"string | null","visibility":"string"},
    "CardPlacementDTO": {"id":"string","campaign_id":"string","scene_id":"string","card_instance_id":"string","owner_user_id":"string | null","x":"number","y":"number","rotation":"number","scale":"number","z_index":"number","face_state":"'face_up' | 'face_down'","visibility":"string","locked":"boolean"},
    "CardEventDTO": {"id":"string","campaign_id":"string","event_type":"string","created_at":"number"},
    "CardDefinitionInstantiateOptions": {"version?":"number","name?":"string","artwork":"CardArtworkMap","metadata?":"CardMetadata"},
    "CardDrawOptions": {"count?":"number","destination?":"'hand' | 'pile' | 'chat' | 'scene' | 'discard' | 'removed'","mode?":"'top' | 'bottom' | 'random' | 'choose'","targetPileId?":"string","reveal?":"boolean"},
    "CardResetOptions": {"shuffle?":"boolean"},
    "CardPlayOptions": {"sceneId?":"string","x?":"number","y?":"number","rotation?":"number","scale?":"number","faceUp?":"boolean"},
    "CardPlacementPatch": {"x?":"number","y?":"number","rotation?":"number","scale?":"number","zIndex?":"number","faceState?":"'face_up' | 'face_down'"},
    "CardDeckMutationResult": {"deck_instance_id":"string","draw_count?":"number"},
    "CardIdsResult": {"card_ids":"string[]"},
    "CardDrawResult": {"event":"CardEventDTO","cards":"CardRuntimeDTO[]","target_pile_id":"string"},
    "CardPlayResult": {"event":"CardEventDTO","placement":"CardPlacementDTO","card":"CardRuntimeDTO | null"},
    "CardPlacementResult": {"event":"CardEventDTO","placement":"CardPlacementDTO"},
    "CardPlacementDiscardResult": {"event":"CardEventDTO","card_ids":"string[]"},
    "CardDefinitionInstantiateResult": {"deck":"DeckRuntimeDTO","definition":"CardDefinitionDTO","provenance":"CardProvenanceDTO"},
    "CardProvenanceDTO": {"definition":"string","packageId":"string","definitionVersion":"number","instanceMetadata":"CardMetadata"},
    "CameraDTO": {"worldX":"number","worldY":"number","zoom":"number"},
    "ToolDefinition": {"id":"string","label?":"string","icon?":"string","cursor?":"string","capability?":"string","when?":"(context: SdkContextDTO) => boolean","activate?":"(context: ToolContextDTO) => void","deactivate?":"(context: ToolContextDTO) => void","pointer?":"(event: ToolPointerEventDTO) => void"},
    "ToolContextDTO": {"id":"string","packageId":"string"},
    "ToolPointerEventDTO": {"phase":"'down' | 'move' | 'up' | 'cancel'","world":"WorldPointDTO","button":"number","modifiers":"ToolModifiersDTO"},
    "ToolModifiersDTO": {"alt":"boolean","ctrl":"boolean","meta":"boolean","shift":"boolean"},
    "ToastOptions": {"duration?":"number","id?":"string | null","onClick?":"(toast: HTMLElement) => void"},
    "ToastHandle": {"dismiss":"() => void"},
    "ApplicationDefinition": {"parts":"ApplicationParts","close?":"(context: ApplicationContext) => void","rendered?":"(root: HTMLElement, context: ApplicationContext, parts: string[]) => void"},
    "ApplicationRenderOptions": {"parts?":"string[]"},
    "ApplicationInstance": {"root":"HTMLElement","update":"(next: ApplicationContext, parts?: string[]) => Promise<ApplicationInstance | null>","close":"() => void"},
    "SheetController": {"setup?":"(context: SheetControllerContext) => void","mount?":"(context: SheetControllerContext) => void","update?":"(context: SheetControllerContext) => void","unmount?":"(context: SheetControllerContext) => void","onAction?":"(action: SheetActionEvent, context: SheetControllerContext) => boolean | void"},
    "SheetActionEvent": {"name":"string","event":"Event","element":"HTMLElement"},
    "ContentPackSummaryDTO": {"id":"string","type":"string","label":"string"},
    "ContentPackDTO": {"id":"string","type":"string","label":"string","entries":"ContentPackEntryDTO[]"},
    "ContentPackEntryDTO": {"id":"string","name?":"string","label?":"string","data":"ContentPackEntryData"},
    "PDFPresentationDTO": {"id":"string","presenter":"string","documentId":"string","audience":"string[]","page":"number","version":"number","status":"string","expiresAt":"number"},
    "NumberParameterSchemaDTO": {"type":"'number'","default":"number","min":"number","max":"number"},
    "BooleanParameterSchemaDTO": {"type":"'boolean'","default":"boolean"},
    "ColorParameterSchemaDTO": {"type":"'color'","default":"string","pattern":"'^#[0-9a-fA-F]{6}$'"},
    "BlendModeParameterSchemaDTO": {"type":"'enum'","default":"'normal'","options":"('normal' | 'add' | 'multiply' | 'screen')[]"},
    "ShaderPresetParametersDTO": {"x":"NumberParameterSchemaDTO","y":"NumberParameterSchemaDTO","radius":"NumberParameterSchemaDTO","rotation":"NumberParameterSchemaDTO","opacity":"NumberParameterSchemaDTO","intensity":"NumberParameterSchemaDTO","scale":"NumberParameterSchemaDTO","speed":"NumberParameterSchemaDTO","color":"ColorParameterSchemaDTO","blendMode":"BlendModeParameterSchemaDTO","enabled":"BooleanParameterSchemaDTO"},
    "ActorMutationResult": {"actor_id":"string","version":"number"},
    "ItemMutationResult": {"item_id":"string","version":"number"},
    "ActorCreateInput": {"systemId":"string","type":"string","name":"string","folderId?":"string"},
    "ActorUpdateInput": {"name?":"string","folderId?":"string","portraitAssetId?":"string","tokenAssetId?":"string"},
    "ItemCreateInput": {"systemId":"string","type":"string","name":"string","folderId?":"string"},
    "ItemUpdateInput": {"name?":"string","folderId?":"string","portraitAssetId?":"string"},
    "EntityListQuery": {"type?":"string","folderId?":"string","cursor?":"string","limit?":"number"},
    "ExpectedVersionOptions": {"expectedVersion?":"number"},
    "ShaderApplyInput": {"presetId":"string","schemaVersion?":"number","parameters?":"ShaderParameterValues"},
    "ShaderUpdateInput": {"parameters?":"ShaderParameterValues","x?":"number","y?":"number","radius?":"number","rotation?":"number","opacity?":"number","intensity?":"number","scale?":"number","speed?":"number","color?":"string","blendMode?":"'normal' | 'add' | 'multiply' | 'screen'","enabled?":"boolean"},
    "ShaderParameterValues": {"x?":"number","y?":"number","radius?":"number","rotation?":"number","opacity?":"number","intensity?":"number","scale?":"number","speed?":"number","color?":"string","blendMode?":"'normal' | 'add' | 'multiply' | 'screen'","enabled?":"boolean"},
    "ShaderRemovalResult": {"instance_id":"string","scene_id":"string"},
    "InteropProviderContext": {"callerPackageId":"string","providerPackageId":"string","userId":"string | undefined","campaignId":"string | undefined","permissions":"PermissionContext | null"},
    "SettingChangeDTO": {"packageId":"string","key":"string","value":"SettingValue","previous":"SettingValue | undefined","scope":"SettingScope"},
    "SdkContextDTO": {"campaign":"CampaignContext | null","scene":"SceneContext | null","user":"UserContext | null","permissions":"PermissionContext | null"},
    "ActorDataDTO": {"actor_id":"string","version":"number","data":"RulesetSheetData"},
    "SheetDataPatchResult": {"actor_id":"string","version":"number","changed_paths":"string[]"},
    "ItemDataPatchResult": {"item_id":"string","version":"number","changed_paths":"string[]"},
    "ActorItemSlotDTO": {"id":"string","accepts":"string[]","duplicatePolicy":"'allow' | 'rejectSource'"},
    "ActorItemInsertResult": {"copy":"ActorItemCopyDTO","actorId":"string","slot":"string","version":"number"},
    "ActorItemRemoveResult": {"removed":"true","actorId":"string","slot":"string","version":"number"},
    "ActorItemSlotOptions": {"slot":"string"},
    "WorkflowDefinitionDTO": {"id":"string","schemaVersion":"1","steps":"WorkflowStepDTO[]","maxDuration":"number","maxSteps":"number","packageId?":"string"},
    "WorkflowStartInput": {"definitionId":"string","input?":"WorkflowContext","sceneId?":"string","idempotencyKey":"string","origin?":"SemanticOriginDTO"},
    "WorkflowDTO": {"id":"string","definitionId":"string","providerPackageId":"string","campaignId":"string","sceneId":"string | null","status":"WorkflowStatus","currentStep":"number","context":"WorkflowContext","origin":"SemanticOriginDTO","createdBy":"string","startedAt":"number","wakeAt":"number | null","waitingOn":"string | null","completionReason":"string | null","version":"number"},
    "GameplayFlowDefinitionDTO": {"id":"string","schemaVersion":"1","turnModel":"GameplayTurnModel","phases":"GameplayPhaseDTO[]","packageId?":"string"},
    "GameplayPhaseDTO": {"id":"string","label":"string","submissionPolicy":"'all'","deadlineSeconds?":"number"},
    "GameplayFlowStartInput": {"definitionId":"string","participants":"string[]","sceneId?":"string","idempotencyKey":"string"},
    "GameplayFlowDTO": {"id":"string","campaignId":"string","sceneId":"string | null","definitionId":"string","providerPackageId":"string","status":"'ACTIVE' | 'COMPLETED' | 'CANCELLED'","phaseId":"string | null","round":"number","cycle":"number","participants":"string[]","activeParticipants":"string[]","submissions":"GameplaySubmissions","revealed":"boolean","version":"number"},
    "GameplayFlowMutationOptions": {"expectedVersion?":"number"},
    "TokenTransferDestination": {"sceneId":"string","x":"number","y":"number","elevation?":"number"},
    "TokenTransferSpec": {"tokenId":"string","sceneId":"string","x":"number","y":"number","elevation?":"number","expectedVersion?":"number"},
    "TokenTransferOptions": {"expectedVersion?":"number","navigateAudience?":"SceneNavigationRecipients"},
    "TokenTransferManyOptions": {"navigateAudience?":"SceneNavigationRecipients"},
    "TransferredTokenDTO": {"id":"string","sceneId":"string","actorId":"string | null","x":"number","y":"number","elevation":"number","version":"number"},
    "TokenTransferResultDTO": {"tokens":"TransferredTokenDTO[]","atomic":"true","navigation":"SceneNavigationDTO | null"},
    "TimelineDefinitionDTO": {"id":"string","schemaVersion":"1","cues":"TimelineCueDTO[]","durationMs":"number","packageId?":"string"},
    "TimelineCueDTO": {"cueId":"string","offsetMs":"number","type":"TimelineCueType","action?":"string","parameters?":"TimelineParameters","cleanupAction?":"string","cleanupInput?":"ActionInput"},
    "TimelineStartInput": {"definitionId":"string","sceneId?":"string","audience?":"AudienceDTO","origin?":"SemanticOriginDTO","startedAt?":"number","idempotencyKey":"string"},
    "TimelineDTO": {"id":"string","definitionId":"string","providerPackageId":"string","campaignId":"string","sceneId":"string | null","status":"'RUNNING' | 'COMPLETED' | 'CANCELLED' | 'FAILED'","startedAt":"number","audience":"AudienceDTO","origin":"SemanticOriginDTO","executedCueIds":"string[]","completionReason":"string | null","version":"number"},
    "SemanticOriginDTO": {"source?":"string","resourceId?":"string","executionId?":"string"},
    "SceneNavigationRecipients": {"kind":"'self' | 'users' | 'gm' | 'campaign'","ids?":"string[]"},
}

DYNAMIC_TYPES = {
    "WorkflowContext": {"typeExpression":"JsonObject", "justification":"Values are bounded JSON data declared by each Workflow definition; executable values are rejected."},
    "GameplaySubmissions": {"typeExpression":"JsonObject", "justification":"Participant IDs key server-filtered typed submissions whose values are definition-owned JSON data."},
    "TimelineParameters": {"typeExpression":"JsonObject", "justification":"The closed Timeline cue discriminant selects the existing semantic domain input DTO."},
    "DropTargetKind": {"typeExpression": "'actor' | 'scene-object' | 'scene-surface'", "justification": "Closed semantic destination discriminant."},
    "CardMetadata": {
        "typeExpression": "JsonObject",
        "justification": "The package-owned metadata schema intentionally defines each deck's card metadata at runtime.",
    },
    "CardMetadataSchema": {
        "typeExpression": "JsonObject",
        "justification": "The declarative card registry publishes the package-owned JSON metadata schema verbatim.",
    },
    "CampaignContext": {"typeExpression": "JsonObject", "justification": "The host page supplies the authenticated campaign projection."},
    "SceneContext": {"typeExpression": "JsonObject", "justification": "The host page supplies the active scene projection."},
    "UserContext": {"typeExpression": "JsonObject", "justification": "The host page supplies the authenticated user projection."},
    "PermissionContext": {"typeExpression": "JsonObject", "justification": "Permission keys are ruleset-defined and intentionally extensible."},
    "RulesetSheetData": {"typeExpression": "JsonObject", "justification": "The active ruleset owns the actor Sheet Data schema."},
    "RulesetItemCopyFields": {"typeExpression": "JsonObject", "justification": "The active ruleset declares copied item projections and defaults."},
    "ActionInput": {"typeExpression": "JsonObject", "justification": "Each declarative action definition owns and validates its input schema."},
    "ChatMetadata": {"typeExpression": "JsonObject", "justification": "Chat metadata is intentionally supplied by the active roll and chat providers."},
    "RulesetCombatResources": {"typeExpression": "JsonObject", "justification": "The active ruleset declares combat resource projections."},
    "RulesetEffectMutation": {"typeExpression": "JsonObject", "justification": "The active ruleset defines condition/effect mutation payloads."},
    "CombatPlugin": {"typeExpression": "JsonObject", "justification": "Handler and slot names are declared by the active system's combat protocol."},
    "CombatProtocolPayload": {"typeExpression": "JsonObject", "justification": "Each named combat handler owns its payload schema."},
    "CombatPanelDefinition": {"typeExpression": "JsonObject", "justification": "The host combat panel consumes the active system's declarative panel definition."},
    "ContentResolvedValue": {"typeExpression": "ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO", "justification": "The discriminant in ContentReferenceDTO selects an authority-filtered domain DTO."},
    "JournalView": {"typeExpression": "JsonObject", "justification": "Journal type and viewer authority select the documented journal projection variant."},
    "CardRuntimeDTO": {"typeExpression": "JsonObject", "justification": "Card authority projection intentionally redacts private face and metadata fields."},
    "DeckRuntimeDTO": {"typeExpression": "JsonObject", "justification": "Deck runtime fields are the authority-filtered campaign instance projection."},
    "JournalDataInput": {"typeExpression": "JsonObject", "justification": "Journal type selects the normalized structured data schema."},
    "ActionInputSchema": {"typeExpression": "JsonObject", "justification": "Each registered action publishes its own bounded JSON input schema."},
    "PdfViewerHostState": {"typeExpression": "JsonObject", "justification": "The selected public PDF viewer adapter contributes its presentation state."},
    "PdfSearchMatch": {"typeExpression": "JsonObject", "justification": "The selected public PDF viewer adapter defines text-match metadata."},
    "ParticleParameterSchemas": {"typeExpression": "JsonObject", "justification": "The core preset registry supplies the typed parameter schema catalog."},
    "SceneImageMetadata": {"typeExpression": "JsonObject", "justification": "Scene image metadata is preserved from campaign-owned placement metadata."},
    "RollOptions": {"typeExpression": "JsonObject", "justification": "The active ruleset declares roll option keys."},
    "RollMetadata": {"typeExpression": "JsonObject", "justification": "The active ruleset and roll presenter own roll metadata."},
    "RollAppliedMutation": {"typeExpression": "JsonObject", "justification": "The active ruleset defines applied roll mutations."},
    "StorageParams": {"typeExpression": "JsonObject", "justification": "Each manifest-declared named query defines its parameter names and scalar types."},
    "StorageRow": {"typeExpression": "JsonObject", "justification": "Each manifest-declared read query defines its selected columns."},
    "SettingValues": {"typeExpression": "JsonObject", "justification": "Manifest setting definitions determine package-specific keys."},
    "CardArtworkMap": {"typeExpression": "JsonObject", "justification": "Declared card IDs determine the artwork asset-ID map keys."},
    "ApplicationContext": {"typeExpression": "JsonObject", "justification": "Each registered partial application declares its own render context."},
    "ApplicationParts": {"typeExpression": "JsonObject", "justification": "Each registered partial application declares package-local part IDs and renderers."},
    "SheetPlugin": {"typeExpression": "JsonObject", "justification": "Each ruleset declares its sheet renderer plugin contract."},
    "SheetControllerContext": {"typeExpression": "JsonObject", "justification": "Actor/item sheet type determines the controller context data projection."},
    "ContentPackEntryData": {"typeExpression": "JsonObject", "justification": "Content pack type and active ruleset define each immutable entry payload."},
    "TokenOverrides": {"typeExpression": "JsonObject", "justification": "The active ruleset defines semantic token override keys."},
    "PackageLifecyclePayload": {"typeExpression": "JsonObject", "justification": "Lifecycle payload fields depend on package kind and activation context."},
    "CommandPayload": {"typeExpression": "JsonValue", "justification": "Each package-registered command defines its own invocation payload."},
    "SheetValue": {"typeExpression": "JsonValue", "justification": "Sheet paths address values defined by the active ruleset schema."},
    "SheetHttpResult": {"typeExpression": "JsonValue", "justification": "The selected sheet endpoint defines the helper response payload."},
}

TYPE_ALIASES = {
    "WorkflowStatus": "'RUNNING' | 'WAITING_INTERACTION' | 'WAITING_TIME' | 'COMPLETED' | 'CANCELLED' | 'FAILED'",
    "WorkflowStepDTO": "{ type: 'ACTION'; action: string; input?: ActionInput } | { type: 'INTERACTION'; request: InteractionRequestInput; resultKey?: string } | { type: 'WAIT_UNTIL'; at?: number; delaySeconds?: number } | { type: 'BRANCH'; key: string; equals: JsonValue; then: number; else: number } | { type: 'SET'; key: string; value: JsonValue } | { type: 'COMPLETE'; output?: JsonValue } | { type: 'FAIL'; reason: string }",
    "GameplayTurnModel": "'SEQUENTIAL' | 'SIMULTANEOUS' | 'PHASED'",
    "GameplaySubmissionValue": "boolean | string | number | null | JsonObject | JsonValue[]",
    "TimelineCueType": "'ACTION' | 'AUDIO_PLAY' | 'PRESENTATION_SHOW' | 'LIGHT_CREATE' | 'SHADER_PRESET' | 'PARTICLE_CREATE' | 'NAVIGATION'",
    "InteractionResponseValue": "boolean | string | number | string[]",
    "Disposer": "() => void",
    "SdkEventName": "string",
    "SdkEvent": "Readonly<{ type: SdkEventName; version: number; resourceId?: string; sceneId?: string }>",
    "SdkEventHandler": "(event: SdkEvent) => void",
    "RollActionHandler": "(message: ChatMessageDTO) => void | Promise<void>",
    "InteropPayload": "JsonValue",
    "InteropHandler": "(payload: InteropPayload, context: InteropProviderContext) => InteropPayload | Promise<InteropPayload>",
    "InteropSubscriber": "(payload: InteropPayload) => void",
    "BusResponse": "{ ok: true; value: InteropPayload } | { ok: false; error: { code: string; message: string } }",
    "CommandHandler": "(payload: CommandPayload) => void | Promise<void>",
    "SettingValue": "string | number | boolean | null | string[]",
    "SettingScope": "'client' | 'campaign' | 'package'",
    "SettingChangeHandler": "(change: SettingChangeDTO) => void",
    "SlotRenderCallback": "(host: HTMLElement, context: SdkContextDTO) => void",
    "InputCommandHandler": "(invocation: InputCommandInvocationDTO) => void | Promise<void>",
    "CampaignContext": "JsonObject",
    "SceneContext": "JsonObject",
    "UserContext": "JsonObject",
    "PermissionContext": "JsonObject",
    "RulesetSheetData": "JsonObject",
    "RulesetItemCopyFields": "JsonObject",
    "ActionInput": "JsonObject",
    "ChatMetadata": "JsonObject",
    "RulesetCombatResources": "JsonObject",
    "RulesetEffectMutation": "JsonObject",
    "CombatPlugin": "JsonObject",
    "CombatProtocolPayload": "JsonObject",
    "CombatPanelDefinition": "JsonObject",
    "ContentResolvedValue": "ActorDTO | ItemDTO | SceneDTO | TokenDTO | JournalDTO | PdfDocumentDTO | CardRuntimeDTO | DeckRuntimeDTO",
    "JournalView": "JsonObject",
    "CardRuntimeDTO": "JsonObject",
    "DeckRuntimeDTO": "JsonObject",
    "JournalDataInput": "JsonObject",
    "ActionInputSchema": "JsonObject",
    "PdfViewerHostState": "JsonObject",
    "PdfViewerOpenResult": "PdfDocumentDTO & PdfViewerHostState & { page: number }",
    "PdfSearchMatch": "JsonObject",
    "ParticleParameterSchemas": "JsonObject",
    "SceneImageMetadata": "JsonObject",
    "FogOp": "{ mode: 'reveal' | 'hide'; shape: 'circle'; geom: { center_x_cells: number; center_y_cells: number; radius_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'square'; geom: { center_x_cells: number; center_y_cells: number; size_cells: number } } | { mode: 'reveal' | 'hide'; shape: 'polygon'; geom: { points_cells: [number, number][] } }",
    "RollOptions": "JsonObject",
    "RollMetadata": "JsonObject",
    "RollAppliedMutation": "JsonObject",
    "StorageParams": "JsonObject",
    "StorageRow": "JsonObject",
    "SettingValues": "{ [key: string]: SettingValue }",
    "CardArtworkMap": "{ [cardId: string]: string }",
    "ApplicationContext": "JsonObject",
    "ApplicationParts": "{ [partId: string]: ((context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>) | { render: (context: ApplicationContext, root: HTMLElement) => Node | string | void | Promise<Node | string | void>; activate?: (root: HTMLElement, context: ApplicationContext) => Disposer | void } }",
    "SheetPlugin": "JsonObject",
    "SheetControllerContext": "JsonObject",
    "ContentPackEntryData": "JsonObject",
    "TokenOverrides": "JsonObject",
    "PackageLifecyclePayload": "JsonObject",
    "CommandPayload": "JsonValue",
    "SheetValue": "JsonValue",
    "SheetHttpResult": "JsonValue",
    "SheetHelpers": "{ el: (tag: string, attributes?: JsonObject, ...children: (Node | string)[]) => HTMLElement; phIcon: (name: string) => HTMLElement; getPath: (value: JsonObject, path: string) => SheetValue | undefined; formatMod: (value: number) => string; cssIdent: (value: string) => string; nonEmptyParts: (...parts: string[]) => string[]; closeFloatingSheetMenus: () => void; postJSON: (url: string, payload: JsonObject) => Promise<SheetHttpResult>; refresh: (root: HTMLElement) => Promise<void>; getContext: (root: HTMLElement) => SheetControllerContext | undefined; getLabels: (systemId: string) => JsonObject }",
    "ActorItemCopyDTO": "{ id: string; sourceItemId: string } & RulesetItemCopyFields",
}

PARAMETER_TYPES = {
    ("workflows.register", "definition"): "WorkflowDefinitionDTO",
    ("workflows.start", "input"): "WorkflowStartInput",
    ("workflows.cancel", "options"): "ExpectedVersionOptions",
    ("gameplay.flows.register", "definition"): "GameplayFlowDefinitionDTO",
    ("gameplay.flows.start", "input"): "GameplayFlowStartInput",
    ("gameplay.flows.advance", "options"): "GameplayFlowMutationOptions",
    ("gameplay.flows.submit", "value"): "GameplaySubmissionValue",
    ("gameplay.flows.submit", "options"): "GameplayFlowMutationOptions",
    ("tokens.transfer", "destination"): "TokenTransferDestination",
    ("tokens.transfer", "options"): "TokenTransferOptions",
    ("tokens.transferMany", "transfers"): "TokenTransferSpec[]",
    ("tokens.transferMany", "options"): "TokenTransferManyOptions",
    ("timelines.register", "definition"): "TimelineDefinitionDTO",
    ("timelines.start", "input"): "TimelineStartInput",
    ("timelines.cancel", "options"): "ExpectedVersionOptions",
    ("actors.create", "input"): "ActorCreateInput",
    ("actors.list", "query"): "EntityListQuery",
    ("actors.update", "patch"): "ActorUpdateInput",
    ("actors.update", "options"): "ExpectedVersionOptions",
    ("items.create", "input"): "ItemCreateInput",
    ("items.list", "query"): "EntityListQuery",
    ("items.update", "patch"): "ItemUpdateInput",
    ("items.update", "options"): "ExpectedVersionOptions",
    ("scene.shaders.apply", "input"): "ShaderApplyInput",
    ("scene.shaders.update", "patch"): "ShaderUpdateInput",
    ("scene.shaders.update", "options"): "ExpectedVersionOptions",
    ("scene.shaders.enable", "options"): "ExpectedVersionOptions",
    ("scene.shaders.customLibrary.registerProvider", "definition"): "CustomShaderProviderDefinition",
    ("scene.shaders.customLibrary.openEditor", "definition"): "CustomShaderDefinition | null",
    ("scene.shaders.customLibrary.preview", "definition"): "CustomShaderDefinition",
    ("scene.shaders.customLibrary.use", "definition"): "CustomShaderDefinition",
    ("events.on", "handler"): "SdkEventHandler",
    ("events.once", "handler"): "SdkEventHandler",
    ("bus.provide", "method"): "string",
    ("bus.provide", "handler"): "InteropHandler",
    ("bus.publish", "payload"): "InteropPayload",
    ("bus.request", "method"): "string",
    ("bus.request", "payload"): "InteropPayload",
    ("bus.subscribe", "fn"): "InteropSubscriber",
    ("commands.register", "handler"): "CommandHandler",
    ("rolls.actions.register", "definition"): "RollActionDefinition",
    ("rolls.actions.register", "handler"): "RollActionHandler",
    ("rolls.reroll", "messageId"): "string",
    ("input.commands.register", "handler"): "InputCommandHandler",
    ("input.gestures.register", "handler"): "InputCommandHandler",
    ("settings.onChange", "handler"): "SettingChangeHandler",
    ("ui.slots.register", "render"): "SlotRenderCallback",
    ("actors.items.insertCopy", "options"): "ActorItemSlotOptions",
    ("actors.items.listCopies", "options"): "ActorItemSlotOptions",
    ("actors.items.removeCopy", "options"): "ActorItemSlotOptions",
    ("actors.patchData", "patch"): "RulesetSheetData",
    ("items.patchData", "patch"): "RulesetSheetData",
    ("assets.list", "options"): "AssetListOptions",
    ("automation.schedule", "input"): "ActionInput",
    ("automation.schedule", "options"): "AutomationScheduleOptions",
    ("chat.list", "options"): "ChatListOptions",
    ("permissions.can", "resource"): "PermissionResource",
    ("permissions.check", "resource"): "PermissionResource",
    ("scene.measurements.measure", "from"): "WorldPointDTO",
    ("scene.measurements.measure", "to"): "WorldPointDTO",
    ("scene.measurements.share", "geometry"): "SharedMeasurementGeometry",
    ("scene.measurements.share", "options"): "SharedMeasurementOptions",
    ("pdf.presentation.start", "input"): "PdfPresentationStartInput",
    ("pdf.presentation.update", "options"): "ExpectedVersionOptions",
    ("scene.geometry.createWall", "input"): "WallCreateInput",
    ("scene.geometry.updateWall", "patch"): "WallUpdatePatch",
    ("scene.geometry.createLight", "input"): "LightCreateInput",
    ("scene.geometry.updateLight", "patch"): "LightUpdatePatch",
    ("scene.geometry.moveWallNode", "from"): "WorldPointDTO",
    ("scene.geometry.moveWallNode", "to"): "WorldPointDTO",
    ("scene.geometry.moveWalls", "delta"): "WorldPointDTO",
    ("tokens.create", "input"): "TokenCreateInput",
    ("tokens.move", "position"): "TokenMoveInput",
    ("tokens.move", "options"): "TokenOptions",
    ("tokens.delete", "options"): "TokenOptions",
    ("tokens.update", "options"): "TokenOptions",
    ("combat.start", "input"): "CombatStartInput",
    ("combat.add", "input"): "CombatAddInput",
    ("combat.setFlags", "flags"): "CombatFlagsPatch",
    ("combat.setHolding", "holding"): "boolean",
    ("combat.rollInitiative", "options"): "CombatRollInitiativeOptions",
    ("combat.setInitiativeOrder", "entries"): "CombatInitiativeOrderEntry[]",
    ("combat.register", "plugin"): "CombatPlugin",
    ("combat.registerPanel", "panel"): "CombatPanelDefinition",
    ("combat.dispatch", "payload"): "CombatProtocolPayload",
    ("combat.renderSlot", "payload"): "CombatProtocolPayload",
    ("content.ref", "options"): "ContentRefOptions",
    ("content.resolve", "reference"): "string | ContentReferenceInput",
    ("content.get", "reference"): "string | ContentReferenceInput",
    ("content.can", "reference"): "string | ContentReferenceInput",
    ("content.open", "reference"): "string | ContentReferenceInput",
    ("content.open", "options"): "ContentOpenOptions",
    ("content.link", "reference"): "string | ContentReferenceInput",
    ("content.link", "options"): "ContentLinkOptions",
    ("content.search", "query"): "string",
    ("content.search", "options"): "ContentSearchOptions",
    ("journals.create", "input"): "JournalCreateInput",
    ("journals.update", "patch"): "JournalUpdatePatch",
    ("journals.list", "options"): "JournalListOptions",
    ("pdf.annotations.create", "annotation"): "PdfAnnotationInput",
    ("pdf.annotations.update", "annotation"): "PdfAnnotationInput",
    ("pdf.viewer.open", "options"): "PdfViewerOpenOptions",
    ("pdf.viewer.search", "query"): "string",
    ("rules.actions.execute", "input"): "ActionInput",
    ("rules.actions.execute", "options"): "ActionExecuteOptions",
    ("rules.actions.executeReference", "input"): "ActionInput",
    ("rules.actions.executeReference", "options"): "ActionReferenceExecuteOptions",
    ("rules.actions.resolve", "input"): "ActionResolveInput",
    ("scene.effects.create", "values"): "ParticleValues",
    ("scene.effects.update", "values"): "ParticleValues",
    ("scene.fog.paint", "ops"): "FogOp[]",
    ("scene.fog.paint", "options"): "FogPaintOptions",
    ("scene.images.place", "options"): "SceneImagePlaceOptions",
    ("scene.images.update", "patch"): "SceneImageUpdatePatch",
    ("scene.images.update", "options"): "ExpectedVersionOptions",
    ("scene.templates.create", "values"): "SceneTemplateValues",
    ("scene.templates.update", "patch"): "Partial<SceneTemplateValues>",
    ("scene.templates.update", "options"): "ExpectedVersionOptions",
    ("scene.templates.delete", "options"): "ExpectedVersionOptions",
    ("scene.zones.create", "input"): "SceneZoneInput",
    ("scene.zones.update", "patch"): "SceneZonePatch",
    ("scene.zones.update", "options"): "ExpectedVersionOptions",
    ("scene.zones.delete", "options"): "ExpectedVersionOptions",
    ("scene.objectTypes.register", "definition"): "SceneObjectTypeDefinition",
    ("scene.objects.list", "options"): "SceneObjectListOptions",
    ("scene.objects.hitTest", "point"): "WorldPointDTO",
    ("scene.objects.hitTest", "options"): "SceneObjectHitTestOptions",
    ("scene.objects.create", "input"): "SceneObjectInput",
    ("scene.objects.update", "patch"): "SceneObjectPatch",
    ("scene.objects.update", "options"): "ExpectedVersionOptions",
    ("scene.objects.delete", "options"): "ExpectedVersionOptions",
    ("scene.objects.interact", "options"): "ExpectedVersionOptions",
    ("ui.presentations.show", "input"): "PresentationInput",
    ("ui.presentations.wait", "options"): "PresentationWaitOptions",
    ("ui.presentations.list", "options"): "PresentationListOptions",
    ("ui.presentations.update", "patch"): "PresentationPatch",
    ("ui.presentations.update", "options"): "ExpectedVersionOptions",
    ("ui.presentations.close", "options"): "ExpectedVersionOptions",
    ("ui.dragDrop.registerSource", "definition"): "DragSourceDefinition",
    ("ui.dragDrop.registerTarget", "definition"): "DropTargetDefinition",
    ("ui.dragDrop.drop", "input"): "SemanticDropInput",
    ("audio.play", "input"): "AudioPlayInput",
    ("audio.list", "options"): "AudioListOptions",
    ("audio.update", "patch"): "AudioPlaybackPatch",
    ("audio.update", "options"): "AudioMutationOptions",
    ("audio.stop", "options"): "AudioMutationOptions",
    ("scene.spatialSounds.create", "input"): "SpatialSoundInput",
    ("scene.spatialSounds.update", "patch"): "SpatialSoundPatch",
    ("scene.spatialSounds.update", "options"): "ExpectedVersionOptions",
    ("scene.spatialSounds.delete", "options"): "ExpectedVersionOptions",
    ("sounds.list", "options"): "SoundListOptions",
    ("sounds.create", "input"): "SoundCreateInput",
    ("sounds.update", "patch"): "SoundPatch",
    ("sounds.update", "options"): "ExpectedVersionOptions",
    ("sounds.delete", "options"): "ExpectedVersionOptions",
    ("navigation.scene.go", "input"): "SceneNavigationInput",
    ("input.commands.register", "definition"): "InputCommandDefinition",
    ("input.commands.execute", "inputs"): "ActionInput",
    ("input.bindings.set", "binding"): "string",
    ("input.bindings.set", "options"): "InputBindingOptions",
    ("input.gestures.register", "definition"): "InputGestureDefinition",
    ("interactions.request", "input"): "InteractionRequestInput",
    ("interactions.list", "options"): "InteractionListOptions",
    ("interactions.respond", "response"): "InteractionResponseValue",
    ("interactions.respond", "options"): "InteractionMutationOptions",
    ("interactions.cancel", "options"): "ExpectedVersionOptions",
    ("bus.request", "options"): "BusRequestOptions",
    ("chat.send", "message"): "string | ChatSendMessage",
    ("dice.roll", "input"): "DiceRollInput",
    ("rolls.intent", "payload"): "RollIntentInput",
    ("handouts.present", "audience"): "HandoutAudience",
    ("settings.set", "options"): "SettingSetOptions",
    ("storage.sqlite.query", "params"): "StorageParams",
    ("storage.sqlite.execute", "params"): "StorageParams",
    ("tokens.get", "options"): "TokenReadOptions",
    ("tokens.list", "options"): "TokenReadOptions",
    ("cards.definitions.instantiate", "options"): "CardDefinitionInstantiateOptions",
    ("cards.draw", "options"): "CardDrawOptions",
    ("cards.reset", "options"): "CardResetOptions",
    ("cards.play", "options"): "CardPlayOptions",
    ("cards.updatePlacement", "patch"): "CardPlacementPatch",
    ("tools.register", "definition"): "ToolDefinition",
    ("ui.toast", "message"): "string",
    ("ui.toast", "options"): "ToastOptions",
    ("ui.applications.register", "definition"): "ApplicationDefinition",
    ("ui.applications.render", "host"): "HTMLElement",
    ("ui.applications.render", "appContext"): "ApplicationContext",
    ("ui.applications.render", "options"): "ApplicationRenderOptions",
    ("sheets.register", "plugin"): "SheetPlugin",
    ("sheets.registerController", "controller"): "SheetController",
    ("scene.shaders.enable", "enabled"): "boolean",
    ("tokens.update", "patch"): "TokenOverrides",
}


def _method_signatures(source: str) -> dict[str, tuple[str, bool]]:
    methods: dict[str, tuple[str, bool]] = {}
    stack: list[tuple[int, str]] = []
    namespace = re.compile(r"^(\s*)([A-Za-z_$][\w$]*): Object\.freeze\(\{$")
    method = re.compile(r"^(\s*)(?:(async)\s+)?([A-Za-z_$][\w$]*)\(([^)]*)\)\s*\{")
    for line in source.splitlines():
        indent = len(line) - len(line.lstrip())
        while stack and indent <= stack[-1][0] and line.strip().startswith("}),"):
            stack.pop()
        match = namespace.match(line)
        if match:
            current = len(match.group(1))
            while stack and stack[-1][0] >= current:
                stack.pop()
            stack.append((current, match.group(2)))
            continue
        match = method.match(line)
        if match and stack:
            current = len(match.group(1))
            path = ".".join([name for level, name in stack if level < current] + [match.group(3)])
            methods[path] = (match.group(4).strip(), bool(match.group(2)))
    return methods


def _parameter(path: str, raw: str) -> dict:
    left, separator, default = raw.partition("=")
    name = left.strip().removeprefix("...")
    if name.startswith("{"):
        name="input"
    lowered = name.lower()
    if (path, name) in PARAMETER_TYPES: kind = PARAMETER_TYPES[(path, name)]
    elif name == "file": kind = "File"
    elif lowered.endswith("ids"): kind = "string[]"
    elif lowered.endswith("id") or lowered in {"name","event","action","capability","key","querytext","method","kind","state","initial","to","scope","sheettype","resourcetype","reference","fallback"}: kind = "string"
    elif lowered in {"page","count","ttlseconds","expectedversion","version","delta","value","x","y"}: kind = "number"
    elif lowered in {"handler","fn","predicate"}: kind = "function"
    else: kind = "object"
    return {"name":name,"type":kind,"required":not separator,"default":default.strip() if separator else None}


def _split_parameters(raw: str) -> list[str]:
    values=[]; start=0; depth=0; quote=""; escaped=False
    for index,char in enumerate(raw):
        if quote:
            if escaped: escaped=False
            elif char=="\\": escaped=True
            elif char==quote: quote=""
        elif char in {"'",'"'}: quote=char
        elif char in "{[()": depth+=1
        elif char in "}])": depth-=1
        elif char=="," and depth==0:
            values.append(raw[start:index].strip()); start=index+1
    tail=raw[start:].strip()
    if tail: values.append(tail)
    return values


def _return_type(path: str) -> str:
    exact = {"actors.get":"ActorDTO | null","actors.list":"ActorDTO[]","actors.create":"ActorMutationResult","actors.update":"ActorMutationResult","actors.delete":"ActorMutationResult","items.get":"ItemDTO | null","items.list":"ItemDTO[]","items.create":"ItemMutationResult","items.update":"ItemMutationResult","items.delete":"ItemMutationResult","scene.get":"SceneDTO | null","scene.list":"SceneDTO[]","tokens.get":"TokenDTO | null","tokens.list":"TokenDTO[]","scene.geometry.walls":"WallDTO[]","scene.geometry.lights":"LightDTO[]","scene.shaders.presets":"ShaderPresetDTO[]","scene.shaders.getPreset":"ShaderPresetDTO | null","scene.shaders.list":"ShaderInstanceDTO[]","scene.shaders.apply":"ShaderInstanceDTO","scene.shaders.update":"ShaderInstanceDTO","scene.shaders.enable":"ShaderInstanceDTO","scene.shaders.remove":"ShaderRemovalResult","automation.get":"AutomationJobDTO | null","automation.list":"AutomationJobDTO[]","pdf.presentation.current":"PDFPresentationDTO | null"}
    exact.update({"scene.shaders.customLibrary.registerProvider":"Disposer","scene.shaders.customLibrary.openEditor":"CustomShaderDefinition | null","scene.shaders.customLibrary.preview":"CustomShaderPreviewResult","scene.shaders.customLibrary.clearPreview":"CustomShaderPreviewResult","scene.shaders.customLibrary.use":"CustomShaderUseResult"})
    primitives = {
        "bus.provide": "Disposer", "bus.publish": "void", "bus.request": "Promise<BusResponse>",
        "bus.subscribe": "Disposer", "commands.register": "void", "chat.send": "void", "rolls.actions.register": "boolean", "rolls.reroll": "Promise<RollResultDTO>",
        "events.available": "SdkEventName[]", "events.on": "Disposer", "events.once": "Disposer",
        "i18n.t": "string", "packages.has": "boolean", "pdf.viewer.currentPage": "number | null",
        "settings.onChange": "Disposer", "settings.scope": "SettingScope | null",
        "tools.activeTool": "string", "tools.register": "Disposer", "ui.slots.available": "string[]",
        "ui.slots.register": "Disposer", "combat.registerPanel": "boolean",
    }
    structured = {
        "workflows.register":"WorkflowDefinitionDTO", "workflows.start":"WorkflowDTO", "workflows.get":"WorkflowDTO | null", "workflows.list":"WorkflowDTO[]", "workflows.cancel":"WorkflowDTO",
        "gameplay.flows.register":"GameplayFlowDefinitionDTO", "gameplay.flows.start":"GameplayFlowDTO", "gameplay.flows.get":"GameplayFlowDTO | null", "gameplay.flows.list":"GameplayFlowDTO[]", "gameplay.flows.advance":"GameplayFlowDTO", "gameplay.flows.submit":"GameplayFlowDTO",
        "tokens.transfer":"TokenTransferResultDTO", "tokens.transferMany":"TokenTransferResultDTO",
        "timelines.register":"TimelineDefinitionDTO", "timelines.start":"TimelineDTO", "timelines.get":"TimelineDTO | null", "timelines.list":"TimelineDTO[]", "timelines.cancel":"TimelineDTO",
        "actors.data": "ActorDataDTO", "actors.patchData": "SheetDataPatchResult",
        "items.patchData": "ItemDataPatchResult", "actors.items.slots": "ActorItemSlotDTO[]",
        "actors.items.listCopies": "ActorItemCopyDTO[]", "actors.items.insertCopy": "ActorItemInsertResult",
        "actors.items.removeCopy": "ActorItemRemoveResult",
        "assets.list": "AssetDTO[]", "assets.ingest": "AssetIngestResult",
        "assets.cancelImport": "AssetCancelResult", "automation.schedule": "AutomationJobDTO",
        "automation.cancel": "AutomationCancelResult", "automation.audit": "AutomationAuditDTO[]",
        "packages.get": "PackageDTO | null", "permissions.check": "PermissionCheckDTO",
        "permissions.can": "boolean", "chat.get": "ChatMessageDTO | null",
        "chat.list": "ChatMessageDTO[]", "scene.active": "SceneDTO | null",
        "campaign.members": "CampaignMemberDTO[]",
        "users.presentation.get": "UserPresentationDTO", "users.presentation.list": "UserPresentationDTO[]",
        "tokens.targets.list": "string[]", "tokens.targets.set": "string[]", "tokens.targets.clear": "string[]",
        "scene.measurements.measure": "MeasurementResultDTO",
        "scene.measurements.share": "SharedMeasurementDTO",
        "scene.measurements.listShared": "SharedMeasurementDTO[]",
        "scene.measurements.cancel": "SharedMeasurementDTO",
        "pdf.presentation.start": "PDFPresentationDTO", "pdf.presentation.update": "PDFPresentationDTO",
        "pdf.presentation.end": "PDFPresentationDTO",
        "tokens.create": "TokenMutationResult", "tokens.move": "TokenMutationResult",
        "tokens.update": "TokenMutationResult", "tokens.delete": "TokenMutationResult",
        "scene.geometry.createWall": "WallResult", "scene.geometry.updateWall": "WallResult",
        "scene.geometry.setDoorState": "WallResult", "scene.geometry.splitWall": "WallsResult",
        "scene.geometry.moveWallNode": "WallsResult", "scene.geometry.moveWalls": "WallsResult",
        "scene.geometry.deleteWall": "WallDeleteResult", "scene.geometry.deleteWalls": "WallsDeleteResult",
        "scene.geometry.createLight": "LightResult", "scene.geometry.updateLight": "LightResult",
        "scene.geometry.deleteLight": "LightDeleteResult",
        "combat.current": "CombatStateDTO", "combat.combatants": "CombatantDTO[]",
        "combat.start": "CombatStateDTO", "combat.end": "CombatStateDTO",
        "combat.advance": "CombatStateDTO", "combat.advanceRound": "CombatStateDTO",
        "combat.setTurn": "CombatStateDTO", "combat.interruptTurn": "CombatStateDTO", "combat.resumeTurn": "CombatStateDTO", "combat.setHolding": "CombatStateDTO", "combat.add": "CombatStateDTO",
        "combat.remove": "CombatStateDTO", "combat.setFlags": "CombatStateDTO",
        "combat.rollInitiative": "CombatStateDTO", "combat.setInitiative": "CombatStateDTO",
        "combat.moveCombatant": "CombatStateDTO", "combat.setInitiativeOrder": "CombatStateDTO",
        "combat.register": "boolean", "combat.dispatch": "CombatProtocolPayload | undefined",
        "combat.renderSlot": "Node[]",
        "content.ref": "string", "content.resolve": "ContentResolutionDTO",
        "content.get": "ContentResolvedValue", "content.can": "boolean",
        "content.open": "ContentResolutionDTO", "content.link": "ContentLinkDTO",
        "content.search": "ContentSearchPageDTO",
        "journals.get": "JournalDTO | null", "journals.list": "JournalListResult",
        "journals.create": "JournalMutationResult", "journals.update": "JournalMutationResult",
        "journals.delete": "JournalMutationResult",
        "pdf.get": "PdfDocumentDTO", "pdf.metadata": "PdfMetadataDTO",
        "pdf.annotations.list": "PdfAnnotationDTO[]", "pdf.annotations.create": "PdfAnnotationResult",
        "pdf.annotations.update": "PdfAnnotationResult", "pdf.annotations.delete": "PdfAnnotationDeleteResult",
        "pdf.viewer.open": "PdfViewerOpenResult", "pdf.viewer.goToPage": "number",
        "pdf.viewer.search": "PdfSearchMatch[]",
        "rules.actions.list": "ActionDefinitionDTO[]", "rules.actions.get": "ActionDefinitionDTO",
        "rules.actions.resolve": "ActionDefinitionDTO", "rules.actions.execute": "ActionExecutionResult",
        "rules.actions.executeReference": "ActionExecutionResult",
        "scene.effects.presets": "ParticlePresetDTO[]", "scene.effects.list": "EffectStateDTO",
        "scene.effects.create": "ParticleResultDTO", "scene.effects.update": "ParticleResultDTO",
        "scene.effects.delete": "ParticleDeleteResult",
        "scene.fog.state": "FogStateDTO", "scene.fog.enable": "FogMutationResult",
        "scene.fog.disable": "FogMutationResult", "scene.fog.reset": "FogMutationResult",
        "scene.fog.paint": "FogMutationResult",
        "scene.images.list": "SceneImageListResult", "scene.images.place": "SceneImageResult",
        "scene.images.update": "SceneImageResult", "scene.images.delete": "SceneImageDeleteResult",
        "scene.templates.list": "SceneTemplateListResult", "scene.templates.get": "SceneTemplateDTO | null",
        "scene.templates.create": "SceneTemplateResult", "scene.templates.update": "SceneTemplateResult",
        "scene.templates.delete": "SceneTemplateDeleteResult",
        "scene.zones.list": "SceneZoneDTO[]", "scene.zones.get": "SceneZoneDTO | null",
        "scene.zones.members": "string[]", "scene.zones.create": "SceneZoneDTO",
        "scene.zones.update": "SceneZoneDTO", "scene.zones.delete": "SceneZoneDeleteResult",
        "scene.objectTypes.register": "Promise<Disposer>",
        "scene.objects.list": "SceneObjectDTO[]", "scene.objects.get": "SceneObjectDTO | null", "scene.objects.hitTest": "SceneObjectDTO[]",
        "scene.objects.create": "SceneObjectDTO", "scene.objects.update": "SceneObjectDTO", "scene.objects.delete": "SceneObjectDeleteResult", "scene.objects.interact": "SceneObjectInteractionIntentDTO",
        "ui.presentations.show": "PresentationDTO", "ui.presentations.get": "PresentationDTO | null", "ui.presentations.list": "PresentationDTO[]", "ui.presentations.wait": "PresentationDTO | null", "ui.presentations.update": "PresentationDTO", "ui.presentations.close": "PresentationCloseResult",
        "ui.dragDrop.registerSource": "Promise<Disposer>", "ui.dragDrop.registerTarget": "Promise<Disposer>", "ui.dragDrop.sources": "SemanticRegistrationDTO[]", "ui.dragDrop.targets": "SemanticRegistrationDTO[]", "ui.dragDrop.drop": "SemanticDropResultDTO",
        "audio.play": "AudioPlaybackDTO", "audio.get": "AudioPlaybackDTO | null", "audio.list": "AudioPlaybackDTO[]", "audio.update": "AudioPlaybackDTO", "audio.stop": "AudioPlaybackDTO",
        "scene.spatialSounds.list": "SpatialSoundDTO[]", "scene.spatialSounds.get": "SpatialSoundDTO | null", "scene.spatialSounds.create": "SpatialSoundDTO", "scene.spatialSounds.update": "SpatialSoundDTO", "scene.spatialSounds.delete": "SpatialSoundDeleteResult",
        "sounds.list": "SoundDTO[]", "sounds.get": "SoundDTO | null", "sounds.create": "SoundDTO", "sounds.update": "SoundDTO", "sounds.delete": "SoundDeleteResult",
        "navigation.scene.go": "SceneNavigationDTO", "navigation.scene.getState": "SceneNavigationStateDTO | null",
        "input.commands.register": "Promise<Disposer>", "input.commands.list": "InputCommandDTO[]", "input.commands.execute": "ActionExecutionResult", "input.bindings.get": "InputBindingDTO[]", "input.bindings.set": "InputBindingDTO", "input.gestures.register": "Promise<Disposer>",
        "interactions.request": "InteractionDTO", "interactions.get": "InteractionDTO | null",
        "interactions.list": "InteractionDTO[]", "interactions.respond": "InteractionDTO", "interactions.cancel": "InteractionDTO",
        "dice.roll": "Promise<RollResultDTO>", "rolls.intent": "Promise<RollResultDTO | SheetDataPatchResult>",
        "handouts.present": "HandoutPresentResult", "settings.definitions": "SettingDefinitionDTO[]",
        "settings.all": "SettingValues", "settings.get": "SettingValue | undefined",
        "settings.set": "SettingSetResult", "storage.sqlite.query": "StorageQueryResult",
        "storage.sqlite.execute": "StorageExecuteResult", "storage.sqlite.status": "StorageStatusDTO",
        "cards.definitions.list": "CardDefinitionDTO[]", "cards.definitions.get": "CardDefinitionDTO | null",
        "cards.definitions.instantiate": "CardDefinitionInstantiateResult", "cards.state": "CardStateDTO",
        "cards.shuffle": "CardDeckMutationResult", "cards.reset": "CardDeckMutationResult",
        "cards.draw": "CardDrawResult", "cards.reveal": "CardIdsResult", "cards.discard": "CardIdsResult",
        "cards.play": "CardPlayResult", "cards.updatePlacement": "CardPlacementResult",
        "cards.discardPlacement": "CardPlacementDiscardResult",
        "scene.activeCanvas": "HTMLElement | null", "scene.activeCameraForScene": "CameraDTO | null",
        "tokens.centerOn": "void", "ui.toast": "ToastHandle | undefined",
        "ui.openModal": "void", "ui.closeModal": "void",
        "ui.applications.register": "Disposer", "ui.applications.render": "Promise<ApplicationInstance | null>",
        "ui.applications.close": "void", "sheets.helpers": "SheetHelpers",
        "sheets.register": "void", "sheets.registerController": "boolean",
        "content.packs": "ContentPackSummaryDTO[]", "content.pack": "ContentPackDTO | null",
    }
    return exact.get(path, primitives.get(path, structured.get(path, "JsonValue")))


def _generic_refs(expression: str, seen: set[str] | None = None) -> set[str]:
    seen = set(seen or ())
    found: set[str] = set()
    for name in re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", expression):
        if name in seen:
            continue
        if name in DYNAMIC_TYPES:
            found.add(name)
            continue
        seen.add(name)
        if name in TYPE_ALIASES:
            found.update(_generic_refs(TYPE_ALIASES[name], seen))
        if name in DTOS:
            for field_type in DTOS[name].values():
                found.update(_generic_refs(field_type, seen))
    return found


def build() -> dict:
    registry=json.loads(REGISTRY.read_text(encoding="utf-8")); manifest=json.loads(MANIFEST.read_text(encoding="utf-8")); source=RUNTIME.read_text(encoding="utf-8")
    signatures=_method_signatures(source)
    signatures.update({"events.available": ("", False), "events.on": ("event, handler", False), "events.once": ("event, handler", False)})
    gates={method:name for name,item in registry["capabilities"].items() for method in item.get("methods",[])}
    missing=sorted(set(gates)-set(signatures))
    if missing:
        raise RuntimeError("runtime signatures missing: "+", ".join(missing))
    methods=[]
    for path in sorted(gates):
        raw,asynchronous=signatures[path]
        methods.append({"path":path,"signature":f"sdk.{path}({raw})","requiredCapability":gates[path],"parameters":[_parameter(path, value) for value in _split_parameters(raw)],"returns":_return_type(path),"asynchronous":asynchronous,"errors":ERRORS,"lifecycle":"active package only; registrations return a disposer","concurrency":"server-authoritative; expectedVersion is atomic CAS when present","visibility":"current-user authority projection; hidden resources are indistinguishable from missing resources","durability":"durable only for server resources; local registrations and presentation handles end on package unload"})
    event_block=source.split("const SDK_EVENT_TYPES",1)[1].split("]);",1)[0]
    events=sorted(set(re.findall(r'"([a-z][a-z0-9.]+)"',event_block)))
    capabilities=[]
    for name,item in sorted(registry["capabilities"].items()):
        capabilities.append({"name":name,"status":item["status"],"description":item["description"],"surfaces":item.get("surfaces",[]),"methods":item.get("methods",[]),"authority":"declared capability plus current-user visibility/mutation authority","visibility":"filtered at the server boundary","securityBoundary":"never grants raw filesystem, database, transport, renderer, or permission-override authority"})
    dto_schemas={name:{"type":"object","additionalProperties":False,"required":[field for field in fields if not field.endswith("?")],"properties":{field.removesuffix("?"):{"typeExpression":kind} for field,kind in fields.items()}} for name,fields in DTOS.items()}
    return_generic_usages = []
    parameter_generic_usages = []
    for item in methods:
        item["justifiedGenericReturn"] = sorted(_generic_refs(item["returns"]))
        if item["justifiedGenericReturn"]:
            return_generic_usages.append({"method": item["path"], "types": item["justifiedGenericReturn"]})
        for parameter in item["parameters"]:
            parameter["justifiedGenericTypes"] = sorted(_generic_refs(parameter["type"]))
            if parameter["justifiedGenericTypes"]:
                parameter_generic_usages.append({"method": item["path"], "parameter": parameter["name"], "types": parameter["justifiedGenericTypes"]})
    generic_audit = {"unresolvedReturns":0,"unresolvedParameters":0,"justifiedReturnUsages":return_generic_usages,"justifiedParameterUsages":parameter_generic_usages,"semanticTypes":[{"name":name,**value} for name,value in sorted(DYNAMIC_TYPES.items())]}
    return {"schemaVersion":1,"sdkVersion":"1","manifestSchema":manifest,"packageKinds":manifest["properties"]["kind"]["enum"],"capabilities":capabilities,"methods":methods,"dtos":dto_schemas,"typeAliases":TYPE_ALIASES,"dynamicTypes":DYNAMIC_TYPES,"genericAudit":generic_audit,"events":[{"name":name,"delivery":"authorized, schema-versioned event; re-read current state"} for name in events],"errors":ERRORS}


DOC_TEXT = {
    "en": {"methods":"SDK 1 method reference","intro":"Generated from the frozen registries. Parameter names and defaults are exact JavaScript signatures.","cap":"Capability","returns":"Returns","errors":"Errors","params":"Parameters","authority":"Authority","visibility":"Visibility","concurrency":"Concurrency","durability":"Durability","lifecycle":"Lifecycle","yes":"Yes","no":"No","types":"SDK 1 DTO and type reference","types_intro":"Canonical structures generated from the SDK 1 DTO/input registry.","fields":"Fields","definition":"Definition","dynamic":"Extensible semantic types","dynamic_reason":"This shape is intentionally extensible by contract: keys and nested values are supplied by the active ruleset, package, user content, or negotiated semantic protocol. It remains a named JSON-safe type, never `any` or `unknown`.","index":"SDK 1 structural contract index","index_intro":"Canonical identifiers are not translated. Structure comes from `gravewright-sdk-1.json`.","caps":"Capabilities","events":"Events","event_anchor":"events","error_title":"Errors","status":"Status","delivery":"Delivery","kinds":"Package kinds","methods_label":"Methods","events_label":"Events","security":"Security boundary"},
    "pt-br": {"methods":"Referência de métodos da SDK 1","intro":"Gerada a partir dos registros congelados. Nomes e defaults dos parâmetros são assinaturas JavaScript exatas.","cap":"Capability","returns":"Retorno","errors":"Erros","params":"Parâmetros","authority":"Autoridade","visibility":"Visibilidade","concurrency":"Concorrência","durability":"Durabilidade","lifecycle":"Ciclo de vida","yes":"Sim","no":"Não","types":"Referência de DTOs e tipos da SDK 1","types_intro":"Estruturas canônicas geradas a partir do registro de DTOs/inputs da SDK 1.","fields":"Campos","definition":"Definição","dynamic":"Tipos semânticos extensíveis","dynamic_reason":"Este shape é intencionalmente extensível por contrato: chaves e valores aninhados vêm do ruleset ativo, package, conteúdo do usuário ou protocolo semântico negociado. Continua sendo um tipo JSON-safe nomeado, nunca `any` ou `unknown`.","index":"Índice estrutural do contrato SDK 1","index_intro":"Identifiers canônicos não são traduzidos. A estrutura vem de `gravewright-sdk-1.json`.","caps":"Capabilities","events":"Eventos","event_anchor":"eventos","error_title":"Erros","status":"Status","delivery":"Entrega","kinds":"Tipos de package","methods_label":"Métodos","events_label":"Eventos","security":"Limite de segurança"},
    "es": {"methods":"Referencia de métodos de SDK 1","intro":"Generada desde los registros congelados. Los nombres y defaults de parámetros son firmas JavaScript exactas.","cap":"Capability","returns":"Retorno","errors":"Errores","params":"Parámetros","authority":"Autoridad","visibility":"Visibilidad","concurrency":"Concurrencia","durability":"Durabilidad","lifecycle":"Ciclo de vida","yes":"Sí","no":"No","types":"Referencia de DTOs y tipos de SDK 1","types_intro":"Estructuras canónicas generadas desde el registro de DTOs/inputs de SDK 1.","fields":"Campos","definition":"Definición","dynamic":"Tipos semánticos extensibles","dynamic_reason":"Este shape es intencionalmente extensible por contrato: las claves y los valores anidados proceden del ruleset activo, package, contenido del usuario o protocolo semántico negociado. Sigue siendo un tipo JSON-safe con nombre, nunca `any` ni `unknown`.","index":"Índice estructural del contrato SDK 1","index_intro":"Los identifiers canónicos no se traducen. La estructura procede de `gravewright-sdk-1.json`.","caps":"Capabilities","events":"Eventos","event_anchor":"eventos","error_title":"Errores","status":"Status","delivery":"Entrega","kinds":"Tipos de package","methods_label":"Métodos","events_label":"Eventos","security":"Límite de seguridad"},
}

POLICY = {
    "en": {"authority":"Declared capability plus current-user resource authority; capabilities never elevate permissions.","visibility":"Current-user projection; hidden resources are indistinguishable from missing resources.","concurrency":"Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.","durability":"Only declared server resources are durable; local registrations end on package unload.","lifecycle":"The package must be installed, enabled, and active; registrations return a disposer.","delivery":"Authorized, schema-versioned event; re-read current state.","security":"No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed."},
    "pt-br": {"authority":"Capability declarada mais autoridade do usuário atual sobre o recurso; capabilities nunca elevam permissões.","visibility":"Projeção do usuário atual; recursos ocultos são indistinguíveis de inexistentes.","concurrency":"Autoritativo no servidor; `expectedVersion` é compare-and-swap atômico quando declarado.","durability":"Somente recursos de servidor declarados são duráveis; registros locais terminam no unload do package.","lifecycle":"O package deve estar instalado, habilitado e ativo; registros retornam um disposer.","delivery":"Evento autorizado e versionado por schema; releia o estado atual.","security":"Não expõe filesystem, database, transport, renderer, internals de ACL nem override de permissão."},
    "es": {"authority":"Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.","visibility":"Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.","concurrency":"Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.","durability":"Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.","lifecycle":"El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.","delivery":"Evento autorizado y versionado por schema; vuelva a leer el estado actual.","security":"No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos."},
}


def render_methods(contract: dict, locale: str) -> str:
    t, policy = DOC_TEXT[locale], POLICY[locale]
    lines=[f"# {t['methods']}","",t["intro"],""]
    for item in contract["methods"]:
        returned=f"Promise<{item['returns']}>" if item["asynchronous"] else item["returns"]
        lines += [f"## `{item['signature']}`","",f"{t['cap']}: `{item['requiredCapability']}`",f"{t['returns']}: `{returned}`",f"{t['errors']}: {', '.join(f'`{code}`' for code in item['errors'])}",f"{t['authority']}: {policy['authority']}",f"{t['visibility']}: {policy['visibility']}",f"{t['concurrency']}: {policy['concurrency']}",f"{t['durability']}: {policy['durability']}",f"{t['lifecycle']}: {policy['lifecycle']}",""]
        if item["parameters"]:
            lines += [f"{t['params']}:","","| Parameter | Type | Required | Default |","|---|---|:---:|---|"]
            for parameter in item["parameters"]:
                lines.append(f"| `{parameter['name']}` | `{parameter['type']}` | {t['yes'] if parameter['required'] else t['no']} | `{parameter['default']}` |")
            lines.append("")
    return "\n".join(lines)


def render_dto_reference(contract: dict, locale: str) -> str:
    t=DOC_TEXT[locale]; lines=[f"# {t['types']}","",t["types_intro"],""]
    for name,schema in sorted(contract["dtos"].items()):
        lines += [f"## `{name}`","",f"{t['fields']}:","","| Field | Type |","|---|---|"]
        lines.extend(f"| `{field}` | `{kind['typeExpression']}` |" for field,kind in schema["properties"].items()); lines.append("")
    for name,definition in sorted(contract["typeAliases"].items()): lines += [f"## `{name}`","",f"{t['definition']}: `{definition}`",""]
    lines += [f"# {t['dynamic']}",""]
    for name,value in sorted(contract["dynamicTypes"].items()):
        lines += [f"## `{name}`","",f"{t['definition']}: `{value['typeExpression']}`","",t["dynamic_reason"],""]
    return "\n".join(lines)


def render_contract_index(contract: dict, locale: str) -> str:
    t,policy=DOC_TEXT[locale],POLICY[locale]; lines=[f"# {t['index']}","",t["index_intro"],"",f"## {t['caps']}",""]
    for cap in contract["capabilities"]:
        methods=", ".join(f"`sdk.{name}`" for name in cap["methods"]) or "—"
        kinds=", ".join(f"`{kind}`" for kind in contract["packageKinds"])
        errors=", ".join(f"`{code}`" for code in contract["errors"])
        lines += [f"### `{cap['name']}`","",f"{t['status']}: `{cap['status']}`",f"{t['kinds']}: {kinds}",f"{t['methods_label']}: {methods}",f"{t['events_label']}: [{t['events']}](#{t['event_anchor']})",f"{t['errors']}: {errors}",f"{t['authority']}: {policy['authority']}",f"{t['visibility']}: {policy['visibility']}",f"{t['concurrency']}: {policy['concurrency']}",f"{t['durability']}: {policy['durability']}",f"{t['lifecycle']}: {policy['lifecycle']}",f"{t['security']}: {policy['security']}",""]
    lines += [f"## {t['events']}",""]
    for event in contract["events"]: lines += [f"### `{event['name']}`","",f"{t['delivery']}: {policy['delivery']}",""]
    lines += [f"## {t['error_title']}",""]; lines.extend(f"- `{code}`" for code in contract["errors"]); lines.append("")
    return "\n".join(lines)


def render_types(contract: dict) -> str:
    lines=["// Generated SDK 1 declarations. JavaScript remains the runtime requirement.","type JsonPrimitive = string | number | boolean | null;","type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };",""]
    lines += ["export type JsonObject = { [key: string]: JsonValue };", "export type CardMetadata = JsonObject;", "export type CardMetadataSchema = JsonObject;", ""]
    lines.extend(f"export type {name} = {expression};" for name, expression in TYPE_ALIASES.items())
    lines.append("")
    for name,fields in DTOS.items():
        lines.append(f"export interface {name} {{")
        lines.extend(f"  {field}: {kind};" for field,kind in fields.items())
        lines += ["}",""]
    tree: dict = {}
    for method in contract["methods"]:
        node=tree
        parts=method["path"].split(".")
        for part in parts[:-1]: node=node.setdefault(part,{})
        node[parts[-1]]={"$method":method}
    def render_node(node: dict, indent: str) -> list[str]:
        output=[]
        for name,value in sorted(node.items()):
            if "$method" in value:
                method=value["$method"]
                params=[]
                for parameter in method["parameters"]:
                    kind={"object":"Record<string, JsonValue>","function":"(...args: unknown[]) => unknown"}.get(parameter["type"],parameter["type"])
                    params.append(f"{parameter['name']}{'' if parameter['required'] else '?'}: {kind}")
                returned=f"Promise<{method['returns']}>" if method["asynchronous"] else method["returns"]
                output.append(f"{indent}{name}({', '.join(params)}): {returned};")
            else:
                output.append(f"{indent}readonly {name}: {{")
                output.extend(render_node(value,indent+"  "))
                output.append(f"{indent}}};")
        return output
    lines += ["export interface GravewrightSDK {","  readonly version: '1';","  readonly package: Readonly<{ id: string; kind: string; version: string }>;","  readonly kind: string;","  readonly capabilities: { has(capability: string): boolean; require(capability: string, apiName?: string): void; list(): readonly string[] };","  context(): Readonly<SdkContextDTO>;"]
    lines.extend(render_node(tree,"  "))
    lines += ["}","","declare global { interface Window { GravewrightSDK: { register(definition: { id: string; setup?(sdk: GravewrightSDK, payload: PackageLifecyclePayload): void; ready?(sdk: GravewrightSDK, payload: PackageLifecyclePayload): void; unload?(): void }): void } } }",""]
    return "\n".join(lines)


def main() -> None:
    contract = build()
    outputs = {
        OUTPUT: json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        DECLARATIONS: render_types(contract),
    }
    for locale,directory in LOCALE_DOCS.items():
        outputs[directory / "method-reference.md"] = render_methods(contract, locale)
        outputs[directory / "dto-reference.md"] = render_dto_reference(contract, locale)
        outputs[directory / "contract-index.md"] = render_contract_index(contract, locale)
    if "--check" in sys.argv:
        drift = [str(path.relative_to(ROOT)) for path, content in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if drift:
            raise SystemExit("generated SDK 1 contract drift: " + ", ".join(drift))
        if "--strict" in sys.argv:
            unresolved_returns = [item["path"] for item in contract["methods"] if item["returns"] == "JsonValue"]
            unresolved_parameters = [
                f"{item['path']}:{parameter['name']}"
                for item in contract["methods"]
                for parameter in item["parameters"]
                if parameter["type"] == "object"
            ]
            if unresolved_returns or unresolved_parameters:
                raise SystemExit(
                    f"unresolved returns={len(unresolved_returns)} parameters={len(unresolved_parameters)}"
                )
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__": main()
