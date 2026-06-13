# Creating a System

> [!WARNING]
> **System API v1 is Alpha.**
>
> Systems are the most sensitive extension surface in Gravewright because they define schema, sheets, rules, rolls, packs, token mappings, labels, and combat behavior.
>
> Alpha releases may change fields or behavior. Test custom systems in one-shots and test environments before trusting long campaigns to them.

A **system** is a declarative package that teaches Gravewright how to understand a specific game: which actor types exist, which item types exist, what data shape each entity uses, how sheets render, which rolls exist, how initiative works, which labels should be shown, and which starter content can be imported.

Systems are not arbitrary backend plugins.

The server reads and validates declarative files. System JavaScript, when used, runs in the browser and must use documented public APIs only.

## When to Create a System

Create a system when you need to define the structural rules of a game:

- actor types such as `character`, `monster`, `npc`, or `vehicle`;
- item types such as `weapon`, `armor`, `spell`, or `feat`;
- declarative actor and item sheets;
- derived data, formulas, rolls, and actions;
- mappings between sheet data and tokens;
- combat configuration, initiative, and resources;
- ruleset vocabulary and UI labels;
- locale files;
- content packs that belong to the system.

Do not create a system for small visual improvements, optional automation, or behavior that should be enabled or disabled per campaign. Use a **module** for that.

## Mental Model

A system has four main layers:

1. **Manifest**: identity, compatibility, capabilities, and the package file map.
2. **Data**: JSON Schemas that validate actor and item data.
3. **Declarative UI**: `.sheet.gw.json` layouts that describe sheets.
4. **Rules**: `.gw.json` files for actions, formulas, derived data, combat, validation, and mappings.

Optionally, a system can also include:

- CSS for custom visuals;
- client-side JavaScript for documented extension points;
- labels;
- locales;
- content packs.

## Recommended Package Layout

```text
data/systems/my-system/
  manifest.json
  README.md
  schemas/
    character.schema.json
    monster.schema.json
    item.schema.json
  layouts/
    character.sheet.gw.json
    monster.sheet.gw.json
  items/
    weapon.sheet.gw.json
    spell.sheet.gw.json
  rules/
    actions.gw.json
    combat.gw.json
    derived.gw.json
    formulas.gw.json
    validation.gw.json
    conditions.gw.json
  mappings/
    token.gw.json
    chat-cards.gw.json
    roll-toast.gw.json
  content/
    actors.monsters.gwpack.json
    items.weapons.gwpack.json
    spells.gwpack.json
  locales/
    en.json
    pt-BR.json
  assets/
    my-system.css
    my-system.js
```

For a minimal system, you need only:

```text
data/systems/my-system/
  manifest.json
  schemas/
    character.schema.json
  layouts/
    character.sheet.gw.json
```

A useful system will usually also have:

- `rules/actions.gw.json`;
- `rules/combat.gw.json`;
- locale files;
- at least one CSS file;
- optional system JavaScript for documented sheet or combat extension points.

## Minimal Manifest

Create `manifest.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-manifest-v1.json",
  "manifestVersion": 1,
  "type": "system",
  "id": "my-system",
  "name": "My System",
  "description": "Example Gravewright system.",
  "version": "0.1.0",
  "apiVersion": "1",
  "authors": [
    {
      "name": "Your Name"
    }
  ],
  "license": "MIT",
  "compatibility": {
    "minimum": "1.0.0-rc.1",
    "verified": "1.0.0-rc.1",
    "maximum": "1.x"
  },
  "display": {
    "color": "#7c5cff"
  },
  "capabilities": [
    "actors.register",
    "sheets.declarative",
    "rules.declarative",
    "dice.roll"
  ],
  "system": {
    "id": "my-system",
    "storage": {
      "model": "scoped-json-v1"
    },
    "actorTypes": [
      {
        "id": "character",
        "label": "Character",
        "schema": "schemas/character.schema.json",
        "sheet": "layouts/character.sheet.gw.json"
      }
    ],
    "itemTypes": [],
    "rules": {
      "actions": "rules/actions.gw.json"
    }
  },
  "dependencies": [],
  "conflicts": []
}
```

Important rules:

- `manifestVersion` must be `1`;
- `type` must be `"system"`;
- `apiVersion` must be `"1"`;
- top-level `id` and `system.id` must match;
- IDs use lowercase kebab-case, such as `my-system`;
- `system.storage.model` must be `"scoped-json-v1"`;
- package paths must be relative to the package root;
- URLs, absolute paths, `..`, and files outside the package are rejected;
- declare only capabilities that correspond to files or APIs you actually use.

## Capabilities

Capabilities describe what the system provides.

