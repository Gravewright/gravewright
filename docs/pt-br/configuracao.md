# Configuracao

O Gravewright le variaveis de ambiente por `app/config.py`. Arquivos de ambiente sao carregados conforme `APP_ENV`, e valores locais em `.env` podem sobrescrever defaults compartilhados.

## Modos De Ambiente

```text
development
staging
production
test
```

O modo `production` faz validacao rigorosa no startup e falha cedo quando encontra configuracoes inseguras.

## Configuracoes Principais

| Variavel | Funcao |
| --- | --- |
| `APP_ENV` | Ambiente de runtime. |
| `APP_DEBUG` | Habilita comportamento de debug. Deve ser falso em producao. |
| `WEB_WORKERS` | Quantidade de workers do Uvicorn. Deve ser 1 em producao na V1 para corretude do realtime. |
| `PUBLIC_BASE_URL` | URL externa canonica. Deve ser HTTPS em producao. |
| `ALLOWED_HOSTS` | Hosts aceitos, separados por virgula. Obrigatorio em producao. |
| `TRUSTED_PROXIES` | IPs ou CIDRs de proxies confiaveis. |
| `WS_ALLOWED_ORIGINS` | Origens explicitas para WebSocket. Derivado de `ALLOWED_HOSTS` quando vazio. |
| `GRAVEWRIGHT_DATA_DIR` | Raiz de dados dos pacotes SDK. Padrao: `data/`. |
| `DATABASE_URL` | URL SQLAlchemy do banco. |

## Banco De Dados

Local:

```env
DATABASE_URL=sqlite:///storage/gravewright.sqlite3
```

Producao deve usar PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/gravewright
```

SQLite em producao e recusado, exceto se `ALLOW_SQLITE_IN_PRODUCTION=true` for definido. MySQL/MariaDB nao e backend suportado em producao na V1.

## Sessao

| Variavel | Funcao |
| --- | --- |
| `SESSION_SECRET` | Segredo de assinatura. Use pelo menos 32 caracteres aleatorios em producao. |
| `SESSION_MAX_AGE` | Tempo de vida da sessao em segundos. |
| `SESSION_COOKIE_NAME` | Nome do cookie no navegador. |
| `SESSION_COOKIE_SECURE` | Deve ser verdadeiro em producao. |
| `SESSION_COOKIE_HTTPONLY` | Deve ser verdadeiro em producao. |
| `SESSION_COOKIE_SAMESITE` | `lax`, `strict` ou `none`. |
| `SESSION_COOKIE_DOMAIN` | Dominio opcional do cookie. |

## Limites

As configuracoes incluem limites numericos para autenticacao, reset de senha, WebSocket, viewport, fog, tokens, marcadores, medicoes, upload de mapas, dimensoes de imagem, tamanho de tiles e quantidade de tiles.

Todos os limites numericos devem ser maiores que zero.
