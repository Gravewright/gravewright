# System API v1: Content Packs

Packs adicionam conteudo inicial ao sistema sem misturar dados oficiais ao core da aplicacao. Eles sao declarados no manifest:

```json
{
  "system": {
    "contentPacks": [
      {
        "id": "starter-monsters",
        "type": "actor_pack",
        "label": "Monstros iniciais",
        "path": "packs/starter-monsters.json"
      }
    ]
  }
}
```

Tipos aceitos:

- `actor_pack`
- `item_pack`
- `spell_pack`
- `journal_pack`
- `table_pack`
- `condition_pack`

Cada entrada deve usar `id`, `type`, `label` e `path`. O path deve ser relativo ao pacote. O conteudo do pack deve usar o mesmo modelo de dados dos schemas declarados pelo sistema.
