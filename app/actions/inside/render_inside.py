from __future__ import annotations

from app.persistence.rows import Row

from litestar.response import Template

from app.business.admin.admin_service import AdminService
from app.business.campaigns.campaign_service import CampaignService
from app.business.inside_settings_service import InsideSettingsService
from app.config import config
from app.domain.roles import SystemRole
from app.engine.systems.system_install_service import SystemInstallService
from app.engine.modules.module_install_service import ModuleInstallService
from app.helpers.view import view_context


def render_inside(
    *,
    cookies: dict[str, str],
    user: Row,
    campaign_service: CampaignService,
    system_install_service: SystemInstallService,
    module_install_service: ModuleInstallService,
    campaign_error: str | None = None,
    campaign_message: str | None = None,
    pending_delete_campaign_id: str | None = None,
    removal_code: str | None = None,
) -> Template:
    is_owner = user["system_role"] == SystemRole.OWNER.value

    installed_systems = system_install_service.list_for_tab()
    installed_modules = module_install_service.list_for_tab()
    inside_settings = InsideSettingsService().read()
    installed_by_id = {item["system_id"]: item["name"] for item in installed_systems if item["system_id"]}

    campaigns_raw = campaign_service.list_for_user(user["id"])
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
    all_users = []
    if is_owner:
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
                "system_role": user["system_role"],
                "is_owner": is_owner,
            },
            campaigns=campaigns,
            available_systems=available_systems,
            installed_systems=installed_systems,
            installed_modules=installed_modules,
            module_campaigns=module_campaigns,
            all_users=all_users,
            inside_settings=inside_settings["app"],
            privacy_settings=inside_settings["privacy"],
            campaign_error=campaign_error,
            campaign_message=campaign_message,
            pending_delete_campaign_id=pending_delete_campaign_id,
            removal_code=removal_code,
            modules_error_key=None,
            modules_message_key=None,
            admin_error_key=None,
            admin_message_key=None,
            settings_error_key=None,
            settings_message_key=None,
            privacy_error_key=None,
            privacy_message_key=None,
        ),
    )
