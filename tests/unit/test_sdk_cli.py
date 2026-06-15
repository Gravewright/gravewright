from __future__ import annotations

import json
from pathlib import Path

from app.cli import main


def test_cli_doctor_json_reports_health(db, capsys):
    exit_code = main(["doctor", "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    by_id = {c["id"]: c for c in payload["checks"]}
    # Environment, packages and database all reported.
    assert by_id["python"]["status"] == "ok"
    assert by_id["sdk_schema"]["status"] == "ok"
    assert by_id["database"]["status"] == "ok"
    # The bundled packages validate.
    assert by_id["packages"]["status"] == "ok"
    assert "2/2" in by_id["packages"]["message"] or "/2" in by_id["packages"]["message"]


def test_cli_doctor_text_ends_with_ready(db, capsys):
    exit_code = main(["doctor"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "OK, ready to play." in out
    assert out.splitlines()[0].startswith("OK")


def test_cli_doctor_ai_prompt(db, capsys):
    exit_code = main(["doctor", "--ai"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Copy this prompt into your AI assistant" in out
    assert "Do not edit Gravewright core." in out


def test_cli_doctor_skip_db_omits_database_check(db, capsys):
    exit_code = main(["doctor", "--json", "--skip-db"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    ids = {c["id"] for c in payload["checks"]}
    assert "database" not in ids
    assert "python" in ids


def test_cli_package_validate_fails_invalid_manifest(tmp_path: Path, capsys):
    package_dir = tmp_path / "bad-package"
    package_dir.mkdir()
    (package_dir / "manifest.json").write_text('{"id": "Bad"}', encoding="utf-8")

    exit_code = main(["package", "validate", str(package_dir), "--json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert "sdk.validation.schema_version" in payload["packages"][0]["errors"]
    assert "sdk.validation.id_invalid" in payload["packages"][0]["errors"]


def test_cli_package_validate_discovers_package_root(tmp_path: Path, capsys):
    package_root = tmp_path / "packages"
    package_dir = package_root / "demo-addon"
    package_dir.mkdir(parents=True)
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sdkVersion": "1",
                "kind": "addon",
                "id": "demo-addon",
                "name": "Demo Addon",
                "version": "0.1.0",
                "compatibility": {"minimum": "0.0.1", "verified": "0.0.1"},
                "capabilities": [],
                "activation": {"mode": "multiple"},
                "entrypoints": {"game": {"scripts": ["assets/demo.js"]}},
                "provides": {},
            }
        ),
        encoding="utf-8",
    )
    (package_dir / "assets").mkdir()
    (package_dir / "assets" / "demo.js").write_text("// demo", encoding="utf-8")

    exit_code = main(["package", "validate", str(package_root), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert [package["id"] for package in payload["packages"]] == ["demo-addon"]
    assert payload["packages"][0]["trusted_code_required"] is True
