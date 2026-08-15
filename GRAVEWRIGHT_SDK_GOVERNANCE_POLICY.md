# Gravewright SDK Governance Policy

> [Versão em Português do Brasil](docs/pt-br/politica-governanca-sdk.md)

**Status:** Proposed project policy  
**Applies to:** Gravewright SDK, package manifests, capability registry, public package runtime, inter-package contracts, package-facing CLI behavior, and all official Gravewright packages  
**Normative language:** The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative.

---

## 1. Purpose

The Gravewright SDK exists to let an extension ecosystem grow without making the Gravewright core permanently dependent on its current implementation.

The SDK is therefore not merely a collection of convenient APIs. It is a **long-lived compatibility boundary** between:

- the Gravewright core;
- rulesets;
- addons;
- libraries;
- content packages;
- themes;
- asset packages;
- and future classes of extensions.

The primary governance objective is:

> **Preserve the freedom to replace Gravewright's internal implementation without unnecessarily breaking packages that depend only on intentional public contracts.**

This policy governs how that boundary is designed, extended, stabilized, deprecated, secured, documented, tested, and eventually versioned.

The project MUST prefer long-term contract quality over short-term convenience.

---

## 2. Core governance principles

### 2.1 Stabilize intent, not implementation

> **Do not stabilize accidental behaviour. Stabilize only intentional contract.**

A behavior becomes part of the public SDK only when the project deliberately defines it as such.

The following MUST NOT become public contract merely because packages can currently observe or access them:

- renderer internals;
- private browser globals;
- DOM structure;
- CSS class names;
- private route names;
- internal database layout;
- WebSocket message ordering;
- private stores;
- internal object identity;
- framework-specific classes;
- internal filesystem layout not explicitly documented as public;
- incidental error text;
- incidental timing behavior.

If third-party packages begin depending on an internal behavior, that dependency does **not** automatically promote the behavior to public API.

The project MUST decide whether to:

1. create a semantic public contract for the legitimate use case;
2. provide a migration path;
3. or explicitly reject the use case.

---

### 2.2 The SDK is a semantic boundary

Public SDK contracts SHOULD describe **what an extension wants to accomplish**, not **how Gravewright currently accomplishes it**.

Preferred:

```js
await sdk.combat.setInitiative(combatantId, value);
await sdk.tokens.move(tokenId, { x, y });
await sdk.cards.draw({ deckId, count: 1 });
```

Discouraged:

```js
fetch("/game/combat/initiative/set", ...);
window.GravewrightCombatActions.refreshRoom(...);
document.querySelector("[data-combat-panel]");
```

A public API MUST NOT expose implementation details unless those details are themselves intentionally part of the durable model.

---

### 2.3 Declarative-first

Whenever a package can express durable intent as data, the SDK SHOULD prefer a declarative contract over imperative runtime code.

Examples include:

- actor types;
- item types;
- sheets;
- rules;
- conditions;
- token mappings;
- settings;
- locales;
- content packs;
- declared inter-package contracts.

Imperative APIs SHOULD exist only where runtime behavior is genuinely necessary.

The purpose of declarative-first design is not to eliminate code. It is to reduce the amount of ecosystem code coupled to implementation details.

---

### 2.4 Least privilege

Every package MUST request the smallest capability set that satisfies its documented behavior.

Every public gated operation MUST map to a canonical capability.

Capabilities SHOULD represent a coherent authority boundary. They MUST NOT be made broader merely to reduce registry size.

The SDK SHOULD prefer:

```text
cards.read
cards.play
cards.manage
```

over:

```text
cards.any
```

when the narrower authorities are operationally meaningful.

---

### 2.5 No universal escape capability

Gravewright MUST NOT introduce a capability equivalent to:

```text
any
all
unrestricted
raw
superuser
unsafe
```

that grants general access to the Gravewright core.

This prohibition is architectural, not cosmetic.

A universal capability would:

- defeat least privilege;
- make capability review meaningless;
- hide gaps in the SDK;
- encourage package dependence on internals;
- destroy useful auditability;
- turn accidental implementation into ecosystem contract;
- make future core replacement substantially harder;
- and increase the impact of malicious or compromised packages.

If a legitimate package requires behavior not expressible through the SDK, that is evidence of either:

1. a missing semantic capability;
2. an inappropriate package design;
3. or a use case Gravewright intentionally does not support.

It is **not** justification for `any`.

---

### 2.6 Server authority

The browser runtime MUST NOT be treated as authoritative for:

- persistence;
- permissions;
- campaign state;
- combat state;
- resource ownership;
- package storage authorization;
- or security decisions.

Public browser APIs that mutate state MUST ultimately pass through server-side validation and authorization.

Capabilities express **package intent and available SDK surface**. They do not override user permissions.

---

### 2.7 Core replaceability is a design requirement

When evaluating a public contract, maintainers SHOULD ask:

> "Could Gravewright replace the renderer, UI framework, persistence layer, server implementation, or transport protocol while preserving this contract?"

If the answer is "no" solely because the proposed API exposes an implementation detail, the proposal SHOULD be redesigned.

The SDK MUST not require that the future Gravewright core continue to use:

- PixiJS;
- WebGL;
- WebGPU;
- Python;
- a specific database engine;
- a specific frontend framework;
- a particular route structure;
- or a particular internal document model,

unless one of those technologies is deliberately promoted to part of the public platform contract.

---

## 3. Scope of the public contract

The Gravewright public extension contract consists only of surfaces explicitly identified as public in project documentation.

For SDK 1 this includes, as applicable:

- `manifest.json` schema and documented fields;
- `sdkVersion`;
- canonical stable capabilities;
- documented scoped `sdk.*` methods;
- documented lifecycle entry points;
- documented sheet/controller contracts;
- documented declarative schemas;
- managed package storage;
- documented `sdk.bus.*` interop;
- documented package events;
- documented CLI behavior designated as stable for package authors;
- stable structured error codes;
- and stable package data formats explicitly designated as public.

Anything else is private unless explicitly documented otherwise.

### 3.1 Public API is opt-in

A symbol, endpoint, class, property, global, route, event, database table, or DOM element is **not public merely because it is accessible**.

Accessibility is not a stability guarantee.

---

## 4. SDK versioning policy

### 4.1 SDK version is independent of Gravewright application version

Packages target an SDK contract:

```json
{
  "sdkVersion": "1"
}
```

They MUST NOT be required to couple themselves to Gravewright application internals simply because the application version changes.

Gravewright MAY ship major internal rewrites while continuing to implement SDK 1.

---

### 4.2 Compatibility guarantee for SDK 1

A package that:

- is valid for `sdkVersion: "1"`;
- uses only stable documented SDK 1 contracts;
- does not depend on private internals;
- does not use forbidden capabilities;
- and respects documented input/output constraints,

SHOULD continue to install, enable, and run across Gravewright releases that claim support for SDK 1.

Bugs do not become permanent compatibility guarantees merely because a package depends on them.

Security vulnerabilities do not become permanent compatibility guarantees.

Undefined behavior does not become permanent compatibility guarantee.

---

### 4.3 Breaking changes

A breaking change to a stable SDK 1 contract MUST require at least one of:

1. a new SDK major version;
2. a formally documented compatibility adapter;
3. or an exceptional security process described in this policy.

Application major versions alone MUST NOT be used as justification to silently break a stable SDK contract.

---

## 5. Capability registry governance

The canonical capability registry is the authority for package capabilities.

Every capability MUST define at minimum:

- canonical name;
- status;
- purpose;
- granted authority;
- associated public methods or declarations;
- whether it is runtime or declaration-only;
- security considerations;
- package kinds that may normally request it, if constrained;
- and documentation reference.

### 5.1 Canonical source

Capability definitions MUST NOT be duplicated as independently maintained allowlists across backend and frontend code.

Generated mirrors MAY exist, but they MUST be derived from or tested against the canonical registry.

