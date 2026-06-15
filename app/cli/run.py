"""``grave run`` — "I want to play, fix the basics for me, then start the server."

The default does the boring-but-essential setup an operator forgets: ensure the
data/storage directories exist, install dependencies if they are missing, ensure
the database schema is present, surface (but don't block on) package problems,
then launch the web server. Flags peel back the automation for power users.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from app.cli.doctor import ERROR, OK, WARN, Check, run_doctor, summarize
from app.cli.exit_codes import EXIT_DOCTOR_ERROR, EXIT_MISSING_DEPENDENCY
from app.config import config
from app.helpers.env import PROJECT_ROOT

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _ensure_directories() -> list[Check]:
    checks: list[Check] = []
    targets = {
        "data_dir": Path(config.data_dir),
        "packages_dir": Path(config.data_dir) / "packages",
        "storage_dir": (PROJECT_ROOT / "storage").resolve(),
    }
    for check_id, path in targets.items():
        if path.is_dir():
            checks.append(Check(check_id, OK, f"{path} exists"))
            continue
        try:
            path.mkdir(parents=True, exist_ok=True)
            checks.append(Check(check_id, OK, f"created {path}"))
        except OSError as exc:
            checks.append(Check(check_id, ERROR, f"could not create {path}: {exc}"))
    return checks


def _dependencies_present() -> bool:
    from importlib.util import find_spec

    return all(find_spec(mod) is not None for mod in ("litestar", "uvicorn"))


def _ensure_dependencies(*, no_install: bool) -> Check:
    if _dependencies_present():
        return Check("dependencies", OK, "dependencies present")
    if no_install:
        return Check(
            "dependencies",
            ERROR,
            "dependencies missing and --no-install was passed",
            fix="Run: uv sync",
        )
    if not shutil.which("uv"):
        return Check(
            "dependencies",
            ERROR,
            "dependencies missing and uv is not available to install them",
            fix="Install uv (https://docs.astral.sh/uv/) then run: uv sync",
        )
    result = subprocess.run(["uv", "sync"], cwd=str(PROJECT_ROOT))
    if result.returncode != 0 or not _dependencies_present():
        return Check("dependencies", ERROR, "uv sync failed", fix="Run uv sync manually and inspect output")
    return Check("dependencies", OK, "dependencies installed via uv sync")


def _ensure_schema(*, no_migrate: bool) -> Check:
    if no_migrate:
        return Check("schema", WARN, "schema step skipped (--no-migrate)")
    try:
        from app.persistence.database import initialize_database

        # Idempotent: creates any missing tables for the configured backend.
        initialize_database()
    except Exception as exc:  # noqa: BLE001 - report, don't crash the launcher
        return Check(
            "schema",
            ERROR,
            f"could not ensure database schema: {type(exc).__name__}: {exc}",
            fix="Check DATABASE_URL and database connectivity",
        )
    return Check("schema", OK, "database schema ready")


def prepare(
    *,
    no_install: bool,
    no_migrate: bool,
    strict_doctor: bool = False,
) -> tuple[list[Check], int | None]:
    """Run pre-flight setup. Returns (checks, abort_exit_code_or_None).

    Only genuinely blocking problems abort the launch; package-level issues are
    surfaced as warnings so an operator can still start the server and fix them.

    When strict_doctor is enabled, doctor validation errors abort the launch.
    """
    checks: list[Check] = []
    checks.extend(_ensure_directories())
    if any(c.status == ERROR for c in checks):
        return checks, EXIT_DOCTOR_ERROR

    dep = _ensure_dependencies(no_install=no_install)
    checks.append(dep)
    if dep.status == ERROR:
        return checks, EXIT_MISSING_DEPENDENCY

    checks.append(_ensure_schema(no_migrate=no_migrate))

    # Non-blocking package/db validation by default.
    audit = run_doctor(packages_dir=Path(config.data_dir) / "packages", skip_db=no_migrate)
    s = summarize(audit)

    has_errors = s["error_count"] > 0
    status = ERROR if strict_doctor and has_errors else OK if not has_errors else WARN

    checks.append(
        Check(
            "validation",
            status,
            f"packages/database: {s['error_count']} error(s), {s['warn_count']} warning(s)",
            fix=None if status == OK else "grave doctor",
        )
    )

    if strict_doctor and has_errors:
        return checks, EXIT_DOCTOR_ERROR

    return checks, None


def uvicorn_command(*, host: str, port: int, dev: bool) -> list[str]:
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", host, "--port", str(port)]
    if dev:
        cmd.append("--reload")
    return cmd


def _open_browser_when_ready(url: str, *, timeout: float = 20.0) -> None:
    def _wait_and_open() -> None:
        import webbrowser

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2):
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.3)
        webbrowser.open(url)

    threading.Thread(target=_wait_and_open, daemon=True).start()


def serve(*, host: str, port: int, dev: bool, open_browser: bool) -> int:
    if open_browser:
        shown = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
        _open_browser_when_ready(f"http://{shown}:{port}/")
    print(f"Starting Gravewright on http://{host}:{port}/  (Ctrl+C to stop)", flush=True)
    try:
        return subprocess.run(uvicorn_command(host=host, port=port, dev=dev), cwd=str(PROJECT_ROOT)).returncode
    except KeyboardInterrupt:
        return 0
