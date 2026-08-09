"""The combat tracker: who is in the order, in what order, and whose turn it is.

The core never interprets an initiative value — the active system decides
whether it is rolled, typed as a number, or typed as free text with the order
arranged by hand. These tests cover all three shapes.
"""

from __future__ import annotations

import pytest

from app.engine.combat.combat_config import CombatConfig, CombatConfigService
from app.engine.combat.combat_service import CombatService
from app.persistence.repositories.actor_repository import ActorRepository
from tests.conftest import seed_campaign, seed_member, seed_user


@pytest.fixture
def table(db):
    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, "player")
    return {"gm": gm, "player": player, "campaign_id": campaign_id}


def make_actor(campaign_id: str, user_id: str, name: str, actor_type: str = "character") -> str:
    return ActorRepository().create(
        campaign_id=campaign_id,
        system_id="valid-ruleset",
        actor_type=actor_type,
        name=name,
        created_by_user_id=user_id,
    )


def names(result) -> list[str]:
    return [combatant["name"] for combatant in result.combatants]


def start_with(table, *actor_names, service=None):
    service = service or CombatService()
    actor_ids = [make_actor(table["campaign_id"], table["gm"], name) for name in actor_names]
    result = service.start(
        campaign_id=table["campaign_id"], user_id=table["gm"], actor_ids=actor_ids
    )
    assert result.success, result.error_key
    return service, result


def use_system(service, **overrides) -> CombatConfig:
    """Pin the service to a system that declares initiative a particular way."""
    config = CombatConfig(system_id="test-system", **overrides)
    service.configs.get_for_system = lambda system_id: config
    return config


def set_order(service, table, values: dict[str, str | None]) -> None:
    """Assign initiative by combatant name."""
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    by_name = {c["name"]: c["id"] for c in state.combatants}
    for name, value in values.items():
        service.set_initiative(
            campaign_id=table["campaign_id"],
            user_id=table["gm"],
            combatant_id=by_name[name],
            value=value,
        )


def test_start_creates_an_active_encounter_at_round_one(table):
    service, result = start_with(table, "Aria")
    assert result.active
    payload = result.state_payload()
    assert payload["round"] == 1
    assert payload["turn"] == 0
    assert names(result) == ["Aria"]


def test_players_cannot_change_the_combat(table):
    service, _ = start_with(table, "Aria")
    result = service.advance_turn(
        campaign_id=table["campaign_id"], user_id=table["player"], delta=1
    )
    assert not result.success
    assert result.error_key == "game.combat.errors.gm_required"


def test_higher_initiative_goes_first_and_unrolled_goes_last(table):
    service, _ = start_with(table, "Aria", "Bran", "Cass")
    set_order(service, table, {"Aria": "12", "Bran": "20", "Cass": None})
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert names(state) == ["Bran", "Aria", "Cass"]


def test_next_turn_walks_the_order_and_rolls_into_the_next_round(table):
    service, _ = start_with(table, "Aria", "Bran")
    set_order(service, table, {"Aria": "20", "Bran": "10"})

    turn_two = service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=1)
    assert turn_two.state_payload()["current_name"] == "Bran"
    assert turn_two.state_payload()["round"] == 1

    wrapped = service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=1)
    assert wrapped.state_payload()["current_name"] == "Aria"
    assert wrapped.state_payload()["round"] == 2


def test_previous_turn_steps_back_into_the_previous_round(table):
    service, _ = start_with(table, "Aria", "Bran")
    set_order(service, table, {"Aria": "20", "Bran": "10"})
    service.advance_round(campaign_id=table["campaign_id"], user_id=table["gm"], delta=1)

    back = service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=-1)
    payload = back.state_payload()
    assert payload["round"] == 1
    assert payload["current_name"] == "Bran"