| Capability | Use when the system... |
|---|---|
| `actors.register` | declares actor types |
| `items.register` | declares item types |
| `sheets.declarative` | provides declarative sheet layouts |
| `rules.declarative` | provides rule files |
| `content.packs` | provides content packs |
| `tokens.mappings` | maps actor/item data to tokens |
| `dice.roll` | declares roll actions |
| `chat.cards` | customizes chat cards |
| `roll.toast` | customizes roll toasts |
| `locales` | provides locale files |
| `assets.ui` | contributes UI behavior |
| `assets.styles` | contributes CSS |
| `assets.scripts` | contributes JavaScript |
| `combat.config` | provides combat configuration |
| `combat.hooks` | registers combat client hooks |
| `rolls.intent` | uses semantic roll intents |

Capabilities are not just decoration.

They are documentation for users and maintainers, and they allow the backend/runtime to reject unsupported behavior.

## Creating the First Actor Schema

Create `schemas/character.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "My System Character",
  "type": "object",
  "additionalProperties": true,
  "properties": {
    "attributes": {
      "type": "object",
      "properties": {
        "strength": {
          "type": "integer",
          "default": 10
        },
        "dexterity": {
          "type": "integer",
          "default": 10
        },
        "strengthMod": {
          "type": "integer",
          "default": 0
        },
        "dexterityMod": {
          "type": "integer",
          "default": 0
        }
      }
    },
    "combat": {
      "type": "object",
      "properties": {
        "hp": {
          "type": "integer",
          "default": 10
        },
        "maxHp": {
          "type": "integer",
          "default": 10
        },
        "initiative": {
          "type": "integer",
          "default": 0
        }
      }
    }
  }
}
```

Gravewright stores core actor metadata separately from system sheet data.

In layouts and rules you normally refer to system data through paths such as:

```text
sheet.attributes.strength
sheet.combat.hp
sheet.combat.maxHp
```

Good practice: keep schemas stable and predictable.

During Alpha, schema changes may make old tables difficult to recover.

## Creating the First Sheet

Create `layouts/character.sheet.gw.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-layout-v1.json",
  "kind": "actorSheet",
  "system": "my-system",
  "actorType": "character",
  "id": "my-system-character",
  "title": {
    "bind": "core.name"
  },
  "body": {
    "type": "tabs",
    "tabs": [
      {
        "type": "tab",
        "id": "main",
        "label": "Main",
        "icon": "user",
        "children": [
          {
            "type": "section",
            "label": "Attributes",
            "children": [
              {
                "type": "grid",
                "columns": 2,
                "children": [
                  {
                    "type": "abilityCard",
                    "label": "Strength",
                    "abbr": "STR",
                    "scorePath": "sheet.attributes.strength",
                    "modPath": "sheet.attributes.strengthMod",
                    "rollAction": "roll.strength"
                  },
                  {
                    "type": "abilityCard",
                    "label": "Dexterity",
                    "abbr": "DEX",
                    "scorePath": "sheet.attributes.dexterity",
                    "modPath": "sheet.attributes.dexterityMod",
                    "rollAction": "roll.dexterity"
                  }
                ]
              }
            ]
          },
          {
            "type": "section",
            "label": "Combat",
            "children": [
              {
                "type": "resourceBar",
                "valuePath": "sheet.combat.hp",
                "maxPath": "sheet.combat.maxHp"
              },
              {
                "type": "combatStat",
                "label": "Initiative",
                "abbr": "INI",
                "valuePath": "sheet.combat.initiative",
                "signed": true,
                "rollAction": "roll.initiative"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

Useful layout nodes:

| Type | Use |
|---|---|
| `tabs` | tabbed container |
| `section` | visual block with a title |
| `row` | flexible row |
| `grid` | grid; accepts `columns` |
| `column` | column |
| `divider` | visual separator |
| `spacer` | visual space |
| `abilityCard` | ability with score, modifier, and roll |
| `rollableStat` | clickable stat row |
| `combatStat` | combat statistic |
| `resourceBar` | value/max resource bar |
| `imageField` | readonly image |
| `readonlyField` | readonly value |
| `text` | plain text |
| `badge` | short label/badge |
| `itemList` | linked item list/table |
| `rollButton` | roll button |
| `actionButton` | action button |
| `incrementButton` | increment button |
| `decrementButton` | decrement button |

Not every field is fully locked down in JSON Schema yet.

Alpha allows additional properties so the renderer can evolve. Document any custom node or variant your system depends on.

## Creating Actions and Rolls

Create `rules/actions.gw.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-actions-v1.json",
  "actions": {
    "roll.strength": {
      "type": "roll",
      "label": "Strength Check",
      "intent": "check",
      "formula": "1d20 + @sheet.attributes.strengthMod",
      "visibility": "public",
      "chatCard": "check"
    },
    "roll.dexterity": {
      "type": "roll",
      "label": "Dexterity Check",
      "intent": "check",
      "formula": "1d20 + @sheet.attributes.dexterityMod",
      "visibility": "public",
      "chatCard": "check"
    },
    "roll.initiative": {
      "type": "roll",
      "label": "Initiative",
      "intent": "initiative",
      "formula": "1d20 + @sheet.combat.initiative",
      "visibility": "public",
      "chatCard": "initiative"
    }
  }
}
```

Intent values in v1:

| Intent | Meaning |
|---|---|
| `check` | generic check |
| `save` | saving throw/resistance |
| `attack` | attack |
| `damage` | damage |
| `initiative` | initiative |
| `skill` | skill |
| `tool` | tool |
| `custom` | system-specific case |

Use `intent` for semantics, not appearance.

Appearance should be controlled through `chatCard`, `rollToast`, CSS, and mappings.

## Configuring Combat

Create `rules/combat.gw.json`:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-combat-v1.json",
  "version": 1,
  "defaultMode": "encounter",
  "turnOrder": {
    "strategy": "formula_sort",
    "label": "Initiative",
    "formula": "@sheet.combat.initiative",
    "sort": "desc",
    "tieBreakers": ["name"]
  },
  "resources": {
    "hp": {
      "label": "HP",
      "path": "sheet.combat.hp",
      "maxPath": "sheet.combat.maxHp",
      "min": 0
    }
  },
  "activityTypes": [
    {
      "id": "action",
      "label": "Action"
    },
    {
      "id": "bonus",
      "label": "Bonus Action"
    },
    {
      "id": "reaction",
      "label": "Reaction"
    }
  ]
}
```

