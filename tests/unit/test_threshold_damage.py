import json
from pathlib import Path

from app.engine.rules.threshold_damage import resolve_threshold_damage


POLICY = {"thresholdPath": "stats.toughness.value", "raiseStep": 4}


def sheet(*, toughness=6, shaken=False, wounds=0, maximum=3):
    return {"stats": {"toughness": {"value": toughness}}, "conditions": {"shaken": shaken, "incapacitated": False}, "wounds": {"value": wounds, "max": maximum}}


def test_damage_below_toughness_has_no_effect():
    data = sheet()
    result = resolve_threshold_damage(data, 5, POLICY, actor_type="character")
    assert not result.shaken and result.wounds == 0


def test_toughness_shakes_and_each_raise_causes_a_wound():
    data = sheet()
    result = resolve_threshold_damage(data, 14, POLICY, actor_type="character")
    assert result.raises == 2 and result.wounds == 2
    assert data["conditions"]["shaken"] and data["wounds"]["value"] == 2


def test_second_shaken_result_becomes_a_wound():
    data = sheet(shaken=True)
    result = resolve_threshold_damage(data, 6, POLICY, actor_type="character")
    assert result.wounds == 1 and data["wounds"]["value"] == 1


def test_extra_is_incapacitated_by_any_wound():
    data = sheet(maximum=1)
    resolve_threshold_damage(data, 10, POLICY, actor_type="extra")
    assert data["conditions"]["incapacitated"] is True


def test_armor_piercing_reduces_only_the_armor_part_of_toughness():
    data = sheet(toughness=8)
    data["stats"]["toughness"]["armor"] = 2
    result = resolve_threshold_damage(data, 7, POLICY, actor_type="character", armor_piercing=1)
    assert result.toughness == 8
    assert result.armor_piercing == 1
    assert result.effective_toughness == 7
    assert result.shaken is True


def test_armor_piercing_cannot_reduce_base_toughness():
    data = sheet(toughness=8)
    data["stats"]["toughness"]["armor"] = 2
    result = resolve_threshold_damage(data, 6, POLICY, actor_type="character", armor_piercing=99)
    assert result.armor_piercing == 2
    assert result.effective_toughness == 6


def test_savage_damage_actions_opt_into_the_declared_policy():
    root = Path(__file__).resolve().parents[2] / "data/packages/rulesets/savage-worlds/rules"
    combat = json.loads((root / "combat.gw.json").read_text(encoding="utf-8"))
    actions = json.loads((root / "actions.gw.json").read_text(encoding="utf-8"))["actions"]
    assert combat["damageResolution"]["mode"] == "threshold-raises"
    assert actions["roll.damage"]["apply"] == {
        "mode": "damage",
        "resolution": "configured",
        "armorPiercing": "@item.data.ap",
    }