CI MUST fail if capability definitions drift between runtime layers.

---

## 6. Capability lifecycle

SDK 1 public capabilities have only two public statuses:

- `stable`;
- `forbidden`.

To permit careful evolution without weakening that rule, the project MAY use non-public governance states before a capability enters the public registry.

### 6.1 Proposed

A proposed capability is an RFC concept only.

It MUST NOT be accepted in production package manifests.

A proposal MUST include:

- problem statement;
- real use cases;
- why existing capabilities are insufficient;
- authority granted;
- abuse cases;
- API sketch;
- server authorization model;
- lifecycle/cleanup behavior;
- expected events or schemas;
- migration impact;
- and tests required for stabilization.

---

### 6.2 Incubating

An incubating capability MAY exist behind:

- development builds;
- experimental feature flags;
- official prototype packages;
- test harnesses;
- or internal preview APIs.

It MUST NOT be treated as a stable SDK 1 public contract.

An incubating API MAY change without compatibility guarantees.

The project SHOULD use incubation to validate semantics, not to accumulate an undocumented shadow SDK.

---

### 6.3 Stable

A capability may be promoted to `stable` only after satisfying the stability gates in Section 10.

Once stable under SDK 1, its intentional contract MUST NOT be broken within SDK 1 except under the emergency security process.

---

### 6.4 Deprecated

Deprecation is metadata and documentation applied to an existing stable contract.

A deprecated SDK 1 capability remains supported for the remainder of SDK 1 unless an exceptional security issue requires otherwise.

Deprecation MUST include:

- replacement path;
- reason;
- migration guide;
- deprecation diagnostics where feasible;
- and target SDK major where removal may occur.

Deprecation MUST NOT be used as a mechanism for rapid removal within the same SDK major.

---

### 6.5 Removed

A stable SDK 1 contract may normally be removed only in SDK 2 or later.

Removal MUST be documented in the SDK migration guide.

---

### 6.6 Forbidden

A forbidden capability represents authority the current SDK deliberately refuses to grant.

The following remain forbidden in SDK 1:

```text
backend.execute
database.raw
filesystem.raw
network.raw
permissions.override
```

Equivalent aliases MUST also be rejected.

A future proposal MUST NOT bypass a forbidden capability by introducing the same authority under a friendlier name.

For example, this is not acceptable:

```text
system.power
```

if its actual semantics are equivalent to arbitrary backend execution.

---

## 7. Capability design rules

Every new capability MUST satisfy the following tests.

### 7.1 Semantic coherence

A capability MUST correspond to a coherent user-visible or system-level authority.

It SHOULD NOT be a grab bag of unrelated operations.

---

### 7.2 Minimum authority

A capability MUST grant no more authority than required by its stated purpose.

If read and mutation have materially different risk, they SHOULD be separate.

If ordinary operation and administration have materially different risk, they SHOULD be separate.

Example:

```text
cards.read
cards.play
cards.manage
```

---

### 7.3 Implementation independence

A capability MUST avoid binding packages to internal routes, internal classes, renderer nodes, DOM selectors, database tables, or private message formats.

---

### 7.4 Explicit failure model

Public operations MUST have defined failure semantics.

Stable machine-readable error codes SHOULD be preferred over parsing human-readable strings.

---

### 7.5 Lifecycle safety

Runtime registration APIs MUST define cleanup behavior.

Subscriptions, providers, UI registrations, observers, and other runtime resources MUST be removable when a package:

- disables;
- unloads;
- changes campaign activation;
- or is replaced during development.

Where appropriate, public registration APIs SHOULD return a disposer:

```js
const dispose = sdk.events.subscribe("actor.updated", handler);
dispose();
```

---

### 7.6 Bounded resource behavior

A capability that can consume significant resources MUST define appropriate limits.

Examples:

- maximum payload size;
- query timeout;
- result row limit;
- storage quota;
- event rate control;
- network response limit if a constrained network capability is ever introduced;
- render/update budget where applicable.

---

## 8. No private-internals policy for official packages

