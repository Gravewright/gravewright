from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class RenderPriority(IntEnum):
    IMMEDIATE = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

    def promoted(self, levels: int = 1) -> RenderPriority:
        return RenderPriority(max(RenderPriority.IMMEDIATE, int(self) - max(0, levels)))


@dataclass(frozen=True)
class RenderPriorityAgingPolicy:
    promote_after_ms: int = 500
    max_aged_priority: RenderPriority = RenderPriority.HIGH

    def __post_init__(self) -> None:
        if self.promote_after_ms <= 0:
            raise ValueError("promote_after_ms must be positive")

    def effective_priority(
        self,
        *,
        base_priority: RenderPriority,
        waited_ms: int,
    ) -> RenderPriority:
        if waited_ms < self.promote_after_ms:
            return base_priority

        promotion_levels = waited_ms // self.promote_after_ms
        promoted_value = int(base_priority) - promotion_levels
        capped_value = max(int(self.max_aged_priority), promoted_value)

        return RenderPriority(capped_value)
