from __future__ import annotations

import json

from app.engine.modules.module_content_import_service import ModuleContentImportService
from app.engine.modules.module_content_pack_service import ModuleContentPackService
from app.engine.modules.module_install_service import ModuleInstallService
from app.engine.modules.module_manifest_validator import validate_manifest
from app.persistence.repositories.journal_repository import JournalRepository
from tests.conftest import seed_campaign, seed_member, seed_system, seed_user


def _manifest(*, content_packs: list[dict]) -> dict:
    return {
        "schemaVersion": 1,
        "type": "module",
        "id": "sample-module",
        "name": "Sample Module",
        "version": "0.1.0",
        "apiVersion": "1",
        "compatibility": {"minimum": "1.0.0-rc.1", "verified": "1.0.0-rc.1", "maximum": "1.x"},
        "capabilities": ["assets.ui", "assets.styles", "assets.scripts", "content.packs"],
        "module": {
            "id": "sample-module",
            "entrypoints": {"game": {"styles": ["assets/sample.css"], "scripts": ["assets/sample.js"]}},
            "contentPacks": content_packs,
        },
    }


def _write_module_package(base, *, content_packs: list[dict], pack_files: dict[str, dict]):
    package = base / "sample-module"
    (package / "assets").mkdir(parents=True)
    (package / "packs").mkdir(parents=True)
    (package / "assets" / "sample.css").write_text(".sample{}", encoding="utf-8")
    (package / "assets" / "sample.js").write_text("export {};", encoding="utf-8")
    for relative, data in pack_files.items():
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    (package / "manifest.json").write_text(json.dumps(_manifest(content_packs=content_packs)), encoding="utf-8")
    return package


def _install_enable_for_campaign(*, modules_dir, gm_id: str, campaign_id: str):
    service = ModuleInstallService()
    installed = service.install(package_id="sample-module", user_id=gm_id)
    assert installed.success, installed.error_key
    assert service.enable(package_id="sample-module").success
    enabled = service.enable_for_campaign(campaign_id=campaign_id, user_id=gm_id, module_id="sample-module")
    assert enabled.success, enabled.error_key


def test_module_manifest_validates_content_pack_contract():
    result = validate_manifest(
        _manifest(
            content_packs=[
                {"id": "sample-journals", "type": "journal_pack", "label": "Journals", "path": "packs/journals.json"}
            ]
        )
    )
    assert result.errors == []


def test_module_manifest_rejects_invalid_content_pack():
    result = validate_manifest(
        _manifest(
            content_packs=[
                {"id": "Bad Pack", "type": "table_pack", "label": "x", "path": "packs/not-json.txt"}
            ]
        )
    )
    assert "inside.modules.validation.content_pack_id" in result.errors
    assert "inside.modules.validation.content_pack_type" in result.errors
    assert "inside.modules.validation.content_pack_path" in result.errors


