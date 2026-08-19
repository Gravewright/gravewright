# Índice estructural del contrato SDK 1

Los identifiers canónicos no se traducen. La estructura procede de `gravewright-sdk-1.json`.

## Capabilities

### `actors.data.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.patchData`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `actors.items.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.items.slots`, `sdk.actors.items.listCopies`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `actors.items.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.items.insertCopy`, `sdk.actors.items.removeCopy`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `actors.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.get`, `sdk.actors.list`, `sdk.actors.data`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `actors.register`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `actors.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.actors.create`, `sdk.actors.update`, `sdk.actors.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.audio`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.icons`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.images`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.import`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.assets.ingest`, `sdk.assets.cancelImport`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.library`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.assets.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.maps`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.pack`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.scripts`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.styles`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.ui`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.toast`, `sdk.ui.openModal`, `sdk.ui.closeModal`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `assets.video`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `audio.playback`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.audio.play`, `sdk.audio.get`, `sdk.audio.list`, `sdk.audio.update`, `sdk.audio.stop`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `automation.schedule`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.automation.schedule`, `sdk.automation.get`, `sdk.automation.list`, `sdk.automation.cancel`, `sdk.automation.audit`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `bus.provide`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.provide`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `bus.publish`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.publish`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `bus.request`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.request`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `bus.subscribe`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.bus.subscribe`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `campaign.members.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.campaign.members`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `cards.manage`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.cards.definitions.instantiate`, `sdk.cards.shuffle`, `sdk.cards.reset`, `sdk.cards.draw`, `sdk.cards.reveal`, `sdk.cards.discard`, `sdk.cards.play`, `sdk.cards.updatePlacement`, `sdk.cards.discardPlacement`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `cards.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.cards.state`, `sdk.cards.definitions.list`, `sdk.cards.definitions.get`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `chat.cards`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.chat.send`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `chat.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.chat.list`, `sdk.chat.get`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `combat.config`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `combat.manage`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.combat.start`, `sdk.combat.end`, `sdk.combat.advance`, `sdk.combat.advanceRound`, `sdk.combat.setTurn`, `sdk.combat.add`, `sdk.combat.remove`, `sdk.combat.setFlags`, `sdk.combat.rollInitiative`, `sdk.combat.setInitiative`, `sdk.combat.moveCombatant`, `sdk.combat.setInitiativeOrder`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `combat.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.combat.current`, `sdk.combat.combatants`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `combat.runtime`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.combat.register`, `sdk.combat.registerPanel`, `sdk.combat.dispatch`, `sdk.combat.renderSlot`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `commands.register`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.commands.register`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `content.index`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.content.search`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `content.packs`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.content.packs`, `sdk.content.pack`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `content.references`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.content.ref`, `sdk.content.resolve`, `sdk.content.get`, `sdk.content.can`, `sdk.content.open`, `sdk.content.link`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `dice.roll`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.dice.roll`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `events.subscribe`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.events.on`, `sdk.events.once`, `sdk.events.available`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `gameplay.flows.manage`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.gameplay.flows.register`, `sdk.gameplay.flows.start`, `sdk.gameplay.flows.advance`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `gameplay.flows.participate`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.gameplay.flows.submit`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `gameplay.flows.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.gameplay.flows.get`, `sdk.gameplay.flows.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `handouts.present`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.handouts.present`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `input.commands`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.input.commands.register`, `sdk.input.commands.list`, `sdk.input.commands.execute`, `sdk.input.bindings.get`, `sdk.input.bindings.set`, `sdk.input.gestures.register`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `interactions.request`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.interactions.request`, `sdk.interactions.cancel`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `interactions.respond`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.interactions.get`, `sdk.interactions.list`, `sdk.interactions.respond`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `items.data.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.items.patchData`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `items.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.items.get`, `sdk.items.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `items.register`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `items.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.items.create`, `sdk.items.update`, `sdk.items.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `journals.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.journals.get`, `sdk.journals.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `journals.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.journals.create`, `sdk.journals.update`, `sdk.journals.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `locales`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.i18n.t`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `navigation.scene`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.navigation.scene.go`, `sdk.navigation.scene.getState`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `packages.inspect`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.packages.get`, `sdk.packages.has`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `pdf.annotations.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.annotations.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `pdf.annotations.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.annotations.create`, `sdk.pdf.annotations.update`, `sdk.pdf.annotations.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `pdf.presentation`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.presentation.start`, `sdk.pdf.presentation.current`, `sdk.pdf.presentation.update`, `sdk.pdf.presentation.end`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `pdf.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.get`, `sdk.pdf.metadata`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `pdf.viewer`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.pdf.viewer.open`, `sdk.pdf.viewer.goToPage`, `sdk.pdf.viewer.search`, `sdk.pdf.viewer.currentPage`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `permissions.inspect`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.permissions.can`, `sdk.permissions.check`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `rolls.intent`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.rolls.intent`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `rules.actions`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.rules.actions.list`, `sdk.rules.actions.get`, `sdk.rules.actions.resolve`, `sdk.rules.actions.execute`, `sdk.rules.actions.executeReference`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `rules.declarative`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `rules.extends`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.effects.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.effects.list`, `sdk.scene.effects.presets`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.effects.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.effects.create`, `sdk.scene.effects.update`, `sdk.scene.effects.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.fog.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.fog.state`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.fog.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.fog.enable`, `sdk.scene.fog.disable`, `sdk.scene.fog.reset`, `sdk.scene.fog.paint`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.geometry.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.geometry.walls`, `sdk.scene.geometry.lights`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.geometry.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.geometry.createWall`, `sdk.scene.geometry.updateWall`, `sdk.scene.geometry.deleteWall`, `sdk.scene.geometry.splitWall`, `sdk.scene.geometry.moveWallNode`, `sdk.scene.geometry.moveWalls`, `sdk.scene.geometry.deleteWalls`, `sdk.scene.geometry.createLight`, `sdk.scene.geometry.updateLight`, `sdk.scene.geometry.deleteLight`, `sdk.scene.geometry.setDoorState`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.images.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.images.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.images.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.images.place`, `sdk.scene.images.update`, `sdk.scene.images.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.measurements.shared`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.measurements.share`, `sdk.scene.measurements.listShared`, `sdk.scene.measurements.cancel`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.objectTypes.register`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.objectTypes.register`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.objects.interact`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.objects.interact`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.objects.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.objects.list`, `sdk.scene.objects.get`, `sdk.scene.objects.hitTest`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.objects.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.objects.create`, `sdk.scene.objects.update`, `sdk.scene.objects.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.overlays`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.get`, `sdk.scene.list`, `sdk.scene.active`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.shaders.customLibrary`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.shaders.customLibrary.registerProvider`, `sdk.scene.shaders.customLibrary.openEditor`, `sdk.scene.shaders.customLibrary.preview`, `sdk.scene.shaders.customLibrary.clearPreview`, `sdk.scene.shaders.customLibrary.use`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.shaders.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.shaders.presets`, `sdk.scene.shaders.getPreset`, `sdk.scene.shaders.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.shaders.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.shaders.apply`, `sdk.scene.shaders.update`, `sdk.scene.shaders.enable`, `sdk.scene.shaders.remove`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.spatialSounds.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.spatialSounds.list`, `sdk.scene.spatialSounds.get`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.spatialSounds.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.spatialSounds.create`, `sdk.scene.spatialSounds.update`, `sdk.scene.spatialSounds.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.templates.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.templates.list`, `sdk.scene.templates.get`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.templates.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.templates.create`, `sdk.scene.templates.update`, `sdk.scene.templates.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.tools`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.activeCanvas`, `sdk.scene.activeCameraForScene`, `sdk.tools.activeTool`, `sdk.tools.register`, `sdk.scene.measurements.measure`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.zones.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.zones.list`, `sdk.scene.zones.get`, `sdk.scene.zones.members`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `scene.zones.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.scene.zones.create`, `sdk.scene.zones.update`, `sdk.scene.zones.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `settings`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.settings.definitions`, `sdk.settings.all`, `sdk.settings.get`, `sdk.settings.set`, `sdk.settings.scope`, `sdk.settings.onChange`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sheets.components`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sheets.controller`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.sheets.registerController`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sheets.declarative`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sheets.html`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sheets.richText`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sheets.runtime`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.sheets.helpers`, `sdk.sheets.register`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sounds.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.sounds.list`, `sdk.sounds.get`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `sounds.write`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.sounds.create`, `sdk.sounds.update`, `sdk.sounds.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `storage.sqlite`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.storage.sqlite.query`, `sdk.storage.sqlite.execute`, `sdk.storage.sqlite.status`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `timelines.control`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.timelines.cancel`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `timelines.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.timelines.get`, `sdk.timelines.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `timelines.start`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.timelines.register`, `sdk.timelines.start`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `tokens.extends`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.centerOn`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `tokens.manage`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.create`, `sdk.tokens.update`, `sdk.tokens.delete`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `tokens.mappings`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: —
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `tokens.move`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.move`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `tokens.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.get`, `sdk.tokens.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `tokens.targets`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.targets.list`, `sdk.tokens.targets.set`, `sdk.tokens.targets.clear`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `tokens.transfer`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.tokens.transfer`, `sdk.tokens.transferMany`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `ui.applications`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.applications.register`, `sdk.ui.applications.render`, `sdk.ui.applications.close`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `ui.dragDrop`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.dragDrop.registerSource`, `sdk.ui.dragDrop.registerTarget`, `sdk.ui.dragDrop.sources`, `sdk.ui.dragDrop.targets`, `sdk.ui.dragDrop.drop`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `ui.presentations`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.presentations.show`, `sdk.ui.presentations.get`, `sdk.ui.presentations.list`, `sdk.ui.presentations.wait`, `sdk.ui.presentations.update`, `sdk.ui.presentations.close`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `ui.slots`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.ui.slots.available`, `sdk.ui.slots.register`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `workflows.control`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.workflows.cancel`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `workflows.read`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.workflows.get`, `sdk.workflows.list`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

