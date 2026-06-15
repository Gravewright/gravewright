from __future__ import annotations

import json

from litestar.testing import TestClient

from app.engine.sdk.package_activation_service import PackageActivationService
from app.engine.sdk.package_asset_service import PackageAssetService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_manifest_validator import validate_manifest
from app.engine.sdk.package_settings_service import PackageSettingsService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def _install_enable(package_id: str, user_id: str) -> None:
    svc = PackageInstallService()
    assert svc.install(package_id=package_id, user_id=user_id).success
    assert svc.enable(package_id=package_id).success


def _package_manifest(
    package_id: str,
    *,
    kind: str = "addon",
    version: str = "1.0.0",
    dependencies: list[dict] | None = None,
    conflicts: list[dict] | None = None,
    capabilities: list[str] | None = None,
    settings: list[dict] | None = None,
) -> dict:
    activation_mode = "exclusive" if kind == "ruleset" else "passive" if kind == "library" else "multiple"
    manifest = {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": kind,
        "id": package_id,
        "name": package_id,
        "version": version,
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1"},
        "capabilities": capabilities or [],
        "activation": {"scope": "campaign", "mode": activation_mode},
        "entrypoints": {},
        "provides": {},
        "dependencies": dependencies or [],
        "conflicts": conflicts or [],
        "settings": settings or [],
    }
    if kind == "ruleset":
        manifest["provides"] = {
            "storage": {"model": "scoped-json-v1"},
            "actorTypes": [{"id": "character", "label": "Character"}],
        }
    return manifest


def _upsert_installed_package(raw: dict, *, status: str = "enabled", user_id: str | None = None) -> None:
    PackageInstallService().installed.upsert(
        package_id=raw["id"],
        kind=raw["kind"],
        name=raw["name"],
        version=raw["version"],
        status=status,
        package_dir=raw["id"],
        manifest_json=json.dumps(raw),
        compatibility_status="compatible",
        validation_errors_json="[]",
        installed_by_user_id=user_id,
    )


def test_set_campaign_ruleset_and_activate_addon(db):
    gm_id = seed_user(name="GM", email="sdk-activate@test.com")
    campaign_id = seed_campaign(gm_id)
    _install_enable("dnd5e", gm_id)
    _install_enable("dice-so-nice-lite", gm_id)

    activation = PackageActivationService()

    assert activation.set_campaign_ruleset(campaign_id, "dnd5e", gm_id).success
    active = activation.get_active_ruleset(campaign_id)
    assert active is not None and active["id"] == "dnd5e"

    # A ruleset cannot be activated as a regular package.
    assert not activation.activate_package(campaign_id, "dnd5e", gm_id).success
    # An addon can.
    assert activation.activate_package(campaign_id, "dice-so-nice-lite", gm_id).success
    rows = {r["package_id"] for r in activation.list_campaign_packages(campaign_id)}
    assert "dice-so-nice-lite" in rows


def test_package_settings_roundtrip(db):
    user_id = seed_user(name="User", email="sdk-settings@test.com")
    _install_enable("dice-so-nice-lite", user_id)

    settings = PackageSettingsService()
    # Default comes from the manifest until overridden.
    assert settings.get("dice-so-nice-lite", "dice.color", None, user_id) == "#7c5cff"
    assert settings.set("dice-so-nice-lite", "dice.color", "#112233", None, user_id)
    assert settings.get("dice-so-nice-lite", "dice.color", None, user_id) == "#112233"


def test_global_package_setting_is_effective_value(db):
    owner_id = seed_user(name="Owner", email="sdk-global-setting@test.com")
    _upsert_installed_package(
        _package_manifest(
            "global-settings-addon",
            capabilities=["settings"],
            settings=[
                {
                    "key": "table.theme",
                    "scope": "global",
                    "type": "string",
                    "default": "light",
                    "label": "Theme",
                }
            ],
        ),
        user_id=owner_id,
    )
    settings = PackageSettingsService()

    assert settings.set("global-settings-addon", "table.theme", "dark", None, None)
    assert settings.effective_values("global-settings-addon", None, owner_id)["table.theme"] == "dark"


