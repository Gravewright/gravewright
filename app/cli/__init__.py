"""Gravewright operator CLI.

The ``grave`` command is the local operator/developer interface.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
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


def _default_validation_path() -> Path:
    cwd = Path.cwd()
    return cwd if (cwd / "manifest.json").is_file() else _default_packages_dir()


_VALIDATION_LABELS = {
    "sdk.validation.manifest_missing": "manifest.json is missing",
    "sdk.validation.schema_version": "Schema version is missing or unsupported",
    "sdk.validation.sdk_version": "SDK version is missing or unsupported",
    "sdk.validation.id_invalid": "Package id is invalid",
    "sdk.validation.kind": "Package kind is invalid",
    "sdk.validation.path_unsafe": "A referenced path is unsafe",
    "sdk.manifest.id_mismatch": "Package id does not match its directory",
    "sdk.manifest.kind_root_mismatch": "Package kind does not match its parent directory",
}


def _validation_label(code: str) -> str:
    if code in _VALIDATION_LABELS:
        return _VALIDATION_LABELS[code]
    return code.rsplit(".", 1)[-1].replace("_", " ").capitalize()


def _render_package_validation(packages: list[dict[str, Any]], target: Path) -> None:
    """Render the human-oriented report; ``--json`` remains stable for tooling."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:  # pragma: no cover - Rich is a runtime dependency
        if not packages:
            print(f"ERROR  No packages found in {target}")
            return
        for package in packages:
            status = "OK" if package["ok"] else "ERROR"
            print(f"{status:<5}  {package['id']} ({package['kind']} {package['version']})")
            for code in package["errors"]:
                print(f"       ERROR  {_validation_label(code)} [{code}]")
            for code in package["warnings"]:
                print(f"       WARN   {_validation_label(code)} [{code}]")
        return

    console = Console()
    console.print(
        Panel.fit(
            Text.assemble(
                ("Package validation\n", "bold"),
                (str(target.resolve()), "dim"),
            ),
            border_style="yellow",
            padding=(0, 2),
        )
    )
    if not packages:
        console.print(
            Panel(
                "[red bold]No packages found.[/] Check the path or run this command "
                "inside a package directory.",
                border_style="red",
            )
        )
        return

    package_table = Table(show_header=True, header_style="bold", border_style="dim")
    package_table.add_column("Status", width=7, no_wrap=True)
    package_table.add_column("Package")
    package_table.add_column("Kind")
    package_table.add_column("Version")
    package_table.add_column("Path", style="dim")
    for package in packages:
        status = Text("PASS", style="green bold") if package["ok"] else Text("FAIL", style="red bold")
        package_table.add_row(
            status,
            str(package["id"]),
            str(package["kind"]),
            str(package["version"]),
            str(package["path"]),
        )
    console.print(package_table)

    issues = [
        (level, package["id"], code)
        for package in packages
        for level, codes in (("ERROR", package["errors"]), ("WARN", package["warnings"]))
        for code in codes
    ]
    if issues:
        issue_table = Table(title="Issues", title_justify="left", border_style="dim")
        issue_table.add_column("Level", width=7, no_wrap=True)
        issue_table.add_column("Package")
        issue_table.add_column("Problem")
        issue_table.add_column("Code", style="dim")
        for level, package_id, code in issues:
            style = "red bold" if level == "ERROR" else "yellow bold"
            issue_table.add_row(Text(level, style=style), package_id, _validation_label(code), code)
        console.print(issue_table)

    passed = sum(1 for package in packages if package["ok"])
    warnings = sum(len(package["warnings"]) for package in packages)
    failed = len(packages) - passed
    if failed:
        verdict = (
            f"[red bold]Validation failed.[/] {passed} passed, {failed} failed, "
            f"{warnings} warning(s).\nFix the issues above and run [bold]grave package validate[/bold] again."
        )
        border = "red"
    else:
        verdict = f"[green bold]Validation passed.[/] {passed} passed, {warnings} warning(s)."
        border = "green"
    console.print(Panel(verdict, border_style=border))


