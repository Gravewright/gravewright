from __future__ import annotations

import app.engine.rules.formula_engine as formula_engine
from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.sheet_action_service import SheetActionService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sdk.package_install_service import PackageInstallService
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup(prefix: str) -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = PackageInstallService()
    assert svc.install(package_id="dnd5e", user_id=gm_id).success
    assert svc.enable(package_id="dnd5e").success
    actor = ActorService().create_actor(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e",
        actor_type="character", name="Aria",
    )
    assert actor.success
    SheetDataService().patch_data(
        actor_id=actor.actor_id, user_id=gm_id,
        patch={"hp.value": 20, "hp.max": 30, "ac": 15, "abilities.dex.score": 14},
    )
    return gm_id, campaign_id, actor.actor_id


def test_roll_action_uses_derived_initiative(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 15)
    gm_id, _, actor_id = _setup("act-roll")

    result = SheetActionService().execute(
        actor_id=actor_id, action_id="roll.initiative", user_id=gm_id
    )
    assert result.success
    assert result.action_type == "roll"
                                                                        
    assert result.total == 17
    assert result.modifier == 2
    assert result.groups[0]["notation"] == "1d20"


def test_patch_action_applies_damage_and_updates_token_view(db):
    gm_id, _, actor_id = _setup("act-patch")

    result = SheetActionService().execute(
        actor_id=actor_id, action_id="resource.hp.damage", user_id=gm_id,
        inputs={"amount": 5},
    )
    assert result.success
    assert result.action_type == "patch"
    assert result.version == 3                                    
    assert result.changed_paths == ["sheet.hp.value"]
    assert result.token_view["bars"]["hp"]["value"] == 15

    fetched = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id)
    assert fetched.data["hp"]["value"] == 15


def test_heal_clamps_to_max(db):
    gm_id, _, actor_id = _setup("act-heal")
    service = SheetActionService()
    service.execute(actor_id=actor_id, action_id="resource.hp.damage", user_id=gm_id, inputs={"amount": 15})
    healed = service.execute(
        actor_id=actor_id, action_id="resource.hp.heal", user_id=gm_id, inputs={"amount": 999}
    )
    assert healed.success
    fetched = SheetDataService().get_data(actor_id=actor_id, user_id=gm_id)
    assert fetched.data["hp"]["value"] == 30                  


def test_unknown_action_fails(db):
    gm_id, _, actor_id = _setup("act-unknown")
    result = SheetActionService().execute(actor_id=actor_id, action_id="roll.nope", user_id=gm_id)
    assert not result.success
    assert result.error_key == "game.actions.errors.action_not_found"


def test_player_cannot_patch_via_action(db):
    gm_id, campaign_id, actor_id = _setup("act-perm")
    player_id = seed_user(name="Player", email="player-act-perm@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = SheetActionService().execute(
        actor_id=actor_id, action_id="resource.hp.damage", user_id=player_id, inputs={"amount": 5}
    )
    assert not result.success
    assert result.error_key == "game.actors.errors.not_allowed"


def test_dice_roll_command(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)
    gm_id, _, actor_id = _setup("act-dice")
    result = SheetActionService().roll_formula(
        actor_id=actor_id, formula="2d6 + 1", user_id=gm_id, label="Damage"
    )
    assert result.success
    assert result.total == 9             
    assert result.label == "Damage"


def test_roll_action_supports_advantage_roll_options(db, monkeypatch):
    rolls = iter([3, 17])
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: next(rolls))
    gm_id, _, actor_id = _setup("act-advantage")

    result = SheetActionService().execute(
        actor_id=actor_id,
        action_id="roll.initiative",
        user_id=gm_id,
        roll_options={"mode": "advantage"},
    )

    assert result.success
    assert result.groups[0]["notation"] == "2d20kh1"
    assert result.groups[0]["results"] == [3, 17]
    assert result.groups[0]["subtotal"] == 17
    assert result.total == 19


def test_roll_action_supports_extra_dice_modifier_and_visibility(db, monkeypatch):
    rolls = iter([10, 4])
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: next(rolls))
    gm_id, _, actor_id = _setup("act-roll-options")

    result = SheetActionService().execute(
        actor_id=actor_id,
        action_id="roll.initiative",
        user_id=gm_id,
        roll_options={"extraDice": ["1d4", "bad"], "extraModifier": 3, "visibility": "gm"},
    )

    assert result.success
    assert [g["notation"] for g in result.groups] == ["1d20", "1d4"]
    assert result.total == 19                                       
    assert result.visibility == "gm"


