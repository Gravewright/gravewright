import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from app.engine.rules.automation_service import AutomationResult, AutomationService
from app.engine.rules.declarative_action_service import DeclarativeActionResult
from app.persistence.repositories.automation_job_repository import AutomationJobRepository
from tests.conftest import seed_campaign, seed_user


def _job(campaign, user, *, key="key", run_at=0, audit=None):
    return AutomationJobRepository().create(campaign_id=campaign, package_id="product-addon", action_id="apply",
        action_version=1, input={"actor":"a"}, principal_user_id=user, run_at_utc=run_at,
        idempotency_key=key, origin_execution_id=None, origin_job_id=None, causal_depth=0, audit=audit)


def test_pending_survives_restart_expired_lease_recovers_and_terminal_jobs_do_not_run(db):
    user = seed_user(); campaign = seed_campaign(user); pending = _job(campaign, user)
    assert AutomationJobRepository().get(pending["id"])["status"] == "pending"
    claimed = AutomationJobRepository().claim_due("worker-a", now=100, lease_seconds=1)
    assert claimed["id"] == pending["id"]
    assert AutomationJobRepository().claim_due("worker-b", now=100) is None
    recovered = AutomationJobRepository().claim_due("worker-b", now=102)
    assert recovered["id"] == pending["id"] and recovered["attempts"] == 2
    assert AutomationJobRepository().finish(pending["id"], "worker-b", "succeeded")
    assert AutomationJobRepository().claim_due("worker-c", now=999) is None
    cancelled = _job(campaign, user, key="cancelled")
    assert AutomationJobRepository().cancel(cancelled["id"], campaign, "product-addon")
    assert AutomationJobRepository().claim_due("worker-c", now=999) is None


def test_two_workers_cannot_claim_same_attempt_and_lost_claim_writes_nothing(db):
    user = seed_user(); campaign = seed_campaign(user); job = _job(campaign, user)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda worker: AutomationJobRepository().claim_due(worker, now=100), ("one", "two")))
    winners = [claim for claim in claims if claim]
    assert len(winners) == 1
    owner = winners[0]["lease_owner"]; loser = "two" if owner == "one" else "one"
    transitions = []
    assert not AutomationJobRepository().finish(job["id"], loser, "succeeded", audit=lambda *_args: transitions.append("bad"))
    assert not AutomationJobRepository().retry(job["id"], loser, 200, "retryable", audit=lambda *_args: transitions.append("bad"))
    assert transitions == [] and AutomationJobRepository().get(job["id"])["status"] == "running"


@pytest.mark.parametrize("reason", [
    "sdk.runtime.permission_denied", "sdk.runtime.user_removed", "sdk.runtime.package_disabled",
    "sdk.runtime.package_inactive", "sdk.runtime.package_uninstalled", "sdk.rules.actions.version_unsupported",
])
def test_execution_time_authority_and_package_lifecycle_fail_closed(db, monkeypatch, reason):
    user = seed_user(); campaign = seed_campaign(user); _job(campaign, user, key=reason)
    monkeypatch.setattr("app.engine.rules.automation_service.DeclarativeActionService.execute",
                        lambda _self, **_kw: DeclarativeActionResult(False, error_key=reason))
    result = AutomationService().run_one(worker_id="worker", now=100)
    assert not result.success and result.value["status"] == "rejected"


def test_due_job_uses_action_executor_and_transient_retry_is_bounded(db, monkeypatch):
    user = seed_user(); campaign = seed_campaign(user); _job(campaign, user)
    calls = []
    monkeypatch.setattr("app.engine.rules.automation_service.DeclarativeActionService.execute",
        lambda _self, **kw: calls.append(kw) or DeclarativeActionResult(True, {"ok": True}))
    completed = AutomationService().run_one(worker_id="worker", now=100)
    assert completed.success and completed.value["status"] == "succeeded" and calls[0]["idempotency_key"] == "key"

    retry = _job(campaign, user, key="retry")
    monkeypatch.setattr("app.engine.rules.automation_service.DeclarativeActionService.execute",
                        lambda _self, **_kw: DeclarativeActionResult(False, error_key="sdk.storage.retryable"))
    for attempt in range(3):
        result = AutomationService().run_one(worker_id=f"worker-{attempt}", now=int(time.time()) + 1000 + attempt)
    assert not result.success
    final = AutomationJobRepository().get(retry["id"])
    assert final["status"] == "failed" and final["attempts"] == AutomationService.MAX_ATTEMPTS


def test_schedule_rejects_loops_and_package_cannot_schedule_arbitrary_work(db, monkeypatch):
    user = seed_user(); campaign = seed_campaign(user); service = AutomationService()
    monkeypatch.setattr(service.audit, "record", lambda **_kw: None)
    monkeypatch.setattr("app.engine.rules.automation_service.SdkRuntimeAuthority.authorize",
                        lambda _self, **_kw: SimpleNamespace(allowed=True, error_key=None))
    immediate = SimpleNamespace(reference="product-addon:work@1", durability="unsupported",
        idempotency="NOT_DURABLE", action_id="work", version=1)
    monkeypatch.setattr("app.engine.rules.automation_service.DeclarativeActionRegistry.get", lambda _self, *_a: immediate)
    arbitrary = service.schedule(campaign_id=campaign, user_id=user, package_id="product-addon", action_id="work",
        version=1, inputs={}, run_at_utc=0, idempotency_key="x")
    assert arbitrary.error_key == "sdk.automation.not_durable"
    durable = SimpleNamespace(reference="product-addon:work@1", durability="supported",
        idempotency="REQUIRES_IDEMPOTENCY_KEY", action_id="work", version=1)
    monkeypatch.setattr("app.engine.rules.automation_service.DeclarativeActionRegistry.get", lambda _self, *_a: durable)
    loop = service.schedule(campaign_id=campaign, user_id=user, package_id="product-addon", action_id="work",
        version=1, inputs={}, run_at_utc=0, idempotency_key="x", causal_depth=service.MAX_DEPTH + 1)
    assert loop.error_key == "sdk.automation.invalid"


def test_audit_transition_is_bounded_and_payload_free(db):
    user = seed_user(); campaign = seed_campaign(user); captured = []
    _job(campaign, user, audit=lambda _conn, row, transition, recovered: captured.append((row, transition, recovered)))
    row, transition, recovered = captured[0]
    assert transition == "created" and recovered is False
    public_keys = {"package_id", "action_id", "action_version", "attempts", "error_code", "id", "campaign_id"}
    projected = {key: row.get(key) for key in public_keys}
    assert "input_json" not in projected and "idempotency_key" not in projected
