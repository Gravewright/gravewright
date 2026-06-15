from __future__ import annotations

from app.engine.sdk import load_all, load_by_package_id


def test_load_all_discovers_bundled_packages():
    by_id = {p.id: p for p in load_all()}
    assert "dnd5e" in by_id
    assert "dice-so-nice-lite" in by_id
    assert by_id["dnd5e"].manifest.kind == "ruleset"
    assert by_id["dice-so-nice-lite"].manifest.kind == "addon"


def test_bundled_packages_are_valid_and_compatible():
    for package in load_all():
        assert package.ok, (package.id, package.validation.errors)
        assert package.validation.compatibility_status == "compatible"


def test_load_by_package_id():
    pkg = load_by_package_id("dnd5e")
    assert pkg is not None
    assert pkg.manifest.id == "dnd5e"
    assert "schemas/character.schema.json" in pkg.manifest.referenced_paths()


def test_load_by_package_id_rejects_unsafe_id():
    assert load_by_package_id("../etc") is None
    assert load_by_package_id("Bad_Id") is None
    assert load_by_package_id("missing-package") is None
