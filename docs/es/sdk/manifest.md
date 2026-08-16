# Manifest de packages de SDK 1

El schema canónico es `gravewright-package-v1.schema.json` y también está
incorporado como `manifestSchema` en
[`gravewright-sdk-1.json`](../../sdk/_data/gravewright-sdk-1.json). Los
identifiers, enum values y JSON keys no se traducen.

Todo package declara `schemaVersion`, `sdkVersion`, `kind`, `id`, `name`,
`version`, `compatibility`, `capabilities`, `activation`, `entrypoints` y
`provides`. Para SDK 1, use `sdkVersion: "1"`. Valide el archivo con
`grave package validate ruta/del/package` antes de instalarlo.

Las capabilities son allow-listed y no reemplazan la autoridad del usuario.
Los package kinds válidos proceden exclusivamente del schema canónico.
