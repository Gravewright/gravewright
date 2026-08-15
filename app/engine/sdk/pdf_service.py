from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from app.engine.assets.asset_read_service import AssetReadService
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.pdf_annotation_repository import PdfAnnotationRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass(frozen=True)
class PdfResult:
    success: bool
    value: Any = None
    error_key: str | None = None


class SdkPdfService:
    def __init__(self, *, assets: AssetRepository | None = None, reader: AssetReadService | None = None, annotations: PdfAnnotationRepository | None = None) -> None:
        self.assets = assets or AssetRepository()
        self.reader = reader or AssetReadService(assets=self.assets)
        self.annotations = annotations or PdfAnnotationRepository()
        self.campaigns = CampaignRepository()

    def document(self, *, campaign_id: str, document_id: str, user_id: str) -> PdfResult:
        asset = self.assets.get_by_id(document_id)
        if not asset or asset.get("campaign_id") != campaign_id:
            return PdfResult(False, error_key="sdk.pdf.not_found")
        access = self.reader.get_asset(asset_id=document_id, user_id=user_id)
        if not access.success:
            return PdfResult(False, error_key="sdk.pdf.not_found" if access.error_key == "not_found" else "sdk.pdf.permission_denied")
        content_type = str(asset.get("content_type") or "").lower()
        if content_type != "application/pdf" and not str(asset.get("filename") or "").lower().endswith(".pdf"):
            return PdfResult(False, error_key="sdk.pdf.not_pdf")
        return PdfResult(True, {
            "id": asset["id"], "filename": asset["filename"], "content_type": "application/pdf",
            "byte_size": int(asset.get("byte_size") or 0), "created_at": asset.get("created_at"),
            "url": f"/game/assets/file/{asset['id']}",
        })

    def list_annotations(self, *, campaign_id: str, document_id: str, user_id: str) -> PdfResult:
        document = self.document(campaign_id=campaign_id, document_id=document_id, user_id=user_id)
        if not document.success:
            return document
        return PdfResult(True, [self._annotation(row) for row in self.annotations.list_for_document(campaign_id=campaign_id, document_id=document_id)])

    def create_annotation(self, *, campaign_id: str, document_id: str, user_id: str, page: Any, region: Any, text: Any) -> PdfResult:
        document = self.document(campaign_id=campaign_id, document_id=document_id, user_id=user_id)
        if not document.success:
            return document
        try:
            page_number = int(page)
        except (TypeError, ValueError):
            return PdfResult(False, error_key="sdk.pdf.annotation_page_invalid")
        if page_number < 1 or page_number > 100_000:
            return PdfResult(False, error_key="sdk.pdf.annotation_page_invalid")
        normalized_region = self._region(region)
        if normalized_region is None:
            return PdfResult(False, error_key="sdk.pdf.annotation_region_invalid")
        normalized_text = str(text or "").strip()
        if not normalized_text or len(normalized_text) > 10_000:
            return PdfResult(False, error_key="sdk.pdf.annotation_text_invalid")
        row = self.annotations.create(campaign_id=campaign_id, document_id=document_id, author_user_id=user_id, page=page_number, region=normalized_region, text=normalized_text)
        return PdfResult(True, self._annotation(row))

    def update_annotation(self, *, campaign_id: str, document_id: str, annotation_id: str, user_id: str, page: Any, region: Any, text: Any) -> PdfResult:
        document = self.document(campaign_id=campaign_id, document_id=document_id, user_id=user_id)
        if not document.success:
            return document
        current = self.annotations.get(annotation_id)
        if not current or current.get("campaign_id") != campaign_id or current.get("document_id") != document_id:
            return PdfResult(False, error_key="sdk.pdf.annotation_not_found")
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if current.get("author_user_id") != user_id and role not in {"gm", "assistant_gm"}:
            return PdfResult(False, error_key="sdk.pdf.permission_denied")
        try:
            page_number = int(page)
        except (TypeError, ValueError):
            return PdfResult(False, error_key="sdk.pdf.annotation_page_invalid")
        normalized_region = self._region(region)
        normalized_text = str(text or "").strip()
        if page_number < 1 or page_number > 100_000:
            return PdfResult(False, error_key="sdk.pdf.annotation_page_invalid")
        if normalized_region is None:
            return PdfResult(False, error_key="sdk.pdf.annotation_region_invalid")
        if not normalized_text or len(normalized_text) > 10_000:
            return PdfResult(False, error_key="sdk.pdf.annotation_text_invalid")
        row = self.annotations.update(annotation_id=annotation_id, page=page_number, region=normalized_region, text=normalized_text)
        return PdfResult(True, self._annotation(row)) if row else PdfResult(False, error_key="sdk.pdf.annotation_not_found")

    def delete_annotation(self, *, campaign_id: str, document_id: str, annotation_id: str, user_id: str) -> PdfResult:
        document = self.document(campaign_id=campaign_id, document_id=document_id, user_id=user_id)
        if not document.success:
            return document
        current = self.annotations.get(annotation_id)
        if not current or current.get("campaign_id") != campaign_id or current.get("document_id") != document_id:
            return PdfResult(False, error_key="sdk.pdf.annotation_not_found")
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if current.get("author_user_id") != user_id and role not in {"gm", "assistant_gm"}:
            return PdfResult(False, error_key="sdk.pdf.permission_denied")
        return PdfResult(True, {"annotation_id": annotation_id}) if self.annotations.delete(annotation_id) else PdfResult(False, error_key="sdk.pdf.annotation_not_found")

    @staticmethod
    def _region(value: Any) -> dict | None:
        if not isinstance(value, dict) or not value:
            return None
        result: dict[str, float] = {}
        for key, raw in value.items():
            if key not in {"x", "y", "width", "height", "x1", "y1", "x2", "y2"}:
                continue
            try:
                number = float(raw)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(number) or abs(number) > 1_000_000:
                return None
            result[key] = number
        rectangular = {"x", "y", "width", "height"} <= result.keys()
        corners = {"x1", "y1", "x2", "y2"} <= result.keys()
        return result if rectangular or corners else None

    @staticmethod
    def _annotation(row: dict) -> dict:
        region = row.get("region_json")
        if isinstance(region, str):
            try:
                region = json.loads(region)
            except json.JSONDecodeError:
                region = {}
        return {
            "id": row["id"], "document_id": row["document_id"], "author_user_id": row["author_user_id"],
            "page": row["page"], "region": region or {}, "text": row["text"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }
