# System API v1: Sheets

Fichas e itens usam layouts declarativos em JSON. Cada `actorType` ou `itemType` aponta para um schema de dados e um layout:

```json
{
  "id": "character",
  "label": "Personagem",
  "schema": "schemas/character.schema.json",
  "sheet": "layouts/character.sheet.gw.json"
}
```

O layout declara uma arvore de componentes:

```json
{
  "kind": "actorSheet",
  "system": "dnd5e",
  "actorType": "character",
  "id": "dnd5e-character",
  "body": {
    "type": "tabs",
    "tabs": [
      {
        "id": "main",
        "icon": "squares-four",
        "children": []
      }
    ]
  }
}
```

Componentes podem apontar para dados com `bind`, `path`, `scorePath`, `modPath` e campos equivalentes. Interacoes podem chamar actions declaradas em `rules/actions.gw.json`.

CSS do sistema deve vir por `system.assets.styles`. JS do sistema deve usar apenas APIs publicas, como `window.GravewrightSheets.registerSystem(...)`, evitando depender de DOM privado do renderer.
