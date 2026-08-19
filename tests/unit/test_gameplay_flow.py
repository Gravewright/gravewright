from app.engine.sdk.gameplay_flow_service import GameplayFlowService
from app.persistence.repositories.semantic_instance_repository import SemanticInstanceRepository
from tests.conftest import seed_campaign, seed_member, seed_user


def test_simultaneous_secret_commit_reveal_and_phase_advance(db):
    gm=seed_user(name="GM");a=seed_user(name="A");b=seed_user(name="B");campaign=seed_campaign(gm);seed_member(campaign,a,"player");seed_member(campaign,b,"player")
    service=GameplayFlowService();definition={"id":"orders","schemaVersion":1,"turnModel":"SIMULTANEOUS","phases":[{"id":"plan"},{"id":"resolve"}]}
    assert service.register(campaign_id=campaign,package_id="war",definition=definition).success
    flow=service.start(campaign_id=campaign,user_id=gm,package_id="war",values={"definitionId":"orders","participants":[a,b],"idempotencyKey":"cycle-1"}).value
    a_view=service.submit(campaign_id=campaign,user_id=a,package_id="war",instance_id=flow["id"],value={"order":"north"},expected_version=flow["version"]).value
    assert list(a_view["submissions"])==[a] and not a_view["revealed"]
    assert service.get(campaign_id=campaign,user_id=b,package_id="war",instance_id=flow["id"]).value["submissions"]=={}
    b_view=service.submit(campaign_id=campaign,user_id=b,package_id="war",instance_id=flow["id"],value={"order":"south"},expected_version=a_view["version"]).value
    assert b_view["revealed"] and set(b_view["submissions"])=={a,b}
    advanced=service.advance(campaign_id=campaign,user_id=gm,package_id="war",instance_id=flow["id"],expected_version=b_view["version"])
    assert advanced.success and advanced.value["phaseId"]=="resolve" and advanced.value["submissions"]=={}


def test_sequential_and_phased_definitions_have_no_combat_assumptions(db):
    gm=seed_user();campaign=seed_campaign(gm);service=GameplayFlowService()
    for mode in ("SEQUENTIAL","PHASED"):
        result=service.register(campaign_id=campaign,package_id="board",definition={"id":mode.lower(),"schemaVersion":1,"turnModel":mode,"phases":[{"id":"move"},{"id":"end"}]})
        assert result.success and "initiative" not in result.value and "hp" not in result.value


def test_sequential_authority_reconnect_and_stale_version(db):
    gm=seed_user();a=seed_user();b=seed_user();campaign=seed_campaign(gm);seed_member(campaign,a,"player");seed_member(campaign,b,"player");service=GameplayFlowService()
    service.register(campaign_id=campaign,package_id="board",definition={"id":"turns","schemaVersion":1,"turnModel":"SEQUENTIAL","phases":[{"id":"play"}]})
    flow=service.start(campaign_id=campaign,user_id=gm,package_id="board",values={"definitionId":"turns","participants":[a,b],"idempotencyKey":"game"}).value
    assert flow["activeParticipants"]==[a]
    assert service.submit(campaign_id=campaign,user_id=b,package_id="board",instance_id=flow["id"],value="early").error_key.endswith("not_active_participant")
    first=service.submit(campaign_id=campaign,user_id=a,package_id="board",instance_id=flow["id"],value="move",expected_version=flow["version"])
    assert first.success and first.value["activeParticipants"]==[b]
    assert not service.submit(campaign_id=campaign,user_id=b,package_id="board",instance_id=flow["id"],value="stale",expected_version=flow["version"]).success
    # A new service instance reconstructs the same authoritative state.
    assert GameplayFlowService().get(campaign_id=campaign,user_id=b,package_id="board",instance_id=flow["id"]).value["activeParticipants"]==[b]


def test_phase_deadline_is_core_owned_and_recovers_after_restart(db):
    import time
    gm=seed_user();campaign=seed_campaign(gm);service=GameplayFlowService()
    service.register(campaign_id=campaign,package_id="war",definition={"id":"timed","schemaVersion":1,"turnModel":"PHASED","phases":[{"id":"orders","deadlineSeconds":1},{"id":"resolve"}]})
    flow=service.start(campaign_id=campaign,user_id=gm,package_id="war",values={"definitionId":"timed","participants":[gm],"idempotencyKey":"timed"}).value
    assert flow["phaseId"]=="orders"
    recovered=GameplayFlowService().recover_campaign(campaign,int(time.time())+2)
    assert recovered[0]["phaseId"]=="resolve"


def test_duplicate_submission_and_package_unload_fail_closed(db):
    gm=seed_user();player=seed_user();campaign=seed_campaign(gm);seed_member(campaign,player,"player");service=GameplayFlowService()
    assert service.register(campaign_id=campaign,package_id="board",definition={"id":"secret","schemaVersion":1,"turnModel":"SIMULTANEOUS","phases":[{"id":"plan"}]}).success
    flow=service.start(campaign_id=campaign,user_id=gm,package_id="board",values={"definitionId":"secret","participants":[player],"idempotencyKey":"secret"}).value
    submitted=service.submit(campaign_id=campaign,user_id=player,package_id="board",instance_id=flow["id"],value="north",expected_version=flow["version"])
    duplicate=service.submit(campaign_id=campaign,user_id=player,package_id="board",instance_id=flow["id"],value="south",expected_version=submitted.value["version"])
    assert duplicate.error_key=="sdk.gameplay.flows.already_submitted"
    changed=SemanticInstanceRepository().fail_closed_package(campaign,"board")
    assert changed[0]["status"]=="CANCELLED" and changed[0]["payload"]["completionReason"]=="package-unload"
