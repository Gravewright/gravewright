"""``grave package`` (and per-kind sugar): the operator package manager.

Install / enable / disable / remove / update packages globally, activate them per
campaign, and run a per-package doctor. Every failure prints the reason plus an
actionable fix; install shows the package's requested capabilities (Android-style)
before committing. Sources are bundled package ids for now (``data/packages/<id>``);
remote/zip install is a later milestone.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from app.cli.exit_codes import (
    EXIT_DOCTOR_ERROR,
    EXIT_INCOMPATIBLE,
    EXIT_MISSING_DEPENDENCY,
    EXIT_OK,
    EXIT_UNSAFE,
)


_ERROR_FIX = {
    "sdk.errors.not_found": "No such package on disk (data/packages/<id>).",
    "sdk.errors.not_installed": "Install it first: grave package install <id>",
    "sdk.errors.not_enabled": "Enable it first: grave package enable <id>",
    "sdk.errors.incompatible": "Package is incompatible with this Gravewright version.",
    "sdk.errors.invalid_manifest": "Fix the manifest, then: grave package doctor <id>",
    "sdk.errors.not_activatable": "Only addon/theme/assets/content packages activate per campaign.",
    "sdk.errors.package_active_in_campaign": (
        "Deactivate it in every campaign first, or pass --force."
    ),
    "sdk.errors.dependency_missing": "Install the required dependency first.",
    "sdk.errors.dependency_disabled": "Enable the required dependency: grave package enable <dep>",
    "sdk.errors.dependency_inactive": "Activate the required dependency in this campaign first.",
    "sdk.errors.package_conflict_active": "Deactivate the conflicting package in this campaign.",
    "sdk.errors.not_a_ruleset": "That package is not a ruleset.",
}


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


_INCOMPATIBLE_ERRORS = {
    "sdk.errors.incompatible",
    "sdk.errors.dependency_missing",
    "sdk.errors.dependency_disabled",
    "sdk.errors.dependency_inactive",
    "sdk.errors.dependency_outdated",
    "sdk.errors.dependency_too_new",
    "sdk.errors.dependency_wrong_kind",
    "sdk.errors.package_conflict_active",
    "PACKAGE_UPDATE_VERSION_INVALID",
}
_UNSAFE_ERRORS = {
    "sdk.errors.package_active_in_campaign",
    "PACKAGE_UPDATE_DISABLE_FIRST",
    "PACKAGE_UPDATE_ACTIVE_IN_CAMPAIGN",
}
_EXTERNAL_ERRORS = {
    "MARKETPLACE_PACKAGE_UNAVAILABLE",
    "PACKAGE_DOWNLOAD_FAILED",
}


def _exit_code_for_error(error_key: str | None) -> int:
    if error_key in _UNSAFE_ERRORS:
        return EXIT_UNSAFE
    if error_key in _INCOMPATIBLE_ERRORS:
        return EXIT_INCOMPATIBLE
    if error_key in _EXTERNAL_ERRORS:
        return EXIT_MISSING_DEPENDENCY
    return EXIT_DOCTOR_ERROR


def _fail(
    error_key: str | None,
    *,
    code: int | None = None,
    as_json: bool = False,
    details: dict[str, Any] | None = None,
) -> int:
    key = error_key or "sdk.errors.unknown"
    code = code if code is not None else _exit_code_for_error(error_key)
    if as_json:
        _print_json({"ok": False, "error_key": key, "exit_code": code, **(details or {})})
        return code
    print(f"ERROR  {key}")
    fix = _ERROR_FIX.get(key)
    if fix:
        print(f"FIX    {fix}")
    return code


def _install_service():
    from app.engine.sdk.package_install_service import PackageInstallService

    return PackageInstallService()


def _activation_service():
    from app.engine.sdk.package_activation_service import PackageActivationService

    return PackageActivationService()


def _campaign_exists(campaign_id: str) -> bool:
    from app.persistence.repositories.campaign_repository import CampaignRepository

    return CampaignRepository().get(campaign_id) is not None





def cmd_list(args: argparse.Namespace) -> int:
    svc = _install_service()
    items = svc.list_for_kind(args.kind) if getattr(args, "kind", None) else svc.list_for_tab()
    if args.json:
        _print_json(
            {
                "packages": [
                    {
                        "id": i["id"],
                        "kind": i["kind"],
                        "version": i["version"],
                        "status": i["status"],
                        "scripted": i["scripted"],
                        "source": i["effective_source"],
                        "declared_source": i["declared_source"],
                        "source_certified": i["source_certified"],
                    }
                    for i in items
                ]
            }
        )
        return EXIT_OK
    if not items:
        print("No packages found.")
        return EXIT_OK
    for i in items:
        flag = " (trusted JS)" if i["scripted"] else ""
        source = i["effective_source"].upper()
        print(f"{i['status']:<11} {i['id']:<24} {i['kind']:<8} {i['version']:<12} {source}{flag}")
    return EXIT_OK





def _print_capabilities(loaded) -> None:
    from app.engine.sdk.package_manifest_validator import FORBIDDEN_CAPABILITIES

    m = loaded.manifest
    print(f"Package: {m.id}")
    print(f"Kind: {m.kind}")
    print(f"Version: {m.version}")
    print("")
    print("Requested capabilities:")
    for cap in m.capabilities or ["(none)"]:
        print(f"- {cap}")
    forbidden = sorted(set(m.capabilities) & FORBIDDEN_CAPABILITIES)
    if forbidden:
        print(f"\nFORBIDDEN capabilities present: {', '.join(forbidden)}")
    else:
        print("\nNo forbidden capabilities detected.")
    if m.has_scripts():
        print("This package runs trusted JavaScript in the table for everyone.")


def _confirm(yes: bool) -> bool:
    if yes:
        return True
    try:
        return input("Install? [y/N] ").strip().lower() in {"y", "yes"}
    except EOFError:
        return False


def cmd_install(args: argparse.Namespace) -> int:
    from app.engine.sdk.package_registry import load_by_package_id

    loaded = load_by_package_id(args.id)
    if loaded is None:
        return _fail("sdk.errors.not_found", as_json=args.json)

    expected_kind = getattr(args, "kind", None)
    if expected_kind and loaded.manifest.kind != expected_kind:
        if args.json:
            return _fail(
                "sdk.errors.wrong_kind",
                code=EXIT_INCOMPATIBLE,
                as_json=True,
                details={"actual_kind": loaded.manifest.kind, "expected_kind": expected_kind},
            )
        print(f"ERROR  {loaded.id} is kind '{loaded.manifest.kind}', expected '{expected_kind}'.")
        return EXIT_INCOMPATIBLE

    if not args.json:
        _print_capabilities(loaded)
    if args.json and not args.yes:
        return _fail("sdk.errors.confirmation_required", code=EXIT_UNSAFE, as_json=True)
    if not _confirm(args.yes):
        print("Aborted.")
        return EXIT_UNSAFE

    svc = _install_service()
    result = svc.install(package_id=loaded.id, user_id=None)
    if not result.success:
        return _fail(result.error_key, as_json=args.json)

    if args.enable:
        enabled = svc.enable(package_id=loaded.id)
        if not enabled.success:
            return _fail(enabled.error_key, as_json=args.json)
    if args.activate:
        if not args.enable:
            enabled = svc.enable(package_id=loaded.id)
            if not enabled.success:
                return _fail(enabled.error_key, as_json=args.json)
        activated = _activation_service().activate_package(args.activate, loaded.id, None)
        if not activated.success:
            return _fail(activated.error_key, as_json=args.json)

    if args.json:
        _print_json({"ok": True, "package_id": loaded.id})
    else:
        print(f"OK     Installed {loaded.id}.")
    return EXIT_OK





def _require_kind(
    svc, package_id: str, expected_kind: str | None, *, as_json: bool = False
) -> int | None:
    if not expected_kind:
        return None
    record = svc.get(package_id)
    if record and record["kind"] != expected_kind:
        if as_json:
            return _fail(
                "sdk.errors.wrong_kind",
                code=EXIT_INCOMPATIBLE,
                as_json=True,
                details={"actual_kind": record["kind"], "expected_kind": expected_kind},
            )
        print(f"ERROR  {package_id} is kind '{record['kind']}', expected '{expected_kind}'.")
        return EXIT_INCOMPATIBLE
    return None


def cmd_enable(args: argparse.Namespace) -> int:
    svc = _install_service()
    if (rc := _require_kind(svc, args.id, getattr(args, "kind", None))) is not None:
        return rc
    result = svc.enable(package_id=args.id)
    if not result.success:
        return _fail(result.error_key)
    print(f"OK     Enabled {args.id}.")
    return EXIT_OK


def cmd_disable(args: argparse.Namespace) -> int:
    svc = _install_service()
    if (rc := _require_kind(svc, args.id, getattr(args, "kind", None))) is not None:
        return rc
    result = svc.disable(package_id=args.id, force=args.force)
    if not result.success:
        code = (
            EXIT_UNSAFE
            if result.error_key == "sdk.errors.package_active_in_campaign"
            else EXIT_DOCTOR_ERROR
        )
        if result.active_campaign_ids:
            print(f"       active in campaigns: {', '.join(result.active_campaign_ids)}")
        return _fail(result.error_key, code=code)
    print(f"OK     Disabled {args.id}.")
    return EXIT_OK


def cmd_remove(args: argparse.Namespace) -> int:
    svc = _install_service()
    if (rc := _require_kind(svc, args.id, getattr(args, "kind", None))) is not None:
        return rc
    result = svc.remove(package_id=args.id, force=args.force)
    if not result.success:
        code = (
            EXIT_UNSAFE
            if result.error_key == "sdk.errors.package_active_in_campaign"
            else EXIT_DOCTOR_ERROR
        )
        if result.active_campaign_ids:
            print(f"       active in campaigns: {', '.join(result.active_campaign_ids)}")
        return _fail(result.error_key, code=code)
    print(f"OK     Removed {args.id}.")
    return EXIT_OK





def _update_one(svc, package_id: str) -> tuple[bool, str | None]:
    """Refresh an installed package's manifest from disk, preserving its status."""
    prior = svc.get(package_id)
    if prior is None:
        return False, "sdk.errors.not_installed"
    result = svc.install(package_id=package_id, user_id=None)
    if not result.success:
        return False, result.error_key
    if prior["status"] == "enabled":
        enabled = svc.enable(package_id=package_id)
        if not enabled.success:
            return False, enabled.error_key
    return True, None