def test_roll_action_schema_driven_transforms(db, monkeypatch):
    rolls = iter([2, 18, 4])
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: next(rolls))
    gm_id, _, actor_id = _setup("act-roll-intent")
    service = SheetActionService()
    action = {
        "type": "roll",
        "label": "Generic Check",
        "formula": "1d20 + @sheet.init",
        "visibility": "public",
        "transforms": [
            {"when": "input.mode == 'advantage'", "replaceFirstDie": {"from": "1d20", "to": "2d20kh1"}},
            {"when": "input.extraModifier != 0", "append": "@input.extraModifier"},
            {"when": "input.extraDice", "appendEach": "@input.extraDice"},
        ],
    }
    monkeypatch.setattr(service.rules, "get_action", lambda system_id, action_id: action)

    result = service.execute(
        actor_id=actor_id,
        action_id="roll.intent",
        user_id=gm_id,
        roll_options={"mode": "advantage", "extraDice": ["1d4", "bad"], "extraModifier": 3},
    )

    assert result.success
    assert [g["notation"] for g in result.groups] == ["2d20kh1", "1d4"]
    assert result.groups[0]["subtotal"] == 18
    assert result.total == 27                                                   


def test_roll_action_schema_transform_visibility(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 10)
    gm_id, _, actor_id = _setup("act-roll-intent-vis")
    service = SheetActionService()
    action = {
        "type": "roll",
        "label": "Visible Check",
        "formula": "1d20 + @sheet.init",
        "visibility": "public",
        "transforms": [],
    }
    monkeypatch.setattr(service.rules, "get_action", lambda system_id, action_id: action)

    result = service.execute(
        actor_id=actor_id,
        action_id="roll.intent",
        user_id=gm_id,
        roll_options={"visibility": "gm"},
    )

    assert result.success
    assert result.visibility == "gm"


def test_roll_action_result_includes_metadata(db, monkeypatch):
    rolls = iter([2, 18, 4])
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: next(rolls))
    gm_id, _, actor_id = _setup("act-roll-metadata")
    service = SheetActionService()
    action = {
        "type": "roll",
        "label": "Generic Check",
        "formula": "1d20 + @sheet.init",
        "visibility": "public",
        "chatCard": "generic-check-card",
        "rollToast": "generic-check-toast",
        "dialog": {"enabled": True, "intent": "check", "fields": []},
        "transforms": [
            {"when": "input.mode == 'advantage'", "replaceFirstDie": {"from": "1d20", "to": "2d20kh1"}},
            {"when": "input.extraModifier != 0", "append": "@input.extraModifier"},
            {"when": "input.extraDice", "appendEach": "@input.extraDice"},
        ],
    }
    monkeypatch.setattr(service.rules, "get_action", lambda system_id, action_id: action)

    result = service.execute(
        actor_id=actor_id,
        action_id="roll.intent.metadata",
        user_id=gm_id,
        roll_options={"mode": "advantage", "extraDice": ["1d4"], "extraModifier": 3, "visibility": "gm"},
    )

    assert result.success
    assert result.base_formula == "1d20 + @sheet.init"
    assert result.final_formula == "2d20kh1 + @sheet.init + 3 + 1d4"
    assert result.intent == "check"
    assert result.chat_card == "generic-check-card"
    assert result.roll_toast == "generic-check-toast"
    assert result.metadata["actionId"] == "roll.intent.metadata"
    assert result.metadata["actorId"] == actor_id
    assert result.metadata["source"] == {"kind": "actor", "actorId": actor_id}
    assert result.metadata["formula"] == {
        "base": "1d20 + @sheet.init",
        "final": "2d20kh1 + @sheet.init + 3 + 1d4",
        "resolved": "2d20kh1 + 2 + 3 + 1d4",
        "display": "2d20kh1 + 1d4 + 5",
    }
    assert "@sheet" not in result.metadata["formula"]["display"]
    assert result.metadata["rollInput"]["mode"] == "advantage"
    assert result.metadata["rollInput"]["visibility"] == "gm"
    assert result.metadata["presentation"] == {
        "chatCard": "generic-check-card",
        "rollToast": "generic-check-toast",
    }
    assert result.metadata["visibility"] == "gm"
