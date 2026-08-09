from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import insert, select

from app.persistence.database import engine_begin
from app.persistence.tables import actor_folders, actors_core
from app.persistence.tables import campaign_members, campaign_packages
from app.persistence.tables import campaign_permission_overrides, campaigns
from app.persistence.tables import item_folders, items_core
from app.persistence.tables import journal_folders, journals, quest_board_entries
from app.persistence.tables import package_settings, scene_groups, scene_layers, scenes


@dataclass(frozen=True)
class CampaignCloneOptions:
    packages: bool = True
    scenes: bool = True
    actors: bool = True
    items: bool = True
    journals: bool = True
    settings: bool = True


@dataclass(frozen=True)
class CampaignCloneResult:
    success: bool
    campaign_id: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    error_key: str | None = None


class CampaignCloneService:
    """Selective, database-transactional campaign clone with explicit exclusions."""

    def preview(
        self, *, source_campaign_id: str, user_id: str, options: CampaignCloneOptions
    ) -> CampaignCloneResult:
        with engine_begin() as connection:
            source = self._source_for_gm(connection, source_campaign_id, user_id)
            if source is None:
                return CampaignCloneResult(success=False, error_key="campaign.clone.errors.denied")
            return CampaignCloneResult(
                success=True, summary=self._summary(connection, source, options)
            )

    def clone(
        self,
        *,
        source_campaign_id: str,
        user_id: str,
        title: str,
        options: CampaignCloneOptions,
    ) -> CampaignCloneResult:
        normalized_title = " ".join(title.strip().split())
        if not 2 <= len(normalized_title) <= 120:
            return CampaignCloneResult(
                success=False, error_key="campaign.clone.errors.invalid_title"
            )
        now = int(time.time())
        new_campaign_id = uuid.uuid4().hex
        with engine_begin() as connection:
            source = self._source_for_gm(connection, source_campaign_id, user_id, lock=True)
            if source is None:
                return CampaignCloneResult(success=False, error_key="campaign.clone.errors.denied")
            summary = self._summary(connection, source, options)
            connection.execute(
                insert(campaigns).values(
                    id=new_campaign_id,
                    owner_user_id=user_id,
                    title=normalized_title,
                    description=source["description"],
                    active_system_id=source["active_system_id"] if options.packages else None,
                    initial_state_json=source["initial_state_json"] if options.settings else "{}",
                    persistent_state_json=(
                        source["persistent_state_json"] if options.settings else "{}"
                    ),
                    state_version=source["state_version"] if options.settings else 1,
                    created_at=now,
                    updated_at=now,
                )
            )
            connection.execute(
                insert(campaign_members).values(
                    id=uuid.uuid4().hex,
                    campaign_id=new_campaign_id,
                    user_id=user_id,
                    role="gm",
                    created_at=now,
                    updated_at=now,
                )
            )
            if options.settings:
                self._clone_role_settings(connection, source_campaign_id, new_campaign_id, now)
            if options.packages:
                self._clone_packages(connection, source_campaign_id, new_campaign_id, user_id, now)
            if options.actors:
                self._clone_tree(
                    connection,
                    actor_folders,
                    actors_core,
                    source_campaign_id,
                    new_campaign_id,
                    user_id,
                    now,
                    clear_fields=("portrait_asset_id", "token_asset_id"),
                )
            if options.items:
                self._clone_tree(
                    connection,
                    item_folders,
                    items_core,
                    source_campaign_id,
                    new_campaign_id,
                    user_id,
                    now,
                    clear_fields=("portrait_asset_id",),
                )
            if options.journals:
                self._clone_journals(connection, source_campaign_id, new_campaign_id, user_id, now)
            if options.scenes:
                self._clone_scenes(connection, source_campaign_id, new_campaign_id, now)
        return CampaignCloneResult(success=True, campaign_id=new_campaign_id, summary=summary)

    @staticmethod
    def _source_for_gm(connection, campaign_id: str, user_id: str, lock: bool = False):
        statement = (
            select(campaigns)
            .join(campaign_members, campaign_members.c.campaign_id == campaigns.c.id)
            .where(campaigns.c.id == campaign_id)
            .where(campaign_members.c.user_id == user_id)
            .where(campaign_members.c.role == "gm")
        )
        if lock and connection.dialect.name != "sqlite":
            statement = statement.with_for_update()
        row = connection.execute(statement).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _rows(connection, table, campaign_id: str) -> list[dict]:
        return [
            dict(row)
            for row in connection.execute(
                select(table).where(table.c.campaign_id == campaign_id)
            ).mappings()
        ]

    def _summary(self, connection, source: dict, options: CampaignCloneOptions) -> dict[str, Any]:
        campaign_id = source["id"]
        count = lambda table: len(self._rows(connection, table, campaign_id))
        return {
            "source_campaign_id": campaign_id,
            "packages": count(campaign_packages) if options.packages else 0,
            "scenes": count(scenes) if options.scenes else 0,
            "actors": count(actors_core) if options.actors else 0,
            "items": count(items_core) if options.items else 0,
            "journals": count(journals) if options.journals else 0,
            "settings": bool(options.settings),
            "warnings": ["campaign.clone.warnings.physical_assets_excluded"]
            if options.scenes
            else [],
            "excluded": [
                "members",
                "invitations",
                "join_codes",
                "chat",
                "presence",
                "audit",
                "streamer_links",
                "user_permissions",
                "physical_assets",
            ],
        }

    def _clone_role_settings(self, connection, source_id: str, target_id: str, now: int) -> None:
        for row in self._rows(connection, campaign_permission_overrides, source_id):
            if row["subject_type"] != "role":
                continue
            row.update(id=uuid.uuid4().hex, campaign_id=target_id, created_at=now, updated_at=now)
            connection.execute(insert(campaign_permission_overrides).values(**row))

    def _clone_packages(
        self, connection, source_id: str, target_id: str, user_id: str, now: int
    ) -> None:
        for row in self._rows(connection, campaign_packages, source_id):
            row.update(campaign_id=target_id, enabled_by_user_id=user_id, enabled_at=now)
            connection.execute(insert(campaign_packages).values(**row))
        settings = connection.execute(
            select(package_settings)
            .where(package_settings.c.campaign_id == source_id)
            .where(package_settings.c.user_id == "")
        ).mappings()
        for original in settings:
            row = dict(original)
            row.update(id=uuid.uuid4().hex, campaign_id=target_id, created_at=now, updated_at=now)
            connection.execute(insert(package_settings).values(**row))

    def _clone_tree(
        self,
        connection,
        folder_table,
        resource_table,
        source_id: str,
        target_id: str,
        user_id: str,
        now: int,
        clear_fields: tuple[str, ...],
    ) -> None:
        folder_map: dict[str, str] = {}
        folders = self._rows(connection, folder_table, source_id)
        for row in folders:
            folder_map[row["id"]] = uuid.uuid4().hex
        for row in folders:
            row.update(
                id=folder_map[row["id"]],
                campaign_id=target_id,
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            row["parent_id"] = folder_map.get(row.get("parent_id"))
            connection.execute(insert(folder_table).values(**row))
        for row in self._rows(connection, resource_table, source_id):
            row.update(
                id=uuid.uuid4().hex,
                campaign_id=target_id,
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            row["folder_id"] = folder_map.get(row.get("folder_id"))
            for field_name in clear_fields:
                row[field_name] = None
            connection.execute(insert(resource_table).values(**row))

    def _clone_journals(
        self, connection, source_id: str, target_id: str, user_id: str, now: int
    ) -> None:
        folder_map: dict[str, str] = {}
        for row in self._rows(connection, journal_folders, source_id):
            folder_map[row["id"]] = uuid.uuid4().hex
        for row in self._rows(connection, journal_folders, source_id):
            row.update(
                id=folder_map[row["id"]],
                campaign_id=target_id,
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            row["parent_id"] = folder_map.get(row.get("parent_id"))
            connection.execute(insert(journal_folders).values(**row))
        journal_map: dict[str, str] = {}
        originals = self._rows(connection, journals, source_id)
        for row in originals:
            journal_map[row["id"]] = uuid.uuid4().hex
        for row in originals:
            row.update(
                id=journal_map[row["id"]],
                campaign_id=target_id,
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            row["folder_id"] = folder_map.get(row.get("folder_id"))
            connection.execute(insert(journals).values(**row))
        links = connection.execute(select(quest_board_entries)).mappings()
        for original in links:
            if original["board_id"] in journal_map and original["quest_id"] in journal_map:
                row = dict(original)
                row.update(
                    board_id=journal_map[row["board_id"]],
                    quest_id=journal_map[row["quest_id"]],
                    created_at=now,
                )
                connection.execute(insert(quest_board_entries).values(**row))

    def _clone_scenes(self, connection, source_id: str, target_id: str, now: int) -> None:
        group_map = {
            row["id"]: uuid.uuid4().hex for row in self._rows(connection, scene_groups, source_id)
        }
        for row in self._rows(connection, scene_groups, source_id):
            row.update(
                id=group_map[row["id"]], campaign_id=target_id, created_at=now, updated_at=now
            )
            connection.execute(insert(scene_groups).values(**row))
        scene_map: dict[str, str] = {}
        originals = self._rows(connection, scenes, source_id)
        for row in originals:
            scene_map[row["id"]] = uuid.uuid4().hex
        for row in originals:
            old_id = row["id"]
            row.update(
                id=scene_map[old_id],
                campaign_id=target_id,
                group_id=group_map.get(row.get("group_id")),
                active=0,
                status="draft",
                created_at=now,
                updated_at=now,
            )
            connection.execute(insert(scenes).values(**row))
            layers = connection.execute(
                select(scene_layers).where(scene_layers.c.scene_id == old_id)
            ).mappings()
            for original_layer in layers:
                layer = dict(original_layer)
                layer.update(
                    id=uuid.uuid4().hex, scene_id=scene_map[old_id], created_at=now, updated_at=now
                )
                connection.execute(insert(scene_layers).values(**layer))
