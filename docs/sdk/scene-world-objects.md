# Scene world objects

Scene world objects are persistent campaign resources whose semantic type comes from an active package while authority, storage, audience filtering, rendering, hit-testing, selection, and mutation remain core-owned. They are not renderer access, arbitrary overlays, Tokens, or Zones.

Register a bounded type with `sdk.scene.objectTypes.register()`. Type IDs must be namespaced by the provider package. Definitions contain JSON-safe schemas, supported world-coordinate geometry kinds, declarative visuals, optional editor metadata, searchable fields, and semantic interactions; they never contain render or hit-test callbacks. Instances use `sdk.scene.objects.list/get/create/update/delete`, and updates require `expectedVersion` CAS.

Supported geometry is `point`, `rect`, `circle`, `polygon`, and `polyline`. The core derives bounds and hit tests. Audience-filtered objects are never projected to unauthorized clients. Clicking a projected object selects it and submits its declared semantic interaction; an exact provider-owned registered-action reference may execute after authority is revalidated.

Disabling a provider preserves its instances and projects an unavailable placeholder to authorized GMs. Re-enabling and registering the matching schema restores normal projection without data loss. Schema changes do not run client migrations: mismatched historical data remains preserved for an explicit future migration workflow.