Use `combat.config` in the capabilities list when declaring this file.

Combat UI text should come from system-owned combat configuration, labels, or locale files when the default engine text is not appropriate for the system.

## Mapping Tokens

If your system uses tokens with HP, names, portraits, or derived states, declare a mapping:

```json
{
  "version": 1,
  "token": {
    "name": "core.name",
    "hp": "sheet.combat.hp",
    "maxHp": "sheet.combat.maxHp",
    "initiative": "sheet.combat.initiative"
  }
}
```

Reference it in the manifest:

```json
{
  "system": {
    "mappings": {
      "tokens": "mappings/token.gw.json"
    }
  }
}
```

Use the `tokens.mappings` capability.

## Adding Assets

In the manifest:

```json
{
  "capabilities": ["assets.ui", "assets.styles", "assets.scripts"],
  "system": {
    "assets": {
      "styles": ["assets/my-system.css"],
      "scripts": ["assets/my-system.js"]
    }
  }
}
```

CSS is the preferred path for visual customization.

JavaScript should be reserved for documented behavior that declarative sheets and rules cannot express yet.

## Providing System UI Labels

Systems can provide UI labels for sheet rendering through their browser asset.

Register labels in `assets/my-system.js`:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("my-system", {
    labels: {
      actorName: "Name",
      levelPrefix: "Level",
      equipped: "Equipped",
      spellCirclePrefix: "Circle",
      prepared: "Prepared",
      active: "Active",
      inactive: "Inactive",
      qtyPrefix: "Qty",
      portrait: "Portrait",
      token: "Token",
      uploadPortrait: "Upload portrait",
      uploadToken: "Upload token",
      cancel: "Cancel",
      roll: "Roll",
      rollDialogTitle: "Roll",
      healed: "healed",
      tookDamage: "took",
      reducedFrom: "reduced from"
    }
  });
})();
```

Use labels for ruleset vocabulary and language-specific text that the engine cannot know safely.

The engine provides English fallbacks, but public systems should define their own labels when distributing a non-English or ruleset-specific experience.

## Adding Sheet Hooks

Example system JavaScript:

```js
(function () {
  const Sheets = window.GravewrightSheets;
  if (!Sheets || typeof Sheets.registerSystem !== "function") return;

  Sheets.registerSystem("my-system", {
    renderSection(node, variant, renderContext, helpers) {
      if (variant !== "special") return null;

      const section = helpers.el("section", "my-system-special");
      section.appendChild(helpers.el("h3", null, node.label || "Special"));
      return section;
    },

    renderHeaderIdentity(main, bundle, helpers) {
      const actor = bundle.actor || {};
      main.appendChild(helpers.el("div", "my-system-subtitle", actor.type || ""));
    },

    autoFitWidth(actorType) {
      if (actorType === "character") return 820;
      return null;
    }
  });
})();
```

Browser APIs available to systems:

- `window.GravewrightSheets.registerSystem(systemId, hooks)`;
- `window.GravewrightSheets.helpers`;
- `window.GravewrightSheets.getLabels(systemId)`;
- `window.GravewrightCombat.registerSystem(systemId, plugin)`.

Avoid internal variables, private stores, undocumented DOM structure, fallback behavior, and renderer internals.

## Adding Combat Hooks and Slots

Systems can register lightweight combat hooks and slots:

```js
(function () {
  const Combat = window.GravewrightCombat;
  if (!Combat || typeof Combat.registerSystem !== "function") return;

  Combat.registerSystem("my-system", {
    hooks: {
      participantMeta({ participant }) {
        return participant?.actor_type || "";
      }
    },

    slots: {
      participantActions({ participant }) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "my-system-combat-action";
        button.textContent = participant?.actor_type || "Action";
        return button;
      }
    }
  });
})();
```

Prefer combat configuration, CSS, labels, hooks, and slots over replacing the entire combat renderer.

Full combat renderer replacement is not part of the stable public API during Alpha.

## Localization

In the manifest:

```json
{
  "capabilities": ["locales"],
  "system": {
    "locales": {
      "en": "locales/en.json",
      "pt-BR": "locales/pt-BR.json"
    }
  }
}
```

Example `locales/en.json`:

```json
{
  "MY_SYSTEM.Character": "Character",
  "MY_SYSTEM.Strength": "Strength",
  "MY_SYSTEM.Initiative": "Initiative"
}
```

Prefer `labelKey` in layouts, manifests, rules, and content packs when text needs to be translated.

## Adding Content Packs

In the manifest:

```json
{
  "capabilities": ["content.packs"],
  "system": {
    "contentPacks": [
      {
        "id": "starter-weapons",
        "type": "item_pack",
        "label": "Starter Weapons",
        "path": "content/items.weapons.gwpack.json"
      }
    ]
  }
}
```

Accepted pack types:

- `actor_pack`;
- `item_pack`;
- `spell_pack`;
- `journal_pack`;
- `table_pack`;
- `condition_pack`.

A pack must use the same data model that the system schemas expect.

## Validation Checklist

Before distributing:

```bash
python3 -m json.tool data/systems/my-system/manifest.json > /dev/null
python3 -m json.tool data/systems/my-system/layouts/character.sheet.gw.json > /dev/null
python3 -m json.tool data/systems/my-system/rules/actions.gw.json > /dev/null
uv run pytest tests/unit/test_system_manifest.py tests/unit/test_system_install_service.py
```

Verify also:

- `id` and `system.id` match;
- every declared path exists;
- there are no absolute paths, URLs, or `..` segments;
- all required capabilities are declared;
- no runtime file, database, cache, or private data entered the package;
- the system installs through the Systems screen;
- a new campaign can select the system;
- new actors and items open their sheets without error;
- labels render correctly;
- rolls appear in chat;
- combat works with the expected initiative logic.

## Common Errors

| Error | Likely cause | Fix |
|---|---|---|
| Manifest invalid | Wrong `manifestVersion`, `type`, `apiVersion`, or `compatibility` fields | Compare with the minimal manifest |
| Path rejected | Absolute path, URL, `..`, or missing file | Use package-relative paths |
| Asset does not load | Missing `assets.styles` or `assets.scripts` capability | Declare the correct capability |
| Sheet opens empty | `actorType` does not match the registered actor type | Check `actorTypes` and layout metadata |
| Roll button does nothing | `rollAction` does not exist in `rules/actions.gw.json` | Create the action or fix the id |
| Token does not show resource | Missing mapping or wrong path | Review `mappings/token.gw.json` |
| Labels do not appear | System script did not load or labels were not registered | Check `assets.scripts`, capabilities, and `window.GravewrightSheets.registerSystem` |
| System breaks an old table | Schema changed without migration | During Alpha, clearly mark breaking changes |

## Distribution

To distribute a system:

```text
my-system.zip
  manifest.json
  schemas/
  layouts/
  rules/
  mappings/
  content/
  locales/
  assets/
  README.md
```

Do not include:

- `.env`;
- SQLite databases;
- `storage/`;
- `__pycache__/`;
- `.pyc`;
- logs;
- real campaign data;
- unlicensed assets.

## README for a Public System

A system package should include a `README.md` with:

- supported Gravewright version;
- game/license notes;
- actor and item types;
- sheet features;
- supported rolls and combat behavior;
- labels/locales included;
- content packs included;
- known Alpha limitations;
- migration warnings for breaking schema changes.