"""Reading a campaign file that a sheet embeds.

The PDF ruleset makes the sheet *be* a library file, and reading the library
answers to table-wide authority. Without this a player opens their own character
sheet and is denied its contents.

The rule: a file one of your own sheets points at is yours to read, and nothing
else in the library becomes reachable with it.
"""

from __future__ import annotations

import pytest

from app.engine.assets.asset_read_service import AssetReadService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.asset_repository import AssetRepository
from tests.conftest import seed_campaign, seed_member, seed_user

SYSTEM_ID = "valid-ruleset"


@pytest.fixture
def table(db, tmp_path, monkeypatch):
    gm = seed_user(name="GM")
    player = seed_user(name="Player")
    outsider = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, "player")
    return {
        "gm": gm,
        "player": player,
        "outsider": outsider,
        "campaign_id": campaign_id,
        "root": tmp_path,
    }


def make_actor(campaign_id: str, user_id: str, name: str = "Aria") -> str:
    return ActorRepository().create(
        campaign_id=campaign_id,
        system_id=SYSTEM_ID,
        actor_type="character",
        name=name,
        created_by_user_id=user_id,
    )


def upload(table, *, name: str = "sheet.pdf") -> str:
    """A library file owned by the GM, with real bytes on disk."""
    relative = f"storage/library/{name}"
    path = table["root"] / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.7\n")
    return AssetRepository().create(
        campaign_id=table["campaign_id"],
        owner_user_id=table["gm"],
        filename=name,
        content_type="application/pdf",
        byte_size=9,
        storage_path=relative,
        hash="deadbeef",
    )["id"]


def point_sheet_at(actor_id: str, campaign_id: str, asset_id: str) -> None:
    ScopedJsonStorage().write_actor(
        system_id=SYSTEM_ID,
        campaign_id=campaign_id,
        actor_id=actor_id,
        version=1,
        data={"pdf": {"asset": asset_id, "page": 1}},
    )


def read(table, asset_id: str, user_id: str):
    return AssetReadService().get_asset(
        asset_id=asset_id, user_id=user_id, project_root=table["root"]
    )


def test_the_gm_reads_the_file_its_sheet_points_at(table):
    actor_id = make_actor(table["campaign_id"], table["gm"])
    asset_id = upload(table)
    point_sheet_at(actor_id, table["campaign_id"], asset_id)

    result = read(table, asset_id, table["gm"])
    assert result.success
    assert result.media_type == "application/pdf"
    assert result.path is not None and result.path.read_bytes().startswith(b"%PDF")


def test_a_player_who_owns_the_actor_reads_it_too(table):
    """The bug this exists for: the sheet opens, the document behind it 403s."""
    actor_id = make_actor(table["campaign_id"], table["gm"])
    ActorRepository().add_owner(actor_id=actor_id, user_id=table["player"])
    asset_id = upload(table)
    point_sheet_at(actor_id, table["campaign_id"], asset_id)

    assert read(table, asset_id, table["player"]).success


def test_a_player_who_cannot_view_the_actor_is_denied(table):
    actor_id = make_actor(table["campaign_id"], table["gm"])
    asset_id = upload(table)
    point_sheet_at(actor_id, table["campaign_id"], asset_id)

    result = read(table, asset_id, table["player"])
    assert not result.success
    assert result.error_key == "not_authorized"


def test_viewing_one_actor_does_not_open_the_rest_of_the_library(table):
    """The reference is checked against the sheet, not merely asserted."""
    actor_id = make_actor(table["campaign_id"], table["gm"])
    ActorRepository().add_owner(actor_id=actor_id, user_id=table["player"])
    mine = upload(table, name="mine.pdf")
    secret = upload(table, name="boss-reveal.pdf")
    point_sheet_at(actor_id, table["campaign_id"], mine)

    assert read(table, mine, table["player"]).success
    denied = read(table, secret, table["player"])
    assert not denied.success
    assert denied.error_key == "not_authorized"


def test_a_non_member_is_denied(table):
    actor_id = make_actor(table["campaign_id"], table["gm"])
    asset_id = upload(table)
    point_sheet_at(actor_id, table["campaign_id"], asset_id)

    result = read(table, asset_id, table["outsider"])
    assert not result.success
    assert result.error_key == "not_authorized"


def test_an_asset_from_another_campaign_is_not_reachable(table):
    """A reference from this table never reaches into another one."""
    other_campaign = seed_campaign(table["gm"], title="Other")
    relative = "storage/library/other.pdf"
    path = table["root"] / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.7\n")
    foreign = AssetRepository().create(
        campaign_id=other_campaign,
        owner_user_id=table["gm"],
        filename="other.pdf",
        content_type="application/pdf",
        byte_size=9,
        storage_path=relative,
        hash="cafe",
    )["id"]

    actor_id = make_actor(table["campaign_id"], table["gm"])
    ActorRepository().add_owner(actor_id=actor_id, user_id=table["player"])
    point_sheet_at(actor_id, table["campaign_id"], foreign)

    result = read(table, foreign, table["player"])
    assert not result.success
    assert result.error_key == "not_authorized"


def test_a_sheet_that_references_nothing_authorizes_nothing(table):
    """The GM uploaded it, so the GM reads it; a player with an empty sheet does not."""
    actor_id = make_actor(table["campaign_id"], table["gm"])
    ActorRepository().add_owner(actor_id=actor_id, user_id=table["player"])
    asset_id = upload(table)

    assert read(table, asset_id, table["gm"]).success
    denied = read(table, asset_id, table["player"])
    assert not denied.success
    assert denied.error_key == "not_authorized"


def test_the_reference_is_found_wherever_the_system_put_it(table):
    """Which field holds the id is the ruleset's business, not the core's."""
    actor_id = make_actor(table["campaign_id"], table["gm"])
    ActorRepository().add_owner(actor_id=actor_id, user_id=table["player"])
    asset_id = upload(table)
    ScopedJsonStorage().write_actor(
        system_id=SYSTEM_ID,
        campaign_id=table["campaign_id"],
        actor_id=actor_id,
        version=1,
        data={"pages": [{"background": {"file": asset_id}}]},
    )

    assert read(table, asset_id, table["player"]).success


def test_a_missing_file_on_disk_is_not_found(table):
    actor_id = make_actor(table["campaign_id"], table["gm"])
    asset_id = AssetRepository().create(
        campaign_id=table["campaign_id"],
        owner_user_id=table["gm"],
        filename="gone.pdf",
        content_type="application/pdf",
        byte_size=9,
        storage_path="storage/library/gone.pdf",
        hash="beef",
    )["id"]
    point_sheet_at(actor_id, table["campaign_id"], asset_id)

    result = read(table, asset_id, table["gm"])
    assert not result.success
    assert result.error_key == "not_found"
