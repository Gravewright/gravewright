from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, update

from app.business.audit import AuditService
from app.business.campaigns.campaign_state_snapshot import CampaignStateSnapshot
from app.persistence.database import engine_begin
from app.config import config
from app.persistence.repositories.campaign_snapshot_repository import CampaignSnapshotRepository
from app.persistence.tables import campaign_members, campaigns, scene_layers, scenes

FORMAT_VERSION = 2
CAMPAIGN_FIELDS = (
    "title", "description", "active_system_id", "initial_state_json",
    "persistent_state_json", "state_version",
)
SCENE_FIELDS = (
    "group_id", "name", "status", "visibility", "active", "width", "height", "tile_size",
    "grid_size", "scene_format_version", "chunk_size", "grid_visible", "grid_color",
    "grid_opacity", "darkness", "image_scale", "start_world_x", "start_world_y", "start_zoom",
    "tile_table_version", "scene_epoch", "fog_enabled", "fog_mask", "fog_baseline", "fog_ops_json",
    "fog_version", "board_area_markers_json", "board_version",
)
LAYER_FIELDS = (
    "name", "kind", "visibility", "display_order", "encoding", "tile_table_version",
    "max_lod", "tile_index_version",
)


@dataclass(frozen=True)
class SnapshotResult:
    success: bool
    snapshot: dict[str, Any] | None = None
    preview: dict[str, Any] = field(default_factory=dict)
    error_key: str | None = None


