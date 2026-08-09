from __future__ import annotations

from litestar.testing import TestClient
from litestar.middleware.csrf import generate_csrf_token

from app.config import config
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.realtime.events import TransportEvent
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_management_endpoints_generate_hide_and_revoke_code(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        generated = client.post(
            "/campaigns/join-code/generate",
            data={"csrf_token": csrf, "campaign_id": campaign_id, "max_uses": "3"},
            headers={"Accept": "application/json"},
        )
        assert generated.status_code == 200, generated.text
        payload = generated.json()
        assert payload["ok"] is True
        assert payload["code"]
        assert payload["masked_code"] == "****-****-****"
        assert generated.headers["cache-control"].startswith("no-store")

        status = client.get(
            "/campaigns/join-code/status",
            params={"campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        )
        assert status.status_code == 200
        assert status.json()["join_code"]["masked_code"] == "****-****-****"
        assert "code" not in status.json()["join_code"]
        assert "code_hash" not in status.json()["join_code"]

        revoked = client.post(
            "/campaigns/join-code/revoke",
            data={"csrf_token": csrf, "campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        )
        assert revoked.status_code == 200
        assert revoked.json()["revoked_at"] is not None


def test_generate_accepts_csrf_from_rendered_form_without_header(db):
    """Browser form remains valid if the JS header helper is unavailable."""
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        client.headers.pop("x-csrftoken")
        response = client.post(
            "/campaigns/join-code/generate",
            data={
                "_csrf_token": csrf,
                "campaign_id": campaign_id,
                "expires_in_hours": "168",
                "role": "player",
            },
            headers={"Accept": "application/json"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["ok"] is True


def test_join_code_modal_embeds_csrf_fallback(db):
    from main import app

    gm_id = seed_user(name="GM")
    seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        page = client.get("/game")

    assert 'class="join-code-form"' in page.text
    form = page.text.split('class="join-code-form"', 1)[1].split("</form>", 1)[0]
    assert 'name="_csrf_token"' in form


def test_public_join_preserves_code_without_leaking_it_in_redirect(db):
    from main import app

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        response = client.get("/join/ABCD-EFGH-JK23", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/login"
        assert "ABCD-EFGH-JK23" not in response.headers["location"]
        assert client.get_session_data()["pending_campaign_join_code"] == "ABCD-EFGH-JK23"


def test_redeem_uses_pending_session_code_and_broadcasts_once(db, monkeypatch):
    from main import app

    events: list[TransportEvent] = []

    async def capture(self, *, room_id, event, payload):  # noqa: ANN001
        events.append(event)

    monkeypatch.setattr("app.realtime.transport.RealtimeTransport.to_room", capture)
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as gm:
        csrf = login(gm, gm_id)
        generated = gm.post(
            "/campaigns/join-code/generate",
            data={"csrf_token": csrf, "campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        ).json()

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as player:
        csrf = login(player, player_id)
        player.get(f"/join/{generated['code']}", follow_redirects=False)
        first = player.post(
            "/campaigns/join-code/redeem",
            data={"csrf_token": csrf, "code": ""},
            headers={"Accept": "application/json"},
        )
        second = player.post(
            "/campaigns/join-code/redeem",
            data={"csrf_token": csrf, "code": generated["code"]},
            headers={"Accept": "application/json"},
        )

    assert first.status_code == 200, first.text
    assert first.json()["membership_created"] is True
    assert first.json()["redirect"].startswith("/game?")
    assert second.status_code == 200
    assert second.json()["membership_created"] is False
    assert events.count(TransportEvent.MEMBER_JOINED) == 1
    assert CampaignRepository().get_member(campaign_id=campaign_id, user_id=player_id)


def test_non_manager_cannot_read_join_code_status(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider_id)
        response = client.get(
            "/campaigns/join-code/status",
            params={"campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        )
    assert response.status_code == 403
    assert response.json()["error_key"] == "campaign.join_code.errors.permission_denied"


def test_public_link_survives_login_and_redeems_from_server_session(db, monkeypatch):
    from main import app

    async def discard_event(self, *, room_id, event, payload):  # noqa: ANN001
        return None

    monkeypatch.setattr("app.realtime.transport.RealtimeTransport.to_room", discard_event)
    gm_id = seed_user(name="GM")
    player_email = "join-link-player@test.com"
    player_id = seed_user(name="Player", email=player_email)
    campaign_id = seed_campaign(gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as gm:
        csrf = login(gm, gm_id)
        code = gm.post(
            "/campaigns/join-code/generate",
            data={"csrf_token": csrf, "campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        ).json()["code"]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as player:
        captured = player.get(f"/join/{code}", follow_redirects=False)
        assert captured.headers["location"] == "/login"
        csrf = generate_csrf_token(config.session_secret)
        player.cookies.set("csrftoken", csrf)
        player.headers["x-csrftoken"] = csrf
        authenticated = player.post(
            "/login",
            data={"csrf_token": csrf, "email": player_email, "password": "Password1!"},
            follow_redirects=False,
        )
        assert authenticated.headers["location"] == "/inside?join_code_pending=1"
        inside = player.get(authenticated.headers["location"])
        assert "data-inside-redeem-pending" in inside.text
        redeemed = player.post(
            "/campaigns/join-code/redeem",
            data={"csrf_token": csrf, "code": ""},
            headers={"Accept": "application/json"},
        )

    assert redeemed.status_code == 200, redeemed.text
    assert redeemed.json()["redirect"] == f"/game?room={campaign_id}"
    assert CampaignRepository().get_member(campaign_id=campaign_id, user_id=player_id)


def test_public_link_survives_registration(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as gm:
        csrf = login(gm, gm_id)
        code = gm.post(
            "/campaigns/join-code/generate",
            data={"csrf_token": csrf, "campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        ).json()["code"]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as player:
        player.get(f"/join/{code}", follow_redirects=False)
        csrf = generate_csrf_token(config.session_secret)
        player.cookies.set("csrftoken", csrf)
        player.headers["x-csrftoken"] = csrf
        registered = player.post(
            "/register",
            data={
                "csrf_token": csrf,
                "name": "New Player",
                "email": "new-join-player@test.com",
                "password": "Password1!",
            },
            follow_redirects=False,
        )
        assert registered.headers["location"] == "/inside?join_code_pending=1"
        inside = player.get(registered.headers["location"])
        assert inside.status_code == 200
        assert "data-inside-redeem-pending" in inside.text
