"""Workflow INTERACTION `resultKey`: project one authoritative answer into context.

The projection exists so a definition can BRANCH on what a player actually chose.
Every assertion here is about the value being *server-derived*: the package never
supplies it, and cancel/expiry never fabricate one.
"""

import time

import pytest

from app.engine.sdk.directed_interaction_service import DirectedInteractionService
from app.engine.sdk.durable_workflow_service import DurableWorkflowService
from tests.conftest import seed_campaign, seed_member, seed_user


def _world():
    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    other = seed_user(name="Other")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    seed_member(campaign, other, "player")
    return gm, player, other, campaign


def _ask(player, *, schema, result_key="decision", recipients=None):
    request = {
        "recipients": recipients if recipients is not None else [player],
        "title": "Decide", "text": "Choose", "responseSchema": schema,
        "deadline": int(time.time()) + 300,
    }
    step = {"type": "INTERACTION", "request": request}
    if result_key is not None:
        step["resultKey"] = result_key
    return step


def _branching(player, *, schema, equals, result_key="decision"):
    """INTERACTION -> BRANCH -> two distinct terminal outcomes."""
    return {
        "id": "branching", "schemaVersion": 1, "steps": [
            _ask(player, schema=schema, result_key=result_key),
            {"type": "BRANCH", "key": result_key, "equals": equals, "then": 2, "else": 3},
            {"type": "COMPLETE", "reason": "matched"},
            {"type": "COMPLETE", "reason": "unmatched"},
        ],
    }


def _run(campaign, gm, player, definition, answer, *, key="run"):
    service = DurableWorkflowService()
    assert service.register(campaign_id=campaign, package_id="rules", definition=definition).success
    started = service.start(campaign_id=campaign, user_id=gm, package_id="rules",
                            values={"definitionId": definition["id"], "idempotencyKey": key}).value
    assert started["status"] == "WAITING_INTERACTION"
    interaction = DirectedInteractionService().get(
        campaign_id=campaign, interaction_id=started["waitingOn"], user_id=player).value
    responded = DirectedInteractionService().respond(
        campaign_id=campaign, interaction_id=interaction["id"], user_id=player,
        response=answer, expected_version=interaction["version"], idempotency_key="answer")
    assert responded.success, responded.error_key
    resumed = service.resume_interaction(campaign_id=campaign, interaction_id=interaction["id"])
    return started, interaction, resumed


def test_interaction_without_result_key_keeps_current_behavior(db):
    gm, player, _, campaign = _world()
    definition = {"id": "legacy", "schemaVersion": 1, "steps": [
        _ask(player, schema={"type": "boolean"}, result_key=None), {"type": "COMPLETE"}]}
    _, _, resumed = _run(campaign, gm, player, definition, True, key="legacy")
    context = resumed[0]["context"]
    assert resumed[0]["status"] == "COMPLETED"
    assert context["interaction"]["responses"][player]["value"] is True
    assert set(context) == {"input", "lastResult", "interaction"}


@pytest.mark.parametrize("schema,answer,equals", [
    ({"type": "boolean"}, True, True),
    ({"type": "single-choice", "choices": [{"id": "USE_JAMMER", "label": "Use"}, {"id": "DECLINE", "label": "No"}]}, "USE_JAMMER", "USE_JAMMER"),
    ({"type": "number", "minimum": 0, "maximum": 10}, 5, 5),
    ({"type": "string", "maxLength": 16}, "QUIET", "QUIET"),
])
def test_typed_scalar_responses_project_and_drive_the_existing_branch(db, schema, answer, equals):
    gm, player, _, campaign = _world()
    _, _, resumed = _run(campaign, gm, player, _branching(player, schema=schema, equals=equals), answer, key=str(equals))
    assert resumed[0]["context"]["decision"] == answer
    assert resumed[0]["completionReason"] == "matched"
    # Only the declared key is added; the runtime slots are untouched.
    assert set(resumed[0]["context"]) == {"input", "lastResult", "interaction", "decision"}


