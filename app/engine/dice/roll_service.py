from __future__ import annotations

import re
from dataclasses import dataclass

import xdice

from app.engine.dice import exploding_dice


# `!` na biblioteca rola um dado extra e para; na mesa, dado aberto continua
# explodindo enquanto cair no máximo. Ver o módulo para o porquê do patch.
exploding_dice.install()



_SIDES = re.compile(r"^\d*d(\d+|%|f)", re.IGNORECASE)


def _sides_from_notation(notation: str) -> int:
    match = _SIDES.match(str(notation or ""))
    if match is None:
        return 0
    face = match.group(1).lower()
    if face == "%":
        return 100
    if face == "f":
        return 0
    return int(face)


@dataclass(frozen=True)
class RollResult:
    expression: str
    groups: list[dict]
    modifier: int
    total: int


class RollService:
    MAX_EXPRESSION_LEN = 60

    def evaluate(self, expression: str) -> RollResult | None:
        if len(expression) > self.MAX_EXPRESSION_LEN:
            return None
        try:
            pattern_score = xdice.roll(expression)
        except Exception:
            return None

        total = int(pattern_score)
        groups = [
            {
                "notation": s.name,
                "results": list(s.detail),



                "dropped": list(getattr(s, "dropped", []) or []),
                "subtotal": int(s),


                "sides": _sides_from_notation(s.name),
            }
            for s in pattern_score.scores()
        ]
        modifier = total - sum(g["subtotal"] for g in groups)

        return RollResult(
            expression=expression,
            groups=groups,
            modifier=modifier,
            total=total,
        )
