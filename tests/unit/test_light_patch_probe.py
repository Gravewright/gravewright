"""Sonda: cada campo do editor de foco, um por vez, pela rota HTTP real.

O painel manda um patch por campo mexido, entao e assim que a rota e exercitada
na mesa, e nao com o objeto inteiro, que e como os testes de servico chamavam.
"""
from litestar.testing import TestClient
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_scene, seed_user


def test_each_editor_field_patches_on_its_own(db):
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    patches = [
        {"bright_radius": 3},
        {"dim_radius": 7},
        {"intensity": 0.5},
        {"angle": 60},
        {"rotation": 90},
        {"animation": "pulse"},
        {"color": "#33ccff"},
        {"enabled": False},
    ]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        created = client.post("/game/lights", json={
            "campaign_id": campaign, "scene_id": scene["id"],
            "x": 100.0, "y": 100.0, "animation": "torch",
            "bright_radius": 2, "dim_radius": 4, "color": "#ffd8a8", "intensity": 1,
        })
        assert created.status_code == 201, created.text
        light_id = created.json()["light"]["id"]

        for patch in patches:
            response = client.post("/game/lights/update", json={
                "campaign_id": campaign, "light_id": light_id, **patch,
            })
            assert response.status_code == 200, (patch, response.status_code, response.text)
