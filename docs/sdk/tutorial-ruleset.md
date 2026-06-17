# Tutorial: from zero to a minimal working ruleset

This walkthrough builds a real ruleset from scratch: one actor type, one item type, a
declarative sheet, a rule formula, and locales. The finished package ships as
[`examples/packages/my-rpg`](../../examples/packages/my-rpg) and is validated in CI.

A `ruleset` defines a campaign's base game rules. Its activation mode is `exclusive`: a
campaign has exactly one active ruleset.

## Prerequisites

- A working Gravewright checkout where the `grave` CLI runs (see [`getting-started.md`](../getting-started.md)).
- A campaign you can configure.

## 1. Scaffold the package

```bash
grave ruleset new my-rpg --name "My RPG" --sheets
```

This creates the package under `data/packages/rulesets/my-rpg/`. The target layout for this
tutorial is:

```text
data/packages/rulesets/my-rpg/
  manifest.json
  schemas/
    character.schema.json
    item.schema.json
  layouts/
    character.sheet.gw.json
    item.sheet.gw.json
  rules/
    formulas.gw.json
  locales/
    en.json
```

## 2. Declare the manifest

A ruleset manifest must use `activation.mode: "exclusive"`, declare a storage model, and
declare at least one actor type. `provides` wires the actor/item types to their schema,
sheet, and rule files:

```json
{
  "kind": "ruleset",
  "id": "my-rpg",
  "name": "My RPG",
  "compatibility": { "minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1" },
  "capabilities": [
    "actors.register",
    "items.register",
    "sheets.declarative",
    "rules.declarative",
    "locales"
  ],
  "activation": { "scope": "campaign", "mode": "exclusive" },
  "entrypoints": {},
  "provides": {
    "storage": { "model": "scoped-json-v1" },
    "actorTypes": [
      {
        "id": "character",
        "labelKey": "my-rpg.actor.character",
        "schema": "schemas/character.schema.json",
        "sheet": "layouts/character.sheet.gw.json"
      }
    ],
    "itemTypes": [
      {
        "id": "item",
        "labelKey": "my-rpg.item.item",
        "schema": "schemas/item.schema.json",
        "sheet": "layouts/item.sheet.gw.json"
      }
    ],
    "rules": { "formulas": "rules/formulas.gw.json" },
    "locales": { "en": "locales/en.json" }
  }
}
```

Every path in `provides` must exist on disk, or validation fails with `file_missing`.

## 3. Define the data shape

`schemas/character.schema.json` describes the stored actor data:

```json
{
  "type": "object",
  "properties": {
    "level": { "type": "number", "default": 1 },
    "hp": {
      "type": "object",
      "properties": {
        "value": { "type": "number", "default": 10 },
        "max": { "type": "number", "default": 10 }
      }
    },
    "strength": { "type": "number", "default": 10 }
  }
}
```

`schemas/item.schema.json`:

```json
{
  "type": "object",
  "properties": {
    "quantity": { "type": "number", "default": 1 },
    "weight": { "type": "number", "default": 0 },
    "description": { "type": "string", "default": "" }
  }
}
```

## 4. Lay out the sheet

`layouts/character.sheet.gw.json` is a declarative sheet bound to actor data:

```json
{
  "kind": "actorSheet",
  "system": "my-rpg",
  "actorType": "character",
  "id": "my-rpg-character",
  "title": { "bind": "core.name" },
  "body": {
    "type": "section",
    "variant": "main",
    "children": [
      { "type": "field", "label": "my-rpg.field.level", "path": "sheet.level" },
      { "type": "field", "label": "my-rpg.field.strength", "path": "sheet.strength" }
    ]
  }
}
```

Provide `layouts/item.sheet.gw.json` the same way for the item type. See
[`declarative-model.md`](declarative-model.md).

## 5. Add a rule and locales

`rules/formulas.gw.json` declares reusable helper formulas:

```json
{
  "helpers": {
    "strengthMod": { "args": ["score"], "expression": "floor((score - 10) / 2)" }
  }
}
```

`locales/en.json` supplies the label keys referenced by the manifest and sheet:

```json
{
  "my-rpg.actor.character": "Character",
  "my-rpg.item.item": "Item",
  "my-rpg.field.level": "Level",
  "my-rpg.field.strength": "Strength"
}
```

## 6. Validate

```bash
grave package validate data/packages/rulesets/my-rpg
```

Expected:

```text
my-rpg: ok
```

## 7. Install, enable, and activate for a campaign

```bash
grave package install my-rpg --yes --enable
```

A ruleset is **exclusive**, so it is not activated with `grave campaign package activate`.
Instead, choose **My RPG** as the campaign's ruleset when you create or edit the campaign
in the Gravewright app — it becomes the campaign's authoritative active ruleset.

## 8. See it work

Open the campaign and create a `character` actor. The declarative character sheet renders
with the Level and Strength fields you defined, backed by the schema defaults.

## 9. Debug when something is off

```bash
grave package doctor my-rpg
```

## Next steps

- Add rolls, combat, and content to the ruleset (`grave ruleset new ... --rolls --combat --content`).
- Build an addon on top: [`tutorial-addon.md`](tutorial-addon.md).
- Map goals to manifest fields and capabilities: [`power-map.md`](power-map.md).
