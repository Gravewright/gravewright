"""Emissores de partícula: efeito de cena que não ilumina.

A separação é o ponto. Vela, fogueira, arcana e fumaça moravam no foco de luz
porque era o lugar que existia, e o editor de foco acabou cheio de controles que
não acendiam nada. Aqui não há raio claro, intensidade nem ângulo: há tipo,
escala, densidade e cor.
"""
from __future__ import annotations

from litestar.testing import TestClient

from app.engine.scenes.scene_particle_service import KINDS, SceneParticleService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_scene, seed_user


def _gm_scene():
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)
    return gm, campaign, scene, SceneParticleService()


def test_an_emitter_is_born_with_workable_defaults(db):
    gm, campaign, scene, service = _gm_scene()

    emitter = service.create(
        campaign_id=campaign, scene_id=scene["id"], user_id=gm, x=10, y=20
    ).payload["emitter"]

    assert emitter["kind"] == "smoke"
    assert emitter["scale"] == 3.0 and emitter["density"] == 0.6
    assert emitter["enabled"] == 1
    # Nada de raio claro, intensidade ou ângulo: emissor não é fonte de luz.
    assert "intensity" not in emitter and "bright_radius" not in emitter


def test_every_kind_is_accepted(db):
    gm, campaign, scene, service = _gm_scene()
    made = service.create(campaign_id=campaign, scene_id=scene["id"], user_id=gm, x=0, y=0).payload["emitter"]

    for kind in KINDS:
        updated = service.update(
            campaign_id=campaign, emitter_id=made["id"], user_id=gm, kind=kind
        ).payload["emitter"]
        assert updated["kind"] == kind

    assert service.update(
        campaign_id=campaign, emitter_id=made["id"], user_id=gm, kind="chuva"
    ).error_key == "lighting.errors.invalid"


def test_density_is_the_performance_dial(db):
    """É o botão que o mestre baixa quando a cena fica pesada, sem ter de apagar
    o emissor e perder a composição que ele montou."""
    gm, campaign, scene, service = _gm_scene()
    made = service.create(campaign_id=campaign, scene_id=scene["id"], user_id=gm, x=0, y=0).payload["emitter"]

    quiet = service.update(campaign_id=campaign, emitter_id=made["id"], user_id=gm, density=0.1)
    assert quiet.payload["emitter"]["density"] == 0.1

    # Fora da faixa entra no limite em vez de ser recusado: a régua da interface
    # nunca manda valor inválido, e um número fora dela é engano, não ataque.
    assert service.update(
        campaign_id=campaign, emitter_id=made["id"], user_id=gm, density=9
    ).payload["emitter"]["density"] == 1.0
    assert service.update(
        campaign_id=campaign, emitter_id=made["id"], user_id=gm, scale=0.01
    ).payload["emitter"]["scale"] == 0.5


def test_only_the_gm_places_and_edits(db):
    from tests.conftest import seed_member

    gm, campaign, scene, service = _gm_scene()
    player = seed_user(name="Player")
    seed_member(campaign, player, "player")

    assert service.create(
        campaign_id=campaign, scene_id=scene["id"], user_id=player, x=0, y=0
    ).error_key == "lighting.errors.denied"

    made = service.create(campaign_id=campaign, scene_id=scene["id"], user_id=gm, x=0, y=0).payload["emitter"]
    assert service.update(
        campaign_id=campaign, emitter_id=made["id"], user_id=player, density=0.2
    ).error_key == "lighting.errors.denied"
    assert service.delete(
        campaign_id=campaign, emitter_id=made["id"], user_id=player
    ).error_key == "lighting.errors.denied"

    # Mas o jogador enxerga: a fumaça faz parte da cena que ele está jogando.
    assert service.state(
        campaign_id=campaign, scene_id=scene["id"], user_id=player
    ).payload["emitters"][0]["id"] == made["id"]


def test_the_route_round_trip(db):
    """A travessia inteira: rota, validação, banco, CHECK: para cada tipo."""
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for kind in KINDS:
            created = client.post("/game/particles", json={
                "campaign_id": campaign, "scene_id": scene["id"],
                "x": 120.0, "y": 240.0, "kind": kind,
                "scale": 4, "density": 0.5, "color": "#9aa3ad",
            })
            assert created.status_code == 201, (kind, created.text)
            emitter = created.json()["emitter"]
            assert emitter["kind"] == kind

            patched = client.post("/game/particles/update", json={
                "campaign_id": campaign, "emitter_id": emitter["id"], "density": 0.9,
            })
            assert patched.status_code == 200, patched.text
            assert patched.json()["emitter"]["density"] == 0.9

        listed = client.get(f"/game/particles/{scene['id']}", params={"campaign_id": campaign})
        assert listed.status_code == 200
        assert len(listed.json()["emitters"]) == len(KINDS)

        removed = client.post("/game/particles/delete", json={
            "campaign_id": campaign, "emitter_id": emitter["id"],
        })
        assert removed.status_code == 200, removed.text
