from __future__ import annotations

import pytest

from app.engine.rules.formula_engine import FormulaError, evaluate

CTX = {
    "core": {"name": "Aria"},
    "sheet": {
        "hp": {"value": 20, "max": 30},
        "ac": 15,
        "attributes": {"str": {"score": 14}, "dex": {"mod": 3}},
    },
}
HELPERS = {"abilityMod": {"args": ["score"], "expression": "floor((score - 10) / 2)"}}


def _fixed_roller(value: int):
    return lambda count, sides: [value] * count


def test_arithmetic_and_precedence():
    assert evaluate("2 + 3 * 4").total == 14
    assert evaluate("(2 + 3) * 4").total == 20
    assert evaluate("-5 + 2").total == -3


def test_path_resolution():
    assert evaluate("@sheet.hp.value + @sheet.attributes.dex.mod", context=CTX).total == 23
                                 
    assert evaluate("@sheet.nope.here", context=CTX).total == 0


def test_functions():
    assert evaluate("floor(7 / 2)").total == 3
    assert evaluate("ceil(7 / 2)").total == 4
    assert evaluate("min(3, 9, 1)").total == 1
    assert evaluate("max(3, 9, 1)").total == 9
    assert evaluate("clamp(40, 0, 30)").total == 30
    assert evaluate("abs(0 - 5)").total == 5


def test_if_and_comparisons():
    assert evaluate("if(@sheet.ac >= 15, 1, 0)", context=CTX).total == 1
    assert evaluate("if(@sheet.ac > 15, 1, 0)", context=CTX).total == 0
    assert evaluate("if(1 == 1 && 2 != 3, 10, 20)").total == 10


def test_helpers():
    assert evaluate("abilityMod(@sheet.attributes.str.score)", context=CTX, helpers=HELPERS).total == 2


def test_input_scope():
    result = evaluate(
        "max(0, @sheet.hp.value - input.amount)", context=CTX, scope={"input": {"amount": 5}}
    )
    assert result.total == 15


def test_dice_collects_groups_and_modifier():
    result = evaluate("1d20 + @sheet.attributes.dex.mod", context=CTX, roller=_fixed_roller(17))
    assert result.total == 20
    assert result.groups == [{"notation": "1d20", "results": [17], "subtotal": 17}]
    assert result.modifier == 3
    assert result.dice_subtotal == 17


def test_multiple_dice_groups():
    result = evaluate("2d6 + 1d4", roller=_fixed_roller(3))
    assert result.groups[0]["notation"] == "2d6"
    assert result.groups[0]["subtotal"] == 6
    assert result.total == 9


def test_exploding_die_rerolls_until_below_threshold():
    rolls = iter((6, 6, 2))
    result = evaluate("explode(6, 6)", roller=lambda count, sides: [next(rolls)])
    assert result.total == 14
    assert result.groups == [
        {"notation": "1d6!>=6", "results": [6, 6, 2], "subtotal": 14}
    ]


def test_exploding_die_supports_sheet_values():
    context = {"sheet": {"die": {"size": 8, "explode": 7}}}
    rolls = iter((7, 3))
    result = evaluate(
        "explode(@sheet.die.size, @sheet.die.explode)",
        context=context,
        roller=lambda count, sides: [next(rolls)],
    )
    assert result.total == 10
    assert result.groups[0]["notation"] == "1d8!>=7"


def test_dynamic_die_uses_runtime_sides():
    result = evaluate("die(@sheet.step)", context={"sheet": {"step": 10}}, roller=_fixed_roller(7))
    assert result.total == 7
    assert result.groups[0]["notation"] == "1d10"


def test_success_pool_counts_results_at_or_above_target():
    result = evaluate("successes(4, 6, 5)", roller=lambda count, sides: [1, 5, 6, 4])
    assert result.total == 2
    assert result.groups == [
        {"notation": "4d6>=5", "results": [1, 5, 6, 4], "subtotal": 2}
    ]


def test_roll_under_counts_results_at_or_below_target():
    result = evaluate("under(2, 20, 10)", roller=lambda count, sides: [8, 14])
    assert result.total == 1
    assert result.groups[0]["notation"] == "2d20<=10"


def test_fate_roll_records_minus_blank_plus_faces():
    result = evaluate("fate() + 2", roller=lambda count, sides: [1, 2, 3, 3])
    assert result.total == 3
    assert result.groups == [
        {"notation": "4dF", "results": [-1, 0, 1, 1], "subtotal": 1}
    ]


def test_draw_returns_card_index():
    result = evaluate("draw(52)", roller=lambda count, sides: [37])
    assert result.total == 37
    assert result.groups[0]["notation"] == "draw(52)"


def test_errors():
    with pytest.raises(FormulaError):
        evaluate("1 / 0")
    with pytest.raises(FormulaError):
        evaluate("floor(")
    with pytest.raises(FormulaError):
        evaluate("9999d6")                      
