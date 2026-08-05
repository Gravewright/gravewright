from __future__ import annotations

from dataclasses import dataclass

import xdice


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
                "subtotal": int(s),
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
