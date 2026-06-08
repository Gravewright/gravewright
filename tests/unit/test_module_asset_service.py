from __future__ import annotations

from app.engine.modules.module_asset_service import ModuleAssetService
from app.engine.modules.module_install_service import ModuleInstallService
from tests.unit.test_module_install_service import _write_module_package
from tests.conftest import seed_user


def test_enabled_module_asset_resolution(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir)
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    user_id = seed_user(name="Owner", email="owner-module-assets@test.com")
    service = ModuleInstallService()
    assert service.install(package_id="sample-module", user_id=user_id).success
    assert service.enable(package_id="sample-module").success

    assets = ModuleAssetService()
    entries = assets.list_enabled_assets()
    assert entries == [
        {
            "module_id": "sample-module",
            "version": "0.1.0",
            "styles": ["assets/sample.css"],
            "scripts": ["assets/sample.js"],
        }
    ]

    resolved = assets.resolve("sample-module", "assets/sample.js")
    assert resolved is not None
    path, content_type = resolved
    assert path.name == "sample.js"
    assert content_type == "application/javascript"

    assert assets.resolve("sample-module", "assets/not-declared.js") is None


def test_module_assets_are_filtered_by_campaign_enablement(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir)
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-assets-campaign@test.com")
    campaign_id = seed_campaign(gm_id)
    other_campaign_id = seed_campaign(gm_id, title="Other Campaign")

    service = ModuleInstallService()
    assert service.install(package_id="sample-module", user_id=gm_id).success
    assert service.enable(package_id="sample-module").success

    assets = ModuleAssetService()
    assert assets.list_enabled_assets(campaign_id=campaign_id) == []

    assert service.enable_for_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        module_id="sample-module",
    ).success

    assert assets.list_enabled_assets(campaign_id=campaign_id) == [
        {
            "module_id": "sample-module",
            "version": "0.1.0",
            "styles": ["assets/sample.css"],
            "scripts": ["assets/sample.js"],
        }
    ]
    assert assets.list_enabled_assets(campaign_id=other_campaign_id) == []


def test_module_assets_are_dependency_ordered(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir, package_id="base-module", manifest_id="base-module", load_order=100)
    _write_module_package(
        modules_dir,
        package_id="addon-module",
        manifest_id="addon-module",
        dependencies=["base-module"],
        load_order=-100,
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-assets-order@test.com")
    campaign_id = seed_campaign(gm_id)
    service = ModuleInstallService()
    for package_id in ["base-module", "addon-module"]:
        assert service.install(package_id=package_id, user_id=gm_id).success
        assert service.enable(package_id=package_id).success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="base-module").success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="addon-module").success

    assets = ModuleAssetService().list_enabled_assets(campaign_id=campaign_id)
    assert [entry["module_id"] for entry in assets] == ["base-module", "addon-module"]
