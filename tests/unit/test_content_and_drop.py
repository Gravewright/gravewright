from __future__ import annotations

from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.content.content_import_service import ContentImportService
from app.engine.content.content_pack_service import ContentPackService
from app.engine.items.item_service import ItemService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sheets.sheet_drop_service import SheetDropService
from tests.conftest import seed_campaign, seed_member, seed_system, seed_user


def _content_source(pack_id: str, entry_id: str) -> dict:
    return {"kind": "content_pack_entry", "pack_id": pack_id, "entry_id": entry_id}


def _setup(prefix: str) -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id, package_id="dnd5e")
    actor = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="character",
        name="Aria",
    )
    assert actor.success
    return gm_id, campaign_id, actor.actor_id


def test_content_pack_listing_and_entries(db):
    gm_id, _, _ = _setup("content-list")
    content = ContentPackService()
    pack_ids = {p["id"] for p in content.list_packs("dnd5e")}
    assert "dnd5e-weapons" in pack_ids

    pack = content.get_pack("dnd5e", "dnd5e-weapons")
    assert pack["type"] == "item_pack"
    assert any(e["id"] == "template-longsword" for e in pack["entries"])
    assert (
        content.get_entry("dnd5e", "dnd5e-weapons", "template-longsword")["name"] == "Espada Longa (modelo)"
    )


def test_drop_weapon_appends_to_inventory(db):
    gm_id, _, actor_id = _setup("drop-ok")

    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source=_content_source("dnd5e-weapons", "template-longsword"),
        drop_zone="weapons",
    )
    assert result.success
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert len(data["weapons"]) == 1
    assert data["weapons"][0]["name"] == "Espada Longa (modelo)"
    assert data["weapons"][0]["source"]["kind"] == "content_pack_entry"


def test_drop_unknown_zone_fails(db):
    gm_id, _, actor_id = _setup("drop-zone")
    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source=_content_source("dnd5e-weapons", "template-longsword"),
        drop_zone="nowhere",
    )
    assert not result.success
    assert result.error_key == "game.drop.errors.zone_not_found"


def test_drop_rejects_unaccepted_type(db):
    gm_id, _, actor_id = _setup("drop-type")
                                                                                    
    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source=_content_source("dnd5e-spells", "template-arcane-bolt"),
        drop_zone="weapons",
    )
    assert not result.success
    assert result.error_key == "game.drop.errors.not_accepted"


def test_player_cannot_drop(db):
    gm_id, campaign_id, actor_id = _setup("drop-perm")
    player_id = seed_user(name="Player", email="player-drop-perm@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=player_id,
        source=_content_source("dnd5e-weapons", "template-longsword"),
        drop_zone="weapons",
    )
    assert not result.success
    assert result.error_key == "game.actors.errors.not_allowed"


def test_drop_item_document_appends_snapshot(db):
    """A campaign Item dropped on the sheet is projected to a DropEntry and
    stored as an editable instance carrying source.kind = item (doc §22.2)."""
    gm_id, campaign_id, actor_id = _setup("drop-item")
    created = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Espada Longa (modelo) +1",
        data={"damage": "1d8+1", "damageType": "slashing"},
    )
    assert created.success

    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source={"kind": "item", "item_id": created.item_id},
        drop_zone="weapons",
    )
    assert result.success
    row = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data["weapons"][0]
    assert row["name"] == "Espada Longa (modelo) +1"
    assert row["type"] == "weapon"
    assert row["data"]["damage"] == "1d8+1"
    assert row["source"] == {"kind": "item", "itemId": created.item_id}


def test_sheet_wide_drop_routes_by_type(db):
    """No explicit drop_zone: the backend routes the entry to the first zone
    whose accepts matches its type (Foundry-style drop anywhere on the sheet)."""
    gm_id, _, actor_id = _setup("drop-route")
    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source=_content_source("dnd5e-weapons", "template-longsword"),
        drop_zone="",
    )
    assert result.success
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["weapons"][0]["name"] == "Espada Longa (modelo)"


def test_sheet_wide_drop_routes_spell_by_type(db):
    gm_id, _, actor_id = _setup("drop-route-spell")
    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source=_content_source("dnd5e-spells", "template-arcane-bolt"),
        drop_zone="",
    )
    assert result.success
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["spells"][0]["name"] == "Raio Arcano (modelo)"


def test_drop_unknown_item_fails(db):
    gm_id, _, actor_id = _setup("drop-item-missing")
    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source={"kind": "item", "item_id": "does-not-exist"},
        drop_zone="inventory",
    )
    assert not result.success
    assert result.error_key == "game.drop.errors.item_not_found"


def test_drop_unsupported_source_fails(db):
    gm_id, _, actor_id = _setup("drop-bad-source")
    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source={"kind": "journal", "journal_id": "x"},
        drop_zone="inventory",
    )
    assert not result.success
    assert result.error_key == "game.drop.errors.unsupported_source"


def test_import_actor_pack_creates_seeded_actor(db):
    gm_id, campaign_id, _ = _setup("import")
    result = ContentImportService().import_entry(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        pack_id="dnd5e-monsters",
        entry_id="template-monster",
    )
    assert result.success
    actor = ActorService().get_actor(actor_id=result.actor_id, user_id=gm_id)
    assert actor["name"] == "Monstro Modelo"
    assert actor["type"] == "monster"
    data = SheetDataService().get_data(actor_id=result.actor_id, user_id=gm_id).data
    assert data["hp"]["value"] == 7


def test_import_non_actor_pack_rejected(db):
    gm_id, campaign_id, _ = _setup("import-bad")
    result = ContentImportService().import_entry(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        pack_id="dnd5e-weapons",
        entry_id="template-longsword",
    )
    assert not result.success
    assert result.error_key == "game.content.errors.not_importable"
