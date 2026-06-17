# Conteúdo e assets

A SDK separa conteúdo importável de mídia reutilizável.

## Content packs

Use `content`/`provides.contentPacks` para dados que o usuário pode importar, como encontros, actors, itens, cenas, compêndios ou material de aventura.

```json
"capabilities": ["content.packs"],
"provides": {
  "contentPacks": [
    {
      "id": "encounters",
      "label": "Starter Encounters",
      "path": "content/encounters.json",
      "type": "encounter"
    }
  ]
}
```

## Asset packs

Use `assets`/`provides.assets` para mídia reutilizável.

```json
"capabilities": ["assets.pack", "assets.images", "assets.maps"],
"provides": {
  "assets": [
    { "id": "forest", "type": "map", "path": "assets/maps/forest.webp", "label": "Forest Map" }
  ]
}
```

## Paths seguros

- Relativos ao pacote.
- Sem `..`.
- Sem path absoluto.
- Sem arquivos fora de `data/packages/{kind_plural}/{id}/`.
- Com extensão compatível com o tipo declarado.

## Runtime

Content e assets devem ser usáveis sem JavaScript. Use `sdk.content` apenas para leitura/integração em runtime.

```js
const packs = sdk.content.packs();
const encounters = sdk.content.pack("encounters");
```