def _cmd_doctor(args: argparse.Namespace) -> int:
    from app.cli.doctor import render_ai_prompt, render_json, render_pretty, run_doctor, summarize
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
        print(_call_compatible(render_pretty, checks=checks, strict=strict, verbose=args.verbose))

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

    target = Path(args.path) if args.path else _default_validation_path()
    packages = [_loaded_payload(package) for package in _resolve_validation_targets(target)]
    ok = bool(packages) and all(package["ok"] for package in packages)
    if args.json:
        _print_json({"ok": ok, "packages": packages})
    else:
        _render_package_validation(packages, target)
    return EXIT_OK if ok else EXIT_DOCTOR_ERROR


def _intent_from_args(args: argparse.Namespace):
    from app.cli.scaffold import Intent

    return Intent(
        has_characters=args.has_characters,
        has_monsters=args.has_monsters,
        has_items=args.has_items,
        # ``--sheets`` is None (absent), [] (present, all types) or [names].
        # Explicit --actor-types/--item-types or --html-sheets also imply sheets.
        has_sheets=(
            args.sheets is not None
            or args.html_sheets
            or args.actor_types is not None
            or args.item_types is not None
        ),
        sheet_types=tuple(args.sheets) if args.sheets else None,
        actor_types=tuple(args.actor_types) if args.actor_types is not None else None,
        item_types=tuple(args.item_types) if args.item_types is not None else None,
        mechanic=args.mechanic,
        wants_biography=args.wants_biography,
        wants_notes=args.wants_notes,
        wants_effects=args.wants_effects,
        html_sheets=args.html_sheets,
        has_rolls=args.has_rolls,
        has_combat=args.has_combat,
        wants_content=args.wants_content,
        wants_settings=args.wants_settings,
        wants_locales=args.wants_locales,
        uses_js=args.uses_js,
        uses_sheet_runtime=args.uses_sheet_runtime,
        uses_combat_runtime=args.uses_combat_runtime,
        uses_scene_tools=args.uses_scene_tools,
        uses_scene_overlays=args.uses_scene_overlays,
        uses_token_extensions=args.uses_token_extensions,
        has_images=args.has_images,
        has_maps=args.has_maps,
        has_audio=args.has_audio,
        has_icons=args.has_icons,
    )


