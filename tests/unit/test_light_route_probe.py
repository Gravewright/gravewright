"""A rota de criacao de foco, com o payload exato que a ferramenta de luz manda.

Existe porque os testes de servico e as assercoes estaticas passavam enquanto a
criacao falhava na mesa: cada camada estava certa isolada. Este exercita a
travessia inteira — rota, validacao, banco, CHECK — para cada emissao.
"""
from litestar.testing import TestClient
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_scene, seed_user


def test_every_emission_survives_the_round_trip(db):
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        for animation in ("torch", "pulse", "none"):
            response = client.post("/game/lights", json={
                "campaign_id": campaign,
                "scene_id": scene["id"],
                "x": 120.0, "y": 240.0,
                "animation": animation,
                "bright_radius": 2, "dim_radius": 4,
                "color": "#ffd8a8", "intensity": 1,
            })
            assert response.status_code == 201, (animation, response.status_code, response.text)
            light = response.json()["light"]
            assert light["animation"] == animation
            assert light["angle"] == 360.0 and light["rotation"] == 0.0
