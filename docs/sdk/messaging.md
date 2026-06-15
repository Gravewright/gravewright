# Package-to-Package Communication

Packages share a single in-page event bus exposed through the scoped SDK. This is
the **official, supported** way for one package to react to or drive another at
runtime. There is no server round-trip — the bus is browser-local to the open
table.

## The bus

```js
window.GravewrightSDK.register({
  id: "my-package",
  setup(sdk) {
    // Emit (requires the hooks.client capability):
    sdk.hooks.emit("package:my-package:roll-finished", { version: 1, total: 17 });

    // Listen (requires the hooks.client capability):
    sdk.hooks.on("package:dice-so-nice-lite:settled", (payload) => { /* ... */ });
  },
});
```

`sdk.hooks` (`on` / `once` / `emit`) and `sdk.events` (`on` / `once`) read and
write the same bus, so a listener registered with `sdk.events.on` receives events
sent with `sdk.hooks.emit`. Both are gated by the `hooks.client` capability —
declare it in your manifest to use them.

## Naming convention

Name every cross-package event after its **owner**:

```
package:<package-id>:<event-name>
```

* `<package-id>` is the emitting package's manifest id.
* `<event-name>` is a kebab-case verb phrase in the past tense for facts
  (`roll-finished`, `token-dropped`) or imperative for requests
  (`open-tray`).

Namespacing by owner keeps a package's events discoverable, avoids collisions,
and makes it obvious in listener code which package you are coupling to. Engine
lifecycle events that are not package-owned (e.g. `game:ready`) keep their
existing `area:name` form and are not part of this convention.

## Versioned payloads

Every payload is a plain object whose first field is an integer `version`:

```js
sdk.hooks.emit("package:my-package:roll-finished", {
  version: 1,
  rollId: "abc",
  total: 17,
});
```

Consumers must check `version` and ignore (or adapt) payloads they do not
understand:

```js
sdk.hooks.on("package:my-package:roll-finished", (payload) => {
  if (!payload || payload.version !== 1) return;
  // ...safe to read v1 fields...
});
```

Bump `version` only on a breaking change to the payload shape; add optional
fields without a bump. This lets an emitter and an out-of-date listener coexist
during upgrades.

## Dependency vs optional dependency

Use the manifest to declare the relationship behind the messaging:

* **Hard `dependencies`** — your package cannot function without the other one.
  The other package must be installed, enabled, compatible, and (for campaign
  activation) active, or your package is blocked. Use this when you *call into*
  or *require events from* another package to do your core job. `grave doctor`
  and the Packages UI surface unmet dependencies (`dependency_missing`,
  `dependency_disabled`, `dependency_inactive`, …).

* **Optional integration (no dependency)** — your package works alone but does
  *more* when a peer is present. Do **not** declare a dependency. Instead, just
  `sdk.hooks.on("package:<peer>:<event>", …)`: if the peer is inactive the event
  simply never fires, and your package degrades gracefully. Guard any direct peer
  access and treat its absence as normal.

Rule of thumb: declare a dependency only when *absence is an error*. If absence
is merely *less functionality*, listen optionally and stay decoupled.
