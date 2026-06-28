from __future__ import annotations

import io

from PIL import Image

from app.domain.roles import PlayerRole
from app.engine.decks.card_asset_service import CardAssetService
from app.infrastructure.storage.local_journal_asset_storage import LocalJournalAssetStorage
from app.persistence.repositories.journal_asset_repository import JournalAssetRepository
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


def _png_bytes(width: int = 16, height: int = 24) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (30, 80, 120)).save(buffer, format="PNG")
    return buffer.getvalue()


def _service(tmp_path) -> CardAssetService:
    return CardAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "card-assets"))


def test_gm_uploads_card_front_asset(db, tmp_path):
    gm_id = seed_user(name="GM", email="card-asset-gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = _service(tmp_path).upload_image(
        campaign_id=campaign_id,
        user_id=gm_id,
        filename="front.png",
        content_type="image/png",
        data=_png_bytes(),
        purpose="card_front",
    )

    assert result.success, result.error_key
    assert result.src == f"/game/journal/asset/{result.asset_id}"
    assert result.width == 16
    assert result.height == 24
    row = JournalAssetRepository().get_by_id(result.asset_id or "")
    assert row is not None
    assert row["journal_id"] is None
    assert row["purpose"] == "card_front"


def test_player_cannot_upload_card_asset_by_default(db, tmp_path):
    gm_id = seed_user(name="GM", email="card-asset-deny-gm@test.com")
    player_id = seed_user(name="Player", email="card-asset-deny-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = _service(tmp_path).upload_image(
        campaign_id=campaign_id,
        user_id=player_id,
        filename="front.png",
        content_type="image/png",
        data=_png_bytes(),
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"


def test_card_asset_upload_rejects_svg_and_executable(db, tmp_path):
    gm_id = seed_user(name="GM", email="card-asset-svg-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    service = _service(tmp_path)

    svg = service.upload_image(
        campaign_id=campaign_id,
        user_id=gm_id,
        filename="front.svg",
        content_type="image/svg+xml",
        data=b"<svg></svg>",
    )
    exe = service.upload_image(
        campaign_id=campaign_id,
        user_id=gm_id,
        filename="front.exe",
        content_type="application/x-msdownload",
        data=b"MZ",
    )

    assert not svg.success
    assert svg.error_key == "game.cards.assets.errors.unsupported_type"
    assert not exe.success
    assert exe.error_key == "game.cards.assets.errors.unsupported_type"


def test_card_asset_upload_sanitizes_traversal_filename(db, tmp_path):
    gm_id = seed_user(name="GM", email="card-asset-path-gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = _service(tmp_path).upload_image(
        campaign_id=campaign_id,
        user_id=gm_id,
        filename="../nested/front face.png",
        content_type="image/png",
        data=_png_bytes(),
    )

    assert result.success, result.error_key
    row = JournalAssetRepository().get_by_id(result.asset_id or "")
    assert row is not None
    assert row["filename"] == "front-face.png"
    assert ".." not in row["storage_path"]
