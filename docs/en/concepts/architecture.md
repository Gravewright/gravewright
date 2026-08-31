# Architecture

## Runtime overview

```text
manifest discovery
       │
       ▼
static validation ──► activation plan ──► module factories
                                              │
                                              ▼
                                  middleware · routes · slots
                                              │
                                              ▼
                                      active server starts
```

Planning occurs before any factory runs. It validates dependencies, SemVer,
capability providers, routes, slots, room protocol, and singleton constraints.
This makes configuration errors fail before modules acquire resources.

## Ownership

The host discovers modules and requests state. The kernel validates and
coordinates. The SDK defines author-facing types and helpers. Each module owns
its implementation and npm dependencies.

```text
host             which modules are installed and active
kernel           whether the composition is valid and how it is activated
SDK              stable author contracts
module           domain behavior, external packages, resources, and cleanup
```

### Module ownership principle

Gravewright coordinates modules and their declared contracts. A module owns
its implementation details: frontend framework, DOM and rendering, client
state, HTTP/WebSocket/WebRTC protocols, persistence libraries, external
integrations, caching, and communication between its own client and server
parts. React, Vue, Svelte, Web Components, Canvas, Three.js and Pixi are all
valid module choices and remain invisible to the kernel.

Modules communicate through declared dependencies and `ctx.use()`, declared
capabilities and `ctx.capability()`, and values obtained with `ModuleRef.get()`.
This is the Gravewright contract regardless of where the host executes a
module. It is not a server-only API and there is no parallel browser API.

### Surface minimization principle

A new kernel or SDK surface is justified only when modules cannot reasonably
solve the problem through existing contracts. Missing standardization is often
a deliberate boundary, not a missing feature. Explicit dependence on a
specific implementation is allowed when portability is not a module's goal.

New public surfaces require evidence: a real problem shared by multiple
modules, no reasonable module-level encapsulation, and demonstrated friction
with the existing contracts. The legacy architecture grew to dozens of
capabilities and extension points; the current runtime deliberately resists
that pattern. Gravewright prefers a missing abstraction to a speculative one.

### Kernel longevity

Kernel simplicity is a longevity strategy. Its responsibilities and APIs stay
small, predictable and insulated from volatile ecosystems. Dependencies are
kept few and must directly support kernel work. React can change, Express can
be replaced, and storage or rendering can evolve without changing the kernel,
because those technologies live in modules.

## Non-goals

Gravewright is not a frontend or full-stack framework, universal transport,
RPC or messaging framework, ORM, renderer, state manager, authentication
system, or persistence API. It does not standardize how a module implements
UI, transport, storage, rendering, or its client/server protocol.

## Security model

The manifest prevents undeclared cross-module access and lets the host reject an
invalid graph before import. `ctx.use("name")` is scoped to the caller's declared
`dependencies`; exported names are checked again at runtime.

This is capability control inside the module graph, not process isolation. Do
not install untrusted modules into a privileged host. Release hashes protect
integrity in transit; they do not make code trustworthy.

## Failure model

Factories register acquired resources immediately with `ctx.onDispose()`.
Failed activation rolls those resources back in reverse order. Normal shutdown
stops the server first, then removes composition and disposes modules in reverse
topological order.

Disabling is committed once teardown begins. Every disposer is attempted in
reverse order and cleanup errors are reported, but a partially torn-down module
is never restored as active and its disposers are not run again at shutdown.

## Visual composition boundary

The shared SDK includes DOM types and the `composeRoomSlots` helper so room and
addon authors share one visual contract. Importing the SDK in Node does not read
`document` or execute DOM work; DOM access occurs only when a browser-side room
explicitly calls the helper. Slots standardize a narrow composition point; they
do not make the kernel responsible for a room's framework, DOM architecture,
rendering strategy, or transport.
