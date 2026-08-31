# Troubleshooting

Start with `grave doctor`; use `grave doctor --json` when another tool needs to
consume the result.

## “Exactly one active server is required”

Inspect `gravewright.modules.json`. Activate one `server` module and disable all
other servers. Installed modules are disabled by default.

## `ctx.use("name")` is rejected

The caller must declare the exact module in `dependencies`, the dependency must
be active, and its version must satisfy the declared SemVer range. A transitive
dependency does not count.

## `ctx.use("name")` is typed as `unknown`

Check that the producer's `types.ts` augments `ModuleRegistry` with the quoted
module name, then run:

```bash
npm run types:sync
npm run typecheck
```

## A room contribution does not appear

Verify that the room renders exactly one element for each canonical `gw-*`
class, that its manifest exposes those slots, and that the contribution is in
`exports.get` and mapped under `slots`. DOM validation happens after `mount()`.

## The project imports but fails during activation

Move network connections, listeners, timers, and database opens from import time
into `create()`. Register cleanup immediately with `ctx.onDispose()`. Planning
cannot roll back side effects performed during module evaluation.

## Marketplace integrity failure

Do not retry with verification disabled. Confirm that the release ZIP is
immutable and recompute `download_sha256`. The remote manifest name and version
must match the archive manifest.
