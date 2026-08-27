"""Uma condição marcada tem de virar um efeito de verdade.

É o que a torna visível no HUD do tabuleiro e o que faz os seus modificadores
passarem pelo mesmo motor que já atende os efeitos soltos numa ficha.
"""

from __future__ import annotations

from app.engine.effects.active_effects import (
    apply_roll_modifiers,
    apply_stat_modifiers,
    effect_modifiers,
)
from app.engine.rules.condition_effects import sync_condition_effects
from app.engine.tokens.actor_token_projector import _compact_buff_debuff


DECLARED = [
    {
        "id": "distracted",
        "labelKey": "sw.cond.distracted",
        "kind": "negative",
        "category": "condition",
        "modifiers": [
            {
                "id": "distracted-trait",
                "target": "roll.check",
                "operation": "subtract",
                "value": 2,
                "labelKey": "sw.cond.distracted",
            }
        ],
    },
    {
        "id": "defending",
        "labelKey": "sw.cond.defending",
        "kind": "positive",
        "category": "condition",
        "modifiers": [
            {
                "id": "defending-parry",
                "target": "sheet.stats.parry.value",
                "operation": "add",
                "value": 4,
                "labelKey": "sw.cond.defending",
            }
        ],
    },
    {"id": "shaken", "labelKey": "sw.cond.shaken", "kind": "negative", "category": "condition"},
]

LABELS = {
    "sw.cond.distracted": "Distraído",
    "sw.cond.defending": "Defendendo",
    "sw.cond.shaken": "Abalado",
}


def _sheet(**flags) -> dict:
    return {"conditions": dict(flags), "stats": {"parry": {"value": 6}}}


def test_a_ticked_flag_becomes_an_effect_instance():
    data = _sheet(shaken=True)
    assert sync_condition_effects(data, DECLARED, LABELS) is True

    assert [e["id"] for e in data["effects"]] == ["condition:shaken"]
    assert data["effects"][0]["name"] == "Abalado", "o HUD mostra o rótulo traduzido"
    assert data["effects"][0]["data"]["category"] == "condition"
    assert data["effects"][0]["data"]["restrictions"] == []


def test_condition_restrictions_are_projected_into_the_effect():
    declared = [{
        "id": "bound",
        "labelKey": "sw.cond.bound",
        "kind": "negative",
        "category": "condition",
        "restrictions": [{"target": "token.movement"}],
    }]
    data = {"conditions": {"bound": True}}
    sync_condition_effects(data, declared)
    assert data["effects"][0]["data"]["restrictions"] == [{"target": "token.movement"}]


def test_unticking_takes_the_effect_away():
    data = _sheet(shaken=True)
    sync_condition_effects(data, DECLARED, LABELS)
    data["conditions"]["shaken"] = False

    assert sync_condition_effects(data, DECLARED, LABELS) is True
    assert data["effects"] == []


def test_an_effect_nobody_declared_is_never_touched():
    """Um efeito solto na ficha: arrastado, escrito pelo mestre: não é nosso.
    Reconstruir as condições não pode varrê-lo junto."""
    dropped = {"id": "bless", "name": "Bênção", "data": {"category": "buff", "modifiers": []}}
    data = _sheet(shaken=True)
    data["effects"] = [dropped]

    sync_condition_effects(data, DECLARED, LABELS)
    assert dropped in data["effects"]
    assert len(data["effects"]) == 2


def test_syncing_twice_changes_nothing_the_second_time():
    """Toda gravação de ficha passa por aqui. Se um estado igual produzisse uma
    lista nova, o HUD piscaria a cada campo editado."""
    data = _sheet(distracted=True)
    assert sync_condition_effects(data, DECLARED, LABELS) is True
    assert sync_condition_effects(data, DECLARED, LABELS) is False


def test_the_declared_order_survives_the_order_they_were_ticked():
    data = _sheet(defending=True)
    sync_condition_effects(data, DECLARED, LABELS)
    data["conditions"]["distracted"] = True
    sync_condition_effects(data, DECLARED, LABELS)

    assert [e["id"] for e in data["effects"]] == ["condition:distracted", "condition:defending"]


def test_the_board_hud_picks_the_condition_up():
    """O HUD lê `sheet.effects` pelo mesmo compactador que serve o D&D."""
    data = _sheet(distracted=True)
    sync_condition_effects(data, DECLARED, LABELS)

    shown = _compact_buff_debuff(data)
    assert [e["name"] for e in shown] == ["Distraído"]
    assert shown[0]["category"] == "condition"
    assert shown[0]["modifiers"][0]["label"] == "Distraído", "o tooltip diz o que ela custa"


def test_a_condition_that_costs_a_roll_reaches_the_formula():
    data = _sheet(distracted=True)
    sync_condition_effects(data, DECLARED, LABELS)

    modifiers, applied = effect_modifiers(data, {"roll.any", "roll.check"})
    assert applied, "o modificador tem de casar com o alvo da ação"
    assert apply_roll_modifiers("acing(8)", modifiers) == "acing(8) - 2"


def test_a_condition_that_costs_a_stat_reaches_the_sheet():
    data = _sheet(defending=True)
    sync_condition_effects(data, DECLARED, LABELS)

    assert apply_stat_modifiers(data)["stats"]["parry"]["value"] == 10
    assert data["stats"]["parry"]["value"] == 6, "a ficha guardada não é reescrita"


def test_a_condition_without_a_number_costs_nothing():
    data = _sheet(shaken=True)
    sync_condition_effects(data, DECLARED, LABELS)

    _, applied = effect_modifiers(data, {"roll.any", "roll.check"})
    assert applied == []
    assert apply_stat_modifiers(data)["stats"]["parry"]["value"] == 6


def test_a_system_with_no_conditions_leaves_the_sheet_alone():
    data = _sheet(shaken=True)
    assert sync_condition_effects(data, [], LABELS) is False
    assert "effects" not in data
