import time
from types import SimpleNamespace

from app.engine.sdk.directed_interaction_service import DirectedInteractionService
from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository
from tests.conftest import seed_campaign, seed_member, seed_user


def _world():
    gm=seed_user(name="GM");player=seed_user(name="Player");campaign=seed_campaign(gm);seed_member(campaign,player,"player")
    return gm,player,campaign


def test_bounded_timed_workflow_is_durable_idempotent_and_cancellable(db):
    gm,_,campaign=_world();service=DurableWorkflowService()
    definition={"id":"clock","schemaVersion":1,"steps":[{"type":"SET","key":"ready","value":True},{"type":"WAIT_UNTIL","delaySeconds":0},{"type":"BRANCH","key":"ready","equals":True,"then":3,"else":4},{"type":"COMPLETE","output":{"ok":True}},{"type":"FAIL","reason":"bad"}]}
    assert service.register(campaign_id=campaign,package_id="rules",definition=definition).success
    started=service.start(campaign_id=campaign,user_id=gm,package_id="rules",values={"definitionId":"clock","idempotencyKey":"same"})
    assert started.success and started.value["status"]=="WAITING_TIME"
    same=service.start(campaign_id=campaign,user_id=gm,package_id="rules",values={"definitionId":"clock","idempotencyKey":"same"})
    assert same.value["id"]==started.value["id"]
    recovered=service.recover_campaign(campaign,int(time.time()))
    assert recovered[-1]["status"]=="COMPLETED" and recovered[-1]["context"]["ready"] is True
    assert not service.register(campaign_id=campaign,package_id="rules",definition={"id":"escape","schemaVersion":1,"steps":[{"type":"CALLBACK","url":"https://bad"}]}).success


def test_interaction_wait_resumes_from_persisted_identity(db):
    gm,player,campaign=_world();service=DurableWorkflowService()
    definition={"id":"reaction","schemaVersion":1,"steps":[{"type":"INTERACTION","request":{"recipients":[player],"title":"React?","text":"Choose","responseSchema":{"type":"boolean"},"deadline":int(time.time())+300}},{"type":"COMPLETE"}]}
    assert service.register(campaign_id=campaign,package_id="rules",definition=definition).success
    waiting=service.start(campaign_id=campaign,user_id=gm,package_id="rules",values={"definitionId":"reaction","idempotencyKey":"attack-1"}).value
    assert waiting["status"]=="WAITING_INTERACTION" and waiting["waitingOn"]
    interaction=DirectedInteractionService().get(campaign_id=campaign,interaction_id=waiting["waitingOn"],user_id=player).value
    answered=DirectedInteractionService().respond(campaign_id=campaign,interaction_id=interaction["id"],user_id=player,response=True,expected_version=interaction["version"],idempotency_key="answer")
    assert answered.success
    resumed=service.resume_interaction(campaign_id=campaign,interaction_id=interaction["id"])
    assert resumed[0]["status"]=="COMPLETED" and resumed[0]["context"]["interaction"]["responses"][player]["value"] is True


def test_package_unload_publishes_terminal_core_state_before_definition_teardown(db):
    gm,player,campaign=_world();service=DurableWorkflowService()
    definition={"id":"wait","schemaVersion":1,"steps":[{"type":"INTERACTION","request":{"recipients":[player],"title":"Wait","text":"Wait","responseSchema":{"type":"boolean"},"deadline":int(time.time())+300}},{"type":"COMPLETE"}]}
    service.register(campaign_id=campaign,package_id="rules",definition=definition)
    active=service.start(campaign_id=campaign,user_id=gm,package_id="rules",values={"definitionId":"wait","idempotencyKey":"unload"}).value
    changed=SemanticInstanceRepository().fail_closed_package(campaign,"rules")
    assert changed[0]["id"]==active["id"] and changed[0]["status"]=="CANCELLED" and changed[0]["payload"]["completionReason"]=="package-unload"


def test_registered_action_step_has_durable_execution_identity_and_restart_recovery(db,monkeypatch):
    gm,_,campaign=_world();calls=[]
    def execute(*_args,**kwargs):
        calls.append(kwargs["idempotency_key"]);return SimpleNamespace(success=True,value={"changedResources":[],"key":kwargs["idempotency_key"]},error_key=None)
    monkeypatch.setattr("app.engine.sdk.durable_workflow_service.DeclarativeActionService.execute",execute)
    service=DurableWorkflowService();definition={"id":"action","schemaVersion":1,"steps":[{"type":"ACTION","action":"rules:apply@1","input":{}},{"type":"WAIT_UNTIL","delaySeconds":0},{"type":"COMPLETE"}]}
    assert service.register(campaign_id=campaign,package_id="rules",definition=definition).success
    waiting=service.start(campaign_id=campaign,user_id=gm,package_id="rules",values={"definitionId":"action","idempotencyKey":"durable"}).value
    assert calls==[f"workflow:{waiting['id']}:0"]
    recovered=DurableWorkflowService().recover_campaign(campaign,int(time.time()))
    assert recovered[-1]["status"]=="COMPLETED" and calls==[f"workflow:{waiting['id']}:0"]


def test_workflow_rejects_backward_branch_and_stale_cancel(db):
    gm,_,campaign=_world();service=DurableWorkflowService()
    assert not service.register(campaign_id=campaign,package_id="rules",definition={"id":"loop","schemaVersion":1,"steps":[{"type":"SET","key":"x","value":1},{"type":"BRANCH","key":"x","equals":1,"then":0,"else":0}]}).success
    service.register(campaign_id=campaign,package_id="rules",definition={"id":"waiting","schemaVersion":1,"steps":[{"type":"WAIT_UNTIL","delaySeconds":100}]})
    row=service.start(campaign_id=campaign,user_id=gm,package_id="rules",values={"definitionId":"waiting","idempotencyKey":"cancel"}).value
    assert service.cancel(campaign_id=campaign,user_id=gm,package_id="rules",instance_id=row["id"],expected_version=999).error_key.endswith("stale_version")


def test_active_workflow_uses_frozen_definition_snapshot(db):
    gm,_,campaign=_world();service=DurableWorkflowService()
    original={"id":"frozen","schemaVersion":1,"steps":[{"type":"WAIT_UNTIL","delaySeconds":0},{"type":"COMPLETE","reason":"original"}]}
    replacement={"id":"frozen","schemaVersion":1,"steps":[{"type":"WAIT_UNTIL","delaySeconds":0},{"type":"FAIL","reason":"replacement"}]}
    service.register(campaign_id=campaign,package_id="rules",definition=original)
    active=service.start(campaign_id=campaign,user_id=gm,package_id="rules",values={"definitionId":"frozen","idempotencyKey":"frozen"}).value
    service.register(campaign_id=campaign,package_id="rules",definition=replacement)
    recovered=service.recover_campaign(campaign,int(time.time()))
    assert recovered[0]["id"]==active["id"] and recovered[0]["status"]=="COMPLETED"
