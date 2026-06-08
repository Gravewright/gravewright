from __future__ import annotations

import json

from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_user


def _by_id(items: list[dict], system_id: str) -> dict | None:
    return next((i for i in items if i["id"] == system_id), None)


def test_list_for_tab_classifies_real_bundled_packages(db):
    items = SystemInstallService().list_for_tab()

    dnd5e = _by_id(items, "dnd5e")

    assert dnd5e is not None
    assert dnd5e["status"] == "available"
    assert dnd5e["can_install"] is True


def test_install_enable_disable_remove_flow(db):
    user_id = seed_user(name="Owner", email="owner-systems@test.com")
    service = SystemInstallService()

    install = service.install(package_id="dnd5e", user_id=user_id)
    assert install.success
    assert _by_id(service.list_for_tab(), "dnd5e")["status"] == "installed"

    assert service.enable(package_id="dnd5e").success
    assert _by_id(service.list_for_tab(), "dnd5e")["status"] == "enabled"
    assert _by_id(service.list_for_tab(), "dnd5e")["enabled"] is True

    assert service.disable(package_id="dnd5e").success
    assert _by_id(service.list_for_tab(), "dnd5e")["status"] == "disabled"

    assert service.remove(package_id="dnd5e").success
    assert _by_id(service.list_for_tab(), "dnd5e")["status"] == "available"


def test_install_invalid_manifest_fails(db, tmp_path, monkeypatch):
    from app.engine.systems import system_loader

    systems_dir = tmp_path / "systems"
    bad_pkg = systems_dir / "invalid-system"
    bad_pkg.mkdir(parents=True)
    (bad_pkg / "manifest.json").write_text(
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
                "capabilities": ["actors.register", "sheets.declarative"],
                "system": {
                    "id": "Invalid System",
                    "storage": {"model": "scoped-json-v1"},
                    "actorTypes": [
                        {
                            "id": "character",
                            "label": "Character",
                            "schema": "schemas/character.schema.json",
                            "sheet": "layouts/character.sheet.gw.json",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(system_loader, "SYSTEMS_DIR", systems_dir)

    user_id = seed_user(name="Owner", email="owner-systems-2@test.com")
    result = SystemInstallService().install(package_id="invalid-system", user_id=user_id)
    assert not result.success
    assert result.error_key == "inside.systems.errors.invalid_manifest"


def test_enable_requires_install(db):
    result = SystemInstallService().enable(package_id="dnd5e")
    assert not result.success
    assert result.error_key == "inside.systems.errors.not_installed"


def test_install_unknown_system_fails(db):
    user_id = seed_user(name="Owner", email="owner-systems-3@test.com")
    result = SystemInstallService().install(package_id="does-not-exist", user_id=user_id)
    assert not result.success
    assert result.error_key == "inside.systems.errors.not_found"
