# SDK 1 method reference

Generated from the frozen registries. Parameter names and defaults are exact JavaScript signatures.

## `sdk.actors.create(input = {})`

Capability: `actors.write`
Returns: `Promise<ActorMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ActorCreateInput` | No | `{}` |

## `sdk.actors.data(actorId)`

Capability: `actors.read`
Returns: `Promise<ActorDataDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |

## `sdk.actors.delete(actorId)`

Capability: `actors.write`
Returns: `Promise<ActorMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |

## `sdk.actors.get(actorId)`

Capability: `actors.read`
Returns: `Promise<ActorDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |

## `sdk.actors.items.insertCopy(actorId, sourceItemId, options = {})`

Capability: `actors.items.write`
Returns: `Promise<ActorItemInsertResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |
| `sourceItemId` | `string` | Yes | `None` |
| `options` | `ActorItemSlotOptions` | No | `{}` |

## `sdk.actors.items.listCopies(actorId, options = {})`

Capability: `actors.items.read`
Returns: `Promise<ActorItemCopyDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |
| `options` | `ActorItemSlotOptions` | No | `{}` |

## `sdk.actors.items.removeCopy(actorId, localInstanceId, options = {})`

Capability: `actors.items.write`
Returns: `Promise<ActorItemRemoveResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |
| `localInstanceId` | `string` | Yes | `None` |
| `options` | `ActorItemSlotOptions` | No | `{}` |

## `sdk.actors.items.slots(actorId)`

Capability: `actors.items.read`
Returns: `Promise<ActorItemSlotDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |

## `sdk.actors.list(query = {})`

Capability: `actors.read`
Returns: `Promise<ActorDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `EntityListQuery` | No | `{}` |

## `sdk.actors.patchData(actorId, patch = {})`

Capability: `actors.data.write`
Returns: `Promise<SheetDataPatchResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |
| `patch` | `RulesetSheetData` | No | `{}` |

## `sdk.actors.update(actorId, patch = {}, options = {})`

Capability: `actors.write`
Returns: `Promise<ActorMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Yes | `None` |
| `patch` | `ActorUpdateInput` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.assets.cancelImport(assetId)`

Capability: `assets.import`
Returns: `Promise<AssetCancelResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `assetId` | `string` | Yes | `None` |

## `sdk.assets.ingest(file)`

Capability: `assets.import`
Returns: `Promise<AssetIngestResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `file` | `File` | Yes | `None` |

## `sdk.assets.list(options = {})`

Capability: `assets.library`
Returns: `Promise<AssetDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `AssetListOptions` | No | `{}` |

## `sdk.audio.get(id)`

Capability: `audio.playback`
Returns: `Promise<AudioPlaybackDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.audio.list(options = {})`

Capability: `audio.playback`
Returns: `Promise<AudioPlaybackDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `AudioListOptions` | No | `{}` |

## `sdk.audio.play(input = {})`

Capability: `audio.playback`
Returns: `Promise<AudioPlaybackDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `AudioPlayInput` | No | `{}` |

## `sdk.audio.stop(id, options = {})`

Capability: `audio.playback`
Returns: `Promise<AudioPlaybackDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `AudioMutationOptions` | No | `{}` |

## `sdk.audio.update(id, patch = {}, options = {})`

Capability: `audio.playback`
Returns: `Promise<AudioPlaybackDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `patch` | `AudioPlaybackPatch` | No | `{}` |
| `options` | `AudioMutationOptions` | No | `{}` |

## `sdk.automation.audit()`

Capability: `automation.schedule`
Returns: `Promise<AutomationAuditDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.automation.cancel(jobId)`

Capability: `automation.schedule`
Returns: `Promise<AutomationCancelResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `jobId` | `string` | Yes | `None` |

## `sdk.automation.get(jobId)`

Capability: `automation.schedule`
Returns: `Promise<AutomationJobDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `jobId` | `string` | Yes | `None` |

## `sdk.automation.list()`

Capability: `automation.schedule`
Returns: `Promise<AutomationJobDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.automation.schedule(actionId, input = {}, options = {})`

Capability: `automation.schedule`
Returns: `Promise<AutomationJobDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Yes | `None` |
| `input` | `ActionInput` | No | `{}` |
| `options` | `AutomationScheduleOptions` | No | `{}` |

## `sdk.bus.provide(method, handler)`

Capability: `bus.provide`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `method` | `string` | Yes | `None` |
| `handler` | `InteropHandler` | Yes | `None` |

## `sdk.bus.publish(name, payload)`

Capability: `bus.publish`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Yes | `None` |
| `payload` | `InteropPayload` | Yes | `None` |

## `sdk.bus.request(method, payload, options)`

Capability: `bus.request`
Returns: `Promise<BusResponse>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `method` | `string` | Yes | `None` |
| `payload` | `InteropPayload` | Yes | `None` |
| `options` | `BusRequestOptions` | Yes | `None` |

## `sdk.bus.subscribe(name, fn)`

Capability: `bus.subscribe`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Yes | `None` |
| `fn` | `InteropSubscriber` | Yes | `None` |

## `sdk.campaign.members()`

Capability: `campaign.members.read`
Returns: `Promise<CampaignMemberDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.cards.definitions.get(id, version)`

Capability: `cards.read`
Returns: `Promise<CardDefinitionDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `version` | `number` | Yes | `None` |

## `sdk.cards.definitions.instantiate(id, options = {})`

Capability: `cards.manage`
Returns: `Promise<CardDefinitionInstantiateResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `CardDefinitionInstantiateOptions` | No | `{}` |

## `sdk.cards.definitions.list()`

Capability: `cards.read`
Returns: `Promise<CardDefinitionDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.cards.discard(cardIds)`

Capability: `cards.manage`
Returns: `Promise<CardIdsResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardIds` | `string[]` | Yes | `None` |

