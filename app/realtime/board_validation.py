"""Board command payload validation/normalization (pure functions).

Extracted from ``board_command_handler`` (maintenance plan, Etapa 8) to separate
input validation from dispatch/authorization/handlers. These functions are pure:
each takes a raw payload fragment and returns a normalized ``dict`` or an error
message ``str``. Behavior is unchanged from the original module.
"""

from __future__ import annotations

from typing import Any


def _expected_board_version(payload: dict[str, Any]) -> int | str | None:
    value = payload.get("expected_board_version")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return "expected_board_version must be a non-negative integer when provided."
    return value


def _normalize_board_shape(raw: dict[str, Any], label: str) -> dict[str, Any] | str:
    shape_id = raw.get("id")
    scene_id = raw.get("scene_id")
    shape = raw.get("shape")
    start = raw.get("start")
    end = raw.get("end")

    if not isinstance(shape_id, str) or not shape_id:
        return f"{label}.id is required."
    if not isinstance(scene_id, str) or not scene_id:
        return f"{label}.scene_id is required."
    if shape not in {"line", "circle", "square", "cone"}:
        return f"{label}.shape must be line, circle, square or cone."
    if not isinstance(start, dict) or not isinstance(end, dict):
        return f"{label}.start and {label}.end are required."

    start_point = _normalize_point(start, f"{label}.start")
    if isinstance(start_point, str):
        return start_point
    end_point = _normalize_point(end, f"{label}.end")
    if isinstance(end_point, str):
        return end_point
    preset = _normalize_preset_id(raw.get("preset_id"), label)
    if isinstance(preset, str):
        return preset

    return {
        "id": shape_id,
        "scene_id": scene_id,
        "shape": shape,
        "start": start_point,
        "end": end_point,
        **preset,
        **_normalize_marker_text(raw.get("text")),
        **_normalize_shape_style(raw.get("style")),
    }


def _normalize_freehand(raw: dict[str, Any], label: str) -> dict[str, Any] | str:
    drawing_id = raw.get("id")
    scene_id = raw.get("scene_id")
    points = raw.get("points")
    if not isinstance(drawing_id, str) or not drawing_id:
        return f"{label}.id is required."
    if not isinstance(scene_id, str) or not scene_id:
        return f"{label}.scene_id is required."
    if not isinstance(points, list) or len(points) < 2 or len(points) > 512:
        return f"{label}.points must contain 2 to 512 points."

    normalized_points: list[dict[str, float]] = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            return f"{label}.points[{index}] must be an object."
        normalized = _normalize_point(point, f"{label}.points[{index}]")
        if isinstance(normalized, str):
            return normalized
        normalized_points.append(normalized)

    return {
        "id": drawing_id,
        "scene_id": scene_id,
        "kind": "freehand",
        "points": normalized_points,
        **_normalize_shape_style(raw.get("style")),
    }


def _normalize_text(raw: dict[str, Any], label: str) -> dict[str, Any] | str:
    drawing_id = raw.get("id")
    scene_id = raw.get("scene_id")
    text = raw.get("text")
    position = raw.get("position")
    if not isinstance(drawing_id, str) or not drawing_id:
        return f"{label}.id is required."
    if not isinstance(scene_id, str) or not scene_id:
        return f"{label}.scene_id is required."
    if not isinstance(text, str) or not text.strip():
        return f"{label}.text is required."
    if not isinstance(position, dict):
        return f"{label}.position is required."

    normalized_position = _normalize_point(position, f"{label}.position")
    if isinstance(normalized_position, str):
        return normalized_position

    font_size = raw.get("fontSize")
    if not isinstance(font_size, int | float):
        font_size = 28.0
    font_size = max(8.0, min(200.0, float(font_size)))

    return {
        "id": drawing_id,
        "scene_id": scene_id,
        "kind": "text",
        "position": normalized_position,
        "text": text.strip()[:200],
        "fontSize": font_size,
        **_normalize_shape_style(raw.get("style")),
    }


def _normalize_ttl_ms(raw: Any) -> int:
    if not isinstance(raw, int | float):
        return 6000
    return max(1000, min(60000, int(raw)))


def _normalize_shape_style(raw: Any) -> dict[str, dict[str, str | float]]:
    if not isinstance(raw, dict):
        return {}
    style: dict[str, str | float] = {}
    for key in ("stroke", "fill", "strokeDasharray"):
        value = raw.get(key)
        if isinstance(value, str) and 0 < len(value) <= 64:
            style[key] = value
    stroke_width = raw.get("strokeWidth")
    if isinstance(stroke_width, int | float):
        style["strokeWidth"] = max(1.0, min(12.0, float(stroke_width)))
    return {"style": style} if style else {}


def _normalize_marker_text(raw: Any) -> dict[str, str]:
    if not isinstance(raw, str):
        return {}
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    return {"text": text[:220]} if text else {}


def _normalize_preset_id(raw: Any, label: str) -> dict[str, str] | str:
    if raw is None:
        return {}
    if not isinstance(raw, str):
        return f"{label}.preset_id must be a string."
    preset_id = raw.strip()
    if not preset_id:
        return {}
    if len(preset_id) > 80:
        return f"{label}.preset_id is too long."
    return {"preset_id": preset_id}


def _normalize_point(raw: dict[str, Any], path: str) -> dict[str, float] | str:
    world_x = raw.get("worldX")
    world_y = raw.get("worldY")
    if not isinstance(world_x, int | float) or not isinstance(world_y, int | float):
        return f"{path}.worldX and {path}.worldY are required numbers."
    return {
        "worldX": float(world_x),
        "worldY": float(world_y),
    }
