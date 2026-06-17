"""Phase 10 — SDK v1 contract fixtures.

Real minimal packages for every kind (valid and invalid) under
``tests/fixtures/sdk_packages``. The valid fixtures must keep loading, installing
and activating; the invalid ones must keep failing with stable error codes. A
change that breaks the public contract breaks these tests immediately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.sdk import package_registry
from app.engine.sdk.package_activation_service import PackageActivationService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_registry import load_all, load_by_package_id
from tests.conftest import seed_campaign, seed_user

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sdk_packages"
VALID_ROOT = FIXTURES / "valid"
INVALID_ROOT = FIXTURES / "invalid"


def _loaded_by_id(root: Path) -> dict:
    return {p.id: p for p in load_all(root)}


# --- valid packages ----------------------------------------------------------


def test_all_valid_fixtures_load_clean():
    loaded = _loaded_by_id(VALID_ROOT)
    expected = {
        "valid-ruleset",
        "valid-addon",
        "valid-library",
        "valid-theme",
        "valid-content",
        "valid-assets",
        "valid-addon-sqlite-contract",
    }
    assert expected <= set(loaded)
    for package_id in expected:
        errors = loaded[package_id].validation.errors
        assert errors == [], f"{package_id} should be valid, got {errors}"


def test_valid_addon_with_sqlite_storage_contract_validates():
    loaded = _loaded_by_id(VALID_ROOT)["valid-addon-sqlite-contract"]
    assert loaded.validation.ok
    storage_errors = [c for c in loaded.validation.errors if c.startswith("sdk.storage.")]
    assert storage_errors == []


@pytest.mark.parametrize(
    "package_id,kind",
    [
        ("valid-ruleset", "ruleset"),
        ("valid-addon", "addon"),
        ("valid-library", "library"),
        ("valid-theme", "theme"),
        ("valid-content", "content"),
        ("valid-assets", "assets"),
    ],
)
def test_valid_fixture_installs_and_enables(db, monkeypatch, package_id, kind):
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", VALID_ROOT)
    gm = seed_user(email=f"fixture-{package_id}@test.com")
    svc = PackageInstallService()

    installed = svc.install(package_id=package_id, user_id=gm)
    assert installed.success, installed.error_key
    enabled = svc.enable(package_id=package_id)
    assert enabled.success, enabled.error_key
    assert svc.get(package_id)["kind"] == kind


def test_valid_ruleset_and_addon_install_enable_and_activate(db, monkeypatch):
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", VALID_ROOT)
    gm = seed_user(email="fixture-activate@test.com")
    campaign = seed_campaign(gm)
    install = PackageInstallService()
    activation = PackageActivationService()

    for package_id in ("valid-ruleset", "valid-addon"):
        assert install.install(package_id=package_id, user_id=gm).success
        assert install.enable(package_id=package_id).success

    assert activation.set_campaign_ruleset(campaign, "valid-ruleset", gm).success
    assert activation.activate_package(campaign, "valid-addon", gm).success


# --- invalid packages --------------------------------------------------------


@pytest.mark.parametrize(
    "package_id,expected_code",
    [
        ("invalid-unknown-capability", "sdk.validation.capability_unknown"),
        ("invalid-forbidden-capability", "sdk.validation.capability_forbidden"),
        ("invalid-path-traversal", "sdk.validation.path_unsafe"),
        ("invalid-bad-setting", "sdk.validation.setting_invalid"),
        ("invalid-storage-declaration", "sdk.storage.capability_missing"),
        ("invalid-storage-query-params", "sdk.storage.sqlite.query_param_invalid_type"),
    ],
)
def test_invalid_fixtures_report_stable_codes(package_id, expected_code):
    loaded = _loaded_by_id(INVALID_ROOT)[package_id]
    assert expected_code in loaded.validation.errors, loaded.validation.errors


def test_invalid_manifest_id_mismatch_rejected():
    loaded = load_by_package_id("wrong-dir-name", INVALID_ROOT)
    assert loaded is not None
    assert "sdk.manifest.id_mismatch" in loaded.validation.errors


def test_invalid_kind_root_mismatch_rejected():
    loaded = load_by_package_id("invalid-kind-root", INVALID_ROOT)
    assert loaded is not None
    assert "sdk.manifest.kind_root_mismatch" in loaded.validation.errors


def test_invalid_fixtures_block_install(db, monkeypatch):
    monkeypatch.setattr(package_registry, "PACKAGES_DIR", INVALID_ROOT)
    gm = seed_user(email="fixture-invalid-install@test.com")
    result = PackageInstallService().install(
        package_id="invalid-unknown-capability", user_id=gm
    )
    assert result.success is False
