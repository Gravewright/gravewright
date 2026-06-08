"""Loads an actor/item type's JSON Schema from its system package (System API v0).

The schema is the authoring surface a system designer writes to declare the shape
of an entity's Sheet Data: field types, ``default`` values, and ``readOnly`` flags.
It is read on demand (small files) and used by :mod:`app.engine.sheets.sheet_validation`
to seed defaults at creation and to coerce/guard writes. Mirrors
:class:`SystemLayoutService` — same safe package-path resolution.
"""

from __future__ import annotations

import json

from app.engine.systems import system_loader
from app.engine.systems.system_loader import safe_join
from app.engine.systems.system_manifest import SystemManifest
from app.persistence.repositories.installed_system_repository import InstalledSystemRepository


class SchemaService:
    def __init__(self) -> None:
        self.installed = InstalledSystemRepository()

    def get_actor_schema(self, *, system_id: str, actor_type: str) -> dict | None:
        return self._get_schema(system_id=system_id, type_id=actor_type, kind="actor")

    def get_item_schema(self, *, system_id: str, item_type: str) -> dict | None:
        return self._get_schema(system_id=system_id, type_id=item_type, kind="item")

    def _get_schema(self, *, system_id: str, type_id: str, kind: str) -> dict | None:
        record = self.installed.get(system_id)
        if record is None:
            return None
        try:
            manifest = SystemManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None

        type_defs = manifest.item_types if kind == "item" else manifest.actor_types
        schema_path = ""
        for type_def in type_defs:
            if type_def.id == type_id:
                schema_path = type_def.schema
                break
        if not schema_path:
            return None

        base = system_loader.SYSTEMS_DIR / record["package_dir"]
        path = safe_join(base, schema_path)
        if path is None or not path.is_file():
            return None
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return schema if isinstance(schema, dict) else None
