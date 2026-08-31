# Core concepts

Read these pages to build a reliable mental model before designing a public
module contract.

1. [Architecture](architecture.md) — what belongs to the kernel and what belongs to modules.
2. [Module kinds](module-kinds.md) — the five roles and their cardinality.
3. [Dependencies and capabilities](dependencies-and-capabilities.md) — concrete use versus replaceable contracts.
4. [Lifecycle](../surfaces/lifecycle.md) — planning, activation, rollback, and shutdown.
5. [Manifest](../surfaces/manifest.md) — the static validation boundary.
6. [Composition](../surfaces/routes.md) — routes, middleware, and slots.

The most important distinction is between **mechanism** and **product policy**.
The kernel enforces graph safety, public surfaces, lifecycle, and the single
server invariant. Modules decide how a VTT stores data, renders a table, applies
rules, and exposes product features.
