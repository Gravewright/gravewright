from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.business.audit.catalog import CATALOG_VERSION, EVENT_METADATA_KEYS, safe_metadata
from app.config import config
from app.persistence.repositories.audit_event_repository import AuditEventRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass(frozen=True)
class AuditResult:
    success: bool
    events: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    error_key: str | None = None


class AuditService:
    def __init__(self) -> None:
        self.repository = AuditEventRepository()
        self.campaigns = CampaignRepository()

    def record(self, *, campaign_id: str, actor_user_id: str | None, event_type: str,
               subject_type: str | None = None, subject_id: str | None = None,
               action: str, result: str, metadata: dict | None = None,
               connection=None, now: int | None = None, required: bool = False) -> dict | None:
        if not config.administrative_audit_enabled and not required:
            return None
        safe = safe_metadata(event_type, metadata)
        row = {
            "id": uuid.uuid4().hex,
            "campaign_id": campaign_id,
            "actor_user_id": actor_user_id,
            "catalog_version": CATALOG_VERSION,
            "event_type": event_type,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "action": action[:191],
            "result": result[:191],
            "metadata_json": json.dumps(safe, sort_keys=True, separators=(",", ":")),
            "created_at": int(time.time()) if now is None else now,
        }
        return self.repository.append(row, connection=connection)

    def list(self, *, campaign_id: str, user_id: str, event_type: str | None = None,
             page: int = 1, page_size: int = 50) -> AuditResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return AuditResult(False, error_key="audit.errors.denied")
        if event_type and event_type not in EVENT_METADATA_KEYS:
            return AuditResult(False, error_key="audit.errors.invalid_filter")
        safe_page = max(1, int(page))
        safe_size = max(1, min(int(page_size), 100))
        rows, total = self.repository.page(
            campaign_id=campaign_id, event_type=event_type,
            offset=(safe_page - 1) * safe_size, limit=safe_size,
        )
        events = []
        for row in rows:
            public = dict(row)
            public["metadata"] = json.loads(public.pop("metadata_json"))
            events.append(public)
        return AuditResult(True, events=events, total=total)

    def prune(self, *, now: int | None = None) -> int:
        timestamp = int(time.time()) if now is None else now
        cutoff = timestamp - max(1, config.administrative_audit_retention_days) * 86400
        return self.repository.prune_before(cutoff)

    def export(
        self, *, campaign_id: str, user_id: str, event_type: str | None = None
    ) -> AuditResult:
        if self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) != "gm":
            return AuditResult(False, error_key="audit.errors.denied")
        if event_type and event_type not in EVENT_METADATA_KEYS:
            return AuditResult(False, error_key="audit.errors.invalid_filter")
        rows, total = self.repository.page(
            campaign_id=campaign_id, event_type=event_type, offset=0, limit=10_000
        )
        events = []
        for row in rows:
            events.append(
                {
                    "catalog_version": row["catalog_version"],
                    "event_type": row["event_type"],
                    "actor_user_id": row["actor_user_id"],
                    "subject_type": row["subject_type"],
                    "subject_id": row["subject_id"],
                    "action": row["action"],
                    "result": row["result"],
                    "metadata": json.loads(row["metadata_json"]),
                    "created_at": row["created_at"],
                }
            )
        return AuditResult(True, events=events, total=total)