Official Gravewright packages are reference implementations of the SDK.

They MUST meet a stricter standard than third-party packages.

An official package MUST NOT depend on private Gravewright internals.

Without an explicit exception approved through SDK governance, official package code MUST NOT:

- call undocumented `/game/...` routes directly;
- access `window.Gravewright*` private globals;
- patch internal prototypes;
- depend on internal DOM selectors outside an extension-owned root;
- observe global DOM structure to infer core state;
- read private stores;
- access renderer objects directly;
- depend on private CSS classes;
- or reconstruct asset URLs from internal route conventions.

### 8.1 Official-package escape is an SDK review trigger

If an official ruleset or addon cannot implement a legitimate feature using the stable SDK, maintainers MUST open an SDK gap review.

The review must choose one of:

1. add or extend a semantic public API;
2. redesign the package behavior;
3. explicitly reject the use case;
4. or temporarily incubate a non-public prototype until a sound contract exists.

"Use the internal API for now" MUST NOT become a permanent solution.

### 8.2 CI enforcement

The project SHOULD maintain automated checks for official packages that flag patterns such as:

```text
window.Gravewright
fetch("/game/
XMLHttpRequest
document.querySelector(
MutationObserver(document.body
```

A match does not automatically prove a violation, but it MUST trigger review.

---

## 9. Existing public surfaces must not become escape hatches

The project MUST review broad helpers and context objects with the same rigor applied to named capabilities.

A narrow capability can be undermined if it returns a powerful unscoped helper bag.

### 9.1 Typed operations over arbitrary internal requests

Public helpers SHOULD NOT expose arbitrary same-origin request primitives such as:

```js
postJSON(url, body)
```

when package authors are expected to use semantic SDK operations.

Preferred:

```js
ctx.actor.patch({...});
ctx.item.patch({...});
ctx.refresh();
```

This preserves route freedom and centralizes authorization.

---

### 9.2 Scoped context

Sheet and runtime contexts SHOULD expose only the data and mutations appropriate to their scope.

A sheet controller MAY be allowed to mutate the actor or item it controls without receiving general campaign-wide write authority.

This is preferred over granting broad capabilities when context can safely narrow authority.

---

## 10. Stability gates for new public capabilities

A proposed capability MUST NOT become `stable` until all applicable gates pass.

### Gate A: Demonstrated need

There MUST be at least one concrete use case.

Preference SHOULD be given to:

- multiple independent use cases;
- multiple package kinds;
- or one strong use case in an official package proving the gap.

Speculative APIs SHOULD remain unimplemented or incubating.

---

### Gate B: Existing API review

The RFC MUST explain why the need cannot be met cleanly using existing stable contracts.

---

### Gate C: Security review

The capability MUST document:

- what authority it grants;
- what it cannot do;
- permission enforcement point;
- package/user trust assumptions;
- input validation;
- resource limits;
- data exposure;
- abuse scenarios;
- and whether browser scripts remain trusted code.

---

### Gate D: Encapsulation review

Reviewers MUST verify that the capability does not unnecessarily expose:

- route names;
- DOM structure;
- renderer internals;
- persistence internals;
- framework objects;
- or transport details.

---

### Gate E: Cross-system review

For rules-oriented APIs, the project MUST evaluate whether the contract is accidentally biased toward one RPG family.

A capability intended to be generic SHOULD be tested conceptually against substantially different systems where practical, for example:

- d20;
- roll-under;
- dice pool;
- PbtA;
- FitD;
- Fate/Fudge;
- Year Zero-style pools;
- card-driven initiative;
- step dice;
- percentile systems.

The SDK MUST not label a D&D-specific abstraction "generic" merely because its identifiers are renamed.

---

### Gate F: Runtime implementation

The public contract MUST have complete implementations on all required runtime layers.

A browser capability that mutates server state is incomplete until server authority and error semantics exist.

---

### Gate G: Tests

Stable capabilities MUST have tests covering, as applicable:

