from __future__ import annotations

from app.engine.effects.active_effects import (
    active_effects,
    adjust_incoming_damage,
    all_effects,
    apply_resource_delta,
    apply_stat_modifiers,
    effect_modifiers,
    granted_effects,
    periodic_modifiers,
    resolve_resource_target,
)


def _dmg_adj(operation, damage_type="", value=None):
    target = f"damage.received.{damage_type}" if damage_type else "damage.received"
    mod = {"target": target, "operation": operation}
    if value is not None:
        mod["value"] = value
    return {"id": f"adj-{operation}", "enabled": True, "data": {"modifiers": [mod]}}


def _dot_sheet(operation: str, value, *, enabled=True, condition=None, hp=None):
    data: dict = {"modifiers": [{"target": "damage.self", "operation": operation, "value": value}]}
    if condition is not None:
        data["condition"] = condition
    sheet: dict = {"effects": [{"id": "e1", "name": "Tick", "enabled": enabled, "data": data}]}
    if hp is not None:
        sheet["hp"] = hp
    return sheet


def _equipped_item(target: str, operation: str, value, *, equipped=None):
    entry: dict = {
        "id": "i1",
        "name": "Item",
        "data": {"modifiers": [{"target": target, "operation": operation, "value": value}]},
    }
    if equipped is not None:
        entry["equipped"] = equipped
    return entry


                                                                                


def test_equipped_item_grants_effect_and_unequipped_does_not():
    equipped = {"inventory": [_equipped_item("sheet.ac", "add", 2, equipped=True)]}
    unequipped = {"inventory": [_equipped_item("sheet.ac", "add", 2, equipped=False)]}
    assert len(granted_effects(equipped)) == 1
    assert granted_effects(unequipped) == []


def test_item_without_flag_is_always_on_and_no_modifiers_ignored():
    always_on = {"features": [_equipped_item("sheet.ac", "add", 1)]}
    assert len(granted_effects(always_on)) == 1

    plain = {"inventory": [{"id": "x", "name": "Rope", "data": {}}]}
    assert granted_effects(plain) == []


def test_all_effects_merges_manual_and_granted():
    sheet = {
        "effects": [
            {
                "id": "e1",
                "enabled": True,
                "data": {"modifiers": [{"target": "sheet.ac", "operation": "add", "value": 1}]},
            }
        ],
        "inventory": [_equipped_item("sheet.ac", "add", 2, equipped=True)],
    }
    assert len(all_effects(sheet)) == 2


def test_manual_effect_can_be_disabled_inside_snapshot_data():
    sheet = {
        "effects": [
            {
                "id": "e1",
                "data": {
                    "enabled": False,
                    "modifiers": [{"target": "sheet.ac", "operation": "add", "value": 2}],
                },
            }
        ]
    }
    assert active_effects(sheet) == []


                                                                                


def test_condition_gates_manual_effect():
    def sheet(hp):
        return {
            "hp": {"value": hp},
            "ac": 10,
            "effects": [
                {
                    "id": "e1",
                    "enabled": True,
                    "data": {
                        "modifiers": [{"target": "sheet.ac", "operation": "add", "value": 5}],
                        "condition": "@sheet.hp.value < 5",
                    },
                }
            ],
        }

    assert apply_stat_modifiers(sheet(10))["ac"] == 10                              
    assert apply_stat_modifiers(sheet(3))["ac"] == 15                       


                                                                                


def test_apply_stat_modifiers_uses_item_grant():
    sheet = {"ac": 10, "inventory": [_equipped_item("sheet.ac", "add", 2, equipped=True)]}
    assert apply_stat_modifiers(sheet)["ac"] == 12


def test_effect_modifiers_picks_up_equipped_weapon_roll_bonus():
    sheet = {"weapons": [_equipped_item("roll.attack", "add_dice", "1d4", equipped=True)]}
    _mods, applied = effect_modifiers(sheet, {"roll.attack"})
    assert len(applied) == 1
    assert applied[0]["operation"] == "add_dice"
    assert applied[0]["value"] == "1d4"


                                                                                


def test_periodic_modifiers_rolls_damage_and_heal():
    dmg = periodic_modifiers(_dot_sheet("damage_over_time", 4))
    assert len(dmg) == 1
    assert dmg[0]["amount"] == 4 and dmg[0]["delta"] == -4
    assert dmg[0]["operation"] == "damage_over_time"

    heal = periodic_modifiers(_dot_sheet("heal_over_time", 3))
    assert heal[0]["amount"] == 3 and heal[0]["delta"] == 3


