from __future__ import annotations

from app.realtime.scene_stream import _MAX_KNOWN_CHUNKS
from app.realtime.scene_stream import _MAX_VIEWPORT_HEIGHT_CHUNKS
from app.realtime.scene_stream import _MAX_VIEWPORT_ID_LEN
from app.realtime.scene_stream import _MAX_VIEWPORT_LAYERS
from app.realtime.scene_stream import _MAX_VIEWPORT_WIDTH_CHUNKS
from app.realtime.scene_stream import SceneStreamCommandHandler


def _parse(payload: dict) -> dict:
    handler = SceneStreamCommandHandler()
    return handler._parse_payload(
        message={"scene_id": "scene-1"},
        payload=payload,
        command_id="cmd-1",
    )


def _base_payload(**overrides) -> dict:
    payload = {
        "viewport_id": "vp-1",
        "generation": 1,
        "layers": [],
        "known": {},
        "cx0": 0,
        "cy0": 0,
        "cx1": 4,
        "cy1": 4,
    }
    payload.update(overrides)
    return payload


def test_valid_viewport_parses() -> None:
    parsed = _parse(_base_payload())
    assert parsed.get("type") != "error"
    assert parsed["scene_id"] == "scene-1"


def test_viewport_id_length_is_bounded() -> None:
    parsed = _parse(_base_payload(viewport_id="v" * (_MAX_VIEWPORT_ID_LEN + 1)))
    assert parsed["type"] == "error"


def test_too_many_layers_rejected() -> None:
    parsed = _parse(_base_payload(layers=[f"l{i}" for i in range(_MAX_VIEWPORT_LAYERS + 1)]))
    assert parsed["type"] == "error"


def test_too_many_known_chunks_rejected() -> None:
    known = {f"l:{i}:0": 1 for i in range(_MAX_KNOWN_CHUNKS + 1)}
    parsed = _parse(_base_payload(known=known))
    assert parsed["type"] == "error"


def test_inverted_bounds_rejected() -> None:
    parsed = _parse(_base_payload(cx0=10, cx1=5))
    assert parsed["type"] == "error"


def test_span_too_large_rejected() -> None:
    parsed = _parse(_base_payload(cx0=0, cx1=_MAX_VIEWPORT_WIDTH_CHUNKS))
    assert parsed["type"] == "error"
    parsed = _parse(_base_payload(cy0=0, cy1=_MAX_VIEWPORT_HEIGHT_CHUNKS))
    assert parsed["type"] == "error"


def test_area_too_large_rejected(monkeypatch) -> None:
                                                                             
    import app.realtime.scene_stream as scene_stream

    monkeypatch.setattr(scene_stream, "_MAX_VIEWPORT_CHUNK_AREA", 4)
                                                                        
    parsed = _parse(_base_payload(cx0=0, cx1=2, cy0=0, cy1=2))
    assert parsed["type"] == "error"