def test_module_content_pack_listing_requires_campaign_enablement(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_module_package(
        modules_dir,
        content_packs=[{"id": "sample-journals", "type": "journal_pack", "label": "Journals", "path": "packs/journals.json"}],
        pack_files={"packs/journals.json": {"entries": [{"id": "welcome", "type": "handout", "title": "Welcome"}]}},
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-packs@test.com")
    campaign_id = seed_campaign(gm_id)
    service = ModuleContentPackService()

    assert service.list_packs(campaign_id=campaign_id, module_id="sample-module", user_id=gm_id) == []
    _install_enable_for_campaign(modules_dir=modules_dir, gm_id=gm_id, campaign_id=campaign_id)

    packs = service.list_packs(campaign_id=campaign_id, module_id="sample-module", user_id=gm_id)
    assert packs == [{"id": "sample-journals", "type": "journal_pack", "label": "Journals", "module_id": "sample-module"}]
    pack = service.get_pack(campaign_id=campaign_id, module_id="sample-module", pack_id="sample-journals", user_id=gm_id)
    assert pack is not None
    assert pack["entries"][0]["id"] == "welcome"


def test_module_content_imports_journal_pack_entry(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_module_package(
        modules_dir,
        content_packs=[{"id": "sample-journals", "type": "journal_pack", "label": "Journals", "path": "packs/journals.json"}],
        pack_files={
            "packs/journals.json": {
                "entries": [
                    {
                        "id": "welcome",
                        "type": "handout",
                        "title": "Welcome Handout",
                        "visibility": "shared",
                        "content": "Hello from a module.",
                        "data": {"source": "module"},
                    }
                ]
            }
        },
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-import-journal@test.com")
    campaign_id = seed_campaign(gm_id)
    _install_enable_for_campaign(modules_dir=modules_dir, gm_id=gm_id, campaign_id=campaign_id)

    result = ModuleContentImportService().import_entry(
        campaign_id=campaign_id,
        user_id=gm_id,
        module_id="sample-module",
        pack_id="sample-journals",
        entry_id="welcome",
    )

    assert result.success
    assert result.journal_id
    journal = JournalRepository().get_by_id(result.journal_id)
    assert journal is not None
    assert journal["title"] == "Welcome Handout"
    assert journal["visibility"] == "shared"
    assert journal["content_markdown"] == "Hello from a module."


def test_module_content_import_rejects_non_gm(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader

    modules_dir = tmp_path / "modules"
    _write_module_package(
        modules_dir,
        content_packs=[{"id": "sample-journals", "type": "journal_pack", "label": "Journals", "path": "packs/journals.json"}],
        pack_files={"packs/journals.json": {"entries": [{"id": "welcome", "type": "handout", "title": "Welcome"}]}},
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-import-forbid@test.com")
    player_id = seed_user(name="Player", email="player-module-import-forbid@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    _install_enable_for_campaign(modules_dir=modules_dir, gm_id=gm_id, campaign_id=campaign_id)

    result = ModuleContentImportService().import_entry(
        campaign_id=campaign_id,
        user_id=player_id,
        module_id="sample-module",
        pack_id="sample-journals",
        entry_id="welcome",
    )

    assert not result.success
    assert result.error_key == "inside.campaigns.errors.gm_required"


def test_module_content_imports_actor_and_item_entries(db, tmp_path, monkeypatch):
    from app.engine.modules import module_loader
    from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.item_repository import ItemRepository

    modules_dir = tmp_path / "modules"
    _write_module_package(
        modules_dir,
        content_packs=[
            {"id": "sample-actors", "type": "actor_pack", "label": "Actors", "path": "packs/actors.json"},
            {"id": "sample-items", "type": "item_pack", "label": "Items", "path": "packs/items.json"},
        ],
        pack_files={
            "packs/actors.json": {"entries": [{"id": "goblin", "type": "character", "name": "Module Hero", "data": {"hp": {"max": 7}}}]},
            "packs/items.json": {"entries": [{"id": "sword", "type": "weapon", "name": "Module Sword", "data": {"damage": "1d8"}}]},
        },
    )
    monkeypatch.setattr(module_loader, "MODULES_DIR", modules_dir)

    gm_id = seed_user(name="GM", email="gm-module-import-core@test.com")
    campaign_id = seed_campaign(gm_id)
    system_id = seed_system(campaign_id, gm_id)
    _install_enable_for_campaign(modules_dir=modules_dir, gm_id=gm_id, campaign_id=campaign_id)

    importer = ModuleContentImportService()
    actor = importer.import_entry(campaign_id=campaign_id, user_id=gm_id, module_id="sample-module", pack_id="sample-actors", entry_id="goblin")
    item = importer.import_entry(campaign_id=campaign_id, user_id=gm_id, module_id="sample-module", pack_id="sample-items", entry_id="sword")

    assert actor.success
    assert item.success
    assert ActorRepository().get(actor.actor_id)["name"] == "Module Hero"
    assert ItemRepository().get(item.item_id)["name"] == "Module Sword"
    storage = ScopedJsonStorage()
    assert storage.read_actor(system_id=system_id, campaign_id=campaign_id, actor_id=actor.actor_id)["data"]["hp"]["max"] == 7
    assert storage.read_item(system_id=system_id, campaign_id=campaign_id, item_id=item.item_id)["data"]["damage"] == "1d8"