def test_branch_takes_the_else_path_when_the_player_chooses_otherwise(db):
    gm, player, _, campaign = _world()
    schema = {"type": "single-choice", "choices": [{"id": "USE_JAMMER", "label": "Use"}, {"id": "DECLINE", "label": "No"}]}
    _, _, resumed = _run(campaign, gm, player, _branching(player, schema=schema, equals="USE_JAMMER"), "DECLINE", key="decline")
    assert resumed[0]["context"]["decision"] == "DECLINE"
    assert resumed[0]["completionReason"] == "unmatched"


def test_projection_survives_restart_recovery_and_is_derived_from_canonical_state(db):
    """The player answers, the process dies, recovery still branches correctly."""
    gm, player, _, campaign = _world()
    service = DurableWorkflowService()
    schema = {"type": "single-choice", "choices": [{"id": "QUIET", "label": "Q"}, {"id": "FAST", "label": "F"}]}
    definition = _branching(player, schema=schema, equals="QUIET", result_key="overrideMode")
    definition["id"] = "restart"
    assert service.register(campaign_id=campaign, package_id="rules", definition=definition).success
    started = service.start(campaign_id=campaign, user_id=gm, package_id="rules",
                            values={"definitionId": "restart", "idempotencyKey": "restart"}).value
    interaction = DirectedInteractionService().get(
        campaign_id=campaign, interaction_id=started["waitingOn"], user_id=player).value
    DirectedInteractionService().respond(campaign_id=campaign, interaction_id=interaction["id"], user_id=player,
                                         response="QUIET", expected_version=interaction["version"], idempotency_key="a")

    # No in-memory event: a cold service instance rebuilds the projection.
    recovered = DurableWorkflowService().recover_campaign(campaign, int(time.time()))
    resumed = next(row for row in recovered if row["id"] == started["id"])
    assert resumed["context"]["overrideMode"] == "QUIET"
    assert resumed["completionReason"] == "matched"


def test_duplicate_interaction_completion_advances_the_workflow_once(db):
    gm, player, _, campaign = _world()
    schema = {"type": "boolean"}
    definition = _branching(player, schema=schema, equals=True)
    definition["id"] = "once"
    started, interaction, resumed = _run(campaign, gm, player, definition, True, key="once")
    assert len(resumed) == 1 and resumed[0]["context"]["decision"] is True
    version = resumed[0]["version"]

    replayed = DurableWorkflowService().resume_interaction(campaign_id=campaign, interaction_id=interaction["id"])
    recovered = DurableWorkflowService().recover_campaign(campaign, int(time.time()))
    assert replayed == []
    current = DurableWorkflowService().get(campaign_id=campaign, user_id=gm, package_id="rules",
                                           instance_id=started["id"]).value
    assert current["version"] == version and current["status"] == "COMPLETED"
    assert not [row for row in recovered if row["id"] == started["id"]]


def test_a_non_recipient_cannot_answer_and_nothing_is_projected(db):
    gm, player, other, campaign = _world()
    service = DurableWorkflowService()
    definition = _branching(player, schema={"type": "boolean"}, equals=True)
    definition["id"] = "authority"
    service.register(campaign_id=campaign, package_id="rules", definition=definition)
    started = service.start(campaign_id=campaign, user_id=gm, package_id="rules",
                            values={"definitionId": "authority", "idempotencyKey": "authority"}).value

    forged = DirectedInteractionService().respond(campaign_id=campaign, interaction_id=started["waitingOn"],
                                                  user_id=other, response=True, idempotency_key="forged")
    assert not forged.success
    assert DurableWorkflowService().resume_interaction(campaign_id=campaign, interaction_id=started["waitingOn"]) == []
    current = service.get(campaign_id=campaign, user_id=gm, package_id="rules", instance_id=started["id"]).value
    assert current["status"] == "WAITING_INTERACTION" and "decision" not in current["context"]


