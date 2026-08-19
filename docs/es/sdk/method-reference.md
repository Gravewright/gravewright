# Referencia de métodos de SDK 1

Generada desde los registros congelados. Los nombres y defaults de parámetros son firmas JavaScript exactas.

## `sdk.actors.create(input = {})`

Capability: `actors.write`
Retorno: `Promise<ActorMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ActorCreateInput` | No | `{}` |

## `sdk.actors.data(actorId)`

Capability: `actors.read`
Retorno: `Promise<ActorDataDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |

## `sdk.actors.delete(actorId)`

Capability: `actors.write`
Retorno: `Promise<ActorMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |

## `sdk.actors.get(actorId)`

Capability: `actors.read`
Retorno: `Promise<ActorDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |

## `sdk.actors.items.insertCopy(actorId, sourceItemId, options = {})`

Capability: `actors.items.write`
Retorno: `Promise<ActorItemInsertResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |
| `sourceItemId` | `string` | Sí | `None` |
| `options` | `ActorItemSlotOptions` | No | `{}` |

## `sdk.actors.items.listCopies(actorId, options = {})`

Capability: `actors.items.read`
Retorno: `Promise<ActorItemCopyDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |
| `options` | `ActorItemSlotOptions` | No | `{}` |

## `sdk.actors.items.removeCopy(actorId, localInstanceId, options = {})`

Capability: `actors.items.write`
Retorno: `Promise<ActorItemRemoveResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |
| `localInstanceId` | `string` | Sí | `None` |
| `options` | `ActorItemSlotOptions` | No | `{}` |

## `sdk.actors.items.slots(actorId)`

Capability: `actors.items.read`
Retorno: `Promise<ActorItemSlotDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |

## `sdk.actors.list(query = {})`

Capability: `actors.read`
Retorno: `Promise<ActorDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `EntityListQuery` | No | `{}` |

## `sdk.actors.patchData(actorId, patch = {})`

Capability: `actors.data.write`
Retorno: `Promise<SheetDataPatchResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |
| `patch` | `RulesetSheetData` | No | `{}` |

## `sdk.actors.update(actorId, patch = {}, options = {})`

Capability: `actors.write`
Retorno: `Promise<ActorMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actorId` | `string` | Sí | `None` |
| `patch` | `ActorUpdateInput` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.assets.cancelImport(assetId)`

Capability: `assets.import`
Retorno: `Promise<AssetCancelResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `assetId` | `string` | Sí | `None` |

## `sdk.assets.ingest(file)`

Capability: `assets.import`
Retorno: `Promise<AssetIngestResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `file` | `File` | Sí | `None` |

## `sdk.assets.list(options = {})`

Capability: `assets.library`
Retorno: `Promise<AssetDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `AssetListOptions` | No | `{}` |

## `sdk.audio.get(id)`

Capability: `audio.playback`
Retorno: `Promise<AudioPlaybackDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.audio.list(options = {})`

Capability: `audio.playback`
Retorno: `Promise<AudioPlaybackDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `AudioListOptions` | No | `{}` |

## `sdk.audio.play(input = {})`

Capability: `audio.playback`
Retorno: `Promise<AudioPlaybackDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `AudioPlayInput` | No | `{}` |

## `sdk.audio.stop(id, options = {})`

Capability: `audio.playback`
Retorno: `Promise<AudioPlaybackDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `AudioMutationOptions` | No | `{}` |

## `sdk.audio.update(id, patch = {}, options = {})`

Capability: `audio.playback`
Retorno: `Promise<AudioPlaybackDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `patch` | `AudioPlaybackPatch` | No | `{}` |
| `options` | `AudioMutationOptions` | No | `{}` |

## `sdk.automation.audit()`

Capability: `automation.schedule`
Retorno: `Promise<AutomationAuditDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.automation.cancel(jobId)`

Capability: `automation.schedule`
Retorno: `Promise<AutomationCancelResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `jobId` | `string` | Sí | `None` |

## `sdk.automation.get(jobId)`

Capability: `automation.schedule`
Retorno: `Promise<AutomationJobDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `jobId` | `string` | Sí | `None` |

## `sdk.automation.list()`

Capability: `automation.schedule`
Retorno: `Promise<AutomationJobDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.automation.schedule(actionId, input = {}, options = {})`

Capability: `automation.schedule`
Retorno: `Promise<AutomationJobDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Sí | `None` |
| `input` | `ActionInput` | No | `{}` |
| `options` | `AutomationScheduleOptions` | No | `{}` |

## `sdk.bus.provide(method, handler)`

Capability: `bus.provide`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `method` | `string` | Sí | `None` |
| `handler` | `InteropHandler` | Sí | `None` |

## `sdk.bus.publish(name, payload)`

Capability: `bus.publish`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sí | `None` |
| `payload` | `InteropPayload` | Sí | `None` |

## `sdk.bus.request(method, payload, options)`

Capability: `bus.request`
Retorno: `Promise<BusResponse>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `method` | `string` | Sí | `None` |
| `payload` | `InteropPayload` | Sí | `None` |
| `options` | `BusRequestOptions` | Sí | `None` |

## `sdk.bus.subscribe(name, fn)`

Capability: `bus.subscribe`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sí | `None` |
| `fn` | `InteropSubscriber` | Sí | `None` |

## `sdk.campaign.members()`

Capability: `campaign.members.read`
Retorno: `Promise<CampaignMemberDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.cards.definitions.get(id, version)`

Capability: `cards.read`
Retorno: `Promise<CardDefinitionDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `version` | `number` | Sí | `None` |

## `sdk.cards.definitions.instantiate(id, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardDefinitionInstantiateResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `CardDefinitionInstantiateOptions` | No | `{}` |