def test_the_first_round_cannot_be_stepped_before(table):
    service, _ = start_with(table, "Aria", "Bran")
    set_order(service, table, {"Aria": "20", "Bran": "10"})
    back = service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=-1)
    assert back.state_payload()["round"] == 1
    assert back.state_payload()["turn"] == 0


def test_reordering_keeps_the_turn_on_the_same_combatant(table):
    """Editing someone else's initiative must not steal the current turn."""
    service, _ = start_with(table, "Aria", "Bran", "Cass")
    set_order(service, table, {"Aria": "20", "Bran": "15", "Cass": "10"})
    service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=1)
    assert (
        service.get_state(
            campaign_id=table["campaign_id"], user_id=table["gm"]
        ).state_payload()["current_name"]
        == "Bran"
    )

    set_order(service, table, {"Cass": "99"})
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert names(state) == ["Cass", "Aria", "Bran"]
    assert state.state_payload()["current_name"] == "Bran"


def test_removing_the_active_combatant_hands_the_turn_to_the_next(table):
    service, _ = start_with(table, "Aria", "Bran", "Cass")
    set_order(service, table, {"Aria": "20", "Bran": "15", "Cass": "10"})
    service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=1)

    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    bran = next(c["id"] for c in state.combatants if c["name"] == "Bran")
    after = service.remove_combatant(
        campaign_id=table["campaign_id"], user_id=table["gm"], combatant_id=bran
    )
    assert names(after) == ["Aria", "Cass"]
    assert after.state_payload()["current_name"] == "Cass"


def test_the_same_actor_is_only_added_once(table):
    service = CombatService()
    actor_id = make_actor(table["campaign_id"], table["gm"], "Aria")
    service.start(campaign_id=table["campaign_id"], user_id=table["gm"], actor_ids=[actor_id])
    result = service.add_combatants(
        campaign_id=table["campaign_id"], user_id=table["gm"], actor_ids=[actor_id]
    )
    assert names(result) == ["Aria"]


def test_hidden_combatants_are_anonymous_to_players_but_still_in_the_order(table):
    service, _ = start_with(table, "Aria", "Lurker")
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    lurker = next(c["id"] for c in state.combatants if c["name"] == "Lurker")
    service.set_flags(
        campaign_id=table["campaign_id"],
        user_id=table["gm"],
        combatant_id=lurker,
        hidden=True,
    )

    as_player = service.get_state(campaign_id=table["campaign_id"], user_id=table["player"])
    assert sorted(names(as_player)) == ["???", "Aria"]
    as_gm = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert sorted(names(as_gm)) == ["Aria", "Lurker"]


def test_rolling_only_the_missing_ones_leaves_existing_values_alone(table):
    service, _ = start_with(table, "Aria", "Bran")
    use_system(service, input="roll", formula="1d20")
    set_order(service, table, {"Aria": "7", "Bran": None})
    service.roll_initiative(
        campaign_id=table["campaign_id"], user_id=table["gm"], scope="missing"
    )

    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    by_name = {c["name"]: c["initiative"] for c in state.combatants}
    assert by_name["Aria"] == "7"
    assert by_name["Bran"] is not None


