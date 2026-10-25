"""Bounded shader parameters shared by authored graphs and their runtime actions."""
from .objects import boolean, number
from .services import MapError, color

SHADER_RANGES = {
    "intensity": (0, 1), "opacity": (0, 1), "speed": (0, 8),
    "scale": (.1, 20), "radius": (0, 1e6), "rotation": (-36000, 36000),
    "light_response": (0, 1), "light_emission": (0, 2),
}


def clean_value(property_name, value):
    if property_name == "enabled":
        return boolean(value)
    if property_name == "color":
        return color(value).lower()
    if isinstance(property_name, str) and property_name in SHADER_RANGES:
        return number(value, *SHADER_RANGES[property_name])
    raise MapError("Invalid shader control property.")


def value_type(property_name):
    return "boolean" if property_name == "enabled" else "text" if property_name == "color" else "number"
