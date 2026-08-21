from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re
import shlex

import pytest

from app.cli import PACKAGE_KINDS, build_parser, main
from app.cli.bundled_packages import PACKAGE_KIND_DIRS
from app.cli.doctor import Check, OK, WARN, render_ai_prompt, render_json, summarize
from app.cli.scaffold import Intent, build_package, derive_capabilities
from app.cli.templates import RULESET_TEMPLATES
from app.cli import packages as package_commands
from app.engine.sdk.capability_registry import get_registry
from app.engine.sdk import package_registry
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.diagnostics import DoctorFinding
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_loader import load_package
from app.engine.sdk.package_manifest import KIND_TO_DIRECTORY, PackageKind


ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads((ROOT / "schemas/gravewright-package-v1.schema.json").read_text(encoding="utf-8"))


def _write_package(tmp_path: Path, package) -> Path:
    kind_dir = KIND_TO_DIRECTORY[package.manifest["kind"]]
    root = tmp_path / kind_dir / package.manifest["id"]
    for relative, content in package.files.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return root


def test_cli_package_kinds_derive_from_the_canonical_model_and_match_schema() -> None:
    schema_kinds = set(_schema()["properties"]["kind"]["enum"])
    assert set(PACKAGE_KINDS) == PackageKind.values() == schema_kinds
    assert set(PACKAGE_KIND_DIRS) == set(KIND_TO_DIRECTORY.values())


@pytest.mark.parametrize("kind", PACKAGE_KINDS)
def test_every_kind_scaffold_uses_only_public_manifest_fields_and_capabilities(
    kind: str,
) -> None:
    intent = Intent(
        has_sheets=kind == "ruleset",
        has_items=kind == "ruleset",
        has_rolls=kind == "ruleset",
        wants_content=kind in {"ruleset", "content", "addon"},
        wants_locales=True,
        wants_settings=kind in {"addon", "library", "theme"},
        uses_js=kind in {"addon", "library", "theme"},
        has_images=kind == "assets",
    )
    package = build_package(
        package_id=f"parity-{kind}", name=f"Parity {kind}", kind=kind, intent=intent
    )
    public_fields = set(_schema()["properties"])
    assert set(package.manifest) <= public_fields
    registry = get_registry()
    for capability in package.manifest["capabilities"]:
        assert registry.status_of(capability) == "stable"
        assert capability not in registry.forbidden_names()


@pytest.mark.parametrize("template", RULESET_TEMPLATES, ids=lambda template: template.id)
@pytest.mark.parametrize("html", [False, True], ids=["declarative", "html"])
def test_every_template_passes_loader_install_and_doctor(
    db, monkeypatch, tmp_path: Path, template, html: bool
) -> None:
    packages_root = tmp_path / "packages"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages_root)
    monkeypatch.setattr(package_registry, "STORAGE_PACKAGES_DIR", tmp_path / "package-storage")
    package = build_package(
        package_id=f"parity-{template.id}",
        name=template.label,
        kind=template.kind,
        intent=replace(template.intent, html_sheets=html),
    )
    package_dir = _write_package(packages_root, package)
    loaded = load_package(
        package_dir,
        expected_id=package.manifest["id"],
        expected_kind_root=KIND_TO_DIRECTORY[template.kind],
    )
    assert loaded.ok, loaded.validation.errors
    service = PackageInstallService()
    assert service.install(package_id=package.manifest["id"], user_id=None).success
    errors = [
        finding
        for finding in PackageDoctorService().audit()
        if finding.package_id == package.manifest["id"] and finding.severity == "error"
    ]
    assert errors == []
    assert service.remove(package_id=package.manifest["id"]).success


def test_new_content_scaffolds_emit_the_canonical_format_two_model() -> None:
    package = build_package(
        package_id="parity-content",
        name="Parity Content",
        kind="content",
        intent=Intent(wants_content=True),
    )
    declaration = package.manifest["provides"]["contentPacks"][0]
    document = json.loads(package.files[declaration["path"]])
    assert declaration["formatVersion"] == 2
    assert declaration["documentType"] == "journal"
    assert declaration["indexFields"]
    assert "index" in document and "entries" not in document


def test_strict_doctor_has_real_behavior_and_stable_json() -> None:
    checks = [Check("healthy", OK, "healthy"), Check("advice", WARN, "advice")]
    assert summarize(checks)["ok"] is True
    assert summarize(checks, strict=True)["ok"] is False
    assert render_json(checks, strict=True)["strict"] is True


def test_ai_prompt_keeps_bounded_authoring_guardrails() -> None:
    prompt = render_ai_prompt([Check("problem", WARN, "problem")])
    assert "Do not edit Gravewright core" in prompt
    assert "Do not invent capabilities" in prompt
    assert "Fix root causes before derived symptoms" in prompt
    assert "grave package validate" in prompt and "grave doctor" in prompt


