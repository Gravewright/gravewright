"""A rota que salva metadados de cena precisa avisar a sala.

O modal de edição é AJAX e atualiza o canvas de quem editou pela própria
resposta (``syncCanvasFromResponse``). Sem um evento de sala, todo o resto da
mesa continuava com a grade, a escala e a escuridão antigas até recarregar a
página, o GM subia a escuridão, via a cena escurecer, e os jogadores não.
"""

from __future__ import annotations

import pytest
from litestar.testing import TestClient

from app.engine.scenes.scene_service import SceneService
from app.persistence.repositories.scene_repository import SceneRepository
from app.realtime.events import TransportEvent
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_scene, seed_user


@pytest.fixture
def captured_room_events(monkeypatch) -> list[dict]:
    """Grava cada ``to_room`` em vez de enviar."""
    from app.realtime.transport import RealtimeTransport

    events: list[dict] = []

    async def fake_to_room(self, *, room_id, event, payload):  # noqa: ANN001
        events.append({"room_id": room_id, "event": event, "payload": payload})

    monkeypatch.setattr(RealtimeTransport, "to_room", fake_to_room)
    return events


def _update_form(campaign_id: str, scene_id: str, **overrides) -> dict:
    form = {
        "campaign_id": campaign_id,
        "scene_id": scene_id,
        "name": "Porão",
        "group_id": "",
        "visibility": "players",
        "grid_visible": "on",
        "grid_color": "#6fddb4",
        "grid_opacity": "0.4",
        "darkness": "0.0",
        "tile_size": "",
        "image_scale": "",
    }
    form.update(overrides)
    return form


def test_saving_scene_metadata_announces_it_to_the_room(db, captured_room_events):
    from main import app

    gm = seed_user(name="GM", email="gm-scene-broadcast@test.com")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    import asyncio

    asyncio.run(SceneService().activate_scene(scene_id=scene["id"], user_id=gm))
    captured_room_events.clear()

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        response = client.post(
            "/game/scenes/update",
            data=_update_form(campaign, scene["id"], darkness="0.75"),
            follow_redirects=False,
        )

    assert response.status_code in (302, 303), response.text

    updates = [e for e in captured_room_events if e["event"] == TransportEvent.SCENE_UPDATED]
    assert len(updates) == 1, captured_room_events
    assert updates[0]["room_id"] == campaign
    assert updates[0]["payload"]["scene"]["darkness"] == 0.75
    assert updates[0]["payload"]["scene"]["id"] == scene["id"]

    # e o valor realmente foi gravado, não só anunciado
    assert float(SceneRepository().get_by_id(scene["id"])["darkness"]) == 0.75


def test_editing_a_stored_scene_stays_quiet(db, captured_room_events):
    """Uma cena guardada não está na mesa de ninguém: anunciá-la espalharia nome
    e dimensões de material que o GM ainda não revelou."""
    from main import app

    gm = seed_user(name="GM", email="gm-scene-quiet@test.com")
    campaign = seed_campaign(gm)
    live = seed_scene(campaign, name="Na mesa")
    stored = SceneRepository().create(
        campaign_id=campaign, name="Segredo do GM", width=700, height=700,
        tile_size=70, chunk_size=16,
    )

    import asyncio

    asyncio.run(SceneService().activate_scene(scene_id=live["id"], user_id=gm))
    captured_room_events.clear()

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        client.post(
            "/game/scenes/update",
            data=_update_form(campaign, stored["id"], name="Segredo do GM", darkness="0.9"),
            follow_redirects=False,
        )

    assert [e for e in captured_room_events if e["event"] == TransportEvent.SCENE_UPDATED] == []
    assert float(SceneRepository().get_by_id(stored["id"])["darkness"]) == 0.9, "gravou mesmo assim"
