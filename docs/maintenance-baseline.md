# Maintenance Baseline (Etapa 0)

Reproducible starting point for the technical maintenance plan
(`Gravewright_Plano_de_Manutencao_Tecnica.md`). Every later stage is compared
against the behaviour captured here. This document records **what the code does
today**; it does not change application behaviour.

## Commit under analysis

| Item | Value |
|------|-------|
| Commit | `1607eb1d` — feat(sdk): expose server-authoritative dice rolls to declarative sheets |
| Branch | `main` |
| Date captured | 2026-08-04 |

## Environment

| Component | Version |
|-----------|---------|
| OS | Windows 11 (win32) |
| Python | 3.13.9 (`.python-version` pins 3.13) |
| uv | 0.9.11 |
| SQLAlchemy | 2.0.50 |
| Litestar | 2.22.0 |
| Alembic | 1.18.4 |
| pytest | 9.0.3 (pytest-asyncio 1.4.0, asyncio mode=AUTO) |

Database exercised by the default suite: **SQLite** (temp file per test, via the
`db` fixture in `tests/conftest.py`). PostgreSQL/MySQL backends are opt-in and
were **not** exercised in this baseline (see Preexisting gaps below).

## Commands executed and results

| # | Command | Result |
|---|---------|--------|
| 1 | `uv sync --frozen` | OK — environment resolved from `uv.lock`, no version was loosened. |
| 2 | `uv run python -m compileall app tests scripts main.py` | OK — all modules compiled (exit 0). |
| 3 | `uv run pytest tests/unit -q` | **992 passed, 1 failed** in ~96s (see Preexisting failures). |
| 4 | `uv run pytest tests/integration -q` | 2 skipped (no `GRAVEWRIGHT_TEST_DATABASE_URLS`). |
| 5 | `uv run pytest tests/e2e -q` | 3 passed in ~3s. |
| 6 | `uv run pytest tests/unit/test_maintenance_baseline_smoke.py -q` | 1 passed — create campaign / list / add member smoke on temp SQLite. |

## Smoke test (create campaign / list / add member)

Added `tests/unit/test_maintenance_baseline_smoke.py`. It uses the isolated
`db` fixture and the persistence layer directly to:

1. create a campaign owned by a seeded GM;
2. confirm it lists back for the owner with `member_role == "gm"`;
3. add a second member and confirm the roster query returns both names.

This is the minimal persistence happy-path and serves as a stable reference for
later stages that touch membership, migrations, or the engine.

## Preexisting failures (NOT regressions — do not fix in Etapa 0)

### F1 — `test_cli_doctor.py::test_doctor_warns_enabled_addon_inactive_in_any_campaign`

- **Symptom:** fails only inside the full `pytest tests/unit` run
  (`assert exit_code == 0` fails because an `error`-level doctor check leaks
  into the payload; `error_count == 1`).
- **Isolation:** PASSES when run alone, PASSES when the whole
  `tests/unit/test_cli_doctor.py` file runs (7/7), and PASSES under
  `pytest tests/unit -k doctor` (30/30).
- **Diagnosis:** order-dependent, **cross-file state pollution** — a non-doctor
  test that runs earlier in the default collection order leaves installed/active
  package or diagnostic state that the CLI `doctor` invocation (which runs
  against the shared engine, not `--skip-db`) then reports as an error. It is a
  **test-isolation defect, not an application-logic defect**.
- **Reproduction:** `uv run pytest tests/unit -q` (full suite).
- **Scope:** out of scope for Etapa 0. Candidate cleanup for the CI/testing
  stage (Etapa 9), where fixture teardown and package-registry isolation are in
  scope. Pinning the exact polluting test requires a bisect and must not be
  bundled with baseline changes.

## Preexisting gaps observed (informational, addressed by later stages)

- **PostgreSQL/MySQL not exercised** — `tests/integration/test_database_backends.py`
  skips without `GRAVEWRIGHT_TEST_DATABASE_URLS`. The plan (Etapas 1, 6, 9)
  requires a SQLite/PostgreSQL matrix; the baseline covers SQLite only.
- **No lint gate** — CI runs compileall + unit tests but no `ruff` (Etapa 9).
- **Schema evolution has two sources** — Alembic migrations *and* startup
  `create_all` / `_ensure_incremental_columns` (Etapas 1–2).

## Minimum validation set required for every later stage (per-PR gate)

Every subsequent stage's pull request MUST run and pass at least the following
before it is considered done. A stage that cannot run part of this set must say
why in its PR.

```bash
# 1. Compile everything
uv run python -m compileall app tests scripts main.py

# 2. Unit tests for the touched area (name the files), plus the full unit suite
uv run pytest tests/unit -q

# 3. Persistence baseline smoke
uv run pytest tests/unit/test_maintenance_baseline_smoke.py -q

# 4. End-to-end HTTP smoke (login + dashboard + static SDK)
uv run pytest tests/e2e -q
```

Add, per stage scope:

- **Schema/migration stages (1, 2, 6):** empty DB → `alembic upgrade head` →
  schema audit; legacy fixture → upgrade → smoke. Run on SQLite and (when a URL
  is available) PostgreSQL via `GRAVEWRIGHT_TEST_DATABASE_URLS`.
- **Concurrency stages (3, 5):** the relevant concurrency/async tests
  (`tests/unit/test_async_blocking.py`, integration race tests).
- **Frontend stages (7, 8):** browser/E2E smoke for the touched flow.

### Accepted baseline delta

At Etapa 0 the only tolerated non-pass in `tests/unit` was the order-dependent
failure **F1** (992 passed, 1 failed).

**Update (Etapa 1):** after adding the schema-parity/legacy test modules, the
collection order shifted and F1 no longer reproduces — `tests/unit` is now
**998 passed, 0 failed**. This *masks* F1's manifestation; the underlying
test-isolation defect is unchanged and remains tracked for Etapa 9. Any later PR
must keep `tests/unit` green (0 failures); a new failure means a regression was
introduced and the stage must stop.

## Acceptance criteria (Etapa 0)

- [x] A versioned baseline file exists with commands and results.
- [x] No dependency was loosened or upgraded (`uv sync --frozen` from lockfile).
- [x] The minimum per-PR test set is documented (above).
- [x] Preexisting failures (F1) are separated from regressions.

## Rollback

This stage adds only documentation and one additive smoke test. To roll back,
delete `docs/maintenance-baseline.md` and
`tests/unit/test_maintenance_baseline_smoke.py`. No application behaviour is
affected.
