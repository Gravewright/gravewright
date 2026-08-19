# Black Vault

Black Vault is the SDK 1 conformance and stress package: a cooperative supernatural
infiltration mission that exercises representative cross-domain SDK functionality in
one coherent, playable slice.

Its purpose is to prove that a demanding third-party module can be built entirely on
the public contract. It reaches no private route, no renderer, no database and no
filesystem, and it requires no change to Gravewright core. It is intentionally not
published to the Marketplace.

The mission is **systemless**: no ruleset, no dice, no initiative, no hit points.

## Domains exercised

| Mission concern | Public domain used |
|---|---|
| Participant selection | Campaign roster (`sdk.campaign.members`) |
| Phase machine, `BRIEFING` → `COMPLETE` | Gameplay Flow, `SIMULTANEOUS` secret commitment |
| Alarm and terminal decisions | Durable Workflow, Directed Interaction, `resultKey` + `BRANCH` |
| Consequences | Registered actions |
| Alarm cascade | Semantic Timeline — audio, presentation, light, shader, particles |
| Restricted and extraction areas | Scene Zones |
| Terminal, Pedestal, Elevator, Beacon, Clue Pin | Scene Object type registry |
| Reaction targeting | `TokenDTO.controllers` |
| Access Card, Artifact | Native Cards, semantic drag and drop |
| Ambience and acoustics | Native Sounds, Spatial Sounds, wall and door geometry |
| Scene-to-scene movement | Token Transfer, then separate Scene Navigation |
| Clue | Journal, ContentReference |
| Operations panel | UI Application, Presentations, Input commands |
| Module preferences | Settings |
| Objective log | Package SQLite storage |

Every branch is decided by the server. A workflow's `INTERACTION` step declares a
`resultKey`, core projects the player's answer into workflow context, and the
existing `BRANCH` step selects the consequence. The package source contains no branch
logic of its own.

## Running the conformance suite

```
python -m pytest tests/unit/test_black_vault_complete_mission.py    # full mission
python -m pytest tests/unit -k black_vault                          # all conformance tests
python -m pytest tests/unit/test_black_vault_rc1_certification.py   # manifest, Doctor, private-API scan
```

The complete-mission test walks the whole slice in one run: roster, secret planning
and reveal, restricted-zone entry, controller resolution, the alarm branch with a
reload while the decision is pending, the cascade, the credential drop, the terminal
override, the artifact, the clue, the elevator, atomic party transfer with navigation
proven separate, extraction, and cold-session reconstruction.

## Declared-but-not-called capabilities

Package Doctor reports `capability_declared_unused` for three capabilities because
its scan looks for `sdk.<method>(` call sites. All three are required and enforced at
runtime, and all three are exercised server-side rather than called directly:

- `interactions.request` / `interactions.respond` — the workflow's `INTERACTION` step
  creates the decision; the player answers it through native UI.
- `audio.playback` — the timeline's `AUDIO_PLAY` cue plays under this package's
  provenance.

No call is added artificially to clear a warning.
