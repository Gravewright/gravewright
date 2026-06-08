# System API v1: Manifest

O `manifest.json` e o ponto de entrada de um sistema Gravewright. Ele declara identidade, compatibilidade, capabilities, tipos de atores/itens, assets e arquivos de regras. O manifest nao executa codigo; ele apenas autoriza o que o Gravewright deve carregar.

Use o schema publico:

```json
{
  "$schema": "https://gravewright.dev/schemas/system-manifest-v1.json",
  "manifestVersion": 1,
  "type": "system",
  "id": "dnd5e",
  "name": "Dungeons & Dragons 5e",
  "version": "0.3.0",
  "apiVersion": "1"
}
```

Campos principais:

- `id`: slug estavel em minusculas, usado em URLs e storage.
- `apiVersion`: deve ser `"1"` para System API v1.
- `compatibility`: limites de versao do Gravewright aceitos pelo pacote.
- `capabilities`: declara os recursos usados pelo sistema. Capabilities desconhecidas ou proibidas tornam o pacote invalido.
- `system.actorTypes` e `system.itemTypes`: registram entidades e apontam para schema/layout.
- `system.assets.styles`: CSS carregado na mesa para fichas, itens e tracker.
- `system.assets.scripts`: JS carregado depois das APIs publicas `window.GravewrightSheets` e `window.GravewrightCombat`.
- `system.rules`: arquivos declarativos de formulas, acoes, derivados, validacao e combate.
- `system.contentPacks`: packs opcionais de atores, itens, journals, tabelas e condicoes.

Capabilities v1 aceitas:

`actors.register`, `items.register`, `sheets.declarative`, `rules.declarative`, `content.packs`, `tokens.mappings`, `dice.roll`, `chat.cards`, `roll.toast`, `locales`, `assets.ui`, `assets.styles`, `assets.scripts`, `combat.config`, `combat.hooks`, `rolls.intent`.

Paths devem ser relativos ao pacote. Paths absolutos, URLs e traversal com `..` sao rejeitados.
