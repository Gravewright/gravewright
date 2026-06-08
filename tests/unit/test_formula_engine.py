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


def test_errors():
    with pytest.raises(FormulaError):
        evaluate("1 / 0")
    with pytest.raises(FormulaError):
        evaluate("floor(")
    with pytest.raises(FormulaError):
        evaluate("9999d6")                      
