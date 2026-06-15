from __future__ import annotations

import app.engine.rules.formula_engine as formula_engine
from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sheets.sheet_drop_service import SheetDropService
from app.engine.sheets.sheet_item_service import SheetItemService
from app.engine.sdk.package_install_service import PackageInstallService
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup(prefix: str) -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-sheet-item-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = PackageInstallService()
    assert svc.install(package_id="dnd5e", user_id=gm_id).success
    assert svc.enable(package_id="dnd5e").success
    actor = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="character",
        name="Aria",
    )
    assert actor.success
    dropped = SheetDropService().drop(
        actor_id=actor.actor_id,
        user_id=gm_id,
        source={"kind": "content_pack_entry", "pack_id": "dnd5e-weapons", "entry_id": "template-longsword"},
        drop_zone="weapons",
    )
    assert dropped.success
    return gm_id, campaign_id, actor.actor_id


def _first_item(actor_id: str, user_id: str) -> dict:
    data = SheetDataService().get_data(actor_id=actor_id, user_id=user_id).data
    return data["weapons"][0]


def test_drop_assigns_actor_item_instance_id(db):
    gm_id, _, actor_id = _setup("id")
    item = _first_item(actor_id, gm_id)
    assert item["id"].startswith("actor_item_")
    assert item["source"]["kind"] == "content_pack_entry"


def test_item_damage_action_uses_item_context(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)
    gm_id, _, actor_id = _setup("damage")
    item = _first_item(actor_id, gm_id)

    result = SheetItemService().execute_action(
        actor_id=actor_id,
        user_id=gm_id,
        item_instance_id=item["id"],
        action_id="weapon.damage",
    )

    assert result.success
    assert result.action_type == "roll"
    assert result.label == "Espada Longa (modelo)"
    assert result.groups[0]["notation"] == "1d8"
    assert result.total == 4


def test_patch_item_instance_does_not_patch_source(db):
    gm_id, _, actor_id = _setup("patch")
    item = _first_item(actor_id, gm_id)

    result = SheetItemService().patch_item(
        actor_id=actor_id,
        user_id=gm_id,
        item_instance_id=item["id"],
        patch={"name": "Espada Longa (modelo) Flamejante", "data.damage": "1d8+1d6"},
    )

    assert result.success
    updated = _first_item(actor_id, gm_id)
    assert updated["name"] == "Espada Longa (modelo) Flamejante"
    assert updated["data"]["damage"] == "1d8+1d6"


def test_remove_item_instance_removes_only_from_sheet(db):
    gm_id, _, actor_id = _setup("remove")
    item = _first_item(actor_id, gm_id)

    result = SheetItemService().remove_item(
        actor_id=actor_id,
        user_id=gm_id,
        item_instance_id=item["id"],
    )

    assert result.success
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert data["weapons"] == []


def test_player_without_owner_cannot_use_item_action(db):
    gm_id, campaign_id, actor_id = _setup("perm")
    player_id = seed_user(name="Player", email="player-sheet-item-perm@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    item = _first_item(actor_id, gm_id)

    result = SheetItemService().execute_action(
        actor_id=actor_id,
        user_id=player_id,
        item_instance_id=item["id"],
        action_id="weapon.damage",
    )

    assert not result.success
    assert result.error_key == "game.actors.errors.not_allowed"


def test_missing_item_instance_fails(db):
    gm_id, _, actor_id = _setup("missing")

    result = SheetItemService().execute_action(
        actor_id=actor_id,
        user_id=gm_id,
        item_instance_id="actor_item_missing",
        action_id="weapon.damage",
    )

    assert not result.success
    assert result.error_key == "game.sheet_items.errors.item_not_found"


def test_item_action_result_includes_actor_item_metadata(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 5)
    gm_id, _, actor_id = _setup("metadata")
    item = _first_item(actor_id, gm_id)

    result = SheetItemService().execute_action(
        actor_id=actor_id,
        user_id=gm_id,
        item_instance_id=item["id"],
        action_id="weapon.damage",
        roll_options={"extraDice": ["1d4"], "visibility": "public"},
    )

    assert result.success
    assert result.metadata["actionId"] == "weapon.damage"
    assert result.metadata["actorId"] == actor_id
    assert result.metadata["source"] == {
        "kind": "actor_item_instance",
        "itemInstanceId": item["id"],
    }
    assert result.metadata["formula"]["base"] == "@item.data.damage"
    assert result.metadata["formula"]["final"] == "1d8 + 1d4"
    assert result.metadata["formula"]["resolved"] == "1d8 + 1d4"
    assert result.metadata["formula"]["display"] == "1d8 + 1d4"
    assert result.metadata["rollInput"]["extraDice"] == ["1d4"]
    assert result.metadata["presentation"]["chatCard"] == "weapon-damage"
