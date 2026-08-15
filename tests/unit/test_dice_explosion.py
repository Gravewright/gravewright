"""Dado aberto tem de continuar aberto.

O ``xdice`` implementa ``!`` como um único dado extra por máximo e nunca
reexamina o que ele mesmo adicionou: um d12 que tira 12, explode e tira 12 de
novo parava ali. O total saía sistematicamente baixo e, num sistema com dado
aberto, isso é a regra errada: não um detalhe de apresentação.
"""

from __future__ import annotations

import random

import pytest

from app.engine.dice.roll_service import RollService
from app.engine.dice import exploding_dice


def _chain(expression: str, rolls: int = 4000) -> int:
    """Maior quantidade de dados que uma cadeia produziu em N rolagens."""
    svc = RollService()
    maior = 0
    for _ in range(rolls):
        result = svc.evaluate(expression)
        assert result is not None
        maior = max(maior, len(result.groups[0]["results"]))
    return maior


def test_an_exploding_die_keeps_exploding():
    random.seed(20260810)
    # Com a biblioteca crua isto nunca passa de 2: um dado extra e acabou.
    assert _chain("1d4!") > 2


def test_the_average_of_an_open_ended_die_matches_the_open_ended_maths():
    """1d4! aberto vale (n+1)/2 · n/(n−1) = 3,33…; parando no primeiro extra
    daria ~3,12. A média é o que denuncia a regra errada."""
    random.seed(20260810)
    svc = RollService()
    amostras = 30000
    media = sum(svc.evaluate("1d4!").total for _ in range(amostras)) / amostras
    assert 3.20 < media < 3.47, media


def test_dice_that_cannot_explode_are_left_alone():
    """dF não tem máximo que signifique explodir e d1 explodiria para sempre."""
    random.seed(1)
    svc = RollService()
    for _ in range(200):
        assert len(svc.evaluate("1dF!").groups[0]["results"]) == 1
        assert len(svc.evaluate("1d1!").groups[0]["results"]) == 1


def test_dropping_still_happens_before_the_explosion():
    """L/H descartam do conjunto rolado; o que a explosão traz não vira candidato
    a descarte, senão a notação mudaria de sentido no meio da rolagem."""
    random.seed(7)
    svc = RollService()
    for _ in range(200):
        result = svc.evaluate("4d6L1!")
        assert len(result.groups[0]["dropped"]) == 1
        assert len(result.groups[0]["results"]) >= 3
        assert result.groups[0]["subtotal"] == sum(result.groups[0]["results"])


def test_a_die_that_always_rolls_its_maximum_still_terminates(monkeypatch):
    """Sem teto, um dado viciado no máximo trava o servidor dentro do request."""
    monkeypatch.setattr(random, "randint", lambda _low, high: high)
    monkeypatch.setattr(exploding_dice, "MAX_EXPLOSIONS", 12)

    result = RollService().evaluate("1d6!")
    assert result is not None
    assert len(result.groups[0]["results"]) == 13, "1 rolado + o teto de explosões"


@pytest.mark.parametrize("expression", ["1d6!", "max(1d8!,1d6!)", "2d20L1", "1d6!+2"])
def test_the_notation_the_tray_builds_still_evaluates(expression: str):
    assert RollService().evaluate(expression) is not None
