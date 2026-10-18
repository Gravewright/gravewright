"""Optional authored labels retain the identity of their map element."""

from .services import MapError, title


MAX_ELEMENT_NAME = 120


def clean_name(value):
    if not isinstance(value, str) or "\x00" in value:
        raise MapError(f"Use a name with 1 to {MAX_ELEMENT_NAME} characters.")
    return title(value, MAX_ELEMENT_NAME)


def copy_name(result, source):
    """Leave older unnamed elements unchanged while validating authored names."""
    if "name" in source:
        result["name"] = clean_name(source["name"])
    return result
