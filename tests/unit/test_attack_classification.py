from app.engine.sheets.sheet_action_service import (
    _attack_classification,
    _first_action_restriction,
    _roll_targets,
    _unlinked_target_sheet,
)


ATTACK = {"chatCard": "attack", "dialog": {"intent": "check"}}


def test_attack_classification_infers_melee_ranged_and_spell() -> None:
    assert _attack_classification(ATTACK, {"type": "weapon", "data": {"range": ""}}) == "melee"
    assert _attack_classification(ATTACK, {"type": "weapon", "data": {"range": "12/24/48"}}) == "ranged"
    assert _attack_classification(ATTACK, {"type": "power", "data": {"range": "Smarts"}}) == "spell"


def test_explicit_mode_overrides_item_inference() -> None:
    thrown_weapon = {"type": "weapon", "data": {"range": "3/6/12"}}
    assert _attack_classification(ATTACK, thrown_weapon, {"attackMode": "melee"}) == "melee"
    assert _attack_classification({**ATTACK, "attackClass": "spell"}, thrown_weapon) == "spell"


def test_item_metadata_and_tags_can_classify_without_core_changes() -> None:
    assert _attack_classification(ATTACK, {"type": "weapon", "data": {"attackType": "spell"}}) == "spell"
    assert _attack_classification(ATTACK, {"type": "feature", "data": {"tags": ["magic"]}}) == "spell"


def test_roll_targets_publish_generic_and_specialized_attack_targets() -> None:
    ranged = _roll_targets("roll.attack", ATTACK, {"type": "weapon", "data": {"range": "10/20/40"}})
    assert {"roll.any", "roll.attack", "roll.attack.ranged"}.issubset(ranged)
    assert "roll.attack.melee" not in ranged


def test_ranged_attack_can_publish_target_proximity() -> None:
    item = {"type": "weapon", "data": {"range": "10/20/40"}}
    distant = _roll_targets("roll.attack", ATTACK, item, {"targetDistance": "distant"})
    assert "roll.attack.ranged.distant" in distant
    assert "roll.attack.ranged.close" not in distant


def test_unknown_explicit_mode_falls_back_to_safe_inference() -> None:
    item = {"type": "weapon", "data": {"range": ""}}
    assert _attack_classification(ATTACK, item, {"attackMode": "laser"}) == "melee"


def test_unlinked_target_uses_its_instance_effects_not_the_base_actor() -> None:
    instance = {"effects": [{"id": "condition:vulnerable"}]}
    token = {
        "actor_link_mode": "unlinked",
        "overrides": {"_actor_instance": {"data": instance}},
    }
    resolved = _unlinked_target_sheet(token)
    assert resolved == instance
    assert resolved is not instance


def test_linked_target_does_not_expose_instance_overrides() -> None:
    token = {
        "actor_link_mode": "linked",
        "overrides": {"_actor_instance": {"data": {"conditions": {"vulnerable": True}}}},
    }
    assert _unlinked_target_sheet(token) is None


def test_skill_roll_publishes_its_linked_attribute_target() -> None:
    targets = _roll_targets(
        "roll.skill",
        {"dialog": {"intent": "check"}},
        {"type": "skill", "data": {"attribute": "agility"}},
    )
    assert "action.roll.skill.attribute.agility" in targets


def test_action_restriction_is_resolved_from_active_effects() -> None:
    sheet = {
        "effects": [{
            "id": "condition:bound",
            "name": "Preso",
            "data": {"restrictions": [{"target": "action.roll.attack"}]},
        }]
    }
    blocked = _first_action_restriction(sheet, {"roll.attack", "action.roll.attack.extra"})
    assert blocked and blocked["effectId"] == "condition:bound"
    assert _first_action_restriction(sheet, {"action.roll.trait.smarts"}) is None


def test_damage_roll_can_publish_area_classification() -> None:
    targets = _roll_targets(
        "roll.damage",
        {"chatCard": "damage", "dialog": {"intent": "damage"}},
        None,
        {"damageMode": "area"},
    )
    assert {"roll.damage", "roll.damage.area"}.issubset(targets)
