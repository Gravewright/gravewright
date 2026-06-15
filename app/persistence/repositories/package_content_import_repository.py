from __future__ import annotations

import time
import uuid

from sqlalchemy import delete, select

from app.persistence.database import engine_begin, engine_connect
from app.persistence.tables import package_content_imports


class PackageContentImportRepository:
    """Tracks which package content packs were imported into a campaign."""

    def list_all(self) -> list[dict]:
        """Every recorded content import (operator audits / `grave doctor`)."""
        with engine_connect() as connection:
            rows = connection.execute(select(package_content_imports)).mappings().all()
        return [dict(row) for row in rows]

    def list_for_campaign(self, campaign_id: str) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(package_content_imports).where(
                        package_content_imports.c.campaign_id == campaign_id
                    )
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def record(
        self,
        *,
        campaign_id: str,
        package_id: str,
        content_pack_id: str,
        content_pack_type: str,
        imported_by_user_id: str | None,
    ) -> str:
        import_id = uuid.uuid4().hex
        with engine_begin() as connection:
            connection.execute(
                package_content_imports.insert().values(
                    id=import_id,
                    campaign_id=campaign_id,
                    package_id=package_id,
                    content_pack_id=content_pack_id,
                    content_pack_type=content_pack_type,
                    imported_by_user_id=imported_by_user_id,
                    imported_at=int(time.time()),
                )
            )
        return import_id

    def delete_for_package(self, *, package_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(package_content_imports).where(
                    package_content_imports.c.package_id == package_id
                )
            )
