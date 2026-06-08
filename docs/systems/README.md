# Gravewright System API

Systems define the rules, sheet models, roll behavior, combat behavior, assets, and optional starter content for a game ruleset.

System API materials are licensed under MIT. The Gravewright runtime that loads, validates, stores, renders, and executes systems remains Apache-2.0.

## Guides

- `creating-a-system.md` explains the recommended package structure.
- `manifest.md` documents `manifest.json`.
- `sheets.md` documents declarative actor and item sheets.
- `rolls.md` documents action and roll configuration.
- `combat.md` documents initiative, turn order, and combat integration.
- `content-packs.md` documents bundled actors, items, journals, and scenes.

## Package Layout

```text
data/systems/<system-id>/
  manifest.json
  schemas/
  layouts/
  rules/
  assets/
  packs/
```

The manifest is the entry point. All referenced files must stay inside the system directory. Gravewright validates manifests, declared capabilities, schema references, layout references, rule files, assets, and content packs before enabling a system for campaigns.

## Stability

System API v1 is the current documented contract for ruleset authors. The project is still pre-1.0, so changes may occur, but public schema, manifest, and runtime API changes should update these docs and tests in the same change.
