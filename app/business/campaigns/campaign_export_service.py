from __future__ import annotations

import base64
import hashlib
import io
import json
import time
import zipfile
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.persistence.database import engine_connect
from app.persistence.tables import (
    actor_folders, actors_core, campaign_members, campaign_packages,
    campaign_permission_overrides, campaigns, item_folders, items_core,
    journal_folders, journals, quest_board_entries, scene_groups, scene_layers, scenes,
)

FORMAT = "gravewright.campaign-export"
FORMAT_VERSION = 1
FORBIDDEN_KEY_PARTS = (
    "email", "password", "token", "secret", "cookie", "session", "code_hash", "csrf",
    "user_id", "owner_user", "created_by", "enabled_by", "imported_by",
)
EXCLUDED_COLUMNS = {
    "owner_user_id", "created_by_user_id", "enabled_by_user_id", "imported_by_user_id",
}
OPTION_TABLES = {
    "packages": (campaign_packages,),
    "settings": (campaign_permission_overrides,),
    "scenes": (scene_groups, scenes),
    "actors": (actor_folders, actors_core),
    "items": (item_folders, items_core),
    "journals": (journal_folders, journals),
}


@dataclass(frozen=True)
class CampaignExportOptions:
    packages: bool = True
    scenes: bool = True
    actors: bool = True
    items: bool = True
    journals: bool = True
    settings: bool = True


@dataclass(frozen=True)
class CampaignExportResult:
    success: bool
    archive: bytes | None = None
    filename: str | None = None
    manifest: dict[str, Any] = field(default_factory=dict)
    error_key: str | None = None


