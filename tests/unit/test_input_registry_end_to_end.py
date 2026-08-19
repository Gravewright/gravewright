"""Input Registry end-to-end behaviour: dispatch, authority and lifecycle.

Registration and bindings alone never proved that a bound key can do anything, so
these exercise the whole path a real invocation takes: the semantic command the core
Input Runtime resolves, the canonical pre-bound input the server owns, and the
authority every registered action still answers to.
"""

from __future__ import annotations

import pytest
from litestar.testing import TestClient

from app.engine.sdk.input_registry_service import InputRegistryService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user

PACKAGE_ID = "black-vault"
SCANNER = f"{PACKAGE_ID}:scanner.engage@1"


def _world():
    gm = seed_user(name="GM")
    player = seed_user(name="Operative")
    campaign = seed_campaign(gm)
    seed_member(campaign, player, "player")
    return gm, player, campaign


def _install(tmp_path, monkeypatch, gm, campaign):
    from tests.unit.test_black_vault_mission import install

    install(tmp_path, monkeypatch, gm, campaign)


def _actor(campaign, gm, name="Vault Systems"):
    from app.persistence.repositories.actor_repository import ActorRepository

    return ActorRepository().create(campaign_id=campaign, system_id="core", actor_type="character",
                                    name=name, created_by_user_id=gm)


def _command(client, campaign, name, payload, package=PACKAGE_ID):
    return client.post(f"/sdk/runtime/command/{name}",
                       json={"campaign_id": campaign, "package_id": package, "payload": payload})


def _read(client, campaign, resource, package=PACKAGE_ID, **params):
    return client.get(f"/sdk/runtime/read/{resource}",
                      params={"campaign_id": campaign, "package_id": package, **params})


def _register(client, campaign, definition, package=PACKAGE_ID):
    return _command(client, campaign, "input.register",
                    {"kind": "command", "definition": definition}, package)


def _scanner_command(actor_id, command_id="engage-scanner"):
    return {"id": command_id, "label": "Engage vault scanner", "contexts": ["global"],
            "defaultBindings": ["Alt+S"], "registeredAction": SCANNER,
            "actionInput": {"actorId": actor_id}}


def _scanner_state(actor_id, user_id):
    from app.engine.sheets.sheet_data_service import SheetDataService

    data = SheetDataService().get_data(actor_id=actor_id, user_id=user_id).data or {}
    return (data.get("blackVault") or {}).get("scanner")


# --- what a bound key actually produces ---------------------------------------

def test_a_bound_key_invocation_executes_the_registered_action(db, tmp_path, monkeypatch):
    """The Input Runtime sends no action input; the server supplies its own."""
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        executed = _command(client, campaign, "input.execute", {"commandId": "engage-scanner"})

    assert executed.status_code == 201, executed.text
    assert executed.json()["result"]["action"] == "scanner.engage"
    assert _scanner_state(actor, gm) == "ACTIVE"


