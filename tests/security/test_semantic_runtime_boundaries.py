from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from app.engine.sdk.gameplay_flow_service import GameplayFlowService
from app.engine.sdk.semantic_timeline_service import SemanticTimelineService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


def test_semantic_runtime_definitions_reject_unknown_executable_fields(db):
    gm = seed_user()
    campaign = seed_campaign(gm)

    workflow = DurableWorkflowService().register(
        campaign_id=campaign,
        package_id="safe-addon",
        definition={
            "id": "unsafe",
            "schemaVersion": 1,
            "steps": [{"type": "COMPLETE", "callback": "window.fetch('/secret')"}],
        },
    )
    flow = GameplayFlowService().register(
        campaign_id=campaign,
        package_id="safe-addon",
        definition={
            "id": "unsafe",
            "schemaVersion": 1,
            "turnModel": "PHASED",
            "phases": [{"id": "play", "script": "while(true){}"}],
        },
    )
    timeline = SemanticTimelineService().register(
        campaign_id=campaign,
        package_id="safe-addon",
        definition={
            "id": "unsafe",
            "schemaVersion": 1,
            "cues": [{"offsetMs": 0, "type": "NAVIGATION", "parameters": {}, "renderer": "raw"}],
        },
    )

    assert not workflow.success
    assert not flow.success
    assert not timeline.success


def test_timeline_cannot_expand_audience_from_player_principal(db):
    gm = seed_user()
    player = seed_user(email="semantic-runtime-player@example.test")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    scene = seed_scene(campaign)
    service = SemanticTimelineService()
    assert service.register(
        campaign_id=campaign,
        package_id="safe-addon",
        definition={
            "id": "nav",
            "schemaVersion": 1,
            "cues": [{"cueId": "navigate", "offsetMs": 100, "type": "NAVIGATION", "parameters": {"sceneId": scene["id"], "recipients": {"kind": "self"}}}],
        },
    ).success

    result = service.start(
        campaign_id=campaign,
        user_id=player,
        package_id="safe-addon",
        values={"definitionId": "nav", "idempotencyKey": "audience-escalation", "audience": {"kind": "campaign"}},
    )

    assert not result.success
    assert result.error_key == "sdk.timelines.invalid_input"


def test_player_cannot_start_or_advance_authoritative_gameplay_flow(db):
    gm = seed_user()
    player = seed_user(email="semantic-runtime-flow-player@example.test")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    service = GameplayFlowService()
    assert service.register(
        campaign_id=campaign,
        package_id="safe-addon",
        definition={"id": "turns", "schemaVersion": 1, "turnModel": "PHASED", "phases": [{"id": "play"}]},
    ).success

    forged = service.start(
        campaign_id=campaign,
        user_id=player,
        package_id="safe-addon",
        values={"definitionId": "turns", "participants": [player], "idempotencyKey": "forged"},
    )
    legitimate = service.start(
        campaign_id=campaign,
        user_id=gm,
        package_id="safe-addon",
        values={"definitionId": "turns", "participants": [player], "idempotencyKey": "legitimate"},
    )
    advance = service.advance(
        campaign_id=campaign,
        user_id=player,
        package_id="safe-addon",
        instance_id=legitimate.value["id"],
        expected_version=legitimate.value["version"],
    )

    assert not forged.success and forged.error_key.endswith("not_found")
    assert not advance.success and advance.error_key.endswith("not_found")