def cmd_update(args: argparse.Namespace) -> int:
    svc = _install_service()
    expected_kind = getattr(args, "kind", None)
    if args.id == "all":
        targets = [
            record["id"]
            for record in svc.installed.list_all()
            if expected_kind is None or record["kind"] == expected_kind
        ]
    else:
        if (rc := _require_kind(svc, args.id, expected_kind, as_json=args.json)) is not None:
            return rc
        targets = [args.id]
    updated, failed = [], []
    marketplace = None
    if getattr(args, "remote", False):
        from app.engine.sdk.marketplace_service import MarketplaceService
        marketplace = MarketplaceService()
        marketplace.catalog_with_automatic_refresh()
    for package_id in targets:
        if getattr(args, "remote", False):
            from app.engine.sdk.marketplace_installer import MarketplaceInstaller
            result = MarketplaceInstaller(marketplace=marketplace).install(
                package_id=package_id, user_id=None
            )
            ok, error_key = result.success, result.error_key or None
        else:
            ok, error_key = _update_one(svc, package_id)
        (updated if ok else failed).append((package_id, error_key))
    exit_code = max((_exit_code_for_error(error) for _package, error in failed), default=EXIT_OK)
    if args.json:
        _print_json(
            {
                "ok": not failed,
                "exit_code": exit_code,
                "updated": [p for p, _ in updated],
                "failed": [{"id": p, "error_key": e} for p, e in failed],
            }
        )
    else:
        for p, _ in updated:
            print(f"OK     Updated {p}.")
        for p, e in failed:
            print(f"ERROR  {p}: {e}")
    return exit_code





