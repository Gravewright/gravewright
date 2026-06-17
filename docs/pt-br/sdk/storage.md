# Storage Gerenciado (`storage.sqlite`)

> **Status: stable.** `storage.sqlite` e `sdk.storage.sqlite.*` fazem parte do
> contrato LTS da SDK 1. O Gravewright controla paths, lifecycle, permissoes,
> migrations, limites de runtime e backup.

## Declarando Storage

```json
{
  "capabilities": ["storage.sqlite"],
  "storage": {
    "sqlite": {
      "status": "stable",
      "location": "gravewright-managed",
      "scopes": ["campaign", "global"],
      "migrations": "storage/sqlite/migrations",
      "queries": "storage/sqlite/queries.json",
      "maxSizeMB": 50,
      "backup": true
    }
  }
}
```

- A capability e o bloco `storage.sqlite` sao obrigatorios juntos
  (`sdk.storage.capability_missing` / `sdk.storage.declaration_invalid`).
- `scopes` deve conter apenas `campaign` e/ou `global`.
- `migrations` e `queries` devem ser paths seguros, relativos ao pacote, e
  existir no disco.
- O runtime revalida `queries.json` no momento da execucao.

## Runtime

```ts
await sdk.storage.sqlite.execute("campaign", "saveState", {
  key: "panel-state",
  value_json: JSON.stringify(state),
});

const rows = await sdk.storage.sqlite.query("campaign", "getState", {
  key: "panel-state",
});

const info = await sdk.storage.sqlite.status("campaign");
```

O backend e a autoridade. Ele resolve o pacote ativo, verifica a capability,
confere permissoes por escopo, aplica migrations pendentes, carrega named
queries do pacote validado no disco e executa SQL com parametros bindados. Nao
existe `sdk.storage.sqlite.raw` e nenhum path absoluto e exposto ao pacote.

## Named Queries

```json
{
  "queries": {
    "getState": {
      "type": "read",
      "params": { "key": "string" },
      "sql": "SELECT value_json FROM addon_state WHERE key = :key LIMIT 1"
    },
    "saveState": {
      "type": "write",
      "params": {
        "key": "string",
        "value_json": "json-string",
        "updated_at": "integer"
      },
      "sql": "INSERT INTO addon_state (key, value_json, updated_at) VALUES (:key, :value_json, :updated_at)"
    }
  }
}
```

Regras principais:

- Cada query declara `type`, `params` e um unico statement `sql`.
- `read` deve comecar com `SELECT` ou `WITH`; `write` com `INSERT`, `UPDATE` ou
  `DELETE`.
- Multiplos statements, `ATTACH`, `PRAGMA` e `VACUUM` sao rejeitados
  (`sdk.storage.sqlite.query_sql_disallowed`).
- Parametros ausentes, extras ou de tipo incorreto sao rejeitados.

## Limites

O runtime aplica limite de tamanho do banco (padrão 50 MB, configurável via
`maxSizeMB` — um número positivo até 1024; o validador de manifest rejeita
valores inválidos ou fora do intervalo com `sdk.storage.max_size_invalid` /
`sdk.storage.max_size_too_large`), timeout de query, limite de linhas
retornadas e limite de bytes de resposta. Migrations possuem estado persistido e
hash SHA-256; uma migration aplicada com conteudo alterado ou estado dirty e
reportada pelo doctor.
Storage sem pacote instalado e reportado como `sdk.storage.orphaned_storage`.

## Backup

Backups com `include_packages` incluem tanto `data/packages/...` quanto
`data/storage/packages/...`. Export/publicacao de pacote inclui apenas o
diretorio do pacote, nao bancos gerenciados.
