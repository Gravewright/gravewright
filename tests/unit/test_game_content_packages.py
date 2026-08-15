from pathlib import Path
from types import SimpleNamespace

from app.business.game_page_service import GamePageService
from app.engine.sdk.package_content_service import PackageContentService
from tests.conftest import seed_campaign, seed_user


ROOT = Path(__file__).resolve().parents[2]


def test_active_content_package_is_exposed_to_the_game_content_browser(db, monkeypatch):
    gm_id = seed_user(name="GM", email="content-browser-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    packages = [
        {
            "id": "savage-worlds",
            "name": "Savage Worlds",
            "kind": "ruleset",
            "status": "enabled",
            "capabilities": [],
            "actor_types": [],
            "item_types": [],
            "area_markers": [],
        },
        {
            "id": "savage-pathfinder-private",
            "name": "Savage Pathfinder: Núcleo Privado",
            "kind": "content",
            "status": "enabled",
            "capabilities": ["content.packs"],
        },
    ]
    service = GamePageService()
    monkeypatch.setattr(service.system_install, "list_for_tab", lambda: packages)
    monkeypatch.setattr(
        service.system_install.campaign_packages,
        "list_for_campaign",
        lambda requested_campaign_id: [
            {
                "campaign_id": requested_campaign_id,
                "package_id": "savage-pathfinder-private",
                "status": "active",
            }
        ],
    )

    context = service.build_context(user_id=gm_id)
    room = next(room for room in context.rooms if room["id"] == campaign_id)

    assert room["content_packages"] == [
        {
            "id": "savage-pathfinder-private",
            "name": "Savage Pathfinder: Núcleo Privado",
        }
    ]
    assert all(system["id"] != "savage-pathfinder-private" for system in room["enabled_systems"])


def test_gm_panel_has_a_content_pack_button():
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")

    assert 'data-panel-toggle="panel-content-{{ room.id }}"' in template
    assert 't("game.gm.content_packs")' in template
    assert "t('game.content.no_active_packages')" in template


def test_active_ruleset_directory_visibility_reaches_the_game_context(db, monkeypatch):
    gm_id = seed_user(name="PDF GM", email="pdf-directory-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    service = GamePageService()
    service.campaigns.campaigns.update_system(
        campaign_id=campaign_id,
        changed_by_user_id=gm_id,
        next_system_id="pdf-ruleset",
    )
    monkeypatch.setattr(
        service.system_install,
        "list_for_tab",
        lambda: [
            {
                "id": "pdf-ruleset",
                "name": "PDF Ruleset",
                "kind": "ruleset",
                "status": "enabled",
                "capabilities": [],
                "actor_types": [{"id": "character", "label": "Character"}],
                "item_types": [],
                "area_markers": [],
                "directories": {"actors": True, "items": False, "journals": True},
            }
        ],
    )
    monkeypatch.setattr(
        service.system_install.installed,
        "get",
        lambda package_id: {"id": package_id} if package_id == "pdf-ruleset" else None,
    )

    context = service.build_context(user_id=gm_id)
    room = next(room for room in context.rooms if room["id"] == campaign_id)

    assert room["active_system"]["directories"]["items"] is False


def test_content_browser_refreshes_active_packages_from_server():
    script = (ROOT / "static/js/content/content-browser.js").read_text(encoding="utf-8")

    assert "/game/content/active-packages?campaign_id=" in script


def test_bulk_import_folder_is_nested_under_package_name():
    rows = []

    class Folders:
        def list_for_campaign(self, *, campaign_id):
            return list(rows)

    class Items:
        folders = Folders()

        def create_folder(self, *, campaign_id, user_id, name, parent_id="", color=""):
            folder_id = f"folder-{len(rows) + 1}"
            rows.append({"id": folder_id, "name": name, "parent_id": parent_id or None})
            return SimpleNamespace(success=True, folder_id=folder_id)

    service = PackageContentService()
    service.items = Items()

    folder_id = service.ensure_import_folder(
        campaign_id="campaign",
        user_id="gm",
        package_name="Example Package",
        pack={"id": "skills", "label": "Skills", "type": "item_pack"},
    )

    assert rows == [
        {"id": "folder-1", "name": "Example Package", "parent_id": None},
        {"id": "folder-2", "name": "Skills", "parent_id": "folder-1"},
    ]
    assert folder_id == "folder-2"
