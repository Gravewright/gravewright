# Release readiness

## Scope decision

Gravewright owns manifests, discovery/loading, dependency validation,
capability resolution, lifecycle, explicit exports, composition planning and
module access through `use`, `capability` and `get`.

Modules own frontend frameworks, UI, DOM, rendering, state management, network
protocols, transport, client/server communication, persistence implementation,
external integrations and implementation-specific APIs.

## Re-evaluated findings

| Finding | Classification | Decision |
| --- | --- | --- |
| No standard server-to-browser transport | non-goal | A module owns communication between its own client and server parts. `use`/`capability`/`get` remain the inter-module language. |
| Neutral HTTP response does not model every HTTP feature | non-goal | The portable route surface is intentionally small. Modules may explicitly consume a concrete server's exports for specialized behavior. |
| `DynamicContext` omitted diagnostics | contract inconsistency | Fixed and covered by type compatibility checks. |
| JSON Schema does not encode every runtime invariant | intended division | Schema serves tooling and structure; runtime validation owns semantic and graph invariants. |
| Capability example encoded `/v1` in its name | documentation / ergonomics | Use stable `gravewright.storage` with a separate SemVer protocol value. |
| `ActivationPlan` was returned publicly but absent from the kernel root export | packaging bug | Fixed during the audit. |

## Kernel dependency footprint

`@gravewright/kernel` has one third-party runtime dependency: `semver`. It
validates module versions, dependency ranges and capability compatibility, which
are direct kernel responsibilities. Node has no equivalent native SemVer range
implementation; replacing it locally would increase correctness risk and code
without meaningfully improving the footprint.

The other runtime dependency is the first-party `@gravewright/sdk`, which owns
the shared contracts the kernel enforces. No framework, transport, renderer,
storage or application dependency is present in the kernel package.

## Current recommendation

**Ready for 0.9 pre-freeze.** The central contracts have composition and
capability-resolution evidence; lifecycle, repeated activation, marketplace security
and packaged consumers are covered. The `0.9.x` line remains a dogfooding and
evidence-gathering period where rare breaking corrections are still possible.
The effective freeze begins at `1.0.0-rc.1`, after broader ecosystem and upgrade
evidence.
