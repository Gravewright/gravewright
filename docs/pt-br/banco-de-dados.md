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
uv run alembic upgrade head
uv run alembic current
uv run alembic history
```

Antes de migrar, faca backup do banco e dos arquivos de storage.

## Schema Runtime

O schema e definido por SQLAlchemy Core em `app/persistence/tables.py` e repositorios em `app/persistence/repositories/`. O runtime local cria tabelas quando necessario para desenvolvimento e testes.
