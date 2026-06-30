# Tutorial: do zero a um ruleset mínimo funcionando

Este passo a passo constrói um ruleset real do zero: um tipo de ator, um tipo de item,
uma ficha declarativa, uma fórmula de regra e locales. O pacote final é distribuído como
[`examples/packages/my-rpg`](../../../examples/packages/my-rpg) e é validado no CI.

Um `ruleset` define as regras base de jogo de uma campanha. Seu modo de ativação é
`exclusive`: uma campanha tem exatamente um ruleset ativo.

## Pré-requisitos

- Um checkout funcional do Gravewright onde a CLI `grave` roda (veja [`inicio.md`](../inicio.md)).
- Uma campanha que você possa configurar.

## 1. Faça o scaffold do pacote

```bash
grave ruleset new my-rpg --name "My RPG" --sheets
```

Isto cria o pacote em `data/packages/rulesets/my-rpg/`. O layout alvo deste tutorial é:

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

## 2. Declare o manifesto

Um manifesto de ruleset deve usar `activation.mode: "exclusive"`, declarar um modelo de
storage e declarar ao menos um tipo de ator. `provides` conecta os tipos de ator/item aos
seus arquivos de schema, ficha e regra:

```json
{
  "kind": "ruleset",
  "id": "my-rpg",
  "name": "My RPG",
  "compatibility": { "minimum": "1", "verified": "1" },
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

Todo caminho em `provides` deve existir em disco, ou a validação falha com `file_missing`.

## 3. Defina o formato dos dados

`schemas/character.schema.json` descreve os dados de ator armazenados:

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

## 4. Monte a ficha

`layouts/character.sheet.gw.json` é uma ficha declarativa ligada aos dados do ator:

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

Forneça `layouts/item.sheet.gw.json` da mesma forma para o tipo de item. Veja
[`declarative-model.md`](declarative-model.md).

## 5. Adicione uma regra e locales

`rules/formulas.gw.json` declara fórmulas helper reutilizáveis:

```json
{
  "helpers": {
    "strengthMod": { "args": ["score"], "expression": "floor((score - 10) / 2)" }
  }
}
```

`locales/en.json` fornece as chaves de label referenciadas pelo manifesto e pela ficha:

```json
{
  "my-rpg.actor.character": "Character",
  "my-rpg.item.item": "Item",
  "my-rpg.field.level": "Level",
  "my-rpg.field.strength": "Strength"
}
```

## 6. Valide

```bash
grave package validate data/packages/rulesets/my-rpg
```

Esperado:

```text
my-rpg: ok
```

## 7. Instale, habilite e ative para uma campanha

```bash
grave package install my-rpg --yes --enable
```

Um ruleset é **exclusive**, então ele não é ativado com `grave campaign package activate`.
Em vez disso, escolha **My RPG** como o ruleset da campanha ao criar ou editar a campanha
no app Gravewright — ele se torna o ruleset ativo autoritativo da campanha.

## 8. Veja funcionando

Abra a campanha e crie um ator do tipo `character`. A ficha declarativa de personagem
renderiza com os campos Level e Strength que você definiu, lastreados pelos defaults do
schema.

## 9. Depure quando algo estiver errado

```bash
grave package doctor my-rpg
```

## Próximos passos

- Adicione rolagens, combate e conteúdo ao ruleset (`grave ruleset new ... --rolls --combat --content`).
- Construa um addon por cima: [`tutorial-addon.md`](tutorial-addon.md).
- Mapeie objetivos para campos do manifesto e capabilities: [`power-map.md`](power-map.md).