def cmd_doctor(args: argparse.Namespace) -> int:
    from app.cli.doctor import ERROR, OK, WARN, Check, render_pretty, summarize
    from app.engine.sdk.package_doctor_service import PackageDoctorService
    from app.engine.sdk.package_registry import load_by_package_id

    checks: list[Check] = []
    loaded = load_by_package_id(args.id)
    if loaded is None:
        checks.append(
            Check("disk", ERROR, f"{args.id} not found on disk", fix="Check data/packages/")
        )
    else:
        if loaded.ok:
            checks.append(Check("manifest", OK, f"{args.id} manifest valid"))
        else:
            for err in loaded.validation.errors:
                checks.append(Check("manifest", ERROR, f"{args.id}: {err}"))
        for warn in loaded.validation.warnings:
            checks.append(Check("manifest", WARN, f"{args.id}: {warn}"))

    svc = _install_service()
    record = svc.get(args.id)
    if record is None:
        checks.append(
            Check(
                "install",
                WARN,
                f"{args.id} is not installed",
                fix=f"grave package install {args.id}",
            )
        )
    else:
        checks.append(Check("install", OK, f"installed (status: {record['status']})"))
        detail = svc.get_details(args.id) or {}
        provenance = detail.get("provenance") or {}
        source_status = OK if not provenance.get("mismatch") else WARN
        checks.append(Check(
            "provenance", source_status,
            f"declared={provenance.get('declaredSource') or 'none'} "
            f"effective={provenance.get('effectiveSource') or 'community'} "
            f"authority={provenance.get('authority') or 'manual'}",
        ))
        for finding in PackageDoctorService().audit():
            if finding.package_id != args.id:
                continue
            status = ERROR if finding.severity == "error" else WARN if finding.severity == "warning" else OK
            context = f" ({finding.campaign_id})" if finding.campaign_id else ""
            details = f": {finding.details}" if finding.details else ""
            checks.append(
                Check(
                    f"package:{finding.code}{context}",
                    status,
                    finding.message or f"{finding.code}{details}",
                    fix=_ERROR_FIX.get(finding.code),
                )
            )

    if args.json:
        from app.cli.doctor import render_json

        _print_json(render_json(checks))
    else:
        print(render_pretty(checks))
    return EXIT_OK if summarize(checks)["ok"] else EXIT_DOCTOR_ERROR