def test_a_local_only_command_registers_but_has_nothing_to_execute(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        registered = _register(client, campaign, {
            "id": "open-operations", "label": "Open Operations", "contexts": ["global"],
            "defaultBindings": ["Alt+O"]})
        assert registered.status_code == 201, registered.text
        executed = _command(client, campaign, "input.execute", {"commandId": "open-operations"})

    assert executed.status_code == 400
    assert executed.json()["error_key"] == "sdk.input.command_not_executable"


def test_a_local_only_command_may_not_pre_bind_action_input(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        registered = _register(client, campaign, {
            "id": "stray", "label": "Stray", "contexts": ["global"],
            "actionInput": {"actorId": "x"}})

    assert registered.status_code == 400
    assert registered.json()["error_key"] == "sdk.input.invalid_definition"


# --- forgery ------------------------------------------------------------------

def test_a_caller_cannot_replace_pre_bound_action_input(db, tmp_path, monkeypatch):
    """The registration owns the payload; an invocation may not substitute one."""
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)
    victim = _actor(campaign, gm, name="Someone Else")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        forged = _command(client, campaign, "input.execute",
                          {"commandId": "engage-scanner", "inputs": {"actorId": victim}})

    assert forged.status_code == 403
    assert forged.json()["error_key"] == "sdk.input.action_input_not_allowed"
    assert _scanner_state(victim, gm) is None
    assert _scanner_state(actor, gm) is None


def test_an_unknown_command_id_is_rejected(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        missing = _command(client, campaign, "input.execute", {"commandId": "no-such-command"})

    assert missing.status_code == 404
    assert missing.json()["error_key"] == "sdk.input.command_not_found"


def test_a_command_cannot_reference_another_packages_action(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        foreign = _register(client, campaign, {
            "id": "borrowed", "label": "Borrowed", "contexts": ["global"],
            "registeredAction": "some-other-package:scanner.engage@1",
            "actionInput": {"actorId": actor}})

    assert foreign.status_code == 400
    assert foreign.json()["error_key"] == "sdk.input.invalid_definition"


def test_a_command_registered_in_one_campaign_is_invisible_in_another(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    other = seed_campaign(gm)
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        crossed = _command(client, other, "input.execute", {"commandId": "engage-scanner"})

    assert crossed.status_code in {403, 404}


def test_pre_bound_input_is_bounded_and_typed(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    oversized_id = "a" * (InputRegistryService.MAX_ACTION_INPUT_BYTES + 64)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        oversized = _register(client, campaign, {
            "id": "bulky", "label": "Bulky", "contexts": ["global"], "registeredAction": SCANNER,
            "actionInput": {"actorId": oversized_id}})
        wrong_shape = _register(client, campaign, {
            "id": "listy", "label": "Listy", "contexts": ["global"], "registeredAction": SCANNER,
            "actionInput": ["actorId"]})

    assert oversized.status_code == 400
    assert wrong_shape.status_code == 400


# --- authority ----------------------------------------------------------------

def test_a_player_invoking_the_command_cannot_mutate_a_gm_owned_actor(db, tmp_path, monkeypatch):
    """The command carries no authority of its own; the action still checks the caller."""
    from main import app

    gm, player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        login(client, player)
        attempted = _command(client, campaign, "input.execute", {"commandId": "engage-scanner"})

    assert attempted.status_code in {403, 404}
    assert _scanner_state(actor, gm) is None


def test_a_package_without_the_capability_cannot_register_a_command(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        blocked = _register(client, campaign, {
            "id": "nope", "label": "Nope", "contexts": ["global"]}, package="not-installed")

    assert blocked.status_code in {403, 404}


def test_an_unknown_context_is_rejected(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        bogus = _register(client, campaign, {
            "id": "ctx", "label": "Ctx", "contexts": ["everywhere"]})

    assert bogus.status_code == 400


# --- bindings -----------------------------------------------------------------

def test_binding_lifecycle_reserved_conflict_and_rebind(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        assert _register(client, campaign, _scanner_command(actor, "second-command")).status_code == 201

        first = _command(client, campaign, "input.bindings.set",
                         {"commandId": "engage-scanner", "binding": "Alt+J"})
        reserved = _command(client, campaign, "input.bindings.set",
                            {"commandId": "engage-scanner", "binding": "F5"})
        conflict = _command(client, campaign, "input.bindings.set",
                            {"commandId": "second-command", "binding": "Alt+J"})
        rebound = _command(client, campaign, "input.bindings.set",
                           {"commandId": "engage-scanner", "binding": "Alt+K"})
        listed = _read(client, campaign, "input.bindings").json()["bindings"]

    assert first.status_code == 201 and first.json()["result"]["binding"] == "Alt+J"
    assert reserved.status_code == 400
    assert reserved.json()["error_key"] == "sdk.input.binding_reserved"
    assert conflict.status_code == 400
    assert conflict.json()["error_key"] == "sdk.input.binding_conflict"
    assert rebound.status_code == 201 and rebound.json()["result"]["binding"] == "Alt+K"
    assert {row["command_id"]: row["binding"] for row in listed}["engage-scanner"] == "Alt+K"


def test_bindings_are_per_user(db, tmp_path, monkeypatch):
    from main import app

    gm, player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        assert _command(client, campaign, "input.bindings.set",
                        {"commandId": "engage-scanner", "binding": "Alt+J"}).status_code == 201
        login(client, player)
        theirs = _read(client, campaign, "input.bindings").json()

    assert theirs.get("bindings") == []


def test_a_registered_command_is_listed_with_its_public_projection(db, tmp_path, monkeypatch):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        listed = _read(client, campaign, "input.commands").json()["commands"]

    entry = next(row for row in listed if row["id"] == "engage-scanner")
    assert entry["registeredAction"] == SCANNER
    assert entry["actionInput"] == {"actorId": actor}
    assert entry["packageId"] == PACKAGE_ID


def test_re_registration_rebinds_the_canonical_action_input(db, tmp_path, monkeypatch):
    """A package may re-register once it knows a different legitimate resource."""
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    first = _actor(campaign, gm)
    second = _actor(campaign, gm, name="Backup Systems")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(first)).status_code == 201
        assert _register(client, campaign, _scanner_command(second)).status_code == 201
        assert _command(client, campaign, "input.execute",
                        {"commandId": "engage-scanner"}).status_code == 201

    assert _scanner_state(second, gm) == "ACTIVE"
    assert _scanner_state(first, gm) is None


# --- events -------------------------------------------------------------------

@pytest.fixture
def broadcasts(monkeypatch):
    """Record every transport broadcast instead of sending it."""
    from app.realtime.transport import RealtimeTransport

    sent: list[tuple[str, object, dict]] = []

    async def to_room(self, *, room_id, event, payload):  # noqa: ANN001
        sent.append(("room", event, payload))

    async def to_players(self, *, player_ids, event, payload):  # noqa: ANN001
        sent.append(("players", event, payload))

    monkeypatch.setattr(RealtimeTransport, "to_room", to_room)
    monkeypatch.setattr(RealtimeTransport, "to_players", to_players)
    return sent


def _names(sent):
    return [str(getattr(event, "value", event)) for _scope, event, _payload in sent]


def test_a_command_execution_completes_like_any_registered_action(db, tmp_path, monkeypatch, broadcasts):
    """Same canonical event as the direct rules.actions path, same semantics."""
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        broadcasts.clear()
        assert _command(client, campaign, "input.execute",
                        {"commandId": "engage-scanner"}).status_code == 201
        direct = list(broadcasts)
        broadcasts.clear()
        assert _command(client, campaign, "rules.action.execute", {
            "actionId": "scanner.engage", "version": 1,
            "input": {"actorId": actor}}).status_code in {200, 201}

    completed = [payload for _scope, event, payload in direct
                 if str(getattr(event, "value", event)) == "rules.action.completed"]
    assert len(completed) == 1, _names(direct)
    assert completed[0]["package_id"] == PACKAGE_ID
    assert completed[0]["action_id"] == "scanner.engage"
    assert completed[0]["version"] == 1
    assert completed[0]["execution_id"]
    # The direct path announces the same event, so consumers need no special case.
    assert "rules.action.completed" in _names(broadcasts)


def test_a_failed_command_execution_announces_nothing(db, tmp_path, monkeypatch, broadcasts):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        broadcasts.clear()
        assert _command(client, campaign, "input.execute",
                        {"commandId": "engage-scanner", "inputs": {"actorId": actor}}).status_code == 403

    assert "rules.action.completed" not in _names(broadcasts)


def test_a_successful_rebind_announces_the_declared_binding_event(db, tmp_path, monkeypatch, broadcasts):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        broadcasts.clear()
        assert _command(client, campaign, "input.bindings.set",
                        {"commandId": "engage-scanner", "binding": "Alt+K"}).status_code == 201

    changed = [payload for scope, event, payload in broadcasts
               if str(getattr(event, "value", event)) == "input.binding.changed"]
    assert len(changed) == 1, _names(broadcasts)
    assert changed[0]["command_id"] == "engage-scanner"
    assert changed[0]["binding"] == "Alt+K"
    assert changed[0]["package_id"] == PACKAGE_ID
    # A binding is the user's own; it is never broadcast to the whole room.
    assert all(scope == "players" for scope, event, _payload in broadcasts
               if str(getattr(event, "value", event)) == "input.binding.changed")


def test_a_rejected_rebind_announces_nothing(db, tmp_path, monkeypatch, broadcasts):
    from main import app

    gm, _player, campaign = _world()
    _install(tmp_path, monkeypatch, gm, campaign)
    actor = _actor(campaign, gm)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        assert _register(client, campaign, _scanner_command(actor)).status_code == 201
        assert _register(client, campaign, _scanner_command(actor, "rival")).status_code == 201
        assert _command(client, campaign, "input.bindings.set",
                        {"commandId": "engage-scanner", "binding": "Alt+J"}).status_code == 201
        broadcasts.clear()
        assert _command(client, campaign, "input.bindings.set",
                        {"commandId": "engage-scanner", "binding": "F5"}).status_code == 400
        assert _command(client, campaign, "input.bindings.set",
                        {"commandId": "rival", "binding": "Alt+J"}).status_code == 400

    assert "input.binding.changed" not in _names(broadcasts)
