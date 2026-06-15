from __future__ import annotations

from app.persistence.rows import Row

from litestar import get
from litestar.params import FromQuery
from litestar.response import Redirect
from litestar.response import Template

from app.actions.inside.render_inside import split_packages
from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.business.campaigns.campaign_service import CampaignService
from app.business.admin.admin_service import AdminService
from app.business.inside_settings_service import InsideSettingsService
from app.config import config
from app.engine.sdk.package_activation_service import PackageActivationService
from app.engine.sdk.package_dependency_service import PackageDependencyService
from app.engine.sdk.package_install_service import PackageInstallService
from app.helpers.auth import require_user
from app.helpers.view import view_context


@get("/inside", guards=[require_user])
async def show_inside(
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    campaign_invitation_service: CampaignInvitationService,
    package_install_service: PackageInstallService,
    campaign_error_key: FromQuery[str | None] = None,
    campaign_message_key: FromQuery[str | None] = None,
    invitation_error_key: FromQuery[str | None] = None,
    invitation_message_key: FromQuery[str | None] = None,
    packages_error_key: FromQuery[str | None] = None,
    packages_message_key: FromQuery[str | None] = None,
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
    pending_invitations = campaign_invitation_service.list_pending_for_user(user["id"])
    packages = package_install_service.list_for_tab()
    rulesets, modules = split_packages(packages)
    inside_settings = InsideSettingsService().read()
    package_activation_service = PackageActivationService()
    dependency_service = PackageDependencyService()

    ruleset_name_by_id = {p["id"]: p["name"] for p in rulesets}
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
    campaigns = []
    for c in campaign_service.list_for_user(user["id"]):
        row = dict(c)
        row["active_ruleset_name"] = ruleset_name_by_id.get(row.get("active_system_id"))
        active_package_ids = {
            package["package_id"]
            for package in package_activation_service.list_campaign_packages(row["id"])
            if package["activation_role"] != "ruleset"
        }
        available_packages = []
        for package in modules:
            if package["status"] != "enabled" or package["kind"] == "library":
                continue
            is_active = package["id"] in active_package_ids
            # Explain why an inactive package cannot be activated in this campaign
            # (missing/disabled/inactive/outdated/too-new dependency, or a conflict
            # with an already-active package). Active packages need no reason.
            blockers: list[str] = []
            if not is_active:
                report = dependency_service.check_campaign_activation(package["id"], row["id"])
                blockers = PackageDependencyService.blocking_error_keys(report)
            available_packages.append(
                {
                    "id": package["id"],
                    "name": package["name"],
                    "kind": package["kind"],
                    "version": package["version"],
                    "active": is_active,
                    "blockers": blockers,
                    "activatable": is_active or not blockers,
                }
            )
        row["available_packages"] = available_packages
        campaigns.append(row)

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
            packages=packages,
            rulesets=rulesets,
            modules=modules,
            all_users=all_users,
            inside_settings=inside_settings["app"],
            privacy_settings=inside_settings["privacy"],
            pending_invitations=[dict(invitation) for invitation in pending_invitations],
            campaign_error_key=campaign_error_key,
            campaign_message_key=campaign_message_key,
            invitation_error_key=invitation_error_key,
            invitation_message_key=invitation_message_key,
            packages_error_key=packages_error_key,
            packages_message_key=packages_message_key,
            systems_error_key=packages_error_key,
            systems_message_key=packages_message_key,
            modules_error_key=packages_error_key,
            modules_message_key=packages_message_key,
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
