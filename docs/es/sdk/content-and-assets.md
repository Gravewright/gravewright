# Content packs v2 y assets

Los packages `content` declaran `provides.contentPacks`. El authoring actual usa
`formatVersion: 2`, `documentType`, `indexFields` y un archivo con `index`.
Cada entrada contiene `document` inline o una ruta relativa para lazy loading.
El formato 1 con `entries` permanece legible por compatibilidad, pero el
scaffold no lo emite.

```json
{
  "id": "weapons",
  "type": "item_pack",
  "documentType": "item",
  "formatVersion": 2,
  "indexFields": ["id", "name", "type", "tags"],
  "label": "Weapons",
  "path": "content/weapons.gwpack.json"
}
```

Los tipos incluyen actors, items, spells, journals, tables, conditions, scenes,
cards, decks, assets, macros, playlists y documentos genéricos. Los packages
`assets` declaran `provides.assets` para imágenes, mapas, audio e iconos. Todos
los paths son relativos al package, no admiten `..`, paths absolutos ni URLs.