def test_periodic_modifiers_rolls_dice_value(monkeypatch):
    import app.engine.rules.formula_engine as formula_engine

    monkeypatch.setattr(formula_engine.random, "randint", lambda a, b: 5)
    out = periodic_modifiers(_dot_sheet("damage_over_time", "1d6"))
    assert out[0]["amount"] == 5 and out[0]["delta"] == -5


def test_periodic_modifiers_respects_disabled_and_condition():
    assert periodic_modifiers(_dot_sheet("damage_over_time", 4, enabled=False)) == []
    gated = _dot_sheet("damage_over_time", 4, condition="@sheet.hp.value < 5", hp={"value": 10})
    assert periodic_modifiers(gated) == []                             


def test_periodic_modifiers_ignores_non_periodic_ops():
    assert periodic_modifiers(_dot_sheet("add", 4)) == []


def test_periodic_modifiers_carry_target():
    assert periodic_modifiers(_dot_sheet("damage_over_time", 4))[0]["target"] == "damage.self"


                                                                                

_HP_RESOURCES = {"hp": {"path": "sheet.hp.value", "maxPath": "sheet.hp.max", "min": 0}}


def test_resolve_explicit_sheet_path():
    assert resolve_resource_target("sheet.vitality.value", {}) == ("vitality.value", "", 0)


def test_resolve_named_and_primary_resource_from_config():
    assert resolve_resource_target("resource.hp", _HP_RESOURCES) == ("hp.value", "hp.max", 0)
                                                                         
    assert resolve_resource_target("damage.self", _HP_RESOURCES) == ("hp.value", "hp.max", 0)


def test_resolve_falls_back_to_hp_without_config():
    assert resolve_resource_target("heal.self", {}) == ("hp.value", "hp.max", 0)


def test_resolve_unknown_named_resource_is_none():
    assert resolve_resource_target("resource.mana", _HP_RESOURCES) is None


def test_apply_resource_delta_clamps_floor_and_sibling_max():
                                                                            
    sheet = {"vitality": {"value": 18, "max": 20}}
    assert apply_resource_delta(sheet, "vitality.value", "", 0, 10) == 20
    assert sheet["vitality"]["value"] == 20

    sheet = {"vitality": {"value": 5}}
    assert apply_resource_delta(sheet, "vitality.value", "", 0, -8) == 0         
    assert apply_resource_delta({}, "", "", 0, -5) is None                      


def test_apply_resource_delta_explicit_max_path():
    sheet = {"hp": {"value": 9, "max": 12}}
    assert apply_resource_delta(sheet, "hp.value", "hp.max", 0, 99) == 12


                                                                                


def test_adjust_incoming_damage_resistance_and_vulnerability():
    resist = {"effects": [_dmg_adj("resistance", "fire")]}
    assert adjust_incoming_damage(resist, 7, "fire") == 3                      
    assert adjust_incoming_damage(resist, 7, "cold") == 7                          
    vuln = {"effects": [_dmg_adj("vulnerability", "fire")]}
    assert adjust_incoming_damage(vuln, 5, "fire") == 10


def test_adjust_incoming_damage_immunity_and_reduce():
    immune = {"effects": [_dmg_adj("immunity", "fire")]}
    assert adjust_incoming_damage(immune, 99, "fire") == 0
    reduce = {"effects": [_dmg_adj("reduce", "", 3)]}                          
    assert adjust_incoming_damage(reduce, 5) == 2
    assert adjust_incoming_damage(reduce, 2) == 0                


def test_periodic_damage_routes_through_resistance():
    sheet = {
        "effects": [
            {
                "id": "burn",
                "enabled": True,
                "data": {
                    "modifiers": [
                        {"target": "damage.self", "operation": "damage_over_time", "value": 8, "damageType": "fire"}
                    ]
                },
            },
            _dmg_adj("resistance", "fire"),
        ]
    }
    entry = next(e for e in periodic_modifiers(sheet) if e["operation"] == "damage_over_time")
    assert entry["rawAmount"] == 8
    assert entry["amount"] == 4 and entry["delta"] == -4                          


def test_periodic_damage_immunity_yields_no_entry():
    sheet = {
        "effects": [
            {
                "id": "burn",
                "enabled": True,
                "data": {
                    "modifiers": [
                        {"target": "damage.self", "operation": "damage_over_time", "value": 6, "damageType": "fire"}
                    ]
                },
            },
            _dmg_adj("immunity", "fire"),
        ]
    }
    assert periodic_modifiers(sheet) == []
