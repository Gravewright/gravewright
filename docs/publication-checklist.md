# Public Alpha Publication Checklist

Use this checklist before publishing a public Alpha release.

## Repository Hygiene

- No `.env` files except explicit templates such as `.env.example`.
- No SQLite databases, WAL files, SHM files, or local runtime storage.
- No `__pycache__/`, `.pyc`, `.pytest_cache/`, `.ruff_cache/`, logs, or generated performance outputs.
- No private maps, actor images, journal assets, campaign exports, or local test data.
- No secrets in current files or public Git history.

## Documentation

- `README.md` has the Alpha warning.
- `docs/alpha.md` explains upgrade risk.
- `SECURITY.md` explains private vulnerability reporting.
- `CONTRIBUTING.md` explains PR expectations and forbidden runtime artifacts.
- `docs/licensing.md` explains Apache-2.0 vs MIT boundaries.
- Issue links point to the public repository.

## Release Notes

Each Alpha release should include:

- install or upgrade steps;
- breaking changes;
- schema or storage changes;
- known data-loss risks;
- known issues;
- what feedback is most useful.
