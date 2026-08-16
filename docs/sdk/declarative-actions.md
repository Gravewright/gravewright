# Declarative actions

Packages declare registered actions through `provides.rules.actionRegistry`. Each definition has a stable package-local ID, an explicit positive contract version, a typed object input schema, an idempotency class and at most 16 allow-listed semantic operations.

Use `sdk.rules.actions.list()` and `sdk.rules.actions.get(id)` for discovery, then `sdk.rules.actions.execute(id, input, {version})`. The caller cannot submit an operation graph. Definitions are validated when the package is loaded; an invalid definition is omitted without making arbitrary code executable.

Execution rechecks package activation, campaign membership, current-user authority, resource visibility and the capability required by every operation. Results contain the action identity, version, an opaque execution ID, a semantic result and small changed-resource references. `rules.action.completed` contains no resource state; listeners re-read resources through their normal authorized APIs.

`REQUIRES_IDEMPOTENCY_KEY` is crash-safe when the core derives `durability: supported`: currently exactly one `actor.data.patch`. Mutation and receipt share one Actor envelope replacement. Multi-step and cross-resource definitions are not durable. This is at-least-once scheduling plus idempotent execution, not cross-domain exactly-once.

`resolve({provider:"active-ruleset", semantic})` discovers typed ruleset semantics and returns a stable reference. `executeReference` invokes the provider through normal current-user authority without exposing private storage paths.
