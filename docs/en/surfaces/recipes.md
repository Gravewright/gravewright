# Recipes and capability providers

A recipe installs a reproducible module composition. Concrete dependencies are
resolved automatically; replaceable capabilities require an explicit provider choice.

```json
{
  "schema_version": 1,
  "kind": "recipe",
  "name": "classic-table",
  "title": "Classic Table",
  "version": "1.0.0",
  "modules": [
    { "manifest_url": "https://example.org/server.json", "state": "active" },
    { "manifest_url": "https://example.org/sqlite.json", "state": "active" },
    { "manifest_url": "https://example.org/game.json", "state": "active" }
  ],
  "capabilities": {
    "gravewright.storage": "sqlite-storage"
  }
}
```

The plan verifies that the selected module provides the capability at a compatible
version. Other providers of the same selected capability are disabled by the plan.
The resulting project must still contain exactly one active server.
