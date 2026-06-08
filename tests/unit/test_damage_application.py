from __future__ import annotations

import app.engine.rules.formula_engine as formula_engine
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.sheet_action_service import SheetActionService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.systems.system_install_service import SystemInstallService
from app.engine.tokens.token_instance_sheet_service import INSTANCE_KEY
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import seed_campaign, seed_scene, seed_user


_SWORD = {"id": "w1", "name": "Espada", "data": {"damage": "1d6", "damage_type": "fire"}}


def _campaign_with_actors(prefix: str) -> tuple[str, str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-dmg-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    systems = SystemInstallService()
    assert systems.install(package_id="dnd5e", user_id=gm_id).success
    assert systems.enable(package_id="dnd5e").success
    actors = ActorService()
    attacker = actors.create_actor(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e", actor_type="character", name="Atacante"
    )
    target = actors.create_actor(
        campaign_id=campaign_id, user_id=gm_id, system_id="dnd5e", actor_type="character", name="Alvo"
    )
    assert attacker.success and target.success
    return gm_id, campaign_id, attacker.actor_id, target.actor_id


def _set_target_hp(actor_id: str, gm_id: str, value: int = 20, effects: list | None = None) -> None:
    patch = {"hp": {"value": value, "max": value}}
    if effects is not None:
        patch["effects"] = effects
    assert SheetDataService().patch_data(actor_id=actor_id, user_id=gm_id, patch=patch).success


def test_roll_damage_applies_to_target(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)            
    gm_id, _, attacker, target = _campaign_with_actors("hit")
    _set_target_hp(target, gm_id, 20)

    result = SheetActionService().execute(
        actor_id=attacker, user_id=gm_id, action_id="weapon.damage",
        item=_SWORD, target_actor_id=target,
    )

    assert result.success
    assert result.total == 4
    assert result.applied is not None
    assert result.applied["targetActorId"] == target
    assert result.applied["amount"] == 4
    assert result.applied["valueAfter"] == 16
    assert result.applied["damageType"] == "fire"

    data = SheetDataService().get_data(actor_id=target, user_id=gm_id).data
    assert data["hp"]["value"] == 16


def test_roll_damage_respects_target_resistance(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 6)            
    gm_id, _, attacker, target = _campaign_with_actors("resist")
    _set_target_hp(target, gm_id, 20, effects=[
        {
            "id": "fire-resist",
            "enabled": True,
            "data": {"modifiers": [{"target": "damage.received.fire", "operation": "resistance"}]},
        }
    ])

    result = SheetActionService().execute(
        actor_id=attacker, user_id=gm_id, action_id="weapon.damage",
        item=_SWORD, target_actor_id=target,
    )

    assert result.success
    assert result.applied["rawAmount"] == 6
    assert result.applied["amount"] == 3                          
    assert result.applied["valueAfter"] == 17          
    assert SheetDataService().get_data(actor_id=target, user_id=gm_id).data["hp"]["value"] == 17


def test_roll_damage_without_target_only_rolls(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)
    gm_id, _, attacker, target = _campaign_with_actors("notarget")
    _set_target_hp(target, gm_id, 20)

    result = SheetActionService().execute(
        actor_id=attacker, user_id=gm_id, action_id="weapon.damage", item=_SWORD,
    )

    assert result.success
    assert result.total == 4
    assert result.applied is None                                    
    assert SheetDataService().get_data(actor_id=target, user_id=gm_id).data["hp"]["value"] == 20


def test_cannot_apply_to_target_in_another_campaign(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)
    gm1, _, attacker, _ = _campaign_with_actors("camp1")
    _, _, _, foreign_target = _campaign_with_actors("camp2")

    result = SheetActionService().execute(
        actor_id=attacker, user_id=gm1, action_id="weapon.damage",
        item=_SWORD, target_actor_id=foreign_target,
    )

    assert not result.success
    assert result.error_key == "game.actors.errors.not_found"


async def test_roll_damage_applies_to_target_token_instance_only(db, monkeypatch):
    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 4)
    gm_id, campaign_id, attacker, target = _campaign_with_actors("token-target")
    _set_target_hp(target, gm_id, 20)
    scene = seed_scene(campaign_id)

    created = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[target, target],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )
    assert created.success
    first_token_id = created.tokens[0]["token_id"]
    second_token_id = created.tokens[1]["token_id"]

    result = SheetActionService().execute(
        actor_id=attacker,
        user_id=gm_id,
        action_id="weapon.damage",
        item=_SWORD,
        target_token_id=first_token_id,
    )

    assert result.success
    assert result.applied["targetTokenId"] == first_token_id
    assert result.applied["targetActorId"] == target
    assert result.applied["valueAfter"] == 16
    first = TokenRepository().get_by_id(first_token_id)
    second = TokenRepository().get_by_id(second_token_id)
    assert first["overrides"][INSTANCE_KEY]["data"]["hp"]["value"] == 16
    assert second["overrides"][INSTANCE_KEY]["data"]["hp"]["value"] == 20
    assert SheetDataService().get_data(actor_id=target, user_id=gm_id).data["hp"]["value"] == 20
