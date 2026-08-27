from __future__ import annotations

import json

from app.engine.journals import journal_data
from app.engine.journals.journal_service import JournalService
from app.persistence.repositories.journal_repository import JournalRepository
from tests.conftest import seed_campaign, seed_user


def test_roll_table_normalizes_entries_and_options():
    table = journal_data.normalize_roll_table_data({
        "withReplacement": False,
        "resultVisibility": "gm",
        "entries": [
            {"id": "b", "name": "Rare", "weight": 0, "sortOrder": 20},
            {"id": "a", "name": "Common", "weight": 3, "active": False, "sortOrder": 10},
        ],
    })

    assert table["withReplacement"] is False
    assert table["resultVisibility"] == "gm"
    assert [entry["id"] for entry in table["entries"]] == ["a", "b"]
    assert table["entries"][1]["weight"] == 1


def test_roll_table_weighted_roll_without_replacement_persists_draw(db, monkeypatch):
    gm_id = seed_user(name="GM", email="gm-roll-table@test.com")
    campaign_id = seed_campaign(gm_id)
    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="roll_table",
        title="Encontros",
        data={
            "withReplacement": False,
            "entries": [
                {"id": "wolves", "name": "Wolves", "weight": 2},
                {"id": "dragon", "name": "Dragon", "weight": 1},
            ],
        },
    )
    monkeypatch.setattr("app.engine.journals.journal_service.secrets.randbelow", lambda total: 2)

    result = JournalService().roll_table(journal_id=created.journal_id, user_id=gm_id)
    stored = json.loads(JournalRepository().get_by_id(created.journal_id)["data_json"])

    assert result.success
    assert result.entry["id"] == "dragon"
    assert result.ticket == 3
    assert next(entry for entry in stored["entries"] if entry["id"] == "dragon")["drawn"] is True


def test_roll_table_rejects_player_roll(db):
    gm_id = seed_user(name="GM", email="gm-roll-table-guard@test.com")
    player_id = seed_user(name="Player", email="player-roll-table-guard@test.com")
    campaign_id = seed_campaign(gm_id)
    created = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm_id, journal_type="roll_table",
        title="Loot", data={"entries": [{"name": "Coin", "weight": 1}]},
    )

    result = JournalService().roll_table(journal_id=created.journal_id, user_id=player_id)

    assert not result.success
