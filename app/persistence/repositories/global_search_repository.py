from __future__ import annotations

from sqlalchemy import func, or_, select

from app.persistence.database import all_dicts, engine_connect
from app.persistence.tables import actor_folders, actors_core
from app.persistence.tables import item_folders, items_core
from app.persistence.tables import journal_folders, journals
from app.persistence.tables import scenes


class GlobalSearchRepository:
    """Portable bounded candidate queries; authorization stays in the service."""

    @staticmethod
    def _pattern(query: str) -> str:
        escaped = query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return f"%{escaped}%"

    def search_actors(self, *, campaign_id: str, query: str, limit: int) -> list[dict]:
        pattern = self._pattern(query)
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(actors_core, actor_folders.c.name.label("folder_name"))
                    .outerjoin(actor_folders, actor_folders.c.id == actors_core.c.folder_id)
                    .where(actors_core.c.campaign_id == campaign_id)
                    .where(actors_core.c.status == "active")
                    .where(func.lower(actors_core.c.name).like(pattern, escape="\\"))
                    .order_by(func.lower(actors_core.c.name), actors_core.c.id)
                    .limit(limit)
                )
            )

    def search_items(self, *, campaign_id: str, query: str, limit: int) -> list[dict]:
        pattern = self._pattern(query)
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(items_core, item_folders.c.name.label("folder_name"))
                    .outerjoin(item_folders, item_folders.c.id == items_core.c.folder_id)
                    .where(items_core.c.campaign_id == campaign_id)
                    .where(items_core.c.status == "active")
                    .where(func.lower(items_core.c.name).like(pattern, escape="\\"))
                    .order_by(func.lower(items_core.c.name), items_core.c.id)
                    .limit(limit)
                )
            )

    def search_journals(self, *, campaign_id: str, query: str, limit: int) -> list[dict]:
        pattern = self._pattern(query)
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(journals, journal_folders.c.name.label("folder_name"))
                    .outerjoin(journal_folders, journal_folders.c.id == journals.c.folder_id)
                    .where(journals.c.campaign_id == campaign_id)
                    .where(journals.c.status == "active")
                    .where(
                        or_(
                            func.lower(journals.c.title).like(pattern, escape="\\"),
                            func.lower(journals.c.content_markdown).like(pattern, escape="\\"),
                        )
                    )
                    .order_by(func.lower(journals.c.title), journals.c.id)
                    .limit(limit)
                )
            )

    def search_scenes(self, *, campaign_id: str, query: str, limit: int) -> list[dict]:
        pattern = self._pattern(query)
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scenes)
                    .where(scenes.c.campaign_id == campaign_id)
                    .where(func.lower(scenes.c.name).like(pattern, escape="\\"))
                    .order_by(func.lower(scenes.c.name), scenes.c.id)
                    .limit(limit)
                )
            )