def test_rolling_for_everyone_restarts_the_order_from_the_top(table):
    service, _ = start_with(table, "Aria", "Bran")
    use_system(service, input="roll", formula="1d20")
    set_order(service, table, {"Aria": "20", "Bran": "10"})
    service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=1)

    rolled = service.roll_initiative(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert rolled.state_payload()["turn"] == 0
    assert all(c["initiative"] is not None for c in rolled.combatants)


def test_a_system_without_a_roll_refuses_to_roll(table):
    """The core has no die of its own to fall back on."""
    service, _ = start_with(table, "Aria")
    use_system(service, input="number")
    result = service.roll_initiative(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert not result.success
    assert result.error_key == "game.combat.errors.roll_unavailable"


def test_a_sheet_initiative_roll_is_adopted_by_the_tracker(table):
    service = CombatService()
    actor_id = make_actor(table["campaign_id"], table["gm"], "Aria")
    service.start(campaign_id=table["campaign_id"], user_id=table["gm"], actor_ids=[actor_id])

    service.record_initiative_roll(
        campaign_id=table["campaign_id"],
        user_id=table["gm"],
        actor_id=actor_id,
        total=18,
    )
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert state.combatants[0]["initiative"] == "18"


def test_a_sheet_roll_is_ignored_when_initiative_is_not_a_number(table):
    service = CombatService()
    actor_id = make_actor(table["campaign_id"], table["gm"], "Aria")
    service.start(campaign_id=table["campaign_id"], user_id=table["gm"], actor_ids=[actor_id])
    use_system(service, input="text")

    service.record_initiative_roll(
        campaign_id=table["campaign_id"], user_id=table["gm"], actor_id=actor_id, total=18
    )
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert state.combatants[0]["initiative"] is None


def test_a_text_system_keeps_free_text_and_never_reorders_on_it(table):
    """The PDF ruleset case: the GM types whatever the table actually uses."""
    service, _ = start_with(table, "Aria", "Bran", "Cass")
    use_system(service, input="text")
    set_order(service, table, {"Cass": "primeira onda", "Aria": "depois", "Bran": "As de espadas"})

    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    # Insertion order survives: nothing about those strings implies a ranking.
    assert names(state) == ["Aria", "Bran", "Cass"]
    by_name = {c["name"]: c["initiative"] for c in state.combatants}
    assert by_name["Cass"] == "primeira onda"
    assert by_name["Bran"] == "As de espadas"


def test_a_text_system_orders_by_hand(table):
    service, _ = start_with(table, "Aria", "Bran", "Cass")
    use_system(service, input="text")

    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    cass = next(c["id"] for c in state.combatants if c["name"] == "Cass")
    moved = service.move_combatant(
        campaign_id=table["campaign_id"], user_id=table["gm"], combatant_id=cass, delta=-1
    )
    assert names(moved) == ["Aria", "Cass", "Bran"]

    moved = service.move_combatant(
        campaign_id=table["campaign_id"], user_id=table["gm"], combatant_id=cass, delta=-1
    )
    assert names(moved) == ["Cass", "Aria", "Bran"]


def test_a_hand_arranged_value_survives_being_relabelled(table):
    """Typing a new label must not undo the order the GM arranged."""
    service, _ = start_with(table, "Aria", "Bran")
    use_system(service, input="text")
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    bran = next(c["id"] for c in state.combatants if c["name"] == "Bran")
    service.move_combatant(
        campaign_id=table["campaign_id"], user_id=table["gm"], combatant_id=bran, delta=-1
    )
    assert names(service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])) == [
        "Bran",
        "Aria",
    ]

    set_order(service, table, {"Aria": "tarde"})
    assert names(service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])) == [
        "Bran",
        "Aria",
    ]


def test_moving_past_the_edge_of_a_hand_arranged_order_is_a_no_op(table):
    service, _ = start_with(table, "Aria", "Bran")
    use_system(service, input="text")
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    aria = next(c["id"] for c in state.combatants if c["name"] == "Aria")

    result = service.move_combatant(
        campaign_id=table["campaign_id"], user_id=table["gm"], combatant_id=aria, delta=-1
    )
    assert result.success
    assert names(result) == ["Aria", "Bran"]


def test_moving_keeps_the_turn_on_the_same_combatant(table):
    service, _ = start_with(table, "Aria", "Bran", "Cass")
    use_system(service, input="text")
    service.advance_turn(campaign_id=table["campaign_id"], user_id=table["gm"], delta=1)
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert state.state_payload()["current_name"] == "Bran"

    cass = next(c["id"] for c in state.combatants if c["name"] == "Cass")
    moved = service.move_combatant(
        campaign_id=table["campaign_id"], user_id=table["gm"], combatant_id=cass, delta=-1
    )
    assert names(moved) == ["Aria", "Cass", "Bran"]
    assert moved.state_payload()["current_name"] == "Bran"