### `workflows.start`

Status: `stable`
Tipos de package: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Métodos: `sdk.workflows.register`, `sdk.workflows.start`
Eventos: [Eventos](#eventos)
Errores: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `IDEMPOTENCY_CONFLICT`, `ALREADY_SUBMITTED`, `NOT_ACTIVE_PARTICIPANT`, `LIMIT_EXCEEDED`, `UNKNOWN_ACTION`, `ALREADY_RESPONDED`, `INTERACTION_EXPIRED`, `INTERACTION_CANCELLED`, `UNKNOWN_OBJECT_TYPE`, `PROVIDER_UNAVAILABLE`, `INVALID_GEOMETRY`, `INVALID_OBJECT_DATA`, `INVALID_PRESENTATION`, `INVALID_ANCHOR`, `ANCHOR_NOT_VISIBLE`, `NOT_AUTHORIZED`, `PACKAGE_INACTIVE`, `UNKNOWN_INTERACTION`, `UNSUPPORTED_PRESENTATION_MODE`, `RESOURCE_IN_USE`
Autoridad: Capability declarada más autoridad del usuario actual sobre el recurso; las capabilities nunca elevan permisos.
Visibilidad: Proyección del usuario actual; los recursos ocultos no se distinguen de los inexistentes.
Concurrencia: Autoritativo en el servidor; `expectedVersion` es compare-and-swap atómico cuando se declara.
Durabilidad: Solo los recursos de servidor declarados son durables; los registros locales terminan al descargar el package.
Ciclo de vida: El package debe estar instalado, habilitado y activo; los registros devuelven un disposer.
Límite de seguridad: No expone filesystem, database, transport, renderer, internals de ACL ni override de permisos.

## Eventos

### `actor.created`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `actor.data.updated`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `actor.deleted`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `actor.updated`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `audio.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `automation.job.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `cards.state.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `chat.created`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `combat.ended`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `combat.started`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `combat.turn.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `combat.updated`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `game.ready`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `gameplay.flow.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `input.binding.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `interaction.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `item.created`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `item.deleted`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `item.updated`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `journal.created`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `journal.deleted`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `journal.updated`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `navigation.scene.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `pdf.annotations.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `pdf.presentation.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `rules.action.completed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.effects.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.fog.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.geometry.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.images.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.measurements.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.object.interacted`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.object.selected`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.objects.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.shaders.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.templates.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `scene.zones.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `setting.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `timeline.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `token.created`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `token.deleted`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `token.moved`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `token.targets.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `token.updated`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `tokens.transferred`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `ui.presentation.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `workflow.changed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `zone.crossed`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `zone.entered`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

### `zone.left`

Entrega: Evento autorizado y versionado por schema; vuelva a leer el estado actual.

## Errores

- `CAPABILITY_REQUIRED`
- `PERMISSION_DENIED`
- `NOT_FOUND`
- `VALIDATION_FAILED`
- `STALE_VERSION`
- `IDEMPOTENCY_CONFLICT`
- `ALREADY_SUBMITTED`
- `NOT_ACTIVE_PARTICIPANT`
- `LIMIT_EXCEEDED`
- `UNKNOWN_ACTION`
- `ALREADY_RESPONDED`
- `INTERACTION_EXPIRED`
- `INTERACTION_CANCELLED`
- `UNKNOWN_OBJECT_TYPE`
- `PROVIDER_UNAVAILABLE`
- `INVALID_GEOMETRY`
- `INVALID_OBJECT_DATA`
- `INVALID_PRESENTATION`
- `INVALID_ANCHOR`
- `ANCHOR_NOT_VISIBLE`
- `NOT_AUTHORIZED`
- `PACKAGE_INACTIVE`
- `UNKNOWN_INTERACTION`
- `UNSUPPORTED_PRESENTATION_MODE`
- `RESOURCE_IN_USE`
