"""O que um item consegue fazer sem o sistema escrever código.

Duas coisas que faltavam: uma transformação de rolagem que consulta o próprio
item (o dano soma a Força porque a *arma* soma, não porque alguém marcou a
caixinha naquele golpe), e uma ação que leva à mesa o que não tem dado nenhum.
"""

from __future__ import annotations

from app.engine.sheets.sheet_action_service import (
    SheetActionService,
    _apply_roll_transforms,
    _condition_matches,
)
from app.engine.sheets.sheet_item_service import _find_linked_skill


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


def test_an_unknown_root_matches_nothing():
    """A linguagem é fechada de propósito: um `when` que aponta para lugar
    nenhum não pode virar 'sempre verdadeiro'."""
    assert _condition_matches("sheet.wounds.value", {"input": {}, "item": {}}) is False
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


def test_a_weapon_resolves_its_attack_skill_from_the_actor():
    skill = {"id": "s1", "type": "skill", "name": "Lutar", "data": {"die": {"sides": 8}}}
    weapon = {"type": "weapon", "data": {"skill": "lUtAr"}}
    assert _find_linked_skill({"skills": [skill]}, weapon) is skill


def test_a_weapon_with_no_matching_skill_does_not_invent_one():
    weapon = {"type": "weapon", "data": {"skill": "Atirar"}}
    assert _find_linked_skill({"skills": []}, weapon) is None


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
