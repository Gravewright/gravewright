"""Dependency-injection providers for the service layer.

Handlers receive services through Litestar DI (``campaign_service: CampaignService``)
instead of instantiating them inline. The services are stateless — they use SQLAlchemy Core connections per method call — so each provider is an app-lifetime singleton
(``use_cache=True``); the parameter name is the snake_case of the class.

Register this in the ``Litestar(dependencies=...)`` map.
"""

from __future__ import annotations

from litestar.di import Provide

from app.business.auth.auth_service import AuthService
from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.business.campaigns.campaign_service import CampaignService
from app.business.campaigns.campaign_system_service import CampaignSystemService
from app.business.campaigns.streamer_link_service import StreamerLinkService
from app.business.game_page_service import GamePageService
from app.business.permissions import PermissionService
from app.business.users import UserPreferenceService
from app.engine.actors.actor_asset_read_service import ActorAssetReadService
from app.engine.actors.actor_asset_service import ActorAssetService
from app.engine.actors.actor_service import ActorService
from app.engine.chat.chat_service import ChatService
from app.engine.combat.turn_order_service import TurnOrderService
from app.engine.content.content_import_service import ContentImportService
from app.engine.content.content_pack_service import ContentPackService
from app.engine.items.item_service import ItemService
from app.engine.modules.module_asset_service import ModuleAssetService
from app.engine.modules.module_content_import_service import ModuleContentImportService
from app.engine.modules.module_content_pack_service import ModuleContentPackService
from app.engine.modules.module_install_service import ModuleInstallService
from app.engine.modules.module_settings_service import ModuleSettingsService
from app.engine.journals.journal_asset_read_service import JournalAssetReadService
from app.engine.journals.journal_asset_service import JournalAssetService
from app.engine.journals.journal_page_service import JournalPageService
from app.engine.journals.journal_service import JournalService
from app.engine.resources.resource_permission_page_service import ResourcePermissionPageService
from app.engine.rolls.roll_presentation_service import RollPresentationService
from app.engine.scenes.map_upload_service import MapUploadService
from app.engine.scenes.scene_asset_read_service import SceneAssetReadService
from app.engine.scenes.scene_service import SceneService
from app.engine.scenes.scene_tile_read_service import SceneTileReadService
from app.engine.sheets.actor_sheet_service import ActorSheetService
from app.engine.sheets.item_sheet_data_service import ItemSheetDataService
from app.engine.sheets.item_sheet_service import ItemSheetService
from app.engine.sheets.sheet_action_service import SheetActionService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.engine.sheets.sheet_drop_service import SheetDropService
from app.engine.sheets.sheet_item_service import SheetItemService
from app.engine.systems.system_asset_service import SystemAssetService
from app.engine.systems.system_install_service import SystemInstallService
from app.engine.tokens.token_hp_service import TokenHpService
from app.engine.tokens.token_service import TokenService
from app.engine.tokens.token_instance_sheet_service import TokenInstanceSheetService
from app.infrastructure.email.dev_email_sender import DevEmailSender
from app.realtime.presence import PresenceService


def _provide_auth_service() -> AuthService:
                                                                                     
    return AuthService(email_sender=DevEmailSender())


def _singleton(factory) -> Provide:
                                                                               
                                                                                
    return Provide(lambda: factory(), sync_to_thread=False, use_cache=True)


SERVICE_DEPENDENCIES = {
    "actor_asset_read_service": _singleton(ActorAssetReadService),
    "actor_asset_service": _singleton(ActorAssetService),
    "actor_service": _singleton(ActorService),
    "actor_sheet_service": _singleton(ActorSheetService),
    "auth_service": _singleton(_provide_auth_service),
    "campaign_service": _singleton(CampaignService),
    "campaign_invitation_service": _singleton(CampaignInvitationService),
    "campaign_system_service": _singleton(CampaignSystemService),
    "chat_service": _singleton(ChatService),
    "content_import_service": _singleton(ContentImportService),
    "content_pack_service": _singleton(ContentPackService),
    "game_page_service": _singleton(GamePageService),
    "item_service": _singleton(ItemService),
    "item_sheet_service": _singleton(ItemSheetService),
    "item_sheet_data_service": _singleton(ItemSheetDataService),
    "journal_asset_read_service": _singleton(JournalAssetReadService),
    "journal_service": _singleton(JournalService),
    "journal_asset_service": _singleton(JournalAssetService),
    "journal_page_service": _singleton(JournalPageService),
    "map_upload_service": _singleton(MapUploadService),
    "module_asset_service": _singleton(ModuleAssetService),
    "module_content_import_service": _singleton(ModuleContentImportService),
    "module_content_pack_service": _singleton(ModuleContentPackService),
    "module_install_service": _singleton(ModuleInstallService),
    "module_settings_service": _singleton(ModuleSettingsService),
    "permission_service": _singleton(PermissionService),
    "presence_service": _singleton(PresenceService),
    "resource_permission_page_service": _singleton(ResourcePermissionPageService),
    "roll_presentation_service": _singleton(RollPresentationService),
    "scene_asset_read_service": _singleton(SceneAssetReadService),
    "scene_service": _singleton(SceneService),
    "scene_tile_read_service": _singleton(SceneTileReadService),
    "sheet_action_service": _singleton(SheetActionService),
    "sheet_data_service": _singleton(SheetDataService),
    "sheet_drop_service": _singleton(SheetDropService),
    "sheet_item_service": _singleton(SheetItemService),
    "streamer_link_service": _singleton(StreamerLinkService),
    "system_asset_service": _singleton(SystemAssetService),
    "system_install_service": _singleton(SystemInstallService),
    "token_hp_service": _singleton(TokenHpService),
    "token_service": _singleton(TokenService),
    "token_instance_sheet_service": _singleton(TokenInstanceSheetService),
    "turn_order_service": _singleton(TurnOrderService),
    "user_preference_service": _singleton(UserPreferenceService),
}
