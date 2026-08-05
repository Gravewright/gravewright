from __future__ import annotations

"""Board command module split (Maintenance Plan - Etapa 8).

``board_command_handler`` was split into pure ``board_validation`` (payload
normalization) and ``board_results`` (ack/error envelopes). These tests lock the
extracted behavior and confirm the public surface is unchanged: the handler
module still exposes ``BoardCommandHandler`` and re-exports the helpers callers
(and existing tests) may reference.
"""

from app.realtime import board_command_handler
from app.realtime.board_results import (
    BoardCommandResult,
    _ack,
    _board_conflict,
    _invalid,
)
from app.realtime.board_validation import (
    _expected_board_version,
    _normalize_board_shape,
    _normalize_freehand,
    _normalize_point,
    _normalize_preset_id,
    _normalize_shape_style,
    _normalize_text,
    _normalize_ttl_ms,
)


def test_handler_public_surface_unchanged():
    assert hasattr(board_command_handler, "BoardCommandHandler")
    # Helpers remain reachable through the handler module (re-exported).
    assert board_command_handler.BoardCommandResult is BoardCommandResult
    assert board_command_handler._normalize_board_shape is _normalize_board_shape
    assert board_command_handler._ack is _ack


def test_normalize_point_accepts_numbers_and_rejects_missing():
    assert _normalize_point({"worldX": 1, "worldY": 2.5}, "p") == {"worldX": 1.0, "worldY": 2.5}
    assert _normalize_point({"worldX": "x", "worldY": 2}, "p").endswith("required numbers.")


def test_normalize_ttl_ms_clamps():
    assert _normalize_ttl_ms("nope") == 6000
    assert _normalize_ttl_ms(10) == 1000
    assert _normalize_ttl_ms(999_999) == 60000
    assert _normalize_ttl_ms(5000) == 5000


def test_normalize_shape_style_filters_and_clamps():
    assert _normalize_shape_style("x") == {}
    styled = _normalize_shape_style({"stroke": "#fff", "strokeWidth": 100, "bogus": "y"})
    assert styled == {"style": {"stroke": "#fff", "strokeWidth": 12.0}}


def test_normalize_preset_id_variants():
    assert _normalize_preset_id(None, "l") == {}
    assert _normalize_preset_id("  ", "l") == {}
    assert _normalize_preset_id("abc", "l") == {"preset_id": "abc"}
    assert _normalize_preset_id(5, "l").endswith("must be a string.")
    assert _normalize_preset_id("x" * 81, "l").endswith("is too long.")


def test_normalize_board_shape_happy_and_error():
    ok = _normalize_board_shape(
        {
            "id": "s1",
            "scene_id": "sc1",
            "shape": "circle",
            "start": {"worldX": 0, "worldY": 0},
            "end": {"worldX": 3, "worldY": 4},
        },
        "shape",
    )
    assert ok["id"] == "s1" and ok["shape"] == "circle"
    assert _normalize_board_shape({"id": "", "scene_id": "s"}, "shape") == "shape.id is required."
    bad_shape = _normalize_board_shape(
        {"id": "s", "scene_id": "sc", "shape": "hexagon", "start": {}, "end": {}}, "shape"
    )
    assert "shape must be" in bad_shape


def test_normalize_freehand_point_bounds():
    too_few = _normalize_freehand({"id": "d", "scene_id": "s", "points": [{"worldX": 0, "worldY": 0}]}, "d")
    assert "2 to 512 points" in too_few
    ok = _normalize_freehand(
        {"id": "d", "scene_id": "s", "points": [{"worldX": 0, "worldY": 0}, {"worldX": 1, "worldY": 1}]},
        "d",
    )
    assert ok["kind"] == "freehand" and len(ok["points"]) == 2


def test_normalize_text_clamps_font_and_length():
    ok = _normalize_text(
        {"id": "t", "scene_id": "s", "text": " hi ", "position": {"worldX": 0, "worldY": 0}, "fontSize": 5},
        "t",
    )
    assert ok["kind"] == "text" and ok["text"] == "hi" and ok["fontSize"] == 8.0


def test_expected_board_version_validation():
    assert _expected_board_version({}) is None
    assert _expected_board_version({"expected_board_version": 3}) == 3
    assert isinstance(_expected_board_version({"expected_board_version": -1}), str)
    assert isinstance(_expected_board_version({"expected_board_version": True}), str)


def test_result_builders_shape():
    ack = _ack("c1", "room", "board.ping", "scene", extra={"board_version": 2})
    assert isinstance(ack, BoardCommandResult) and ack.handled is True
    assert ack.response["payload"]["success"] is True
    assert ack.response["payload"]["board_version"] == 2

    conflict = _board_conflict("c1")
    assert conflict.handled is True and conflict.response["code"] == "board_version_conflict"

    invalid = _invalid("c1", "bad")
    assert invalid.response["code"] == "invalid_payload"
