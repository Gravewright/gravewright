"""Sheet Data plane (System API v0, commands ``sheet.data.*``).

The full per-actor system data lives in scoped-json-v1 storage. This service is
the only sanctioned way to read/patch it: it enforces actor permissions, bumps
the data version, and reports the changed paths so realtime listeners (and the
token mapping layer in a later slice) can react.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sheets.schema_service import SchemaService
from app.engine.sheets.sheet_validation import sanitize_write
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass(frozen=True)
class SheetDataResult:
    success: bool
    actor_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    version: int | None = None
    data: dict | None = None
    changed_paths: list[str] = field(default_factory=list)
    error_key: str | None = None


def _set_path(data: dict, dotted_path: str, value: Any) -> None:
    """Set ``value`` at a dot-delimited path, creating intermediate dicts."""
    segments = [segment for segment in dotted_path.split(".") if segment]
    if not segments:
        return
    cursor = data
    for segment in segments[:-1]:
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    cursor[segments[-1]] = value


class SheetDataService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.schemas = SchemaService()
        self.rules = SystemRulesService()

    def get_data(self, *, actor_id: str, user_id: str) -> SheetDataResult:
        actor, campaign, error = self._load(actor_id, user_id, require_edit=False)
        if error is not None:
            return error
        envelope = self._read(actor)
        return SheetDataResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            version=int(envelope.get("version", 1)),
            data=envelope.get("data", {}),
        )

    def patch_data(
        self, *, actor_id: str, user_id: str, patch: dict[str, Any]
    ) -> SheetDataResult:
        actor, campaign, error = self._load(actor_id, user_id, require_edit=True)
        if error is not None:
            return error
        if not isinstance(patch, dict) or not patch:
            return SheetDataResult(success=False, error_key="game.sheet_data.errors.empty_patch")

                                                                                        
        schema = self.schemas.get_actor_schema(
            system_id=actor["system_id"], actor_type=actor["type"]
        )
        validation = self.rules.get_validation(actor["system_id"], actor["type"])
        clean, _rejected = sanitize_write(schema, validation, patch)
        if not clean:
            return SheetDataResult(success=False, error_key="game.sheet_data.errors.empty_patch")

        envelope = self._read(actor)
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        for path, value in clean.items():
            _set_path(data, str(path), value)

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor_id,
            version=version,
            data=data,
        )
        return SheetDataResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            version=version,
            data=data,
            changed_paths=sorted(clean),
        )

    def set_data(self, *, actor_id: str, user_id: str, data: dict) -> SheetDataResult:
        actor, campaign, error = self._load(actor_id, user_id, require_edit=True)
        if error is not None:
            return error
        if not isinstance(data, dict):
            return SheetDataResult(success=False, error_key="game.sheet_data.errors.invalid_data")

        envelope = self._read(actor)
        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor_id,
            version=version,
            data=data,
        )
        return SheetDataResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            version=version,
            data=data,
            changed_paths=["*"],
        )

                                                                                

    def _read(self, actor: dict) -> dict:
        envelope = self.storage.read_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor["id"],
        )
        if envelope is None:
            return {"version": 1, "data": {}}
        return envelope

    def _load(
        self, actor_id: str, user_id: str, *, require_edit: bool
    ) -> tuple[dict | None, dict | None, SheetDataResult | None]:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return None, None, SheetDataResult(success=False, error_key="game.actors.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return None, None, SheetDataResult(success=False, error_key="game.actors.errors.not_found")
        campaign_dict = dict(campaign)
        allowed = (
            can_edit_actor(actor=actor, campaign=campaign_dict, user_id=user_id)
            if require_edit
            else can_view_actor(actor=actor, campaign=campaign_dict, user_id=user_id)
        )
        if not allowed:
            return None, None, SheetDataResult(success=False, error_key="game.actors.errors.not_allowed")
        return actor, campaign_dict, None