def test_cancelled_interaction_never_fabricates_a_player_answer(db):
    gm, player, _, campaign = _world()
    service = DurableWorkflowService()
    definition = _branching(player, schema={"type": "boolean"}, equals=True)
    definition["id"] = "cancelled"
    service.register(campaign_id=campaign, package_id="rules", definition=definition)
    started = service.start(campaign_id=campaign, user_id=gm, package_id="rules",
                            values={"definitionId": "cancelled", "idempotencyKey": "cancelled"}).value
    assert DirectedInteractionService().cancel(campaign_id=campaign, interaction_id=started["waitingOn"], user_id=gm).success

    resumed = DurableWorkflowService().resume_interaction(campaign_id=campaign, interaction_id=started["waitingOn"])
    assert resumed and "decision" not in resumed[0]["context"]
    # The branch saw an absent key, not a fabricated False.
    assert resumed[0]["completionReason"] == "unmatched"


def test_expired_interaction_never_fabricates_a_player_answer(db):
    gm, player, _, campaign = _world()
    service = DurableWorkflowService()
    definition = _branching(player, schema={"type": "boolean"}, equals=True)
    definition["id"] = "expired"
    definition["steps"][0]["request"]["deadline"] = int(time.time()) + 1
    service.register(campaign_id=campaign, package_id="rules", definition=definition)
    started = service.start(campaign_id=campaign, user_id=gm, package_id="rules",
                            values={"definitionId": "expired", "idempotencyKey": "expired"}).value

    interaction = DirectedInteractionService().get(campaign_id=campaign, interaction_id=started["waitingOn"], user_id=gm)
    assert interaction.success
    resumed = DurableWorkflowService().resume_interaction(campaign_id=campaign, interaction_id=started["waitingOn"])
    assert all("decision" not in row["context"] for row in resumed)


@pytest.mark.parametrize("bad_key", ["", " ", "a" * 192, "with space", "input", "lastResult", "interaction", 7, None])
def test_invalid_or_reserved_result_keys_are_rejected_at_registration(db, bad_key):
    gm, player, _, campaign = _world()
    definition = {"id": "invalid", "schemaVersion": 1, "steps": [
        {"type": "INTERACTION", "resultKey": bad_key, "request": {
            "recipients": [player], "title": "T", "text": "T",
            "responseSchema": {"type": "boolean"}, "deadline": int(time.time()) + 300}},
        {"type": "COMPLETE"}]}
    result = DurableWorkflowService().register(campaign_id=campaign, package_id="rules", definition=definition)
    assert not result.success and result.error_key == "sdk.workflows.invalid_definition"


def test_scalar_projection_is_rejected_when_the_answer_would_be_ambiguous(db):
    """Two independent responders cannot collapse into one branch value."""
    gm, player, other, campaign = _world()
    service = DurableWorkflowService()
    for recipients in ([player, other], []):
        definition = {"id": "ambiguous", "schemaVersion": 1, "steps": [
            _ask(player, schema={"type": "boolean"}, recipients=recipients), {"type": "COMPLETE"}]}
        result = service.register(campaign_id=campaign, package_id="rules", definition=definition)
        assert not result.success, recipients

    # The same multi-recipient request is still legal without a projection.
    allowed = {"id": "ambiguous", "schemaVersion": 1, "steps": [
        _ask(player, schema={"type": "boolean"}, recipients=[player, other], result_key=None), {"type": "COMPLETE"}]}
    assert service.register(campaign_id=campaign, package_id="rules", definition=allowed).success


def test_projection_carries_only_the_value_and_stays_inside_workflow_authority(db):
    gm, player, other, campaign = _world()
    definition = _branching(player, schema={"type": "boolean"}, equals=True)
    definition["id"] = "privacy"
    started, interaction, resumed = _run(campaign, gm, player, definition, True, key="privacy")

    projected = resumed[0]["context"]["decision"]
    assert projected is True and not isinstance(projected, dict)
    for leaked in (interaction["id"], player):
        assert leaked != projected

    # An unrelated player gains nothing: the workflow itself stays invisible.
    denied = DurableWorkflowService().get(campaign_id=campaign, user_id=other, package_id="rules",
                                          instance_id=started["id"])
    assert not denied.success and denied.error_key == "sdk.workflows.not_found"
    assert DurableWorkflowService().list(campaign_id=campaign, user_id=other, package_id="rules").value == []
