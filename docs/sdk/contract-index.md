# SDK 1 structural contract index

Canonical identifiers are not translated. Structure comes from `gravewright-sdk-1.json`.

## Capabilities

### `actors.data.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.actors.patchData`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `actors.items.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.actors.items.slots`, `sdk.actors.items.listCopies`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `actors.items.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.actors.items.insertCopy`, `sdk.actors.items.removeCopy`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `actors.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.actors.get`, `sdk.actors.list`, `sdk.actors.data`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `actors.register`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `actors.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.actors.create`, `sdk.actors.update`, `sdk.actors.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.audio`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.icons`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.images`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.import`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.assets.ingest`, `sdk.assets.cancelImport`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.library`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.assets.list`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.maps`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.pack`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.scripts`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.styles`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.ui`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.ui.toast`, `sdk.ui.openModal`, `sdk.ui.closeModal`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `assets.video`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `automation.schedule`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.automation.schedule`, `sdk.automation.get`, `sdk.automation.list`, `sdk.automation.cancel`, `sdk.automation.audit`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `bus.provide`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.bus.provide`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `bus.publish`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.bus.publish`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `bus.request`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.bus.request`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `bus.subscribe`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.bus.subscribe`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `cards.manage`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.cards.definitions.instantiate`, `sdk.cards.shuffle`, `sdk.cards.reset`, `sdk.cards.draw`, `sdk.cards.reveal`, `sdk.cards.discard`, `sdk.cards.play`, `sdk.cards.updatePlacement`, `sdk.cards.discardPlacement`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `cards.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.cards.state`, `sdk.cards.definitions.list`, `sdk.cards.definitions.get`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `chat.cards`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.chat.send`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `chat.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.chat.list`, `sdk.chat.get`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `combat.config`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `combat.manage`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.combat.start`, `sdk.combat.end`, `sdk.combat.advance`, `sdk.combat.advanceRound`, `sdk.combat.setTurn`, `sdk.combat.add`, `sdk.combat.remove`, `sdk.combat.setFlags`, `sdk.combat.rollInitiative`, `sdk.combat.setInitiative`, `sdk.combat.moveCombatant`, `sdk.combat.setInitiativeOrder`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `combat.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.combat.current`, `sdk.combat.combatants`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `combat.runtime`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.combat.register`, `sdk.combat.registerPanel`, `sdk.combat.dispatch`, `sdk.combat.renderSlot`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `commands.register`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.commands.register`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `content.index`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.content.search`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `content.packs`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.content.packs`, `sdk.content.pack`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `content.references`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.content.ref`, `sdk.content.resolve`, `sdk.content.get`, `sdk.content.can`, `sdk.content.open`, `sdk.content.link`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `dice.roll`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.dice.roll`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `events.subscribe`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.events.on`, `sdk.events.once`, `sdk.events.available`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `handouts.present`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.handouts.present`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `items.data.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.items.patchData`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `items.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.items.get`, `sdk.items.list`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `items.register`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `items.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.items.create`, `sdk.items.update`, `sdk.items.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `journals.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.journals.get`, `sdk.journals.list`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `journals.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.journals.create`, `sdk.journals.update`, `sdk.journals.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `locales`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.i18n.t`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `packages.inspect`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.packages.get`, `sdk.packages.has`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `pdf.annotations.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.pdf.annotations.list`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `pdf.annotations.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.pdf.annotations.create`, `sdk.pdf.annotations.update`, `sdk.pdf.annotations.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `pdf.presentation`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.pdf.presentation.start`, `sdk.pdf.presentation.current`, `sdk.pdf.presentation.update`, `sdk.pdf.presentation.end`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `pdf.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.pdf.get`, `sdk.pdf.metadata`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `pdf.viewer`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.pdf.viewer.open`, `sdk.pdf.viewer.goToPage`, `sdk.pdf.viewer.search`, `sdk.pdf.viewer.currentPage`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `permissions.inspect`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.permissions.can`, `sdk.permissions.check`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `rolls.intent`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.rolls.intent`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `rules.actions`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.rules.actions.list`, `sdk.rules.actions.get`, `sdk.rules.actions.resolve`, `sdk.rules.actions.execute`, `sdk.rules.actions.executeReference`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `rules.declarative`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `rules.extends`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.effects.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.effects.list`, `sdk.scene.effects.presets`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.effects.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.effects.create`, `sdk.scene.effects.update`, `sdk.scene.effects.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.fog.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.fog.state`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.fog.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.fog.enable`, `sdk.scene.fog.disable`, `sdk.scene.fog.reset`, `sdk.scene.fog.paint`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.geometry.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.geometry.walls`, `sdk.scene.geometry.lights`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.geometry.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.geometry.createWall`, `sdk.scene.geometry.updateWall`, `sdk.scene.geometry.deleteWall`, `sdk.scene.geometry.splitWall`, `sdk.scene.geometry.moveWallNode`, `sdk.scene.geometry.moveWalls`, `sdk.scene.geometry.deleteWalls`, `sdk.scene.geometry.createLight`, `sdk.scene.geometry.updateLight`, `sdk.scene.geometry.deleteLight`, `sdk.scene.geometry.setDoorState`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.images.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.images.list`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.images.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.images.place`, `sdk.scene.images.update`, `sdk.scene.images.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.measurements.shared`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.measurements.share`, `sdk.scene.measurements.listShared`, `sdk.scene.measurements.cancel`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.overlays`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.get`, `sdk.scene.list`, `sdk.scene.active`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.shaders.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.shaders.presets`, `sdk.scene.shaders.getPreset`, `sdk.scene.shaders.list`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.shaders.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.shaders.apply`, `sdk.scene.shaders.update`, `sdk.scene.shaders.enable`, `sdk.scene.shaders.remove`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.templates.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.templates.list`, `sdk.scene.templates.get`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.templates.write`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.templates.create`, `sdk.scene.templates.update`, `sdk.scene.templates.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `scene.tools`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.scene.activeCanvas`, `sdk.scene.activeCameraForScene`, `sdk.tools.activeTool`, `sdk.tools.register`, `sdk.scene.measurements.measure`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `settings`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.settings.definitions`, `sdk.settings.all`, `sdk.settings.get`, `sdk.settings.set`, `sdk.settings.scope`, `sdk.settings.onChange`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `sheets.components`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `sheets.controller`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.sheets.registerController`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `sheets.declarative`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `sheets.html`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `sheets.richText`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `sheets.runtime`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.sheets.helpers`, `sdk.sheets.register`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `storage.sqlite`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.storage.sqlite.query`, `sdk.storage.sqlite.execute`, `sdk.storage.sqlite.status`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `tokens.extends`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.tokens.centerOn`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `tokens.manage`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.tokens.create`, `sdk.tokens.update`, `sdk.tokens.delete`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `tokens.mappings`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: —
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `tokens.move`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.tokens.move`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `tokens.read`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.tokens.get`, `sdk.tokens.list`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `tokens.targets`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.tokens.targets.list`, `sdk.tokens.targets.set`, `sdk.tokens.targets.clear`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `ui.applications`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.ui.applications.register`, `sdk.ui.applications.render`, `sdk.ui.applications.close`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