## `sdk.cards.discardPlacement(placementId)`

Capability: `cards.manage`
Returns: `Promise<CardPlacementDiscardResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Yes | `None` |

## `sdk.cards.draw(deckId, options = {})`

Capability: `cards.manage`
Returns: `Promise<CardDrawResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Yes | `None` |
| `options` | `CardDrawOptions` | No | `{}` |

## `sdk.cards.play(cardId, options = {})`

Capability: `cards.manage`
Returns: `Promise<CardPlayResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardId` | `string` | Yes | `None` |
| `options` | `CardPlayOptions` | No | `{}` |

## `sdk.cards.reset(deckId, options = {})`

Capability: `cards.manage`
Returns: `Promise<CardDeckMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Yes | `None` |
| `options` | `CardResetOptions` | No | `{}` |

## `sdk.cards.reveal(cardIds)`

Capability: `cards.manage`
Returns: `Promise<CardIdsResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardIds` | `string[]` | Yes | `None` |

## `sdk.cards.shuffle(deckId)`

Capability: `cards.manage`
Returns: `Promise<CardDeckMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Yes | `None` |

## `sdk.cards.state()`

Capability: `cards.read`
Returns: `Promise<CardStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.cards.updatePlacement(placementId, patch = {})`

Capability: `cards.manage`
Returns: `Promise<CardPlacementResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Yes | `None` |
| `patch` | `CardPlacementPatch` | No | `{}` |

## `sdk.chat.get(messageId)`

Capability: `chat.read`
Returns: `Promise<ChatMessageDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `messageId` | `string` | Yes | `None` |

## `sdk.chat.list(options = {})`

Capability: `chat.read`
Returns: `Promise<ChatMessageDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `ChatListOptions` | No | `{}` |

## `sdk.chat.send(message)`

Capability: `chat.cards`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `message` | `string | ChatSendMessage` | Yes | `None` |

## `sdk.combat.add(input = {})`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `CombatAddInput` | No | `{}` |

## `sdk.combat.advance(delta = 1)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `delta` | `number` | No | `1` |

## `sdk.combat.advanceRound(delta = 1)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `delta` | `number` | No | `1` |

## `sdk.combat.combatants()`

Capability: `combat.read`
Returns: `Promise<CombatantDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.combat.current()`

Capability: `combat.read`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.combat.dispatch(name, payload)`

Capability: `combat.runtime`
Returns: `CombatProtocolPayload | undefined`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Yes | `None` |
| `payload` | `CombatProtocolPayload` | Yes | `None` |

## `sdk.combat.end()`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.combat.interruptTurn(combatantId)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Yes | `None` |

## `sdk.combat.moveCombatant(combatantId, delta)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Yes | `None` |
| `delta` | `number` | Yes | `None` |

## `sdk.combat.register(plugin)`

Capability: `combat.runtime`
Returns: `boolean`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `plugin` | `CombatPlugin` | Yes | `None` |

## `sdk.combat.registerPanel(panel)`

Capability: `combat.runtime`
Returns: `boolean`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `panel` | `CombatPanelDefinition` | Yes | `None` |

## `sdk.combat.remove(combatantId)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Yes | `None` |

## `sdk.combat.renderSlot(name, payload)`

Capability: `combat.runtime`
Returns: `Node[]`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Yes | `None` |
| `payload` | `CombatProtocolPayload` | Yes | `None` |

## `sdk.combat.resumeTurn()`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.combat.rollInitiative(options = {})`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `CombatRollInitiativeOptions` | No | `{}` |

## `sdk.combat.setFlags(combatantId, flags = {})`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Yes | `None` |
| `flags` | `CombatFlagsPatch` | No | `{}` |

## `sdk.combat.setHolding(combatantId, holding = true)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Yes | `None` |
| `holding` | `boolean` | No | `true` |

## `sdk.combat.setInitiative(combatantId, value)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Yes | `None` |
| `value` | `number` | Yes | `None` |

## `sdk.combat.setInitiativeOrder(entries)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `entries` | `CombatInitiativeOrderEntry[]` | Yes | `None` |

## `sdk.combat.setTurn(combatantId)`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Yes | `None` |

## `sdk.combat.start(input = {})`

Capability: `combat.manage`
Returns: `Promise<CombatStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `CombatStartInput` | No | `{}` |

## `sdk.commands.register(name, handler)`

Capability: `commands.register`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Yes | `None` |
| `handler` | `CommandHandler` | Yes | `None` |

## `sdk.content.can(reference, action = "read")`

Capability: `content.references`
Returns: `Promise<boolean>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Yes | `None` |
| `action` | `string` | No | `"read"` |

## `sdk.content.get(reference)`

Capability: `content.references`
Returns: `Promise<ContentResolvedValue>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Yes | `None` |

## `sdk.content.link(reference, options = {})`

Capability: `content.references`
Returns: `ContentLinkDTO`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Yes | `None` |
| `options` | `ContentLinkOptions` | No | `{}` |

## `sdk.content.open(reference, options = {})`

Capability: `content.references`
Returns: `Promise<ContentResolutionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Yes | `None` |
| `options` | `ContentOpenOptions` | No | `{}` |

## `sdk.content.pack(packId)`

Capability: `content.packs`
Returns: `Promise<ContentPackDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packId` | `string` | Yes | `None` |

## `sdk.content.packs()`

Capability: `content.packs`
Returns: `Promise<ContentPackSummaryDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.content.ref(kind, resourceId, options = {})`

Capability: `content.references`
Returns: `string`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `kind` | `string` | Yes | `None` |
| `resourceId` | `string` | Yes | `None` |
| `options` | `ContentRefOptions` | No | `{}` |

## `sdk.content.resolve(reference)`

