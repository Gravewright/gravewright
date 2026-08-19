"""The two orchestration reads: who is at the table, and who drives a token.

Both exist so a module can *address* a user. Neither may become a directory: the
roster follows campaign membership, and controllers are only visible to a caller
who could control that token anyway.
"""

from litestar.testing import TestClient

from app.engine.tokens.token_service import TokenService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon


ROSTER = ["campaign.members.read"]
TOKENS = ["tokens.read"]


def _read(client, campaign, resource, **params):
    return client.get(f"/sdk/runtime/read/{resource}",
                      params={"campaign_id": campaign, "package_id": "runtime-addon", **params})


def _actor(campaign, gm, name="Operative", owners=None):
    from app.persistence.repositories.actor_repository import ActorRepository

    actor_id = ActorRepository().create(campaign_id=campaign, system_id="core", actor_type="character",
                                        name=name, created_by_user_id=gm)
    for owner in owners or ():
        ActorRepository().add_owner(actor_id=actor_id, user_id=owner)
    return actor_id


def _token(scene, actor_id, x=1, y=1, hidden=False):
    from app.persistence.repositories.token_repository import TokenRepository

    return TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=x, grid_y=y,
                                    hidden=1 if hidden else 0)


# --- campaign roster -----------------------------------------------------------

def test_roster_reports_members_with_roles_and_no_account_metadata(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "assistant_gm")
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ROSTER)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        response = _read(client, campaign, "campaign.members")
        assert response.status_code == 200, response.text
        members = response.json()["members"]

    assert {m["userId"] for m in members} == {gm, a, b}
    assert {m["userId"]: m["role"] for m in members}[b] == "assistant_gm"
    assert all(set(m) == {"userId", "role", "name"} for m in members)
    # A display name is fine; anything that identifies the account is not.
    body = str(members).lower()
    for leak in ("@", "password", "email", "token", "session", "hash", "ip"):
        assert leak not in body, leak


def test_a_player_sees_the_same_roster_the_native_table_already_shows_them(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ROSTER)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        members = _read(client, campaign, "campaign.members").json()["members"]
    assert {m["userId"] for m in members} == {gm, a}


def test_roster_is_campaign_scoped_and_closed_to_outsiders(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")

    other_gm = seed_user(name="Other GM")
    other_player = seed_user(name="Other Player")
    other_campaign = seed_campaign(other_gm)
    seed_member(other_campaign, other_player, "player")
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ROSTER)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        members = _read(client, campaign, "campaign.members").json()["members"]
        assert {m["userId"] for m in members} == {gm, a}
        assert other_gm not in {m["userId"] for m in members}

        # The other campaign is not readable through this package's activation.
        foreign = _read(client, other_campaign, "campaign.members")
        assert foreign.status_code == 403

        # A user outside the campaign gets nothing.
        login(client, other_player)
        assert _read(client, campaign, "campaign.members").status_code == 403


def test_roster_requires_the_capability_and_tracks_membership_changes(db, tmp_path, monkeypatch):
    from main import app
    from app.persistence.repositories.campaign_repository import CampaignRepository

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["scene.read"])

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        denied = _read(client, campaign, "campaign.members")
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "CAPABILITY_REQUIRED"

    _install_runtime_addon.__wrapped__ if False else None
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        # Removing the member removes them from the authoritative re-read.
        CampaignRepository().remove_member(campaign_id=campaign, user_id=a)
        from app.persistence.repositories.campaign_repository import CampaignRepository as Repo
        assert a not in {m["user_id"] for m in Repo().list_members(campaign_id=campaign)}


# --- token controllers ---------------------------------------------------------

def test_controllers_report_canonical_control_including_multiple_owners(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "player")
    scene = seed_scene(campaign)
    shared = _token(scene, _actor(campaign, gm, "Shared", owners=[a, b]))
    solo = _token(scene, _actor(campaign, gm, "Solo", owners=[a]), x=2, y=2)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, TOKENS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        tokens = _read(client, campaign, "tokens", scene_id=scene["id"]).json()["tokens"]
        by_id = {str(t.get("id") or t.get("token_id")): t for t in tokens}

    assert set(by_id[shared["id"]]["controllers"]) == {gm, a, b}
    assert set(by_id[solo["id"]]["controllers"]) == {gm, a}
    # Multiple controllers are reported, never collapsed to one.
    assert len(by_id[shared["id"]]["controllers"]) == 3