## `sdk.cards.definitions.list()`

Capability: `cards.read`
Retorno: `Promise<CardDefinitionDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.cards.discard(cardIds)`

Capability: `cards.manage`
Retorno: `Promise<CardIdsResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardIds` | `string[]` | Sí | `None` |

## `sdk.cards.discardPlacement(placementId)`

Capability: `cards.manage`
Retorno: `Promise<CardPlacementDiscardResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sí | `None` |

## `sdk.cards.draw(deckId, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardDrawResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Sí | `None` |
| `options` | `CardDrawOptions` | No | `{}` |

## `sdk.cards.play(cardId, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardPlayResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardId` | `string` | Sí | `None` |
| `options` | `CardPlayOptions` | No | `{}` |

## `sdk.cards.reset(deckId, options = {})`

Capability: `cards.manage`
Retorno: `Promise<CardDeckMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Sí | `None` |
| `options` | `CardResetOptions` | No | `{}` |

## `sdk.cards.reveal(cardIds)`

Capability: `cards.manage`
Retorno: `Promise<CardIdsResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `cardIds` | `string[]` | Sí | `None` |

## `sdk.cards.shuffle(deckId)`

Capability: `cards.manage`
Retorno: `Promise<CardDeckMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `deckId` | `string` | Sí | `None` |

## `sdk.cards.state()`

Capability: `cards.read`
Retorno: `Promise<CardStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.cards.updatePlacement(placementId, patch = {})`

Capability: `cards.manage`
Retorno: `Promise<CardPlacementResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sí | `None` |
| `patch` | `CardPlacementPatch` | No | `{}` |

## `sdk.chat.get(messageId)`

Capability: `chat.read`
Retorno: `Promise<ChatMessageDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `messageId` | `string` | Sí | `None` |

## `sdk.chat.list(options = {})`

Capability: `chat.read`
Retorno: `Promise<ChatMessageDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `ChatListOptions` | No | `{}` |

## `sdk.chat.send(message)`

Capability: `chat.cards`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `message` | `string | ChatSendMessage` | Sí | `None` |

## `sdk.combat.add(input = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `CombatAddInput` | No | `{}` |

## `sdk.combat.advance(delta = 1)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `delta` | `number` | No | `1` |

## `sdk.combat.advanceRound(delta = 1)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `delta` | `number` | No | `1` |

## `sdk.combat.combatants()`

Capability: `combat.read`
Retorno: `Promise<CombatantDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.combat.current()`

Capability: `combat.read`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.combat.dispatch(name, payload)`

Capability: `combat.runtime`
Retorno: `CombatProtocolPayload | undefined`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sí | `None` |
| `payload` | `CombatProtocolPayload` | Sí | `None` |

## `sdk.combat.end()`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.combat.moveCombatant(combatantId, delta)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sí | `None` |
| `delta` | `number` | Sí | `None` |

## `sdk.combat.register(plugin)`

Capability: `combat.runtime`
Retorno: `boolean`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `plugin` | `CombatPlugin` | Sí | `None` |

## `sdk.combat.registerPanel(panel)`

Capability: `combat.runtime`
Retorno: `boolean`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `panel` | `CombatPanelDefinition` | Sí | `None` |

## `sdk.combat.remove(combatantId)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sí | `None` |

## `sdk.combat.renderSlot(name, payload)`

Capability: `combat.runtime`
Retorno: `Node[]`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sí | `None` |
| `payload` | `CombatProtocolPayload` | Sí | `None` |

## `sdk.combat.rollInitiative(options = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `CombatRollInitiativeOptions` | No | `{}` |

## `sdk.combat.setFlags(combatantId, flags = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sí | `None` |
| `flags` | `CombatFlagsPatch` | No | `{}` |

## `sdk.combat.setInitiative(combatantId, value)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sí | `None` |
| `value` | `number` | Sí | `None` |

## `sdk.combat.setInitiativeOrder(entries)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `entries` | `CombatInitiativeOrderEntry[]` | Sí | `None` |

## `sdk.combat.setTurn(combatantId)`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `combatantId` | `string` | Sí | `None` |

## `sdk.combat.start(input = {})`

Capability: `combat.manage`
Retorno: `Promise<CombatStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `CombatStartInput` | No | `{}` |

## `sdk.commands.register(name, handler)`

Capability: `commands.register`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `name` | `string` | Sí | `None` |
| `handler` | `CommandHandler` | Sí | `None` |

## `sdk.content.can(reference, action = "read")`

Capability: `content.references`
Retorno: `Promise<boolean>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sí | `None` |
| `action` | `string` | No | `"read"` |

## `sdk.content.get(reference)`

Capability: `content.references`
Retorno: `Promise<ContentResolvedValue>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sí | `None` |

## `sdk.content.link(reference, options = {})`

Capability: `content.references`
Retorno: `ContentLinkDTO`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sí | `None` |
| `options` | `ContentLinkOptions` | No | `{}` |

## `sdk.content.open(reference, options = {})`

Capability: `content.references`
Retorno: `Promise<ContentResolutionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sí | `None` |
| `options` | `ContentOpenOptions` | No | `{}` |

## `sdk.content.pack(packId)`

Capability: `content.packs`
Retorno: `Promise<ContentPackDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packId` | `string` | Sí | `None` |

## `sdk.content.packs()`

Capability: `content.packs`
Retorno: `Promise<ContentPackSummaryDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.content.ref(kind, resourceId, options = {})`

Capability: `content.references`
Retorno: `string`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `kind` | `string` | Sí | `None` |
| `resourceId` | `string` | Sí | `None` |
| `options` | `ContentRefOptions` | No | `{}` |

## `sdk.content.resolve(reference)`

Capability: `content.references`
Retorno: `Promise<ContentResolutionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string | ContentReferenceInput` | Sí | `None` |

## `sdk.content.search(query = "", options = {})`

Capability: `content.index`
Retorno: `Promise<ContentSearchPageDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `string` | No | `""` |
| `options` | `ContentSearchOptions` | No | `{}` |

## `sdk.dice.roll({ formula, label = "", actorId = "" } = {})`

Capability: `dice.roll`
Retorno: `Promise<RollResultDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `DiceRollInput` | No | `"", actorId = "" } = {}` |

## `sdk.events.available()`

Capability: `events.subscribe`
Retorno: `SdkEventName[]`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.events.on(event, handler)`

Capability: `events.subscribe`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `event` | `string` | Sí | `None` |
| `handler` | `SdkEventHandler` | Sí | `None` |

## `sdk.events.once(event, handler)`

Capability: `events.subscribe`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `event` | `string` | Sí | `None` |
| `handler` | `SdkEventHandler` | Sí | `None` |

## `sdk.gameplay.flows.advance(id, options = {})`

Capability: `gameplay.flows.manage`
Retorno: `Promise<GameplayFlowDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `GameplayFlowMutationOptions` | No | `{}` |

## `sdk.gameplay.flows.get(id)`

Capability: `gameplay.flows.read`
Retorno: `Promise<GameplayFlowDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.gameplay.flows.list()`

Capability: `gameplay.flows.read`
Retorno: `Promise<GameplayFlowDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.gameplay.flows.register(definition = {})`

Capability: `gameplay.flows.manage`
Retorno: `Promise<GameplayFlowDefinitionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `GameplayFlowDefinitionDTO` | No | `{}` |

## `sdk.gameplay.flows.start(input = {})`

Capability: `gameplay.flows.manage`
Retorno: `Promise<GameplayFlowDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `GameplayFlowStartInput` | No | `{}` |

## `sdk.gameplay.flows.submit(id, value, options = {})`

Capability: `gameplay.flows.participate`
Retorno: `Promise<GameplayFlowDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `value` | `GameplaySubmissionValue` | Sí | `None` |
| `options` | `GameplayFlowMutationOptions` | No | `{}` |

## `sdk.handouts.present(resourceType, resourceId, audience = {})`

Capability: `handouts.present`
Retorno: `Promise<HandoutPresentResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `resourceType` | `string` | Sí | `None` |
| `resourceId` | `string` | Sí | `None` |
| `audience` | `HandoutAudience` | No | `{}` |

## `sdk.i18n.t(key, fallback)`

Capability: `locales`
Retorno: `string`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sí | `None` |
| `fallback` | `string` | Sí | `None` |

## `sdk.input.bindings.get()`

Capability: `input.commands`
Retorno: `Promise<InputBindingDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.input.bindings.set(commandId, binding, options = {})`

Capability: `input.commands`
Retorno: `Promise<InputBindingDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `commandId` | `string` | Sí | `None` |
| `binding` | `string` | Sí | `None` |
| `options` | `InputBindingOptions` | No | `{}` |

## `sdk.input.commands.execute(commandId, inputs = {})`

Capability: `input.commands`
Retorno: `Promise<ActionExecutionResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `commandId` | `string` | Sí | `None` |
| `inputs` | `ActionInput` | No | `{}` |

## `sdk.input.commands.list()`

Capability: `input.commands`
Retorno: `Promise<InputCommandDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.input.commands.register(definition = {}, handler = null)`

Capability: `input.commands`
Retorno: `Promise<Promise<Disposer>>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `InputCommandDefinition` | No | `{}` |
| `handler` | `InputCommandHandler` | No | `null` |

## `sdk.input.gestures.register(definition = {}, handler = null)`

Capability: `input.commands`
Retorno: `Promise<Promise<Disposer>>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `InputGestureDefinition` | No | `{}` |
| `handler` | `InputCommandHandler` | No | `null` |

## `sdk.interactions.cancel(id, options = {})`

Capability: `interactions.request`
Retorno: `Promise<InteractionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.interactions.get(id)`

Capability: `interactions.respond`
Retorno: `Promise<InteractionDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.interactions.list(options = {})`

Capability: `interactions.respond`
Retorno: `Promise<InteractionDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `InteractionListOptions` | No | `{}` |

## `sdk.interactions.request(input = {})`

Capability: `interactions.request`
Retorno: `Promise<InteractionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `InteractionRequestInput` | No | `{}` |

## `sdk.interactions.respond(id, response, options = {})`

Capability: `interactions.respond`
Retorno: `Promise<InteractionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `response` | `InteractionResponseValue` | Sí | `None` |
| `options` | `InteractionMutationOptions` | No | `{}` |

## `sdk.items.create(input = {})`

Capability: `items.write`
Retorno: `Promise<ItemMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ItemCreateInput` | No | `{}` |

## `sdk.items.delete(itemId)`

Capability: `items.write`
Retorno: `Promise<ItemMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sí | `None` |

## `sdk.items.get(itemId)`

Capability: `items.read`
Retorno: `Promise<ItemDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sí | `None` |

## `sdk.items.list(query = {})`

Capability: `items.read`
Retorno: `Promise<ItemDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `query` | `EntityListQuery` | No | `{}` |

## `sdk.items.patchData(itemId, patch = {})`

Capability: `items.data.write`
Retorno: `Promise<ItemDataPatchResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sí | `None` |
| `patch` | `RulesetSheetData` | No | `{}` |

## `sdk.items.update(itemId, patch = {}, options = {})`

Capability: `items.write`
Retorno: `Promise<ItemMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `itemId` | `string` | Sí | `None` |
| `patch` | `ItemUpdateInput` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.journals.create(input = {})`

Capability: `journals.write`
Retorno: `Promise<JournalMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `JournalCreateInput` | No | `{}` |

## `sdk.journals.delete(journalId)`

Capability: `journals.write`
Retorno: `Promise<JournalMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Sí | `None` |

## `sdk.journals.get(journalId)`

Capability: `journals.read`
Retorno: `Promise<JournalDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Sí | `None` |

## `sdk.journals.list(options = {})`

Capability: `journals.read`
Retorno: `Promise<JournalListResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `JournalListOptions` | No | `{}` |

## `sdk.journals.update(journalId, patch = {})`

Capability: `journals.write`
Retorno: `Promise<JournalMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `journalId` | `string` | Sí | `None` |
| `patch` | `JournalUpdatePatch` | No | `{}` |

## `sdk.navigation.scene.getState()`

Capability: `navigation.scene`
Retorno: `Promise<SceneNavigationStateDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.navigation.scene.go(input = {})`

Capability: `navigation.scene`
Retorno: `Promise<SceneNavigationDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `SceneNavigationInput` | No | `{}` |

## `sdk.packages.get(packageId)`

Capability: `packages.inspect`
Retorno: `Promise<PackageDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packageId` | `string` | Sí | `None` |

## `sdk.packages.has(packageId)`

Capability: `packages.inspect`
Retorno: `Promise<boolean>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `packageId` | `string` | Sí | `None` |

## `sdk.pdf.annotations.create(documentId, annotation = {})`

Capability: `pdf.annotations.write`
Retorno: `Promise<PdfAnnotationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |
| `annotation` | `PdfAnnotationInput` | No | `{}` |

## `sdk.pdf.annotations.delete(documentId, annotationId)`

Capability: `pdf.annotations.write`
Retorno: `Promise<PdfAnnotationDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |
| `annotationId` | `string` | Sí | `None` |

## `sdk.pdf.annotations.list(documentId)`

Capability: `pdf.annotations.read`
Retorno: `Promise<PdfAnnotationDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |

## `sdk.pdf.annotations.update(documentId, annotationId, annotation = {})`

Capability: `pdf.annotations.write`
Retorno: `Promise<PdfAnnotationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |
| `annotationId` | `string` | Sí | `None` |
| `annotation` | `PdfAnnotationInput` | No | `{}` |

## `sdk.pdf.get(documentId)`

Capability: `pdf.read`
Retorno: `Promise<PdfDocumentDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |

## `sdk.pdf.metadata(documentId)`

Capability: `pdf.read`
Retorno: `Promise<PdfMetadataDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |

## `sdk.pdf.presentation.current(documentId)`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |

## `sdk.pdf.presentation.end(documentId)`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |

## `sdk.pdf.presentation.start(documentId, input = {})`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |
| `input` | `PdfPresentationStartInput` | No | `{}` |

## `sdk.pdf.presentation.update(documentId, page, options = {})`

Capability: `pdf.presentation`
Retorno: `Promise<PDFPresentationDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |
| `page` | `number` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.pdf.viewer.currentPage(documentId)`

Capability: `pdf.viewer`
Retorno: `number | null`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |

## `sdk.pdf.viewer.goToPage(documentId, page)`

Capability: `pdf.viewer`
Retorno: `Promise<number>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |
| `page` | `number` | Sí | `None` |

## `sdk.pdf.viewer.open(reference, options = {})`

Capability: `pdf.viewer`
Retorno: `Promise<PdfViewerOpenResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string` | Sí | `None` |
| `options` | `PdfViewerOpenOptions` | No | `{}` |

## `sdk.pdf.viewer.search(documentId, query)`

Capability: `pdf.viewer`
Retorno: `Promise<PdfSearchMatch[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `documentId` | `string` | Sí | `None` |
| `query` | `string` | Sí | `None` |

## `sdk.permissions.can(action, resource = {})`

Capability: `permissions.inspect`
Retorno: `Promise<boolean>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `action` | `string` | Sí | `None` |
| `resource` | `PermissionResource` | No | `{}` |

## `sdk.permissions.check(action, resource = {})`

Capability: `permissions.inspect`
Retorno: `Promise<PermissionCheckDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `action` | `string` | Sí | `None` |
| `resource` | `PermissionResource` | No | `{}` |

## `sdk.rolls.intent(payload = {})`

Capability: `rolls.intent`
Retorno: `Promise<RollResultDTO | SheetDataPatchResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `payload` | `RollIntentInput` | No | `{}` |

## `sdk.rules.actions.execute(actionId, input = {}, options = {})`

Capability: `rules.actions`
Retorno: `Promise<ActionExecutionResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Sí | `None` |
| `input` | `ActionInput` | No | `{}` |
| `options` | `ActionExecuteOptions` | No | `{}` |

## `sdk.rules.actions.executeReference(reference, input = {}, options = {})`

Capability: `rules.actions`
Retorno: `Promise<ActionExecutionResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `reference` | `string` | Sí | `None` |
| `input` | `ActionInput` | No | `{}` |
| `options` | `ActionReferenceExecuteOptions` | No | `{}` |

## `sdk.rules.actions.get(actionId)`

Capability: `rules.actions`
Retorno: `Promise<ActionDefinitionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `actionId` | `string` | Sí | `None` |

## `sdk.rules.actions.list()`

Capability: `rules.actions`
Retorno: `Promise<ActionDefinitionDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.rules.actions.resolve({ provider, semantic } = {})`

Capability: `rules.actions`
Retorno: `Promise<ActionDefinitionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `ActionResolveInput` | No | `{}` |

## `sdk.scene.active()`

Capability: `scene.read`
Retorno: `Promise<SceneDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.scene.activeCameraForScene(sceneId)`

Capability: `scene.tools`
Retorno: `CameraDTO | null`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |

## `sdk.scene.activeCanvas()`

Capability: `scene.tools`
Retorno: `HTMLElement | null`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.scene.effects.create(sceneId, kind, values = {})`

Capability: `scene.effects.write`
Retorno: `Promise<ParticleResultDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `kind` | `string` | Sí | `None` |
| `values` | `ParticleValues` | No | `{}` |

## `sdk.scene.effects.delete(effectId, kind)`

Capability: `scene.effects.write`
Retorno: `Promise<ParticleDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `effectId` | `string` | Sí | `None` |
| `kind` | `string` | Sí | `None` |

## `sdk.scene.effects.list(sceneId = context.scene?.id)`

Capability: `scene.effects.read`
Retorno: `Promise<EffectStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.effects.presets()`

Capability: `scene.effects.read`
Retorno: `Promise<ParticlePresetDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.scene.effects.update(effectId, kind, values = {})`

Capability: `scene.effects.write`
Retorno: `Promise<ParticleResultDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `effectId` | `string` | Sí | `None` |
| `kind` | `string` | Sí | `None` |
| `values` | `ParticleValues` | No | `{}` |

## `sdk.scene.fog.disable(sceneId = context.scene?.id)`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.fog.enable(sceneId = context.scene?.id, initial = "hide_all")`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `initial` | `string` | No | `"hide_all"` |

## `sdk.scene.fog.paint(sceneId = context.scene?.id, ops = [], options = {})`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `ops` | `FogOp[]` | No | `[]` |
| `options` | `FogPaintOptions` | No | `{}` |

## `sdk.scene.fog.reset(sceneId = context.scene?.id, to = "hide_all")`

Capability: `scene.fog.write`
Retorno: `Promise<FogMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `to` | `string` | No | `"hide_all"` |

## `sdk.scene.fog.state(sceneId = context.scene?.id)`

Capability: `scene.fog.read`
Retorno: `Promise<FogStateDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.geometry.createLight(sceneId, input = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<LightResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `input` | `LightCreateInput` | No | `{}` |

## `sdk.scene.geometry.createWall(sceneId, input = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<WallResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `input` | `WallCreateInput` | No | `{}` |

## `sdk.scene.geometry.deleteLight(lightId)`

Capability: `scene.geometry.write`
Retorno: `Promise<LightDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `lightId` | `string` | Sí | `None` |

## `sdk.scene.geometry.deleteWall(wallId)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sí | `None` |

## `sdk.scene.geometry.deleteWalls(wallIds)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallIds` | `string[]` | Sí | `None` |

## `sdk.scene.geometry.lights(sceneId = context.scene?.id)`

Capability: `scene.geometry.read`
Retorno: `Promise<LightDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.geometry.moveWallNode(sceneId, from, to)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `from` | `WorldPointDTO` | Sí | `None` |
| `to` | `WorldPointDTO` | Sí | `None` |

## `sdk.scene.geometry.moveWalls(sceneId, wallIds, delta)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `wallIds` | `string[]` | Sí | `None` |
| `delta` | `WorldPointDTO` | Sí | `None` |

## `sdk.scene.geometry.setDoorState(wallId, state)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sí | `None` |
| `state` | `string` | Sí | `None` |

## `sdk.scene.geometry.splitWall(wallId, x, y)`

Capability: `scene.geometry.write`
Retorno: `Promise<WallsResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sí | `None` |
| `x` | `number` | Sí | `None` |
| `y` | `number` | Sí | `None` |

## `sdk.scene.geometry.updateLight(lightId, patch = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<LightResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `lightId` | `string` | Sí | `None` |
| `patch` | `LightUpdatePatch` | No | `{}` |

## `sdk.scene.geometry.updateWall(wallId, patch = {})`

Capability: `scene.geometry.write`
Retorno: `Promise<WallResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `wallId` | `string` | Sí | `None` |
| `patch` | `WallUpdatePatch` | No | `{}` |

## `sdk.scene.geometry.walls(sceneId = context.scene?.id)`

Capability: `scene.geometry.read`
Retorno: `Promise<WallDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.get(sceneId)`

Capability: `scene.read`
Retorno: `Promise<SceneDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |

## `sdk.scene.images.delete(placementId)`

Capability: `scene.images.write`
Retorno: `Promise<SceneImageDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sí | `None` |

## `sdk.scene.images.list(sceneId = context.scene?.id)`

Capability: `scene.images.read`
Retorno: `Promise<SceneImageListResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.images.place(sceneId, assetId, options = {})`

Capability: `scene.images.write`
Retorno: `Promise<SceneImageResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `assetId` | `string` | Sí | `None` |
| `options` | `SceneImagePlaceOptions` | No | `{}` |

## `sdk.scene.images.update(placementId, patch = {}, options = {})`

Capability: `scene.images.write`
Retorno: `Promise<SceneImageResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `placementId` | `string` | Sí | `None` |
| `patch` | `SceneImageUpdatePatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.list()`

Capability: `scene.read`
Retorno: `Promise<SceneDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.scene.measurements.cancel(sceneId, measurementId)`

Capability: `scene.measurements.shared`
Retorno: `Promise<SharedMeasurementDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `measurementId` | `string` | Sí | `None` |

## `sdk.scene.measurements.listShared(sceneId = context.scene?.id)`

Capability: `scene.measurements.shared`
Retorno: `Promise<SharedMeasurementDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.measurements.measure(sceneId, from, to)`

Capability: `scene.tools`
Retorno: `Promise<MeasurementResultDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `from` | `WorldPointDTO` | Sí | `None` |
| `to` | `WorldPointDTO` | Sí | `None` |

## `sdk.scene.measurements.share(sceneId, geometry, options = {})`

Capability: `scene.measurements.shared`
Retorno: `Promise<SharedMeasurementDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `geometry` | `SharedMeasurementGeometry` | Sí | `None` |
| `options` | `SharedMeasurementOptions` | No | `{}` |

## `sdk.scene.objectTypes.register(definition = {})`

Capability: `scene.objectTypes.register`
Retorno: `Promise<Promise<Disposer>>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `SceneObjectTypeDefinition` | No | `{}` |

## `sdk.scene.objects.create(sceneId, input = {})`

Capability: `scene.objects.write`
Retorno: `Promise<SceneObjectDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `input` | `SceneObjectInput` | No | `{}` |

## `sdk.scene.objects.delete(id, options = {})`

Capability: `scene.objects.write`
Retorno: `Promise<SceneObjectDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.objects.get(id)`

Capability: `scene.objects.read`
Retorno: `Promise<SceneObjectDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.scene.objects.hitTest(sceneId, point, options = {})`

Capability: `scene.objects.read`
Retorno: `Promise<SceneObjectDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `point` | `WorldPointDTO` | Sí | `None` |
| `options` | `SceneObjectHitTestOptions` | No | `{}` |

## `sdk.scene.objects.interact(id, interactionId, options = {})`

Capability: `scene.objects.interact`
Retorno: `Promise<SceneObjectInteractionIntentDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `interactionId` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.objects.list(sceneId = context.scene?.id, options = {})`

Capability: `scene.objects.read`
Retorno: `Promise<SceneObjectDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |
| `options` | `SceneObjectListOptions` | No | `{}` |

## `sdk.scene.objects.update(id, patch = {}, options = {})`

Capability: `scene.objects.write`
Retorno: `Promise<SceneObjectDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `patch` | `SceneObjectPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.shaders.apply(sceneId, input = {})`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderInstanceDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `input` | `ShaderApplyInput` | No | `{}` |

## `sdk.scene.shaders.customLibrary.clearPreview()`

Capability: `scene.shaders.customLibrary`
Retorno: `CustomShaderPreviewResult`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.scene.shaders.customLibrary.openEditor(definition = null)`

Capability: `scene.shaders.customLibrary`
Retorno: `Promise<CustomShaderDefinition | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderDefinition | null` | No | `null` |

## `sdk.scene.shaders.customLibrary.preview(definition)`

Capability: `scene.shaders.customLibrary`
Retorno: `CustomShaderPreviewResult`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderDefinition` | Sí | `None` |

## `sdk.scene.shaders.customLibrary.registerProvider(definition = {})`

Capability: `scene.shaders.customLibrary`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderProviderDefinition` | No | `{}` |

## `sdk.scene.shaders.customLibrary.use(definition)`

Capability: `scene.shaders.customLibrary`
Retorno: `Promise<CustomShaderUseResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `CustomShaderDefinition` | Sí | `None` |

## `sdk.scene.shaders.enable(id, enabled, options = {})`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderInstanceDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `enabled` | `boolean` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.shaders.getPreset(presetId)`

Capability: `scene.shaders.read`
Retorno: `Promise<ShaderPresetDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `presetId` | `string` | Sí | `None` |

## `sdk.scene.shaders.list(sceneId = context.scene?.id)`

Capability: `scene.shaders.read`
Retorno: `Promise<ShaderInstanceDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.shaders.presets()`

Capability: `scene.shaders.read`
Retorno: `Promise<ShaderPresetDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.scene.shaders.remove(id)`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderRemovalResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.scene.shaders.update(id, patch = {}, options = {})`

Capability: `scene.shaders.write`
Retorno: `Promise<ShaderInstanceDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `patch` | `ShaderUpdateInput` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.spatialSounds.create(sceneId, input = {})`

Capability: `scene.spatialSounds.write`
Retorno: `Promise<SpatialSoundDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `input` | `SpatialSoundInput` | No | `{}` |

## `sdk.scene.spatialSounds.delete(id, options = {})`

Capability: `scene.spatialSounds.write`
Retorno: `Promise<SpatialSoundDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.spatialSounds.get(id)`

Capability: `scene.spatialSounds.read`
Retorno: `Promise<SpatialSoundDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.scene.spatialSounds.list(sceneId = context.scene?.id)`

Capability: `scene.spatialSounds.read`
Retorno: `Promise<SpatialSoundDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.spatialSounds.update(id, patch = {}, options = {})`

Capability: `scene.spatialSounds.write`
Retorno: `Promise<SpatialSoundDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `patch` | `SpatialSoundPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.templates.create(sceneId, values = {})`

Capability: `scene.templates.write`
Retorno: `Promise<SceneTemplateResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `values` | `SceneTemplateValues` | No | `{}` |

## `sdk.scene.templates.delete(templateId, options = {})`

Capability: `scene.templates.write`
Retorno: `Promise<SceneTemplateDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `templateId` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.templates.get(sceneId, templateId)`

Capability: `scene.templates.read`
Retorno: `Promise<SceneTemplateDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `templateId` | `string` | Sí | `None` |

## `sdk.scene.templates.list(sceneId = context.scene?.id)`

Capability: `scene.templates.read`
Retorno: `Promise<SceneTemplateListResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.templates.update(templateId, patch = {}, options = {})`

Capability: `scene.templates.write`
Retorno: `Promise<SceneTemplateResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `templateId` | `string` | Sí | `None` |
| `patch` | `Partial<SceneTemplateValues>` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.zones.create(sceneId, input = {})`

Capability: `scene.zones.write`
Retorno: `Promise<SceneZoneDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | Sí | `None` |
| `input` | `SceneZoneInput` | No | `{}` |

## `sdk.scene.zones.delete(id, options = {})`

Capability: `scene.zones.write`
Retorno: `Promise<SceneZoneDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.scene.zones.get(id)`

Capability: `scene.zones.read`
Retorno: `Promise<SceneZoneDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.scene.zones.list(sceneId = context.scene?.id)`

Capability: `scene.zones.read`
Retorno: `Promise<SceneZoneDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.scene.zones.members(id)`

Capability: `scene.zones.read`
Retorno: `Promise<string[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.scene.zones.update(id, patch = {}, options = {})`

Capability: `scene.zones.write`
Retorno: `Promise<SceneZoneDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `patch` | `SceneZonePatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.settings.all()`

Capability: `settings`
Retorno: `SettingValues`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.settings.definitions()`

Capability: `settings`
Retorno: `SettingDefinitionDTO[]`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.settings.get(key, fallback = undefined)`

Capability: `settings`
Retorno: `SettingValue | undefined`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sí | `None` |
| `fallback` | `string` | No | `undefined` |

## `sdk.settings.onChange(key, handler)`

Capability: `settings`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sí | `None` |
| `handler` | `SettingChangeHandler` | Sí | `None` |

## `sdk.settings.scope(key)`

Capability: `settings`
Retorno: `SettingScope | null`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sí | `None` |

## `sdk.settings.set(key, value, options = {})`

Capability: `settings`
Retorno: `Promise<SettingSetResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `key` | `string` | Sí | `None` |
| `value` | `number` | Sí | `None` |
| `options` | `SettingSetOptions` | No | `{}` |

## `sdk.sheets.helpers()`

Capability: `sheets.runtime`
Retorno: `SheetHelpers`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.sheets.register(plugin)`

Capability: `sheets.runtime`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `plugin` | `SheetPlugin` | Sí | `None` |

## `sdk.sheets.registerController(sheetType, controller)`

Capability: `sheets.controller`
Retorno: `boolean`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sheetType` | `string` | Sí | `None` |
| `controller` | `SheetController` | Sí | `None` |

## `sdk.sounds.create(input = {})`

Capability: `sounds.write`
Retorno: `Promise<SoundDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `SoundCreateInput` | No | `{}` |

## `sdk.sounds.delete(id, options = {})`

Capability: `sounds.write`
Retorno: `Promise<SoundDeleteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.sounds.get(id)`

Capability: `sounds.read`
Retorno: `Promise<SoundDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.sounds.list(options = {})`

Capability: `sounds.read`
Retorno: `Promise<SoundDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `SoundListOptions` | No | `{}` |

## `sdk.sounds.update(id, patch = {}, options = {})`

Capability: `sounds.write`
Retorno: `Promise<SoundDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `patch` | `SoundPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.storage.sqlite.execute(scope, name, params = {})`

Capability: `storage.sqlite`
Retorno: `Promise<StorageExecuteResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Sí | `None` |
| `name` | `string` | Sí | `None` |
| `params` | `StorageParams` | No | `{}` |

## `sdk.storage.sqlite.query(scope, name, params = {})`

Capability: `storage.sqlite`
Retorno: `Promise<StorageQueryResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Sí | `None` |
| `name` | `string` | Sí | `None` |
| `params` | `StorageParams` | No | `{}` |

## `sdk.storage.sqlite.status(scope)`

Capability: `storage.sqlite`
Retorno: `Promise<StorageStatusDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `scope` | `string` | Sí | `None` |

## `sdk.timelines.cancel(id, options = {})`

Capability: `timelines.control`
Retorno: `Promise<TimelineDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.timelines.get(id)`

Capability: `timelines.read`
Retorno: `Promise<TimelineDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.timelines.list()`

Capability: `timelines.read`
Retorno: `Promise<TimelineDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.timelines.register(definition = {})`

Capability: `timelines.start`
Retorno: `Promise<TimelineDefinitionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `TimelineDefinitionDTO` | No | `{}` |

## `sdk.timelines.start(input = {})`

Capability: `timelines.start`
Retorno: `Promise<TimelineDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `TimelineStartInput` | No | `{}` |

## `sdk.tokens.centerOn(tokenId)`

Capability: `tokens.extends`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sí | `None` |

## `sdk.tokens.create(input = {})`

Capability: `tokens.manage`
Retorno: `Promise<TokenMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `TokenCreateInput` | No | `{}` |

## `sdk.tokens.delete(tokenId, options = {})`

Capability: `tokens.manage`
Retorno: `Promise<TokenMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sí | `None` |
| `options` | `TokenOptions` | No | `{}` |

## `sdk.tokens.get(tokenId, options = {})`

Capability: `tokens.read`
Retorno: `Promise<TokenDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sí | `None` |
| `options` | `TokenReadOptions` | No | `{}` |

## `sdk.tokens.list(options = {})`

Capability: `tokens.read`
Retorno: `Promise<TokenDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `TokenReadOptions` | No | `{}` |

## `sdk.tokens.move(tokenId, position = {}, options = {})`

Capability: `tokens.move`
Retorno: `Promise<TokenMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sí | `None` |
| `position` | `TokenMoveInput` | No | `{}` |
| `options` | `TokenOptions` | No | `{}` |

## `sdk.tokens.targets.clear(sceneId = context.scene?.id)`

Capability: `tokens.targets`
Retorno: `Promise<string[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.tokens.targets.list(sceneId = context.scene?.id)`

Capability: `tokens.targets`
Retorno: `Promise<string[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.tokens.targets.set(ids, sceneId = context.scene?.id)`

Capability: `tokens.targets`
Retorno: `Promise<string[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `ids` | `string[]` | Sí | `None` |
| `sceneId` | `string` | No | `context.scene?.id` |

## `sdk.tokens.transfer(tokenId, destination = {}, options = {})`

Capability: `tokens.transfer`
Retorno: `Promise<TokenTransferResultDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sí | `None` |
| `destination` | `TokenTransferDestination` | No | `{}` |
| `options` | `TokenTransferOptions` | No | `{}` |

## `sdk.tokens.transferMany(transfers = [], options = {})`

Capability: `tokens.transfer`
Retorno: `Promise<TokenTransferResultDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `transfers` | `TokenTransferSpec[]` | No | `[]` |
| `options` | `TokenTransferManyOptions` | No | `{}` |

## `sdk.tokens.update(tokenId, patch = {}, options = {})`

Capability: `tokens.manage`
Retorno: `Promise<TokenMutationResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `tokenId` | `string` | Sí | `None` |
| `patch` | `TokenOverrides` | No | `{}` |
| `options` | `TokenOptions` | No | `{}` |

## `sdk.tools.activeTool()`

Capability: `scene.tools`
Retorno: `string`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.tools.register(definition = {})`

Capability: `scene.tools`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `ToolDefinition` | No | `{}` |

## `sdk.ui.applications.close(applicationId)`

Capability: `ui.applications`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Sí | `None` |

## `sdk.ui.applications.register(applicationId, definition)`

Capability: `ui.applications`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Sí | `None` |
| `definition` | `ApplicationDefinition` | Sí | `None` |

## `sdk.ui.applications.render(applicationId, host, appContext = {}, options = {})`

Capability: `ui.applications`
Retorno: `Promise<ApplicationInstance | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `applicationId` | `string` | Sí | `None` |
| `host` | `HTMLElement` | Sí | `None` |
| `appContext` | `ApplicationContext` | No | `{}` |
| `options` | `ApplicationRenderOptions` | No | `{}` |

## `sdk.ui.closeModal(modalOrId)`

Capability: `assets.ui`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `modalOrId` | `string` | Sí | `None` |

## `sdk.ui.dragDrop.drop(input = {})`

Capability: `ui.dragDrop`
Retorno: `Promise<SemanticDropResultDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `SemanticDropInput` | No | `{}` |

## `sdk.ui.dragDrop.registerSource(definition = {})`

Capability: `ui.dragDrop`
Retorno: `Promise<Promise<Disposer>>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `DragSourceDefinition` | No | `{}` |

## `sdk.ui.dragDrop.registerTarget(definition = {})`

Capability: `ui.dragDrop`
Retorno: `Promise<Promise<Disposer>>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `DropTargetDefinition` | No | `{}` |

## `sdk.ui.dragDrop.sources()`

Capability: `ui.dragDrop`
Retorno: `Promise<SemanticRegistrationDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.ui.dragDrop.targets()`

Capability: `ui.dragDrop`
Retorno: `Promise<SemanticRegistrationDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.ui.openModal(modalId)`

Capability: `assets.ui`
Retorno: `void`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `modalId` | `string` | Sí | `None` |

## `sdk.ui.presentations.close(id, options = {})`

Capability: `ui.presentations`
Retorno: `Promise<PresentationCloseResult>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.ui.presentations.get(id)`

Capability: `ui.presentations`
Retorno: `Promise<PresentationDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.ui.presentations.list(options = {})`

Capability: `ui.presentations`
Retorno: `Promise<PresentationDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `options` | `PresentationListOptions` | No | `{}` |

## `sdk.ui.presentations.show(input = {})`

Capability: `ui.presentations`
Retorno: `Promise<PresentationDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `PresentationInput` | No | `{}` |

## `sdk.ui.presentations.update(id, patch = {}, options = {})`

Capability: `ui.presentations`
Retorno: `Promise<PresentationDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `patch` | `PresentationPatch` | No | `{}` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.ui.presentations.wait(id, options = {})`

Capability: `ui.presentations`
Retorno: `Promise<PresentationDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `PresentationWaitOptions` | No | `{}` |

## `sdk.ui.slots.available()`

Capability: `ui.slots`
Retorno: `string[]`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.ui.slots.register(slotId, render)`

Capability: `ui.slots`
Retorno: `Disposer`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `slotId` | `string` | Sí | `None` |
| `render` | `SlotRenderCallback` | Sí | `None` |

## `sdk.ui.toast(message, options)`

Capability: `assets.ui`
Retorno: `ToastHandle | undefined`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `message` | `string` | Sí | `None` |
| `options` | `ToastOptions` | Sí | `None` |

## `sdk.workflows.cancel(id, options = {})`

Capability: `workflows.control`
Retorno: `Promise<WorkflowDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |
| `options` | `ExpectedVersionOptions` | No | `{}` |

## `sdk.workflows.get(id)`

Capability: `workflows.read`
Retorno: `Promise<WorkflowDTO | null>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `id` | `string` | Sí | `None` |

## `sdk.workflows.list()`

Capability: `workflows.read`
Retorno: `Promise<WorkflowDTO[]>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

## `sdk.workflows.register(definition = {})`

Capability: `workflows.start`
Retorno: `Promise<WorkflowDefinitionDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `definition` | `WorkflowDefinitionDTO` | No | `{}` |

## `sdk.workflows.start(input = {})`

Capability: `workflows.start`
Retorno: `Promise<WorkflowDTO>`
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.

Parámetros:

| Parameter | Type | Required | Default |
|---|---|:---:|---|
| `input` | `WorkflowStartInput` | No | `{}` |
