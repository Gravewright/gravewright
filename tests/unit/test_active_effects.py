from __future__ import annotations

import app.engine.rules.formula_engine as formula_engine
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.sheet_action_service import SheetActionService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sheets.sheet_drop_service import SheetDropService
from app.engine.systems.system_install_service import SystemInstallService
from tests.conftest import seed_campaign, seed_user


def _setup(prefix: str) -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-active-effects-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    systems = SystemInstallService()
    assert systems.install(package_id="dnd5e", user_id=gm_id).success
    assert systems.enable(package_id="dnd5e").success
    actor = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="character",
        name="Fiona",
    )
    assert actor.success
    SheetDataService().patch_data(
        actor_id=actor.actor_id,
        user_id=gm_id,
        patch={"abilities.str.score": 10, "level": 1},
    )
    return gm_id, campaign_id, actor.actor_id


def test_drop_effect_adds_active_effect_instance(db):
    gm_id, _, actor_id = _setup("drop")

    result = SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source={"kind": "content_pack_entry", "pack_id": "dnd5e-conditions", "entry_id": "bless"},
        drop_zone="effects",
    )

    assert result.success
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert len(data["effects"]) == 1
    effect = data["effects"][0]
    assert effect["id"].startswith("actor_item_")
    assert effect["type"] == "effect"
    assert effect["name"] == "Bless"
    assert effect["enabled"] is True
    assert effect["data"]["category"] == "buff"
    assert effect["source"]["kind"] == "content_pack_entry"


def test_active_effect_modifier_applies_to_matching_roll(db, monkeypatch):
    rolls = iter([10, 4])
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: next(rolls))
    gm_id, _, actor_id = _setup("roll")
    assert SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source={"kind": "content_pack_entry", "pack_id": "dnd5e-conditions", "entry_id": "bless"},
        drop_zone="effects",
    ).success

    result = SheetActionService().execute(
        actor_id=actor_id,
        user_id=gm_id,
        action_id="roll.save.str",
    )

    assert result.success
    assert [group["notation"] for group in result.groups] == ["1d20", "1d4"]
    assert result.metadata["effects"][0]["effectName"] == "Bless"
    assert result.metadata["effects"][0]["target"] == "roll.save"


def test_disabled_active_effect_does_not_apply(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 10)
    gm_id, _, actor_id = _setup("disabled")
    assert SheetDropService().drop(
        actor_id=actor_id,
        user_id=gm_id,
        source={"kind": "content_pack_entry", "pack_id": "dnd5e-conditions", "entry_id": "bless"},
        drop_zone="effects",
    ).success
    data = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    effect_id = data["effects"][0]["id"]
    from app.engine.sheets.sheet_item_service import SheetItemService

    assert SheetItemService().patch_item(
        actor_id=actor_id,
        user_id=gm_id,
        item_instance_id=effect_id,
        patch={"enabled": False},
    ).success

    result = SheetActionService().execute(
        actor_id=actor_id,
        user_id=gm_id,
        action_id="roll.save.str",
    )

    assert result.success
    assert [group["notation"] for group in result.groups] == ["1d20"]
    assert result.metadata["effects"] == []


def test_custom_effect_builder_stat_modifier_changes_effective_sheet_bundle(db):
    from app.engine.sheets.actor_sheet_service import ActorSheetService

    gm_id, _, actor_id = _setup("stat")
    SheetDataService().patch_data(
        actor_id=actor_id,
        user_id=gm_id,
        patch={
            "ac": 10,
            "effects": [
                {
                    "id": "active_effect_shield",
                    "type": "effect",
                    "name": "Shield of Faith",
                    "enabled": True,
                    "data": {
                        "category": "buff",
                        "modifiers": [
                            {
                                "target": "stat.ac",
                                "operation": "add",
                                "value": 2,
                                "label": "Shield of Faith",
                            }
                        ],
                    },
                }
            ],
        },
    )

    bundle = ActorSheetService().build_bundle(actor_id=actor_id, user_id=gm_id)

    assert bundle is not None
    assert bundle.data["ac"] == 12
                                                                                         
    raw = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id).data
    assert raw["ac"] == 10


def test_custom_effect_builder_specific_roll_target_applies_only_when_matching(db, monkeypatch):
    rolls = iter([10, 4, 10])
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: next(rolls))
    gm_id, _, actor_id = _setup("specific")
    SheetDataService().patch_data(
        actor_id=actor_id,
        user_id=gm_id,
        patch={
            "effects": [
                {
                    "id": "active_effect_str_save",
                    "type": "effect",
                    "name": "Strength Ward",
                    "enabled": True,
                    "data": {
                        "category": "buff",
                        "modifiers": [
                            {
                                "target": "roll.save.str",
                                "operation": "add_dice",
                                "value": "1d4",
                                "label": "Strength Ward",
                            }
                        ],
                    },
                }
            ]
        },
    )

    str_result = SheetActionService().execute(
        actor_id=actor_id,
        user_id=gm_id,
        action_id="roll.save.str",
    )
    dex_result = SheetActionService().execute(
        actor_id=actor_id,
        user_id=gm_id,
        action_id="roll.save.dex",
    )

    assert str_result.success
    assert [group["notation"] for group in str_result.groups] == ["1d20", "1d4"]
    assert str_result.metadata["effects"][0]["target"] == "roll.save.str"
    assert dex_result.success
    assert [group["notation"] for group in dex_result.groups] == ["1d20"]
    assert dex_result.metadata["effects"] == []
