# Operacao

## Backups

Backups precisam cobrir:

- banco de dados;
- `storage/`;
- diretorio de dados configurado por `GRAVEWRIGHT_DATA_DIR`;
- arquivos `.env` usados no deploy.

Sem backup do banco e dos uploads, uma campanha pode ficar inconsistente.

## Migracoes

Use Alembic para evolucao de schema quando migracoes estiverem presentes:

```bash
uv run alembic upgrade head
```

Em Alpha, nao ha garantia de upgrade entre todas as versoes. Sempre faca backup antes.

## Diagnosticos

Owners podem acessar diagnosticos do runtime quando habilitados pela aplicacao. Eventos devem ser scrubbed para nao expor segredos.

## Limpeza De Campanha

Ao deletar uma campanha, o Gravewright remove linhas relacionadas do banco e storage escopado da campanha, incluindo mapas, tiles, imagens de atores, assets de diarios e dados escopados de sistemas/modulos.

## Incidentes

Em caso de falha:

1. Pare a instancia se houver risco de corrupcao.
2. Preserve logs e backups.
3. Verifique banco, storage e versao do codigo.
4. Abra uma issue com passos de reproducao quando o problema for do projeto.
