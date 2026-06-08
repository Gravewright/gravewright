from __future__ import annotations

import json

from app.engine.modules.module_asset_service import ModuleAssetService
from app.engine.modules.module_install_service import ModuleInstallService
from app.engine.modules.module_settings_service import ModuleSettingsService
from tests.conftest import seed_campaign, seed_member, seed_user


def _write_settings_module(base, package_id="settings-module", *, manifest_id="settings-module"):
    package = base / package_id
    (package / "assets").mkdir(parents=True)
    (package / "assets" / "game.js").write_text("export {};", encoding="utf-8")
    (package / "manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "type": "module",
                "id": manifest_id,
                "name": "Settings Module",
                "version": "0.1.0",
                "apiVersion": "1",
                "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
                "capabilities": ["assets.scripts", "settings"],
                "module": {
                    "id": manifest_id,
                    "entrypoints": {"game": {"scripts": ["assets/game.js"]}},
                    "settings": [
                        {"key": "feature.enabled", "scope": "campaign", "type": "boolean", "default": False},
                        {"key": "theme", "scope": "user", "type": "enum", "default": "dark", "choices": ["dark", "light"]},
                        {"key": "global.label", "scope": "global", "type": "string", "default": "Gravewright"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    return package


def _install_enabled_for_campaign(tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_settings_module(modules_dir)
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-settings@test.com")
    campaign_id = seed_campaign(gm_id)
    service = ModuleInstallService()
    assert service.install(package_id="settings-module", user_id=gm_id).success
    assert service.enable(package_id="settings-module").success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="settings-module").success
    return gm_id, campaign_id


def test_module_settings_defaults_and_overrides_reach_client_manifest(db, tmp_path, monkeypatch):
    gm_id, campaign_id = _install_enabled_for_campaign(tmp_path, monkeypatch)
    settings = ModuleSettingsService()

    result = settings.set_value(
        module_id="settings-module",
        setting_key_value="feature.enabled",
        raw_value=True,
        user_id=gm_id,
        user_system_role="user",
        campaign_id=campaign_id,
    )
    assert result.success

    manifests = ModuleAssetService().list_enabled_client_manifests(
        campaign_id=campaign_id,
        user_id=gm_id,
        entrypoint="game",
    )

    assert manifests[0]["settingValues"] == {
        "feature.enabled": True,
        "theme": "dark",
        "global.label": "Gravewright",
    }


def test_module_settings_enforce_scope_permissions(db, tmp_path, monkeypatch):
    gm_id, campaign_id = _install_enabled_for_campaign(tmp_path, monkeypatch)
    player_id = seed_user(name="Player", email="player-module-settings@test.com")
    seed_member(campaign_id, player_id, role="player")
    settings = ModuleSettingsService()

    denied = settings.set_value(
        module_id="settings-module",
        setting_key_value="feature.enabled",
        raw_value=True,
        user_id=player_id,
        user_system_role="user",
        campaign_id=campaign_id,
    )
    assert not denied.success
    assert denied.error_key == "inside.campaigns.errors.gm_required"

    user_setting = settings.set_value(
        module_id="settings-module",
        setting_key_value="theme",
        raw_value="light",
        user_id=player_id,
        user_system_role="user",
        campaign_id=campaign_id,
    )
    assert user_setting.success

    invalid_enum = settings.set_value(
        module_id="settings-module",
        setting_key_value="theme",
        raw_value="neon",
        user_id=player_id,
        user_system_role="user",
        campaign_id=campaign_id,
    )
    assert not invalid_enum.success
    assert invalid_enum.error_key == "inside.modules.settings.errors.invalid_value"
