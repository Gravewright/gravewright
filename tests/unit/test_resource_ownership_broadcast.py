"""Trocar o dono de um recurso precisa avisar a sala.

Dar um ator a um jogador não fazia nada aparecer na tela dele: a rota gravava e
ficava calada. Pior no caso do ator, porque a posse alimenta
``controlled_by_user_ids``, que é de onde sai a visão de token — o jogador ganhava
o personagem e continuava sem enxergar por ele até recarregar a página.

O modal de permissões (``/game/resource-permissions``) já anunciava. Os dois
caminhos mudam a mesma coisa, então anunciam o mesmo evento.
"""

from __future__ import annotations

import pytest
from litestar.testing import TestClient

from app.realtime.events import TransportEvent
from app.realtime.resource_events import announce_resource_access_change
from tests.conftest import (
    TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_system, seed_user,
)


class FakeTransport:
    def __init__(self):
        self.events = []

    async def to_room(self, *, room_id, event, payload):
        self.events.append({"room_id": room_id, "event": event, "payload": payload})


@pytest.fixture
def captured_room_events(monkeypatch) -> list[dict]:
    from app.realtime.transport import RealtimeTransport

    events: list[dict] = []

    async def fake_to_room(self, *, room_id, event, payload):  # noqa: ANN001
        events.append({"room_id": room_id, "event": event, "payload": payload})

    monkeypatch.setattr(RealtimeTransport, "to_room", fake_to_room)
    return events


@pytest.mark.parametrize(
    "resource_type,event,id_field",
    [
        ("actor", TransportEvent.ACTOR_UPDATED, "actor_id"),
        ("item", TransportEvent.ITEM_UPDATED, "item_id"),
        ("journal", TransportEvent.JOURNAL_ACCESS_CHANGED, "journal_id"),
    ],
)
async def test_each_resource_type_has_its_event(resource_type, event, id_field):
    transport = FakeTransport()
    assert await announce_resource_access_change(
        resource_type=resource_type, resource_id="r1",
        campaign_id="c1", updated_by="u1", transport=transport,
    )
    assert transport.events == [{
        "room_id": "c1",
        "event": event,
        "payload": {"room_id": "c1", id_field: "r1", "updated_by": "u1"},
    }]


async def test_unknown_resource_or_missing_campaign_stays_quiet():
    transport = FakeTransport()
    assert not await announce_resource_access_change(
        resource_type="spaceship", resource_id="r1",
        campaign_id="c1", updated_by="u1", transport=transport,
    )
    assert not await announce_resource_access_change(
        resource_type="actor", resource_id="r1",
        campaign_id=None, updated_by="u1", transport=transport,
    )
    assert transport.events == []


def test_granting_an_actor_announces_it_to_the_room(db, captured_room_events):
    from main import app
    from app.engine.actors.actor_service import ActorService
    from app.persistence.repositories.actor_repository import ActorRepository

    gm = seed_user(name="GM", email="gm-owner-actor@test.com")
    player = seed_user(name="Player", email="player-owner-actor@test.com")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    system = seed_system(campaign, gm)
    actor_id = ActorRepository().create(
        campaign_id=campaign, system_id=system, actor_type="character",
        name="Rogue", created_by_user_id=gm,
    )
    captured_room_events.clear()

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        response = client.post(
            "/game/actor/owner",
            data={"actor_id": actor_id, "owner_user_id": player},
            headers={"Accept": "application/json"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["is_owner"] is True

    updates = [e for e in captured_room_events if e["event"] == TransportEvent.ACTOR_UPDATED]
    assert len(updates) == 1, captured_room_events
    assert updates[0]["room_id"] == campaign
    assert updates[0]["payload"]["actor_id"] == actor_id

    # e a posse chegou de verdade — é dela que a visão de token depende
    assert player in [o["id"] for o in ActorService().list_owners(actor_id=actor_id)]


def test_a_refused_toggle_announces_nothing(db, captured_room_events):
    """Jogador não concede posse; sem sucesso não pode haver anúncio."""
    from main import app
    from app.persistence.repositories.actor_repository import ActorRepository

    gm = seed_user(name="GM", email="gm-owner-denied@test.com")
    player = seed_user(name="Player", email="player-owner-denied@test.com")
    other = seed_user(name="Other", email="other-owner-denied@test.com")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    seed_member(campaign, other, "player")
    system = seed_system(campaign, gm)
    actor_id = ActorRepository().create(
        campaign_id=campaign, system_id=system, actor_type="character",
        name="Rogue", created_by_user_id=gm,
    )
    captured_room_events.clear()

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        client.post(
            "/game/actor/owner",
            data={"actor_id": actor_id, "owner_user_id": other},
            headers={"Accept": "application/json"},
        )

    assert [e for e in captured_room_events if e["event"] == TransportEvent.ACTOR_UPDATED] == []
