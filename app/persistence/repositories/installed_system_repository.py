from __future__ import annotations

import time

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import systems_installed


class InstalledSystemRepository:
    def list_all(self) -> list[dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(select(systems_installed).order_by(systems_installed.c.name.asc()))
                .mappings()
                .all()
            )
        return [dict(row) for row in rows]

    def get(self, system_id: str) -> dict | None:
        with engine_connect() as connection:
            row = (
                connection.execute(select(systems_installed).where(systems_installed.c.id == system_id).limit(1))
                .mappings()
                .first()
            )
        return dict(row) if row is not None else None

    def get_by_package_id(self, package_id: str) -> dict | None:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(systems_installed).where(systems_installed.c.package_id == package_id).limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row is not None else None

    def upsert(
        self,
        *,
        system_id: str,
        package_id: str,
        name: str,
        version: str,
        api_version: str,
        package_dir: str,
        manifest_json: str,
        status: str,
        validation_errors_json: str,
        installed_by_user_id: str | None,
    ) -> None:
        now = int(time.time())
        values = {
            "id": system_id,
            "package_id": package_id,
            "name": name,
            "version": version,
            "api_version": api_version,
            "package_dir": package_dir,
            "manifest_json": manifest_json,
            "status": status,
            "validation_errors_json": validation_errors_json,
            "installed_by_user_id": installed_by_user_id,
            "installed_at": now,
            "updated_at": now,
        }
        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=systems_installed,
                    values=values,
                    index_elements=[systems_installed.c.id],
                    set_={
                        "package_id": package_id,
                        "name": name,
                        "version": version,
                        "api_version": api_version,
                        "package_dir": package_dir,
                        "manifest_json": manifest_json,
                        "status": status,
                        "validation_errors_json": validation_errors_json,
                        "updated_at": now,
                    },
                )
            )

    def set_status(self, *, system_id: str, status: str) -> None:
        now = int(time.time())
        with engine_begin() as connection:
            connection.execute(
                update(systems_installed)
                .where(systems_installed.c.id == system_id)
                .values(status=status, updated_at=now)
            )

    def delete(self, *, system_id: str) -> None:
        with engine_begin() as connection:
            connection.execute(delete(systems_installed).where(systems_installed.c.id == system_id))