def _is_interactive() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def _no_intent_flags(args: argparse.Namespace) -> bool:
    """True when ``new`` was given no intent flags (pure defaults)."""
    return (
        args.has_characters is True  # the only flag defaulting on
        and args.sheets is None
        and args.actor_types is None
        and args.item_types is None
        and args.mechanic == "none"
        and not any(
            (
                args.has_monsters,
                args.has_items,
                args.html_sheets,
                args.wants_biography,
                args.wants_notes,
                args.wants_effects,
                args.has_rolls,
                args.has_combat,
                args.wants_content,
                args.wants_settings,
                args.wants_locales,
                args.uses_js,
                args.uses_sheet_runtime,
                args.uses_combat_runtime,
                args.uses_scene_tools,
                args.uses_scene_overlays,
                args.uses_token_extensions,
                args.has_images,
                args.has_maps,
                args.has_audio,
                args.has_icons,
            )
        )
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
    from app.cli.scaffold import (
        DEFAULT_VERSION,
        build_package,
        declared_sheet_type_ids,
        suggest_package_id,
    )
    from app.cli.templates import get_template, templates_for_kind
    from app.engine.sdk.package_loader import load_package
    from app.engine.sdk.package_manifest import KIND_TO_DIRECTORY
    from app.engine.sdk.package_paths import package_id_is_safe, safe_join

    if getattr(args, "list_templates", False):
        _print_templates(args.kind, as_json=args.json)
        return EXIT_OK

    template = None
    if getattr(args, "template", None):
        template = get_template(args.template)
        if template is None or template.kind != args.kind:
            available = ", ".join(t.id for t in templates_for_kind(args.kind)) or "(none)"
            if args.json:
                _print_json({
                    "ok": False,
                    "error_key": "scaffold.unknown_template",
                    "template": args.template,
                    "available": [t.id for t in templates_for_kind(args.kind)],
                })
            else:
                print(f"ERROR  unknown {args.kind} template: {args.template}")
                print(f"FIX    Available templates: {available}")
                print(f"       List them with: grave {args.kind} new --list-templates")
            return EXIT_DOCTOR_ERROR

    # Pick the wizard when explicitly asked, or by default on an interactive
    # terminal with no intent flags and no non-interactive markers (--yes/--json,
    # --template). A --template selection is a complete intent, so it never opens
    # the wizard.
    interactive = _is_interactive()
    use_wizard = args.wizard or (
        interactive
        and template is None
        and _no_intent_flags(args)
        and not args.yes
        and not args.json
    )
    if use_wizard and not interactive:
        if args.wizard:
            print("WARN  --wizard needs an interactive terminal; using flags/defaults.")
        use_wizard = False

    if template is not None:
        name = _prompt_value(args.name, "Package name") or template.name_suggestion
        intent = template.intent
    elif use_wizard:
        from app.cli.wizard import run_new_wizard

        result = run_new_wizard(args.kind, default_name=args.name)
        if result is None:
            print("Aborted.")
            return EXIT_UNSAFE
        name = result.name
        intent = result.intent
    else:
        name = _prompt_value(args.name, "Package name")
        if not name:
            print("ERROR  package name is required")
            return EXIT_DOCTOR_ERROR
        intent = _intent_from_args(args)

        # A named --sheets selection must reference types the ruleset declares.
        if args.kind == "ruleset" and args.sheets:
            declared = declared_sheet_type_ids(intent)
            unknown = [t for t in args.sheets if t not in declared]
            if unknown:
                if args.json:
                    _print_json({
                        "ok": False,
                        "error_key": "scaffold.unknown_sheet_types",
                        "unknown": unknown,
                        "declared": declared,
                    })
                else:
                    print(f"ERROR  --sheets names unknown types: {', '.join(unknown)}")
                    print(f"FIX    Declared types: {', '.join(declared) or '(none)'}")
                    print("       Declare types with --characters/--monsters/--items.")
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
        intent=intent,
    )
    # Packages live under the universal grouped layout
    # ``data/packages/{kind_plural}/{id}`` — the same layout discovery, install,
    # asset serving and storage expect. ``--output-dir`` is the packages root.
    root = Path(args.output_dir)
    kind_dir = KIND_TO_DIRECTORY.get(args.kind)
    package_dir = (root / kind_dir / package_id) if kind_dir else (root / package_id)
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

    loaded = load_package(package_dir, expected_id=package_id, expected_kind_root=kind_dir)
    ok = loaded.ok

    actor_sheets = _sheet_summary(scaffold.manifest, "actorTypes")
    item_sheets = _sheet_summary(scaffold.manifest, "itemTypes")
    mechanic = intent.mechanic

    if args.json:
        _print_json({
            "ok": ok,
            "package_id": package_id,
            "kind": args.kind,
            "path": str(package_dir),
            "actor_sheets": actor_sheets,
            "item_sheets": item_sheets,
            "mechanic": mechanic,
            "files": sorted(files),
            "validation_errors": list(loaded.validation.errors),
            "validation_warnings": list(loaded.validation.warnings),
        })
    else:
        _print_creation_summary(
            kind=args.kind,
            package_id=package_id,
            package_dir=package_dir,
            actor_sheets=actor_sheets,
            item_sheets=item_sheets,
            mechanic=mechanic,
            file_count=len(files),
            warnings=list(loaded.validation.warnings),
            errors=list(loaded.validation.errors),
        )

    return EXIT_OK if ok else EXIT_DOCTOR_ERROR