def _campaign_guard(campaign_id: str, *, as_json: bool = False) -> int | None:
    if not _campaign_exists(campaign_id):
        if as_json:
            return _fail(
                "sdk.errors.campaign_not_found",
                as_json=True,
                details={"campaign_id": campaign_id},
            )
        print(f"ERROR  campaign not found: {campaign_id}")
        print(
            "FIX    grave campaign package list <campaign_id> uses the campaign's id, not its title."
        )
        return EXIT_DOCTOR_ERROR
    return None


def cmd_campaign_list(args: argparse.Namespace) -> int:
    if (rc := _campaign_guard(args.campaign, as_json=args.json)) is not None:
        return rc
    rows = _activation_service().list_campaign_packages(args.campaign)
    if args.json:
        _print_json({"packages": rows})
        return EXIT_OK
    if not rows:
        print("No active packages in this campaign.")
        return EXIT_OK
    for r in rows:
        print(f"{r['package_id']:<24} {r.get('activation_role', ''):<8} {r.get('status', '')}")
    return EXIT_OK


def cmd_campaign_activate(args: argparse.Namespace) -> int:
    if (rc := _campaign_guard(args.campaign)) is not None:
        return rc
    result = _activation_service().activate_package(args.campaign, args.id, None)
    if not result.success:
        return _fail(result.error_key)
    print(f"OK     Activated {args.id} in campaign {args.campaign}.")
    return EXIT_OK


def cmd_campaign_deactivate(args: argparse.Namespace) -> int:
    if (rc := _campaign_guard(args.campaign)) is not None:
        return rc
    result = _activation_service().deactivate_package(args.campaign, args.id, None)
    if not result.success:
        return _fail(result.error_key)
    print(f"OK     Deactivated {args.id} in campaign {args.campaign}.")
    return EXIT_OK
