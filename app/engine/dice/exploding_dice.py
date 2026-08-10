"""Explosão aberta (``!``) para o avaliador de dados.

O ``xdice`` implementa ``!`` como **um** dado extra por dado que caiu no máximo,
e nunca reexamina os dados que ele mesmo adicionou::

    if self._explode:
        exploded = [self._rollone() for _ in range(len([s for s in results if s == self._sides]))]
        results += exploded

Na mesa isso está errado: um d12 que tira 12, explode e tira 12 de novo tem de
continuar explodindo — é essa a promessa de "explodir" em Savage Worlds e em
qualquer sistema com dado aberto. Do jeito da biblioteca a cadeia parava em dois
dados e o total ficava sistematicamente baixo.

O ``xdice`` não expõe configuração para isso, e ele é o avaliador de toda a
notação do projeto (``L``/``H``, ``max()``, modificadores). Trocar a biblioteca
por causa de uma regra seria muito maior do que substituir o método que a viola,
então ``Dice.roll`` é substituído aqui, uma vez, na importação — e as regras que
não são a explosão (ordem de rolagem, descarte, nome do grupo) continuam sendo
as da biblioteca.
"""

from __future__ import annotations

import xdice


# Teto de segurança: sem ele, um ``99d2!`` (ou qualquer dado de poucas faces em
# quantidade) rola para sempre. É por rolagem, não por dado, e alto o bastante
# para nunca ser alcançado por uma cadeia honesta.
MAX_EXPLOSIONS = 100


def _explodes(sides) -> bool:
    """dF não tem "máximo" que signifique explodir, e d1 explodiria sem fim."""
    if not isinstance(sides, int):
        return False
    return sides >= 2


def _pop_lowest(values: list[int]) -> int:
    return values.pop(values.index(min(values)))


def _pop_highest(values: list[int]) -> int:
    return values.pop(values.index(max(values)))


def _roll_open_ended(dice) -> xdice.Score:
    """``Dice.roll`` da biblioteca, mas com a explosão em cadeia.

    A ordem é a mesma do original: rola, descarta, e só então explode — um dado
    descartado não gera explosão, e os dados que a explosão traz não entram no
    descarte (senão o ``L``/``H`` mudaria de significado no meio da rolagem).
    """
    results = [dice._rollone() for _ in range(dice.amount)]
    dropped = [_pop_lowest(results) for _ in range(dice.drop_lowest)] + [
        _pop_highest(results) for _ in range(dice.drop_highest)
    ]

    if dice._explode and _explodes(dice.sides):
        wave = results
        adicionados = 0
        while adicionados < MAX_EXPLOSIONS:
            wave = [dice._rollone() for value in wave if value == dice.sides]
            if not wave:
                break
            del wave[max(0, MAX_EXPLOSIONS - adicionados) :]
            results += wave
            adicionados += len(wave)

    return xdice.Score(results, dropped, dice.name)


def install() -> None:
    """Idempotente: importar o módulo duas vezes não empilha patches."""
    if getattr(xdice.Dice.roll, "_gravewright_open_ended", False):
        return
    _roll_open_ended._gravewright_open_ended = True
    xdice.Dice.roll = _roll_open_ended
