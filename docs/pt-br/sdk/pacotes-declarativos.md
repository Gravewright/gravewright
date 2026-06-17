# Pacotes Declarativos

A maioria dos pacotes SDK deve ser declarativa: o manifest aponta para arquivos
JSON que descrevem dados, fichas, regras, conteúdo, locales, assets e mappings.
Use JavaScript apenas quando o pacote precisar de comportamento de navegador que
o modelo declarativo não expressa.

## Ordem de criação

1. Escolha o `kind` do pacote.
2. Declare `actorTypes` e `itemTypes` no `manifest.json`.
3. Crie JSON Schemas para cada tipo.
4. Crie fichas declarativas para cada tipo.
5. Adicione rules, validation, token mappings e content packs quando necessário.
6. Adicione locales para cada `labelKey`.
7. Rode `grave package validate <path>` e `grave package doctor <id>`.

## Ligação no manifest

Um ruleset declara o modelo de jogo em `provides`:

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

Os ids em `actorTypes[].id` e `itemTypes[].id` são os nomes usados por actors,
items, content packs, fichas, drops, rules e mappings.

## Modelo de dados com JSON Schema

Dados de actor e item vivem no namespace `sheet`. O schema descreve esses dados
sem o prefixo `sheet.`. Defaults criam a árvore inicial quando um registro é
criado ou importado.

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

Paths em fichas e regras usam `sheet.hp.value`; propriedades de schema usam
`hp.value`. `core.name` é metadado embutido, não parte do schema da ficha.

## Fichas declarativas

Um arquivo de ficha é uma árvore JSON. Fichas de actor usam `kind:
"actorSheet"`; fichas de item usam `kind: "itemSheet"`. Todo campo editável
escreve em `core.*` ou `sheet.*`.

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

Famílias de componentes suportadas:

- Layout: `tabs`, `tab`, `section`, `row`, `column`, `grid`, `divider`, `spacer`.
- Campos: `textField`, `textArea`, `numberField`, `checkboxField`,
  `checkboxTrack`, `selectField`, `resourceField`, `imageField`,
  `readonlyField`, `modifierBuilder`.
- Ações: `rollButton`, `actionButton`, `incrementButton`, `decrementButton`.
- Display: `text`, `badge`, `resourceBar`, `itemList`, `dropZone`,
  `abilityCard`, `combatStat`, `resourceBox`, `rollableStat`.

## Criando itens

Para criar um novo tipo de item:

1. Adicione uma entrada em `provides.itemTypes`.
2. Aponte essa entrada para um schema e uma ficha de item.
3. Adicione entradas em content packs com `type` igual ao id do tipo de item.
4. Adicione drop zones em fichas de actor se actors puderem carregar esse item.

Entradas de content pack para itens usam:

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

`data` é mesclado sobre os defaults do schema e armazenado como dados `sheet`
do item.

## Inventário de actor e drag/drop

Fichas de actor usam `itemList` e `dropZone` para aceitar conteúdo ou itens
arrastados. A lista `accepts` casa tanto o tipo completo (`item.weapon`) quanto
o sufixo (`weapon`).

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

Drops copiam o item para os dados do actor em `path`; a cópia é editável e
mantém metadados de origem para rastreabilidade.

## Campos derivados e fórmulas

Helpers de fórmula ficam em `rules/formulas.gw.json`:

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

Regras derivadas ficam em `rules/derived.gw.json` e são agrupadas por actor type:

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

Expressões derivadas são determinísticas e não devem rolar dados. Elas podem
referenciar `@sheet.*`, `@core.*` e helpers.

## Validation

Regras de validation limitam paths numéricos graváveis. Chaves podem incluir o
prefixo `sheet.`.

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

Campos de schema com `readOnly: true` rejeitam escrita.

## Actions e rolagens

Interações de ficha e ações de linha apontam para ids em `rules/actions.gw.json`.

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

Diálogos de rolagem podem pedir input com tipos como `boolean`, `number`,
`text`, `select`, `segmented`, `radio`, `dice`, `diceList`, `formula` e
`visibility`.

## Token mappings

Token mappings dizem à mesa quais campos do actor alimentam a UI do token:

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

Todo `labelKey` resolve por catálogos de locale:

```json
{
  "my.ui.character": "Personagem",
  "my.ui.weapon": "Arma",
  "my.ui.name": "Nome"
}
```

Prefira `labelKey` a `label` fixo para pacotes que devem existir em mais de um
idioma.

## Pacotes de assets

Um pacote `assets` declara mídia reutilizável em `provides.assets`:

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

Entradas de asset precisam de `id`, `label` e `path` relativo ao pacote. Um
pacote `assets` não pode definir actor types, item types, rules ou storage.

## Exemplo completo

Faça o scaffold de um ruleset para gerar uma referência funcional completa e
então inspecione a árvore gerada:

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