Capability: `content.references`
Returns: `Promise<ContentResolutionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Yes | `None` |

## `sdk.content.search(query = "", options = {})`

Capability: `content.index`
Returns: `Promise<ContentSearchPageDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `string` | No | `""` |
| `options` | `ContentSearchOptions` | No | `{}` |

## `sdk.dice.roll({ formula, label = "", actorId = "" } = {})`

Capability: `dice.roll`
Returns: `Promise<RollResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `DiceRollInput` | No | `"", actorId = "" } = {}` |

## `sdk.events.available()`

Capability: `events.subscribe`
Returns: `SdkEventName[]`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.events.on(event, handler)`

Capability: `events.subscribe`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `event` | `string` | Yes | `None` |
| `handler` | `SdkEventHandler` | Yes | `None` |

## `sdk.events.once(event, handler)`

Capability: `events.subscribe`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `event` | `string` | Yes | `None` |
| `handler` | `SdkEventHandler` | Yes | `None` |

## `sdk.gameplay.flows.advance(id, options = {})`

Capability: `gameplay.flows.manage`
Returns: `Promise<GameplayFlowDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `GameplayFlowMutationOptions` | No | `{}` |

## `sdk.gameplay.flows.get(id)`

Capability: `gameplay.flows.read`
Returns: `Promise<GameplayFlowDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.gameplay.flows.list()`

Capability: `gameplay.flows.read`
Returns: `Promise<GameplayFlowDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.gameplay.flows.register(definition = {})`

Capability: `gameplay.flows.manage`
Returns: `Promise<GameplayFlowDefinitionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `GameplayFlowDefinitionDTO` | No | `{}` |

## `sdk.gameplay.flows.start(input = {})`

Capability: `gameplay.flows.manage`
Returns: `Promise<GameplayFlowDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `GameplayFlowStartInput` | No | `{}` |

## `sdk.gameplay.flows.submit(id, value, options = {})`

Capability: `gameplay.flows.participate`
Returns: `Promise<GameplayFlowDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `value` | `GameplaySubmissionValue` | Yes | `None` |
| `options` | `GameplayFlowMutationOptions` | No | `{}` |

## `sdk.handouts.present(resourceType, resourceId, audience = {})`

Capability: `handouts.present`
Returns: `Promise<HandoutPresentResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `resourceType` | `string` | Yes | `None` |
| `resourceId` | `string` | Yes | `None` |
| `audience` | `HandoutAudience` | No | `{}` |

## `sdk.i18n.t(key, fallback)`

Capability: `locales`
Returns: `string`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Yes | `None` |
| `fallback` | `string` | Yes | `None` |

## `sdk.input.bindings.get()`

Capability: `input.commands`
Returns: `Promise<InputBindingDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.input.bindings.set(commandId, binding, options = {})`

Capability: `input.commands`
Returns: `Promise<InputBindingDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `commandId` | `string` | Yes | `None` |
| `binding` | `string` | Yes | `None` |
| `options` | `InputBindingOptions` | No | `{}` |

## `sdk.input.commands.execute(commandId, inputs = {})`

Capability: `input.commands`
Returns: `Promise<ActionExecutionResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `commandId` | `string` | Yes | `None` |
| `inputs` | `ActionInput` | No | `{}` |

## `sdk.input.commands.list()`

Capability: `input.commands`
Returns: `Promise<InputCommandDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.input.commands.register(definition = {}, handler = null)`

Capability: `input.commands`
Returns: `Promise<Promise<Disposer>>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `InputCommandDefinition` | No | `{}` |
| `handler` | `InputCommandHandler` | No | `null` |

## `sdk.input.gestures.register(definition = {}, handler = null)`

Capability: `input.commands`
Returns: `Promise<Promise<Disposer>>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `InputGestureDefinition` | No | `{}` |
| `handler` | `InputCommandHandler` | No | `null` |

## `sdk.interactions.cancel(id, options = {})`

Capability: `interactions.request`
Returns: `Promise<InteractionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.interactions.get(id)`

Capability: `interactions.respond`
Returns: `Promise<InteractionDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.interactions.list(options = {})`

Capability: `interactions.respond`
Returns: `Promise<InteractionDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `InteractionListOptions` | No | `{}` |

## `sdk.interactions.request(input = {})`

Capability: `interactions.request`
Returns: `Promise<InteractionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `InteractionRequestInput` | No | `{}` |

## `sdk.interactions.respond(id, response, options = {})`

Capability: `interactions.respond`
Returns: `Promise<InteractionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `response` | `InteractionResponseValue` | Yes | `None` |
| `options` | `InteractionMutationOptions` | No | `{}` |

## `sdk.items.create(input = {})`

Capability: `items.write`
Returns: `Promise<ItemMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ItemCreateInput` | No | `{}` |

## `sdk.items.delete(itemId)`

Capability: `items.write`
Returns: `Promise<ItemMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Yes | `None` |

## `sdk.items.get(itemId)`

Capability: `items.read`
Returns: `Promise<ItemDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Yes | `None` |

## `sdk.items.list(query = {})`

Capability: `items.read`
Returns: `Promise<ItemDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `EntityListQuery` | No | `{}` |

## `sdk.items.patchData(itemId, patch = {})`

Capability: `items.data.write`
Returns: `Promise<ItemDataPatchResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Yes | `None` |
| `patch` | `RulesetSheetData` | No | `{}` |

## `sdk.items.update(itemId, patch = {}, options = {})`

Capability: `items.write`
Returns: `Promise<ItemMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Yes | `None` |
| `patch` | `ItemUpdateInput` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.journals.create(input = {})`

Capability: `journals.write`
Returns: `Promise<JournalMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `JournalCreateInput` | No | `{}` |

## `sdk.journals.delete(journalId)`

Capability: `journals.write`
Returns: `Promise<JournalMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Yes | `None` |

