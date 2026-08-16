from concurrent.futures import ThreadPoolExecutor

import pytest

from app.engine.rules.declarative_action_registry import ActionContractError, _validate_definition
from app.engine.sheets.sheet_data_service import SheetDataService
from app.persistence.repositories.actor_repository import ActorRepository
from tests.conftest import seed_campaign, seed_member, seed_user


def _actor():
    gm = seed_user(name="GM"); campaign = seed_campaign(gm)
    actor = ActorRepository().create(campaign_id=campaign, system_id="contract-rules", actor_type="character",
                                     name="Hero", created_by_user_id=gm, owner_user_ids=[])
    return gm, campaign, actor


def _apply(actor, user, key="key", payload="hash", value=1, fault=None):
    return SheetDataService().patch_data_idempotent(actor_id=actor, user_id=user, patch={"counter": value},
        receipt_identity=f"package:action@1:{key}", payload_hash=payload, execution_id=f"exec-{key}", fault=fault)


def test_first_execution_replay_conflict_and_new_key(db):
    gm, _campaign, actor = _actor()
    first = _apply(actor, gm); replay = _apply(actor, gm)
    assert first.success and replay.success and first.version == replay.version
    assert replay.receipt["executionId"] == first.receipt["executionId"]
    assert _apply(actor, gm, payload="different").error_key == "sdk.rules.actions.idempotency_conflict"
    second = _apply(actor, gm, key="second", value=2)
    assert second.success and second.version == first.version + 1


def test_concurrent_same_key_has_one_authoritative_commit(db):
    gm, _campaign, actor = _actor()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _apply(actor, gm, key="race", value=7), range(2)))
    assert all(result.success for result in results)
    assert len({result.version for result in results}) == 1
    assert SheetDataService().get_data(actor_id=actor, user_id=gm).data["counter"] == 7


def test_fault_boundary_is_atomic_before_and_durable_after_commit(db):
    gm, _campaign, actor = _actor()
    def before(point):
        if point == "before_authoritative_commit": raise RuntimeError("crash")
    with pytest.raises(RuntimeError): _apply(actor, gm, key="before", value=3, fault=before)
    assert SheetDataService().get_data(actor_id=actor, user_id=gm).data == {}
    clean = _apply(actor, gm, key="before", value=3)
    assert clean.success

    def after(point):
        if point == "after_authoritative_commit": raise RuntimeError("crash")
    with pytest.raises(RuntimeError): _apply(actor, gm, key="after", value=4, fault=after)
    replay = _apply(actor, gm, key="after", value=4)
    assert replay.success and replay.data is None
    assert SheetDataService().get_data(actor_id=actor, user_id=gm).data["counter"] == 4


def test_failed_validation_or_permission_does_not_poison_receipt(db):
    gm, campaign, actor = _actor(); outsider = seed_user(name="Outsider")
    denied = _apply(actor, outsider, key="authority")
    assert not denied.success
    assert _apply(actor, gm, key="authority").success
    invalid = SheetDataService().patch_data_idempotent(actor_id=actor, user_id=gm, patch={}, receipt_identity="invalid",
        payload_hash="hash", execution_id="exec")
    assert not invalid.success
    assert _apply(actor, gm, key="invalid").success


def test_receipts_are_private_bounded_and_durability_is_core_derived(db):
    gm, campaign, actor = _actor(); outsider = seed_user(name="Outsider")
    assert _apply(actor, gm).success
    assert not SheetDataService().get_data(actor_id=actor, user_id=outsider).success
    public = SheetDataService().get_data(actor_id=actor, user_id=gm)
    assert public.success and not hasattr(public, "action_receipts") and "_core_action_receipts" not in public.data
    for index in range(1, 128):
        assert _apply(actor, gm, key=f"retention-{index}").success
    assert _apply(actor, gm, key="over-quota").error_key == "sdk.rules.actions.idempotency_quota"

    definition = {"id":"durable", "version":1, "inputs":{"type":"object","properties":{}},
                  "operations":[{"op":"actor.data.patch","actorId":"a","patch":{"x":1}}],
                  "idempotency":"REQUIRES_IDEMPOTENCY_KEY", "durability":"package-claimed"}
    action = _validate_definition("package", definition, {"actors.data.write"})
    assert action.durability == "supported"
    cross_resource = _validate_definition("package", {**definition, "operations": definition["operations"] * 2}, {"actors.data.write"})
    assert cross_resource.durability == "unsupported"