def _sheet_summary(manifest: dict, key: str) -> list[tuple[str, str]]:
    """``(type_id, template_path)`` for each type in ``provides[key]`` with a sheet."""
    out: list[tuple[str, str]] = []
    for type_def in manifest.get("provides", {}).get(key, []) or []:
        sheet = type_def.get("sheet")
        if isinstance(sheet, dict) and sheet.get("template"):
            out.append((type_def.get("id", ""), sheet["template"]))
    return out


def _print_creation_summary(
    *,
    kind: str,
    package_id: str,
    package_dir: Path,
    actor_sheets: list[tuple[str, str]],
    item_sheets: list[tuple[str, str]],
    mechanic: str,
    file_count: int,
    warnings: list[str],
    errors: list[str],
) -> None:
    """Render the post-creation summary with ``rich`` when available."""
    next_steps = [
        f"grave package validate {package_dir}",
        f"grave package install {package_id} --yes --enable",
    ]
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:  # pragma: no cover - rich ships with the runtime deps
        _print_creation_summary_plain(
            kind, package_dir, actor_sheets, item_sheets, mechanic, file_count,
            next_steps, warnings, errors,
        )
        return

    console = Console()
    console.print(
        Panel.fit(
            f"[bold green]Created {kind} package[/]\n[dim]{package_dir}[/]",
            border_style="green",
        )
    )
    for warning in warnings:
        console.print(f"[yellow]WARN[/]  {warning}")
    for error in errors:
        console.print(f"[red]ERROR[/]  {error}")

    def _sheet_table(heading: str, rows: list[tuple[str, str]]) -> None:
        if not rows:
            return
        table = Table(title=heading, title_justify="left", show_edge=False, pad_edge=False)
        table.add_column("Type", style="cyan", no_wrap=True)
        table.add_column("Sheet", style="dim")
        for tid, template in rows:
            table.add_row(tid, template)
        console.print(table)

    _sheet_table("Actor sheet types", actor_sheets)
    _sheet_table("Item sheet types", item_sheets)
    if kind == "ruleset":
        console.print(f"Core mechanic: [magenta]{mechanic}[/]")
    console.print(f"Files created: [bold]{file_count}[/]")
    console.print("\n[bold]Next:[/]")
    for step in next_steps:
        console.print(f"  [green]$[/] {step}")


def _print_creation_summary_plain(
    kind, package_dir, actor_sheets, item_sheets, mechanic, file_count,
    next_steps, warnings, errors,
) -> None:
    print(f"OK     Created {kind} package:")
    print(f"  {package_dir}")
    for warning in warnings:
        print(f"WARN   {warning}")
    for error in errors:
        print(f"ERROR  {error}")

    def _rows(heading, rows):
        if not rows:
            return
        print(f"\n{heading}:")
        width = max((len(tid) for tid, _ in rows), default=0)
        for tid, template in rows:
            print(f"  {tid.ljust(width)}  ->  {template}")

    _rows("Actor sheet types", actor_sheets)
    _rows("Item sheet types", item_sheets)
    if kind == "ruleset":
        print(f"\nCore mechanic:\n  {mechanic}")
    print(f"\nFiles created: {file_count}")
    print("\nNext:")
    for step in next_steps:
        print(f"  {step}")


