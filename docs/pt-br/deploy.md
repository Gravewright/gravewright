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

## Docker Compose

O repositório inclui um `docker-compose.yml` na raiz para uma execução rápida em
um único host:

```bash
docker compose up -d --build   # abra http://localhost:8000
docker compose logs -f
docker compose down            # para; os dados ficam em volumes nomeados
```

Ele constrói a imagem a partir do `Dockerfile`, roda um worker, usa SQLite e
persiste os dados nos volumes nomeados `gravewright-storage` (`/app/storage`) e
`gravewright-data` (`/app/data`). A configuração padrão serve em HTTP puro, para
uso local/self-hosted.

Antes de expor à internet, sobrescreva o ambiente no `docker-compose.yml` (ou
pelo shell/`.env`) para produção:

- defina um `SESSION_SECRET` forte (`python -c "import secrets; print(secrets.token_urlsafe(48))"`);
- defina `SESSION_COOKIE_SECURE=true` e faça terminação HTTPS num proxy reverso;
- defina `ALLOWED_HOSTS`, `PUBLIC_BASE_URL` e `WS_ALLOWED_ORIGINS` com seu domínio.

PostgreSQL é recomendado para instalações públicas; ele exige construir a imagem
com o extra `postgres` (`psycopg`), que a imagem padrão não inclui.

## Atualizacoes

Antes de atualizar:

1. Pare a aplicacao.
2. Faca backup do banco.
3. Faca backup de `storage/` e do diretorio configurado em `GRAVEWRIGHT_DATA_DIR`.
4. Aplique migracoes.
5. Suba a aplicacao e valide login, campanhas, mapa, WebSocket e uploads.
