from __future__ import annotations

from app.persistence.rows import Row

from litestar import Request, get
from litestar.params import FromQuery
from litestar.response import Redirect
from litestar.response import Template

from app.actions.inside.render_inside import (
    bind_published_update_channels, hide_unpublished_core_channel, split_packages,
)
from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.business.campaigns.campaign_service import CampaignService
from app.business.campaigns.campaign_snapshot_service import CampaignSnapshotService
from app.business.admin.admin_service import AdminService
from app.business.audit import catalog as audit_catalog
from app.business.inside_settings_service import InsideSettingsService
from app.business.core_update_service import CoreUpdateService
from app.business.users import UserPreferenceService
from app.config import config
from app.engine.sdk.package_activation_service import PackageActivationService
from app.engine.sdk.package_dependency_service import PackageDependencyService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.marketplace_service import MarketplaceService
from app.helpers.auth import require_user
from app.helpers.pending_join_code import (
    PENDING_JOIN_CODE_KEY,
    clear_pending_join_code,
    get_pending_join_code,
)
from app.helpers.view import view_context


@get("/inside", guards=[require_user], sync_to_thread=True)
def show_inside(
    request: Request,
    cookies: dict[str, str],
    current_user: Row,
    campaign_service: CampaignService,
    campaign_invitation_service: CampaignInvitationService,
    package_install_service: PackageInstallService,
    campaign_snapshot_service: CampaignSnapshotService,
    user_preference_service: UserPreferenceService,
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
    join_code_pending: FromQuery[str | None] = None,
) -> Redirect | Template:
    user = current_user
    pending_invitations = campaign_invitation_service.list_pending_for_user(user["id"])
    packages = package_install_service.list_for_tab()
    rulesets, modules = split_packages(packages)
    # Entering Inside is navigation-critical. A stale remote registry must not
    # hold the browser on the game page while DNS/TLS/download work completes.
    marketplace = MarketplaceService().catalog()
    marketplace_bands = {
        kind: [item for item in marketplace.get("packages", []) if item.get("kind") == kind]
        for kind in ("ruleset", "addon", "library", "content", "theme", "assets")
    }
    inside_settings = InsideSettingsService().read()
    update_settings = bind_published_update_channels(inside_settings["updates"], marketplace)
    package_activation_service = PackageActivationService()
    dependency_service = PackageDependencyService()
    pending_join_code = get_pending_join_code(request.session)
    if pending_join_code is None and PENDING_JOIN_CODE_KEY in request.session:
        request.set_session(clear_pending_join_code(request.session))

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
        row["has_inactive_packages"] = row.get("member_role") == "gm" and any(
            not package["active"] for package in available_packages
        )
        row["snapshots"] = (
            campaign_snapshot_service.list_for_campaign(
                campaign_id=row["id"], user_id=str(user["id"])
            ).preview.get("snapshots", [])
            if row.get("member_role") == "gm" and config.campaign_snapshots_enabled
            else []
        )
        campaigns.append(row)

    system_role = str(user["system_role"])
    all_users = []
    if system_role == "owner":
        for listed_user in AdminService().list_users():
            listed = dict(listed_user)
            listed["campaign_count"] = len(campaign_service.list_for_user(listed["id"]))
            all_users.append(listed)

    show_package_onboarding = (
        any(campaign["has_inactive_packages"] for campaign in campaigns)
        and not user_preference_service.has_seen_package_onboarding(str(user["id"]))
    )

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
            show_package_onboarding=show_package_onboarding,
            audit_event_types=audit_catalog.EVENT_TYPES,
            audit_metadata_fields=audit_catalog.METADATA_FIELDS,
            available_systems=available_systems,
            packages=packages,
            rulesets=rulesets,
            modules=modules,
            marketplace=marketplace,
            marketplace_bands=marketplace_bands,
            all_users=all_users,
            inside_settings=inside_settings["app"],
            update_settings=update_settings,
            core_update=hide_unpublished_core_channel(CoreUpdateService().status(), update_settings),
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
            has_pending_join_code=pending_join_code is not None,
            campaign_join_code_enabled=config.campaign_join_code_enabled,
            campaign_clone_enabled=config.campaign_clone_enabled,
            campaign_snapshots_enabled=config.campaign_snapshots_enabled,
            administrative_audit_enabled=config.administrative_audit_enabled,
            campaign_export_enabled=config.campaign_export_enabled,
        ),
    )
