# SDK 1 RC 1 — certification record

Status: **RC 1**. `sdkVersion`: **1**.

RC status is release metadata. It does not appear as a second compatibility axis:
packages declare `"sdkVersion": "1"` and will continue to when SDK 1 goes stable.

## Certified contract

Derived from the canonical generators at certification time:

| | |
|---|---|
| SDK version | 1 |
| Methods | 264 |
| Capabilities | 116 |
| Events | 51 |
| Errors | 25 |
| DTOs | 290 |
| Unresolved returns | 0 |
| Unresolved parameters | 0 |

Regenerate with `scripts/generate_sdk1_contract.py` and
`scripts/generate_sdk_reference.py`; both verify clean with `--check`. The frozen
semantic fingerprint lives in `_data/gravewright-sdk-1.rc1-snapshot.json` and is
enforced by `scripts/sdk1_contract_snapshot.py --check`. See
[rc1-compatibility-policy.md](rc1-compatibility-policy.md).

## Conformance package

Black Vault (`data/packages/addons/black-vault`) is the permanent SDK 1 RC
conformance and extreme-stress package. It is deliberately **not** published to the
Marketplace.

| | |
|---|---|
| Private API references | 0 |
| Unknown capabilities | 0 |
| Undeclared SDK usage | 0 |
| Core modification required | No |
| Public methods used | 51 |
| Capabilities declared | 45 |
| Events consumed | 2 |
| Systemless | Yes — no ruleset, no dice |

Domains exercised: campaign members, actors, tokens, zones, world objects, gameplay
flow, durable workflow, directed interactions, registered actions, semantic timeline,
audio playback, native sounds, spatial sounds, cards, semantic drag/drop, token
transfer, scene navigation, presentations, content references, journals, UI
applications, input commands, settings, and package storage. Package interop is not
used, because the mission does not need it.

## Known non-blocking observations

These are recorded, not fixed. None blocks RC 1.

1. **Gameplay Flow has no terminal resource state.** `advance` cycles through phases
   modulo their count and there is no `complete`/`cancel`, so an instance stays
   `ACTIVE` indefinitely. A phase named `COMPLETE` is sufficient for a mission to
   express completion.
2. **Wall `behavior.sound` is write-only.** `createWall`/`updateWall` accept it, but
   `WallDTO`/`GeometryBehaviorDTO` do not expose it, so a package cannot read back
   what it set. A closed door blocks sound by default, so no mission is blocked.
3. **The runtime command endpoint returns `201` broadly**, including for updates and
   state toggles. Pre-existing convention.
4. **Package-shipped image assets cannot be minted into campaign assets.**
   `sdk.assets.ingest` accepts only a user-selected browser `File`. Card artwork is a
   `campaign-asset-slot` by design, so this is intended rather than a gap.
5. **Package Doctor cannot see every declarative capability use.** Doctor now infers
   capabilities from a declared action registry, so a registered action no longer
   reports its operations' capabilities as unused. Definitions registered at runtime —
   workflow `INTERACTION` steps and timeline `AUDIO_PLAY` cues — remain invisible to
   static analysis, so `interactions.request`, `interactions.respond` and
   `audio.playback` may still be reported as `capability_declared_unused`. These are
   warnings about detection, not about the declaration: the capabilities are required
   and enforced at runtime. Closing this fully would need real JS static analysis.

## Author guidance

Build on the public SDK if you want RC and stable compatibility guarantees. If your
addon appears to need an internal API:

1. verify the public SDK genuinely cannot express the use case;
2. report it as a public SDK gap, naming the blocked operation;
3. do not treat private internals as stable in the meantime.

Gravewright is open source and you remain free to fork or patch it. Those changes
simply fall outside the SDK compatibility guarantee.
