from __future__ import annotations

import time

from sqlalchemy import delete, select, update

from app.persistence.database import engine_begin, engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import campaign_packages


class CampaignPackageRepository:
    """Per-campaign activation of installed SDK packages."""

    def list_all(self) -> list[dict]:
        """Every per-campaign activation row (operator audits / `grave doctor`)."""
        with engine_connect() as connection:
            rows = connection.execute(select(campaign_packages)).mappings().all()
        return [dict(row) for row in rows]

    def list_for_campaign(self, campaign_id: str) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(campaign_packages)
                    .where(campaign_packages.c.campaign_id == campaign_id)
                    .order_by(campaign_packages.c.load_order.asc())
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def list_by_role(self, campaign_id: str, activation_role: str) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(campaign_packages).where(
                        campaign_packages.c.campaign_id == campaign_id,
                        campaign_packages.c.activation_role == activation_role,
                    )
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def get(self, *, campaign_id: str, package_id: str) -> dict | None:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(campaign_packages)
                    .where(
                        campaign_packages.c.campaign_id == campaign_id,
                        campaign_packages.c.package_id == package_id,
                    )
                    .limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row is not None else None

    def list_active_for_package(self, package_id: str) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(campaign_packages).where(
                        campaign_packages.c.package_id == package_id,
                        campaign_packages.c.status == "active",
                    )
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def activate(
        self,
        *,
        campaign_id: str,
        package_id: str,
        activation_role: str,
        enabled_by_user_id: str | None,
        load_order: int = 0,
    ) -> None:
        now = int(time.time())
        values = {
            "campaign_id": campaign_id,
            "package_id": package_id,
            "activation_role": activation_role,
            "status": "active",
            "load_order": load_order,
            "enabled_by_user_id": enabled_by_user_id,
            "enabled_at": now,
            "disabled_at": None,
        }
        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=campaign_packages,
                    values=values,
                    index_elements=[
                        campaign_packages.c.campaign_id,
                        campaign_packages.c.package_id,
                    ],
                    set_={
                        "activation_role": activation_role,
                        "status": "active",
                        "load_order": load_order,
                        "enabled_by_user_id": enabled_by_user_id,
                        "enabled_at": now,
                        "disabled_at": None,
                    },
                )
            )

    def deactivate(self, *, campaign_id: str, package_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(campaign_packages).where(
                    campaign_packages.c.campaign_id == campaign_id,
                    campaign_packages.c.package_id == package_id,
                )
            )

    def deactivate_role(self, *, campaign_id: str, activation_role: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(campaign_packages).where(
                    campaign_packages.c.campaign_id == campaign_id,
                    campaign_packages.c.activation_role == activation_role,
                )
            )

    def delete_for_package(self, *, package_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(campaign_packages).where(campaign_packages.c.package_id == package_id)
            )

    def set_load_order(self, *, campaign_id: str, package_id: str, load_order: int) -> None:
        with engine_begin() as connection:
            connection.execute(
                update(campaign_packages)
                .where(
                    campaign_packages.c.campaign_id == campaign_id,
                    campaign_packages.c.package_id == package_id,
                )
                .values(load_order=load_order)
            )
