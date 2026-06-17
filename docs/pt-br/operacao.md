# Operação

## CLI de Operação

```bash
grave doctor
grave run --open
grave backup -o gravewright-backup.zip --include-assets --verify
grave restore gravewright-backup.zip --dry-run
grave package list
grave lock -o grave.lock.json
```

Fallback:

```bash
uv run python -m app.cli doctor
```

## Backups

Antes de atualizar o Gravewright ou alterar pacotes, faça backup:

```bash
grave backup -o gravewright-backup.zip --include-assets --verify
```

Para pacotes locais/customizados, use backup autocontido quando suportado:

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
```

Backups precisam cobrir:

- banco de dados;
- `storage/`;
- `GRAVEWRIGHT_DATA_DIR` ou `data/packages/`;
- `.env` ou secrets do deploy;
- pacotes locais que não podem ser baixados novamente.

## Restore

Teste primeiro:

```bash
grave restore gravewright-backup.zip --dry-run
```

Restore real exige confirmação:

```bash
grave restore gravewright-backup.zip --yes
```

Ordem recomendada:

1. Pare a aplicação.
2. Restaure o banco.
3. Restaure `storage/`.
4. Restaure `GRAVEWRIGHT_DATA_DIR` ou `data/packages/`.
5. Rode `grave doctor`.
6. Inicie a aplicação.
7. Abra `/inside/diagnostics` como owner.

## Diagnósticos

```bash
grave doctor
grave doctor --json
grave doctor --ai
```

Owners também podem acessar diagnósticos do runtime em `/inside/diagnostics`.

## Operações de Pacotes

```bash
grave package list
grave package doctor <package_id>
grave package disable <package_id>
grave package remove <package_id>
grave campaign package list <campaign_id>
grave campaign package deactivate <campaign_id> <package_id>
```

Substituição de pacote deve ser feita depois de desativar o pacote nas campanhas e desabilitá-lo globalmente.
