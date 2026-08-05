from __future__ import annotations

from app.engine.tokens.actor_token_projector import _compact_buff_debuff


def test_compact_effects_keeps_hud_details_for_buff_debuff_and_condition():
    effects = _compact_buff_debuff(
        {
            "effects": [
                {
                    "id": "bless",
                    "name": "Bless",
                    "enabled": True,
                    "data": {
                        "category": "buff",
                        "description": "Adiciona 1d4 em ataques e salvaguardas.",
                        "duration": {"type": "rounds", "remaining": 4},
                        "concentration": True,
                        "modifiers": [{"target": "roll.attack", "operation": "add_dice", "value": "1d4"}],
                    },
                },
                {
                    "id": "burning",
                    "name": "Em Chamas",
                    "data": {
                        "category": "condition",
                        "description": "Sofre dano de fogo no início da rodada.",
                    },
                },
                {"id": "stance", "name": "Postura", "data": {"category": "stance"}},
                {"id": "off", "name": "Desligado", "enabled": False, "data": {"category": "debuff"}},
            ]
        }
    )

    assert [effect["id"] for effect in effects] == ["bless", "burning"]
    assert effects[0]["description"] == "Adiciona 1d4 em ataques e salvaguardas."
    assert effects[0]["duration"] == {"type": "rounds", "remaining": 4}
    assert effects[0]["concentration"] is True
    assert effects[0]["modifiers"] == [
        {"target": "roll.attack", "operation": "add_dice", "value": "1d4"}
    ]
    assert effects[1]["category"] == "condition"