## `sdk.journals.get(journalId)`

Capability: `journals.read`
Returns: `Promise<JournalDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Yes | `None` |

## `sdk.journals.list(options = {})`

Capability: `journals.read`
Returns: `Promise<JournalListResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `JournalListOptions` | No | `{}` |

## `sdk.journals.update(journalId, patch = {})`

Capability: `journals.write`
Returns: `Promise<JournalMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Yes | `None` |
| `patch` | `JournalUpdatePatch` | No | `{}` |

## `sdk.navigation.scene.getState()`

Capability: `navigation.scene`
Returns: `Promise<SceneNavigationStateDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.navigation.scene.go(input = {})`

Capability: `navigation.scene`
Returns: `Promise<SceneNavigationDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `SceneNavigationInput` | No | `{}` |

## `sdk.packages.get(packageId)`

Capability: `packages.inspect`
Returns: `Promise<PackageDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packageId` | `string` | Yes | `None` |

## `sdk.packages.has(packageId)`

Capability: `packages.inspect`
Returns: `Promise<boolean>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packageId` | `string` | Yes | `None` |

## `sdk.pdf.annotations.create(documentId, annotation = {})`

Capability: `pdf.annotations.write`
Returns: `Promise<PdfAnnotationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |
| `annotation` | `PdfAnnotationInput` | No | `{}` |

## `sdk.pdf.annotations.delete(documentId, annotationId)`

Capability: `pdf.annotations.write`
Returns: `Promise<PdfAnnotationDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |
| `annotationId` | `string` | Yes | `None` |

## `sdk.pdf.annotations.list(documentId)`

Capability: `pdf.annotations.read`
Returns: `Promise<PdfAnnotationDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |

## `sdk.pdf.annotations.update(documentId, annotationId, annotation = {})`

Capability: `pdf.annotations.write`
Returns: `Promise<PdfAnnotationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |
| `annotationId` | `string` | Yes | `None` |
| `annotation` | `PdfAnnotationInput` | No | `{}` |

## `sdk.pdf.get(documentId)`

Capability: `pdf.read`
Returns: `Promise<PdfDocumentDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |

## `sdk.pdf.metadata(documentId)`

Capability: `pdf.read`
Returns: `Promise<PdfMetadataDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |

## `sdk.pdf.presentation.current(documentId)`

Capability: `pdf.presentation`
Returns: `Promise<PDFPresentationDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |

## `sdk.pdf.presentation.end(documentId)`

Capability: `pdf.presentation`
Returns: `Promise<PDFPresentationDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |

## `sdk.pdf.presentation.start(documentId, input = {})`

Capability: `pdf.presentation`
Returns: `Promise<PDFPresentationDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |
| `input` | `PdfPresentationStartInput` | No | `{}` |

## `sdk.pdf.presentation.update(documentId, page, options = {})`

Capability: `pdf.presentation`
Returns: `Promise<PDFPresentationDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |
| `page` | `number` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.pdf.viewer.currentPage(documentId)`

Capability: `pdf.viewer`
Returns: `number | null`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |

## `sdk.pdf.viewer.goToPage(documentId, page)`

Capability: `pdf.viewer`
Returns: `Promise<number>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |
| `page` | `number` | Yes | `None` |

## `sdk.pdf.viewer.open(reference, options = {})`

Capability: `pdf.viewer`
Returns: `Promise<PdfViewerOpenResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string` | Yes | `None` |
| `options` | `PdfViewerOpenOptions` | No | `{}` |

## `sdk.pdf.viewer.search(documentId, query)`

Capability: `pdf.viewer`
Returns: `Promise<PdfSearchMatch[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Yes | `None` |
| `query` | `string` | Yes | `None` |

## `sdk.permissions.can(action, resource = {})`

Capability: `permissions.inspect`
Returns: `Promise<boolean>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `action` | `string` | Yes | `None` |
| `resource` | `PermissionResource` | No | `{}` |

## `sdk.permissions.check(action, resource = {})`

Capability: `permissions.inspect`
Returns: `Promise<PermissionCheckDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `action` | `string` | Yes | `None` |
| `resource` | `PermissionResource` | No | `{}` |

## `sdk.rolls.actions.register(definition, handler)`

Capability: `rolls.actions`
Returns: `boolean`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `RollActionDefinition` | Yes | `None` |
| `handler` | `RollActionHandler` | Yes | `None` |

## `sdk.rolls.intent(payload = {})`

Capability: `rolls.intent`
Returns: `Promise<RollResultDTO | SheetDataPatchResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `payload` | `RollIntentInput` | No | `{}` |

## `sdk.rolls.reroll(messageId)`

Capability: `rolls.reroll`
Returns: `Promise<RollResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `messageId` | `string` | Yes | `None` |

## `sdk.rules.actions.execute(actionId, input = {}, options = {})`

Capability: `rules.actions`
Returns: `Promise<ActionExecutionResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Yes | `None` |
| `input` | `ActionInput` | No | `{}` |
| `options` | `ActionExecuteOptions` | No | `{}` |

## `sdk.rules.actions.executeReference(reference, input = {}, options = {})`

Capability: `rules.actions`
Returns: `Promise<ActionExecutionResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string` | Yes | `None` |
| `input` | `ActionInput` | No | `{}` |
| `options` | `ActionReferenceExecuteOptions` | No | `{}` |

## `sdk.rules.actions.get(actionId)`

Capability: `rules.actions`
Returns: `Promise<ActionDefinitionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Yes | `None` |

## `sdk.rules.actions.list()`

Capability: `rules.actions`
Returns: `Promise<ActionDefinitionDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.rules.actions.resolve({ provider, semantic } = {})`

Capability: `rules.actions`
Returns: `Promise<ActionDefinitionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ActionResolveInput` | No | `{}` |

## `sdk.scene.active()`

Capability: `scene.read`
Returns: `Promise<SceneDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.scene.activeCameraForScene(sceneId)`

Capability: `scene.tools`
Returns: `CameraDTO | null`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |

## `sdk.scene.activeCanvas()`

Capability: `scene.tools`
Returns: `HTMLElement | null`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.scene.effects.create(sceneId, kind, values = {})`

