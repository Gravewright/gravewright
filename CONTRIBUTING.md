# Contributing to Gravewright

Gravewright welcomes focused contributions that improve reliability, performance, security, documentation, and the public SDK/package APIs.

## Development Setup

```bash
uv sync --group dev
cp .env.example .env
chmod +x grave
./grave doctor
./grave run --open
```

Fallback:

```bash
uv run python -m app.cli doctor
uv run python -m app.cli run --open
```

Open:

```text
http://127.0.0.1:8000
```

## Before Opening a Pull Request

Run the checks that match your change.

For most changes:

```bash
./grave doctor
uv run pytest tests/unit
python3 -m compileall app tests scripts main.py
```

For CLI changes:

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
```

For SDK/browser-runtime changes:

```bash
uv run pytest tests/e2e -q
```

For Docker/performance configuration changes:

```bash
docker compose -f tests/docker-compose.perf.yml config
```

Use focused test runs while developing. Broaden the run when touching shared services, persistence, realtime transport, permissions, scene streaming, package lifecycle, browser SDK runtime, or public APIs.

## Engineering Standards

- Keep HTTP handlers in `app/actions`.
- Keep product rules in `app/business`.
- Keep table-runtime behavior in `app/engine`.
- Keep SDK package services in `app/engine/sdk`.
- Keep CLI behavior in `app/cli`.
- Keep persistence in `app/persistence/repositories`.
- Do not make `actions` import repositories directly.
- Do not make `engine` depend on Litestar request or response objects.
- Treat the backend as authoritative for game state.
- Treat documented SDK APIs as the only public extension surface.
- Do not rely on private browser globals, renderer internals, DOM structure, or fallback labels.

## SDK Package Contributions

When adding or changing bundled packages under `data/packages/`:

1. validate the package;
2. run package doctor;
3. install/enable/activate it in a test campaign when relevant;
4. include or update docs for any public package surface.

Useful commands:

```bash
grave package validate data/packages/<id>
grave package doctor <id>
grave package list
grave campaign package activate <campaign_id> <id>
```

## Public API Changes

When changing SDK package, browser runtime, manifest, content-pack, schema, CLI, or realtime public contracts:

1. update docs in the same change;
2. update schemas when applicable;
3. add compatibility or migration notes;
4. add tests that cover both valid and invalid inputs;
5. update `CHANGELOG.md`.

## Generated and Runtime Files

Do not commit local runtime data from `storage/`, SQLite databases, WAL/SHM sidecars, `.env`, caches, temporary uploads, local backups, generated performance outputs, or private campaign assets unless a fixture is intentionally part of the test suite.

## Licensing of Contributions

Unless explicitly stated otherwise, contributions to the core are submitted under Apache-2.0. Contributions to API materials are submitted under MIT. See `docs/licensing.md`.

## Security Issues

Do not open a public issue for a vulnerability. Follow `SECURITY.md`.
