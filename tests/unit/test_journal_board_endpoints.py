from __future__ import annotations

from litestar.testing import TestClient

from app.engine.journals.journal_service import JournalService
from app.persistence.repositories.journal_repository import JournalRepository
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def _make_board_with_quests(gm_id, campaign_id):
    svc = JournalService()
    board = svc.create_journal(
        campaign_id=campaign_id, user_id=gm_id, journal_type="quest_board", title="Board",
    )
    q1 = svc.create_journal(
        campaign_id=campaign_id, user_id=gm_id, journal_type="quest", title="Quest 1",
        data={"status": "available", "public": {"summary": "one"}},
    )
    q2 = svc.create_journal(
        campaign_id=campaign_id, user_id=gm_id, journal_type="quest", title="Quest 2",
        data={"status": "available", "public": {"summary": "two"}},
    )
    assert svc.add_quest_to_board(
        board_id=board.journal_id, quest_id=q1.journal_id, requester_user_id=gm_id
    ).success
    assert svc.add_quest_to_board(
        board_id=board.journal_id, quest_id=q2.journal_id, requester_user_id=gm_id
    ).success
    return board.journal_id, q1.journal_id, q2.journal_id


def test_board_pin_endpoint_persists(db):
    from main import app

    gm_id = seed_user(name="GM", email="gm-board-pin-ep@test.com")
    campaign_id = seed_campaign(gm_id)
    board_id, q1, _q2 = _make_board_with_quests(gm_id, campaign_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        resp = client.post(
            "/game/journal/board/pin",
            data={"csrf_token": csrf, "board_id": board_id, "quest_id": q1, "pinned": "1"},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200, resp.text

    entry = JournalRepository().get_board_entry(board_id=board_id, quest_id=q1)
    assert entry is not None
    assert bool(entry["pinned"]) is True


def test_board_reorder_endpoint_persists(db):
    from main import app

    gm_id = seed_user(name="GM", email="gm-board-reorder-ep@test.com")
    campaign_id = seed_campaign(gm_id)
    board_id, q1, q2 = _make_board_with_quests(gm_id, campaign_id)

    before = [e["quest_id"] for e in JournalRepository().list_board_entries(board_id=board_id)]
    assert before == [q1, q2]

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        resp = client.post(
            "/game/journal/board/reorder",
            data={"csrf_token": csrf, "board_id": board_id, "quest_ids": [q2, q1]},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200, resp.text

    after = [e["quest_id"] for e in JournalRepository().list_board_entries(board_id=board_id)]
    assert after == [q2, q1]
