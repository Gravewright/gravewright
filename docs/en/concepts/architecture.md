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