Capability: `scene.effects.write`
Returns: `Promise<ParticleResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `kind` | `string` | Yes | `None` |
| `values` | `ParticleValues` | No | `{}` |

## `sdk.scene.effects.delete(effectId, kind)`

Capability: `scene.effects.write`
Returns: `Promise<ParticleDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `effectId` | `string` | Yes | `None` |
| `kind` | `string` | Yes | `None` |

## `sdk.scene.effects.list(sceneId = context.scene?.id)`

Capability: `scene.effects.read`
Returns: `Promise<EffectStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.effects.presets()`

Capability: `scene.effects.read`
Returns: `Promise<ParticlePresetDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.scene.effects.update(effectId, kind, values = {})`

Capability: `scene.effects.write`
Returns: `Promise<ParticleResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `effectId` | `string` | Yes | `None` |
| `kind` | `string` | Yes | `None` |
| `values` | `ParticleValues` | No | `{}` |

## `sdk.scene.fog.disable(sceneId = context.scene?.id)`

Capability: `scene.fog.write`
Returns: `Promise<FogMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.fog.enable(sceneId = context.scene?.id, initial = "hide_all")`

Capability: `scene.fog.write`
Returns: `Promise<FogMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `initial` | `string` | No | `"hide_all"` |

## `sdk.scene.fog.paint(sceneId = context.scene?.id, ops = [], options = {})`

Capability: `scene.fog.write`
Returns: `Promise<FogMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `ops` | `FogOp[]` | No | `[]` |
| `options` | `FogPaintOptions` | No | `{}` |

## `sdk.scene.fog.reset(sceneId = context.scene?.id, to = "hide_all")`

Capability: `scene.fog.write`
Returns: `Promise<FogMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `to` | `string` | No | `"hide_all"` |

## `sdk.scene.fog.state(sceneId = context.scene?.id)`

Capability: `scene.fog.read`
Returns: `Promise<FogStateDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.geometry.createLight(sceneId, input = {})`

Capability: `scene.geometry.write`
Returns: `Promise<LightResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `input` | `LightCreateInput` | No | `{}` |

## `sdk.scene.geometry.createWall(sceneId, input = {})`

Capability: `scene.geometry.write`
Returns: `Promise<WallResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `input` | `WallCreateInput` | No | `{}` |

## `sdk.scene.geometry.deleteLight(lightId)`

Capability: `scene.geometry.write`
Returns: `Promise<LightDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `lightId` | `string` | Yes | `None` |

## `sdk.scene.geometry.deleteWall(wallId)`

Capability: `scene.geometry.write`
Returns: `Promise<WallDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Yes | `None` |

## `sdk.scene.geometry.deleteWalls(wallIds)`

Capability: `scene.geometry.write`
Returns: `Promise<WallsDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallIds` | `string[]` | Yes | `None` |

## `sdk.scene.geometry.lights(sceneId = context.scene?.id)`

Capability: `scene.geometry.read`
Returns: `Promise<LightDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.geometry.moveWallNode(sceneId, from, to)`

Capability: `scene.geometry.write`
Returns: `Promise<WallsResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `from` | `WorldPointDTO` | Yes | `None` |
| `to` | `WorldPointDTO` | Yes | `None` |

## `sdk.scene.geometry.moveWalls(sceneId, wallIds, delta)`

Capability: `scene.geometry.write`
Returns: `Promise<WallsResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `wallIds` | `string[]` | Yes | `None` |
| `delta` | `WorldPointDTO` | Yes | `None` |

## `sdk.scene.geometry.setDoorState(wallId, state)`

Capability: `scene.geometry.write`
Returns: `Promise<WallResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Yes | `None` |
| `state` | `string` | Yes | `None` |

## `sdk.scene.geometry.splitWall(wallId, x, y)`

Capability: `scene.geometry.write`
Returns: `Promise<WallsResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Yes | `None` |
| `x` | `number` | Yes | `None` |
| `y` | `number` | Yes | `None` |

## `sdk.scene.geometry.updateLight(lightId, patch = {})`

Capability: `scene.geometry.write`
Returns: `Promise<LightResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `lightId` | `string` | Yes | `None` |
| `patch` | `LightUpdatePatch` | No | `{}` |

## `sdk.scene.geometry.updateWall(wallId, patch = {})`

Capability: `scene.geometry.write`
Returns: `Promise<WallResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Yes | `None` |
| `patch` | `WallUpdatePatch` | No | `{}` |

## `sdk.scene.geometry.walls(sceneId = context.scene?.id)`

Capability: `scene.geometry.read`
Returns: `Promise<WallDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.get(sceneId)`

Capability: `scene.read`
Returns: `Promise<SceneDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |

## `sdk.scene.images.delete(placementId)`

Capability: `scene.images.write`
Returns: `Promise<SceneImageDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Yes | `None` |

## `sdk.scene.images.list(sceneId = context.scene?.id)`

Capability: `scene.images.read`
Returns: `Promise<SceneImageListResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.images.place(sceneId, assetId, options = {})`

Capability: `scene.images.write`
Returns: `Promise<SceneImageResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `assetId` | `string` | Yes | `None` |
| `options` | `SceneImagePlaceOptions` | No | `{}` |

## `sdk.scene.images.update(placementId, patch = {}, options = {})`

Capability: `scene.images.write`
Returns: `Promise<SceneImageResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Yes | `None` |
| `patch` | `SceneImageUpdatePatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.list()`

