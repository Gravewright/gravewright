# Gravewright documentation

This guide documents the repository at version `0.1.0`. Public APIs are pre-1.0; compatibility is governed by the [SDK governance policy](../SDK-GOVERNANCE.md).

## 1. Overview

Gravewright is an extensible virtual tabletop built on a small modular kernel. Gravewright is the product, the kernel is its internal modular infrastructure, the SDK is the public authoring surface, and modules are extensions of the VTT. The host discovers local modules, validates their manifests, plans a dependency-safe composition, creates them, starts the three structural roles, and disposes their resources. Ordinary extensions use kind `module` and may be enabled or disabled while the kernel runs.

The system intentionally owns no web framework, database, or browser renderer. Implementations provide those choices through narrow SDK contracts.

## 2. Architecture

```text
CLI / host
   │ discovers modules/* and reads gravewright.modules.json
   ▼
@gravewright/kernel ── validates manifests and dependency graph
   │
   ├── exactly one active server
   ├── exactly one active backend
   ├── exactly one active frontend
   └── zero or more active extension modules
          │
          └── declared dependency → public exports only
```

The root host (`src/start-gravewright.ts`) creates a `Kernel`, loads every directory containing `manifest.json`, applies persisted state, and initializes the plan. `@gravewright/sdk` contains contracts only. `@gravewright/kernel` contains loading and orchestration. `@gravewright/ui` provides optional Vue components and CSS.

Trust boundaries are explicit but modules are not sandboxed: imported module code has the host process's permissions.

## 3. Manifest

Each module has `modules/<directory>/manifest.json`:

```json
{
  "name": "dice-tools",
  "kind": "module",
  "provider": "community",
  "version": "1.2.0",
  "entry": "./index.ts",
  "types": "./types.ts",
  "dependencies": { "rules": "^1.0.0" },
  "tooling": { "read": true, "stat": true },
  "exports": { "get": ["roll"] }
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `name` | yes | Non-empty, installation-unique module identifier |
| `kind` | yes | `server`, `frontend`, `backend`, or `module` |
| `provider` | yes | `core`, `community`, `official`, `licensed`, or `partner` |
| `version` | yes | Valid semantic version |
| `entry` | yes | Factory entry contained inside the module directory |
| `types` | no | Type augmentation file contained inside the module directory |
| `dependencies` | no | Concrete module names mapped to SemVer ranges |
| `tooling` | no | Opt-in `read`, `write`, or `stat` administrative operations; only `true` is accepted |
| `exports.get` | no | Unique public property names (the `exports` object itself is required) |
| `manifest_url` | no | String identifying a remote manifest |
| `download_url` | no | Stable string URL for the latest release archive |
| `download_sha256` | no | 64-character hexadecimal SHA-256 of that archive |

Unknown fields, `exports.set`, and `exports.prop` are rejected. Paths are resolved and checked again after symlink resolution. The machine-readable schema is [manifest-v1.json](../schema/manifest-v1.json).

`gravewright.modules.json` is separate installation state:

```json
{ "my-server": "active", "dice-tools": "disabled" }
```

Missing entries default to `disabled`. State writes use a temporary file and atomic rename.

## 4. Lifecycle

Initialization is serialized as follows:

1. Validate the active composition and topologically order dependencies before consumers.
2. Import and create every active module in plan order.
3. Start backend, then frontend, then server.
4. If startup fails, stop only structural components whose start was attempted/completed, then dispose all registered resources in reverse module and reverse registration order.

Shutdown stops server, frontend, and backend in that order, then disposes all module resources in reverse activation order. `shutdown()` is safe to call again after a completed shutdown. `ctx.onDispose(fn)` is the required ownership mechanism for routes, listeners, timers, and connections.

Only kind `module` supports runtime `activate()` and `disable()`. Structural replacements require restart. Activation rolls back state and resources on failure. A module cannot be disabled while an active module depends on it. Runtime mutations are queued.

## 5. Dependencies

Dependencies are concrete module identities and SemVer ranges, not capabilities or kinds:

```json
"dependencies": { "character-store": ">=1.2 <2" }
```

The target must exist, be active, satisfy the range, and not create a cycle. Self-dependencies fail. Dependencies are not transitive permissions: if `a` uses `c`, `a` must declare `c` even when `a → b → c`. Inside the factory, `ctx.use("character-store")` works only for names directly declared by that manifest.

Package dependencies are distinct. The SDK module should normally be a peer dependency; runtime libraries belong in the module's own `package.json`.

## 6. Exports

`exports.get` is the entire public runtime surface. Every declared name must be an own property of the factory result. Consumers obtain a stable reference and read allowed properties with `ref.get(name)`:

```ts
const rules = ctx.use("rules");
const calculate = rules.get("calculate");
```

An undeclared export fails even if the property exists on the object. There is no public setter, property injection, kind lookup, or capability lookup. Keep exports small and behavior-oriented.

## 7. Server contract

A `server` must declare and implement `start`, `stop`, `http`, `route`, and `middleware`. `route(mount, handler)` and `middleware(mount, handler)` return disposers. Requests and responses use transport-neutral `BaseRequest` and `BaseResponse` shapes. `http` is deliberately `unknown`; consumers must establish their own typed integration before using it.

Optional `realtime`, when listed in `exports.get`, must contain `toRoom`, `toGM`, and `toWhisper`, each accepting a `{ type, payload }` message. The SDK does not prescribe WebSocket, SSE, or message persistence.

## 8. Backend contract

A `backend` declares and implements asynchronous-or-synchronous `start()` and `stop()`. It owns the server-side application and persistence lifecycle but has no mandatory database API. Domain storage should be exposed as explicit exports and consumed through declared module dependencies. Startup must not assume the server has started: backend starts first.

## 9. Frontend contract

The Node-side `frontend` module declares and implements `start()` and `stop()` to make its browser bundle available. The kernel never invokes DOM methods.

Browser bundles may implement `ClientFrontend`: `mount(root)`, `unmount()`, and `slot(name, module, contribution)`. A contribution has an `id`, optional order, and `mount(container)`, which may return a disposer. Slot names are protocol identifiers selected by the frontend. `@gravewright/ui` is optional and exports Vue primitives plus styles via `@gravewright/ui/styles`.

## 10. Extension modules

Kind `module` represents ordinary Gravewright extensions, including product and game features. It has no required exports and may be hot-activated or disabled. A factory receives only `use`, `onDispose`, and `diagnostic`. Factories may be async and must return an object. Keep setup inside `create`, expose only supported operations, and register cleanup immediately after acquiring a resource.

Administrative `tooling` is separate from product exports. If declared, the returned object must implement the operation. The host invokes it through `Kernel.tooling`; `grave help` maps to `read`, `grave test` to `write`, and `grave doctor` may call `stat`.

## 11. CLI

From this repository use `npm run grave -- <command>`; an installed binary uses `grave`.

| Command | Purpose |
| --- | --- |
| `grave run [--diagnostic] [--diagnostic-file path]` | Start the current project and optionally write a sanitized action journal |
| `grave new <kind> [name]` | Scaffold a module; supports `--minimal`, `--example-complete`, tooling flags, `--realtime`, metadata, tests, README, Git, and `--dry-run` |
| `grave doctor [--json]` | Check inventory, state, manifests, dependencies, structural roles, and declared health tooling |
| `grave test [module]` | Run `write` tooling for one or all eligible active modules |
| `grave help [command-or-topic]` | Show CLI help, or invoke module `read` tooling for a supplied topic |
| `grave module build [path] [--check]` | Generate or verify manifest and types from `defineModule()` |

Exit codes are `0` for success, `1` for an operation/validation failure, and `2` for usage or project-discovery errors.

## 12. Creating a module

```bash
npm run grave -- new module dice-tools --example-complete
```

Then edit `modules/dice-tools/index.ts`, add public names to `exports.get`, declare all concrete dependencies, and run:

```bash
npm run grave -- module build modules/dice-tools
npm run grave -- module build modules/dice-tools --check
npm run grave -- doctor
```

`module build` imports the TypeScript entry, reads the metadata captured by `defineModule`, and generates `manifest.json` and `types.ts`. The generated type file augments `ModuleRegistry`, making dependency names and their public exports type-safe. Activate the reviewed module explicitly in `gravewright.modules.json`.

## 13. Minimal examples

Extension module:

```ts
import { defineModule } from "@gravewright/sdk";

