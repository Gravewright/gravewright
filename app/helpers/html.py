from __future__ import annotations

import html


def escape_html(value: str) -> str:
    return html.escape(value, quote=True)


def forbid_html(value: str) -> str:
    return value.replace("<", "").replace(">", "")