### `ui.slots`

Status: `stable`
Package kinds: `ruleset`, `addon`, `library`, `content`, `theme`, `assets`
Methods: `sdk.ui.slots.available`, `sdk.ui.slots.register`
Events: [Events](#events)
Errors: `CAPABILITY_REQUIRED`, `PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_FAILED`, `STALE_VERSION`, `UNKNOWN_ACTION`
Authority: Declared capability plus current-user resource authority; capabilities never elevate permissions.
Visibility: Current-user projection; hidden resources are indistinguishable from missing resources.
Concurrency: Server-authoritative; `expectedVersion` is atomic compare-and-swap when declared.
Durability: Only declared server resources are durable; local registrations end on package unload.
Lifecycle: The package must be installed, enabled, and active; registrations return a disposer.
Security boundary: No raw filesystem, database, transport, renderer, ACL internals, or permission override is exposed.

## Events

### `actor.created`

Delivery: Authorized, schema-versioned event; re-read current state.

### `actor.data.updated`

Delivery: Authorized, schema-versioned event; re-read current state.

### `actor.deleted`

Delivery: Authorized, schema-versioned event; re-read current state.

### `actor.updated`

Delivery: Authorized, schema-versioned event; re-read current state.

### `automation.job.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `cards.state.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `chat.created`

Delivery: Authorized, schema-versioned event; re-read current state.

### `combat.ended`

Delivery: Authorized, schema-versioned event; re-read current state.

### `combat.started`

Delivery: Authorized, schema-versioned event; re-read current state.

### `combat.turn.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `combat.updated`

Delivery: Authorized, schema-versioned event; re-read current state.

### `game.ready`

Delivery: Authorized, schema-versioned event; re-read current state.

### `item.created`

Delivery: Authorized, schema-versioned event; re-read current state.

### `item.deleted`

Delivery: Authorized, schema-versioned event; re-read current state.

### `item.updated`

Delivery: Authorized, schema-versioned event; re-read current state.

### `journal.created`

Delivery: Authorized, schema-versioned event; re-read current state.

### `journal.deleted`

Delivery: Authorized, schema-versioned event; re-read current state.

### `journal.updated`

Delivery: Authorized, schema-versioned event; re-read current state.

### `pdf.annotations.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `pdf.presentation.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `rules.action.completed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.effects.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.fog.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.geometry.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.images.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.measurements.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.shaders.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `scene.templates.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `setting.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `token.created`

Delivery: Authorized, schema-versioned event; re-read current state.

### `token.deleted`

Delivery: Authorized, schema-versioned event; re-read current state.

### `token.moved`

Delivery: Authorized, schema-versioned event; re-read current state.

### `token.targets.changed`

Delivery: Authorized, schema-versioned event; re-read current state.

### `token.updated`

Delivery: Authorized, schema-versioned event; re-read current state.

## Errors

- `CAPABILITY_REQUIRED`
- `PERMISSION_DENIED`
- `NOT_FOUND`
- `VALIDATION_FAILED`
- `STALE_VERSION`
- `UNKNOWN_ACTION`
