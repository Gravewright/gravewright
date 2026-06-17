# Layout de Dados da SDK — Pacotes Universais + Storage Gerenciado

> Define onde os pacotes e seu storage persistente vivem no disco. O layout
> universal agrupado `data/packages/{kind_plural}/{id}` é o único layout
> suportado, congelado pela Alpha 2.0.0 — SDK Freeze.

## Regra arquitetural

> Tudo é package. Um package vive em `data/packages/{kind_plural}/{id}`. Seu
> storage vive em `data/storage/packages/{kind_plural}/{id}`.

Mapeamento `kind_plural`:

| `manifest.kind` | `kind_plural` |
|---|---|
| `addon` | `addons` |
| `ruleset` | `rulesets` |
| `library` | `libraries` |
| `theme` | `themes` |
| `content` | `content` |
| `assets` | `assets` |

> Observação: `content` e `assets` já são plurais como escritos; seu diretório é
> igual ao kind.

## Layout atual (universal agrupado)

```text
data/
  packages/
    addons/{id}/
    rulesets/{id}/
    libraries/{id}/
    themes/{id}/
    content/{id}/
    assets/{id}/

  storage/
    packages/
      addons/{id}/
        global/data.sqlite3
        campaigns/{campaign_id}/data.sqlite3
      rulesets/{id}/
        ...
      (libraries|themes|content|assets)/{id}/

  .gravewright/
    instance.json
    schema-version
    locks/

  backups/
```

### Mapeamento de paths

| `manifest.kind` | Diretório do package | Diretório de storage |
|---|---|---|
| `addon` | `data/packages/addons/{id}` | `data/storage/packages/addons/{id}` |
| `ruleset` | `data/packages/rulesets/{id}` | `data/storage/packages/rulesets/{id}` |
| `library` | `data/packages/libraries/{id}` | `data/storage/packages/libraries/{id}` |
| `theme` | `data/packages/themes/{id}` | `data/storage/packages/themes/{id}` |
| `content` | `data/packages/content/{id}` | `data/storage/packages/content/{id}` |
| `assets` | `data/packages/assets/{id}` | `data/storage/packages/assets/{id}` |

### Escopos de storage (Fase 7A/7B)

| Escopo | Path |
|---|---|
| `global` | `data/storage/packages/{kind_plural}/{id}/global/data.sqlite3` |
| `campaign` | `data/storage/packages/{kind_plural}/{id}/campaigns/{campaign_id}/data.sqlite3` |

## UX de backup / export

- **Backup da instância inteira**: copiar `data/` (inclui pacotes e storage).
- **Backup de package (com dados)**: `data/packages/{kind_plural}/{id}/` +
  `data/storage/packages/{kind_plural}/{id}/`.
- **Export/publicação de package (sem dados)**: apenas
  `data/packages/{kind_plural}/{id}/`; o storage é excluído por padrão.

A superfície de CLI para isso é definida na Fase 7B (`grave package backup|export`).

## Status de implementação

A descoberta lê apenas `data/packages/{kind_plural}/{id}`; diretórios fora de uma
raiz de kind não são descobertos. O binding kind-root é imposto: um pacote cujo
`manifest.kind` diverge da raiz `kind_plural` falha com
`sdk.manifest.kind_root_mismatch`, e um `manifest.id` diferente do nome do
diretório falha com `sdk.manifest.id_mismatch`.
