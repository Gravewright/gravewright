from __future__ import annotations

from app.actions.inside.accept_campaign_invitation import accept_campaign_invitation
from app.actions.inside.create_campaign import create_campaign
from app.actions.inside.decline_campaign_invitation import decline_campaign_invitation
from app.actions.inside.delete_campaign import delete_campaign
from app.actions.inside.list_campaign_invitations import list_campaign_invitations
from app.actions.inside.manage_settings import update_inside_settings
from app.actions.inside.manage_settings import update_privacy_settings
from app.actions.inside.diagnostics import show_diagnostics
from app.actions.inside.request_delete_campaign import request_delete_campaign
from app.actions.inside.show_inside import show_inside
from app.actions.inside.update_campaign import update_campaign


route_handlers = [
    show_inside,
    create_campaign,
    update_campaign,
    request_delete_campaign,
    delete_campaign,
    accept_campaign_invitation,
    decline_campaign_invitation,
    list_campaign_invitations,
    update_inside_settings,
    update_privacy_settings,
    show_diagnostics,
]
