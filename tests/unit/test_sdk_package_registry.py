from __future__ import annotations

from tests.conftest import SDK_FIXTURES_ROOT
from app.engine.sdk import load_all, load_by_package_id


def test_load_all_discovers_fixture_packages():
    by_id = {p.id: p for p in load_all(SDK_FIXTURES_ROOT)}
    assert "valid-ruleset" in by_id
    assert "valid-addon" in by_id
    assert by_id["valid-ruleset"].manifest.kind == "ruleset"
    assert by_id["valid-addon"].manifest.kind == "addon"


def test_fixture_packages_are_valid_and_not_incompatible():
    for package in load_all(SDK_FIXTURES_ROOT):
        assert package.ok, (package.id, package.validation.errors)
        assert package.validation.compatibility_status != "incompatible"


def test_load_by_package_id():
    pkg = load_by_package_id("valid-ruleset", packages_dir=SDK_FIXTURES_ROOT)
    assert pkg is not None
    assert pkg.manifest.id == "valid-ruleset"


def test_load_by_package_id_rejects_unsafe_id():
    assert load_by_package_id("../etc") is None
    assert load_by_package_id("Bad_Id") is None
    assert load_by_package_id("missing-package") is None


def test_load_all_reports_grouped_package_dir_without_manifest(tmp_path):
    pkg = tmp_path / "rulesets" / "sample-ruleset"
    pkg.mkdir(parents=True)

    loaded = load_all(tmp_path)

    assert len(loaded) == 1
    assert loaded[0].id == "sample-ruleset"
    assert loaded[0].ok is False
    assert "sdk.validation.manifest_missing" in loaded[0].validation.errors


def test_load_by_package_id_reports_missing_manifest_in_grouped_layout(tmp_path):
    pkg = tmp_path / "rulesets" / "sample-ruleset"
    pkg.mkdir(parents=True)

    loaded = load_by_package_id("sample-ruleset", packages_dir=tmp_path)

    assert loaded is not None
    assert loaded.id == "sample-ruleset"
    assert loaded.ok is False
    assert "sdk.validation.manifest_missing" in loaded.validation.errors
