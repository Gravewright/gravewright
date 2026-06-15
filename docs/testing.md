# Testing

## Recommended Local Gate

Before sharing a broad change:

```bash
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```

For CLI changes, also run:

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
```

## Unit Tests

```bash
uv run pytest tests/unit
```

Use focused files for development:

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_game_render_smoke.py -q
```

## Compile Check

```bash
python3 -m compileall app tests scripts main.py
```

## CLI Tests

CLI tests cover:

- parser command coverage;
- backup/restore behavior;
- doctor JSON/text/AI output;
- package validation;
- SDK CLI package discovery.

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
```

## Integration Tests

Database backend smoke tests are opt-in:

```bash
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://user:pass@localhost:5432/gravewright_test" \
  uv run pytest tests/integration/test_database_backends.py -q
```

MySQL/MariaDB URLs may be used for experimental schema portability checks, but MySQL/MariaDB is not a supported production backend in V1.

## Browser End-to-End Tests

`tests/e2e/` drives a real headless Firefox through the full SDK package runtime: it seeds a campaign, boots a live `uvicorn` server against a temporary database, logs in through the actual form, opens the table, and asserts that bundled packages register through `window.GravewrightSDK`.

```bash
uv run pytest tests/e2e -q
```

Requirements: the `selenium` dev dependency plus local Firefox. Selenium Manager fetches a matching `geckodriver` automatically. The suite skips itself when Selenium or a Firefox/geckodriver pair is unavailable.

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
