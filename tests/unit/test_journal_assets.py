from __future__ import annotations

import io

from litestar.testing import TestClient
from PIL import Image

from app.domain.roles import PlayerRole
from app.engine.journals.journal_asset_service import JournalAssetService
from app.engine.journals.journal_service import JournalService
from app.infrastructure.storage.local_journal_asset_storage import LocalJournalAssetStorage
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user


def _png_bytes(width: int = 12, height: int = 8) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 80, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def _journal(
    campaign_id: str,
    gm_id: str,
    *,
    title: str = "Asset Journal",
    owner_user_ids: list[str] | None = None,
) -> str:
    result = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title=title,
        visibility="private",
        owner_user_ids=owner_user_ids,
    )
    assert result.success
    assert result.journal_id
    return result.journal_id


def test_upload_valid_png(db, tmp_path):
    gm = seed_user(name="GM", email="gm-asset1@test.com")
    campaign_id = seed_campaign(gm)
    journal_id = _journal(campaign_id, gm)
    service = JournalAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "ja"))

    result = service.upload_image(
        journal_id=journal_id,
        user_id=gm,
        filename="cover.png",
        content_type="image/png",
        data=_png_bytes(),
    )

    assert result.success
    assert result.src == f"/game/journal/asset/{result.asset_id}"
    assert result.width == 12 and result.height == 8


def test_upload_valid_pdf_page(db, tmp_path):
    gm = seed_user(name="GM", email="gm-asset-pdf@test.com")
    campaign_id = seed_campaign(gm)
    journal_id = _journal(campaign_id, gm)
    service = JournalAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "ja"))

    result = service.upload_image(
        journal_id=journal_id,
        user_id=gm,
        filename="handout.pdf",
        content_type="application/pdf",
        data=b"%PDF-1.7\n%%EOF",
        purpose="journal_pdf",
    )

    assert result.success
    assert result.src == f"/game/journal/asset/{result.asset_id}"
    assert result.width is None and result.height is None


def test_journal_pdf_cap_is_larger_than_image_cap(db, tmp_path):
    from app.engine.journals.journal_asset_service import MAX_PDF_BYTES, MAX_UPLOAD_BYTES

    gm = seed_user(name="GM", email="gm-large-journal-pdf@test.com")
    campaign_id = seed_campaign(gm)
    journal_id = _journal(campaign_id, gm)
    service = JournalAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "ja"))
    data = b"%PDF-1.7\n" + b"0" * (MAX_UPLOAD_BYTES + 1)

    result = service.upload_image(
        journal_id=journal_id, user_id=gm, filename="large.pdf",
        content_type="application/pdf", data=data, purpose="journal_pdf",
    )

    assert MAX_PDF_BYTES > MAX_UPLOAD_BYTES
    assert result.success


def test_journal_upload_route_has_multipart_headroom_above_pdf_cap():
    import main
    from app.engine.journals.journal_asset_service import MAX_PDF_BYTES

    limits = [
        handler.request_max_body_size
        for route in main.app.routes
        if route.path == "/game/journal/asset"
        for handler in route.route_handlers
        if isinstance(getattr(handler, "request_max_body_size", None), int)
    ]
    assert limits and max(limits) > MAX_PDF_BYTES


def test_journal_client_checks_file_size_and_reports_413():
    from pathlib import Path

    script = (Path(__file__).resolve().parents[2] / "static/js/journals/journal-editor.js").read_text(
        encoding="utf-8"
    )
    assert "dataset?.journalPdfMaxBytes" in script
    assert "dataset?.journalImageMaxBytes" in script
    assert "file.size > cap" in script
    assert "res.status === 413" in script


def test_diary_pdf_section_keeps_semantic_document_identity():
    from app.engine.journals.journal_data import normalize_diary_data

    normalized = normalize_diary_data({"sections": [{
        "kind": "pdf", "title": "Handout", "src": "/game/journal/asset/document_123",
    }]})

    section = normalized["sections"][0]
    assert section["assetId"] == "document_123"
    assert section["src"] == "/game/journal/asset/document_123"
    assert "storage" not in section["src"]


def test_upload_rejects_unsupported_type(db, tmp_path):
    gm = seed_user(name="GM", email="gm-asset2@test.com")
    campaign_id = seed_campaign(gm)
    journal_id = _journal(campaign_id, gm)
    service = JournalAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "ja"))

    result = service.upload_image(
        journal_id=journal_id,
        user_id=gm,
        filename="evil.gif",
        content_type="image/gif",
        data=b"GIF89a....",
    )

    assert not result.success
    assert result.error_key == "game.journal.assets.errors.unsupported_type"


def test_upload_rejects_non_member(db, tmp_path):
    gm = seed_user(name="GM", email="gm-asset3@test.com")
    outsider = seed_user(name="Out", email="out-asset3@test.com")
    campaign_id = seed_campaign(gm)
    journal_id = _journal(campaign_id, gm)
    service = JournalAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "ja"))

    result = service.upload_image(
        journal_id=journal_id,
        user_id=outsider,
        filename="a.png",
        content_type="image/png",
        data=_png_bytes(),
    )

    assert not result.success


