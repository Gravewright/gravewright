from app.engine.scenes.scene_light_service import SceneLightService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user

def _gm_scene(db_unused=None):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign)
    return gm, campaign, scene, SceneLightService()

def test_gm_creates_moves_and_deletes_lights(db):
    gm, campaign, scene, service = _gm_scene()
    made=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=120,y=80,animation="torch",bright_radius=2,dim_radius=5,color="#FFD8A8",intensity=0.8)
    assert made.success
    light=made.payload["light"]
    assert (light["x"],light["y"]) == (120,80)
    assert light["animation"] == "torch" and light["color"] == "#ffd8a8", "cor normalizada para minusculo"
    assert light["intensity"] == 0.8

    moved=service.update(campaign_id=campaign,light_id=light["id"],user_id=gm,x=300,y=310)
    assert moved.success and (moved.payload["light"]["x"],moved.payload["light"]["y"]) == (300,310)
    assert moved.payload["light"]["animation"] == "torch", "update parcial preserva o resto"

    assert service.delete(campaign_id=campaign,light_id=light["id"],user_id=gm).success
    assert service.state(campaign_id=campaign,scene_id=scene["id"],user_id=gm).payload["lights"] == []

def test_a_light_emits_in_a_circle_until_someone_narrows_it(db):
    """Abertura e direcao sao o que separa uma lanterna de um lampiao. O padrao e
    360 graus: nenhum foco que ja existia muda de aparencia por causa disto."""
    gm, campaign, scene, service = _gm_scene()
    made=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=0,y=0).payload["light"]
    assert made["angle"] == 360.0 and made["rotation"] == 0.0

    facho=service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,angle=60,rotation=90).payload["light"]
    assert facho["angle"] == 60.0 and facho["rotation"] == 90.0

    # Cone mais estreito que o minimo vira uma risca sem area, e o mestre perde o
    # alvo do ponteiro para corrigir; acima de 360 ele daria a volta em si mesmo.
    assert service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,angle=0).payload["light"]["angle"] == 5.0
    assert service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,angle=999).payload["light"]["angle"] == 360.0

    # Direcao normaliza: uma regua mostrando -1080 nao diz nada a ninguem.
    assert service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,rotation=-90).payload["light"]["rotation"] == 270.0
    assert service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,angle="largo").error_key == "lighting.errors.invalid"

def test_intensity_is_the_only_brightness_dial(db):
    """`opacity` vivia ao lado de `intensity` porque uma mexia na tinta e a outra
    no quanto o foco levantava a escuridao. Quando o recorte do foco passou a ser
    duro nos dois modos de visao — para que a visao bonita nunca custasse area
    revelada — sobraram duas reguas multiplicando o mesmo alfa."""
    gm, campaign, scene, service = _gm_scene()
    made=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=0,y=0).payload["light"]
    assert "opacity" not in made and "animated_core" not in made

    ajustado=service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,intensity=0.3).payload["light"]
    assert ajustado["intensity"] == 0.3
    clamped=service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,intensity=9).payload["light"]
    assert clamped["intensity"] == 1.0

def test_every_emission_type_is_accepted(db):
    """Fonte de luz anima de dois jeitos: chama irregular e respiracao. O resto
    virou emissor de particula, que nao ilumina e mora noutra tabela."""
    gm, campaign, scene, service = _gm_scene()
    made=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=0,y=0).payload["light"]
    for emission in ("none", "torch", "pulse"):
        light=service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,animation=emission).payload["light"]
        assert light["animation"] == emission

def test_light_input_is_validated(db):
    gm, campaign, scene, service = _gm_scene()
    bad = lambda **kw: service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,**kw).error_key
    assert bad(x=0,y=0,animation="strobe") == "lighting.errors.invalid"
    assert bad(x=0,y=0,color="red") == "lighting.errors.invalid"
    assert bad(x=float("nan"),y=0) == "lighting.errors.invalid"
    assert bad(x=10**9,y=0) == "lighting.errors.invalid", "fora dos limites da cena"

    clamped=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=0,y=0,intensity=5,dim_radius=10_000).payload["light"]
    assert clamped["intensity"] == 1.0 and clamped["dim_radius"] == 200.0

def test_bright_radius_never_exceeds_dim_radius(db):
    gm, campaign, scene, service = _gm_scene()
    made=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=0,y=0,bright_radius=8,dim_radius=3).payload["light"]
    assert made["dim_radius"] == 8, "criar com claro maior empurra o escuro"

    # update parcial precisa comparar com o valor ja gravado, nao so com o payload
    widened=service.update(campaign_id=campaign,light_id=made["id"],user_id=gm,bright_radius=20).payload["light"]
    assert widened["dim_radius"] == 20

def test_only_the_gm_edits_lights_but_members_read_them(db):
    gm=seed_user(name="GM"); player=seed_user(name="Player"); stranger=seed_user(name="Stranger")
    campaign=seed_campaign(gm); seed_member(campaign,player,"player"); scene=seed_scene(campaign)
    service=SceneLightService()
    light=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=0,y=0).payload["light"]

    assert service.state(campaign_id=campaign,scene_id=scene["id"],user_id=player).success, "jogador le os focos"
    assert service.state(campaign_id=campaign,scene_id=scene["id"],user_id=stranger).error_key == "lighting.errors.denied"
    assert service.create(campaign_id=campaign,scene_id=scene["id"],user_id=player,x=0,y=0).error_key == "lighting.errors.denied"
    assert service.update(campaign_id=campaign,light_id=light["id"],user_id=player,x=5).error_key == "lighting.errors.denied"
    assert service.delete(campaign_id=campaign,light_id=light["id"],user_id=player).error_key == "lighting.errors.denied"

def test_lights_do_not_leak_across_campaigns(db):
    gm=seed_user(name="GM"); other=seed_user(name="Other")
    campaign=seed_campaign(gm); other_campaign=seed_campaign(other)
    scene=seed_scene(campaign); service=SceneLightService()
    light=service.create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,x=0,y=0).payload["light"]

    assert service.create(campaign_id=other_campaign,scene_id=scene["id"],user_id=other,x=0,y=0).error_key == "lighting.errors.not_found"
    assert service.update(campaign_id=other_campaign,light_id=light["id"],user_id=other,x=1).error_key == "lighting.errors.not_found"
