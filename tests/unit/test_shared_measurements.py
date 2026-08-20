import time

from app.engine.sdk.ephemeral_domain_service import SharedMeasurementService
from app.persistence.repositories.core_ephemeral_state_repository import CoreEphemeralStateRepository
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


POINTS = {"points": [{"x": 0, "y": 0}, {"x": 70, "y": 70}]}


def _allow_scenes(monkeypatch):
    monkeypatch.setattr(SharedMeasurementService, "_scene", lambda *_args, **_kwargs: True)


def test_share_audience_projection_cancel_and_multi_worker_coherence(db, monkeypatch):
    gm, player, other = seed_user(name="GM"), seed_user(name="Player"), seed_user(name="Other")
    campaign = seed_campaign(gm); seed_member(campaign, player, "player"); seed_member(campaign, other, "player")
    scene = seed_scene(campaign)["id"]; _allow_scenes(monkeypatch)
    creator, reader = SharedMeasurementService(), SharedMeasurementService()
    own = creator.create(campaign_id=campaign, scene_id=scene, user_id=player, geometry=POINTS, audience="self")
    public = creator.create(campaign_id=campaign, scene_id=scene, user_id=gm, geometry=POINTS, audience="campaign")
    gm_only = creator.create(campaign_id=campaign, scene_id=scene, user_id=gm, geometry=POINTS, audience="gm")
    assert own.success and public.success and gm_only.success
    assert {m["id"] for m in reader.list(campaign_id=campaign, scene_id=scene, user_id=other).value} == {public.value["id"]}
    assert {m["id"] for m in reader.list(campaign_id=campaign, scene_id=scene, user_id=gm).value} == {public.value["id"], gm_only.value["id"]}
    assert reader.cancel(campaign_id=campaign, scene_id=scene, user_id=gm, measurement_id=own.value["id"]).success
    assert not reader.cancel(campaign_id=campaign, scene_id=scene, user_id=other, measurement_id=gm_only.value["id"]).success


def test_ttl_scene_cleanup_quota_rate_and_private_store_boundary(db, monkeypatch):
    user = seed_user(); campaign = seed_campaign(user); scene = seed_scene(campaign)["id"]; _allow_scenes(monkeypatch)
    store = CoreEphemeralStateRepository()
    store.put(namespace=SharedMeasurementService.NS, campaign_id=campaign, scope_id=scene, owner_user_id=user,
              entry_key="expired", audience={"kind": "self"}, payload={"geometry": POINTS}, ttl_seconds=1)
    from app.persistence import database
    with database.engine_begin() as conn:
        conn.exec_driver_sql("UPDATE core_ephemeral_states SET expires_at = ? WHERE entry_key = ?", (int(time.time()) - 1, "expired"))
    assert SharedMeasurementService().list(campaign_id=campaign, scene_id=scene, user_id=user).value == []
    for index in range(8):
        result = SharedMeasurementService().create(campaign_id=campaign, scene_id=scene, user_id=user, geometry=POINTS, audience="self")
        assert result.success
    assert SharedMeasurementService().create(campaign_id=campaign, scene_id=scene, user_id=user, geometry=POINTS, audience="self").error_key == "sdk.scene.measurements.rate_limited"
    store.delete_scope(namespace=SharedMeasurementService.NS, campaign_id=campaign, scope_id=scene)
    assert SharedMeasurementService().list(campaign_id=campaign, scene_id=scene, user_id=user).value == []
    assert set(SharedMeasurementService._public(store.put(namespace=SharedMeasurementService.NS, campaign_id=campaign, scope_id=scene,
        owner_user_id=user, entry_key="safe", audience={"kind": "self"}, payload={"geometry": POINTS}, ttl_seconds=30))) == {
        "id", "creator", "sceneId", "geometry", "audience", "expiresAt", "version"
    }


def _force_created_at(campaign, scene, segundos_atras):
    from app.persistence import database
    with database.engine_begin() as conn:
        conn.exec_driver_sql(
            "UPDATE core_ephemeral_states SET created_at = ? WHERE namespace = ? AND campaign_id = ? AND scope_id = ?",
            (int(time.time()) - segundos_atras, SharedMeasurementService.NS, campaign, scene),
        )


def test_the_rate_window_releases_and_survives_a_second_boundary(db, monkeypatch):
    """A janela do limite não pode ser "o segundo inteiro corrente".

    Ela era: contava só as linhas cujo `created_at` fosse o segundo atual. Oito
    criações que atravessassem a virada do segundo deixavam o contador cair
    abaixo do limite e nada era barrado -- passava na máquina rápida e falhava
    no CI, que é onde o loop cruza a virada. Este teste crava os dois lados da
    janela na mão, então não depende de quão rápido a máquina roda.
    """
    user = seed_user(); campaign = seed_campaign(user); scene = seed_scene(campaign)["id"]
    _allow_scenes(monkeypatch)
    servico = SharedMeasurementService()

    for _ in range(servico.RATE_MAX):
        assert servico.create(campaign_id=campaign, scene_id=scene, user_id=user,
                              geometry=POINTS, audience="self").success

    # Dentro da janela, no segundo corrente: barrado.
    _force_created_at(campaign, scene, 0)
    assert servico.create(campaign_id=campaign, scene_id=scene, user_id=user, geometry=POINTS,
                          audience="self").error_key == "sdk.scene.measurements.rate_limited"

    # Dentro da janela, mas UM SEGUNDO ATRÁS: é exatamente aqui que a versão
    # antiga soltava a rajada, porque só olhava o segundo corrente. É o caso que
    # o CI expunha e a máquina local escondia.
    _force_created_at(campaign, scene, 1)
    assert servico.create(campaign_id=campaign, scene_id=scene, user_id=user, geometry=POINTS,
                          audience="self").error_key == "sdk.scene.measurements.rate_limited"

    # Fora da janela: a rajada antiga não pode prender o usuário para sempre.
    _force_created_at(campaign, scene, servico.RATE_WINDOW_SECONDS + 1)
    assert servico.create(campaign_id=campaign, scene_id=scene, user_id=user,
                          geometry=POINTS, audience="self").success
