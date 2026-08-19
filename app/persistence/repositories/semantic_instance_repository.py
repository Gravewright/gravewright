"""Persistence for live semantic instances: workflows, flows and timelines."""
from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from app.persistence.database import all_dicts, engine_begin
from app.persistence.tables import sdk_semantic_instances


class SemanticInstanceRepository:
    """Atomic persistence for live semantic instances.

    An instance is the durable, server-owned side of a semantic contract:
    workflows, gameplay flows and timelines all suspend and recover through
    this row, so a package never holds that state itself.
    """

    def create(self, values: dict) -> dict:
        now = int(time.time())
        values = dict(values)
        payload = values.pop("payload")
        stored = {
            **values,
            "id": str(values.get("id") or uuid.uuid4().hex),
            "payload_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        try:
            with engine_begin() as conn:
                conn.execute(insert(sdk_semantic_instances).values(**stored))
        except IntegrityError:
            prior=self.by_idempotency(stored["campaign_id"],stored["package_id"],stored["domain"],stored.get("idempotency_key")) if stored.get("idempotency_key") else None
            if prior:return prior
            raise
        return self.get(stored["id"])

    def get(self, instance_id: str) -> dict | None:
        with engine_begin() as conn:
            row = conn.execute(select(sdk_semantic_instances).where(sdk_semantic_instances.c.id == instance_id)).mappings().first()
        return self._row(row)

    def by_idempotency(self, campaign_id: str, package_id: str, domain: str, key: str) -> dict | None:
        with engine_begin() as conn:
            row = conn.execute(select(sdk_semantic_instances).where(
                sdk_semantic_instances.c.campaign_id == campaign_id,
                sdk_semantic_instances.c.package_id == package_id,
                sdk_semantic_instances.c.domain == domain,
                sdk_semantic_instances.c.idempotency_key == key,
            )).mappings().first()
        return self._row(row)

    def list(self, campaign_id: str, domain: str, package_id: str | None = None) -> list[dict]:
        stmt = select(sdk_semantic_instances).where(
            sdk_semantic_instances.c.campaign_id == campaign_id,
            sdk_semantic_instances.c.domain == domain,
        )
        if package_id:
            stmt = stmt.where(sdk_semantic_instances.c.package_id == package_id)
        with engine_begin() as conn:
            rows = all_dicts(conn.execute(stmt.order_by(sdk_semantic_instances.c.created_at, sdk_semantic_instances.c.id)))
        return [self._row(row) for row in rows]

    def due_campaigns(self, now: int) -> list[str]:
        with engine_begin() as conn:
            rows = conn.execute(select(sdk_semantic_instances.c.campaign_id).where(
                sdk_semantic_instances.c.status.in_(["RUNNING", "WAITING_TIME", "WAITING_INTERACTION", "ACTIVE"]),
                (sdk_semantic_instances.c.wake_at.is_(None)) | (sdk_semantic_instances.c.wake_at <= now),
            ).distinct()).all()
        return [str(row[0]) for row in rows]

    def patch(self, instance_id: str, expected_version: int | None, *, payload: dict | None = None, **values) -> dict | None:
        stmt = update(sdk_semantic_instances).where(sdk_semantic_instances.c.id == instance_id)
        if expected_version is not None:
            stmt = stmt.where(sdk_semantic_instances.c.version == expected_version)
        if payload is not None:
            values["payload_json"] = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        values.update(version=sdk_semantic_instances.c.version + 1, updated_at=int(time.time()))
        with engine_begin() as conn:
            changed = conn.execute(stmt.values(**values)).rowcount
        return self.get(instance_id) if changed == 1 else None

    def fail_closed_package(self, campaign_id: str, package_id: str) -> list[dict]:
        terminal = {"COMPLETED", "CANCELLED", "FAILED"}
        changed = []
        for row in self.list(campaign_id, "workflow", package_id) + self.list(campaign_id, "timeline", package_id) + self.list(campaign_id, "gameplay-flow", package_id):
            if row["status"] in terminal:
                continue
            value = self.patch(row["id"], row["version"], status="CANCELLED", waiting_on=None, wake_at=None,
                               payload={**row["payload"], "completionReason": "package-unload"})
            if value:
                changed.append(value)
        return changed

    def fail_closed_scene(self, campaign_id: str, scene_id: str) -> list[dict]:
        changed=[]
        for domain in ("workflow","gameplay-flow","timeline"):
            for row in self.list(campaign_id,domain):
                if row["scene_id"]!=scene_id or row["status"] in {"COMPLETED","CANCELLED","FAILED"}:continue
                value=self.patch(row["id"],row["version"],status="CANCELLED",waiting_on=None,wake_at=None,payload={**row["payload"],"completionReason":"scene-deleted"})
                if value:changed.append(value)
        return changed

    @staticmethod
    def _row(row):
        if not row:
            return None
        value = dict(row)
        value["payload"] = json.loads(value.pop("payload_json") or "{}")
        return value
