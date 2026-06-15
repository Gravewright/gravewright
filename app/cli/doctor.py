"""``grave doctor`` — the operational health check for a Gravewright install.

Doctor answers five questions for every problem it finds: *what* is wrong, *why*,
*where*, *how to fix it*, and *whether it can be fixed automatically*. It checks
the environment, the on-disk packages, and the database, and always ends by
telling the operator either "ready to play" or exactly what to do next.

The report is a flat list of :class:`Check`; renderers turn it into the human
``OK/WARN/ERROR/FIX`` view, ``--json`` for CI/AI/tooling, or an ``--ai`` prompt.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import config
from app.helpers.env import PROJECT_ROOT

OK = "ok"
WARN = "warn"
ERROR = "error"

_MIN_PYTHON = (3, 11)
_DEV_SECRETS = {"dev-only-change-me", "change-me-in-production"}


@dataclass
class Check:
    id: str
    status: str
    message: str
    fix: str | None = None


def _schema_path() -> Path:
    return PROJECT_ROOT / "schemas" / "gravewright-package-v1.schema.json"


# --- environment ------------------------------------------------------------


def _environment_checks() -> list[Check]:
    checks: list[Check] = []

    py = sys.version_info
    if (py.major, py.minor) >= _MIN_PYTHON:
        checks.append(Check("python", OK, f"Python {py.major}.{py.minor} detected"))
    else:
        checks.append(
            Check(
                "python",
                ERROR,
                f"Python {py.major}.{py.minor} is too old (need >= {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]})",
                fix="Install a supported Python and recreate the virtualenv",
            )
        )

    if shutil.which("uv"):
        checks.append(Check("uv", OK, "uv is available"))
    else:
        checks.append(
            Check("uv", WARN, "uv was not found on PATH", fix="Install uv: https://docs.astral.sh/uv/")
        )

    data_dir = Path(config.data_dir)
    if data_dir.is_dir():
        checks.append(Check("data_dir", OK, f"data dir exists ({data_dir})"))
    else:
        checks.append(
            Check("data_dir", ERROR, f"data dir is missing ({data_dir})", fix=f"mkdir -p {data_dir}")
        )

    packages_dir = data_dir / "packages"
    if packages_dir.is_dir():
        checks.append(Check("packages_dir", OK, f"data/packages exists ({packages_dir})"))
    else:
        checks.append(
            Check(
                "packages_dir",
                ERROR,
                f"data/packages is missing ({packages_dir})",
                fix=f"mkdir -p {packages_dir}",
            )
        )

    storage_dir = (PROJECT_ROOT / "storage").resolve()
    if storage_dir.is_dir():
        checks.append(Check("storage_dir", OK, "storage dir exists"))
    else:
        checks.append(
            Check("storage_dir", WARN, "storage dir is missing (created on first run)", fix="grave run")
        )

    schema = _schema_path()
    if schema.is_file():
        checks.append(Check("sdk_schema", OK, "SDK package schema found"))
    else:
        checks.append(Check("sdk_schema", ERROR, f"SDK package schema missing ({schema})"))

    # Legacy directories from the pre-SDK System/Module API must not linger.
    for legacy in ("systems", "modules"):
        legacy_dir = data_dir / legacy
        if legacy_dir.exists():
            checks.append(
                Check(
                    f"legacy_dir_{legacy}",
                    WARN,
                    f"legacy data/{legacy} directory still present (pre-SDK)",
                    fix=f"Migrate its packages to data/packages, then remove {legacy_dir}",
                )
            )

    if config.session_secret in _DEV_SECRETS:
        checks.append(
            Check(
                "session_secret",
                WARN if config.app_env != "production" else ERROR,
                "SESSION_SECRET is still the development default",
                fix="Set a strong SESSION_SECRET in your environment",
            )
        )

    return checks


def _database_checks() -> list[Check]:
    """Confirm the database is reachable and carries the SDK schema."""
    try:
        from sqlalchemy import text

        from app.persistence.database import engine_connect

        with engine_connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.execute(text("SELECT 1 FROM installed_packages LIMIT 1"))
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        return [
            Check(
                "database",
                ERROR,
                f"database not reachable or schema missing: {type(exc).__name__}: {exc}",
                fix="grave run (initializes the schema), or check DATABASE_URL",
            )
        ]
    return [Check("database", OK, "database reachable")]


# --- packages (on disk) -----------------------------------------------------


def _package_checks(packages_dir: Path) -> list[Check]:
    from app.engine.sdk.package_registry import load_all

    checks: list[Check] = []
    packages = load_all(packages_dir)
    valid = 0
    for package in packages:
        if package.ok:
            valid += 1
            for warning in package.validation.warnings:
                checks.append(Check(f"package:{package.id}", WARN, f"{package.id}: {warning}"))
            continue
        for error in package.validation.errors:
            checks.append(
                Check(
                    f"package:{package.id}",
                    ERROR,
                    f"{package.id}: {error}",
                    fix=f"grave package validate {package.package_dir}",
                )
            )
    checks.insert(0, Check("packages", OK, f"{valid}/{len(packages)} on-disk packages valid"))
    return checks


# --- database audit (drift) -------------------------------------------------

_AUDIT_FIX = {
    "package_missing_on_disk": "Reinstall the package or run: grave package remove {package_id}",
    "enabled_but_invalid": "grave package validate data/packages/{package_id}",
    "enabled_but_incompatible": "Update the package or Gravewright to a compatible version",
    "active_but_disabled": "grave package enable {package_id}",
    "active_but_not_installed": "Reinstall {package_id} or deactivate it in the campaign",
    "dependency_missing": "Install the missing dependency package",
    "dependency_disabled": "grave package enable the required dependency",
    "dependency_inactive": "Activate the required dependency in the campaign",
    "dependency_outdated": "Update the required dependency to a newer version",
    "dependency_too_new": "Update {package_id} or downgrade the dependency",
    "dependency_wrong_kind": "Install the dependency of the expected kind",
    "conflict_active": "Deactivate the conflicting package in the campaign",
    "orphan_setting_uninstalled": "Stored settings for a package that is gone (safe to clean up)",
    "orphan_setting_undeclared": "Setting key no longer declared by the manifest (safe to clean up)",
    "orphan_content_import": "Content import for a package that is gone (safe to clean up)",
}


def _audit_checks() -> list[Check]:
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    try:
        findings = PackageDoctorService().audit()
    except Exception as exc:  # noqa: BLE001
        return [Check("db_audit", WARN, f"database audit skipped: {type(exc).__name__}: {exc}")]

    checks: list[Check] = []
    for f in findings:
        where = f"{f.package_id}"
        if f.campaign_id:
            where += f" (campaign {f.campaign_id})"
        detail = f" {f.detail}" if f.detail else ""
        fix = _AUDIT_FIX.get(f.code)
        if fix:
            fix = fix.format(package_id=f.package_id)
        checks.append(Check(f"audit:{f.code}", f.severity, f"{f.code}: {where}{detail}", fix=fix))
    return checks


def _activation_hints() -> list[Check]:
    """Informational: enabled add-ons not active in any campaign."""
    from app.engine.sdk.package_install_service import PackageInstallService

    svc = PackageInstallService()
    checks: list[Check] = []
    try:
        records = svc.installed.list_all()
    except Exception:  # noqa: BLE001 - DB issues already reported elsewhere
        return checks
    for record in records:
        if record["status"] != "enabled" or record["kind"] in {"ruleset", "library"}:
            continue
        if not svc._active_campaign_ids(record["id"]):
            checks.append(
                Check(
                    f"inactive:{record['id']}",
                    WARN,
                    f"{record['id']} is enabled but not active in any campaign",
                    fix="Activate it in a campaign, or leave it idle: grave package list",
                )
            )
    return checks


# --- orchestration ----------------------------------------------------------


def run_doctor(*, packages_dir: Path, skip_db: bool) -> list[Check]:
    checks: list[Check] = []
    checks.extend(_environment_checks())
    checks.extend(_package_checks(packages_dir))
    if not skip_db:
        checks.extend(_database_checks())
        if any(c.id == "database" and c.status == OK for c in checks):
            checks.extend(_audit_checks())
            checks.extend(_activation_hints())
    return checks


def summarize(checks: list[Check]) -> dict:
    errors = sum(1 for c in checks if c.status == ERROR)
    warns = sum(1 for c in checks if c.status == WARN)
    return {"ok": errors == 0, "error_count": errors, "warn_count": warns}


def render_check_lines(checks: list[Check], *, verbose: bool = False) -> list[str]:
    """The ``OK/WARN/ERROR`` (+ ``FIX``) lines, without the closing verdict."""
    label = {OK: "OK   ", WARN: "WARN ", ERROR: "ERROR"}
    lines: list[str] = []

    for c in checks:
        prefix = f"{label[c.status]} "
        if verbose:
            lines.append(f"{prefix}[{c.id}] {c.message}")
        else:
            lines.append(f"{prefix}{c.message}")

        if c.fix:
            lines.append(f"FIX    {c.fix}")

    return lines


def render_text(checks: list[Check]) -> str:
    lines = render_check_lines(checks)
    s = summarize(checks)
    lines.append("")
    if s["ok"]:
        lines.append("OK, ready to play.")
    else:
        lines.append(
            f"Not ready: {s['error_count']} error(s), {s['warn_count']} warning(s). "
            "Fix the items above and run grave doctor again."
        )
    return "\n".join(lines)


def render_json(checks: list[Check]) -> dict:
    return {**summarize(checks), "checks": [asdict(c) for c in checks]}


def render_ai_prompt(checks: list[Check]) -> str:
    report = render_text(checks)
    return (
        "Copy this prompt into your AI assistant:\n\n"
        "I am operating a Gravewright install. Here is the `grave doctor` output:\n\n"
        f"{report}\n\n"
        "Please tell me exactly how to resolve the errors and warnings.\n"
        "Only change package files or my environment/config.\n"
        "Do not edit Gravewright core.\n"
        "Do not use the legacy System API or Module API.\n"
        "Do not invent capabilities."
    )