- manifest validation;
- capability gating;
- allowed path;
- denied path;
- permission denial;
- malformed input;
- lifecycle disposal;
- inactive package behavior;
- dependency absence;
- serialization;
- schema validation;
- compatibility fixture;
- and browser runtime behavior.

Static source-inspection tests MAY supplement, but SHOULD NOT replace, executable runtime tests for important JavaScript contracts.

---

### Gate H: Documentation

Stable capability documentation MUST include:

- purpose;
- required manifest declaration;
- method signatures;
- data schemas;
- examples;
- failure behavior;
- security notes;
- and lifecycle notes.

No undocumented public behavior is stable.

---

### Gate I: Reference package validation

Where practical, at least one real package SHOULD consume the proposed capability before stabilization.

---

### Gate J: Migration and future-proofing review

The proposal MUST answer:

> "What would we regret promising permanently?"

If reviewers cannot clearly state the durable semantic promise, the capability is not ready to stabilize.

---

## 11. RFC process

Substantive SDK changes require an SDK RFC.

### 11.1 Changes requiring an RFC

An RFC is REQUIRED for:

- adding a capability;
- broadening a capability's authority;
- adding a new stable public runtime surface;
- changing manifest schema;
- changing lifecycle semantics;
- changing package storage guarantees;
- changing inter-package messaging guarantees;
- adding externally reachable package networking;
- adding package-executed backend logic;
- deprecating a stable capability;
- creating a new SDK major;
- or making an exception to the official-package internals policy.

---

### 11.2 RFC template

Every SDK RFC SHOULD contain:

```markdown
# Title

## Status
Proposed / Accepted / Rejected / Implemented

## Problem

## Real use cases

## Non-goals

## Existing SDK limitations

## Proposed contract

## Requested capability/capabilities

## Authority model

## Server authorization

## Data schemas

## Lifecycle

## Security analysis

## Encapsulation analysis

## Alternative designs

## Compatibility impact

## Migration plan

## Test plan

## Documentation plan

## Open questions
```

---

### 11.3 Decision criteria

SDK proposals are evaluated in this order:

1. Does the use case belong in the Gravewright extension platform?
2. Can the need be expressed declaratively?
3. Can an existing capability solve it without distortion?
4. What is the narrowest semantic authority?
5. Can the contract survive a core rewrite?
6. Can permissions remain server-authoritative?
7. Can the contract be tested and documented precisely?
8. Is Gravewright willing to support this promise for the lifetime of the SDK major?

Convenience alone is not sufficient reason to stabilize an API.

---

## 12. Governance roles

### 12.1 Project maintainer

The Gravewright project maintainer has final responsibility for:

- SDK compatibility promises;
- security boundaries;
- capability registry changes;
- SDK major-version decisions;
- and emergency security action.

The maintainer MAY delegate review authority but remains accountable for the contract.

---

### 12.2 SDK reviewers

As the contributor base grows, the project SHOULD designate SDK reviewers.

An SDK reviewer SHOULD have demonstrated competence in at least one of:

- API design;
- package authoring;
- security;
- browser/runtime architecture;
- backend authorization;
- or RPG systems modeling.

At least one reviewer of a new capability SHOULD evaluate it from the perspective of a package author rather than only from the core implementation perspective.

---

### 12.3 Security reviewer

Capabilities that materially expand authority SHOULD receive explicit security review.

Examples include:

- external networking;
- storage changes;
- state mutation;
- content import;
- executable code;
- permission-sensitive operations;
- cross-package communication;
- and anything that crosses process, origin, or filesystem boundaries.

---

### 12.4 Package authors

Package authors are responsible for:

- declaring only required capabilities;
- avoiding private internals;
- documenting their capability use;
- handling optional peers safely;
- using versioned inter-package payloads;
- respecting lifecycle cleanup;
- and reporting SDK gaps rather than normalizing private workarounds.

---

## 13. Decision transparency

Accepted and rejected SDK RFCs SHOULD remain publicly available.

Significant decisions SHOULD include rationale, especially when the project chooses:

- not to expose a core subsystem;
- to split a capability;
- to forbid an authority;
- or to reject a seemingly convenient escape hatch.

The project SHOULD maintain a lightweight SDK decision log.

The purpose is to preserve architectural reasoning when maintainers change.

---

## 14. Inter-package governance

Package-to-package integration MUST use documented interop contracts.

The preferred mechanism is `sdk.bus.*` or another explicitly documented stable successor.

Packages SHOULD NOT integrate by:

- reaching into another package's globals;
- importing another package's private files;
- inspecting another package's DOM;
- or relying on load order unless load order is explicitly part of a stable contract.

### 14.1 Namespaces

Publishers and providers MUST use owned namespaces.

A package MUST NOT impersonate another package's namespace.

### 14.2 Payload schemas

Cross-package payloads SHOULD be:

- serializable;
- versioned;
- schema-validatable;
- bounded;
- and independent of internal Gravewright classes.

### 14.3 Missing peers

Packages MUST treat optional peer absence as a normal state.

---

## 15. Event governance

If Gravewright exposes core events, the event catalog MUST remain intentionally small.

Events MUST describe durable semantic facts, not implementation choreography.

Preferred:

```text
actor.updated
token.moved
scene.activated
combat.updated
chat.created
```

Avoid:

```text
pixi-container-mounted
sidebar-div-replaced
websocket-message-17-received
```

Event payloads MUST be documented and versionable.

Packages MUST NOT receive mutable internal domain objects merely for convenience.

---

## 16. UI extension governance

The project SHOULD provide explicit UI extension points where ecosystem demand is demonstrated.

Preferred model:

```text
ui.slots
```

with stable semantic slots such as:

```text
scene.toolbar
actor.header.actions
item.header.actions
chat.message.actions
combat.combatant.actions
```

A slot name is a semantic location, not a DOM selector guarantee.

Packages SHOULD render into extension-owned roots supplied by Gravewright.

Gravewright MUST retain freedom to replace surrounding DOM and frontend framework.

---

## 17. Data and storage governance

### 17.1 Managed storage

Package storage MUST remain scoped and Gravewright-managed.

Packages MUST NOT receive arbitrary filesystem paths.

### 17.2 Raw database access

`database.raw` remains forbidden.

If packages need richer persistence, Gravewright SHOULD expand managed semantic storage rather than expose the application database.

### 17.3 Migrations

Package storage migrations MUST be treated as privileged input.

Migration execution SHOULD be constrained by authorization or authorizer mechanisms appropriate to the storage engine.

The migration path MUST NOT silently grant capabilities forbidden by ordinary storage APIs.

### 17.4 Secrets

Package settings and package storage MUST NOT be advertised as a general secret vault unless Gravewright explicitly implements one.

---

## 18. Network governance

`network.raw` remains forbidden.

If a legitimate integration ecosystem eventually requires outbound network access, it MUST be introduced through a new RFC and a constrained semantic capability, not by un-forbidding arbitrary networking.

A future constrained network capability SHOULD consider:

- explicit origin allowlists;
- no localhost/LAN access by default;
- request timeouts;
- response-size limits;
- safe redirect policy;
- stripped ambient credentials;
- operator-visible requested origins;
- and SSRF defenses.

Until such a contract is deliberately designed, packages MUST NOT receive SDK-backed arbitrary network authority.

---

## 19. Backend code governance

`backend.execute` remains forbidden in SDK 1.

The project MUST NOT add arbitrary server-side package execution merely to achieve parity with browser package flexibility.

If future systems prove that server-side custom computation is necessary, the project MUST first evaluate safer models such as:

- richer declarative rules;
- typed intents;
- deterministic expression evaluation;
- constrained WASM;
- or another sandbox with strict CPU, memory, host-call, and persistence limits.

Any such mechanism requires an SDK-major-level security review unless it can be proven compatible with the existing trust model.

---

## 20. Official package policy

Official rulesets and addons serve two purposes:

1. provide useful game functionality;
2. continuously test whether the public SDK is sufficient.

