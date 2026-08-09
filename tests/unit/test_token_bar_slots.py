"""A token draws two bars and the core never decides what they count.

``bar_1`` sits under the token, ``bar_2`` above it. A system points each slot at
whatever it tracks — hit points, stress, ammunition, a countdown — and the core
only resolves the paths and picks an ink.
"""

from __future__ import annotations

from app.engine.rules.token_mapping_resolver import (
    BAR_SLOTS,
    DEFAULT_BAR_COLORS,
    resolve_bars,
    resolve_token_view,
)

CONTEXT = {
    "core": {"name": "Aria"},
    "sheet": {
        "hp": {"value": 7, "max": 10, "temp": 3},
        "stress": {"level": 2},
        "ac": 15,
    },
}


def view(mapping: dict) -> dict:
    return resolve_token_view(
        actor_type="character",
        sheet_data=CONTEXT["sheet"],
        core=CONTEXT["core"],
        token_mappings={"character": mapping},
    )


def test_there_are_exactly_two_slots_in_render_order():
    assert BAR_SLOTS == ("bar_1", "bar_2")


def test_a_slot_resolves_its_value_and_max_paths():
    bars = resolve_bars({"bar_1": {"value": "sheet.hp.value", "max": "sheet.hp.max"}}, CONTEXT)
    assert bars["bar_1"]["value"] == 7
    assert bars["bar_1"]["max"] == 10


def test_a_bar_can_read_anything_the_sheet_has():
    """Nothing about the slot implies hit points."""
    bars = resolve_bars({"bar_2": {"value": "sheet.stress.level", "max": "sheet.ac"}}, CONTEXT)
    assert bars["bar_2"] == {
        "value": 2,
        "max": 15,
        "color": DEFAULT_BAR_COLORS["bar_2"],
        "visibility": "everyone",
    }


def test_the_default_inks_are_green_below_and_blue_above():
    bars = resolve_bars(
        {
            "bar_1": {"value": "sheet.hp.value", "max": "sheet.hp.max"},
            "bar_2": {"value": "sheet.hp.temp", "max": "sheet.hp.max"},
        },
        CONTEXT,
    )
    assert bars["bar_1"]["color"] == "#4caf50"
    assert bars["bar_2"]["color"] == "#3b82f6"


def test_a_system_may_repaint_a_bar():
    bars = resolve_bars(
        {"bar_1": {"value": "sheet.hp.value", "max": "sheet.hp.max", "color": "#a020f0"}},
        CONTEXT,
    )
    assert bars["bar_1"]["color"] == "#a020f0"


def test_a_colour_that_is_not_a_hex_falls_back_to_the_default():
    bars = resolve_bars(
        {"bar_1": {"value": "sheet.hp.value", "color": "javascript:alert(1)"}}, CONTEXT
    )
    assert bars["bar_1"]["color"] == DEFAULT_BAR_COLORS["bar_1"]


def test_a_colour_is_never_read_as_a_sheet_path():
    """``color`` is a literal. Resolving it would silently blank every bar."""
    bars = resolve_bars({"bar_1": {"value": "sheet.hp.value", "color": "#abc"}}, CONTEXT)
    assert bars["bar_1"]["color"] == "#abc"


def test_max_falls_back_to_the_value_so_a_bar_reads_full():
    bars = resolve_bars({"bar_1": {"value": "sheet.hp.value"}}, CONTEXT)
    assert bars["bar_1"]["max"] == 7


def test_an_unreadable_value_drops_the_bar_instead_of_drawing_it_empty():
    bars = resolve_bars({"bar_1": {"value": "sheet.nothing.here"}}, CONTEXT)
    assert bars == {}


def test_an_unknown_slot_name_is_ignored():
    bars = resolve_bars({"bar_9": {"value": "sheet.hp.value"}}, CONTEXT)
    assert bars == {}


def test_the_old_single_hp_bar_still_lands_in_the_lower_slot():
    """Mappings written before the slots existed keep working."""
    bars = resolve_bars({"hp": {"value": "sheet.hp.value", "max": "sheet.hp.max"}}, CONTEXT)
    assert bars["bar_1"]["value"] == 7
    assert "hp" not in bars


def test_the_rest_of_the_mapping_is_still_path_resolved():
    resolved = view(
        {
            "name": "core.name",
            "defense": "sheet.ac",
            "bars": {"bar_1": {"value": "sheet.hp.value", "max": "sheet.hp.max"}},
        }
    )
    assert resolved["name"] == "Aria"
    assert resolved["defense"] == 15
    assert resolved["bars"]["bar_1"]["value"] == 7


def test_a_mapping_without_bars_still_produces_a_view():
    resolved = view({"name": "core.name"})
    assert resolved["name"] == "Aria"
    assert resolved["bars"] == {}
