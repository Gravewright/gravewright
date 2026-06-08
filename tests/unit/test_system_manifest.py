from __future__ import annotations

import json

from app.engine.systems import system_registry
from app.engine.systems.system_loader import SYSTEMS_DIR, load_package, safe_join
from app.engine.systems.system_manifest_validator import (
    COMPAT_INCOMPATIBLE,
    validate_manifest,
)


def _valid_manifest() -> dict:
    return {
        "manifestVersion": 1,
        "type": "system",
        "id": "dnd5e",
        "name": "Dungeons & Dragons 5e",
        "version": "0.1.0",
        "apiVersion": "1",
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["actors.register", "sheets.declarative", "dice.roll"],
        "system": {
            "id": "dnd5e",
            "storage": {"model": "scoped-json-v1"},
            "actorTypes": [
                {"id": "character", "label": "Character", "schema": "schemas/c.json", "sheet": "layouts/c.json"}
            ],
        },
    }


def test_valid_manifest_passes():
    result = validate_manifest(_valid_manifest())
    assert result.ok
    assert result.errors == []
    assert result.compatibility_status == "compatible"


def test_invalid_id_is_rejected():
    raw = _valid_manifest()
    raw["id"] = "Dungeons & Dragons 5e"
    result = validate_manifest(raw)
    assert "inside.systems.validation.id_invalid" in result.errors


def test_forbidden_capability_is_rejected():
    raw = _valid_manifest()
    raw["capabilities"].append("backend.execute")
    result = validate_manifest(raw)
    assert "inside.systems.validation.capability_forbidden" in result.errors


def test_missing_system_block_is_rejected():
    raw = _valid_manifest()
    del raw["system"]
    result = validate_manifest(raw)
    assert "inside.systems.validation.system_required" in result.errors


def test_unsafe_path_is_rejected():
    raw = _valid_manifest()
    raw["system"]["actorTypes"][0]["schema"] = "../../etc/passwd"
    result = validate_manifest(raw)
    assert "inside.systems.validation.path_unsafe" in result.errors


def test_system_id_mismatch_is_rejected():
    raw = _valid_manifest()
    raw["system"]["id"] = "other-id"
    result = validate_manifest(raw)
    assert "inside.systems.validation.system_id_mismatch" in result.errors


def test_incompatible_maximum_marks_incompatible():
    raw = _valid_manifest()
    raw["compatibility"] = {"minimum": "0.1.0", "verified": "0.1.0", "maximum": "0.9.0"}
    result = validate_manifest(raw)
    assert result.compatibility_status == COMPAT_INCOMPATIBLE
    assert "inside.systems.validation.incompatible" in result.errors


def test_safe_join_blocks_traversal():
    assert safe_join(SYSTEMS_DIR, "dnd5e/manifest.json") is not None
    assert safe_join(SYSTEMS_DIR, "../../etc/passwd") is None


def test_invalid_manifest_package_reports_errors(tmp_path):
    package_dir = tmp_path / "invalid-system"
    package_dir.mkdir()
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "manifestVersion": 1,
                "type": "system",
                "id": "Invalid System",
                "name": "Invalid System",
                "version": "0.1.0",
                "apiVersion": "1",
                "compatibility": {
                    "minimum": "1.0.0-rc.1",
                    "verified": "1.0.0-rc.1",
                    "maximum": "1.x",
                },
                "capabilities": ["actors.register", "sheets.declarative", "dice.roll"],
                "system": {
                    "id": "Invalid System",
                    "storage": {"model": "scoped-json-v1"},
                    "actorTypes": [
                        {
                            "id": "character",
                            "label": "Character",
                            "schema": "schemas/c.json",
                            "sheet": "layouts/c.json",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = load_package(package_dir)
    assert not loaded.validation.ok
    assert "inside.systems.validation.id_invalid" in loaded.validation.errors

def test_bundled_dnd5e_loads_cleanly():
    loaded = load_package(SYSTEMS_DIR / "dnd5e")
    assert loaded.manifest is not None
    assert loaded.manifest.id == "dnd5e"
    assert loaded.validation.ok
    assert "assets.styles" in loaded.manifest.capabilities
    assert "assets.scripts" in loaded.manifest.capabilities
    assert "combat.config" in loaded.manifest.capabilities
    assert "rolls.intent" in loaded.manifest.capabilities


def test_system_api_v1_capabilities_are_allowed():
    raw = _valid_manifest()
    raw["capabilities"] = [
        "actors.register",
        "items.register",
        "sheets.declarative",
        "rules.declarative",
        "content.packs",
        "tokens.mappings",
        "dice.roll",
        "chat.cards",
        "roll.toast",
        "locales",
        "assets.ui",
        "assets.styles",
        "assets.scripts",
        "combat.config",
        "combat.hooks",
        "rolls.intent",
    ]

    result = validate_manifest(raw)
    assert result.ok


def test_public_system_api_contract_files_exist_and_parse():
    docs = [
        "docs/systems/manifest.md",
        "docs/systems/rolls.md",
        "docs/systems/sheets.md",
        "docs/systems/combat.md",
        "docs/systems/content-packs.md",
        "docs/systems/creating-a-system.md",
    ]
    schemas = [
        "schemas/system-manifest-v1.schema.json",
        "schemas/system-actions-v1.schema.json",
        "schemas/system-combat-v1.schema.json",
        "schemas/system-layout-v1.schema.json",
    ]

    for path in docs:
        text = (SYSTEMS_DIR.parent.parent / path).read_text(encoding="utf-8")
        assert "System API v1" in text

    for path in schemas:
        raw = json.loads((SYSTEMS_DIR.parent.parent / path).read_text(encoding="utf-8"))
        assert raw["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert raw["$id"].startswith("https://gravewright.dev/schemas/")
        assert "properties" in raw

def test_registry_discovers_bundled_packages():
    ids = {ls.manifest.id for ls in system_registry.load_all() if ls.manifest}
    assert "dnd5e" in ids