def test_cli_has_no_signature_filter_or_dead_restore_flags() -> None:
    source = (ROOT / "app/cli/__init__.py").read_text(encoding="utf-8")
    assert "_call_compatible" not in source
    assert "inspect.signature" not in source
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["restore", "backup.zip", "--replace-assets"])


@pytest.mark.parametrize(
    "argv",
    [
        ["content", "new", "content-pack", "--rolls"],
        ["assets", "new", "asset-pack", "--settings"],
        ["theme", "new", "theme-pack", "--scene-tools"],
        ["addon", "new", "addon-pack", "--mechanic", "2d20"],
    ],
)
def test_kind_specific_parsers_reject_flags_without_semantics(argv: list[str]) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)


def test_template_cannot_silently_discard_intent_flags(capsys, tmp_path: Path) -> None:
    assert main(
        [
            "ruleset",
            "new",
            "template-conflict",
            "--template",
            "blank",
            "--rolls",
            "--name",
            "Conflict",
            "--output-dir",
            str(tmp_path),
            "--yes",
            "--json",
        ]
    ) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_key"] == "scaffold.template_intent_conflict"


def test_strict_doctor_flag_reaches_behavior_and_json_is_not_mixed(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    import app.cli.doctor as doctor

    monkeypatch.setattr(
        doctor,
        "run_doctor",
        lambda **_kwargs: [Check("warning", WARN, "warning")],
    )
    assert main(["doctor", "--packages-dir", str(tmp_path), "--skip-db", "--strict", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and payload["strict"] is True


def test_package_install_json_failure_is_one_structured_document(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(package_registry, "load_by_package_id", lambda _package_id: None)
    assert main(["package", "install", "missing-package", "--yes", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "error_key": "sdk.errors.not_found",
        "exit_code": 1,
        "ok": False,
    }


def test_package_install_json_requires_yes_without_prompting(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    packages_root = tmp_path / "packages"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages_root)
    package = build_package(
        package_id="confirmation-package",
        name="Confirmation",
        kind="addon",
        intent=Intent(),
    )
    _write_package(packages_root, package)
    assert main(["package", "install", "confirmation-package", "--json"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_key"] == "sdk.errors.confirmation_required"


def test_scaffold_json_failure_is_one_structured_document(capsys, tmp_path: Path) -> None:
    assert main(
        [
            "addon",
            "new",
            "INVALID ID",
            "--name",
            "Invalid",
            "--output-dir",
            str(tmp_path),
            "--json",
        ]
    ) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and payload["error_key"] == "scaffold.invalid_id"


def test_package_doctor_consumes_canonical_doctor_findings(
    db, monkeypatch, capsys, tmp_path: Path
) -> None:
    packages_root = tmp_path / "packages"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages_root)
    package = build_package(
        package_id="doctor-parity",
        name="Doctor Parity",
        kind="addon",
        intent=Intent(),
    )
    _write_package(packages_root, package)
    assert PackageInstallService().install(package_id="doctor-parity", user_id=None).success
    monkeypatch.setattr(
        PackageDoctorService,
        "audit",
        lambda _self: [
            DoctorFinding(
                code="sdk.manifest.snapshot_stale",
                severity="warning",
                package_id="doctor-parity",
            )
        ],
    )
    assert main(["package", "doctor", "doctor-parity", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert any(
        check["id"].startswith("package:sdk.manifest.snapshot_stale")
        for check in payload["checks"]
    )


@pytest.mark.parametrize(
    ("error_key", "exit_code"),
    [
        ("sdk.errors.invalid_manifest", 1),
        ("sdk.errors.package_active_in_campaign", 3),
        ("PACKAGE_DOWNLOAD_FAILED", 4),
        ("sdk.errors.incompatible", 5),
    ],
)
def test_package_error_classes_keep_the_stable_exit_code_contract(
    error_key: str, exit_code: int
) -> None:
    from app.cli.packages import _exit_code_for_error

    assert _exit_code_for_error(error_key) == exit_code


def test_per_kind_update_all_cannot_cross_package_kind(
    monkeypatch, capsys
) -> None:
    class Installed:
        @staticmethod
        def list_all() -> list[dict]:
            return [
                {"id": "addon-one", "kind": "addon"},
                {"id": "theme-one", "kind": "theme"},
            ]

    class Service:
        installed = Installed()

    calls: list[str] = []
    monkeypatch.setattr(package_commands, "_install_service", lambda: Service())
    monkeypatch.setattr(
        package_commands,
        "_update_one",
        lambda _service, package_id: calls.append(package_id) or (True, None),
    )
    from argparse import Namespace

    assert package_commands.cmd_update(
        Namespace(id="all", kind="addon", remote=False, json=True)
    ) == 0
    assert calls == ["addon-one"]
    assert json.loads(capsys.readouterr().out)["updated"] == ["addon-one"]


def test_every_scaffold_mapping_resolves_against_registry() -> None:
    for kind in PACKAGE_KINDS:
        capabilities = derive_capabilities(kind, Intent())
        assert set(capabilities) <= get_registry().known_names()


@pytest.mark.parametrize("document", ["docs/sdk/cli.md", "docs/pt-br/sdk/cli.md"])
def test_every_documented_grave_command_parses(document: str) -> None:
    parser = build_parser()
    text = (ROOT / document).read_text(encoding="utf-8")
    commands = [line for line in text.splitlines() if line.startswith("grave ")]
    assert commands
    replacements = {
        "path": "data/packages",
        "package": "sample-package",
        "package_id": "sample-package",
        "campaign_id": "sample-campaign",
    }
    for command in commands:
        expanded = command.replace("[", "").replace("]", "")
        expanded = re.sub(
            r"<([^>]+)>", lambda match: replacements.get(match.group(1), "sample"), expanded
        )
        arguments = shlex.split(expanded)[1:]
        try:
            parsed = parser.parse_args(arguments)
        except SystemExit as exc:  # pragma: no cover - assertion adds the command
            pytest.fail(f"documented command does not parse: {command} ({exc})")
        assert callable(parsed.func), command


@pytest.mark.parametrize("kind", PACKAGE_KINDS)
def test_generated_kind_matrix_loads_installs_enables_and_passes_doctor(
    db, monkeypatch, tmp_path: Path, kind: str
) -> None:
    packages_root = tmp_path / "packages"
    storage_root = tmp_path / "package-storage"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages_root)
    monkeypatch.setattr(package_registry, "STORAGE_PACKAGES_DIR", storage_root)
    package = build_package(
        package_id=f"matrix-{kind}",
        name=f"Matrix {kind}",
        kind=kind,
        intent=Intent(has_sheets=kind == "ruleset", wants_content=kind == "content"),
    )
    package_dir = _write_package(packages_root, package)
    loaded = load_package(
        package_dir,
        expected_id=package.manifest["id"],
        expected_kind_root=KIND_TO_DIRECTORY[kind],
    )
    assert loaded.ok, loaded.validation.errors

    service = PackageInstallService()
    assert service.install(package_id=package.manifest["id"], user_id=None).success
    assert service.enable(package_id=package.manifest["id"]).success
    findings = [
        finding
        for finding in PackageDoctorService().audit()
        if finding.package_id == package.manifest["id"] and finding.severity == "error"
    ]
    assert findings == []

    assert service.disable(package_id=package.manifest["id"]).success
    assert service.remove(package_id=package.manifest["id"]).success


@pytest.mark.parametrize("kind", PACKAGE_KINDS)
def test_public_cli_generated_package_loop_reaches_loader_lifecycle_and_doctor(
    db, monkeypatch, capsys, tmp_path: Path, kind: str
) -> None:
    packages_root = tmp_path / "packages"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages_root)
    monkeypatch.setattr(package_registry, "STORAGE_PACKAGES_DIR", tmp_path / "package-storage")
    package_id = f"cli-loop-{kind}"

    assert main(
        [
            kind,
            "new",
            package_id,
            "--name",
            f"CLI Loop {kind}",
            "--output-dir",
            str(packages_root),
            "--yes",
            "--json",
        ]
    ) == 0
    created = json.loads(capsys.readouterr().out)
    package_dir = Path(created["path"])
    assert created["ok"] is True

    assert main(["package", "validate", str(package_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert main(["package", "install", package_id, "--yes", "--enable", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert main(["package", "doctor", package_id, "--json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["ok"] is True
    assert not [check for check in doctor["checks"] if check["status"] == "error"]

    assert main(["package", "disable", package_id]) == 0
    capsys.readouterr()
    assert main(["package", "remove", package_id]) == 0


def test_ai_authoring_loop_reports_contract_error_then_accepts_package_only_fix(
    db, monkeypatch, capsys, tmp_path: Path
) -> None:
    packages_root = tmp_path / "packages"
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", packages_root)
    monkeypatch.setattr(package_registry, "STORAGE_PACKAGES_DIR", tmp_path / "package-storage")
    assert main(
        [
            "addon",
            "new",
            "ai-authoring-loop",
            "--name",
            "AI Authoring Loop",
            "--output-dir",
            str(packages_root),
            "--yes",
            "--json",
        ]
    ) == 0
    package_dir = Path(json.loads(capsys.readouterr().out)["path"])
    manifest_path = package_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["capabilities"].append("invented.capability")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert main(["package", "validate", str(package_dir), "--json"]) == 1
    invalid = json.loads(capsys.readouterr().out)
    assert invalid["packages"][0]["errors"] == ["sdk.validation.capability_unknown"]

    manifest["capabilities"].remove("invented.capability")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert main(["package", "validate", str(package_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert main(["package", "install", "ai-authoring-loop", "--yes", "--json"]) == 0
    capsys.readouterr()
    assert main(["package", "doctor", "ai-authoring-loop", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
