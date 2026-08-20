"""Route wiring for the Streamer Mode link: generate / revoke / public consume."""

from __future__ import annotations

from litestar.testing import TestClient

from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_repository import CampaignRepository
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_generate_and_consume_streamer_link(db):
    from main import app

    gm_id = seed_user(name="GM", email="sl-ep-gm@test.com")
    campaign_id = seed_campaign(gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        generated = client.post("/game/streamer-link", data={"campaign_id": campaign_id})
        assert generated.status_code == 200
        body = generated.json()
        assert body["ok"] is True
        assert "/stream/" in body["url"]

    token = body["url"].split("/stream/", 1)[1]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as viewer:
        resp = viewer.get(f"/stream/{token}", follow_redirects=False)
        assert resp.status_code in (301, 302, 303, 307, 308)
        assert resp.headers["location"] == "/game"

        page = viewer.get("/game")
        assert page.status_code == 200
        body = page.text
        assert 'data-lighting-gm="true"' in body
        assert 'class="layer-hud"' in body
        assert 'data-active-layer="effects"' in body
        assert 'data-active-layer="walls"' in body
        assert f'data-modal-id="light-editor-{campaign_id}"' in body
        assert f'data-modal-id="particle-editor-{campaign_id}"' in body
        assert f'data-modal-id="shader-editor-{campaign_id}"' in body
        # Cenas deixou de ser modal e virou painel de diretório, alcançado pela
        # aba do rail; Decks e Assets desceram para Configurações.
        assert f'data-panel-toggle="panel-scenes-{campaign_id}"' in body
        assert f'data-modal-id="panel-scenes-{campaign_id}"' in body
        assert f'data-modal-open="panel-cards-{campaign_id}"' in body
        assert f'data-modal-open="library-images-{campaign_id}"' in body
        assert f'data-modal-id="library-images-{campaign_id}"' in body

        # O streamer lê a biblioteca de cenas, mas não cria: criar cena e pasta
        # são do GM, e roles.py garante que ele nunca muta o estado da mesa.
        painel = body.split(f'data-modal-id="panel-scenes-{campaign_id}"', 1)[1].split("</article>", 1)[0]
        assert f'data-modal-open="scene-create-{campaign_id}"' not in painel
        assert f'data-modal-open="scene-group-create-{campaign_id}"' not in painel

    members = CampaignRepository().list_members(campaign_id=campaign_id)
    roles = {m["role"] for m in members}
    assert PlayerRole.STREAMER.value in roles


def test_consume_invalid_token_redirects_to_login(db):
    from main import app

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as viewer:
        resp = viewer.get("/stream/nope-not-real", follow_redirects=False)
        assert resp.status_code in (301, 302, 303, 307, 308)
        assert resp.headers["location"] == "/login"


def test_non_gm_cannot_generate_via_endpoint(db):
    from main import app

    gm_id = seed_user(name="GM", email="sl-ep-gm2@test.com")
    player_id = seed_user(name="Player", email="sl-ep-player@test.com")
    campaign_id = seed_campaign(gm_id)
    from tests.conftest import seed_member

    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player_id)
        resp = client.post("/game/streamer-link", data={"campaign_id": campaign_id})
        assert resp.status_code == 403
        assert resp.json()["error_key"] == "game.streamer.errors.gm_required"
