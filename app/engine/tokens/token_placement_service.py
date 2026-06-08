from __future__ import annotations

from math import ceil


class TokenPlacementService:
    def calculate_positions(
        self,
        *,
        origin_x: int,
        origin_y: int,
        count: int,
    ) -> list[tuple[int, int]]:
        """Return (grid_x, grid_y) for `count` tokens in a square formation.

        First token lands on the origin cell; subsequent tokens fill left-to-right,
        top-to-bottom with columns = ceil(sqrt(count)).
        """
        if count <= 0:
            return []

        columns = ceil(count ** 0.5)
        return [
            (origin_x + (i % columns), origin_y + (i // columns))
            for i in range(count)
        ]
