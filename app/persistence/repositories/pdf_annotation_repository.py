from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import delete, insert, select, update

from app.persistence.database import all_dicts, engine_begin, engine_connect, one_or_none
from app.persistence.tables import pdf_annotations


class PdfAnnotationRepository:
    def get(self, annotation_id: str) -> dict | None:
        with engine_connect() as connection:
            return one_or_none(connection.execute(
                select(pdf_annotations).where(pdf_annotations.c.id == annotation_id).limit(1)
            ))

    def list_for_document(self, *, campaign_id: str, document_id: str) -> list[dict]:
        statement = (
            select(pdf_annotations)
            .where(pdf_annotations.c.campaign_id == campaign_id)
            .where(pdf_annotations.c.document_id == document_id)
            .order_by(pdf_annotations.c.page.asc(), pdf_annotations.c.created_at.asc())
        )
        with engine_connect() as connection:
            return all_dicts(connection.execute(statement))

    def create(self, *, campaign_id: str, document_id: str, author_user_id: str, page: int, region: dict, text: str) -> dict:
        now = int(time.time())
        annotation_id = uuid.uuid4().hex
        with engine_begin() as connection:
            connection.execute(insert(pdf_annotations).values(
                id=annotation_id, campaign_id=campaign_id, document_id=document_id,
                author_user_id=author_user_id, page=page,
                region_json=json.dumps(region, separators=(",", ":"), sort_keys=True),
                text=text, created_at=now, updated_at=now,
            ))
            row = one_or_none(connection.execute(
                select(pdf_annotations).where(pdf_annotations.c.id == annotation_id).limit(1)
            ))
        if row is None:
            raise RuntimeError("Created PDF annotation could not be read back.")
        return row

    def update(self, *, annotation_id: str, page: int, region: dict, text: str) -> dict | None:
        with engine_begin() as connection:
            connection.execute(update(pdf_annotations).where(pdf_annotations.c.id == annotation_id).values(
                page=page, region_json=json.dumps(region, separators=(",", ":"), sort_keys=True),
                text=text, updated_at=int(time.time()),
            ))
            return one_or_none(connection.execute(
                select(pdf_annotations).where(pdf_annotations.c.id == annotation_id).limit(1)
            ))

    def delete(self, annotation_id: str) -> bool:
        with engine_begin() as connection:
            result = connection.execute(delete(pdf_annotations).where(pdf_annotations.c.id == annotation_id))
        return bool(result.rowcount)
