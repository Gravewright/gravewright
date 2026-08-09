from __future__ import annotations

import time
import uuid

from litestar.testing import TestClient
from sqlalchemy import insert

from app.business.handouts import HandoutService
from app.business.handouts.presentation_ticket import issue_presentation_ticket
from app.persistence.database import engine_begin
from app.persistence.tables import items_core
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user


def _item(campaign_id: str, gm_id: str) -> str:
    item_id = uuid.uuid4().hex
    now = int(time.time())
    with engine_begin() as connection:
        connection.execute(insert(items_core).values(
            id=item_id, campaign_id=campaign_id, system_id="core", type="item",
            name="Secret", folder_id=None, portrait_asset_id=None, permissions_json="{}",
            external_data_ref=None, status="active", version=1,
            created_by_user_id=gm_id, created_at=now, updated_at=now,
        ))
    return item_id


def test_show_to_players_is_transient_and_normal_route_stays_denied(db):
    from main import app

    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    item_id = _item(campaign_id, gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as gm:
        login(gm, gm_id)
        shown = gm.post("/game/handouts/present", json={
            "campaign_id": campaign_id, "resource_type": "item", "resource_id": item_id,
            "subject_type": "user", "subject_id": player_id,
        })
    assert shown.status_code == 200, shown.text
    assert not HandoutService().can_view(
        campaign_id=campaign_id, user_id=player_id,
        resource_type="item", resource_id=item_id,
    )
    ticket = issue_presentation_ticket(
        campaign_id=campaign_id, user_id=player_id,
        resource_type="item", resource_id=item_id,
    )
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as player:
        login(player, player_id)
        presentation = player.get(f"/game/handouts/presentation/{ticket}")
        ordinary = player.get(f"/game/item/sheet/modal/{item_id}", follow_redirects=False)
    assert presentation.status_code == 200
    assert f'data-item-id="{item_id}"' in presentation.text
    assert ordinary.status_code in {302, 303, 307}


def test_presentation_ticket_is_bound_to_recipient(db):
    from main import app

    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    other_id = seed_user(name="Other")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    seed_member(campaign_id, other_id, "player")
    item_id = _item(campaign_id, gm_id)
    ticket = issue_presentation_ticket(
        campaign_id=campaign_id, user_id=player_id,
        resource_type="item", resource_id=item_id,
    )
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as other:
        login(other, other_id)
        response = other.get(f"/game/handouts/presentation/{ticket}")
    assert response.status_code == 403


def test_legacy_permission_grant_routes_are_not_exposed(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        assert client.post("/game/handouts/grant", json={"campaign_id": campaign_id}).status_code == 404
        assert client.post("/game/handouts/revoke", json={"campaign_id": campaign_id}).status_code == 404
        assert client.get("/game/handouts", params={"campaign_id": campaign_id}).status_code == 404
