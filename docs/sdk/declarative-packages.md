# Declarative Packages

Most SDK packages should be declarative: the manifest points at JSON files that
describe data, sheets, rules, content, locales, assets, and mappings. Use
JavaScript only when the package needs custom browser behavior that the
declarative model cannot express.

## Build order

1. Pick the package `kind`.
2. Declare `actorTypes` and `itemTypes` in `manifest.json`.
3. Create JSON Schemas for each type.
4. Create declarative sheets for each type.
5. Add rules, validation, token mappings, and content packs as needed.
6. Add locales for every `labelKey`.
7. Run `grave package validate <path>` and `grave package doctor <id>`.

## Manifest wiring

A ruleset declares the game model under `provides`:

```json
{
  "kind": "ruleset",
  "capabilities": [
    "actors.register",
    "items.register",
    "sheets.declarative",
    "rules.declarative",
    "tokens.mappings",
    "content.packs",
    "locales"
  ],
  "provides": {
    "storage": { "model": "scoped-json-v1" },
    "actorTypes": [
      {
        "id": "character",
        "labelKey": "my.ui.character",
        "schema": "schemas/character.schema.json",
        "sheet": "layouts/character.sheet.gw.json"
      }
    ],
    "itemTypes": [
      {
        "id": "weapon",
        "labelKey": "my.ui.weapon",
        "schema": "schemas/item.schema.json",
        "sheet": "layouts/items/weapon.sheet.gw.json"
      }
    ],
    "rules": {
      "formulas": "rules/formulas.gw.json",
      "derived": "rules/derived.gw.json",
      "validation": "rules/validation.gw.json",
      "actions": "rules/actions.gw.json"
    },
    "mappings": {
      "tokens": "mappings/token.gw.json"
    },
    "contentPacks": [
      {
        "id": "my-weapons",
        "type": "item_pack",
        "labelKey": "my.ui.weapons",
        "path": "content/items.weapons.gwpack.json"
      }
    ],
    "locales": {
      "en": "locales/en.json",
      "pt-BR": "locales/pt-BR.json"
    }
  }
}
```

The ids in `actorTypes[].id` and `itemTypes[].id` are the type names used by
actors, items, content pack entries, sheets, drops, rules, and mappings.

## Data model with JSON Schema

Actor and item data lives under the `sheet` namespace. The schema describes that
stored data without the leading `sheet.` prefix. Defaults create the initial data
tree when a record is created or imported.

```json
{
  "type": "object",
  "properties": {
    "hp": {
      "type": "object",
      "properties": {
        "value": { "type": "integer", "default": 10 },
        "max": { "type": "integer", "default": 10 }
      }
    },
    "level": { "type": "integer", "default": 1 },
    "ac": { "type": "integer", "default": 10 },
    "description": { "type": "string", "default": "" }
  }
}
```

Paths in sheets and rules use `sheet.hp.value`; schema properties use `hp.value`.
`core.name` is built-in metadata, not part of the sheet schema.

## Declarative sheets

A sheet file is a JSON tree. Actor sheets use `kind: "actorSheet"`; item sheets
use `kind: "itemSheet"`. Every editable field writes to `core.*` or `sheet.*`.

```json
{
  "kind": "itemSheet",
  "system": "my-rpg",
  "id": "my-weapon",
  "title": { "bind": "core.name" },
  "body": {
    "type": "section",
    "labelKey": "my.ui.weapon",
    "children": [
      { "type": "textField", "path": "core.name", "labelKey": "my.ui.name" },
      { "type": "textField", "path": "sheet.damage", "labelKey": "my.ui.damage" },
      { "type": "textArea", "path": "sheet.description", "labelKey": "my.ui.description" }
    ]
  }
}
```

Supported component families:

- Layout: `tabs`, `tab`, `section`, `row`, `column`, `grid`, `divider`, `spacer`.
- Fields: `textField`, `textArea`, `numberField`, `checkboxField`,
  `checkboxTrack`, `selectField`, `resourceField`, `imageField`,
  `readonlyField`, `modifierBuilder`.
- Actions: `rollButton`, `actionButton`, `incrementButton`, `decrementButton`.
- Display: `text`, `badge`, `resourceBar`, `itemList`, `dropZone`,
  `abilityCard`, `combatStat`, `resourceBox`, `rollableStat`.

## Creating items

To create a new item type:

1. Add an entry to `provides.itemTypes`.
2. Point it at a schema and an item sheet.
3. Add content pack entries with `type` equal to the item type id.
4. Add actor sheet drop zones if actors can hold that item.

Content pack entries for items use:

