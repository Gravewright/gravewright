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

Antes de migrar, faca backup do banco e dos arquivos de storage.

O head atual e `0042_particle_kinds`. As migrations da Alpha 3 cobrem snapshots
e auditoria, handouts, lobby e onboarding do mestre, paredes/portas, fontes de
luz e visao, combate simplificado, barras de token, particulas e shaders de cena
com origem estavel, rotacao, modo de mistura, opacidade e tipos de particula.

Para uma instalacao Alpha existente, crie um backup verificado, rode
`grave db status`, aplique `grave db upgrade` e finalize com `grave doctor`.

## Schema Runtime

O schema e definido por SQLAlchemy Core em `app/persistence/tables.py`, mas o
historico Alembic em `migrations/versions/` e a autoridade de evolucao. Bancos
persistentes devem ser inicializados e atualizados por `grave db upgrade`.
Bootstrap por metadata fica restrito a SQLite em memoria e ambientes de teste
explicitamente autorizados.
