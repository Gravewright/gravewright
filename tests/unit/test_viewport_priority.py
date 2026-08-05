from __future__ import annotations

from app.domain.scenes import RenderPriority
from app.realtime.viewport_priority import classify_chunk_priority


def _classify(cx, cy, *, cx0=4, cy0=4, cx1=6, cy1=6, prefetch_radius=1):
    return classify_chunk_priority(
        cx=cx,
        cy=cy,
        cx0=cx0,
        cy0=cy0,
        cx1=cx1,
        cy1=cy1,
        prefetch_radius=prefetch_radius,
    )


def test_center_chunk_is_high_priority():
    result = _classify(5, 5)
    assert result.priority == RenderPriority.HIGH
    assert result.ring == "visible_center"
    assert result.distance == 0


def test_visible_edge_chunk_is_normal_priority():
                                                                 
    result = _classify(3, 3, cx0=0, cy0=0, cx1=10, cy1=10)
    assert result.priority == RenderPriority.NORMAL
    assert result.ring == "visible_edge"


def test_prefetch_ring_is_low_priority():
    result = _classify(7, 5)
    assert result.priority == RenderPriority.LOW
    assert result.ring == "prefetch"


def test_background_outside_prefetch_ring():
    result = _classify(20, 20)
    assert result.priority == RenderPriority.BACKGROUND
    assert result.ring == "background"


def test_center_before_edge_before_prefetch():
    big = {"cx0": 0, "cy0": 0, "cx1": 10, "cy1": 10}
    center = classify_chunk_priority(cx=5, cy=5, **big)
    edge = classify_chunk_priority(cx=0, cy=0, **big)
    prefetch = classify_chunk_priority(cx=11, cy=5, **big)

    assert int(center.priority) < int(edge.priority) < int(prefetch.priority)