def test_package_settings_route_requires_owner_for_global_scope(db):
    from main import app

    owner_id = seed_user(name="Owner", email="sdk-global-owner@test.com")
    user_id = seed_user(name="User", email="sdk-global-user@test.com")
    _upsert_installed_package(
        _package_manifest(
            "global-route-addon",
            capabilities=["settings"],
            settings=[
                {
                    "key": "table.theme",
                    "scope": "global",
                    "type": "string",
                    "default": "light",
                    "label": "Theme",
                }
            ],
        ),
        user_id=owner_id,
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        denied = client.post(
            "/sdk/packages/settings",
            json={"package_id": "global-route-addon", "key": "table.theme", "value": "dark"},
        )
        login(client, owner_id)
        allowed = client.post(
            "/sdk/packages/settings",
            json={"package_id": "global-route-addon", "key": "table.theme", "value": "dark"},
        )

    assert denied.status_code == 403
    assert denied.json()["error_key"] == "sdk.errors.owner_required"
    assert allowed.status_code in {200, 201}
    assert allowed.json()["value"] == "dark"


def test_package_settings_route_requires_enabled_package_and_capability(db):
    from main import app

    owner_id = seed_user(name="Owner", email="sdk-settings-enabled@test.com")
    _upsert_installed_package(
        _package_manifest(
            "disabled-settings-addon",
            capabilities=["settings"],
            settings=[{"key": "enabled", "scope": "user", "type": "boolean", "default": True}],
        ),
        status="disabled",
        user_id=owner_id,
    )
    _upsert_installed_package(
        _package_manifest(
            "no-settings-cap-addon",
            settings=[{"key": "enabled", "scope": "user", "type": "boolean", "default": True}],
        ),
        user_id=owner_id,
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, owner_id)
        disabled = client.post(
            "/sdk/packages/settings",
            json={"package_id": "disabled-settings-addon", "key": "enabled", "value": False},
        )
        no_cap = client.post(
            "/sdk/packages/settings",
            json={"package_id": "no-settings-cap-addon", "key": "enabled", "value": False},
        )

    assert disabled.status_code == 400
    assert disabled.json()["error_key"] == "sdk.errors.not_enabled"
    assert no_cap.status_code == 403
    assert no_cap.json()["error_key"] == "sdk.errors.capability_required"


def test_content_import_route_enforces_capability_server_side(db):
    """The content-import flow is mutable, so the server must reject a package
    that does not declare ``content.packs`` even if a client SDK calls it.

    The capability check precedes the on-disk pack lookup, so no real content is
    needed to prove enforcement."""
    from main import app

    gm_id = seed_user(name="GM", email="sdk-content-cap@test.com")
    campaign_id = seed_campaign(gm_id)
    # Installed + enabled, but with NO content.packs capability declared.
    _upsert_installed_package(
        _package_manifest("no-content-cap-addon", capabilities=[]),
        user_id=gm_id,
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        denied = client.post(
            "/sdk/packages/content/import",
            json={
                "campaign_id": campaign_id,
                "package_id": "no-content-cap-addon",
                "pack_id": "whatever",
                "entry_id": "whatever",
            },
        )

    assert denied.status_code == 400
    assert denied.json()["error_key"] == "sdk.errors.capability_required"


def test_disable_and_remove_refuse_active_campaign_package(db):
    gm_id = seed_user(name="GM", email="sdk-active-refuse@test.com")
    campaign_id = seed_campaign(gm_id)
    _install_enable("dice-so-nice-lite", gm_id)
    activation = PackageActivationService()
    assert activation.activate_package(campaign_id, "dice-so-nice-lite", gm_id).success

    packages = PackageInstallService()
    disabled = packages.disable(package_id="dice-so-nice-lite")
    removed = packages.remove(package_id="dice-so-nice-lite")

    assert not disabled.success
    assert disabled.error_key == "sdk.errors.package_active_in_campaign"
    assert disabled.active_campaign_ids == (campaign_id,)
    assert not removed.success
    assert removed.error_key == "sdk.errors.package_active_in_campaign"
    assert packages.get("dice-so-nice-lite")["status"] == "enabled"


def test_activate_package_requires_installed_dependency(db):
    gm_id = seed_user(name="GM", email="sdk-dep-missing@test.com")
    campaign_id = seed_campaign(gm_id)
    _upsert_installed_package(
        _package_manifest(
            "needs-missing",
            dependencies=[{"id": "missing-lib", "kind": "library"}],
        ),
        user_id=gm_id,
    )

    result = PackageActivationService().activate_package(campaign_id, "needs-missing", gm_id)

    assert not result.success
    assert result.error_key == "sdk.errors.dependency_missing"


def test_activate_package_requires_enabled_dependency(db):
    gm_id = seed_user(name="GM", email="sdk-dep-disabled@test.com")
    campaign_id = seed_campaign(gm_id)
    _upsert_installed_package(
        _package_manifest("disabled-lib", kind="library"), status="disabled", user_id=gm_id
    )
    _upsert_installed_package(
        _package_manifest(
            "needs-disabled",
            dependencies=[{"id": "disabled-lib", "kind": "library"}],
        ),
        user_id=gm_id,
    )

    result = PackageActivationService().activate_package(campaign_id, "needs-disabled", gm_id)

    assert not result.success
    assert result.error_key == "sdk.errors.dependency_disabled"


def test_activate_package_rejects_dependency_above_maximum(db):
    gm_id = seed_user(name="GM", email="sdk-dep-too-new@test.com")
    campaign_id = seed_campaign(gm_id)
    _upsert_installed_package(
        _package_manifest("future-lib", kind="library", version="2.0.0"), user_id=gm_id
    )
    _upsert_installed_package(
        _package_manifest(
            "needs-older-lib",
            dependencies=[{"id": "future-lib", "kind": "library", "maximum": "1.x"}],
        ),
        user_id=gm_id,
    )

    result = PackageActivationService().activate_package(campaign_id, "needs-older-lib", gm_id)

    assert not result.success
    assert result.error_key == "sdk.errors.dependency_too_new"


def test_activate_package_requires_campaign_active_dependency(db):
    gm_id = seed_user(name="GM", email="sdk-dep-inactive@test.com")
    campaign_id = seed_campaign(gm_id)
    _upsert_installed_package(_package_manifest("base-addon"), user_id=gm_id)
    _upsert_installed_package(
        _package_manifest(
            "needs-active-addon",
            dependencies=[{"id": "base-addon", "kind": "addon"}],
        ),
        user_id=gm_id,
    )
    activation = PackageActivationService()

    inactive = activation.activate_package(campaign_id, "needs-active-addon", gm_id)
    assert not inactive.success
    assert inactive.error_key == "sdk.errors.dependency_inactive"

    assert activation.activate_package(campaign_id, "base-addon", gm_id).success
    assert activation.activate_package(campaign_id, "needs-active-addon", gm_id).success


def test_activate_package_rejects_active_conflict(db):
    gm_id = seed_user(name="GM", email="sdk-conflict-active@test.com")
    campaign_id = seed_campaign(gm_id)
    _upsert_installed_package(_package_manifest("conflicting-addon"), user_id=gm_id)
    _upsert_installed_package(
        _package_manifest(
            "blocked-addon",
            conflicts=[{"id": "conflicting-addon", "reason": "same UI slot"}],
        ),
        user_id=gm_id,
    )
    activation = PackageActivationService()
    assert activation.activate_package(campaign_id, "conflicting-addon", gm_id).success

    result = activation.activate_package(campaign_id, "blocked-addon", gm_id)

    assert not result.success
    assert result.error_key == "sdk.errors.package_conflict_active"


def test_client_manifest_separates_setting_definitions_and_values(db):
    gm_id = seed_user(name="GM", email="sdk-client-settings@test.com")
    campaign_id = seed_campaign(gm_id)
    _install_enable("dice-so-nice-lite", gm_id)
    assert PackageActivationService().activate_package(
        campaign_id, "dice-so-nice-lite", gm_id
    ).success
    settings = PackageSettingsService()
    assert settings.set("dice-so-nice-lite", "dice.color", "#112233", None, gm_id)

    manifests = PackageAssetService().list_client_manifests(campaign_id, gm_id)
    addon = next(m for m in manifests if m["id"] == "dice-so-nice-lite")

    assert "settings" not in addon
    assert any(d["key"] == "dice.color" for d in addon["settingDefinitions"])
    assert addon["settingValues"]["dice.color"] == "#112233"


def test_assets_package_validation():
    manifest = {
        "schemaVersion": 1,
        "sdkVersion": "1",
        "kind": "assets",
        "id": "fantasy-assets",
        "name": "Fantasy Assets",
        "version": "0.1.0",
        "compatibility": {"verified": "1.0.0-rc.1"},
        "capabilities": ["assets.pack", "assets.images"],
        "activation": {"scope": "campaign", "mode": "multiple"},
        "entrypoints": {},
        "provides": {
            "assets": {
                "images": [
                    {"id": "goblin", "label": "Goblin", "path": "assets/tokens/goblin.webp"}
                ]
            }
        },
    }
    assert validate_manifest(manifest).ok

    # Duplicate asset ids in a category are rejected.
    manifest["provides"]["assets"]["images"].append(
        {"id": "goblin", "label": "Goblin 2", "path": "assets/tokens/goblin2.webp"}
    )
    assert "sdk.validation.assets_invalid_assets" in validate_manifest(manifest).errors
