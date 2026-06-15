# Public Alpha Publication Checklist

Use this checklist before publishing a public Alpha release.

## Repository Hygiene

- No `.env` files except explicit templates such as `.env.example`.
- No SQLite databases, WAL files, SHM files, or local runtime storage.
- No `__pycache__/`, `.pyc`, `.pytest_cache/`, `.ruff_cache/`, logs, local backups, or generated performance outputs.
- No private maps, actor images, journal assets, campaign exports, or local test data.
- No secrets in current files or public Git history.

## Required Checks

```bash
grave doctor
uv run pytest tests/unit -q
python3 -m compileall app tests scripts main.py
uv run pytest tests/e2e -q
```

For CLI/package changes:

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
```

## Documentation

- `README.md` has the Alpha warning.
- `docs/alpha.md` explains upgrade risk.
- `docs/getting-started.md` uses `grave run`.
- `docs/operations.md` explains `grave backup` and restore.
- `docs/sdk/cli.md` documents the current CLI surface.
- `SECURITY.md` explains private vulnerability reporting and SDK package trust.
- `CONTRIBUTING.md` explains PR expectations and forbidden runtime artifacts.
- `docs/licensing.md` explains Apache-2.0 vs MIT boundaries.
- Issue links point to the public repository.

## Release Notes

Each Alpha release should include:

- install or upgrade steps;
- breaking changes;
- schema or storage changes;
- SDK/package manifest changes;
- known data-loss risks;
- known issues;
- what feedback is most useful.
