# Testes

## Testes Unitarios

```bash
uv run pytest tests/unit
```

Durante desenvolvimento, rode arquivos focados:

```bash
uv run pytest tests/unit/test_campaign_delete_cascade.py
uv run pytest tests/unit/test_game_render_smoke.py
```

## Checagem De Compilacao

```bash
python3 -m compileall app tests scripts main.py
```

## Testes De Integracao

Smoke tests de backend de banco sao opt-in:

```bash
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://user:pass@localhost:5432/gravewright_test" \
  uv run pytest tests/integration/test_database_backends.py -q
```

URLs MySQL/MariaDB podem ser usadas para checagens experimentais de portabilidade de schema, mas MySQL/MariaDB nao e backend de producao suportado na V1.

## Docker E Performance

Os Compose de teste ficam em `tests/`:

```text
tests/docker-compose.perf.yml
tests/docker-compose.max-stress.yml
tests/docker-compose.i5-stress.yml
tests/docker-compose.chunk-stream.yml
```

Validacao sem subir containers:

```bash
docker compose -f tests/docker-compose.perf.yml config
docker compose -f tests/docker-compose.max-stress.yml config
docker compose -f tests/docker-compose.i5-stress.yml config
docker compose -f tests/docker-compose.chunk-stream.yml config
```

Scripts:

```bash
bash tests/run_perf_test.sh
bash tests/run_max_stress.sh
bash tests/run_i5_stress.sh
bash tests/run_chunk_stream_test.sh
```

Resultados de performance sao gravados em `tests/performance/`.
