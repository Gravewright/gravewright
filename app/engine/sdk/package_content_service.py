"""Content-pack listing and import for SDK packages.

Packages of kind ``ruleset`` / ``content`` (and any package declaring
``content.packs``) ship read-only content packs. This service lists them, copies
a pack *entry* into campaign-owned actors / items / journals, and records the
import in ``package_content_imports``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.assets.asset_library_service import AssetLibraryService
from app.engine.decks.card_service import CardService
from app.engine.content.content_pack_access import ContentPackAccessService
from app.engine.content.content_pack_service import ContentPackService
from app.engine.items.item_service import ItemService
from app.engine.journals.journal_service import JournalService
from app.engine.scenes.scene_service import SceneService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk import package_registry
from app.engine.sdk.package_paths import safe_join
from app.engine.sheets.sheet_data_service import SheetDataService
from app.persistence.repositories.campaign_package_repository import (
    CampaignPackageRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.package_content_import_repository import (
    PackageContentImportRepository,
)

_ITEM_PACK_TYPES = {"item_pack", "spell_pack"}
_JOURNAL_TYPES = {"diary", "quest", "quest_board", "roll_table"}


@dataclass(frozen=True)
class ContentImportResult:
    success: bool
    campaign_id: str | None = None
    package_id: str | None = None
    pack_type: str | None = None
    actor_id: str | None = None
    item_id: str | None = None
    journal_id: str | None = None
    deck_id: str | None = None
    scene_id: str | None = None
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
        self.access = ContentPackAccessService()
        self.assets = AssetLibraryService()
        self.cards = CardService()
        self.scenes = SceneService()



    def list_packs(self, package_id: str) -> list[dict]:
        if not self._content_enabled(package_id):
            return []
        return self.packs.list_packs(package_id)

    def list_active_packages(self, *, campaign_id: str, user_id: str) -> list[dict]:
        """Pacotes de conteúdo que ESTE usuário alcança nesta mesa.

        Era gm-only, o que deixava a aba de compêndio do jogador sempre vazia
        mesmo depois de o mestre liberar um pack. Agora o pacote só aparece se
        houver ao menos um pack legível dentro dele -- senão o jogador abriria um
        pacote para encontrar nada, que é o mesmo problema um nível abaixo.
        """
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return []
        active_ids = {
            str(row["package_id"])
            for row in self.campaign_packages.list_for_campaign(campaign_id)
            if row.get("status") == "active"
        }
        if campaign.get("active_system_id"):
            active_ids.add(str(campaign["active_system_id"]))
        disponiveis = []
        for item in self.install.list_for_tab():
            if not (
                item["id"] in active_ids
                and item["status"] == "enabled"
                and "content.packs" in item.get("capabilities", [])
            ):
                continue
            if not any(
                self.access.can_read(
                    campaign_id=campaign_id,
                    package_id=item["id"],
                    pack_id=str(pack.get("id") or ""),
                    user_id=user_id,
                )
                for pack in self.list_packs(item["id"])
            ):
                continue
            disponiveis.append({"id": item["id"], "name": item["name"]})
        return disponiveis

    def ensure_import_folder(
        self,
        *,
        campaign_id: str,
        user_id: str,
        package_name: str,
        pack: dict,
    ) -> str:
        """Return the package/pack destination folder for a bulk import."""
        pack_type = str(pack.get("type") or "")
        if pack_type == "actor_pack":
            service = self.actors
        elif pack_type in _ITEM_PACK_TYPES:
            service = self.items
        elif pack_type == "journal_pack":
            service = self.journals
        else:
            return ""

        root_name = package_name.strip()[:60] or "Content"
        pack_name = str(pack.get("label") or pack.get("name") or pack.get("id") or "Content").strip()[:60]
        folders = service.folders.list_for_campaign(campaign_id=campaign_id)
        root = next(
            (folder for folder in folders if folder.get("parent_id") is None and folder.get("name") == root_name),
            None,
        )
        if root is None:
            created_root = service.create_folder(
                campaign_id=campaign_id,
                user_id=user_id,
                name=root_name,
            )
            if not created_root.success or not created_root.folder_id:
                return ""
            root_id = created_root.folder_id
        else:
            root_id = str(root["id"])

        folders = service.folders.list_for_campaign(campaign_id=campaign_id)
        child = next(
            (
                folder
                for folder in folders
                if str(folder.get("parent_id") or "") == root_id and folder.get("name") == pack_name
            ),
            None,
        )
        if child is not None:
            return str(child["id"])
        created_child = service.create_folder(
            campaign_id=campaign_id,
            user_id=user_id,
            name=pack_name,
            parent_id=root_id,
        )
        return str(created_child.folder_id or "") if created_child.success else ""

    def ensure_entry_import_folder(
        self, *, campaign_id: str, user_id: str, pack: dict, entry: dict, parent_id: str
    ) -> str:
        """Optionally nest an entry under a package-declared folder label."""
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        name = str(data.get("importFolder") or "").strip()[:60]
        if not name or not parent_id:
            return parent_id
        pack_type = str(pack.get("type") or "")
        service = (
            self.actors if pack_type == "actor_pack"
            else self.items if pack_type in _ITEM_PACK_TYPES
            else self.journals if pack_type == "journal_pack"
            else None
        )
        if service is None:
            return parent_id
        folders = service.folders.list_for_campaign(campaign_id=campaign_id)
        existing = next(
            (f for f in folders if str(f.get("parent_id") or "") == parent_id and f.get("name") == name),
            None,
        )
        if existing:
            return str(existing["id"])
        created = service.create_folder(
            campaign_id=campaign_id, user_id=user_id, name=name, parent_id=parent_id
        )
        return str(created.folder_id or parent_id) if created.success else parent_id

    def get_pack(self, package_id: str, pack_id: str) -> dict | None:
        if not self._content_enabled(package_id):
            return None
        return self.packs.get_pack(package_id, pack_id)

    def get_entry(self, package_id: str, pack_id: str, entry_id: str) -> dict | None:
        if not self._content_enabled(package_id):
            return None
        return self.packs.get_entry(package_id, pack_id, entry_id)

    def list_imports(self, campaign_id: str) -> list[dict]:
        return self.imports.list_for_campaign(campaign_id)



    def import_entry(
        self,
        *,
        campaign_id: str,
        user_id: str,
        package_id: str,
        pack_id: str,
        entry_id: str,
        folder_id: str = "",
    ) -> ContentImportResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ContentImportResult(success=False, error_key="inside.campaigns.errors.not_found")
        if campaign.get("member_role") != PlayerRole.GM.value:
            return ContentImportResult(
                success=False, error_key="inside.campaigns.errors.gm_required"
            )
        if not self._content_enabled(package_id):
            return ContentImportResult(success=False, error_key="sdk.errors.capability_required")
        if not self._active_for_campaign(package_id=package_id, campaign=dict(campaign)):
            return ContentImportResult(success=False, error_key="sdk.errors.dependency_inactive")

        pack = self.packs.get_pack(package_id, pack_id)
        if pack is None:
            return ContentImportResult(success=False, error_key="game.drop.errors.entry_not_found")
        entry = self.packs.get_entry(package_id, pack_id, entry_id)
        if entry is None:
            return ContentImportResult(success=False, error_key="game.drop.errors.entry_not_found")

        pack_type = str(pack.get("type") or "")
        if not folder_id:
            record = self.install.get(package_id)
            summary = next(
                (candidate for candidate in self.list_packs(package_id) if candidate.get("id") == pack_id),
                {},
            )
            folder_id = self.ensure_import_folder(
                campaign_id=campaign_id,
                user_id=user_id,
                package_name=str(record.get("name") if record else package_id),
                pack={**pack, "label": summary.get("label") or pack.get("label")},
            )
        folder_id = self.ensure_entry_import_folder(
            campaign_id=campaign_id,
            user_id=user_id,
            pack=pack,
            entry=entry,
            parent_id=folder_id,
        )
        campaign = dict(campaign)
        if pack_type == "actor_pack":
            result = self._import_actor(campaign, user_id, package_id, pack_type, entry, folder_id)
        elif pack_type in _ITEM_PACK_TYPES:
            result = self._import_item(campaign, user_id, package_id, pack_type, entry, folder_id)
        elif pack_type == "journal_pack":
            result = self._import_journal(campaign, user_id, package_id, pack_type, entry, folder_id)
        elif pack_type in {"card_pack", "deck_pack"}:
            result = self._import_deck(campaign, user_id, package_id, pack_id, pack_type, entry)
        elif pack_type == "scene_pack":
            result = self._import_scene(campaign, user_id, package_id, pack_type, entry, folder_id)
        else:
            return ContentImportResult(
                success=False, error_key="game.content.errors.not_importable"
            )

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

    def _import_actor(self, campaign, user_id, package_id, pack_type, entry, folder_id) -> ContentImportResult:
        system_id = self._entry_system_id(campaign, entry)
        if not system_id:
            return ContentImportResult(
                success=False, error_key="game.items.errors.system_not_assigned"
            )
        created = self.actors.create_actor(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            system_id=system_id,
            actor_type=str(entry.get("type") or ""),
            name=str(entry.get("name") or entry.get("title") or "Imported"),
            folder_id=folder_id,
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

    def _import_item(self, campaign, user_id, package_id, pack_type, entry, folder_id) -> ContentImportResult:
        system_id = self._entry_system_id(campaign, entry)
        if not system_id:
            return ContentImportResult(
                success=False, error_key="game.items.errors.system_not_assigned"
            )
        seed = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        created = self.items.create_item(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            system_id=system_id,
            item_type=str(entry.get("type") or ""),
            name=str(entry.get("name") or entry.get("title") or "Imported"),
            folder_id=folder_id,
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

    def _import_journal(
        self, campaign, user_id, package_id, pack_type, entry, folder_id
    ) -> ContentImportResult:
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
            folder_id=folder_id,
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

    def _import_deck(self, campaign, user_id, package_id, pack_id, pack_type, entry):
        """Materialize package artwork, then create a campaign-owned usable deck."""
        data = entry.get("data") if isinstance(entry.get("data"), dict) else entry
        raw_cards = data.get("cards") if isinstance(data.get("cards"), list) else []
        if not raw_cards:
            return ContentImportResult(success=False, error_key="game.cards.errors.empty_deck")
        cards = []
        for position, raw in enumerate(raw_cards):
            if not isinstance(raw, dict):
                return ContentImportResult(success=False, error_key="game.content.errors.not_importable")
            artwork = str(raw.get("artwork") or raw.get("front") or "")
            asset_id = self._materialize_package_asset(
                campaign_id=str(campaign["id"]), user_id=user_id,
                package_id=package_id, relative=artwork,
            )
            if not asset_id:
                return ContentImportResult(success=False, error_key="game.cards.errors.missing_front_asset")
            quantity = raw.get("quantity", 1)
            if not isinstance(quantity, int) or isinstance(quantity, bool):
                return ContentImportResult(success=False, error_key="game.content.errors.not_importable")
            cards.append({
                "name": str(raw.get("name") or raw.get("label") or raw.get("id") or "Card")[:191],
                "front_asset_id": asset_id,
                "quantity": max(1, min(quantity, 999)),
                "tags": raw.get("tags") if isinstance(raw.get("tags"), list) else [],
                "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
                "sort_key": str(raw.get("sortKey") or raw.get("sort_key") or f"{position:04d}"),
            })
        source_ref = self.packs.canonical_ref(package_id, pack_id, str(entry.get("id") or ""))
        created = self.cards.create_deck_definition(
            campaign_id=str(campaign["id"]), user_id=user_id,
            name=str(entry.get("name") or entry.get("title") or "Imported deck"),
            description=str(data.get("description") or "") or None, cards=cards,
            metadata={"source": source_ref, "packageId": package_id, "contentPackId": pack_id},
        )
        if not created.success:
            return ContentImportResult(success=False, error_key=created.error_key)
        instantiated = self.cards.instantiate_deck(
            campaign_id=str(campaign["id"]), user_id=user_id,
            deck_definition_id=str(created.payload["deck"]["id"]),
        )
        if not instantiated.success:
            return ContentImportResult(success=False, error_key=instantiated.error_key)
        return ContentImportResult(
            success=True, campaign_id=str(campaign["id"]), package_id=package_id,
            pack_type=pack_type, deck_id=str(instantiated.payload["deck"]["id"]),
        )

    def _import_scene(self, campaign, user_id, package_id, pack_type, entry, group_id):
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        try:
            dimensions = {
                "width": int(data.get("width") or 2048),
                "height": int(data.get("height") or 2048),
                "tile_size": int(data.get("tileSize") or data.get("tile_size") or 256),
                "chunk_size": int(data.get("chunkSize") or data.get("chunk_size") or 1024),
            }
        except (TypeError, ValueError):
            return ContentImportResult(success=False, error_key="game.scenes.errors.invalid_dimensions")
        result = self.scenes.create_scene(
            campaign_id=str(campaign["id"]), user_id=user_id,
            name=str(entry.get("name") or entry.get("title") or "Imported scene"),
            **dimensions,
        )
        if not result.success or result.scene is None:
            return ContentImportResult(success=False, error_key=result.error_key)
        scene_id = str(result.scene["id"])
        if group_id:
            self.scenes.move_scene_to_group(
                scene_id=scene_id, group_id=group_id, campaign_id=str(campaign["id"])
            )
        return ContentImportResult(
            success=True, campaign_id=str(campaign["id"]), package_id=package_id,
            pack_type=pack_type, scene_id=scene_id,
        )

    def _materialize_package_asset(self, *, campaign_id, user_id, package_id, relative):
        if not relative:
            return None
        record, manifest = self.install.get(package_id), self.install.get_manifest(package_id)
        if not record or not manifest or relative not in set(manifest.referenced_paths()):
            return None
        path = safe_join(package_registry.PACKAGES_DIR / record["package_dir"], relative)
        if path is None or not path.is_file() or Path(relative).suffix.lower() != ".webp":
            return None
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        existing = next((asset for asset in self.assets.assets.list_for_campaign(campaign_id=campaign_id)
                         if asset.get("hash") == digest), None)
        if existing:
            return str(existing["id"])
        result = self.assets.create_asset(
            campaign_id=campaign_id, user_id=user_id, filename=path.name,
            content_type="image/webp", data=payload,
        )
        return str(result.payload["asset"]["id"]) if result.success else None
