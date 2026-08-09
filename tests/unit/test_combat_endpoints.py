"""The combat HTTP surface: ten routes, all returning the same state payload."""

from __future__ import annotations

from litestar.testing import TestClient

from app.persistence.repositories.actor_repository import ActorRepository
from tests.conftest import (
    TEST_SESSION_CONFIG,
    login,
    seed_campaign,
    seed_member,
    seed_system,
    seed_user,
)


def make_actor(campaign_id: str, user_id: str, name: str, system_id: str = "valid-ruleset") -> str:
    return ActorRepository().create(
        campaign_id=campaign_id,
        system_id=system_id,
        actor_type="character",
        name=name,
        created_by_user_id=user_id,
    )


def post(client, csrf, path, campaign_id, **body):
    return client.post(
        f"/game/combat/{path}",
        json={"csrf_token": csrf, "campaign_id": campaign_id, **body},
        headers={"Accept": "application/json"},
    )


def test_gm_runs_a_full_encounter_over_http(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    aria = make_actor(campaign_id, gm_id, "Aria")
    bran = make_actor(campaign_id, gm_id, "Bran")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)

        started = post(client, csrf, "start", campaign_id, actor_ids=[aria])
        assert started.status_code == 200, started.text
        assert started.json()["active"] is True
        assert started.json()["round"] == 1

        added = post(client, csrf, "combatants/add", campaign_id, actor_ids=[bran])
        assert [c["name"] for c in added.json()["combatants"]] == ["Aria", "Bran"]

        by_name = {c["name"]: c["id"] for c in added.json()["combatants"]}
        post(client, csrf, "initiative/set", campaign_id, combatant_id=by_name["Bran"], value=20)
        ordered = post(
            client, csrf, "initiative/set", campaign_id, combatant_id=by_name["Aria"], value=5
        )
        assert [c["name"] for c in ordered.json()["combatants"]] == ["Bran", "Aria"]
        # Editing initiative reorders the list but leaves the turn where it was.
        assert ordered.json()["current_name"] == "Aria"

        jumped = post(client, csrf, "turn", campaign_id, combatant_id=by_name["Bran"])
        assert jumped.json()["current_name"] == "Bran"
        assert jumped.json()["turn"] == 0

        stepped = post(client, csrf, "turn", campaign_id, delta=1)
        assert stepped.json()["current_name"] == "Aria"

        wrapped = post(client, csrf, "turn", campaign_id, delta=1)
        assert wrapped.json()["round"] == 2
        assert wrapped.json()["current_name"] == "Bran"

        back = post(client, csrf, "turn", campaign_id, delta=-1)
        assert back.json()["round"] == 1
        assert back.json()["current_name"] == "Aria"

        # This campaign has no system declaring a roll, so there is nothing to roll.
        refused = post(client, csrf, "initiative/roll", campaign_id, scope="all")
        assert refused.status_code == 400
        assert refused.json()["error_key"] == "game.combat.errors.roll_unavailable"

        hidden = post(
            client, csrf, "combatants/flags", campaign_id, combatant_id=by_name["Bran"], hidden=True
        )
        assert next(c for c in hidden.json()["combatants"] if c["id"] == by_name["Bran"])["hidden"]

        removed = post(client, csrf, "combatants/remove", campaign_id, combatant_id=by_name["Bran"])
        assert [c["name"] for c in removed.json()["combatants"]] == ["Aria"]

        before_round = removed.json()["round"]
        rounds = post(client, csrf, "round", campaign_id, delta=1)
        assert rounds.json()["round"] == before_round + 1
        assert rounds.json()["turn"] == 0

        ended = post(client, csrf, "end", campaign_id)
        assert ended.json()["active"] is False


def test_state_is_readable_by_a_player_but_not_writable(db):
    from main import app

    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    actor_id = make_actor(campaign_id, gm_id, "Aria")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        post(client, csrf, "start", campaign_id, actor_ids=[actor_id])

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, player_id)
        state = client.get(
            f"/game/combat/state/{campaign_id}", headers={"Accept": "application/json"}
        )
        assert state.status_code == 200
        assert state.json()["active"] is True
        assert [c["name"] for c in state.json()["combatants"]] == ["Aria"]

        denied = post(client, csrf, "turn", campaign_id, delta=1)
        assert denied.status_code == 400
        assert denied.json()["error_key"] == "game.combat.errors.gm_required"


def test_a_text_initiative_system_types_and_reorders_over_http(db):
    """The PDF-style case: free text in the field, order arranged by hand."""
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id, "valid-text-initiative-ruleset")
    actors = [
        make_actor(campaign_id, gm_id, name, system_id="valid-text-initiative-ruleset")
        for name in ("Aria", "Bran", "Cass")
    ]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        started = post(client, csrf, "start", campaign_id, actor_ids=actors)
        assert started.json()["config"]["input"] == "text"
        assert started.json()["config"]["manual_order"] is True

        by_name = {c["name"]: c["id"] for c in started.json()["combatants"]}
        typed = post(
            client,
            csrf,
            "initiative/set",
            campaign_id,
            combatant_id=by_name["Cass"],
            value="primeira onda",
        )
        cass = next(c for c in typed.json()["combatants"] if c["id"] == by_name["Cass"])
        assert cass["initiative"] == "primeira onda"
        # The text says nothing about ranking, so the order is untouched.
        assert [c["name"] for c in typed.json()["combatants"]] == ["Aria", "Bran", "Cass"]

        moved = post(client, csrf, "order", campaign_id, combatant_id=by_name["Cass"], delta=-1)
        assert [c["name"] for c in moved.json()["combatants"]] == ["Aria", "Cass", "Bran"]

        moved = post(client, csrf, "order", campaign_id, combatant_id=by_name["Cass"], delta=-1)
        assert [c["name"] for c in moved.json()["combatants"]] == ["Cass", "Aria", "Bran"]

        refused = post(client, csrf, "initiative/roll", campaign_id, scope="all")
        assert refused.status_code == 400
        assert refused.json()["error_key"] == "game.combat.errors.roll_unavailable"


def test_a_numeric_system_rejects_hand_reordering_over_http(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    actor_id = make_actor(campaign_id, gm_id, "Aria")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        started = post(client, csrf, "start", campaign_id, actor_ids=[actor_id])
        assert started.json()["config"]["manual_order"] is False
        combatant_id = started.json()["combatants"][0]["id"]

        refused = post(client, csrf, "order", campaign_id, combatant_id=combatant_id, delta=1)
        assert refused.status_code == 400
        assert refused.json()["error_key"] == "game.combat.errors.order_is_automatic"
