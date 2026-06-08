# Deploy

> [!WARNING]
> Gravewright esta em Alpha. Nao use para campanhas longas ou mesas que voce nao possa perder.

## Requisitos De Producao

- `APP_ENV=production`.
- `APP_DEBUG=false`.
- `WEB_WORKERS=1` na V1.
- `PUBLIC_BASE_URL` com HTTPS.
- `ALLOWED_HOSTS` definido.
- `SESSION_SECRET` forte.
- Cookies seguros habilitados.
- PostgreSQL como banco.
- Storage persistente para uploads e pacotes.
- Backup antes de migracoes ou atualizacoes.

## Banco

Use PostgreSQL em producao:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/gravewright
```

SQLite em producao e bloqueado por padrao. MySQL/MariaDB nao e suporte de producao na V1.

## Proxy

Configure o proxy reverso para encaminhar HTTP e WebSocket para a aplicacao. Defina `PUBLIC_BASE_URL`, `ALLOWED_HOSTS`, `TRUSTED_PROXIES` e `WS_ALLOWED_ORIGINS` de acordo com o dominio publico.

## Atualizacoes

Antes de atualizar:

1. Pare a aplicacao.
2. Faca backup do banco.
3. Faca backup de `storage/` e do diretorio configurado em `GRAVEWRIGHT_DATA_DIR`.
4. Aplique migracoes.
5. Suba a aplicacao e valide login, campanhas, mapa, WebSocket e uploads.