def test_upload_and_serve_route_is_membership_gated(db, tmp_path, monkeypatch):

    import app.actions.game.manage_journals as mj
    import app.infrastructure.storage.local_journal_asset_storage as stormod

    monkeypatch.setattr(stormod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mj, "PROJECT_ROOT", tmp_path)

    from main import app

    gm = seed_user(name="GM", email="gm-asset4@test.com")
    player = seed_user(name="P", email="p-asset4@test.com")
    outsider = seed_user(name="X", email="x-asset4@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, PlayerRole.PLAYER.value)
    journal_id = _journal(campaign_id, gm)
    assert (
        JournalService()
        .set_member_access(
            journal_id=journal_id, target_user_id=player, access_level="read", requester_user_id=gm
        )
        .success
    )

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        upload = client.post(
            "/game/journal/asset",
            files={"file": ("cover.png", _png_bytes(), "image/png")},
            data={"journal_id": journal_id},
        )
        assert upload.status_code == 201
        src = upload.json()["src"]
        assert src.startswith("/game/journal/asset/")

        assert client.get(src).status_code == 200
        client.set_session_data({"user_id": player})
        assert client.get(src).status_code == 200
        client.set_session_data({"user_id": outsider})
        assert client.get(src).status_code in (401, 403)
        client.set_session_data({"user_id": gm})
        assert client.get("/game/journal/asset/does-not-exist").status_code == 404


def test_pdf_document_resolution_uses_existing_visibility_policy(db, tmp_path, monkeypatch):
    import app.actions.game.manage_journals as mj
    import app.infrastructure.storage.local_journal_asset_storage as stormod

    monkeypatch.setattr(stormod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mj, "PROJECT_ROOT", tmp_path)
    from main import app

    gm = seed_user(name="GM", email="gm-pdf-viewer@test.com")
    reader = seed_user(name="Reader", email="reader-pdf-viewer@test.com")
    outsider = seed_user(name="Out", email="out-pdf-viewer@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, reader, PlayerRole.PLAYER.value)
    journal_id = _journal(campaign_id, gm)
    assert JournalService().set_member_access(
        journal_id=journal_id, target_user_id=reader, access_level="read", requester_user_id=gm,
    ).success

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        uploaded = client.post(
            "/game/journal/asset",
            files={"file": ("handout.pdf", b"%PDF-1.7\n%%EOF", "application/pdf")},
            data={"journal_id": journal_id, "purpose": "journal_pdf"},
        )
        assert uploaded.status_code == 201
        asset_id = uploaded.json()["asset_id"]
        endpoint = f"/game/journal/pdf/{asset_id}"
        document = client.get(endpoint)
        assert document.status_code == 200
        assert document.json()["document"]["id"] == asset_id
        assert document.json()["document"]["url"] == f"/game/journal/asset/{asset_id}"

        client.set_session_data({"user_id": reader})
        assert client.get(endpoint).status_code == 200
        client.set_session_data({"user_id": outsider})
        assert client.get(endpoint).status_code in (401, 403)
        assert client.get(f"/game/journal/asset/{asset_id}").status_code in (401, 403)


def test_owner_can_upload_but_read_user_cannot(db, tmp_path):
    gm = seed_user(name="GM", email="gm-asset5@test.com")
    owner = seed_user(name="Owner", email="owner-asset5@test.com")
    reader = seed_user(name="Reader", email="reader-asset5@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, owner, PlayerRole.PLAYER.value)
    seed_member(campaign_id, reader, PlayerRole.PLAYER.value)
    journal_id = _journal(campaign_id, gm, owner_user_ids=[owner])
    assert (
        JournalService()
        .set_member_access(
            journal_id=journal_id, target_user_id=reader, access_level="read", requester_user_id=gm
        )
        .success
    )

    service = JournalAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "ja"))
    owner_upload = service.upload_image(
        journal_id=journal_id,
        user_id=owner,
        filename="owner.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    reader_upload = service.upload_image(
        journal_id=journal_id,
        user_id=reader,
        filename="reader.png",
        content_type="image/png",
        data=_png_bytes(),
    )

    assert owner_upload.success
    assert not reader_upload.success
    assert reader_upload.error_key == "game.journal.errors.not_owner"


def test_upload_rejects_missing_journal(db, tmp_path):
    gm = seed_user(name="GM", email="gm-asset6@test.com")
    service = JournalAssetService(storage=LocalJournalAssetStorage(root=tmp_path / "ja"))

    result = service.upload_image(
        journal_id="missing",
        user_id=gm,
        filename="a.png",
        content_type="image/png",
        data=_png_bytes(),
    )

    assert not result.success
    assert result.error_key == "game.journal.errors.not_found"
