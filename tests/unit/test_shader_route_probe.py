"""As rotas de shader, com o payload exato que o editor manda.

Cada camada passando isolada não prova travessia: foi assim que criar foco de luz
ficou quebrado na mesa enquanto serviço e asserções estáticas estavam verdes.
Aqui a rota, a revisão do GLSL, o banco e a permissão são exercidos juntos.
"""
from litestar.testing import TestClient
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user

_GOOD = "void main(){ finalColor = vec4(uColor * uIntensity, 1.0); }"


def _create(client, campaign, scene, **extra):
    return client.post("/game/shaders", json={"campaign_id": campaign, "scene_id": scene["id"], **extra})


def test_a_shader_survives_the_round_trip(db):
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        # É assim que a ferramenta cria: o ponto do clique e nada mais. Nome não
        # é pedido, e o texto chega depois, no Salvar.
        created = _create(client, campaign, scene, x=520.0, y=360.0)
        assert created.status_code == 201, created.text
        shader = created.json()["shader"]
        assert (shader["x"], shader["y"]) == (520.0, 360.0)
        assert "void main" in shader["source"], "nasce desenhando: tela em branco parece defeito"

        written = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "source": _GOOD,
        })
        assert written.status_code == 200 and written.json()["shader"]["source"] == _GOOD

        # Nasce com texto que já faz alguma coisa: tela em branco faz o recurso
        # parecer quebrado antes de a pessoa escrever a primeira linha.
        blank = _create(client, campaign, scene)
        assert blank.status_code == 201
        assert "void main" in blank.json()["shader"]["source"]

        listed = client.get(f"/game/shaders/{scene['id']}", params={"campaign_id": campaign})
        assert listed.status_code == 200
        assert {shader["id"], blank.json()["shader"]["id"]} <= {row["id"] for row in listed.json()["shaders"]}

        patched = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "intensity": 5, "speed": -3,
        })
        # Fora do intervalo é preso na faixa, não recusado: uma régua não tem como
        # o mestre errar, e devolver erro aqui só atrapalharia.
        assert patched.status_code == 200
        assert patched.json()["shader"]["intensity"] == 1.0 and patched.json()["shader"]["speed"] == 0.0

        mixed = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "blend_mode": "multiply",
        })
        assert mixed.status_code == 200
        assert mixed.json()["shader"]["blend_mode"] == "multiply"

        faded = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "opacity": 0.35,
        })
        assert faded.status_code == 200
        assert faded.json()["shader"]["opacity"] == 0.35

        invalid_mix = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "blend_mode": "not-a-mode",
        })
        assert invalid_mix.status_code == 400

        # Sem x/y (SDK, importação) ainda cai no centro da cena: um shader que
        # nasce em (0,0) nasce no canto, fora da vista de quem o criou.
        centred = _create(client, campaign, scene).json()["shader"]
        assert (centred["x"], centred["y"]) == (float(scene["width"]) / 2, float(scene["height"]) / 2)
        assert shader["radius"] == 0.0, "sem alcance é cena inteira, que é o que existia antes"

        # Giro dá a volta em vez de recusar: é uma régua circular.
        turned = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "rotation": 370,
        })
        assert turned.status_code == 200 and turned.json()["shader"]["rotation"] == 10.0

        moved = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "x": 640.0, "y": 480.0, "radius": 6,
        })
        assert moved.status_code == 200
        assert (moved.json()["shader"]["x"], moved.json()["shader"]["y"]) == (640.0, 480.0)
        assert moved.json()["shader"]["radius"] == 6.0

        # Fora da cena não é um lugar: aceitar viraria um efeito que ninguém acha.
        lost = client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "x": 10 ** 9, "y": 0.0,
        })
        assert lost.status_code == 400 and lost.json()["error_key"] == "lighting.errors.invalid"

        removed = client.post("/game/shaders/delete", json={"campaign_id": campaign, "shader_id": shader["id"]})
        assert removed.status_code == 200


def test_the_route_accepts_glsl_it_does_not_understand(db):
    """O servidor não é revisor de GLSL, e isso é deliberado.

    Ele já foi: recusava laço sem teto para garantir que o efeito ficasse dentro
    do alcance. Só que garantir isso lendo texto obriga a mexer no texto. A
    contenção virou geométrica — quadro do tamanho do alcance, recortado por
    máscara — e o texto voltou a ser de quem escreve.

    O que protege quem está na mesa é outra coisa: só o mestre escreve, e cada
    jogador tem a chave de desligar os shaders da mesa na própria tela.
    """
    from main import app
    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        estranho = "void main(){ while(true) { } }"
        aceito = _create(client, campaign, scene, source=estranho)
        assert aceito.status_code == 201, aceito.text
        assert aceito.json()["shader"]["source"] == estranho, "grava o que foi escrito, letra por letra"

        # Vazio continua sendo recusado: é limite do campo, não do código.
        assert _create(client, campaign, scene, source="   ").status_code == 400


def test_only_the_gm_writes_shaders(db):
    from main import app
    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    scene = seed_scene(campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        shader = _create(client, campaign, scene, source=_GOOD).json()["shader"]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player)
        # Ler pode: o shader roda na tela dele, então o cliente precisa da lista.
        assert client.get(f"/game/shaders/{scene['id']}", params={"campaign_id": campaign}).status_code == 200
        # Escrever, não. Um jogador que pudesse escrever GLSL escreveria na GPU
        # dos outros — inclusive na do mestre.
        assert _create(client, campaign, scene, source=_GOOD).status_code == 403
        assert client.post("/game/shaders/update", json={
            "campaign_id": campaign, "shader_id": shader["id"], "source": _GOOD,
        }).status_code == 403
        assert client.post("/game/shaders/delete", json={
            "campaign_id": campaign, "shader_id": shader["id"],
        }).status_code == 403


def test_another_table_cannot_touch_this_scene(db):
    from main import app
    gm = seed_user(name="GM")
    outsider = seed_user(name="Outro GM")
    campaign = seed_campaign(gm)
    scene = seed_scene(campaign)
    other_campaign = seed_campaign(outsider)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        shader = _create(client, campaign, scene, source=_GOOD).json()["shader"]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider)
        assert client.get(f"/game/shaders/{scene['id']}", params={"campaign_id": campaign}).status_code == 403
        # Ser mestre em algum lugar não é ser mestre aqui: o id da campanha vem do
        # corpo, e sem esta checagem ele seria uma porta aberta.
        response = client.post("/game/shaders/update", json={
            "campaign_id": other_campaign, "shader_id": shader["id"], "source": _GOOD,
        })
        assert response.status_code == 400
        assert response.json()["error_key"] == "lighting.errors.not_found"
