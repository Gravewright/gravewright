# Public API status audit

This inventory reflects the current contract and automated integration
coverage. “Stable candidate” is not a freeze declaration.

## `@gravewright/sdk`

| Contract | Status | Evidence or risk |
| --- | --- | --- |
| `ModuleKind`, `ModuleProvider` | stable candidate | Five roles covered the reference composition. |
| `ModuleManifest` and manifest fields | stable candidate | Static graph, routes, middleware, slots, dependencies and release metadata exercised. |
| `ModuleDefinition`, `DefinedModule`, `defineModule`, `InferModuleAPI` | stable candidate | All reference modules use the authoring and inferred API path. |
| `ModuleRegistry`, `CapabilityRegistry`, `Context`, `ModuleRef`, `Dispose` | stable candidate | Concrete and replaceable dependencies plus lifecycle exercised. |
| `DynamicContext` | stable candidate | It now has the same `use`, `capability`, lifecycle and diagnostic surface as `Context`, with dynamic names. |
| `BaseRequest`, `BaseResponse`, `RouteHandler`, `MiddlewareHandler` | stable candidate | Deliberately small neutral composition surface. Specialized HTTP features belong to a concrete server module API. |
| `SlotContribution`, `composeRoomSlots`, `ROOM_PROTOCOL`, room slots | stable candidate | Narrow visual composition contract; framework, rendering and client/server transport remain room/module details. |

## `@gravewright/kernel`

| Contract | Status |
| --- | --- |
| `Kernel`, `KernelOptions`, `LoadOptions` | stable candidate |
| `load`, `plan`, `initialize`, `activate`, `disable`, `use`, `shutdown` | stable candidate |
| `ActivationPlan` | stable candidate; exported from the package root and exercised by planner tests |
| `createActivationPlan`, manifest validator, lifecycle helpers, runtime record types | internal; file layout does not make them public package exports |

## Manifest schema v1

The fields `name`, `kind`, `provider`, `version`, `entry`, `types`,
`dependencies`, `requires`, `provides`, `routes`, `middleware`, `slots`,
`exposes`, `exports`, and release metadata are stable candidates. Runtime
validation remains authoritative; JSON Schema supports editors and tooling.

## Surface-minimization audit

| Surface | Core purpose | Module-owned detail excluded | Freeze decision |
| --- | --- | --- | --- |
| Manifest constants and types | Declare identity, graph, permissions and composition | Module behavior and libraries | Keep |
| `defineModule` and inference helpers | Author and type the declared factory contract | Factory internals | Keep |
| `Context.use`, `Context.capability`, `ModuleRef.get` | Resolve and authorize inter-module communication | How either module implements the value | Keep; central language |
| `onDispose` | Bind acquired resources to lifecycle rollback/shutdown | Resource implementation | Keep |
| diagnostics | Emit the existing opt-in semantic audit contract | Logging backend and application telemetry | Keep; narrow host integration |
| route and middleware neutral types | Compose portable basic handlers | Full HTTP protocol and server framework | Keep small |
| room protocol, slot contracts and composition helper | Compose independently authored visual contributions | UI framework, rendering, state and transport | Keep narrow |
| `DynamicContext` | Explicit untyped fallback for dynamic hosts | Discovery and module implementation | Keep; now coherent with `Context` |
| Kernel facade and activation plan | Validate and execute the composition | Host product policy and module internals | Keep |

Every current core surface supports declaration, composition, authorization,
lifecycle, or an already-established narrow host integration. HTTP and DOM
helpers are interoperability contracts rather than attempts to model their
entire technology domains. No transport, RPC, event bus, frontend framework,
persistence or authentication surface is required. Nothing should be added for
theoretical completeness.

The implementation-specific `http` and `ws` exports of `gravewright-server`
demonstrate the escape hatch: a module may explicitly depend on that provider
when it needs behavior outside the neutral route contract. Portability is an
available design choice, not a universal requirement.