export default defineModule({
  name: "dice-tools",
  kind: "module",
  provider: "community",
  version: "1.0.0",
  exports: { get: ["roll"] },
  create(ctx) {
    const timer = setInterval(() => {}, 60_000);
    ctx.onDispose(() => clearInterval(timer));
    return { roll: (sides: number) => 1 + Math.floor(Math.random() * sides) };
  },
});
```

Route-owning module (its manifest must declare the concrete server dependency):

```ts
create(ctx) {
  const route = ctx.use("my-server").get("route") as RouteRegistrar;
  ctx.onDispose(route("/health", (_request, response) => {
    response.status(200).json({ ok: true });
  }));
  return {};
}
```

## 14. Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `Expected exactly one active ...` | Install and activate exactly one module of each structural kind; disable duplicates |
| `requires missing/disabled dependency` | Install and activate the exact named module, or update the consumer manifest |
| `requires ... but ... is loaded` | Choose a compatible version or change the range after compatibility testing |
| `Circular dependency detected` | Move shared behavior into a lower-level module and remove one graph edge |
| `cannot use undeclared dependency` | Add the concrete name and SemVer range to `dependencies` |
| `cannot access export` | Add the property to the provider's `exports.get` only if it is intended to be public |
| `manifest/types is stale` | Run `grave module build <path>` and commit generated files |
| `entry/types outside module directory` | Use a contained relative path; symlink escapes are intentionally rejected |
| Project starts with no table | Run `grave doctor`; a clean source checkout has no structural implementations configured |

Use `grave doctor --json` for automation. Diagnostic recording is opt-in; review its output before sharing it.

## 15. SDK reference

### Values and helpers

- `MODULE_KINDS`, `ModuleKind`; `MODULE_PROVIDERS`, `ModuleProvider`; `ModuleState`.
- `STRUCTURAL_EXPORTS`: minimum names for each structural kind.
- `defineModule(definition)`: typed factory helper with frozen `.definition` metadata.
- `InferModuleAPI<typeof module>`: derives the public `get` surface.

### Authoring types

- `ModuleDefinition<T>`, `DefinedModule`, `ModuleManifest`, `ModuleTooling`.
- `ModuleRegistry`: augment this empty interface to type concrete dependencies.
- `Context<R>`: typed `use`, `onDispose`, and `diagnostic`.
- `DynamicContext`: deliberate untyped fallback for hosts that cannot know modules at compile time.
- `ModuleAPI`, `ModuleRef<T>`, `Dispose`.

### Contracts

- `ServerContract`, `BackendContract`, `FrontendContract`, `ContractDefinition<K>`.
- `BaseRequest`, `BaseResponse`, `RouteHandler`, `RouteRegistrar`.
- `MiddlewareNext`, `MiddlewareHandler`, `MiddlewareRegistrar`.
- `ServerMessage`, `ServerRealtime`.
- `ClientFrontend`, `FrontendSlotContribution`, `FrontendSlotRegistrar`.
- `DiagnosticAction`, `DiagnosticActionStatus`, `DiagnosticReporter`.

### Kernel API

`@gravewright/kernel` exports `Kernel`, `KernelOptions`, `LoadOptions`, and `ActivationPlan`. Principal methods are `load`, `plan`, `initialize`, `use`, `tooling`, `activate`, `disable`, and `shutdown`. `load` is available only before initialization; `activate`/`disable` only after it and only for extension modules.
