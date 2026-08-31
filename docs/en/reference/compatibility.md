# Compatibility and versioning

Gravewright currently remains `0.x`. This document defines the policy proposed
for an eventual 1.x line; it does not claim that the API is frozen today.

## Release path

- `0.9.0`: pre-freeze; the central architecture is defined.
- `0.9.x`: dogfooding, third-party modules, upgrade testing and final evidence-based adjustments.
- `1.0.0-rc.1`: effective API freeze once no fundamental breaking changes are foreseeable.
- `1.0.0`: stable after the RC survives real use without contract redesign.

During `0.9.x`, bug fixes, security hardening, documentation, tooling and
compatible ergonomics are expected. A breaking change remains possible only
when real module use demonstrates that a contract is wrong. Speculative
redesign, aesthetic churn and core expansion into module responsibilities are
not appropriate. The guiding question is: “Is there a real reason to break
these contracts before 1.0?”

There is no required number of intermediate releases. RC begins when real
modules work without demanding new central surfaces, upgrades are understood,
and the public API has no foreseeable fundamental break. Stable follows when RC
usage produces predominantly bug, documentation and tooling changes.

## Version axes

- The kernel version covers runtime validation, planning, composition, and lifecycle.
- The SDK version covers TypeScript author contracts and helpers.
- Manifest schema v1 is the JSON shape documented in `docs/schema/manifest-v1.json`.
- `gravewright.room/v1` versions the browser room/slot protocol.
- Capabilities use stable names such as `gravewright.storage` and declare their
  protocol version separately with SemVer. A breaking storage protocol becomes
  capability version `2.0.0`; it does not need a second name containing `/v2`.

There is intentionally no additional manifest handshake field. A manifest is
validated against the schema understood by the host, while module npm metadata
declares the compatible SDK package range. Add a handshake only if real
multi-schema coexistence demonstrates the need.

## Proposed 1.x guarantees

A Kernel 1.5 host should accept a module authored against SDK 1.1 when its
manifest, dependencies, capability ranges, and room protocol validate. Minor
versions may add optional fields, types, helpers, or behavior that does not
invalidate existing valid compositions.

The following require a major version or a separately versioned protocol:

- removing or changing an SDK public member incompatibly;
- changing lifecycle ordering or authorization guarantees;
- making a previously valid manifest invalid without a security justification;
- changing a capability's method semantics incompatibly;
- changing required room slots or their semantics.

Security validation may become stricter in a minor or patch release when needed
to reject unsafe input. Such changes must be called out prominently.

Deprecations should remain documented for at least one minor release and include
a migration path before removal in the next major version.
