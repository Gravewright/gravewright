from __future__ import annotations

import io
import json
import zipfile

from app.engine.modules.module_install_service import ModuleInstallService
from app.persistence.repositories.installed_module_repository import InstalledModuleRepository
from tests.conftest import seed_user


def _manifest(module_id: str = "zip-module") -> dict:
    return {
        "schemaVersion": 1,
        "type": "module",
        "id": module_id,
        "name": "ZIP Module",
        "version": "0.1.0",
        "apiVersion": "1",
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["assets.ui", "assets.styles", "assets.scripts"],
        "module": {
            "id": module_id,
            "entrypoints": {
                "game": {"styles": ["assets/game.css"], "scripts": ["assets/game.js"]}
            },
        },
    }


def _zip(entries: dict[str, bytes | str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content if isinstance(content, bytes) else content.encode("utf-8"))
    return buf.getvalue()


def _module_zip(module_id: str = "zip-module", *, root_folder: bool = False) -> bytes:
    prefix = f"{module_id}/" if root_folder else ""
    return _zip(
        {
            f"{prefix}manifest.json": json.dumps(_manifest(module_id)),
            f"{prefix}assets/game.css": ".zip-module{}",
            f"{prefix}assets/game.js": "export {};",
        }
    )


def test_upload_module_zip_installs_to_modules_dir(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)
    user_id = seed_user(name="Owner", email="owner-module-upload@test.com")

    result = ModuleInstallService().install_uploaded_package(
        filename="zip-module.zip",
        data=_module_zip(),
        user_id=user_id,
    )

    assert result.success
    assert result.module_id == "zip-module"
    assert (modules_dir / "zip-module" / "manifest.json").is_file()
    assert (modules_dir / "zip-module" / "assets" / "game.js").is_file()

    record = InstalledModuleRepository().get("zip-module")
    assert record is not None
    assert record["package_id"] == "zip-module"
    assert record["package_sha256"]


def test_upload_module_zip_accepts_single_root_folder(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)
    user_id = seed_user(name="Owner", email="owner-module-upload-root@test.com")

    result = ModuleInstallService().install_uploaded_package(
        filename="rooted.zip",
        data=_module_zip("rooted-module", root_folder=True),
        user_id=user_id,
    )

    assert result.success
    assert (modules_dir / "rooted-module" / "manifest.json").is_file()
    assert not (modules_dir / "rooted-module" / "rooted-module").exists()


def test_upload_module_zip_rejects_path_traversal(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)
    user_id = seed_user(name="Owner", email="owner-module-upload-traversal@test.com")

    data = _zip(
        {
            "manifest.json": json.dumps(_manifest("evil-module")),
            "assets/game.css": ".x{}",
            "../evil.js": "export {};",
        }
    )

    result = ModuleInstallService().install_uploaded_package(
        filename="evil.zip",
        data=data,
        user_id=user_id,
    )

    assert not result.success
    assert result.error_key == "inside.modules.errors.package_unsafe"
    assert not (modules_dir / "evil-module").exists()


def test_upload_module_zip_blocks_replacing_enabled_module(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)
    user_id = seed_user(name="Owner", email="owner-module-upload-enabled@test.com")
    service = ModuleInstallService()

    installed = service.install_uploaded_package(filename="zip-module.zip", data=_module_zip(), user_id=user_id)
    assert installed.success
    assert service.enable(package_id="zip-module").success

    replaced = service.install_uploaded_package(filename="zip-module.zip", data=_module_zip(), user_id=user_id)

    assert not replaced.success
    assert replaced.error_key == "inside.modules.errors.disable_before_replace"


def test_upload_module_zip_blocks_replacing_campaign_enabled_module(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)
    user_id = seed_user(name="Owner", email="owner-module-upload-campaign-enabled@test.com")
    campaign_id = seed_campaign(user_id)
    service = ModuleInstallService()

    installed = service.install_uploaded_package(filename="zip-module.zip", data=_module_zip(), user_id=user_id)
    assert installed.success
    assert service.enable(package_id="zip-module").success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="zip-module").success
    assert service.disable(package_id="zip-module").success

    replaced = service.install_uploaded_package(filename="zip-module.zip", data=_module_zip(), user_id=user_id)

    assert not replaced.success
    assert replaced.error_key == "inside.modules.errors.disable_campaigns_before_replace"


def test_upload_module_zip_allows_replacing_after_global_and_campaign_disable(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from tests.conftest import seed_campaign

    modules_dir = tmp_path / "modules"
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)
    user_id = seed_user(name="Owner", email="owner-module-upload-safe-replace@test.com")
    campaign_id = seed_campaign(user_id)
    service = ModuleInstallService()

    assert service.install_uploaded_package(filename="zip-module.zip", data=_module_zip(), user_id=user_id).success
    assert service.enable(package_id="zip-module").success
    assert service.enable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="zip-module").success
    assert service.disable_for_campaign(campaign_id=campaign_id, user_id=user_id, module_id="zip-module").success
    assert service.disable(package_id="zip-module").success

    replaced = service.install_uploaded_package(filename="zip-module.zip", data=_module_zip(), user_id=user_id)

    assert replaced.success
    assert (modules_dir / "zip-module" / "manifest.json").is_file()
