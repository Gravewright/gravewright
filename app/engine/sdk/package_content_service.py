"""Content-pack listing and import for SDK packages.

Packages of kind ``ruleset`` / ``content`` (and any package declaring
``content.packs``) ship read-only content packs. This service lists them, copies
a pack *entry* into campaign-owned actors / items / journals, and records the
import in ``package_content_imports``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.content.content_pack_service import ContentPackService
from app.engine.items.item_service import ItemService
from app.engine.journals.journal_service import JournalService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.persistence.repositories.campaign_package_repository import (
    CampaignPackageRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.package_content_import_repository import (
    PackageContentImportRepository,
)

_ITEM_PACK_TYPES = {"item_pack", "spell_pack"}
_JOURNAL_TYPES = {"diary", "quest", "quest_board"}


@dataclass(frozen=True)
class ContentImportResult:
    success: bool
    campaign_id: str | None = None
    package_id: str | None = None
    pack_type: str | None = None
    actor_id: str | None = None
    item_id: str | None = None
    journal_id: str | None = None
    system_id: str | None = None
    error_key: str | None = None


class PackageContentService:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.packs = ContentPackService()
        self.imports = PackageContentImportRepository()
        self.campaigns = CampaignRepository()
        self.campaign_packages = CampaignPackageRepository()
        self.actors = ActorService()
        self.items = ItemService()
        self.journals = JournalService()
        self.sheet_data = SheetDataService()

    # --- reads -----------------------------------------------------------------

    def list_packs(self, package_id: str) -> list[dict]:
        if not self._content_enabled(package_id):
            return []
        return self.packs.list_packs(package_id)

    def get_pack(self, package_id: str, pack_id: str) -> dict | None:
        if not self._content_enabled(package_id):
            return None
        return self.packs.get_pack(package_id, pack_id)

    def list_imports(self, campaign_id: str) -> list[dict]:
        return self.imports.list_for_campaign(campaign_id)

    # --- import ----------------------------------------------------------------

    def import_entry(
        self,
        *,
        campaign_id: str,
        user_id: str,
        package_id: str,
        pack_id: str,
        entry_id: str,
    ) -> ContentImportResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ContentImportResult(success=False, error_key="inside.campaigns.errors.not_found")
        if campaign.get("member_role") != PlayerRole.GM.value:
            return ContentImportResult(success=False, error_key="inside.campaigns.errors.gm_required")
        if not self._content_enabled(package_id):
            return ContentImportResult(success=False, error_key="sdk.errors.capability_required")
        if not self._active_for_campaign(package_id=package_id, campaign=dict(campaign)):
            return ContentImportResult(success=False, error_key="sdk.errors.dependency_inactive")

        pack = self.packs.get_pack(package_id, pack_id)
        if pack is None:
            return ContentImportResult(success=False, error_key="game.drop.errors.entry_not_found")
        entry = next((e for e in pack["entries"] if e.get("id") == entry_id), None)
        if entry is None:
            return ContentImportResult(success=False, error_key="game.drop.errors.entry_not_found")

        pack_type = str(pack.get("type") or "")
        campaign = dict(campaign)
        if pack_type == "actor_pack":
            result = self._import_actor(campaign, user_id, package_id, pack_type, entry)
        elif pack_type in _ITEM_PACK_TYPES:
            result = self._import_item(campaign, user_id, package_id, pack_type, entry)
        elif pack_type == "journal_pack":
            result = self._import_journal(campaign, user_id, package_id, pack_type, entry)
        else:
            return ContentImportResult(success=False, error_key="game.content.errors.not_importable")

        if result.success:
            self.imports.record(
                campaign_id=campaign_id,
                package_id=package_id,
                content_pack_id=pack_id,
                content_pack_type=pack_type,
                imported_by_user_id=user_id,
            )
        return result

    def _content_enabled(self, package_id: str) -> bool:
        record = self.install.get(package_id)
        manifest = self.install.get_manifest(package_id)
        return bool(
            record
            and record["status"] == "enabled"
            and manifest
            and "content.packs" in manifest.capabilities
        )

    def _active_for_campaign(self, *, package_id: str, campaign: dict) -> bool:
        if campaign.get("active_system_id") == package_id:
            return True
        return (
            self.campaign_packages.get(campaign_id=str(campaign["id"]), package_id=package_id)
            is not None
        )

    def _entry_system_id(self, campaign: dict, entry: dict) -> str:
        return str(
            entry.get("systemId")
            or entry.get("system_id")
            or campaign.get("active_system_id")
            or ""
        )

    def _import_actor(self, campaign, user_id, package_id, pack_type, entry) -> ContentImportResult:
        system_id = self._entry_system_id(campaign, entry)
        if not system_id:
            return ContentImportResult(success=False, error_key="game.items.errors.system_not_assigned")
        created = self.actors.create_actor(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            system_id=system_id,
            actor_type=str(entry.get("type") or ""),
            name=str(entry.get("name") or entry.get("title") or "Imported"),
        )
        if not created.success or not created.actor_id:
            return ContentImportResult(success=False, error_key=created.error_key)
        data = entry.get("data")
        if isinstance(data, dict) and data:
            self.sheet_data.set_data(actor_id=created.actor_id, user_id=user_id, data=data)
        return ContentImportResult(
            success=True,
            campaign_id=str(campaign["id"]),
            package_id=package_id,
            pack_type=pack_type,
            actor_id=created.actor_id,
            system_id=system_id,
        )

    def _import_item(self, campaign, user_id, package_id, pack_type, entry) -> ContentImportResult:
        system_id = self._entry_system_id(campaign, entry)
        if not system_id:
            return ContentImportResult(success=False, error_key="game.items.errors.system_not_assigned")
        seed = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        created = self.items.create_item(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            system_id=system_id,
            item_type=str(entry.get("type") or ""),
            name=str(entry.get("name") or entry.get("title") or "Imported"),
            data=seed,
        )
        if not created.success or not created.item_id:
            return ContentImportResult(success=False, error_key=created.error_key)
        return ContentImportResult(
            success=True,
            campaign_id=str(campaign["id"]),
            package_id=package_id,
            pack_type=pack_type,
            item_id=created.item_id,
            system_id=system_id,
        )

    def _import_journal(self, campaign, user_id, package_id, pack_type, entry) -> ContentImportResult:
        journal_type = str(entry.get("type") or "handout")
        if journal_type not in _JOURNAL_TYPES:
            journal_type = "handout"
        content = entry.get("content_markdown", entry.get("content", ""))
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        created = self.journals.create_journal(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            journal_type=journal_type,
            title=str(entry.get("title") or entry.get("name") or "Imported"),
            visibility=str(entry.get("visibility") or "private"),
            content_markdown=str(content or ""),
            data=data,
        )
        if not created.success or not created.journal_id:
            return ContentImportResult(success=False, error_key=created.error_key)
        return ContentImportResult(
            success=True,
            campaign_id=str(campaign["id"]),
            package_id=package_id,
            pack_type=pack_type,
            journal_id=created.journal_id,
        )
