# Testing

## Unit Tests

```bash
uv run pytest tests/unit
```

Use focused files for development:

```bash
uv run pytest tests/unit/test_campaign_delete_cascade.py
uv run pytest tests/unit/test_game_render_smoke.py
```

## Compile Check

```bash
python3 -m compileall app tests scripts main.py
```

## Integration Tests

Database backend smoke tests are opt-in:

```bash
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://user:pass@localhost:5432/gravewright_test" \
  uv run pytest tests/integration/test_database_backends.py -q
```

MySQL/MariaDB URLs may be used for experimental schema portability checks, but MySQL/MariaDB is not a supported production backend in V1.

## Docker and Performance Tests

Docker Compose files for tests live in `tests/`:

```text
tests/docker-compose.perf.yml
tests/docker-compose.max-stress.yml
tests/docker-compose.i5-stress.yml
tests/docker-compose.chunk-stream.yml
```

Validate them without starting containers:

```bash
docker compose -f tests/docker-compose.perf.yml config
docker compose -f tests/docker-compose.max-stress.yml config
docker compose -f tests/docker-compose.i5-stress.yml config
docker compose -f tests/docker-compose.chunk-stream.yml config
```

Runner scripts:

```bash
bash tests/run_perf_test.sh
bash tests/run_max_stress.sh
bash tests/run_i5_stress.sh
bash tests/run_chunk_stream_test.sh
```

Performance outputs are written under `tests/performance/`.
