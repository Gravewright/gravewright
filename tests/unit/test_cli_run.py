from __future__ import annotations

import sys

from app.cli import run as run_mod
from app.cli.exit_codes import EXIT_MISSING_DEPENDENCY


def test_uvicorn_command_default_and_dev():
    base = run_mod.uvicorn_command(host="0.0.0.0", port=9001, dev=False)
    assert base == [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001"]
    assert "--reload" in run_mod.uvicorn_command(host="127.0.0.1", port=8000, dev=True)


def test_prepare_succeeds_and_proceeds(db):
    # db fixture points the schema at a temp sqlite; deps are present in the venv.
    checks, abort = run_mod.prepare(no_install=False, no_migrate=False)
    assert abort is None
    by_id = {c.id: c for c in checks}
    assert by_id["dependencies"].status == "ok"
    assert by_id["schema"].status == "ok"
    assert by_id["validation"].status in {"ok", "warn"}


def test_prepare_skips_schema_with_no_migrate(db):
    checks, abort = run_mod.prepare(no_install=True, no_migrate=True)
    assert abort is None
    by_id = {c.id: c for c in checks}
    assert by_id["schema"].status == "warn"
    assert "--no-migrate" in by_id["schema"].message


def test_prepare_aborts_when_dependencies_missing(db, monkeypatch):
    monkeypatch.setattr(run_mod, "_dependencies_present", lambda: False)
    checks, abort = run_mod.prepare(no_install=True, no_migrate=True)
    assert abort == EXIT_MISSING_DEPENDENCY
    dep = next(c for c in checks if c.id == "dependencies")
    assert dep.status == "error"
    assert dep.fix
