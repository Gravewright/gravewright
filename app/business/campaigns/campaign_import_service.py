from __future__ import annotations

import base64
import binascii
import io
import json
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.business.campaigns.campaign_export_service import CampaignExportService
from app.persistence.database import engine_begin
from app.persistence.tables import (
    actor_folders,
    actors_core,
    campaign_members,
    campaign_packages,
    campaign_permission_overrides,
    campaigns,
    installed_packages,
    item_folders,
    items_core,
    journal_folders,
    journals,
    quest_board_entries,
    scene_groups,
    scene_layers,
    scenes,
)

MAX_CAMPAIGN_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_CAMPAIGN_JSON_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True)
class CampaignImportResult:
    success: bool
    campaign_id: str | None = None
    summary: dict[str, int] = field(default_factory=dict)
    error_key: str | None = None


class CampaignImportService:
    """Validate and transactionally restore a portable campaign export."""

    def import_archive(
        self, *, archive: bytes, user_id: str, title: str = ""
    ) -> CampaignImportResult:
        if not archive or len(archive) > MAX_CAMPAIGN_ARCHIVE_BYTES:
            return self._invalid()
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                info = bundle.getinfo("campaign.json")
                if info.file_size > MAX_CAMPAIGN_JSON_BYTES:
                    return self._invalid()
                if not CampaignExportService.validate(archive):
                    return self._invalid()
                payload = json.loads(bundle.read(info))
        except (KeyError, TypeError, ValueError, zipfile.BadZipFile):
            return self._invalid()

        source_campaign = payload.get("campaign")
        content = payload.get("content")
        if not isinstance(source_campaign, dict) or not isinstance(content, dict):
            return self._invalid()
        imported_title = " ".join((title.strip() or str(source_campaign.get("title") or "")).split())
        if not 2 <= len(imported_title) <= 120:
            return CampaignImportResult(False, error_key="campaign.import.errors.invalid_title")

        now = int(time.time())
        campaign_id = uuid.uuid4().hex
        summary: dict[str, int] = {}
        try:
            with engine_begin() as connection:
                available_packages = set(
                    connection.execute(select(installed_packages.c.id)).scalars()
                )
                exported_packages = self._rows(content, campaign_packages.name)
                active_system_id = source_campaign.get("active_system_id")
                if active_system_id not in available_packages:
                    active_system_id = None
                connection.execute(insert(campaigns).values(
                    id=campaign_id,
                    owner_user_id=user_id,
                    title=imported_title,
                    description=str(source_campaign.get("description") or "")[:2000],
                    active_system_id=active_system_id,
                    initial_state_json=str(source_campaign.get("initial_state_json") or "{}"),
                    persistent_state_json=str(source_campaign.get("persistent_state_json") or "{}"),
                    state_version=int(source_campaign.get("state_version") or 1),
                    created_at=now,
                    updated_at=now,
                ))
                connection.execute(insert(campaign_members).values(
                    id=uuid.uuid4().hex,
                    campaign_id=campaign_id,
                    user_id=user_id,
                    role="gm",
                    created_at=now,
                    updated_at=now,
                ))

                summary["settings"] = self._simple_rows(
                    connection, content, campaign_permission_overrides, campaign_id, user_id, now
                )
                summary["packages"] = 0
                for raw in exported_packages:
                    if raw.get("package_id") not in available_packages:
                        continue
                    row = self._fit(campaign_packages, raw)
                    row.update(campaign_id=campaign_id, enabled_by_user_id=user_id, enabled_at=now)
                    connection.execute(insert(campaign_packages).values(**row))
                    summary["packages"] += 1

                summary["actors"] = self._tree(
                    connection, content, actor_folders, actors_core, campaign_id, user_id, now,
                    clear_fields=("portrait_asset_id", "token_asset_id"),
                )
                summary["items"] = self._tree(
                    connection, content, item_folders, items_core, campaign_id, user_id, now,
                    clear_fields=("portrait_asset_id",),
                )
                journal_map, journal_count = self._journals(
                    connection, content, campaign_id, user_id, now
                )
                summary["journals"] = journal_count
                summary["quest_board_entries"] = self._quest_links(
                    connection, content, journal_map, now
                )
                summary["scenes"] = self._scenes(
                    connection, content, campaign_id, user_id, now
                )
        except (KeyError, TypeError, ValueError, binascii.Error, SQLAlchemyError):
            return self._invalid()
        return CampaignImportResult(True, campaign_id=campaign_id, summary=summary)

    @staticmethod
    def _invalid() -> CampaignImportResult:
        return CampaignImportResult(False, error_key="campaign.import.errors.invalid")

    @staticmethod
    def _rows(content: dict[str, Any], name: str) -> list[dict[str, Any]]:
        rows = content.get(name, [])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"invalid table {name}")
        return rows

    @classmethod
    def _fit(cls, table, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            key: cls._decode(value)
            for key, value in raw.items()
            if key in table.c
        }

    @classmethod
    def _decode(cls, value: Any) -> Any:
        if isinstance(value, dict) and set(value) == {"$base64"}:
            return base64.b64decode(value["$base64"], validate=True)
        return value

    def _simple_rows(self, connection, content, table, campaign_id, user_id, now) -> int:
        count = 0
        for raw in self._rows(content, table.name):
            row = self._fit(table, raw)
            row.update(campaign_id=campaign_id, created_at=now, updated_at=now)
            if "id" in table.c:
                row["id"] = uuid.uuid4().hex
            if "created_by_user_id" in table.c:
                row["created_by_user_id"] = user_id
            connection.execute(insert(table).values(**row))
            count += 1
        return count

    def _tree(self, connection, content, folder_table, resource_table, campaign_id,
              user_id, now, clear_fields=()) -> int:
        folders = self._rows(content, folder_table.name)
        folder_map = {str(row.get("id")): uuid.uuid4().hex for row in folders}
        for raw in folders:
            row = self._fit(folder_table, raw)
            row.update(id=folder_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["parent_id"] = folder_map.get(str(raw.get("parent_id")))
            connection.execute(insert(folder_table).values(**row))
        count = 0
        for raw in self._rows(content, resource_table.name):
            row = self._fit(resource_table, raw)
            row.update(id=uuid.uuid4().hex, campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["folder_id"] = folder_map.get(str(raw.get("folder_id")))
            for field_name in clear_fields:
                row[field_name] = None
            connection.execute(insert(resource_table).values(**row))
            count += 1
        return count

    def _journals(self, connection, content, campaign_id, user_id, now):
        folders = self._rows(content, journal_folders.name)
        folder_map = {str(row.get("id")): uuid.uuid4().hex for row in folders}
        for raw in folders:
            row = self._fit(journal_folders, raw)
            row.update(id=folder_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["parent_id"] = folder_map.get(str(raw.get("parent_id")))
            connection.execute(insert(journal_folders).values(**row))
        originals = self._rows(content, journals.name)
        journal_map = {str(row.get("id")): uuid.uuid4().hex for row in originals}
        for raw in originals:
            row = self._fit(journals, raw)
            row.update(id=journal_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_by_user_id=user_id, created_at=now, updated_at=now)
            row["folder_id"] = folder_map.get(str(raw.get("folder_id")))
            connection.execute(insert(journals).values(**row))
        return journal_map, len(originals)

    def _quest_links(self, connection, content, journal_map, now):
        count = 0
        for raw in self._rows(content, quest_board_entries.name):
            board_id = journal_map.get(str(raw.get("board_id")))
            quest_id = journal_map.get(str(raw.get("quest_id")))
            if not board_id or not quest_id:
                continue
            row = self._fit(quest_board_entries, raw)
            row.update(board_id=board_id, quest_id=quest_id, created_at=now)
            connection.execute(insert(quest_board_entries).values(**row))
            count += 1
        return count

    def _scenes(self, connection, content, campaign_id, user_id, now):
        groups = self._rows(content, scene_groups.name)
        group_map = {str(row.get("id")): uuid.uuid4().hex for row in groups}
        for raw in groups:
            row = self._fit(scene_groups, raw)
            row.update(id=group_map[str(raw.get("id"))], campaign_id=campaign_id,
                       created_at=now, updated_at=now)
            connection.execute(insert(scene_groups).values(**row))
        originals = self._rows(content, scenes.name)
        scene_map = {str(row.get("id")): uuid.uuid4().hex for row in originals}
        for raw in originals:
            row = self._fit(scenes, raw)
            row.update(id=scene_map[str(raw.get("id"))], campaign_id=campaign_id,
                       group_id=group_map.get(str(raw.get("group_id"))), active=0,
                       status="draft", created_at=now, updated_at=now)
            if "created_by_user_id" in scenes.c:
                row["created_by_user_id"] = user_id
            connection.execute(insert(scenes).values(**row))
        count = len(originals)
        for raw in self._rows(content, scene_layers.name):
            scene_id = scene_map.get(str(raw.get("scene_id")))
            if not scene_id:
                continue
            row = self._fit(scene_layers, raw)
            row.update(id=uuid.uuid4().hex, scene_id=scene_id, created_at=now, updated_at=now)
            connection.execute(insert(scene_layers).values(**row))
        return count
