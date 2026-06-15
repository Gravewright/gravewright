from __future__ import annotations

import time

from sqlalchemy import delete, select, update

from app.persistence.database import engine_begin, engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import installed_packages


class InstalledPackageRepository:
    """Global install registry for Gravewright SDK packages (all kinds)."""

    def list_all(self) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(installed_packages).order_by(installed_packages.c.name.asc())
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def list_by_kind(self, kind: str) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(installed_packages)
                    .where(installed_packages.c.kind == kind)
                    .order_by(installed_packages.c.name.asc())
                )
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def get(self, package_id: str) -> dict | None:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(installed_packages)
                    .where(installed_packages.c.id == package_id)
                    .limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row is not None else None

    def upsert(
        self,
        *,
        package_id: str,
        kind: str,
        name: str,
        version: str,
        status: str,
        package_dir: str,
        manifest_json: str,
        compatibility_status: str,
        validation_errors_json: str,
        installed_by_user_id: str | None,
        package_sha256: str | None = None,
    ) -> None:
        now = int(time.time())
        values = {
            "id": package_id,
            "kind": kind,
            "name": name,
            "version": version,
            "status": status,
            "package_dir": package_dir,
            "manifest_json": manifest_json,
            "compatibility_status": compatibility_status,
            "validation_errors_json": validation_errors_json,
            "package_sha256": package_sha256,
            "installed_by_user_id": installed_by_user_id,
            "installed_at": now,
            "updated_at": now,
            "enabled_at": now if status == "enabled" else None,
            "disabled_at": None,
        }
        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=installed_packages,
                    values=values,
                    index_elements=[installed_packages.c.id],
                    set_={
                        "kind": kind,
                        "name": name,
                        "version": version,
                        "status": status,
                        "package_dir": package_dir,
                        "manifest_json": manifest_json,
                        "compatibility_status": compatibility_status,
                        "validation_errors_json": validation_errors_json,
                        "package_sha256": package_sha256,
                        "updated_at": now,
                    },
                )
            )

    def set_status(self, *, package_id: str, status: str) -> None:
        now = int(time.time())
        values: dict = {"status": status, "updated_at": now}
        if status == "enabled":
            values["enabled_at"] = now
        elif status == "disabled":
            values["disabled_at"] = now
        with engine_begin() as connection:
            connection.execute(
                update(installed_packages)
                .where(installed_packages.c.id == package_id)
                .values(**values)
            )

    def delete(self, *, package_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(
                delete(installed_packages).where(installed_packages.c.id == package_id)
            )
