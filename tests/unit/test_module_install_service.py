from __future__ import annotations

import json

from app.engine.modules.module_install_service import ModuleInstallService
from tests.conftest import seed_user


def _write_module_package(base, package_id="sample-module", *, manifest_id="sample-module", dependencies=None, conflicts=None, load_order=0):
    package = base / package_id
    (package / "assets").mkdir(parents=True)
    (package / "assets" / "sample.css").write_text(".sample{}", encoding="utf-8")
    (package / "assets" / "sample.js").write_text("export {};", encoding="utf-8")
    (package / "manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "type": "module",
                "id": manifest_id,
                "name": "Sample Module",
                "version": "0.1.0",
                "apiVersion": "1",
                "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
                "capabilities": ["assets.ui", "assets.styles", "assets.scripts"],
                "dependencies": dependencies or [],
                "conflicts": conflicts or [],
                "loadOrder": load_order,
                "module": {
                    "id": manifest_id,
                    "entrypoints": {
                        "game": {"styles": ["assets/sample.css"], "scripts": ["assets/sample.js"]}
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return package


def _by_id(items: list[dict], module_id: str) -> dict | None:
    return next((i for i in items if i["id"] == module_id), None)


def test_module_install_enable_disable_remove_flow(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir)
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    user_id = seed_user(name="Owner", email="owner-modules@test.com")
    service = ModuleInstallService()

    listed = _by_id(service.list_for_tab(), "sample-module")
    assert listed is not None
    assert listed["status"] == "available"
    assert listed["can_install"] is True

    install = service.install(package_id="sample-module", user_id=user_id)
    assert install.success
    assert install.module_id == "sample-module"
    assert _by_id(service.list_for_tab(), "sample-module")["status"] == "installed"

    assert service.enable(package_id="sample-module").success
    assert _by_id(service.list_for_tab(), "sample-module")["status"] == "enabled"

    assert service.disable(package_id="sample-module").success
    assert _by_id(service.list_for_tab(), "sample-module")["status"] == "disabled"

    assert service.remove(package_id="sample-module").success
    assert _by_id(service.list_for_tab(), "sample-module")["status"] == "available"


def test_module_install_invalid_manifest_fails(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    bad_pkg = modules_dir / "bad-module"
    bad_pkg.mkdir(parents=True)
    (bad_pkg / "manifest.json").write_text(
        json.dumps({"schemaVersion": 1, "type": "module", "id": "Bad Module"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    user_id = seed_user(name="Owner", email="owner-modules-invalid@test.com")
    result = ModuleInstallService().install(package_id="bad-module", user_id=user_id)

    assert not result.success
    assert result.error_key == "inside.modules.errors.invalid_manifest"


def test_enable_requires_install(db):
    result = ModuleInstallService().enable(package_id="does-not-exist")
    assert not result.success
    assert result.error_key == "inside.modules.errors.not_installed"


def test_module_campaign_enablement_requires_global_enabled_and_gm(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign
    from tests.conftest import seed_member

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir)
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-campaign@test.com")
    player_id = seed_user(name="Player", email="player-module-campaign@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")

    service = ModuleInstallService()
    assert service.install(package_id="sample-module", user_id=gm_id).success

    not_globally_enabled = service.enable_for_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        module_id="sample-module",
    )
    assert not not_globally_enabled.success
    assert not_globally_enabled.error_key == "inside.modules.errors.not_installed"

    assert service.enable(package_id="sample-module").success

    forbidden = service.enable_for_campaign(
        campaign_id=campaign_id,
        user_id=player_id,
        module_id="sample-module",
    )
    assert not forbidden.success
    assert forbidden.error_key == "inside.campaigns.errors.gm_required"

    enabled = service.enable_for_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        module_id="sample-module",
    )
    assert enabled.success
    assert service.enabled_campaign_ids_by_module([campaign_id]) == {"sample-module": {campaign_id}}

    disabled = service.disable_for_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        module_id="sample-module",
    )
    assert disabled.success
    assert service.enabled_campaign_ids_by_module([campaign_id]) == {}



def test_module_campaign_enablement_requires_dependencies(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir, package_id="base-module", manifest_id="base-module")
    _write_module_package(
        modules_dir,
        package_id="addon-module",
        manifest_id="addon-module",
        dependencies=["base-module"],
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-deps@test.com")
    campaign_id = seed_campaign(gm_id)
    service = ModuleInstallService()
    assert service.install(package_id="base-module", user_id=gm_id).success
    assert service.enable(package_id="base-module").success
    assert service.install(package_id="addon-module", user_id=gm_id).success
    assert service.enable(package_id="addon-module").success

    missing = service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="addon-module")
    assert not missing.success
    assert missing.error_key == "inside.modules.errors.dependency_missing"

    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="base-module").success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="addon-module").success


def test_module_campaign_enablement_blocks_conflicts(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir, package_id="first-module", manifest_id="first-module", conflicts=["second-module"])
    _write_module_package(modules_dir, package_id="second-module", manifest_id="second-module")
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-conflicts@test.com")
    campaign_id = seed_campaign(gm_id)
    service = ModuleInstallService()
    for package_id in ["first-module", "second-module"]:
        assert service.install(package_id=package_id, user_id=gm_id).success
        assert service.enable(package_id=package_id).success

    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="first-module").success
    blocked = service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="second-module")
    assert not blocked.success
    assert blocked.error_key == "inside.modules.errors.conflict"


def test_module_remove_requires_global_disable(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir, package_id="remove-enabled", manifest_id="remove-enabled")
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    user_id = seed_user(name="Owner", email="owner-modules-remove-enabled@test.com")
    service = ModuleInstallService()
    assert service.install(package_id="remove-enabled", user_id=user_id).success
    assert service.enable(package_id="remove-enabled").success

    removed = service.remove(package_id="remove-enabled")

    assert not removed.success
    assert removed.error_key == "inside.modules.errors.disable_before_remove"


def test_module_remove_requires_campaign_disable(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir, package_id="remove-campaign", manifest_id="remove-campaign")
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    user_id = seed_user(name="Owner", email="owner-modules-remove-campaign@test.com")
    campaign_id = seed_campaign(user_id)
    service = ModuleInstallService()
    assert service.install(package_id="remove-campaign", user_id=user_id).success
    assert service.enable(package_id="remove-campaign").success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="remove-campaign").success
    assert service.disable(package_id="remove-campaign").success

    removed = service.remove(package_id="remove-campaign")

    assert not removed.success
    assert removed.error_key == "inside.modules.errors.disable_campaigns_before_remove"

    assert service.disable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="remove-campaign").success
    assert service.remove(package_id="remove-campaign").success


def test_module_campaign_disable_blocks_enabled_dependents(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir, package_id="base-disable", manifest_id="base-disable")
    _write_module_package(
        modules_dir,
        package_id="addon-disable",
        manifest_id="addon-disable",
        dependencies=["base-disable"],
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    user_id = seed_user(name="GM", email="gm-module-disable-dependent@test.com")
    campaign_id = seed_campaign(user_id)
    service = ModuleInstallService()
    for package_id in ["base-disable", "addon-disable"]:
        assert service.install(package_id=package_id, user_id=user_id).success
        assert service.enable(package_id=package_id).success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="base-disable").success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="addon-disable").success

    blocked = service.disable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="base-disable")

    assert not blocked.success
    assert blocked.error_key == "inside.modules.errors.dependent_enabled"
    assert service.disable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="addon-disable").success
    assert service.disable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="base-disable").success
