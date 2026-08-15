from __future__ import annotations

"""HTTP-level invitation regression flow (post-maintenance plan, Etapa 1 / 5.1-5.2).

Drives the real endpoints: create campaign, invite, accept, remove or ban,
replay the accept, and asserts the realtime MEMBER_JOINED broadcast fires
exactly once, on the single accept that actually created the membership.
"""

import pytest
from litestar.testing import TestClient

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_invitation_repository import (
    CampaignInvitationRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.realtime.events import TransportEvent
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


@pytest.fixture
def captured_room_events(monkeypatch) -> list[tuple[str, TransportEvent]]:
    """Record every ``to_room`` broadcast instead of sending it."""
    from app.realtime.transport import RealtimeTransport

    events: list[tuple[str, TransportEvent]] = []

    async def fake_to_room(self, *, room_id, event, payload):  # noqa: ANN001
        events.append((room_id, event))

    monkeypatch.setattr(RealtimeTransport, "to_room", fake_to_room)
    return events


def _invite_and_get_id(campaign_id: str, gm_id: str, player_id: str, email: str) -> str:
    result = CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email=email,
        role=PlayerRole.PLAYER.value,
    )
    assert result.success, result.error_key
    pending = CampaignInvitationRepository().list_pending_for_user(player_id)
    match = [row for row in pending if row["campaign_id"] == campaign_id]
    assert match, "expected a pending invitation"
    return match[0]["id"]


def _accept(client, csrf: str, invitation_id: str):
    return client.post(
        "/campaigns/invitations/accept",
        data={"csrf_token": csrf, "invitation_id": invitation_id},
        headers={"Accept": "application/json"},
    )


def _member_count(campaign_id: str, user_id: str) -> int:
    members = CampaignRepository().list_members(campaign_id=campaign_id)
    return len([m for m in members if m["user_id"] == user_id])


def test_removed_member_cannot_replay_accepted_invitation(db, captured_room_events):
    from main import app

    email = "player-replay-ep@test.com"
    gm_id = seed_user(name="GM", email="gm-replay-ep@test.com")
    player_id = seed_user(name="Player", email=email)
    campaign_id = seed_campaign(gm_id, title="Replay Endpoint")
    invitation_id = _invite_and_get_id(campaign_id, gm_id, player_id, email)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, player_id)

        first = _accept(client, csrf, invitation_id)
        assert first.status_code == 200, first.text
        assert first.json()["membership_created"] is True
        assert _member_count(campaign_id, player_id) == 1

        CampaignRepository().remove_member(campaign_id=campaign_id, user_id=player_id)

        replay = _accept(client, csrf, invitation_id)
        assert replay.status_code == 400, replay.text
        assert replay.json()["error_key"] == "inside.invitations.errors.membership_removed"

    assert _member_count(campaign_id, player_id) == 0
    joined = [e for e in captured_room_events if e[1] is TransportEvent.MEMBER_JOINED]
    assert len(joined) == 1, "MEMBER_JOINED must fire only for the real creation"


def test_banned_member_cannot_replay_accepted_invitation(db, captured_room_events):
    from app.business.campaigns.campaign_service import CampaignService
    from main import app

    email = "player-ban-ep@test.com"
    gm_id = seed_user(name="GM", email="gm-ban-ep@test.com")
    player_id = seed_user(name="Player", email=email)
    campaign_id = seed_campaign(gm_id, title="Ban Endpoint")
    invitation_id = _invite_and_get_id(campaign_id, gm_id, player_id, email)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, player_id)
        assert _accept(client, csrf, invitation_id).status_code == 200

        banned = CampaignService().ban_member(
            campaign_id=campaign_id,
            requester_user_id=gm_id,
            target_user_id=player_id,
        )
        assert banned.success, banned.error_key

        replay = _accept(client, csrf, invitation_id)
        assert replay.status_code == 400, replay.text
        assert replay.json()["error_key"] == "inside.invitations.errors.membership_removed"

    assert _member_count(campaign_id, player_id) == 0
    joined = [e for e in captured_room_events if e[1] is TransportEvent.MEMBER_JOINED]
    assert len(joined) == 1


def test_repeated_accept_is_idempotent_and_broadcasts_once(db, captured_room_events):
    from main import app

    email = "player-idem-ep@test.com"
    gm_id = seed_user(name="GM", email="gm-idem-ep@test.com")
    player_id = seed_user(name="Player", email=email)
    campaign_id = seed_campaign(gm_id, title="Idempotent Endpoint")
    invitation_id = _invite_and_get_id(campaign_id, gm_id, player_id, email)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, player_id)
        first = _accept(client, csrf, invitation_id)
        second = _accept(client, csrf, invitation_id)

    assert first.json()["membership_created"] is True
    assert second.status_code == 200, second.text
    assert second.json()["membership_created"] is False
    assert _member_count(campaign_id, player_id) == 1

    joined = [e for e in captured_room_events if e[1] is TransportEvent.MEMBER_JOINED]
    assert len(joined) == 1
