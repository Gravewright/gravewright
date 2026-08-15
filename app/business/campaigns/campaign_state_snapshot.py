from __future__ import annotations

import base64
import shutil
from typing import Any

from sqlalchemy import and_, delete, insert, or_, select, update

from app.persistence.database import database_storage_root
from app.persistence.tables import campaigns, metadata


EXCLUDED_TABLES = {
    "audit_events",
    "campaign_snapshots",
    "campaign_presence",
    "room_event_log",
    "transport_messages",
    "campaign_delete_codes",
}


class CampaignStateSnapshot:
    """Capture and restore the complete persistent state owned by one campaign."""

    def capture(self, connection, campaign_id: str) -> dict[str, Any]:
        rows = self._collect(connection, campaign_id)
        scene_ids = {str(row["id"]) for row in rows.get("scenes", [])}
        return {
            "tables": {
                name: [self._encode_row(row) for row in table_rows]
                for name, table_rows in rows.items()
            },
            "files": self._capture_files(campaign_id, scene_ids),
        }

    def restore(self, connection, campaign_id: str, state: dict[str, Any]) -> dict[str, int]:
        saved = state.get("tables")
        if not isinstance(saved, dict) or "campaigns" not in saved:
            raise ValueError("invalid campaign state")
        decoded = {
            name: [self._decode_row(row) for row in rows]
            for name, rows in saved.items()
            if name in metadata.tables and name not in EXCLUDED_TABLES and isinstance(rows, list)
        }
        current = self._collect(connection, campaign_id)
        ordered = [table for table in metadata.sorted_tables if table.name in decoded]
        for table in reversed(ordered):
            if table is campaigns:
                continue
            identities = current.get(table.name, [])
            condition = self._identity_condition(table, identities)
            if condition is not None:
                connection.execute(delete(table).where(condition))

        campaign_rows = decoded.get("campaigns", [])
        if len(campaign_rows) != 1:
            raise ValueError("invalid campaign row")
        campaign = campaign_rows[0]
        values = {
            key: value
            for key, value in campaign.items()
            if key in campaigns.c and key not in {"id", "owner_user_id", "created_at"}
        }
        connection.execute(update(campaigns).where(campaigns.c.id == campaign_id).values(**values))

        counts: dict[str, int] = {}
        for table in ordered:
            if table is campaigns:
                continue
            rows = decoded.get(table.name, [])
            for row in rows:
                if "campaign_id" in table.c:
                    row["campaign_id"] = campaign_id
                if "room_id" in table.c and row.get("room_id") == campaign.get("id"):
                    row["room_id"] = campaign_id
                connection.execute(insert(table).values(**{
                    key: value for key, value in row.items() if key in table.c
                }))
            counts[table.name] = len(rows)
        self._restore_files(campaign_id, current, decoded, state.get("files", {}))
        return counts

    def _collect(self, connection, campaign_id: str) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {
            "campaigns": [dict(connection.execute(
                select(campaigns).where(campaigns.c.id == campaign_id)
            ).mappings().one())]
        }
        scoped_tables = {"campaigns"}
        for table in metadata.sorted_tables:
            if table is campaigns or table.name in EXCLUDED_TABLES:
                continue
            criteria = []
            if "campaign_id" in table.c:
                criteria.append(table.c.campaign_id == campaign_id)
                scoped_tables.add(table.name)
            if "room_id" in table.c:
                criteria.append(table.c.room_id == campaign_id)
                scoped_tables.add(table.name)
            for column in table.c:
                for foreign_key in column.foreign_keys:
                    parent_name = foreign_key.column.table.name
                    if parent_name in scoped_tables:
                        scoped_tables.add(table.name)
                    parent_rows = result.get(parent_name, [])
                    values = {
                        row.get(foreign_key.column.name)
                        for row in parent_rows
                        if row.get(foreign_key.column.name) is not None
                    }
                    if values:
                        criteria.append(column.in_(values))
            if table.name not in scoped_tables:
                continue
            rows = [] if not criteria else [dict(row) for row in connection.execute(
                select(table).where(or_(*criteria))
            ).mappings()]
            result[table.name] = rows
        return result

    @staticmethod
    def _identity_condition(table, rows):
        primary = list(table.primary_key.columns)
        if not primary or not rows:
            return None
        identities = []
        for row in rows:
            identities.append(and_(*[column == row[column.name] for column in primary]))
        return or_(*identities)

    @classmethod
    def _encode_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        return {key: cls._encode(value) for key, value in row.items()}

    @classmethod
    def _decode_row(cls, row: Any) -> dict[str, Any]:
        if not isinstance(row, dict):
            raise ValueError("invalid row")
        return {key: cls._decode(value) for key, value in row.items()}

    @staticmethod
    def _encode(value: Any) -> Any:
        if isinstance(value, (bytes, bytearray, memoryview)):
            return {"$base64": base64.b64encode(bytes(value)).decode("ascii")}
        return value

    @staticmethod
    def _decode(value: Any) -> Any:
        if isinstance(value, dict) and set(value) == {"$base64"}:
            return base64.b64decode(value["$base64"], validate=True)
        return value

    def _capture_files(self, campaign_id: str, scene_ids: set[str]) -> dict[str, str]:
        root = database_storage_root().resolve()
        candidates = [
            root / "library-assets" / campaign_id,
            root / "actor-assets" / campaign_id,
            root / "journal-assets" / campaign_id,
        ]
        candidates.extend((root / "scenes" / scene_id) for scene_id in scene_ids)
        candidates.extend((root / "system-data").glob(f"*/campaigns/{campaign_id}"))
        files: dict[str, str] = {}
        for directory in candidates:
            if not directory.is_dir():
                continue
            for path in directory.rglob("*"):
                if path.is_file():
                    files[path.relative_to(root).as_posix()] = base64.b64encode(path.read_bytes()).decode("ascii")
        return files

    def _restore_files(self, campaign_id: str, current: dict[str, list[dict]], tables: dict[str, list[dict]], files: Any) -> None:
        if not isinstance(files, dict):
            raise ValueError("invalid files")
        root = database_storage_root().resolve()
        scene_ids = {str(row["id"]) for row in tables.get("scenes", [])}
        scene_ids.update(str(row["id"]) for row in current.get("scenes", []))
        targets = [
            root / "library-assets" / campaign_id,
            root / "actor-assets" / campaign_id,
            root / "journal-assets" / campaign_id,
        ]
        targets.extend((root / "scenes" / scene_id) for scene_id in scene_ids)
        targets.extend((root / "system-data").glob(f"*/campaigns/{campaign_id}"))
        for target in targets:
            if target.is_dir():
                shutil.rmtree(target)
        for relative, encoded in files.items():
            destination = (root / str(relative)).resolve()
            if root not in destination.parents:
                raise ValueError("unsafe snapshot path")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(base64.b64decode(encoded, validate=True))
