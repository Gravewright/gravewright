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
uv run pytest tests/unit/test_cli_run.py tests/unit/test_cli_scaffold.py tests/unit/test_sdk_cli.py -q
```

## Unit Tests

```bash
uv run pytest tests/unit
```

Use focused files for development:

```bash
uv run pytest tests/unit/test_sdk_cli.py -q
uv run pytest tests/unit/test_inside_modules_smoke.py -q
```

## Compile Check

```bash
python3 -m compileall app tests scripts main.py
```

## CLI Tests

CLI tests cover:

- the `run` command and server launch wiring;
- package scaffolding (`ruleset new`, `addon new`, and friends);
- SDK CLI package discovery and doctor JSON output.

```bash
uv run pytest tests/unit/test_cli_run.py tests/unit/test_cli_scaffold.py tests/unit/test_sdk_cli.py -q
```

## Integration Tests

Database backend smoke tests are opt-in:

```bash
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://user:pass@localhost:5432/gravewright_test" \
  uv run pytest tests/integration/test_database_backends.py -q
```

MySQL/MariaDB URLs may be used for experimental schema portability checks, but MySQL/MariaDB is not a supported production backend in V1.

## End-to-End Tests

`tests/e2e/` boots a real `uvicorn` server in a subprocess against a temporary database and drives it over genuine HTTP — no bundled packages and no browser required. It seeds a GM and a campaign, performs a real CSRF-protected form login, confirms the authenticated dashboard renders, checks that a protected route redirects anonymous visitors to the login page, and that the SDK runtime script is served as a static asset.

```bash
uv run pytest tests/e2e -q
```

The suite is browserless (pure `urllib`), so it runs everywhere with no Selenium or geckodriver.

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

Windows Command Prompt runners:

```batch
tests\run_perf_test.bat
tests\run_max_stress.bat
tests\run_i5_stress.bat
tests\run_chunk_stream_test.bat
```

Use `--no-build` to reuse existing images, `--no-seed` on stress and chunk-stream
runners to reuse test data, and `--keep` on the chunk-stream runner to leave its
containers running.

Performance outputs are written under `tests/performance/`.
