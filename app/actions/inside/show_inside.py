from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.params import FromQuery
from litestar.response import Redirect
from litestar.response import Template

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.business.campaigns.campaign_service import CampaignService
from app.business.admin.admin_service import AdminService
from app.business.inside_settings_service import InsideSettingsService
from app.config import config
from app.engine.systems.system_install_service import SystemInstallService
from app.engine.modules.module_install_service import ModuleInstallService
from app.helpers.auth import require_user
from app.helpers.view import view_context


@get("/inside", guards=[require_user])
async def show_inside(
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    campaign_invitation_service: CampaignInvitationService,
    system_install_service: SystemInstallService,
    module_install_service: ModuleInstallService,
    campaign_error_key: FromQuery[str | None] = None,
    campaign_message_key: FromQuery[str | None] = None,
    invitation_error_key: FromQuery[str | None] = None,
    invitation_message_key: FromQuery[str | None] = None,
    systems_error_key: FromQuery[str | None] = None,
    systems_message_key: FromQuery[str | None] = None,
    modules_error_key: FromQuery[str | None] = None,
    modules_message_key: FromQuery[str | None] = None,
    admin_error_key: FromQuery[str | None] = None,
    admin_message_key: FromQuery[str | None] = None,
    settings_error_key: FromQuery[str | None] = None,
    settings_message_key: FromQuery[str | None] = None,
    privacy_error_key: FromQuery[str | None] = None,
    privacy_message_key: FromQuery[str | None] = None,
    pending_delete_campaign_id: FromQuery[str | None] = None,
    removal_code: FromQuery[str | None] = None,
) -> Redirect | Template:
    user = current_user
    campaigns_raw = campaign_service.list_for_user(user["id"])
    pending_invitations = campaign_invitation_service.list_pending_for_user(user["id"])
    installed_systems = system_install_service.list_for_tab()
    installed_modules = module_install_service.list_for_tab()
    inside_settings = InsideSettingsService().read()

    installed_by_id = {item["system_id"]: item["name"] for item in installed_systems if item["system_id"]}
                                                                  
    available_systems = [
        {
            "id": item["system_id"],
            "name": item["name"],
            "description": item["description"],
            "version": item["version"],
        }
        for item in installed_systems
        if item["system_id"] and item["status"] == "enabled"
    ]
    campaigns = []
    for c in campaigns_raw:
        row = dict(c)
        sys_id = row.get("active_system_id")
        row["active_system_name"] = installed_by_id.get(sys_id)
        campaigns.append(row)

    module_campaigns = [
        {"id": row["id"], "title": row["title"], "member_role": row.get("member_role")}
        for row in campaigns
        if row.get("member_role") == "gm"
    ]
    enabled_campaigns_by_module = module_install_service.enabled_campaign_ids_by_module(
        [row["id"] for row in module_campaigns]
    )
    for module in installed_modules:
        module["enabled_campaign_ids"] = sorted(enabled_campaigns_by_module.get(module.get("module_id") or "", set()))

    system_role = str(user["system_role"])
    all_users = []
    if system_role == "owner":
        for listed_user in AdminService().list_users():
            listed = dict(listed_user)
            listed["campaign_count"] = len(campaign_service.list_for_user(listed["id"]))
            all_users.append(listed)

    return Template(
        template_name="pages/inside/index.html",
        context=view_context(
            cookies,
            app_name=inside_settings["app"]["app_name"] or config.app_name,
            user={
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "system_role": system_role,
                "is_owner": system_role == "owner",
            },
            campaigns=campaigns,
            available_systems=available_systems,
            installed_systems=installed_systems,
            installed_modules=installed_modules,
            module_campaigns=module_campaigns,
            all_users=all_users,
            inside_settings=inside_settings["app"],
            privacy_settings=inside_settings["privacy"],
            pending_invitations=[dict(invitation) for invitation in pending_invitations],
            campaign_error_key=campaign_error_key,
            campaign_message_key=campaign_message_key,
            invitation_error_key=invitation_error_key,
            invitation_message_key=invitation_message_key,
            systems_error_key=systems_error_key,
            systems_message_key=systems_message_key,
            modules_error_key=modules_error_key,
            modules_message_key=modules_message_key,
            admin_error_key=admin_error_key,
            admin_message_key=admin_message_key,
            settings_error_key=settings_error_key,
            settings_message_key=settings_message_key,
            privacy_error_key=privacy_error_key,
            privacy_message_key=privacy_message_key,
            pending_delete_campaign_id=pending_delete_campaign_id,
            removal_code=removal_code,
        ),
    )
