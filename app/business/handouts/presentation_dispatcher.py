from __future__ import annotations

from app.business.handouts.presentation_ticket import issue_presentation_ticket
from app.domain.roles import PlayerRole
from app.helpers.async_blocking import run_blocking
from app.persistence.repositories.realtime_recipient_repository import RealtimeRecipientRepository
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport


async def dispatch_handout_presentation(grant: dict) -> None:
    recipients = RealtimeRecipientRepository()
    subject_type = grant["subject_type"]
    if subject_type == "user":
        user_ids = [grant["subject_id"]]
    elif subject_type == "role":
        try:
            role = PlayerRole(grant["subject_id"])
        except ValueError:
            return
        user_ids = await run_blocking(
            recipients.list_role_member_user_ids,
            room_id=grant["campaign_id"],
            role=role,
        )
    else:
        user_ids = await run_blocking(
            recipients.list_room_member_user_ids, grant["campaign_id"]
        )
    user_ids = [
        user_id for user_id in user_ids if user_id != grant["created_by_user_id"]
    ]
    transport = RealtimeTransport()
    for user_id in user_ids:
        ticket = issue_presentation_ticket(
            campaign_id=grant["campaign_id"],
            user_id=user_id,
            resource_type=grant["resource_type"],
            resource_id=grant["resource_id"],
        )
        await transport.to_player(
            player_id=user_id,
            event=TransportEvent.HANDOUT_PRESENTED,
            payload={"ticket": ticket, "resource_type": grant["resource_type"]},
        )
