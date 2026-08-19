# SDK 1 RC 1 — compatibility policy

Gravewright SDK **1** is at **Release Candidate 1**. The public contract is frozen:
what is published in `gravewright-sdk-1.json`, `gravewright-sdk-1.d.ts` and the SDK
documentation is what a package may build on, and it is not expected to change again
before SDK 1 goes stable.

RC status is a statement about stability, not a version. `sdkVersion` is `1`, packages
declare `"sdkVersion": "1"`, and promotion from RC 1 to SDK 1 Stable will not change
that field or require any package to be republished.

## What is public

Only what the contract declares:

- the methods, parameters and return types in `gravewright-sdk-1.json`;
- the types in `gravewright-sdk-1.d.ts`;
- the capabilities, events and error codes in the same registries;
- the runtime semantics those documents describe — authority, visibility,
  concurrency and durability.

## What is not public

Everything else, including:

- response fields the DTO does not declare;
- internal service and repository shapes;
- the DOM, the renderer, and anything under `window` other than the documented SDK
  entry point;
- private HTTP routes and raw WebSocket frames;
- the database schema and the filesystem layout;
- internal events and implementation-only DTO fields.

A package that depends on any of these has **no compatibility guarantee**, and a
release may change them without notice. This is not a restriction on what you may do
with the source — Gravewright is open, and forking or patching it is entirely
legitimate. It is a statement about what the SDK promises to keep working.

Before RC 1 the token read passed undeclared core fields through, including
`token_id` and an unfiltered `controlled_by_user_ids`. Those were never part of the
contract; the read now returns the declared `TokenDTO`, whose identity field is `id`
and whose `controllers` list is filtered by the caller's authority to inspect
control. No alias is provided for the removed internals.

## Breaking versus compatible

**Breaking** — not permitted during RC without explicit review:

- removing or renaming a method, capability, event or error code;
- removing a public DTO field, or narrowing a public type;
- making an optional parameter required, or removing a parameter;
- changing what a method returns;
- changing authority semantics for a caller that was already valid;
- moving a method to a different namespace.

**Compatible** — permitted during RC:

- bug, security and performance fixes;
- replacing an implementation behind an unchanged contract;
- documentation corrections and new tests;
- removing undeclared or internally leaked fields, which were never promised;
- adding an optional field or parameter, after explicit RC review.

New methods and new capabilities are structurally compatible, but RC 1 is a feature
freeze: they require explicit review before they are accepted, and the contract diff
classifier reports them as `POTENTIALLY_BREAKING` so they cannot land silently.

## How the freeze is enforced

`docs/sdk/_data/gravewright-sdk-1.rc1-snapshot.json` is a semantic fingerprint of the
certified contract — method identities, parameter requiredness and types, return
types, capability, event and error ids, and DTO fields. Formatting, ordering and
prose are deliberately excluded, so documentation may be rewritten freely.

```
python scripts/sdk1_contract_snapshot.py --diff    # classify every difference
python scripts/sdk1_contract_snapshot.py --check   # fail on a breaking change
python scripts/sdk1_contract_snapshot.py --write   # re-freeze after an approved change
```

The test suite runs `--check`, so an accidental breaking change fails CI rather than
reaching a published package.

## Reporting a gap

If your addon needs something the public SDK cannot express:

1. confirm no existing public composition solves it;
2. report it as a public SDK gap, with the operation you are blocked on;
3. do not ship against private internals in the meantime and expect them to hold.

SDK **2** is reserved exclusively for an intentional incompatible change to this
public contract. It is not a product release number, and the product version moves
independently of it.
