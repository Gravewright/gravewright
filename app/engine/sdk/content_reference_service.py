"""Permission-filtered universal content references for SDK 1."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, quote, unquote, urlparse

from app.engine.actors.actor_service import ActorService
from app.engine.items.item_service import ItemService
from app.engine.journals.journal_service import JournalService
from app.engine.scenes.scene_service import SceneService
from app.engine.tokens.token_service import TokenService
from app.engine.decks.card_service import CardService
from app.engine.sdk.pdf_service import SdkPdfService
from app.engine.sdk.runtime_dto import actor_snapshot, item_snapshot, scene_snapshot
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.journal_repository import JournalRepository


SUPPORTED_KINDS = frozenset({"actor", "item", "journal", "pdf", "deck", "card", "scene", "token"})


@dataclass(frozen=True)
class ContentReference:
    campaign_id: str
    kind: str
    resource_id: str
    parent_kind: str | None = None
    parent_id: str | None = None
    page: int | None = None
    anchor: str | None = None

    @property
    def uri(self) -> str:
        pieces = ["campaign", quote(self.campaign_id), self.kind, quote(self.resource_id)]
        if self.parent_kind and self.parent_id:
            pieces = ["campaign", quote(self.campaign_id), self.parent_kind, quote(self.parent_id), self.kind, quote(self.resource_id)]
        query = []
        if self.page is not None:
            query.append(f"page={self.page}")
        if self.anchor:
            query.append(f"anchor={quote(self.anchor)}")
        return "grave://" + "/".join(pieces) + (("?" + "&".join(query)) if query else "")

    def public(self) -> dict:
        return {
            "uri": self.uri, "campaignId": self.campaign_id, "kind": self.kind,
            "id": self.resource_id, "parentKind": self.parent_kind,
            "parentId": self.parent_id, "page": self.page, "anchor": self.anchor,
        }


def parse_content_reference(value: str | dict, *, campaign_id: str = "") -> ContentReference:
    if isinstance(value, dict):
        kind = str(value.get("kind") or "").lower()
        resource_id = str(value.get("id") or value.get("resourceId") or value.get("documentId") or "")
        ref = ContentReference(
            campaign_id=str(value.get("campaignId") or campaign_id), kind=kind,
            resource_id=resource_id, parent_kind=value.get("parentKind"),
            parent_id=value.get("parentId"), page=_page(value.get("page")),
            anchor=str(value.get("anchor") or "") or None,
        )
    else:
        parsed = urlparse(str(value))
        if parsed.scheme != "grave":
            raise ValueError("content reference must use grave://")
        parts = [unquote(part) for part in ([parsed.netloc] + parsed.path.split("/")) if part]
        if len(parts) not in {4, 6} or parts[0] != "campaign":
            raise ValueError("invalid content reference shape")
        query = parse_qs(parsed.query)
        if len(parts) == 4:
            ref = ContentReference(parts[1], parts[2].lower(), parts[3], page=_page(query.get("page", [None])[0]), anchor=(query.get("anchor", [None])[0]))
        else:
            ref = ContentReference(parts[1], parts[4].lower(), parts[5], parts[2].lower(), parts[3], _page(query.get("page", [None])[0]), query.get("anchor", [None])[0])
    if not ref.campaign_id or not ref.resource_id or ref.kind not in SUPPORTED_KINDS:
        raise ValueError("unsupported or incomplete content reference")
    if campaign_id and ref.campaign_id != campaign_id:
        raise PermissionError("cross-campaign reference")
    return ref


def _page(value: object) -> int | None:
    if value in {None, ""}:
        return None
    page = int(value)
    if page < 1:
        raise ValueError("page must be positive")
    return page


class ContentReferenceService:
    """Resolve references to public DTOs only after their normal permission checks."""

    def resolve(self, reference: str | dict, *, campaign_id: str, user_id: str) -> dict | None:
        ref = parse_content_reference(reference, campaign_id=campaign_id)
        value = self._resolve(ref, user_id=user_id)
        return {"ref": ref.public(), "value": value} if value is not None else None

    def search(self, *, campaign_id: str, user_id: str, query: str = "", kinds: set[str] | None = None, limit: int = 50) -> list[dict]:
        wanted = (kinds or SUPPORTED_KINDS) & SUPPORTED_KINDS
        needle = query.strip().casefold()
        entries: list[dict] = []
        def add(kind: str, row: dict, label_key: str = "name") -> None:
            label = str(row.get(label_key) or row.get("title") or row.get("label") or row.get("id") or "")
            if kind in wanted and (not needle or needle in label.casefold()):
                ref = ContentReference(campaign_id, kind, str(row.get("id") or ""))
                entries.append({"ref": ref.public(), "label": label, "kind": kind})
        if "actor" in wanted:
            for row in ActorService().list_for_campaign(campaign_id=campaign_id, user_id=user_id): add("actor", row)
        if "item" in wanted:
            for row in ItemService().list_for_campaign(campaign_id=campaign_id, user_id=user_id): add("item", row)
        campaign = CampaignRepository().get_for_user(campaign_id=campaign_id, user_id=user_id)
        if "journal" in wanted and campaign:
            journals = JournalService()
            for row in JournalRepository().list_active_for_campaign(campaign_id=campaign_id):
                if journals.can_view_journal(journal=row, campaign=dict(campaign), user_id=user_id): add("journal", row, "title")
        if "scene" in wanted:
            result = SceneService().list_scenes_for_campaign(campaign_id=campaign_id, user_id=user_id)
            if result.success:
                for row in result.scenes or []: add("scene", row)
        if wanted & {"deck", "card"}:
            state = CardService().get_state(campaign_id=campaign_id, user_id=user_id)
            if state.success:
                for row in state.payload.get("decks", []): add("deck", row)
                for row in state.payload.get("cards", []): add("card", row)
        entries.sort(key=lambda entry: (entry["label"].casefold(), entry["kind"], entry["ref"]["id"]))
        return entries[:max(1, min(limit, 100))]

    def _resolve(self, ref: ContentReference, *, user_id: str):
        if ref.kind == "actor":
            row = ActorService().get_actor(actor_id=ref.resource_id, user_id=user_id)
            return actor_snapshot(row) if row and row.get("campaign_id") == ref.campaign_id else None
        if ref.kind == "item":
            row = ItemService().get_item(item_id=ref.resource_id, user_id=user_id)
            return item_snapshot(row) if row and row.get("campaign_id") == ref.campaign_id else None
        if ref.kind == "journal":
            campaign = CampaignRepository().get_for_user(campaign_id=ref.campaign_id, user_id=user_id)
            row = JournalRepository().get_by_id(ref.resource_id)
            service = JournalService()
            if not campaign or not row or row.get("campaign_id") != ref.campaign_id or not service.can_view_journal(journal=row, campaign=dict(campaign), user_id=user_id):
                return None
            return {"id": row["id"], "title": row["title"], "type": row["type"], "view": service.build_view(journal=row, campaign=dict(campaign), user_id=user_id)}
        if ref.kind == "pdf":
            result = SdkPdfService().document(campaign_id=ref.campaign_id, document_id=ref.resource_id, user_id=user_id)
            return result.value if result.success else None
        if ref.kind == "scene":
            result = SceneService().list_scenes_for_campaign(campaign_id=ref.campaign_id, user_id=user_id)
            row = next((row for row in (result.scenes or []) if row.get("id") == ref.resource_id), None) if result.success else None
            return scene_snapshot(dict(row)) if row else None
        if ref.kind == "token":
            if ref.parent_kind != "scene" or not ref.parent_id:
                return None
            result = TokenService().get_snapshot(campaign_id=ref.campaign_id, scene_id=ref.parent_id, user_id=user_id)
            return next((row for row in (result.tokens or []) if row.get("id") == ref.resource_id), None) if result.success else None
        state = CardService().get_state(campaign_id=ref.campaign_id, user_id=user_id)
        if not state.success:
            return None
        key = "decks" if ref.kind == "deck" else "cards"
        return next((row for row in state.payload.get(key, []) if row.get("id") == ref.resource_id), None)