class CampaignSnapshotService:
    def __init__(self) -> None:
        self.repository = CampaignSnapshotRepository()
        self.audit = AuditService()
        self.state = CampaignStateSnapshot()

    def create(self, *, campaign_id: str, user_id: str, name: str, description: str = "", kind: str = "manual", connection=None) -> SnapshotResult:
        normalized = " ".join(name.strip().split())
        if not 2 <= len(normalized) <= 120:
            return SnapshotResult(False, error_key="campaign.snapshot.errors.invalid_name")
        if connection is None:
            with engine_begin() as own_connection:
                return self._create(own_connection, campaign_id, user_id, normalized, description, kind)
        return self._create(connection, campaign_id, user_id, normalized, description, kind)

    def _create(self, connection, campaign_id: str, user_id: str, name: str, description: str, kind: str) -> SnapshotResult:
        campaign = self._campaign_for_gm(connection, campaign_id, user_id)
        if campaign is None:
            return SnapshotResult(False, error_key="campaign.snapshot.errors.denied")
        payload = self._capture(connection, campaign)
        payload_json = self._canonical(payload)
        tables = payload.get("state", {}).get("tables", {})
        manifest = {
            "format": "gravewright.campaign-snapshot",
            "version": FORMAT_VERSION,
            "scope": ["complete_campaign_state", "physical_files"],
            "excluded": ["accounts", "sessions", "snapshot_history", "audit_log", "live_presence", "transport_queue"],
            "counts": {name: len(rows) for name, rows in tables.items()},
        }
        now = int(time.time())
        row = self.repository.create({
            "id": uuid.uuid4().hex, "campaign_id": campaign_id, "created_by_user_id": user_id,
            "name": name, "description": description.strip()[:1000], "kind": kind,
            "format_version": FORMAT_VERSION, "manifest_json": self._canonical(manifest),
            "payload_json": payload_json, "checksum": hashlib.sha256(payload_json.encode()).hexdigest(),
            "created_at": now,
        }, connection=connection)
        self.repository.prune(
            campaign_id,
            max(1, config.campaign_snapshot_retention),
            connection=connection,
        )
        self.audit.record(
            campaign_id=campaign_id,
            actor_user_id=user_id,
            event_type="snapshot.created",
            subject_type="snapshot",
            subject_id=row["id"],
            action="create",
            result="success",
            metadata={"kind": kind, "format_version": FORMAT_VERSION},
            connection=connection,
            now=now,
        )
        return SnapshotResult(True, snapshot=self._public(row))

    def list_for_campaign(self, *, campaign_id: str, user_id: str) -> SnapshotResult:
        with engine_begin() as connection:
            if self._campaign_for_gm(connection, campaign_id, user_id) is None:
                return SnapshotResult(False, error_key="campaign.snapshot.errors.denied")
        rows = self.repository.list_for_campaign(campaign_id)
        return SnapshotResult(
            True,
            preview={"snapshots": [self._public(row) for row in rows]},
        )

    def delete(self, *, snapshot_id: str, campaign_id: str, user_id: str) -> SnapshotResult:
        with engine_begin() as connection:
            if self._campaign_for_gm(connection, campaign_id, user_id) is None:
                return SnapshotResult(False, error_key="campaign.snapshot.errors.denied")
            row = self.repository.get(snapshot_id, connection=connection)
            if row is None or row["campaign_id"] != campaign_id:
                return SnapshotResult(False, error_key="campaign.snapshot.errors.not_found")
        deleted = self.repository.delete(snapshot_id, campaign_id)
        if deleted:
            self.audit.record(
                campaign_id=campaign_id,
                actor_user_id=user_id,
                event_type="snapshot.deleted",
                subject_type="snapshot",
                subject_id=snapshot_id,
                action="delete",
                result="success",
                metadata={"kind": row["kind"]},
            )
        return SnapshotResult(deleted, error_key=None if deleted else "campaign.snapshot.errors.not_found")

    def preview(self, *, snapshot_id: str, campaign_id: str, user_id: str) -> SnapshotResult:
        with engine_begin() as connection:
            campaign = self._campaign_for_gm(connection, campaign_id, user_id)
            row = self.repository.get(snapshot_id, connection=connection)
            checked = self._validate(row, campaign_id)
            if campaign is None:
                return SnapshotResult(False, error_key="campaign.snapshot.errors.denied")
            if isinstance(checked, str):
                return SnapshotResult(False, error_key=checked)
            current_ids = set(connection.execute(select(scenes.c.id).where(scenes.c.campaign_id == campaign_id)).scalars())
            saved_scenes = (
                checked.get("state", {}).get("tables", {}).get("scenes", [])
                if int(row["format_version"]) >= 2
                else checked.get("scenes", [])
            )
            saved_ids = {item["id"] for item in saved_scenes}
            preview = {
                "scenes_restored": len(current_ids & saved_ids),
                "missing_scenes": len(saved_ids - current_ids),
                "safety_snapshot": True,
            }
            preview[
                "new_scenes_removed" if int(row["format_version"]) >= 2 else "new_scenes_untouched"
            ] = len(current_ids - saved_ids)
            return SnapshotResult(True, snapshot=self._public(row), preview=preview)

    def restore(self, *, snapshot_id: str, campaign_id: str, user_id: str) -> SnapshotResult:
        with engine_begin() as connection:
            campaign = self._campaign_for_gm(connection, campaign_id, user_id, lock=True)
            if campaign is None:
                return SnapshotResult(False, error_key="campaign.snapshot.errors.denied")
            row = self.repository.get(snapshot_id, connection=connection)
            payload = self._validate(row, campaign_id)
            if isinstance(payload, str):
                return SnapshotResult(False, error_key=payload)
            safety = self._create(connection, campaign_id, user_id, f"Before restore: {row['name']}", "Automatic recovery point", "safety")
            now = int(time.time())
            if int(row["format_version"]) >= 2:
                counts = self.state.restore(connection, campaign_id, payload["state"])
                restored = counts.get("scenes", 0)
                restored_layers = counts.get("scene_layers", 0)
            else:
                connection.execute(update(campaigns).where(campaigns.c.id == campaign_id).values(**payload["campaign"], updated_at=now))
                restored = 0
                for item in payload["scenes"]:
                    values = {key: self._decode(item[key]) for key in SCENE_FIELDS if key in item}
                    result = connection.execute(update(scenes).where(scenes.c.id == item["id"]).where(scenes.c.campaign_id == campaign_id).values(**values, updated_at=now))
                    restored += int(result.rowcount or 0)
                restored_layers = 0
                for item in payload["layers"]:
                    values = {key: self._decode(item[key]) for key in LAYER_FIELDS if key in item}
                    result = connection.execute(
                        update(scene_layers)
                        .where(scene_layers.c.id == item["id"])
                        .where(scene_layers.c.scene_id.in_(select(scenes.c.id).where(scenes.c.campaign_id == campaign_id)))
                        .values(**values, updated_at=now)
                    )
                    restored_layers += int(result.rowcount or 0)
            self.audit.record(
                campaign_id=campaign_id,
                actor_user_id=user_id,
                event_type="snapshot.restored",
                subject_type="snapshot",
                subject_id=snapshot_id,
                action="restore",
                result="success",
                metadata={
                    "safety_snapshot_id": safety.snapshot["id"],
                    "scenes_restored": restored,
                },
                connection=connection,
                now=now,
            )
            return SnapshotResult(True, snapshot=self._public(row), preview={
                "scenes_restored": restored,
                "layers_restored": restored_layers,
                "safety_snapshot_id": safety.snapshot["id"],
            })

    def _capture(self, connection, campaign: dict) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "state": self.state.capture(connection, str(campaign["id"])),
        }

    def _validate(self, row: dict | None, campaign_id: str):
        if row is None or row["campaign_id"] != campaign_id:
            return "campaign.snapshot.errors.not_found"
        if int(row["format_version"]) not in {1, FORMAT_VERSION}:
            return "campaign.snapshot.errors.incompatible"
        if hashlib.sha256(row["payload_json"].encode()).hexdigest() != row["checksum"]:
            return "campaign.snapshot.errors.checksum"
        try:
            payload = json.loads(row["payload_json"])
        except (TypeError, ValueError):
            return "campaign.snapshot.errors.checksum"
        return payload

    @staticmethod
    def _campaign_for_gm(connection, campaign_id: str, user_id: str, lock: bool = False):
        statement = select(campaigns).join(campaign_members, campaign_members.c.campaign_id == campaigns.c.id).where(campaigns.c.id == campaign_id, campaign_members.c.user_id == user_id, campaign_members.c.role == "gm")
        if lock and connection.dialect.name != "sqlite": statement = statement.with_for_update()
        row = connection.execute(statement).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

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

    @staticmethod
    def _public(row: dict) -> dict:
        return {key: row[key] for key in ("id", "campaign_id", "created_by_user_id", "name", "description", "kind", "format_version", "checksum", "created_at")}
