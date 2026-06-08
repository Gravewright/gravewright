from __future__ import annotations

import json
from pathlib import Path

from app.engine.modules import module_registry
from app.engine.modules.module_manifest_validator import validate_manifest
from app.engine.modules.module_loader import load_package, safe_join


def _manifest(**overrides):
    raw = {
        "schemaVersion": 1,
        "type": "module",
        "id": "sample-module",
        "name": "Sample Module",
        "version": "0.1.0",
        "apiVersion": "1",
        "compatibility": {
            "minimum": "1.0.0-rc.1",
            "verified": "1.0.0-rc.1",
            "maximum": "1.x",
        },
        "capabilities": ["assets.ui", "assets.styles", "assets.scripts"],
        "module": {
            "id": "sample-module",
            "entrypoints": {
                "game": {
                    "styles": ["assets/sample.css"],
                    "scripts": ["assets/sample.js"],
                }
            },
        },
    }
    raw.update(overrides)
    return raw


def test_valid_module_manifest_passes_validation():
    result = validate_manifest(_manifest())
    assert result.errors == []


def test_module_manifest_rejects_forbidden_capability():
    result = validate_manifest(_manifest(capabilities=["backend.execute"]))
    assert "inside.modules.validation.capability_forbidden" in result.errors


def test_module_manifest_rejects_unsafe_paths():
    raw = _manifest(module={"id": "sample-module", "entrypoints": {"game": {"scripts": ["../evil.js"]}}})
    result = validate_manifest(raw)
    assert "inside.modules.validation.path_unsafe" in result.errors


def test_load_module_package_checks_referenced_files(tmp_path):
    package = tmp_path / "sample-module"
    (package / "assets").mkdir(parents=True)
    (package / "assets" / "sample.css").write_text(".x{}", encoding="utf-8")
    (package / "assets" / "sample.js").write_text("export {};", encoding="utf-8")
    (package / "manifest.json").write_text(json.dumps(_manifest()), encoding="utf-8")

    loaded = load_package(package)

    assert loaded.manifest is not None
    assert loaded.validation.errors == []


def test_module_registry_discovers_packages(tmp_path):
    modules_dir = tmp_path / "modules"
    package = modules_dir / "sample-module"
    (package / "assets").mkdir(parents=True)
    (package / "assets" / "sample.css").write_text(".x{}", encoding="utf-8")
    (package / "assets" / "sample.js").write_text("export {};", encoding="utf-8")
    (package / "manifest.json").write_text(json.dumps(_manifest()), encoding="utf-8")

    packages = module_registry.load_all(modules_dir)

    assert [p.package_id for p in packages] == ["sample-module"]


def test_dice_so_nice_lite_package_is_valid():
    loaded = load_package(Path("data/modules/dice-so-nice-lite"))

    assert loaded.manifest is not None
    assert loaded.validation.errors == []
    assert loaded.manifest.id == "dice-so-nice-lite"
    assert loaded.manifest.entrypoint_styles("game") == ["assets/dice-so-nice-lite.css"]
    assert loaded.manifest.entrypoint_scripts("game") == ["assets/dice-so-nice-lite.js"]
    assert loaded.manifest.settings[0]["key"] == "dice.color"


def test_module_manifest_requires_schema_version():
    raw = _manifest()
    raw.pop("schemaVersion")
    result = validate_manifest(raw)
    assert "inside.modules.validation.schema_version" in result.errors


def test_module_manifest_rejects_legacy_assets_block():
    raw = _manifest(module={"id": "sample-module", "assets": {"scripts": ["assets/sample.js"]}})
    result = validate_manifest(raw)
    assert "inside.modules.validation.assets_legacy" in result.errors
    assert "inside.modules.validation.entrypoints_required" in result.errors


def test_module_manifest_rejects_script_without_capability():
    raw = _manifest(capabilities=["assets.ui", "assets.styles"])
    result = validate_manifest(raw)
    assert "inside.modules.validation.capability_missing" in result.errors


def test_module_manifest_rejects_too_many_assets():
    scripts = [f"assets/{index}.js" for index in range(17)]
    raw = _manifest(module={"id": "sample-module", "entrypoints": {"game": {"scripts": scripts}}})
    result = validate_manifest(raw)
    assert "inside.modules.validation.asset_limit" in result.errors


def test_module_manifest_rejects_wrong_asset_type():
    raw = _manifest(module={"id": "sample-module", "entrypoints": {"game": {"styles": ["assets/not-css.js"]}}})
    result = validate_manifest(raw)
    assert "inside.modules.validation.asset_type" in result.errors


def test_module_manifest_validates_settings_contract():
    raw = _manifest(
        capabilities=["assets.ui", "assets.styles", "assets.scripts", "settings"],
        module={
            "id": "sample-module",
            "entrypoints": {"game": {"styles": ["assets/sample.css"], "scripts": ["assets/sample.js"]}},
            "settings": [
                {"key": "feature.enabled", "scope": "campaign", "type": "boolean", "default": False},
                {"key": "theme", "scope": "user", "type": "enum", "default": "dark", "choices": ["dark", "light"]},
            ],
        },
    )
    result = validate_manifest(raw)
    assert result.errors == []


def test_module_manifest_rejects_invalid_setting_definition():
    raw = _manifest(
        capabilities=["assets.ui", "assets.styles", "assets.scripts", "settings"],
        module={
            "id": "sample-module",
            "entrypoints": {"game": {"styles": ["assets/sample.css"], "scripts": ["assets/sample.js"]}},
            "settings": [{"key": "Bad Key", "scope": "table", "type": "enum", "default": "x", "choices": []}],
        },
    )
    result = validate_manifest(raw)
    assert "inside.modules.validation.setting_key" in result.errors
    assert "inside.modules.validation.setting_scope" in result.errors
    assert "inside.modules.validation.setting_options" in result.errors
    assert "inside.modules.validation.setting_default" in result.errors


def test_module_manifest_validates_relationships_and_load_order():
    raw = _manifest(
        dependencies=["base-module"],
        conflicts=[{"id": "other-module"}],
        loadOrder=25,
    )
    result = validate_manifest(raw)
    assert result.errors == []


def test_module_manifest_rejects_invalid_relationships():
    raw = _manifest(
        dependencies=["Bad Dependency", "sample-module"],
        conflicts=["sample-module", "bad conflict"],
        loadOrder=20000,
    )
    result = validate_manifest(raw)
    assert "inside.modules.validation.dependency_id" in result.errors
    assert "inside.modules.validation.dependency_self" in result.errors
    assert "inside.modules.validation.conflict_id" in result.errors
    assert "inside.modules.validation.conflict_self" in result.errors
    assert "inside.modules.validation.load_order" in result.errors
