from __future__ import annotations

from app.engine.modules.module_asset_service import ModuleAssetService
from app.engine.modules.module_install_service import ModuleInstallService
from tests.conftest import seed_campaign, seed_user
from tests.unit.test_module_install_service import _write_module_package


def test_module_client_manifest_exposes_campaign_scoped_public_metadata(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_module_package(modules_dir)
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-client-api@test.com")
    campaign_id = seed_campaign(gm_id)

    service = ModuleInstallService()
    assert service.install(package_id="sample-module", user_id=gm_id).success
    assert service.enable(package_id="sample-module").success
    assert service.enable_for_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        module_id="sample-module",
    ).success

    manifests = ModuleAssetService().list_enabled_client_manifests(
        campaign_id=campaign_id,
        entrypoint="game",
    )

    assert manifests == [
        {
            "id": "sample-module",
            "name": "Sample Module",
            "version": "0.1.0",
            "apiVersion": "1",
            "capabilities": ["assets.ui", "assets.styles", "assets.scripts"],
            "hooks": [],
            "dependencies": [],
            "conflicts": [],
            "loadOrder": 0,
            "settings": [],
            "settingValues": {},
            "entrypoint": "game",
            "styles": ["/modules/sample-module/asset/assets/sample.css?v=0.1.0"],
            "scripts": ["/modules/sample-module/asset/assets/sample.js?v=0.1.0"],
        }
    ]


def test_game_template_injects_module_api_bootstrap_json():
    template = open("templates/pages/game/index.html", encoding="utf-8").read()

    assert 'id="gravewright-game-context"' in template
    assert 'id="gravewright-module-manifests"' in template
    assert "game_client_context_json" in template
    assert "module_manifests_json" in template
    assert "module_scripts" in template
    assert 'type="module"' in template


def test_module_public_api_exposes_gravewright_namespace_and_capability_guard():
    public_api = open("static/js/modules/public-api.js", encoding="utf-8").read()
    modules_js = open("static/js/modules/modules.js", encoding="utf-8").read()

    assert "window.Gravewright.modules" in modules_js
    assert "window.Gravewright.hooks" in modules_js
    assert "requireCapability" in public_api
    assert "hooks.client" in public_api
    assert "settings.get" in public_api
    assert "settings.set" in public_api
    assert "game.context" not in public_api                                               


def test_module_public_api_declares_capability_requirements_for_privileged_namespaces():
    public_api = open("static/js/modules/public-api.js", encoding="utf-8").read()

    assert "CAPABILITY_REQUIREMENTS" in public_api
    assert '"chat.send": CAPABILITIES.CHAT_CARDS' in public_api
    assert '"hooks.on": CAPABILITIES.HOOKS_CLIENT' in public_api
    assert '"hooks.once": CAPABILITIES.HOOKS_CLIENT' in public_api
    assert '"settings.get": CAPABILITIES.SETTINGS' in public_api
    assert '"settings.set": CAPABILITIES.SETTINGS' in public_api
    assert '"tokens.centerOn": CAPABILITIES.TOKENS_EXTENDS' in public_api
    assert '"ui.toast": CAPABILITIES.UI' in public_api
    assert '"scene.activeCanvas": CAPABILITIES.UI' in public_api
    assert "requireApiCapability(scopedModule, \"chat.send\")" in public_api
    assert "requireApiCapability(scopedModule, \"tokens.centerOn\")" in public_api
    assert "requires a scoped module api" in public_api