Therefore official packages SHOULD intentionally exercise the SDK as third-party authors are expected to use it.

They MUST NOT receive private privileged APIs merely because they are official.

If Gravewright gives an official package a privileged internal integration, that integration either:

- must remain clearly core-owned and not packaged as an SDK example;
- or must go through SDK governance before becoming a package-facing contract.

---

## 21. Capability request review at install time

The ecosystem SHOULD make package authority understandable to operators.

Package tooling SHOULD distinguish categories such as:

- declarative-only;
- trusted browser JavaScript;
- state mutation;
- storage;
- inter-package communication;
- administrative functionality;
- future external integrations.

Packages SHOULD document why each requested capability is needed.

The CLI and UI MAY surface concise human-readable capability descriptions generated from the canonical registry.

---

## 22. Compatibility test fixtures

The project MUST maintain representative SDK 1 compatibility fixtures.

These SHOULD include packages exercising:

- minimal manifest;
- each package kind;
- stable capability combinations;
- managed storage;
- lifecycle;
- interop;
- sheets;
- content;
- and representative rulesets.

A core rewrite that claims SDK 1 compatibility MUST pass these fixtures.

This is how Gravewright proves that the SDK boundary is real rather than aspirational.

---

## 23. Architecture fitness tests

In addition to ordinary unit tests, Gravewright SHOULD maintain tests that enforce architectural policy.

Examples:

### 23.1 Capability sync

```text
canonical capabilities == generated frontend capability map
```

### 23.2 No unknown public method

Every gated public method maps to a canonical capability.

### 23.3 Forbidden authority

Forbidden capabilities are rejected by:

- manifest validation;
- package doctor;
- installation;
- activation;
- and runtime construction where applicable.

### 23.4 Official packages do not use internals

Static checks and executable tests SHOULD detect known classes of boundary escape.

### 23.5 Public schema fixtures

Old valid SDK 1 fixtures continue to validate.

### 23.6 Scoped package identity

A package cannot register, publish, or provide as another package.

### 23.7 Server-side permission enforcement

Possession of a capability alone does not bypass the current user's authority.

---

## 24. Deprecation policy

Deprecation MUST be boring.

When a stable API is deprecated:

1. documentation marks it deprecated;
2. the replacement is documented;
3. migration examples are provided;
4. diagnostics warn authors where feasible;
5. the old API continues to work through the supported SDK major;
6. removal occurs only in the next SDK major unless security requires emergency action.

The project MUST avoid deprecation churn.

A stable API SHOULD not be deprecated merely because maintainers prefer a different coding style.

---

## 25. Emergency security changes

Security may require behavior changes faster than ordinary compatibility policy permits.

An emergency breaking change to a stable SDK contract is permitted only when maintaining the old behavior creates a credible security risk that cannot reasonably be mitigated through a compatible patch.

When this occurs, the project MUST:

- document the affected contract;
- explain the security class without unnecessarily disclosing exploitable detail before a fix is available;
- provide the narrowest feasible break;
- provide migration guidance;
- provide diagnostics where possible;
- and record the decision as an exception.

"Security" MUST NOT be used as a generic justification for unrelated API cleanup.

---

## 26. SDK major version policy

A new SDK major is expensive and SHOULD be rare.

SDK 2 SHOULD exist only when the project needs to make intentional contract changes that cannot be preserved cleanly under SDK 1.

Before opening SDK 2, maintainers SHOULD ask whether the desired change can instead be implemented behind the existing semantic contract.

When a new major is necessary:

- SDK 1 and SDK 2 MAY coexist for a transition period;
- adapters SHOULD be centralized in Gravewright where feasible;
- package authors SHOULD receive migration tooling;
- compatibility diagnostics MUST clearly explain requirements;
- and the project SHOULD avoid forcing simultaneous migration of unrelated APIs.

The goal of an SDK major is to retire genuine architectural mistakes, not to synchronize with the Gravewright application version number.

---

## 27. Package ecosystem growth policy

