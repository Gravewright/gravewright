"""Gravewright operator CLI.

The ``grave`` command is the local operator/developer interface.
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any, Sequence

from app.config import config

PACKAGE_KINDS = ("ruleset", "addon", "library", "theme", "assets", "content")


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() in {"y", "yes"}
    except EOFError:
        return False


def _default_packages_dir() -> Path:
    return Path(config.data_dir) / "packages"


def _call_compatible(fn, /, **kwargs):
    """Call a function with only the keyword args it currently accepts.

    This keeps the CLI parser compatible with both the current project modules
    and the fuller CLI modules generated during the SDK tooling pass.
    """
    params = inspect.signature(fn).parameters
    return fn(**{key: value for key, value in kwargs.items() if key in params})


def _manifest_has_scripts(manifest: Any) -> bool:
    method = getattr(manifest, "has_scripts", None)
    if callable(method):
        return bool(method())

    entrypoints = getattr(manifest, "entrypoints", {}) or {}
    for entrypoint in entrypoints.values():
        if getattr(entrypoint, "scripts", None):
            return True
        if isinstance(entrypoint, dict) and entrypoint.get("scripts"):
            return True
    return False


def _package_trusted_code_required(package) -> bool:
    attr = getattr(package, "trusted_code_required", None)
    if attr is not None:
        return bool(attr)
    return _manifest_has_scripts(package.manifest)


def _package_cmd(name: str):
    def _dispatch(args: argparse.Namespace) -> int:
        from app.cli import packages as package_commands

        return int(getattr(package_commands, name)(args))

    return _dispatch


def _loaded_payload(package) -> dict[str, Any]:
    return {
        "id": package.id,
        "kind": package.manifest.kind,
        "version": package.manifest.version,
        "path": str(package.package_dir),
        "ok": package.ok,
        "compatibility_status": package.validation.compatibility_status,
        "errors": list(package.validation.errors),
        "warnings": list(package.validation.warnings),
        "trusted_code_required": _package_trusted_code_required(package),
    }


def _resolve_validation_targets(path: Path) -> list:
    from app.engine.sdk.package_loader import load_package
    from app.engine.sdk.package_registry import load_all

    if (path / "manifest.json").is_file():
        return [load_package(path)]
    return load_all(path)


def _cmd_doctor(args: argparse.Namespace) -> int:
    from app.cli.doctor import render_ai_prompt, render_json, render_text, run_doctor, summarize
    from app.cli.exit_codes import EXIT_DOCTOR_ERROR, EXIT_OK

    strict = getattr(args, "strict", False)

    checks = _call_compatible(
        run_doctor,
        packages_dir=Path(args.packages_dir),
        skip_db=args.skip_db,
        strict=strict,
    )

    if args.json:
        _print_json(_call_compatible(render_json, checks=checks, strict=strict))
    elif args.ai:
        print(_call_compatible(render_ai_prompt, checks=checks, strict=strict))
    else:
        print(_call_compatible(render_text, checks=checks, strict=strict, verbose=args.verbose))

    summary = _call_compatible(summarize, checks=checks, strict=strict)
    return EXIT_OK if summary["ok"] else EXIT_DOCTOR_ERROR


def _cmd_run(args: argparse.Namespace) -> int:
    from app.cli.doctor import render_check_lines
    from app.cli.run import prepare, serve

    checks, abort = prepare(
        no_install=args.no_install,
        no_migrate=args.no_migrate,
        strict_doctor=args.strict_doctor,
    )
    for line in render_check_lines(checks, verbose=args.verbose):
        print(line)
    if abort is not None:
        return abort
    return serve(host=args.host, port=args.port, dev=args.dev, open_browser=args.open)


def _cmd_backup(args: argparse.Namespace) -> int:
    from app.cli.backup import create_backup, default_backup_name

    out_arg = getattr(args, "out", None) or getattr(args, "out_pos", None)
    out = Path(out_arg) if out_arg else Path(default_backup_name())
    exit_code, _manifest = _call_compatible(
        create_backup,
        out=out,
        include_assets=args.include_assets,
        include_packages=args.include_packages,
        verify=getattr(args, "verify", True),
    )
    return exit_code


def _cmd_restore(args: argparse.Namespace) -> int:
    from app.cli.backup import restore_backup

    return _call_compatible(
        restore_backup,
        path=Path(args.path),
        dry_run=args.dry_run,
        yes=args.yes,
        replace_assets=args.replace_assets,
        replace_packages=args.replace_packages,
    )


def _cmd_lock(args: argparse.Namespace) -> int:
    from app.cli.exit_codes import EXIT_DOCTOR_ERROR, EXIT_OK
    from app.cli.lockfile import write_lock

    try:
        out = getattr(args, "out", None) or getattr(args, "path", None)
        payload = write_lock(Path(out) if out else None)
    except Exception as exc:  # noqa: BLE001
        if args.json:
            _print_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        else:
            print(f"ERROR  could not write grave.lock.json: {type(exc).__name__}: {exc}")
            print("FIX    Check write permissions and run grave doctor.")
        return EXIT_DOCTOR_ERROR

    if args.json:
        _print_json({"ok": True, "lock": payload})
    else:
        print("OK     grave.lock.json written.")
    return EXIT_OK


def _cmd_package_validate(args: argparse.Namespace) -> int:
    from app.cli.exit_codes import EXIT_DOCTOR_ERROR, EXIT_OK

    packages = [_loaded_payload(package) for package in _resolve_validation_targets(Path(args.path))]
    ok = all(package["ok"] for package in packages)
    if args.json:
        _print_json({"ok": ok, "packages": packages})
    else:
        if not packages:
            print("No packages found.")
        for package in packages:
            status = "ok" if package["ok"] else "error"
            print(f"{package['id']}: {status}")
            for error in package["errors"]:
                print(f"  error: {error}")
            for warning in package["warnings"]:
                print(f"  warning: {warning}")
    return EXIT_OK if ok else EXIT_DOCTOR_ERROR


def _intent_from_args(args: argparse.Namespace):
    from app.cli.scaffold import Intent

    return Intent(
        has_characters=args.has_characters,
        has_monsters=args.has_monsters,
        has_items=args.has_items,
        has_sheets=args.has_sheets,
        has_rolls=args.has_rolls,
        has_combat=args.has_combat,
        wants_content=args.wants_content,
        wants_settings=args.wants_settings,
        wants_locales=args.wants_locales,
        uses_js=args.uses_js,
        uses_hooks=args.uses_hooks,
        uses_sheet_hooks=args.uses_sheet_hooks,
        uses_combat_hooks=args.uses_combat_hooks,
        uses_scene_tools=args.uses_scene_tools,
        uses_scene_overlays=args.uses_scene_overlays,
        uses_token_extensions=args.uses_token_extensions,
        has_images=args.has_images,
        has_maps=args.has_maps,
        has_audio=args.has_audio,
        has_icons=args.has_icons,
    )


def _prompt_value(value: str | None, label: str) -> str | None:
    if value:
        return value
    try:
        entered = input(f"{label}: ").strip()
    except EOFError:
        return None
    return entered or None


def _cmd_new(args: argparse.Namespace) -> int:
    from app.cli.exit_codes import EXIT_DOCTOR_ERROR, EXIT_OK, EXIT_UNSAFE
    from app.cli.scaffold import DEFAULT_VERSION, build_package, suggest_package_id
    from app.engine.sdk.package_loader import load_package
    from app.engine.sdk.package_paths import package_id_is_safe, safe_join

    name = _prompt_value(args.name, "Package name")
    if not name:
        print("ERROR  package name is required")
        return EXIT_DOCTOR_ERROR

    package_id = args.id or suggest_package_id(name)
    if not package_id_is_safe(package_id):
        print(f"ERROR  invalid package id: {package_id}")
        print("FIX    Use lowercase kebab-case, for example: my-package")
        return EXIT_DOCTOR_ERROR

    scaffold = build_package(
        package_id=package_id,
        name=name,
        version=args.version or DEFAULT_VERSION,
        kind=args.kind,
        intent=_intent_from_args(args),
    )
    root = Path(args.output_dir)
    package_dir = root / package_id
    files = scaffold.files

    if args.dry_run:
        if args.json:
            _print_json({
                "ok": True,
                "dry_run": True,
                "package_id": package_id,
                "kind": args.kind,
                "path": str(package_dir),
                "files": sorted(files),
                "manifest": scaffold.manifest,
            })
        else:
            print(f"Would create {package_dir}")
            for rel in sorted(files):
                print(f"- {rel}")
        return EXIT_OK

    conflicts: list[str] = []
    unsafe: list[str] = []
    for rel in files:
        dest = safe_join(package_dir, rel)
        if dest is None:
            unsafe.append(rel)
        elif dest.exists() and not args.force:
            conflicts.append(rel)

    if unsafe:
        if args.json:
            _print_json({"ok": False, "error_key": "scaffold.unsafe_path", "paths": unsafe})
        else:
            print("ERROR  scaffold generated unsafe paths:")
            for rel in unsafe:
                print(f"- {rel}")
        return EXIT_DOCTOR_ERROR

    if conflicts:
        if args.json:
            _print_json({
                "ok": False,
                "error_key": "scaffold.files_exist",
                "paths": conflicts,
                "fix": "Pass --force to overwrite existing files.",
            })
        else:
            print(f"ERROR  {package_dir} already has files that would be overwritten:")
            for rel in conflicts:
                print(f"- {rel}")
            print("FIX    Pass --force to overwrite, or choose a different id.")
        return EXIT_UNSAFE

    if not args.yes:
        print(f"Create {args.kind} package at {package_dir}?")
        print(f"Files: {len(files)}")
        if not _confirm("Create? [y/N] "):
            print("Aborted.")
            return EXIT_UNSAFE

    package_dir.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        dest = safe_join(package_dir, rel)
        if dest is None:
            print(f"ERROR  unsafe generated path: {rel}")
            return EXIT_DOCTOR_ERROR
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

    loaded = load_package(package_dir)
    ok = loaded.ok

    if args.json:
        _print_json({
            "ok": ok,
            "package_id": package_id,
            "kind": args.kind,
            "path": str(package_dir),
            "files": sorted(files),
            "validation_errors": list(loaded.validation.errors),
            "validation_warnings": list(loaded.validation.warnings),
        })
    else:
        print(f"OK     Created {args.kind} package: {package_dir}")
        for warning in loaded.validation.warnings:
            print(f"WARN   {warning}")
        for error in loaded.validation.errors:
            print(f"ERROR  {error}")
        print("")
        print("Next:")
        print(f"  grave package validate {package_dir}")
        print(f"  grave package install {package_id} --yes --enable")

    return EXIT_OK if ok else EXIT_DOCTOR_ERROR


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def _add_package_list_parser(sub) -> None:
    parser = sub.add_parser("list", help="list discovered SDK packages")
    parser.add_argument("--kind", choices=PACKAGE_KINDS)
    _add_json(parser)
    parser.set_defaults(func=_package_cmd("cmd_list"))


def _add_package_install_parser(sub, *, kind: str | None = None) -> None:
    parser = sub.add_parser("install", help="install a bundled package from data/packages")
    parser.add_argument("id", help="package id")
    parser.add_argument("--yes", action="store_true", help="skip confirmation")
    parser.add_argument("--enable", action="store_true", help="enable globally after install")
    parser.add_argument("--activate", metavar="CAMPAIGN_ID")
    _add_json(parser)
    parser.set_defaults(func=_package_cmd("cmd_install"), kind=kind)


def _add_package_enable_parser(sub, *, kind: str | None = None) -> None:
    parser = sub.add_parser("enable", help="enable an installed package globally")
    parser.add_argument("id", help="package id")
    parser.set_defaults(func=_package_cmd("cmd_enable"), kind=kind)


def _add_package_disable_parser(sub, *, kind: str | None = None) -> None:
    parser = sub.add_parser("disable", help="disable an installed package globally")
    parser.add_argument("id", help="package id")
    parser.add_argument("--force", action="store_true")
    parser.set_defaults(func=_package_cmd("cmd_disable"), kind=kind)


def _add_package_remove_parser(sub, *, kind: str | None = None) -> None:
    parser = sub.add_parser("remove", help="remove an installed package record")
    parser.add_argument("id", help="package id")
    parser.add_argument("--force", action="store_true")
    parser.set_defaults(func=_package_cmd("cmd_remove"), kind=kind)


def _add_package_update_parser(sub, *, kind: str | None = None) -> None:
    parser = sub.add_parser("update", help="refresh package metadata from disk")
    parser.add_argument("id", help="package id, or 'all'")
    _add_json(parser)
    parser.set_defaults(func=_package_cmd("cmd_update"), kind=kind)


def _add_package_doctor_parser(sub, *, kind: str | None = None) -> None:
    parser = sub.add_parser("doctor", help="diagnose one package")
    parser.add_argument("id", help="package id")
    _add_json(parser)
    parser.set_defaults(func=_package_cmd("cmd_doctor"), kind=kind)


def _add_package_validate_parser(sub) -> None:
    parser = sub.add_parser("validate", help="validate one package directory or package root")
    parser.add_argument("path")
    _add_json(parser)
    parser.set_defaults(func=_cmd_package_validate)


def _add_new_parser(sub, *, kind: str) -> None:
    parser = sub.add_parser("new", help=f"create a new {kind} package scaffold")
    parser.add_argument("id", nargs="?", help="package id; defaults to slugified --name")
    parser.add_argument("--name", help="display name; prompted when omitted")
    parser.add_argument("--version", default=None)
    parser.add_argument("--output-dir", default=str(_default_packages_dir()))
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    _add_json(parser)

    parser.add_argument("--characters", dest="has_characters", action="store_true", default=True)
    parser.add_argument("--no-characters", dest="has_characters", action="store_false")
    parser.add_argument("--monsters", dest="has_monsters", action="store_true")
    parser.add_argument("--items", dest="has_items", action="store_true")
    parser.add_argument("--sheets", dest="has_sheets", action="store_true")
    parser.add_argument("--rolls", dest="has_rolls", action="store_true")
    parser.add_argument("--combat", dest="has_combat", action="store_true")
    parser.add_argument("--content", dest="wants_content", action="store_true")
    parser.add_argument("--settings", dest="wants_settings", action="store_true")
    parser.add_argument("--locales", dest="wants_locales", action="store_true")
    parser.add_argument("--js", dest="uses_js", action="store_true")
    parser.add_argument("--hooks", dest="uses_hooks", action="store_true")
    parser.add_argument("--sheet-hooks", dest="uses_sheet_hooks", action="store_true")
    parser.add_argument("--combat-hooks", dest="uses_combat_hooks", action="store_true")
    parser.add_argument("--scene-tools", dest="uses_scene_tools", action="store_true")
    parser.add_argument("--scene-overlays", dest="uses_scene_overlays", action="store_true")
    parser.add_argument("--tokens", dest="uses_token_extensions", action="store_true")
    parser.add_argument("--images", dest="has_images", action="store_true")
    parser.add_argument("--maps", dest="has_maps", action="store_true")
    parser.add_argument("--audio", dest="has_audio", action="store_true")
    parser.add_argument("--icons", dest="has_icons", action="store_true")
    parser.set_defaults(func=_cmd_new, kind=kind)


def _add_package_subcommands(package_sub) -> None:
    _add_package_list_parser(package_sub)
    _add_package_install_parser(package_sub)
    _add_package_enable_parser(package_sub)
    _add_package_disable_parser(package_sub)
    _add_package_remove_parser(package_sub)
    _add_package_update_parser(package_sub)
    _add_package_doctor_parser(package_sub)
    _add_package_validate_parser(package_sub)


def _add_kind_command(sub, *, kind: str) -> None:
    parser = sub.add_parser(kind, help=f"{kind} package commands")
    kind_sub = parser.add_subparsers(dest=f"{kind}_command", required=True)

    list_parser = kind_sub.add_parser("list", help=f"list {kind} packages")
    _add_json(list_parser)
    list_parser.set_defaults(func=_package_cmd("cmd_list"), kind=kind)

    _add_package_install_parser(kind_sub, kind=kind)
    _add_package_enable_parser(kind_sub, kind=kind)
    _add_package_disable_parser(kind_sub, kind=kind)
    _add_package_remove_parser(kind_sub, kind=kind)
    _add_package_update_parser(kind_sub, kind=kind)
    _add_package_doctor_parser(kind_sub, kind=kind)
    _add_new_parser(kind_sub, kind=kind)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grave", description="Gravewright operator CLI")
    parser.add_argument("--version", action="version", version=f"Gravewright {config.gravewright_version}")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="diagnose the local Gravewright install")
    doctor.add_argument("--packages-dir", default=str(_default_packages_dir()))
    doctor.add_argument("--skip-db", action="store_true")
    doctor.add_argument("--strict", action="store_true")
    doctor.add_argument("--verbose", action="store_true")
    doctor_output = doctor.add_mutually_exclusive_group()
    doctor_output.add_argument("--json", action="store_true")
    doctor_output.add_argument("--ai", action="store_true")
    doctor.set_defaults(func=_cmd_doctor)

    run = sub.add_parser("run", help="prepare basics and start the server")
    run.add_argument("--host", default="127.0.0.1")
    run.add_argument("--port", type=int, default=8000)
    run.add_argument("--dev", action="store_true")
    run.add_argument("--open", action="store_true")
    run.add_argument("--no-install", action="store_true")
    run.add_argument("--no-migrate", action="store_true")
    run.add_argument("--strict-doctor", action="store_true")
    run.add_argument("--verbose", action="store_true")
    run.set_defaults(func=_cmd_run)

    backup = sub.add_parser("backup", help="write a Gravewright backup zip")
    backup.add_argument("out_pos", nargs="?", help="output zip path")
    backup.add_argument("-o", "--output", dest="out", help="output zip path")
    backup.add_argument("--include-assets", action="store_true")
    backup.add_argument("--include-packages", action="store_true")
    backup.add_argument("--verify", dest="verify", action="store_true", default=True)
    backup.add_argument("--no-verify", dest="verify", action="store_false")
    backup.set_defaults(func=_cmd_backup)

    restore = sub.add_parser("restore", help="restore a Gravewright backup zip")
    restore.add_argument("path")
    restore.add_argument("--dry-run", action="store_true")
    restore.add_argument("--yes", action="store_true")
    restore.add_argument("--replace-assets", action="store_true")
    restore.add_argument("--replace-packages", action="store_true")
    restore.set_defaults(func=_cmd_restore)

    lock = sub.add_parser("lock", help="write grave.lock.json")
    lock.add_argument("-o", "--output", dest="out", help="custom lockfile path")
    lock.add_argument("--path", help="custom lockfile path")
    _add_json(lock)
    lock.set_defaults(func=_cmd_lock)

    package = sub.add_parser("package", help="manage SDK packages")
    package_sub = package.add_subparsers(dest="package_command", required=True)
    _add_package_subcommands(package_sub)

    campaign = sub.add_parser("campaign", help="campaign-level operations")
    campaign_sub = campaign.add_subparsers(dest="campaign_command", required=True)
    campaign_package = campaign_sub.add_parser("package", help="campaign package activation")
    campaign_package_sub = campaign_package.add_subparsers(dest="campaign_package_command", required=True)

    campaign_package_list = campaign_package_sub.add_parser("list", help="list active packages in a campaign")
    campaign_package_list.add_argument("campaign")
    _add_json(campaign_package_list)
    campaign_package_list.set_defaults(func=_package_cmd("cmd_campaign_list"))

    campaign_package_activate = campaign_package_sub.add_parser("activate", help="activate a package in a campaign")
    campaign_package_activate.add_argument("campaign")
    campaign_package_activate.add_argument("id")
    campaign_package_activate.set_defaults(func=_package_cmd("cmd_campaign_activate"))

    campaign_package_deactivate = campaign_package_sub.add_parser("deactivate", help="deactivate a package in a campaign")
    campaign_package_deactivate.add_argument("campaign")
    campaign_package_deactivate.add_argument("id")
    campaign_package_deactivate.set_defaults(func=_package_cmd("cmd_campaign_deactivate"))

    for kind in PACKAGE_KINDS:
        _add_kind_command(sub, kind=kind)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


__all__ = ["build_parser", "main"]
