"""Partir uma parede, e apagar uma seleção inteira de uma vez.

As duas nasceram do mesmo atrito de montar cena: corrigir o meio de uma parede
longa obrigava a apagar e redesenhar as duas metades, e limpar um canto do mapa
era clicar item por item.
"""
from litestar.testing import TestClient
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user


def _wall(client, campaign, scene, **extra):
    body = {"campaign_id": campaign, "scene_id": scene["id"], "kind": "wall",
            "x1": 100.0, "y1": 100.0, "x2": 500.0, "y2": 100.0, **extra}
    return client.post("/game/walls", json=body).json()["wall"]


def test_splitting_a_wall_keeps_the_line_and_adds_a_node(db):
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        wall = _wall(client, campaign, scene)

        # O ponto do duplo clique quase nunca cai exatamente sobre a linha; ele é
        # projetado no segmento antes do corte, senão a parede dobraria em vez de
        # se dividir.
        split = client.post("/game/walls/split", json={
            "campaign_id": campaign, "wall_id": wall["id"], "x": 300.0, "y": 118.0,
        })
        assert split.status_code == 200, split.text
        walls = split.json()["walls"]
        assert len(walls) == 2

        first = next(w for w in walls if w["id"] == wall["id"])
        second = next(w for w in walls if w["id"] != wall["id"])
        # As duas metades continuam sendo a mesma linha: ponta a ponta, sem desvio.
        assert (first["x1"], first["y1"]) == (100.0, 100.0)
        assert (second["x2"], second["y2"]) == (500.0, 100.0)
        assert (first["x2"], first["y2"]) == (second["x1"], second["y1"]) == (300.0, 100.0)


def test_a_split_door_stays_a_door_on_both_halves(db):
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        door = _wall(client, campaign, scene, kind="door")
        client.post("/game/walls/door-state", json={
            "campaign_id": campaign, "wall_id": door["id"], "door_state": "locked",
        })

        walls = client.post("/game/walls/split", json={
            "campaign_id": campaign, "wall_id": door["id"], "x": 300.0, "y": 100.0,
        }).json()["walls"]
        # Partir uma porta trancada tem de devolver duas portas trancadas: o
        # contrário abre passagem sem ninguém ter destrancado nada.
        assert {w["kind"] for w in walls} == {"door"}
        assert {w["door_state"] for w in walls} == {"locked"}


def test_a_cut_too_close_to_the_end_is_refused(db):
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        wall = _wall(client, campaign, scene)
        # Um toco menor que a tolerância do nó é impossível de pegar e some no
        # próximo arrasto: melhor recusar do que criar lixo invisível.
        refused = client.post("/game/walls/split", json={
            "campaign_id": campaign, "wall_id": wall["id"], "x": 102.0, "y": 100.0,
        })
        assert refused.status_code == 400
        assert len(client.get(f"/game/walls/{scene['id']}", params={"campaign_id": campaign}).json()["walls"]) == 1


def test_a_player_cannot_split(db):
    from main import app
    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        wall = _wall(client, campaign, scene)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        assert client.post("/game/walls/split", json={
            "campaign_id": campaign, "wall_id": wall["id"], "x": 300.0, "y": 100.0,
        }).status_code == 403


def test_bulk_delete_takes_the_whole_selection_in_one_request(db):
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        walls = [_wall(client, campaign, scene, y1=float(i * 20), y2=float(i * 20)) for i in range(5)]

        removed = client.post("/game/walls/delete-many", json={
            "campaign_id": campaign, "wall_ids": [w["id"] for w in walls[:3]],
        })
        assert removed.status_code == 200
        assert len(removed.json()["wall_ids"]) == 3
        left = client.get(f"/game/walls/{scene['id']}", params={"campaign_id": campaign}).json()["walls"]
        assert {w["id"] for w in left} == {w["id"] for w in walls[3:]}


def test_bulk_delete_ignores_what_is_not_ours_instead_of_failing(db):
    """Uma seleção pode conter o que outra pessoa já apagou.

    Recusar o lote inteiro por causa de um item transformaria uma corrida comum em
    erro na cara do mestre; obedecer a qualquer id seria a porta aberta para
    apagar cena de outra mesa. Apagar só o que é daqui resolve os dois.
    """
    from main import app
    gm = seed_user(name="GM")
    outsider = seed_user(name="Outro GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)
    other_campaign = seed_campaign(outsider)
    other_scene = seed_scene(other_campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider)
        alheia = _wall(client, other_campaign, other_scene)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        minha = _wall(client, campaign, scene)
        removed = client.post("/game/walls/delete-many", json={
            "campaign_id": campaign,
            "wall_ids": [minha["id"], alheia["id"], "sumiu-faz-tempo"],
        })
        assert removed.status_code == 200
        assert removed.json()["wall_ids"] == [minha["id"]]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider)
        left = client.get(f"/game/walls/{other_scene['id']}", params={"campaign_id": other_campaign})
        assert [w["id"] for w in left.json()["walls"]] == [alheia["id"]], "a cena da outra mesa fica de pé"


def test_bulk_delete_is_gm_only(db):
    from main import app
    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        wall = _wall(client, campaign, scene)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        assert client.post("/game/walls/delete-many", json={
            "campaign_id": campaign, "wall_ids": [wall["id"]],
        }).status_code == 403


def test_every_kind_can_be_bulk_deleted(db):
    """Luz, parede, partícula e shader: a seleção pega qualquer um deles."""
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        light = client.post("/game/lights", json={
            "campaign_id": campaign, "scene_id": scene["id"], "x": 10.0, "y": 10.0,
            "animation": "torch", "bright_radius": 2, "dim_radius": 4,
            "color": "#ffd8a8", "intensity": 1,
        }).json()["light"]
        emitter = client.post("/game/particles", json={
            "campaign_id": campaign, "scene_id": scene["id"], "x": 20.0, "y": 20.0, "kind": "smoke",
        }).json()["emitter"]
        shader = client.post("/game/shaders", json={
            "campaign_id": campaign, "scene_id": scene["id"], "x": 30.0, "y": 30.0,
        }).json()["shader"]

        assert client.post("/game/lights/delete-many", json={
            "campaign_id": campaign, "light_ids": [light["id"]]}).json()["light_ids"] == [light["id"]]
        assert client.post("/game/particles/delete-many", json={
            "campaign_id": campaign, "emitter_ids": [emitter["id"]]}).json()["emitter_ids"] == [emitter["id"]]
        assert client.post("/game/shaders/delete-many", json={
            "campaign_id": campaign, "shader_ids": [shader["id"]]}).json()["shader_ids"] == [shader["id"]]

        assert client.get(f"/game/lights/{scene['id']}", params={"campaign_id": campaign}).json()["lights"] == []
        assert client.get(f"/game/particles/{scene['id']}", params={"campaign_id": campaign}).json()["emitters"] == []
        assert client.get(f"/game/shaders/{scene['id']}", params={"campaign_id": campaign}).json()["shaders"] == []
