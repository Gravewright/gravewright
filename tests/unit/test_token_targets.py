import time
from types import SimpleNamespace

from app.engine.sdk.ephemeral_domain_service import TokenTargetService
from app.persistence.repositories.core_ephemeral_state_repository import CoreEphemeralStateRepository
from tests.conftest import seed_campaign, seed_scene, seed_user


def _snapshot(monkeypatch, visible):
    monkeypatch.setattr(
        "app.engine.sdk.ephemeral_domain_service.TokenService.get_snapshot",
        lambda _self, **kw: SimpleNamespace(success=True, tokens=[{"token_id": token} for token in visible.get(kw["user_id"], [])]),
    )


def test_set_list_clear_and_owner_isolation_are_server_owned(db, monkeypatch):
    alice, bob = seed_user(name="Alice"), seed_user(name="Bob")
    campaign = seed_campaign(alice); scene = seed_scene(campaign)["id"]
    _snapshot(monkeypatch, {alice: ["a", "b"], bob: ["b"]})
    first, second = TokenTargetService(), TokenTargetService()

    assert first.set(campaign_id=campaign, scene_id=scene, user_id=alice, ids=["a", "b"]).success
    assert second.set(campaign_id=campaign, scene_id=scene, user_id=bob, ids=["b"]).success
    assert second.list(campaign_id=campaign, scene_id=scene, user_id=alice).value == ["a", "b"]
    assert first.list(campaign_id=campaign, scene_id=scene, user_id=bob).value == ["b"]
    assert first.clear(campaign_id=campaign, scene_id=scene, user_id=alice).value == []
    assert second.list(campaign_id=campaign, scene_id=scene, user_id=alice).value == []
    row = CoreEphemeralStateRepository().list_scope(namespace=TokenTargetService.NS, campaign_id=campaign, scope_id=scene)[0]
    assert row["audience"] == {"kind": "owner"}
    assert set(row["payload"]) == {"ids"}


def test_visibility_deletion_and_scene_transition_fail_closed(db, monkeypatch):
    user = seed_user(); campaign = seed_campaign(user)
    old_scene, new_scene = seed_scene(campaign)["id"], seed_scene(campaign)["id"]
    visible = {user: ["visible", "deleted"]}; _snapshot(monkeypatch, visible)
    service = TokenTargetService()
    assert service.set(campaign_id=campaign, scene_id=old_scene, user_id=user, ids=["visible", "deleted"]).success
    visible[user] = ["visible"]
    assert service.list(campaign_id=campaign, scene_id=old_scene, user_id=user).value == ["visible"]
    assert service.clear(campaign_id=campaign, scene_id=old_scene, user_id=user).success
    assert service.set(campaign_id=campaign, scene_id=new_scene, user_id=user, ids=["visible"]).success
    assert service.list(campaign_id=campaign, scene_id=old_scene, user_id=user).value == []
    assert not service.set(campaign_id=campaign, scene_id=new_scene, user_id=user, ids=["hidden"]).success


class _Relogio:
    """Relógio do serviço, movido à mão.

    O debounce compara `updated_at` com `time.time()` em segundos inteiros, então
    qualquer teste que dependa do relógio real é uma corrida: as duas chamadas
    podem cair em lados opostos da virada do segundo. Congelar só o `time` do
    módulo do serviço mantém os timestamps gravados pelo repositório reais e
    torna a comparação determinística.
    """

    def __init__(self, agora): self._agora = agora
    def time(self): return self._agora
    def mover(self, segundos): self._agora += segundos


def test_limits_rate_and_no_global_token_state(db, monkeypatch):
    user = seed_user(); campaign = seed_campaign(user); scene = seed_scene(campaign)["id"]
    ids = [str(index) for index in range(TokenTargetService.MAX + 1)]
    _snapshot(monkeypatch, {user: ids})
    service = TokenTargetService()
    assert service.set(campaign_id=campaign, scene_id=scene, user_id=user, ids=ids).error_key == "sdk.tokens.targets.invalid"
    assert service.set(campaign_id=campaign, scene_id=scene, user_id=user, ids=["0"]).success

    # Dentro da janela: o segundo update é barrado.
    from app.engine.sdk import ephemeral_domain_service as modulo
    relogio = _Relogio(int(time.time()) - 5)
    monkeypatch.setattr(modulo, "time", relogio)
    assert service.set(campaign_id=campaign, scene_id=scene, user_id=user, ids=["1"]).error_key == "sdk.tokens.targets.rate_limited"

    # E o debounce solta: passado o segundo, o mesmo update entra.
    relogio.mover(60)
    assert service.set(campaign_id=campaign, scene_id=scene, user_id=user, ids=["1"]).success
    from app.persistence.tables import tokens
    assert not any("target" in column.name for column in tokens.c)
