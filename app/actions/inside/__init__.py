from __future__ import annotations

from app.actions.inside.accept_campaign_invitation import accept_campaign_invitation
from app.actions.inside.create_campaign import create_campaign
from app.actions.inside.clone_campaign import clone_campaign, preview_campaign_clone
from app.actions.inside.campaign_snapshots import route_handlers as snapshot_handlers
from app.actions.inside.administrative_audit import route_handlers as audit_handlers
from app.actions.inside.decline_campaign_invitation import decline_campaign_invitation
from app.actions.inside.delete_campaign import delete_campaign
from app.actions.inside.export_campaign import export_campaign
from app.actions.inside.import_campaign import import_campaign
from app.actions.inside.list_campaign_invitations import list_campaign_invitations
from app.actions.inside.manage_settings import update_inside_settings
from app.actions.inside.manage_settings import update_privacy_settings
from app.actions.inside.diagnostics import show_diagnostics
from app.actions.inside.request_delete_campaign import request_delete_campaign
from app.actions.inside.show_inside import show_inside
from app.actions.inside.update_campaign import update_campaign
from app.actions.inside.package_onboarding import dismiss_package_onboarding


route_handlers = [
    show_inside,
    create_campaign,
    clone_campaign,
    preview_campaign_clone,
    *snapshot_handlers,
    *audit_handlers,
    update_campaign,
    request_delete_campaign,
    delete_campaign,
    export_campaign,
    import_campaign,
    accept_campaign_invitation,
    decline_campaign_invitation,
    list_campaign_invitations,
    update_inside_settings,
    update_privacy_settings,
    show_diagnostics,
    dismiss_package_onboarding,
]
