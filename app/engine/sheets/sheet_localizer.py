"""Resolves Sheet IR translation keys against a system locale catalog.

The renderer stays language-agnostic: any IR node (or option) may carry a
``labelKey``/``titleKey``/similar key pointing at a key in the system's
``locales/{id}.json``. Here we walk the layout and fill display fields from the
active catalog, falling back to whatever literal value the node already had.
"""

from __future__ import annotations

from typing import Any


LOCALIZABLE_FIELDS = {
    "label": "labelKey",
    "title": "titleKey",
    "placeholder": "placeholderKey",
    "emptyText": "emptyTextKey",
    "abbr": "abbrKey",
    "ability": "abilityKey",
}


def localize_layout(layout: Any, catalog: dict[str, str]) -> Any:
    """Return a copy of ``layout`` with system locale keys resolved."""
    if not catalog:
        return layout
    return _walk(layout, catalog)


def _walk(node: Any, catalog: dict[str, str]) -> Any:
    if isinstance(node, dict):
        out = {key: _walk(value, catalog) for key, value in node.items()}
        for field, key_field in LOCALIZABLE_FIELDS.items():
            locale_key = out.get(key_field)
            if isinstance(locale_key, str) and locale_key in catalog:
                out[field] = catalog[locale_key]
        return out
    if isinstance(node, list):
        return [_walk(item, catalog) for item in node]
    return node