Capability: `scene.read`
Returns: `Promise<SceneDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.scene.measurements.cancel(sceneId, measurementId)`

Capability: `scene.measurements.shared`
Returns: `Promise<SharedMeasurementDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `measurementId` | `string` | Yes | `None` |

## `sdk.scene.measurements.listShared(sceneId = context.scene?.id)`

Capability: `scene.measurements.shared`
Returns: `Promise<SharedMeasurementDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.measurements.measure(sceneId, from, to)`

Capability: `scene.tools`
Returns: `Promise<MeasurementResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `from` | `WorldPointDTO` | Yes | `None` |
| `to` | `WorldPointDTO` | Yes | `None` |

## `sdk.scene.measurements.share(sceneId, geometry, options = {})`

Capability: `scene.measurements.shared`
Returns: `Promise<SharedMeasurementDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `geometry` | `SharedMeasurementGeometry` | Yes | `None` |
| `options` | `SharedMeasurementOptions` | No | `{}` |

## `sdk.scene.objectTypes.register(definition = {})`

Capability: `scene.objectTypes.register`
Returns: `Promise<Promise<Disposer>>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `SceneObjectTypeDefinition` | No | `{}` |

## `sdk.scene.objects.create(sceneId, input = {})`

Capability: `scene.objects.write`
Returns: `Promise<SceneObjectDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `input` | `SceneObjectInput` | No | `{}` |

## `sdk.scene.objects.delete(id, options = {})`

Capability: `scene.objects.write`
Returns: `Promise<SceneObjectDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.objects.get(id)`

Capability: `scene.objects.read`
Returns: `Promise<SceneObjectDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.scene.objects.hitTest(sceneId, point, options = {})`

Capability: `scene.objects.read`
Returns: `Promise<SceneObjectDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `point` | `WorldPointDTO` | Yes | `None` |
| `options` | `SceneObjectHitTestOptions` | No | `{}` |

## `sdk.scene.objects.interact(id, interactionId, options = {})`

Capability: `scene.objects.interact`
Returns: `Promise<SceneObjectInteractionIntentDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `interactionId` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.objects.list(sceneId = context.scene?.id, options = {})`

Capability: `scene.objects.read`
Returns: `Promise<SceneObjectDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `options` | `SceneObjectListOptions` | No | `{}` |

## `sdk.scene.objects.update(id, patch = {}, options = {})`

Capability: `scene.objects.write`
Returns: `Promise<SceneObjectDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `patch` | `SceneObjectPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.shaders.apply(sceneId, input = {})`

Capability: `scene.shaders.write`
Returns: `Promise<ShaderInstanceDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `input` | `ShaderApplyInput` | No | `{}` |

## `sdk.scene.shaders.customLibrary.clearPreview()`

Capability: `scene.shaders.customLibrary`
Returns: `CustomShaderPreviewResult`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.scene.shaders.customLibrary.openEditor(definition = null)`

Capability: `scene.shaders.customLibrary`
Returns: `Promise<CustomShaderDefinition | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderDefinition | null` | No | `null` |

## `sdk.scene.shaders.customLibrary.preview(definition)`

Capability: `scene.shaders.customLibrary`
Returns: `CustomShaderPreviewResult`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderDefinition` | Yes | `None` |

## `sdk.scene.shaders.customLibrary.registerProvider(definition = {})`

Capability: `scene.shaders.customLibrary`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderProviderDefinition` | No | `{}` |

## `sdk.scene.shaders.customLibrary.use(definition)`

Capability: `scene.shaders.customLibrary`
Returns: `Promise<CustomShaderUseResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderDefinition` | Yes | `None` |

## `sdk.scene.shaders.enable(id, enabled, options = {})`

Capability: `scene.shaders.write`
Returns: `Promise<ShaderInstanceDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `enabled` | `boolean` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.shaders.getPreset(presetId)`

Capability: `scene.shaders.read`
Returns: `Promise<ShaderPresetDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `presetId` | `string` | Yes | `None` |

## `sdk.scene.shaders.list(sceneId = context.scene?.id)`

Capability: `scene.shaders.read`
Returns: `Promise<ShaderInstanceDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.shaders.presets()`

Capability: `scene.shaders.read`
Returns: `Promise<ShaderPresetDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.scene.shaders.remove(id)`

Capability: `scene.shaders.write`
Returns: `Promise<ShaderRemovalResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.scene.shaders.update(id, patch = {}, options = {})`

Capability: `scene.shaders.write`
Returns: `Promise<ShaderInstanceDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `patch` | `ShaderUpdateInput` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.spatialSounds.create(sceneId, input = {})`

Capability: `scene.spatialSounds.write`
Returns: `Promise<SpatialSoundDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `input` | `SpatialSoundInput` | No | `{}` |

## `sdk.scene.spatialSounds.delete(id, options = {})`

Capability: `scene.spatialSounds.write`
Returns: `Promise<SpatialSoundDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.spatialSounds.get(id)`

Capability: `scene.spatialSounds.read`
Returns: `Promise<SpatialSoundDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.scene.spatialSounds.list(sceneId = context.scene?.id)`

Capability: `scene.spatialSounds.read`
Returns: `Promise<SpatialSoundDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.spatialSounds.update(id, patch = {}, options = {})`

Capability: `scene.spatialSounds.write`
Returns: `Promise<SpatialSoundDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `patch` | `SpatialSoundPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.templates.create(sceneId, values = {})`

Capability: `scene.templates.write`
Returns: `Promise<SceneTemplateResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `values` | `SceneTemplateValues` | No | `{}` |

## `sdk.scene.templates.delete(templateId, options = {})`

Capability: `scene.templates.write`
Returns: `Promise<SceneTemplateDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `templateId` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.templates.get(sceneId, templateId)`

