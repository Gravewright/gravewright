# Public surfaces

Each page documents one explicit boundary between a module, the SDK, and the kernel.

## Authoring

- [`defineModule`](define-module.md) — declare a typed module definition.
- [`create`](create.md) — construct the runtime instance.
- [Manifest](manifest.md) — static validation boundary.
- [Exports](exports.md) — declare the public capability list.
- [ModuleRegistry](module-registry.md) — register module APIs for TypeScript.

## Module communication

- [`use`](use.md) — obtain a revocable reference to a declared dependency.
- [`get`](get.md) — read a permitted value or command.
- [`set`](set.md) — deprecated generic cross-module mutation.
- [`prop`](prop.md) — explicitly shared readable/writable property.
- [Dependencies](dependencies.md) — names, SemVer, ordering, and installation.

## Composition

- [Routes](routes.md) — publish final request handlers.
- [Middleware](middleware.md) — publish chained request handlers.
- [Slots](slots.md) — contribute values to named extension points.
- [Server contract](server.md) — the only required module kind.

## Runtime

- [Diagnostics](diagnostic.md) — opt-in semantic audit events.
- [Lifecycle and state](lifecycle.md) — load, activate, compose, disable, and dispose.
