"""Interop contract for SDK packages — ``sdk.bus.*``.

Validates a package's declared ``interop`` block: the events it ``emits`` and
``listens`` to, and the methods it ``provides`` / ``requires``. Namespacing is
enforced — a package may only emit/provide in its own ``{id}.*`` namespace, and
the reserved ``gravewright.*`` / ``core.*`` / ``system.*`` / ``sdk.*`` namespaces
are owned by the engine. Declared event/RPC schema paths must be safe
package-relative paths.

``sdk.bus`` is the only package-to-package communication surface in SDK 1.
"""

from __future__ import annotations

import re

from app.engine.sdk.package_paths import path_is_safe

RESERVED_NAMESPACES = ("gravewright", "core", "system", "sdk")

# A dotted event/method name with at least two segments, e.g.
# ``my-addon.inventory.changed`` or the RPC ``my-addon.getWeight``. Segments allow
# camelCase for method names; the leading (namespace) segment is the package id.
_NAME = re.compile(r"^[A-Za-z0-9]+(-[A-Za-z0-9]+)*(\.[A-Za-z0-9]+(-[A-Za-z0-9]+)*)+$")


def _interop_block(raw: dict) -> dict | None:
    block = raw.get("interop") if isinstance(raw, dict) else None
    return block if isinstance(block, dict) else None


def _root_namespace(name: str) -> str:
    return name.split(".", 1)[0]


def validate_interop_manifest(raw: dict) -> list[str]:
    """Validate the manifest ``interop`` block. Returns ``sdk.interop.*`` codes."""
    block = _interop_block(raw)
    if block is None:
        return []

    codes: list[str] = []
    package_id = raw.get("id") if isinstance(raw.get("id"), str) else ""

    def check_owned(section: str, schema_keys: tuple[str, ...]) -> None:
        entries = block.get(section)
        if entries is None:
            return
        if not isinstance(entries, dict):
            codes.append("sdk.interop.declaration_invalid")
            return
        for name, entry in entries.items():
            if not isinstance(name, str) or not _NAME.match(name):
                codes.append("sdk.interop.event_name_invalid")
                continue
            # Owned sections (emits/provides) must use the package namespace.
            if _root_namespace(name) in RESERVED_NAMESPACES or (
                package_id and _root_namespace(name) != package_id
            ):
                codes.append("sdk.interop.namespace_forbidden")
            _check_schema_paths(entry, schema_keys, codes)

    def check_external(section: str, schema_keys: tuple[str, ...]) -> None:
        entries = block.get(section)
        if entries is None:
            return
        if not isinstance(entries, dict):
            codes.append("sdk.interop.declaration_invalid")
            return
        for name, entry in entries.items():
            if not isinstance(name, str) or not _NAME.match(name):
                codes.append("sdk.interop.event_name_invalid")
                continue
            _check_schema_paths(entry, schema_keys, codes)

    # Owned: the package emits these events / provides these methods.
    check_owned("emits", ("schema",))
    check_owned("provides", ("params", "returns", "request", "response"))
    # External: the package listens to / requires others' events/methods.
    check_external("listens", ("schema",))
    check_external("requires", ())

    # De-duplicate, keep order.
    seen: set[str] = set()
    return [c for c in codes if not (c in seen or seen.add(c))]


def _check_schema_paths(entry: object, schema_keys: tuple[str, ...], codes: list[str]) -> None:
    if not isinstance(entry, dict):
        codes.append("sdk.interop.declaration_invalid")
        return
    for key in schema_keys:
        value = entry.get(key)
        if value is not None and not path_is_safe(value):
            codes.append("sdk.interop.schema_path_unsafe")


def interop_schema_paths(raw: dict) -> list[str]:
    """Every declared schema path in the interop block (for disk existence)."""
    block = _interop_block(raw)
    if block is None:
        return []
    paths: list[str] = []
    for section, keys in (
        ("emits", ("schema",)),
        ("listens", ("schema",)),
        ("provides", ("params", "returns", "request", "response")),
    ):
        entries = block.get(section)
        if not isinstance(entries, dict):
            continue
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            for key in keys:
                value = entry.get(key)
                if isinstance(value, str) and value and path_is_safe(value):
                    paths.append(value)
    return paths