Capability: `scene.templates.read`
Returns: `Promise<SceneTemplateDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `templateId` | `string` | Yes | `None` |

## `sdk.scene.templates.list(sceneId = context.scene?.id)`

Capability: `scene.templates.read`
Returns: `Promise<SceneTemplateListResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.templates.update(templateId, patch = {}, options = {})`

Capability: `scene.templates.write`
Returns: `Promise<SceneTemplateResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `templateId` | `string` | Yes | `None` |
| `patch` | `Partial<SceneTemplateValues>` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.zones.create(sceneId, input = {})`

Capability: `scene.zones.write`
Returns: `Promise<SceneZoneDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Yes | `None` |
| `input` | `SceneZoneInput` | No | `{}` |

## `sdk.scene.zones.delete(id, options = {})`

Capability: `scene.zones.write`
Returns: `Promise<SceneZoneDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.zones.get(id)`

Capability: `scene.zones.read`
Returns: `Promise<SceneZoneDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.scene.zones.list(sceneId = context.scene?.id)`

Capability: `scene.zones.read`
Returns: `Promise<SceneZoneDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.zones.members(id)`

Capability: `scene.zones.read`
Returns: `Promise<string[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.scene.zones.update(id, patch = {}, options = {})`

Capability: `scene.zones.write`
Returns: `Promise<SceneZoneDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `patch` | `SceneZonePatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.settings.all()`

Capability: `settings`
Returns: `SettingValues`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.settings.definitions()`

Capability: `settings`
Returns: `SettingDefinitionDTO[]`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.settings.get(key, fallback = undefined)`

Capability: `settings`
Returns: `SettingValue | undefined`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Yes | `None` |
| `fallback` | `string` | No | `undefined` |

## `sdk.settings.onChange(key, handler)`

Capability: `settings`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Yes | `None` |
| `handler` | `SettingChangeHandler` | Yes | `None` |

## `sdk.settings.scope(key)`

Capability: `settings`
Returns: `SettingScope | null`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Yes | `None` |

## `sdk.settings.set(key, value, options = {})`

Capability: `settings`
Returns: `Promise<SettingSetResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Yes | `None` |
| `value` | `number` | Yes | `None` |
| `options` | `SettingSetOptions` | No | `{}` |

## `sdk.sheets.helpers()`

Capability: `sheets.runtime`
Returns: `SheetHelpers`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.sheets.register(plugin)`

Capability: `sheets.runtime`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `plugin` | `SheetPlugin` | Yes | `None` |

## `sdk.sheets.registerController(sheetType, controller)`

Capability: `sheets.controller`
Returns: `boolean`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sheetType` | `string` | Yes | `None` |
| `controller` | `SheetController` | Yes | `None` |

## `sdk.sounds.create(input = {})`

Capability: `sounds.write`
Returns: `Promise<SoundDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `SoundCreateInput` | No | `{}` |

## `sdk.sounds.delete(id, options = {})`

Capability: `sounds.write`
Returns: `Promise<SoundDeleteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.sounds.get(id)`

Capability: `sounds.read`
Returns: `Promise<SoundDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.sounds.list(options = {})`

Capability: `sounds.read`
Returns: `Promise<SoundDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `SoundListOptions` | No | `{}` |

## `sdk.sounds.update(id, patch = {}, options = {})`

Capability: `sounds.write`
Returns: `Promise<SoundDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `patch` | `SoundPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.storage.sqlite.execute(scope, name, params = {})`

Capability: `storage.sqlite`
Returns: `Promise<StorageExecuteResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Yes | `None` |
| `name` | `string` | Yes | `None` |
| `params` | `StorageParams` | No | `{}` |

## `sdk.storage.sqlite.query(scope, name, params = {})`

Capability: `storage.sqlite`
Returns: `Promise<StorageQueryResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Yes | `None` |
| `name` | `string` | Yes | `None` |
| `params` | `StorageParams` | No | `{}` |

## `sdk.storage.sqlite.status(scope)`

Capability: `storage.sqlite`
Returns: `Promise<StorageStatusDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Yes | `None` |

## `sdk.timelines.cancel(id, options = {})`

Capability: `timelines.control`
Returns: `Promise<TimelineDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.timelines.get(id)`

Capability: `timelines.read`
Returns: `Promise<TimelineDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.timelines.list()`

Capability: `timelines.read`
Returns: `Promise<TimelineDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.timelines.register(definition = {})`

Capability: `timelines.start`
Returns: `Promise<TimelineDefinitionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `TimelineDefinitionDTO` | No | `{}` |

## `sdk.timelines.start(input = {})`

Capability: `timelines.start`
Returns: `Promise<TimelineDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `TimelineStartInput` | No | `{}` |

## `sdk.tokens.centerOn(tokenId)`

Capability: `tokens.extends`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Yes | `None` |

## `sdk.tokens.create(input = {})`

Capability: `tokens.manage`
Returns: `Promise<TokenMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `TokenCreateInput` | No | `{}` |

## `sdk.tokens.delete(tokenId, options = {})`

Capability: `tokens.manage`
Returns: `Promise<TokenMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Yes | `None` |
| `options` | `TokenOptions` | No | `{}` |

## `sdk.tokens.get(tokenId, options = {})`

Capability: `tokens.read`
Returns: `Promise<TokenDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Yes | `None` |
| `options` | `TokenReadOptions` | No | `{}` |

## `sdk.tokens.list(options = {})`

Capability: `tokens.read`
Returns: `Promise<TokenDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `TokenReadOptions` | No | `{}` |

## `sdk.tokens.move(tokenId, position = {}, options = {})`