def test_a_numeric_system_refuses_to_be_reordered_by_hand(table):
    service, _ = start_with(table, "Aria", "Bran")
    set_order(service, table, {"Aria": "20", "Bran": "10"})
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    result = service.move_combatant(
        campaign_id=table["campaign_id"],
        user_id=table["gm"],
        combatant_id=state.combatants[0]["id"],
        delta=1,
    )
    assert not result.success
    assert result.error_key == "game.combat.errors.order_is_automatic"


def test_an_ascending_system_puts_the_lowest_value_first(table):
    service, _ = start_with(table, "Aria", "Bran", "Cass")
    use_system(service, input="number", sort="asc")
    set_order(service, table, {"Aria": "12", "Bran": "3", "Cass": "20"})
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert names(state) == ["Bran", "Aria", "Cass"]


def test_an_unparseable_number_clears_the_value(table):
    service, _ = start_with(table, "Aria")
    set_order(service, table, {"Aria": "not a number"})
    state = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert state.combatants[0]["initiative"] is None


def test_ending_combat_clears_the_active_encounter(table):
    service, _ = start_with(table, "Aria")
    ended = service.end(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert not ended.active
    assert ended.combatants == []


def test_starting_a_second_combat_replaces_the_first(table):
    service, _ = start_with(table, "Aria")
    first_id = service.get_state(
        campaign_id=table["campaign_id"], user_id=table["gm"]
    ).state_payload()["combat_id"]

    service.start(campaign_id=table["campaign_id"], user_id=table["gm"])
    second = service.get_state(campaign_id=table["campaign_id"], user_id=table["gm"])
    assert second.state_payload()["combat_id"] != first_id
    assert second.combatants == []


def test_config_reads_the_authored_initiative_block(monkeypatch):
    authored = {
        "version": 2,
        "initiative": {
            "label": "Speed",
            "formula": "1d20 + @sheet.dex",
            "tieBreaker": "@sheet.dex",
            "icon": "shield",
            "accent": "#abcdef",
        },
        "resources": {"hp": {"path": "sheet.hp.value"}},
    }
    service = CombatConfigService()
    monkeypatch.setattr(service.rules, "get_combat_config", lambda system_id: authored)
    monkeypatch.setattr(service.locales, "get_locale", lambda system_id, locale: {})

    config = service.get_for_system("any-system")
    assert config.label == "Speed"
    assert config.formula == "1d20 + @sheet.dex"
    assert config.icon == "ph-shield"
    assert config.accent == "#abcdef"
    assert config.resources == {"hp": {"path": "sheet.hp.value"}}


def test_config_still_reads_the_pre_v2_nesting(monkeypatch):
    """Packages written against the old contract keep working."""
    legacy = {
        "turnOrder": {"strategy": "formula_sort", "label": "Iniciativa"},
        "initiative": {
            "mode": "individual",
            "roll": {"formula": "1d20 + @sheet.combat.initiative"},
            "sort": {"direction": "desc", "tieBreakers": ["@sheet.abilities.dex.score"]},
        },
    }
    service = CombatConfigService()
    monkeypatch.setattr(service.rules, "get_combat_config", lambda system_id: legacy)
    monkeypatch.setattr(service.locales, "get_locale", lambda system_id, locale: {})

    config = service.get_for_system("legacy-system")
    assert config.formula == "1d20 + @sheet.combat.initiative"
    assert config.tie_breaker == "@sheet.abilities.dex.score"
    assert config.label == "Iniciativa"


def test_config_without_a_system_is_a_plain_d20():
    config = CombatConfigService().get_for_system(None)
    assert config == CombatConfig()
    assert config.formula == ""
    assert config.action_id == "roll.initiative"