class CampaignExportService:
    def export(self, *, campaign_id: str, user_id: str,
               options: CampaignExportOptions) -> CampaignExportResult:
        with engine_connect() as connection:
            campaign = connection.execute(
                select(campaigns).join(
                    campaign_members, campaign_members.c.campaign_id == campaigns.c.id
                ).where(
                    campaigns.c.id == campaign_id,
                    campaign_members.c.user_id == user_id,
                    campaign_members.c.role == "gm",
                )
            ).mappings().first()
            if campaign is None:
                return CampaignExportResult(False, error_key="campaign.export.errors.denied")
            payload = {
                "format": FORMAT,
                "version": FORMAT_VERSION,
                "campaign": self._clean_row(dict(campaign), drop={"id"}),
                "content": {},
            }
            counts = {}
            selected = []
            for option, tables in OPTION_TABLES.items():
                if not getattr(options, option):
                    continue
                selected.append(option)
                for table in tables:
                    rows = self._campaign_rows(connection, table, campaign_id)
                    payload["content"][table.name] = [self._clean_row(row) for row in rows]
                    counts[table.name] = len(rows)
            if options.scenes:
                scene_ids = [row["id"] for row in payload["content"].get("scenes", [])]
                layers = [] if not scene_ids else [dict(row) for row in connection.execute(
                    select(scene_layers).where(scene_layers.c.scene_id.in_(scene_ids))
                ).mappings()]
                payload["content"]["scene_layers"] = [self._clean_row(row) for row in layers]
                counts["scene_layers"] = len(layers)
            if options.journals:
                journal_ids = {row["id"] for row in payload["content"].get("journals", [])}
                board_rows = [dict(row) for row in connection.execute(
                    select(quest_board_entries).where(
                        quest_board_entries.c.board_id.in_(journal_ids)
                    )
                ).mappings()] if journal_ids else []
                payload["content"]["quest_board_entries"] = [
                    self._clean_row(row) for row in board_rows if row["quest_id"] in journal_ids
                ]
                counts["quest_board_entries"] = len(payload["content"]["quest_board_entries"])

        payload_json = self._canonical(payload).encode("utf-8")
        payload_checksum = hashlib.sha256(payload_json).hexdigest()
        manifest = {
            "format": FORMAT, "version": FORMAT_VERSION,
            "created_at": int(time.time()), "selected": selected, "counts": counts,
            "files": {"campaign.json": {"sha256": payload_checksum, "bytes": len(payload_json)}},
            "excluded": [
                "users", "members", "invitations", "join_codes", "sessions", "passwords",
                "emails", "streamer_links", "presence", "chat", "audit", "user_permissions",
                "ownership", "handout_grants", "lobby_state", "package_settings", "physical_assets",
            ],
        }
        manifest_json = self._canonical(manifest).encode("utf-8")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", manifest_json)
            archive.writestr("campaign.json", payload_json)
        archive_bytes = output.getvalue()
        if not self.validate(archive_bytes):
            return CampaignExportResult(False, error_key="campaign.export.errors.validation")
        filename = f"gravewright-{self._slug(str(campaign['title']))}-{int(time.time())}.gwcampaign"
        return CampaignExportResult(True, archive=archive_bytes, filename=filename, manifest=manifest)

    @classmethod
    def validate(cls, archive_bytes: bytes) -> bool:
        try:
            with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
                if set(archive.namelist()) != {"manifest.json", "campaign.json"}:
                    return False
                manifest = json.loads(archive.read("manifest.json"))
                payload = archive.read("campaign.json")
                parsed = json.loads(payload)
            expected = manifest["files"]["campaign.json"]
            return (
                manifest["format"] == FORMAT
                and manifest["version"] == FORMAT_VERSION
                and parsed["format"] == FORMAT
                and hashlib.sha256(payload).hexdigest() == expected["sha256"]
                and len(payload) == expected["bytes"]
                and not cls._contains_forbidden_key(parsed)
            )
        except (KeyError, TypeError, ValueError, zipfile.BadZipFile):
            return False

    @staticmethod
    def _campaign_rows(connection, table, campaign_id: str) -> list[dict]:
        rows = connection.execute(select(table).where(table.c.campaign_id == campaign_id)).mappings()
        if table is campaign_permission_overrides:
            return [dict(row) for row in rows if row["subject_type"] == "role"]
        return [dict(row) for row in rows]

    @classmethod
    def _clean_row(cls, row: dict, drop: set[str] | None = None) -> dict:
        dropped = EXCLUDED_COLUMNS | (drop or set())
        return {
            key: cls._sanitize_value(key, value)
            for key, value in row.items()
            if key not in dropped and not any(part in key.lower() for part in FORBIDDEN_KEY_PARTS)
        }

    @classmethod
    def _contains_forbidden_key(cls, value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                any(part in str(key).lower() for part in FORBIDDEN_KEY_PARTS)
                or cls._contains_forbidden_key(child)
                for key, child in value.items()
            )
        if isinstance(value, list):
            return any(cls._contains_forbidden_key(child) for child in value)
        if isinstance(value, str) and value[:1] in {"{", "["}:
            try:
                return cls._contains_forbidden_key(json.loads(value))
            except (TypeError, ValueError):
                return False
        return False

    @classmethod
    def _sanitize_value(cls, key: str, value: Any) -> Any:
        if isinstance(value, str) and (key.endswith("_json") or key in {"data", "metadata"}):
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                return value
            return cls._canonical(cls._scrub(parsed))
        return cls._encode(value)

    @classmethod
    def _scrub(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: cls._scrub(child)
                for key, child in value.items()
                if not any(part in str(key).lower() for part in FORBIDDEN_KEY_PARTS)
            }
        if isinstance(value, list):
            return [cls._scrub(child) for child in value]
        return cls._encode(value)

    @staticmethod
    def _encode(value: Any) -> Any:
        if isinstance(value, (bytes, bytearray, memoryview)):
            return {"$base64": base64.b64encode(bytes(value)).decode("ascii")}
        return value

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _slug(value: str) -> str:
        slug = "".join(char.lower() if char.isalnum() else "-" for char in value)
        return "-".join(part for part in slug.split("-") if part)[:60] or "campaign"
