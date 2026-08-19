from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from app.engine.sdk.semantic_timeline_service import SemanticTimelineService
from app.engine.sdk.token_transfer_service import TokenTransferService
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import seed_campaign, seed_scene, seed_user


def test_semantic_runtime_rejects_work_beyond_each_public_bound(db):
    gm = seed_user()
    campaign = seed_campaign(gm)

    workflow = DurableWorkflowService().register(
        campaign_id=campaign,
        package_id="bounded-addon",
        definition={"id": "too-many", "schemaVersion": 1, "steps": [{"type": "COMPLETE"}] * 129},
    )
    timeline = SemanticTimelineService().register(
        campaign_id=campaign,
        package_id="bounded-addon",
        definition={
            "id": "too-many",
            "schemaVersion": 1,
            "cues": [{"cueId": f"cue-{index}", "offsetMs": 0, "type": "NAVIGATION", "parameters": {}} for index in range(257)],
        },
    )

    assert not workflow.success
    assert not timeline.success


def test_atomic_transfer_accepts_100_token_party_and_rejects_one_more(db):
    gm = seed_user()
    campaign = seed_campaign(gm)
    source = seed_scene(campaign, name="Source")
    destination = seed_scene(campaign, name="Destination")
    repository = TokenRepository()
    tokens = [repository.create(scene_id=source["id"], actor_id=None, grid_x=index, grid_y=0) for index in range(101)]
    service = TokenTransferService()

    maximum = service.transfer_many(
        campaign_id=campaign,
        user_id=gm,
        values={
            "transfers": [
                {"tokenId": token["id"], "sceneId": destination["id"], "x": index, "y": 1, "expectedVersion": token["version"]}
                for index, token in enumerate(tokens[:100])
            ]
        },
    )
    overflow = service.transfer_many(
        campaign_id=campaign,
        user_id=gm,
        values={
            "transfers": [
                {"tokenId": token["id"], "sceneId": destination["id"], "x": index, "y": 2, "expectedVersion": token["version"]}
                for index, token in enumerate(tokens)
            ]
        },
    )

    assert maximum.success
    assert len(maximum.value["tokens"]) == 100
    assert not overflow.success
    assert repository.get_by_id(tokens[-1]["id"])["scene_id"] == source["id"]


def test_scheduler_scale_1000_waiting_workflows_and_500_future_cues(db):
    gm = seed_user()
    campaign = seed_campaign(gm)
    workflows = DurableWorkflowService()
    assert workflows.register(
        campaign_id=campaign,
        package_id="load-addon",
        definition={"id": "wait", "schemaVersion": 1, "steps": [{"type": "WAIT_UNTIL", "delaySeconds": 3600}]},
    ).success
    for index in range(1000):
        assert workflows.start(
            campaign_id=campaign,
            user_id=gm,
            package_id="load-addon",
            values={"definitionId": "wait", "idempotencyKey": f"workflow-{index}"},
        ).success
    assert len(workflows.list(campaign_id=campaign, user_id=gm, package_id="load-addon").value) == 1000

    timelines = SemanticTimelineService()
    scene = seed_scene(campaign, name="Timeline load")
    cues = [
        {
            "cueId": f"cue-{index}",
            "offsetMs": (index + 1) * 1000,
            "type": "NAVIGATION",
            "parameters": {"sceneId": scene["id"], "recipients": {"kind": "self"}},
        }
        for index in range(10)
    ]
    assert timelines.register(
        campaign_id=campaign,
        package_id="load-addon",
        definition={"id": "future", "schemaVersion": 1, "cues": cues},
    ).success
    for index in range(50):
        result = timelines.start(
            campaign_id=campaign,
            user_id=gm,
            package_id="load-addon",
            values={"definitionId": "future", "idempotencyKey": f"timeline-{index}"},
        )
        assert result.success and result.value["status"] == "RUNNING"
    assert len(timelines.list(campaign_id=campaign, user_id=gm, package_id="load-addon").value) == 50
