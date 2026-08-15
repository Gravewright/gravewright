# Banco De Dados

## Backends

SQLite e usado para desenvolvimento local e testes. PostgreSQL e o backend esperado para producao. MySQL/MariaDB pode aparecer em testes experimentais de portabilidade, mas nao e suportado em producao na V1.

## Configuracao Local

```env
DATABASE_URL=sqlite:///storage/gravewright.sqlite3
```

## Configuracao De Producao

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/gravewright
```

Em `APP_ENV=production`, SQLite e recusado por padrao. MySQL/MariaDB tambem e recusado para producao.

## Migracoes

```bash
grave db status
grave db upgrade
uv run alembic history
```

Antes de migrar, faça backup do banco e dos arquivos de storage.

O head atual é `0046_pdf_annotations`. As migrations cobrem snapshots
e auditoria, handouts, lobby e onboarding do mestre, paredes/portas, fontes de
luz e visao, combate simplificado, barras de token, particulas e shaders de cena
com origem estável, rotação, modo de mistura, opacidade e tipos de partícula,
além de cores de ping, raster virtual, granularidade adaptativa e anotações PDF.

Para uma instalação existente, crie um backup verificado, rode
`grave db status`, aplique `grave db upgrade` e finalize com `grave doctor`.

## Schema Runtime

O schema e definido por SQLAlchemy Core em `app/persistence/tables.py`, mas o
historico Alembic em `migrations/versions/` e a autoridade de evolucao. Bancos
persistentes devem ser inicializados e atualizados por `grave db upgrade`.
Bootstrap por metadata fica restrito a SQLite em memoria e ambientes de teste
explicitamente autorizados.