def _print_templates(kind: str, *, as_json: bool) -> None:
    """List the ready-made templates available for ``kind``."""
    from app.cli.templates import templates_for_kind

    templates = templates_for_kind(kind)
    if as_json:
        _print_json({
            "ok": True,
            "kind": kind,
            "templates": [
                {
                    "id": t.id,
                    "label": t.label,
                    "tagline": t.tagline,
                    "description": t.description,
                }
                for t in templates
            ],
        })
        return

    if not templates:
        print(f"No templates available for {kind}.")
        print(f"Build one interactively with: grave {kind} new")
        return

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(
            title=f"{kind} templates",
            title_justify="left",
            show_edge=False,
            pad_edge=False,
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Template", style="bold")
        table.add_column("What you get", style="dim")
        for t in templates:
            table.add_row(t.id, t.label, t.tagline)
        console.print(table)
        console.print(
            f"\n[bold]Use one:[/]  [green]$[/] grave {kind} new --template "
            f"{templates[0].id} --name \"My Game\""
        )
    except ImportError:  # pragma: no cover - rich ships with the runtime deps
        width = max(len(t.id) for t in templates)
        print(f"{kind} templates:")
        for t in templates:
            print(f"  {t.id.ljust(width)}  {t.label} - {t.tagline}")
        print(f"\nUse one: grave {kind} new --template {templates[0].id} --name \"My Game\"")


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
    parser.add_argument(
        "path",
        nargs="?",
        help="package directory or package root (default: current package or data/packages)",
    )
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
    parser.add_argument(
        "--wizard",
        "-i",
        dest="wizard",
        action="store_true",
        help="interactive guided wizard (checkbox selection) instead of flags",
    )
    parser.add_argument(
        "--template",
        dest="template",
        default=None,
        metavar="ID",
        help="start from a ready-made template (see --list-templates). "
        "Non-interactive: combine with --name/--yes for scripted scaffolds.",
    )
    parser.add_argument(
        "--list-templates",
        dest="list_templates",
        action="store_true",
        help="list the available templates for this kind and exit",
    )
    _add_json(parser)

    from app.cli.scaffold import mechanic_ids

    parser.add_argument(
        "--actor-types",
        dest="actor_types",
        nargs="*",
        default=None,
        metavar="TYPE",
        help="actor sheet type ids to generate (e.g. --actor-types character npc). "
        "Supersedes --characters/--monsters.",
    )
    parser.add_argument(
        "--item-types",
        dest="item_types",
        nargs="*",
        default=None,
        metavar="TYPE",
        help="item sheet type ids to generate (e.g. --item-types weapon spell). "
        "Supersedes --items.",
    )
    parser.add_argument(
        "--mechanic",
        dest="mechanic",
        default="none",
        choices=mechanic_ids(),
        help="core dice mechanic seeded into the character sheet (default: none)",
    )
    parser.add_argument(
        "--biography",
        dest="wants_biography",
        action="store_true",
        help="add a text-only Biography section to actor sheets",
    )
    parser.add_argument(
        "--notes",
        dest="wants_notes",
        action="store_true",
        help="add a text-only Notes section to actor sheets",
    )
    parser.add_argument(
        "--effects",
        dest="wants_effects",
        action="store_true",
        help="add an effect item type and an Active Effects area to actor sheets",
    )
    parser.add_argument("--characters", dest="has_characters", action="store_true", default=True)
    parser.add_argument("--no-characters", dest="has_characters", action="store_false")
    parser.add_argument("--monsters", dest="has_monsters", action="store_true")
    parser.add_argument("--items", dest="has_items", action="store_true")
    parser.add_argument(
        "--sheets",
        dest="sheets",
        nargs="*",
        default=None,
        metavar="TYPE",
        help="legacy: generate sheets for declared types (prefer --actor-types/--item-types)",
    )
    parser.add_argument(
        "--html-sheets",
        dest="html_sheets",
        action="store_true",
        help="scaffold HTML-mode sheets (template + CSS, plus an inventory controller "
        "when the ruleset has items) instead of declarative Sheet IR; implies --sheets",
    )
    parser.add_argument("--rolls", dest="has_rolls", action="store_true")
    parser.add_argument("--combat", dest="has_combat", action="store_true")
    parser.add_argument("--content", dest="wants_content", action="store_true")
    parser.add_argument("--settings", dest="wants_settings", action="store_true")
    parser.add_argument("--locales", dest="wants_locales", action="store_true")
    parser.add_argument("--js", dest="uses_js", action="store_true")
    parser.add_argument("--sheet-runtime", dest="uses_sheet_runtime", action="store_true")
    parser.add_argument("--combat-runtime", dest="uses_combat_runtime", action="store_true")
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
