from __future__ import annotations

from app.persistence.rows import Row

from litestar.response import Template

from app.business.admin.admin_service import AdminService
from app.business.campaigns.campaign_service import CampaignService
from app.business.inside_settings_service import InsideSettingsService
from app.config import config
from app.domain.roles import SystemRole
from app.engine.sdk.package_install_service import PackageInstallService
from app.helpers.view import view_context


def split_packages(packages: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split installed packages into rulesets (the "Systems" block) and every
    other kind (the "Modules" block, where each card carries a kind marker)."""
    rulesets = [p for p in packages if p["kind"] == "ruleset"]
    modules = [p for p in packages if p["kind"] != "ruleset"]
    return rulesets, modules


def render_inside(
    *,
    cookies: dict[str, str],
    user: Row,
    campaign_service: CampaignService,
    package_install_service: PackageInstallService,
    campaign_error: str | None = None,
    campaign_message: str | None = None,
    pending_delete_campaign_id: str | None = None,
    removal_code: str | None = None,
) -> Template:
    is_owner = user["system_role"] == SystemRole.OWNER.value

    packages = package_install_service.list_for_tab()
    rulesets, modules = split_packages(packages)
    inside_settings = InsideSettingsService().read()
    ruleset_name_by_id = {p["id"]: p["name"] for p in rulesets}

    campaigns = []
    for c in campaign_service.list_for_user(user["id"]):
        row = dict(c)
        row["active_ruleset_name"] = ruleset_name_by_id.get(row.get("active_system_id"))
        campaigns.append(row)

    available_systems = [
        {
            "id": item["id"],
            "name": item["name"],
            "description": item.get("description", ""),
            "version": item["version"],
        }
        for item in rulesets
        if item["status"] == "enabled"
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
            packages=packages,
            rulesets=rulesets,
            modules=modules,
            all_users=all_users,
            inside_settings=inside_settings["app"],
            privacy_settings=inside_settings["privacy"],
            campaign_error=campaign_error,
            campaign_message=campaign_message,
            pending_delete_campaign_id=pending_delete_campaign_id,
            removal_code=removal_code,
            packages_error_key=None,
            packages_message_key=None,
            admin_error_key=None,
            admin_message_key=None,
            settings_error_key=None,
            settings_message_key=None,
            privacy_error_key=None,
            privacy_message_key=None,
        ),
    )
