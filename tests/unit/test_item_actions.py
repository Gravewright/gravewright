"""O que um item consegue fazer sem o sistema escrever código.

Duas coisas que faltavam: uma transformação de rolagem que consulta o próprio
item (o dano soma a Força porque a *arma* soma, não porque alguém marcou a
caixinha naquele golpe), e uma ação que leva à mesa o que não tem dado nenhum.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.engine.sheets.sheet_action_service import (
    SheetActionService,
    _apply_roll_transforms,
    _condition_matches,
    _target_token_is_eligible,
)
from app.engine.sheets.sheet_item_service import (
    _actor_has_resource,
    _actor_resource_cost,
    _find_linked_skill,
    _item_has_resource,
    _item_resource_cost,
    _item_resource_selection_valid,
)


ESPADA = {
    "id": "itm_1",
    "name": "Espada longa",
    "data": {"damage": "acing(6)", "addStrength": True, "summary": "Corta."},
}
PISTOLA = {
    "id": "itm_2",
    "name": "Pistola",
    "data": {"damage": "acing(6) + 1", "addStrength": False},
}

DAMAGE_ACTION = {
    "type": "roll",
    "formula": "@item.data.damage",
    "transforms": [
        {
            "when": "item.data.addStrength",
            "append": "acing(@sheet.attributes.strength.sides)",
        },
        {"when": "input.raise", "append": "acing(6)"},
    ],
}


# --- a condição enxerga o item ---------------------------------------------


def test_a_condition_can_read_the_item():
    scope = {"input": {}, "item": ESPADA}
    assert _condition_matches("item.data.addStrength", scope) is True
    assert _condition_matches("item.data.addStrength", {"input": {}, "item": PISTOLA}) is False


def test_a_condition_still_reads_the_dialog():
    scope = {"input": {"raise": True, "situational": "-2"}, "item": {}}
    assert _condition_matches("input.raise", scope) is True
    assert _condition_matches("input.situational == '-2'", scope) is True
    assert _condition_matches("input.situational == '2'", scope) is False


def test_sheet_conditions_are_available_to_safe_transform_predicates():
    scope = {"input": {"benefit": "bonus"}, "item": {}, "sheet": {"conditions": {"aiming": True}}}
    assert _condition_matches("sheet.conditions.aiming", scope) is True
    assert _condition_matches("sheet.conditions.aiming && input.benefit == 'bonus'", scope) is True


def test_roll_transform_requires_the_declared_sheet_condition() -> None:
    action = {
        "transforms": [{
            "when": "sheet.conditions.aiming && input.benefit == 'bonus'",
            "append": 2,
        }]
    }
    assert _apply_roll_transforms(
        "acing(8)", action, {"benefit": "bonus"}, None, {"conditions": {"aiming": True}}
    ) == "acing(8) + 2"
    assert _apply_roll_transforms(
        "acing(8)", action, {"benefit": "bonus"}, None, {"conditions": {"aiming": False}}
    ) == "acing(8)"


def test_an_unknown_root_matches_nothing():
    """A linguagem é fechada de propósito: um `when` que aponta para lugar
    nenhum não pode virar 'sempre verdadeiro'."""
    assert _condition_matches("world.weather", {"input": {}, "item": {}, "sheet": {}}) is False
    assert _condition_matches("random junk", {"input": {}, "item": {}}) is False


# --- o dano soma a Força quando a arma soma ---------------------------------


def test_a_melee_weapon_adds_the_wielders_strength():
    out = _apply_roll_transforms("acing(6)", DAMAGE_ACTION, {}, ESPADA)
    assert out == "acing(6) + acing(@sheet.attributes.strength.sides)"


def test_a_ranged_weapon_does_not():
    assert _apply_roll_transforms("acing(6) + 1", DAMAGE_ACTION, {}, PISTOLA) == "acing(6) + 1"


def test_the_weapon_is_read_even_with_no_dialog_answers():
    """O dano de Força é da arma, então vale mesmo quando a rolagem sai direto,
    sem ninguém abrir o diálogo."""
    assert "strength" in _apply_roll_transforms("acing(6)", DAMAGE_ACTION, None, ESPADA)


def test_item_and_dialog_stack():
    out = _apply_roll_transforms("acing(6)", DAMAGE_ACTION, {"raise": True}, ESPADA)
    assert out == "acing(6) + acing(@sheet.attributes.strength.sides) + acing(6)"


def test_an_action_with_no_transforms_is_untouched():
    assert _apply_roll_transforms("acing(6)", {"type": "roll"}, {"raise": True}, ESPADA) == "acing(6)"


def test_a_roll_without_a_target_does_not_require_target_sheet_state(monkeypatch):
    """Most rolls have no target; incoming effects must remain optional."""
    service = SheetActionService.__new__(SheetActionService)
    monkeypatch.setattr(
        "app.engine.sheets.sheet_action_service.evaluate",
        lambda *_args, **_kwargs: type(
            "Roll", (), {"groups": [], "modifier": 0, "int_total": 4}
        )(),
    )

    result = service._do_roll(
        {"id": "a1", "name": "Aria", "campaign_id": "c1", "system_id": "sw"},
        {"type": "roll", "formula": "1d6", "label": "Ataque"},
        {"core": {"name": "Aria"}, "sheet": {}, "item": ESPADA},
        {"input": {}, "drop": {}},
        {},
        action_id="roll.attack",
        item=ESPADA,
    )

    assert result.success is True
    assert result.total == 4


def test_attack_pool_rolls_rof_trait_dice_and_wild_die_replaces_only_one(monkeypatch):
    service = SheetActionService.__new__(SheetActionService)
    totals = iter([3, 8, 4, 10])

    def fake_evaluate(*_args, **_kwargs):
        total = next(totals)
        return type("Roll", (), {
            "groups": [{"notation": "1d8!", "results": [total], "subtotal": total}],
            "modifier": 0,
            "int_total": total,
        })()

    monkeypatch.setattr("app.engine.sheets.sheet_action_service.evaluate", fake_evaluate)
    result = service._do_roll(
        {"id": "a1", "name": "Aria", "campaign_id": "c1", "system_id": "sw"},
        {
            "type": "roll", "formula": "acing(8)", "label": "Ataque",
            "pool": {
                "countInput": "rateOfFire", "wildFormula": "acing(6)",
                "target": 4, "step": 4,
            },
        },
        {"core": {"name": "Aria"}, "sheet": {}, "item": PISTOLA},
        {"input": {}, "drop": {}}, {}, action_id="roll.attack", item=PISTOLA,
        roll_options={"rateOfFire": "3"},
    )

    pool = result.metadata["pool"]
    assert pool["trait"] == [3, 8, 4]
    assert pool["wild"] == 10
    assert [entry["total"] for entry in pool["kept"]] == [10, 8, 4]
    assert pool["hits"] == 3
    assert pool["raises"] == 2
    assert result.total == 10


def test_pool_target_allocations_are_authoritative_and_scene_scoped():
    service = SheetActionService.__new__(SheetActionService)
    service.scenes = type("Scenes", (), {"get_active_scene": lambda _self, _campaign: {"id": "s1"}})()
    tokens = {
        "t1": {"id": "t1", "scene_id": "s1", "actor_id": "enemy1", "name": "Guarda", "hidden": False},
        "gm": {"id": "gm", "scene_id": "s1", "actor_id": "enemy2", "name": "Segredo", "hidden": True},
    }
    service.tokens = type("Tokens", (), {"get_by_id": lambda _self, token_id: tokens.get(token_id)})()
    action = {"pool": {"countInput": "rateOfFire"}}
    actor = {"campaign_id": "c1"}

    valid = service._pool_target_allocations(
        actor=actor, action=action,
        roll_options={"rateOfFire": "2", "targetAllocations": [{"targetTokenId": "t1", "amount": 2}]},
    )
    assert valid == [{
        "targetTokenId": "t1", "targetActorId": "enemy1",
        "targetName": "Guarda", "amount": 2,
    }]
    assert service._pool_target_allocations(
        actor=actor, action=action,
        roll_options={"rateOfFire": "2", "targetAllocations": [{"targetTokenId": "gm", "amount": 2}]},
    ) is None
    assert service._pool_target_allocations(
        actor=actor, action=action,
        roll_options={"rateOfFire": "2", "targetAllocations": [{"targetTokenId": "t1", "amount": 1}]},
    ) is None


def test_roll_intent_can_route_an_item_action_without_exposing_internal_http_to_packages():
    sdk = Path(__file__).resolve().parents[2].joinpath(
        "static/js/sdk/gravewright-sdk.js"
    ).read_text(encoding="utf-8")
    assert 'itemInstanceId ? "/game/actor/item/action" : "/game/actor/action"' in sdk
    assert "item_instance_id: itemInstanceId || undefined" in sdk


def test_only_game_layer_tokens_from_the_active_scene_are_targetable():
    active = {"id": "scene-current"}
    assert _target_token_is_eligible(
        {"scene_id": "scene-current", "hidden": False}, active
    )
    assert not _target_token_is_eligible(
        {"scene_id": "scene-other", "hidden": False}, active
    )
    assert not _target_token_is_eligible(
        {"scene_id": "scene-current", "hidden": True}, active
    )


def test_visible_targets_are_not_filtered_by_target_sheet_edit_permission():
    source = Path(__file__).resolve().parents[2].joinpath(
        "static/js/sheets/actors/actor-sheet-actions.js"
    ).read_text(encoding="utf-8")
    target_block = source.split("function damageTargets", 1)[1].split(
        "function buildTargetField", 1
    )[0]
    assert "canEdit" not in target_block


def test_a_weapon_resolves_its_attack_skill_from_the_actor():
    skill = {"id": "s1", "type": "skill", "name": "Lutar", "data": {"die": {"sides": 8}}}
    weapon = {"type": "weapon", "data": {"skill": "lUtAr"}}
    assert _find_linked_skill({"skills": [skill]}, weapon) is skill


def test_a_weapon_with_no_matching_skill_does_not_invent_one():
    weapon = {"type": "weapon", "data": {"skill": "Atirar"}}
    assert _find_linked_skill({"skills": []}, weapon) is None


def test_a_power_uses_the_arcane_skill_configured_on_the_actor():
    skill = {"id": "s1", "type": "skill", "name": "Ocultismo", "data": {"die": {"sides": 10}}}
    power = {"type": "power", "data": {"damage": "explode(6, 6)"}}
    data = {"power": {"skill": "Ocultismo"}, "skills": [skill]}
    assert _find_linked_skill(data, power) is skill


def test_item_resource_uses_the_declared_rate_of_fire_cost_table():
    resource = {
        "input": "rateOfFire", "default": 1,
        "costs": {"1": 1, "2": 5, "3": 10},
    }
    assert _item_resource_cost(resource, {"rateOfFire": "1"}) == 1
    assert _item_resource_cost(resource, {"rateOfFire": "3"}) == 10


def test_rate_of_fire_cannot_exceed_the_weapon_and_ammo_is_checked():
    weapon = {"data": {"rof": 3, "ammo": {"value": 9, "max": 20}}}
    resource = {
        "path": "data.ammo.value", "capacityPath": "data.ammo.max",
        "limitPath": "data.rof", "input": "rateOfFire", "default": 1,
    }
    assert _item_resource_selection_valid(weapon, resource, {"rateOfFire": "3"})
    assert not _item_resource_selection_valid(weapon, resource, {"rateOfFire": "4"})
    assert _item_has_resource(weapon, resource, 5)
    assert not _item_has_resource(weapon, resource, 10)


def test_zero_capacity_keeps_legacy_weapons_ammo_agnostic():
    weapon = {"data": {"ammo": {"value": 0, "max": 0}}}
    resource = {"path": "data.ammo.value", "capacityPath": "data.ammo.max"}
    assert _item_has_resource(weapon, resource, 50)


def test_power_point_cost_is_declared_by_the_power_and_checked_on_the_actor():
    power = {"data": {"powerPoints": 3}}
    resource = {"path": "power.points.value", "costPath": "data.powerPoints"}
    assert _actor_resource_cost(power, resource) == 3
    assert _actor_resource_cost(
        power, {**resource, "extraCostInput": "additionalPowerPoints"},
        {"additionalPowerPoints": 2},
    ) == 5
    assert _actor_has_resource({"power": {"points": {"value": 3}}}, resource, 3)
    assert not _actor_has_resource({"power": {"points": {"value": 2}}}, resource, 3)


def test_savage_power_actions_declare_authoritative_power_point_consumption():
    actions = json.loads(
        Path(__file__).resolve().parents[2].joinpath(
            "data/packages/rulesets/savage-worlds/rules/actions.gw.json"
        ).read_text(encoding="utf-8")
    )["actions"]
    expected = {
        "path": "power.points.value", "costPath": "data.powerPoints",
        "extraCostInput": "additionalPowerPoints",
    }
    assert actions["roll.power"]["actorResource"] == expected
    assert actions["roll.power.extra"]["actorResource"] == expected


# --- levar à mesa o que não rola --------------------------------------------


def _chat(action: dict, item: dict):
    service = SheetActionService.__new__(SheetActionService)
    return service._do_chat(
        {"id": "a1", "name": "Aria", "campaign_id": "c1", "system_id": "sw"},
        action,
        {"core": {"name": "Aria"}, "sheet": {}, "item": item},
        {"input": {}, "drop": {}},
        action_id="item.describe",
        item=item,
    )


def test_a_chat_action_carries_the_item_to_the_table():
    result = _chat({"type": "chat", "label": "@item.name", "chatCard": "item"}, ESPADA)

    assert result.success and result.action_type == "chat"
    assert result.label == "Espada longa", "o cartão é titulado pelo item"
    assert result.chat_card == "item"
    assert result.source == {"kind": "actor_item_instance", "itemInstanceId": "itm_1"}


def test_a_chat_action_has_no_score():
    """Sem dado não há total. Zero seria um número inventado, e o cartão o
    imprimiria em destaque como se fosse resultado."""
    result = _chat({"type": "chat", "label": "@item.name", "chatCard": "item"}, ESPADA)

    assert result.total is None
    assert result.groups == []
    assert result.expression == ""


def test_the_item_reaches_the_presentation_context():
    result = _chat({"type": "chat", "label": "@item.name", "chatCard": "item"}, ESPADA)
    assert result.metadata["item"]["data"]["summary"] == "Corta."
    assert result.metadata["presentation"]["chatCard"] == "item"
