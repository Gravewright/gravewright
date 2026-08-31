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
- [Dependencies](dependencies.md) — names, SemVer, ordering, and installation.
- [Recipes](recipes.md) — reproducible compositions and capability-provider choices.

## Composition

- [Routes](routes.md) — publish final request handlers.
- [Middleware](middleware.md) — publish chained request handlers.
- [Slots](slots.md) — contribute values to named extension points.
- [Room slots](room-slots.md) — guaranteed DOM regions and isolated visual contributions.
- [Server contract](server.md) — the required transport contract.
- [`read`, `write`, `stat`](read-write-stat.md) — common POSIX-inspired module commands.

## Runtime

- [Diagnostics](diagnostic.md) — opt-in semantic audit events.
- [Lifecycle and state](lifecycle.md) — load, activate, compose, disable, and dispose.
