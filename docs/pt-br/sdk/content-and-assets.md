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
      "path": "content/encounters.gwpack.json",
      "type": "journal_pack",
      "documentType": "journal",
      "formatVersion": 2,
      "indexFields": ["id", "name", "type", "tags"]
    }
  ]
}
```

Novos packages usam content packs v2. O arquivo do pack contém um array
`index`; cada entrada fornece o documento inline em `document` ou aponta para
um caminho relativo em `document`. `documentType` define o domínio estável e
`indexFields` limita os dados de resumo. O formato 1 com `entries` continua
legível por compatibilidade, mas não é emitido pelo scaffold atual.

Tipos suportados: `actor_pack`, `item_pack`, `spell_pack`, `journal_pack`,
`table_pack`, `condition_pack`, `scene_pack`, `card_pack`, `deck_pack`,
`asset_pack`, `macro_pack`, `playlist_pack` e `document_pack`.

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
const packs = await sdk.content.packs();
const encounters = await sdk.content.pack("encounters");
```