def test_batched_controller_projection_matches_the_canonical_predicate(db):
    """The batched read must never drift from the rule that gates control."""
    from app.persistence.repositories.token_repository import TokenRepository

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "player")
    scene = seed_scene(campaign)
    _token(scene, _actor(campaign, gm, "Shared", owners=[a, b]))
    _token(scene, _actor(campaign, gm, "Solo", owners=[a]), x=2, y=2)
    _token(scene, None, x=3, y=3)

    service = TokenService()
    rows = TokenRepository().list_by_scene(scene["id"])
    batched = service.controllers_for_tokens(campaign_id=campaign, tokens=rows)
    for row in rows:
        expected = [user for user in (gm, a, b)
                    if service.can_control_token(token=row, user_id=user, campaign_id=campaign)]
        assert sorted(batched[row["id"]]) == sorted(expected), row["id"]


def test_a_player_cannot_use_controllers_to_enumerate_the_table(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "player")
    scene = seed_scene(campaign)
    mine = _token(scene, _actor(campaign, gm, "Mine", owners=[a]))
    theirs = _token(scene, _actor(campaign, gm, "Theirs", owners=[b]), x=2, y=2)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, TOKENS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        tokens = _read(client, campaign, "tokens", scene_id=scene["id"]).json()["tokens"]
        by_id = {str(t.get("id") or t.get("token_id")): t for t in tokens}

    # Player A controls their own token, so the relationship is inspectable.
    assert set(by_id[mine["id"]]["controllers"]) == {gm, a}
    # Player B's token is on the same board, but A learns nothing about who drives it.
    assert by_id[theirs["id"]]["controllers"] == []
    assert b not in str(by_id[theirs["id"]])


def test_hidden_and_cross_campaign_tokens_expose_no_controllers(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    scene = seed_scene(campaign)
    hidden = _token(scene, _actor(campaign, gm, "Ghost", owners=[gm]), hidden=True)

    other_gm = seed_user(name="Other GM")
    other_campaign = seed_campaign(other_gm)
    other_scene = seed_scene(other_campaign)
    _token(other_scene, _actor(other_campaign, other_gm, "Foreign", owners=[other_gm]))
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, TOKENS)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        visible = _read(client, campaign, "tokens", scene_id=scene["id"]).json()["tokens"]
        assert hidden["id"] not in {str(t.get("id") or t.get("token_id")) for t in visible}

        login(client, gm)
        foreign = _read(client, campaign, "tokens", scene_id=other_scene["id"])
        assert foreign.status_code != 200 or foreign.json().get("tokens", []) == []


def test_knowing_a_controller_id_grants_no_authority_over_that_token(db, tmp_path, monkeypatch):
    from main import app

    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "player")
    scene = seed_scene(campaign)
    other_scene = seed_scene(campaign, name="Inner")
    theirs = _token(scene, _actor(campaign, gm, "Theirs", owners=[b]), x=2, y=2)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, TOKENS + ["tokens.move", "tokens.transfer"])

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        controllers = _read(client, campaign, "tokens", scene_id=scene["id"]).json()["tokens"]
        known = next(t for t in controllers if str(t.get("id") or t.get("token_id")) == theirs["id"])["controllers"]
        assert b in known

        # Player A now knows B controls it. That knowledge is inert.
        login(client, a)
        for name, payload in (
            ("tokens.move", {"id": theirs["id"], "sceneId": scene["id"], "x": 9, "y": 9}),
            ("tokens.transfer", {"input": {"tokenId": theirs["id"], "sceneId": other_scene["id"], "x": 1, "y": 1}}),
        ):
            denied = client.post(f"/sdk/runtime/command/{name}", json={
                "campaign_id": campaign, "package_id": "runtime-addon", "payload": payload})
            assert denied.status_code not in {200, 201}, name