Capability: `tokens.move`
Returns: `Promise<TokenMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Yes | `None` |
| `position` | `TokenMoveInput` | No | `{}` |
| `options` | `TokenOptions` | No | `{}` |

## `sdk.tokens.targets.clear(sceneId = context.scene?.id)`

Capability: `tokens.targets`
Returns: `Promise<string[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.tokens.targets.list(sceneId = context.scene?.id)`

Capability: `tokens.targets`
Returns: `Promise<string[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.tokens.targets.set(ids, sceneId = context.scene?.id)`

Capability: `tokens.targets`
Returns: `Promise<string[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `ids` | `string[]` | Yes | `None` |
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.tokens.transfer(tokenId, destination = {}, options = {})`

Capability: `tokens.transfer`
Returns: `Promise<TokenTransferResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Yes | `None` |
| `destination` | `TokenTransferDestination` | No | `{}` |
| `options` | `TokenTransferOptions` | No | `{}` |

## `sdk.tokens.transferMany(transfers = [], options = {})`

Capability: `tokens.transfer`
Returns: `Promise<TokenTransferResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `transfers` | `TokenTransferSpec[]` | No | `[]` |
| `options` | `TokenTransferManyOptions` | No | `{}` |

## `sdk.tokens.update(tokenId, patch = {}, options = {})`

Capability: `tokens.manage`
Returns: `Promise<TokenMutationResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Yes | `None` |
| `patch` | `TokenOverrides` | No | `{}` |
| `options` | `TokenOptions` | No | `{}` |

## `sdk.tools.activeTool()`

Capability: `scene.tools`
Returns: `string`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.tools.register(definition = {})`

Capability: `scene.tools`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `ToolDefinition` | No | `{}` |

## `sdk.ui.applications.close(applicationId)`

Capability: `ui.applications`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Yes | `None` |

## `sdk.ui.applications.register(applicationId, definition)`

Capability: `ui.applications`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Yes | `None` |
| `definition` | `ApplicationDefinition` | Yes | `None` |

## `sdk.ui.applications.render(applicationId, host, appContext = {}, options = {})`

Capability: `ui.applications`
Returns: `Promise<ApplicationInstance | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Yes | `None` |
| `host` | `HTMLElement` | Yes | `None` |
| `appContext` | `ApplicationContext` | No | `{}` |
| `options` | `ApplicationRenderOptions` | No | `{}` |

## `sdk.ui.closeModal(modalOrId)`

Capability: `assets.ui`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `modalOrId` | `string` | Yes | `None` |

## `sdk.ui.dragDrop.drop(input = {})`

Capability: `ui.dragDrop`
Returns: `Promise<SemanticDropResultDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `SemanticDropInput` | No | `{}` |

## `sdk.ui.dragDrop.registerSource(definition = {})`

Capability: `ui.dragDrop`
Returns: `Promise<Promise<Disposer>>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `DragSourceDefinition` | No | `{}` |

## `sdk.ui.dragDrop.registerTarget(definition = {})`

Capability: `ui.dragDrop`
Returns: `Promise<Promise<Disposer>>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `DropTargetDefinition` | No | `{}` |

## `sdk.ui.dragDrop.sources()`

Capability: `ui.dragDrop`
Returns: `Promise<SemanticRegistrationDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.ui.dragDrop.targets()`

Capability: `ui.dragDrop`
Returns: `Promise<SemanticRegistrationDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.ui.openModal(modalId)`

Capability: `assets.ui`
Returns: `void`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `modalId` | `string` | Yes | `None` |

## `sdk.ui.presentations.close(id, options = {})`

Capability: `ui.presentations`
Returns: `Promise<PresentationCloseResult>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.ui.presentations.get(id)`

Capability: `ui.presentations`
Returns: `Promise<PresentationDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.ui.presentations.list(options = {})`

Capability: `ui.presentations`
Returns: `Promise<PresentationDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `PresentationListOptions` | No | `{}` |

## `sdk.ui.presentations.show(input = {})`

Capability: `ui.presentations`
Returns: `Promise<PresentationDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `PresentationInput` | No | `{}` |

## `sdk.ui.presentations.update(id, patch = {}, options = {})`

Capability: `ui.presentations`
Returns: `Promise<PresentationDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `patch` | `PresentationPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.ui.presentations.wait(id, options = {})`

Capability: `ui.presentations`
Returns: `Promise<PresentationDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `PresentationWaitOptions` | No | `{}` |

## `sdk.ui.slots.available()`

Capability: `ui.slots`
Returns: `string[]`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.ui.slots.register(slotId, render)`

Capability: `ui.slots`
Returns: `Disposer`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `slotId` | `string` | Yes | `None` |
| `render` | `SlotRenderCallback` | Yes | `None` |

## `sdk.ui.toast(message, options)`

Capability: `assets.ui`
Returns: `ToastHandle | undefined`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `message` | `string` | Yes | `None` |
| `options` | `ToastOptions` | Yes | `None` |

## `sdk.users.presentation.get(userId)`

Capability: `users.presentation.read`
Returns: `Promise<UserPresentationDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `userId` | `string` | Yes | `None` |

## `sdk.users.presentation.list()`

Capability: `users.presentation.read`
Returns: `Promise<UserPresentationDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.workflows.cancel(id, options = {})`

Capability: `workflows.control`
Returns: `Promise<WorkflowDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.workflows.get(id)`

Capability: `workflows.read`
Returns: `Promise<WorkflowDTO | null>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Yes | `None` |

## `sdk.workflows.list()`

Capability: `workflows.read`
Returns: `Promise<WorkflowDTO[]>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

## `sdk.workflows.register(definition = {})`

Capability: `workflows.start`
Returns: `Promise<WorkflowDefinitionDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `WorkflowDefinitionDTO` | No | `{}` |

## `sdk.workflows.start(input = {})`

Capability: `workflows.start`
Returns: `Promise<WorkflowDTO>`
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.

Parameters:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `WorkflowStartInput` | No | `{}` |
