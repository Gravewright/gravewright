from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from app.domain.scenes import RenderPriority


@dataclass(frozen=True)
class ChunkViewportPriority:
    priority: RenderPriority
    distance: int
    ring: str


def classify_chunk_priority(
    *,
    cx: int,
    cy: int,
    cx0: int,
    cy0: int,
    cx1: int,
    cy1: int,
    focus_cx: float | None = None,
    focus_cy: float | None = None,
    prefetch_radius: int = 1,
) -> ChunkViewportPriority:
    """Classify a chunk relative to the viewport so the scheduler can favour
    visible work first, then the prefetch ring, then background.

    The distance is the Euclidean distance (in chunks) from the player's focal
    point, rounded to integer rings, so chunks fill in concentric arcs from where
    the player is actually looking outward. The focal point is the viewport
    centre supplied by the client (``focus_cx``/``focus_cy``); it falls back to
    the centre of the requested range when not provided. Using the client focus
    keeps the origin at the screen centre even when the range is clamped to the
    scene edges.
    """

    center_x = focus_cx if focus_cx is not None else (cx0 + cx1) / 2
    center_y = focus_cy if focus_cy is not None else (cy0 + cy1) / 2
    distance = round(hypot(cx - center_x, cy - center_y))

    visible = cx0 <= cx <= cx1 and cy0 <= cy <= cy1
    if visible:
        if distance <= 1:
            return ChunkViewportPriority(RenderPriority.HIGH, distance, "visible_center")
        return ChunkViewportPriority(RenderPriority.NORMAL, distance, "visible_edge")

    in_prefetch = (
        cx0 - prefetch_radius <= cx <= cx1 + prefetch_radius
        and cy0 - prefetch_radius <= cy <= cy1 + prefetch_radius
    )
    if in_prefetch:
        return ChunkViewportPriority(RenderPriority.LOW, distance, "prefetch")

    return ChunkViewportPriority(RenderPriority.BACKGROUND, distance, "background")