```json
{
  "id": "my-weapons",
  "type": "item_pack",
  "entries": [
    {
      "id": "iron-sword",
      "type": "weapon",
      "name": "Iron Sword",
      "data": {
        "damage": "1d8",
        "description": "A plain sword."
      }
    }
  ]
}
```

`data` is merged over schema defaults and stored as the item's `sheet` data.

## Actor inventories and drag/drop

Actor sheets use `itemList` and `dropZone` to accept dropped content or items.
The `accepts` list matches either the full drop type (`item.weapon`) or its
suffix (`weapon`).

```json
{
  "type": "itemList",
  "path": "sheet.weapons",
  "columns": [
    { "path": "name", "labelKey": "my.ui.name" },
    { "path": "data.damage", "labelKey": "my.ui.damage" }
  ],
  "dropZone": {
    "id": "weapons",
    "accepts": ["item.weapon", "weapon"],
    "onDrop": "weapons.addWeapon"
  },
  "row": {
    "type": "weaponRow",
    "actions": [
      { "type": "itemAction", "action": "weapon.attack", "labelKey": "my.ui.attack" },
      { "type": "removeAction", "labelKey": "my.ui.remove" }
    ]
  }
}
```

Drops copy the item into the actor data at `path`; the copy is editable and keeps
source metadata for traceability.

## Derived fields and formulas

Formula helpers live in `rules/formulas.gw.json`:

```json
{
  "helpers": {
    "abilityMod": {
      "args": ["score"],
      "expression": "floor((score - 10) / 2)"
    }
  }
}
```

Derived rules live in `rules/derived.gw.json` and are grouped by actor type:

```json
{
  "derived": {
    "character": {
      "sheet.str.mod": "abilityMod(@sheet.str.score)",
      "sheet.init": "@sheet.dex.mod"
    }
  }
}
```

Derived expressions are deterministic and must not roll dice. They may reference
`@sheet.*`, `@core.*`, and helpers.

## Validation

Validation rules clamp writable numeric paths. Keys may include the leading
`sheet.` prefix.

```json
{
  "validation": {
    "character": {
      "sheet.level": { "min": 1, "max": 20 },
      "sheet.hp.value": { "min": 0 }
    }
  }
}
```

Schema `readOnly: true` fields reject writes.

## Actions and rolls

Sheet interactions and row actions target action ids from `rules/actions.gw.json`.

```json
{
  "actions": {
    "weapon.attack": {
      "type": "roll",
      "label": "my.ui.attack",
      "formula": "1d20 + @sheet.attack_bonus",
      "visibility": "public",
      "chatCard": "attack"
    }
  }
}
```

Roll dialogs can request user input with field types such as `boolean`,
`number`, `text`, `select`, `segmented`, `radio`, `dice`, `diceList`, `formula`,
and `visibility`.

## Token mappings

Token mappings tell the table which actor fields drive token UI:

```json
{
  "character": {
    "name": "core.name",
    "bars": {
      "hp": {
        "value": "sheet.hp.value",
        "max": "sheet.hp.max"
      }
    },
    "initiative": "sheet.init",
    "defense": "sheet.ac"
  }
}
```

## Locales

Every `labelKey` resolves through locale catalogs:

```json
{
  "my.ui.character": "Character",
  "my.ui.weapon": "Weapon",
  "my.ui.name": "Name"
}
```

Prefer `labelKey` over hard-coded `label` for packages intended to ship in more
than one language.

## Assets packages

An `assets` package declares reusable media under `provides.assets`:

```json
{
  "kind": "assets",
  "capabilities": ["assets.pack", "assets.images", "assets.maps"],
  "provides": {
    "assets": {
      "images": [
        { "id": "portrait-1", "label": "Portrait 1", "path": "assets/portrait-1.webp" }
      ],
      "maps": [
        { "id": "forest-road", "label": "Forest Road", "path": "assets/forest-road.webp" }
      ]
    }
  }
}
```

Asset entries need `id`, `label`, and package-relative `path`. An `assets`
package must not define actor types, item types, rules, or storage.

## Complete example source

Scaffold a ruleset to generate a full working reference, then inspect the
generated tree:

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
```

- `data/packages/rulesets/my-rpg/manifest.json`
- `data/packages/rulesets/my-rpg/schemas/`
- `data/packages/rulesets/my-rpg/layouts/`
- `data/packages/rulesets/my-rpg/rules/`
- `data/packages/rulesets/my-rpg/mappings/`
- `data/packages/rulesets/my-rpg/content/`
- `data/packages/rulesets/my-rpg/locales/`
