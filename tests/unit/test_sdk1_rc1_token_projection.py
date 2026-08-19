"""RC 1: the SDK token read exposes the declared DTO and nothing else.

Before RC 1 the runtime passed the core token view straight through, so packages
received undeclared internals — including `controlled_by_user_ids`, an unfiltered
controller list. The public contract declares `id` and `controllers`; those, and
only those, are what a package may depend on.
"""

from __future__ import annotations

import json
from pathlib import Path

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "docs/sdk/_data/gravewright-sdk-1.json").read_text(encoding="utf-8"))
DECLARED = set(CONTRACT["dtos"]["TokenDTO"]["properties"])

# Core view fields that used to leak through the SDK read.
INTERNAL_LEAKS = {
    "token_id", "controlled_by_user_ids", "controlled_by_role", "actor_link_mode",
    "overrides", "conditions", "effects", "status_summary", "vision_enabled", "vision_range",
}


def _world():
    gm = seed_user(name="GM")
    a = seed_user(name="Player A")
    b = seed_user(name="Player B")
    campaign = seed_campaign(gm)
    seed_member(campaign, a, "player")
    seed_member(campaign, b, "player")
    return gm, a, b, campaign


def _token(campaign, scene, gm, owner=None, x=1, y=1, hidden=False):
    from app.persistence.repositories.actor_repository import ActorRepository
    from app.persistence.repositories.token_repository import TokenRepository

    actor = ActorRepository().create(campaign_id=campaign, system_id="core", actor_type="character",
                                     name="Operative", created_by_user_id=gm)
    if owner:
        ActorRepository().add_owner(actor_id=actor, user_id=owner)
    return TokenRepository().create(scene_id=scene["id"], actor_id=actor, grid_x=x, grid_y=y,
                                    hidden=1 if hidden else 0)


def _read(client, campaign, **params):
    return client.get("/sdk/runtime/read/tokens",
                      params={"campaign_id": campaign, "package_id": "runtime-addon", **params})


def test_token_read_returns_exactly_the_declared_public_dto(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = _world()
    scene = seed_scene(campaign)
    token = _token(campaign, scene, gm, owner=a)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["tokens.read"])

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        listed = _read(client, campaign, scene_id=scene["id"]).json()["tokens"]
        fetched = _read(client, campaign, scene_id=scene["id"], entity_id=token["id"]).json()["token"]

    assert len(listed) == 1
    for value in (listed[0], fetched):
        assert set(value) == DECLARED, set(value) ^ DECLARED
        # No undeclared core field survives the projection.
        assert not (set(value) & INTERNAL_LEAKS)
    assert listed[0] == fetched


def test_token_identity_is_the_contracted_id_with_no_compatibility_alias(db, tmp_path, monkeypatch):
    from main import app

    gm, a, _b, campaign = _world()
    scene = seed_scene(campaign)
    token = _token(campaign, scene, gm, owner=a)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["tokens.read"])

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        value = _read(client, campaign, scene_id=scene["id"]).json()["tokens"][0]

    assert value["id"] == token["id"]
    # The previously leaked alias is deliberately not reintroduced.
    assert "token_id" not in value
    assert "id" in DECLARED and "token_id" not in DECLARED


def test_controllers_never_leak_through_the_projection(db, tmp_path, monkeypatch):
    from main import app

    gm, a, b, campaign = _world()
    scene = seed_scene(campaign)
    mine = _token(campaign, scene, gm, owner=a)
    theirs = _token(campaign, scene, gm, owner=b, x=2, y=2)
    hidden = _token(campaign, scene, gm, owner=b, x=3, y=3, hidden=True)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["tokens.read"])

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, a)
        tokens = _read(client, campaign, scene_id=scene["id"]).json()["tokens"]

    by_id = {value["id"]: value for value in tokens}
    assert hidden["id"] not in by_id
    assert set(by_id[mine["id"]]["controllers"]) == {gm, a}
    assert by_id[theirs["id"]]["controllers"] == []
    # Player B is not discoverable anywhere in what Player A received.
    assert b not in json.dumps(tokens)