The project SHOULD optimize for an ecosystem that can become large **without forcing the core to freeze**.

That means Gravewright SHOULD prefer:

- small semantic contracts;
- versioned data;
- explicit capabilities;
- explicit extension slots;
- server-authoritative mutations;
- declarative configuration;
- scoped storage;
- stable interop;
- and strong tooling.

It SHOULD avoid:

- monkey patching as a supported extension model;
- public renderer objects;
- public DOM contracts;
- arbitrary route calls;
- private-global conventions;
- implicit load-order dependencies;
- and "temporary" unrestricted escape hatches.

---

## 28. Governance of SDK gaps

An SDK gap is not automatically a bug.

When a package author reports that the SDK cannot perform a task, the project MUST classify the gap:

### A. Common semantic need

Add or extend a public capability after RFC review.

### B. Context-scoped need

Prefer a narrower context API rather than a broad global capability.

Example:

```js
ctx.actor.patch(...)
```

may be safer than campaign-wide `actors.write`.

### C. Package-to-package concern

Use or extend the interop contract.

### D. UI placement concern

Use or add a semantic UI slot rather than exposing DOM structure.

### E. Core implementation concern

Do not expose it merely because a package wants access.

### F. Unsafe authority

Reject it or design a constrained substitute.

This classification process replaces the temptation to add `any`.

---

## 29. Maintainer checklist for every SDK change

Before merging a public SDK change, the maintainer SHOULD be able to answer "yes" to all applicable questions:

- Is the use case real?
- Is this the narrowest useful contract?
- Is it semantic rather than implementation-specific?
- Can the core be rewritten behind it?
- Does it preserve server authority?
- Is capability scope appropriate?
- Are error semantics defined?
- Is lifecycle cleanup defined?
- Are resource limits defined?
- Are data schemas versionable?
- Is it tested in executable runtime code?
- Is it documented?
- Has security been reviewed?
- Has at least one realistic package validated the design?
- Are we willing to support this contract for the lifetime of the SDK major?

If the last answer is uncertain, the API is not ready to become stable.

---

## 30. Package author covenant

By targeting the Gravewright SDK, package authors should be able to expect:

- intentional stable contracts;
- explicit deprecation;
- strong compatibility discipline;
- documented capabilities;
- and a core that treats package compatibility as a platform responsibility.

In return, package authors are expected to:

- stay within documented public boundaries;
- avoid private internals;
- request least privilege;
- report missing capabilities;
- use supported interop;
- write portable package code;
- and migrate when a future SDK major deliberately changes the contract.

The stability promise is strongest when both sides respect the boundary.

---

## 31. Governance philosophy

Gravewright must resist two opposite failures.

The first is an SDK so restrictive that serious systems cannot be built.

The second is an SDK so permissive that every internal detail becomes ecosystem dependency.

The project should aim for a third model:

> **Powerful semantic extension, narrow authority, strong encapsulation.**

The purpose of SDK governance is not to prevent evolution.

It is to make evolution possible.

A healthy Gravewright ecosystem should be able to accumulate:

- dozens of rulesets;
- hundreds of addons;
- years of user content;
- and long-lived campaigns,

while the core remains free to replace its renderer, UI, persistence, networking, and internal architecture.

That freedom is a product feature.

It is also the central long-term promise of the Gravewright SDK.

---

## 32. Final policy

The Gravewright SDK will be governed according to the following hierarchy:

1. **Security over convenience.**
2. **Intentional contract over accidental behavior.**
3. **Semantic API over implementation exposure.**
4. **Least privilege over broad authority.**
5. **Declarative contracts over unnecessary runtime coupling.**
6. **Compatibility over internal convenience once an API is stable.**
7. **Core replaceability over ecosystem dependence on current internals.**
8. **Real use cases over speculative API growth.**
9. **Explicit RFC decisions over undocumented exceptions.**
10. **No universal escape capability.**

The project will not promise that Gravewright's internals remain the same.

It will promise that stable SDK contracts are treated as real contracts.

That distinction is the foundation of the platform.
