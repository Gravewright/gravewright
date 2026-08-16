from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any


PREFIXES = ("orb", "portal", "fog", "flame", "liquid", "weather", "particles", "grid", "vortex", "aura")
PRESET_IDS = tuple(f"{prefix}-{number}" for prefix in PREFIXES for number in range(1, 6))
SCHEMA_VERSION = 1

PARAMETERS: dict[str, dict[str, Any]] = {
    "x": {"type": "number", "default": 0.0, "min": -1_000_000.0, "max": 1_000_000.0},
    "y": {"type": "number", "default": 0.0, "min": -1_000_000.0, "max": 1_000_000.0},
    "radius": {"type": "number", "default": 8.0, "min": 0.0, "max": 120.0},
    "rotation": {"type": "number", "default": 0.0, "min": 0.0, "max": 360.0},
    "opacity": {"type": "number", "default": 1.0, "min": 0.0, "max": 1.0},
    "intensity": {"type": "number", "default": 0.8, "min": 0.0, "max": 1.0},
    "scale": {"type": "number", "default": 1.0, "min": 0.1, "max": 20.0},
    "speed": {"type": "number", "default": 1.0, "min": 0.0, "max": 8.0},
    "color": {"type": "color", "default": "#8fb6ff", "pattern": "^#[0-9a-fA-F]{6}$"},
    "blendMode": {"type": "enum", "default": "normal", "options": ["normal", "add", "multiply", "screen"]},
    "enabled": {"type": "boolean", "default": True},
}

REGISTRY = tuple(
    {
        "id": preset_id,
        "schemaVersion": SCHEMA_VERSION,
        "labelKey": f"lighting.shaders.presets.{preset_id}.name",
        "descriptionKey": f"lighting.shaders.presets.{preset_id}.description",
        "parameters": deepcopy(PARAMETERS),
    }
    for preset_id in PRESET_IDS
)


def public_registry() -> list[dict[str, Any]]:
    return deepcopy(list(REGISTRY))


def get_preset(preset_id: str) -> dict[str, Any] | None:
    return next((deepcopy(value) for value in REGISTRY if value["id"] == preset_id), None)


def validate_parameters(value: Any, *, partial: bool) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, dict) or len(value) > len(PARAMETERS):
        return None, "sdk.shaders.parameters_invalid"
    if any(key not in PARAMETERS for key in value):
        return None, "sdk.shaders.parameter_unknown"
    source = value if partial else {key: spec["default"] for key, spec in PARAMETERS.items()} | value
    normalized: dict[str, Any] = {}
    for key, raw in source.items():
        spec = PARAMETERS[key]
        kind = spec["type"]
        if kind == "number":
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not isfinite(float(raw)):
                return None, "sdk.shaders.parameter_type_invalid"
            number = float(raw)
            if number < spec["min"] or number > spec["max"]:
                return None, "sdk.shaders.parameter_range_invalid"
            normalized[key] = number
        elif kind == "boolean":
            if not isinstance(raw, bool):
                return None, "sdk.shaders.parameter_type_invalid"
            normalized[key] = raw
        elif kind == "enum":
            if raw not in spec["options"]:
                return None, "sdk.shaders.parameter_invalid"
            normalized[key] = raw
        elif kind == "color":
            import re
            if not isinstance(raw, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", raw) is None:
                return None, "sdk.shaders.parameter_invalid"
            normalized[key] = raw.lower()
    return normalized, None


def implementation_reference(preset_id: str) -> str:
    return f"gravewright-preset://{preset_id}/v{SCHEMA_VERSION}"
