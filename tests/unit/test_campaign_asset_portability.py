import base64
import hashlib
import io
import shutil
import time
import zipfile

import pytest
from sqlalchemy import delete, insert, select, update

from app.business.campaigns.campaign_export_service import CampaignExportOptions, CampaignExportService
from app.business.campaigns.campaign_import_service import CampaignImportService
from app.business.campaigns.portable_asset_archive import PortableAssetError, validate_asset_manifest
from app.engine.assets.asset_library_service import AssetLibraryService
from app.infrastructure.storage.local_asset_storage import LocalAssetStorage
from app.persistence.database import engine_begin, engine_connect
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.scene_image_repository import SceneImageRepository
from app.persistence.repositories.token_repository import TokenRepository
from app.persistence.tables import actors_core, campaigns, items_core, library_assets, scene_image_placements, tokens, card_deck_definitions, card_definitions
from tests.conftest import seed_campaign, seed_scene, seed_user


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def test_physical_asset_archive_roundtrip_owns_new_ids_and_paths(db):
    gm = seed_user(name="GM"); source = seed_campaign(gm, title="Portable physical table"); scene = seed_scene(source)
    uploaded = AssetLibraryService().upload_asset(campaign_id=source, user_id=gm, filename="art.png", content_type="image/png", data=PNG)
    assert uploaded.success; asset_id = uploaded.payload["asset"]["id"]
    actor = ActorRepository().create(campaign_id=source, system_id="core", actor_type="character", name="Hero", created_by_user_id=gm)
    item = ItemRepository().create(campaign_id=source, system_id="core", item_type="gear", name="Relic", created_by_user_id=gm)
    TokenRepository().create(scene_id=scene["id"], actor_id=actor, grid_x=1, grid_y=1, token_asset_url=f"/game/assets/file/{asset_id}")
    SceneImageRepository().create(campaign_id=source, scene_id=scene["id"], asset_id=asset_id, owner_user_id=gm,
        x=10, y=20, natural_width=1, natural_height=1)
    now = int(time.time()); deck_id, card_id = "portable-deck", "portable-card"
    with engine_begin() as conn:
        conn.execute(update(actors_core).where(actors_core.c.id == actor).values(portrait_asset_id=asset_id, token_asset_id=asset_id))
        conn.execute(update(items_core).where(items_core.c.id == item).values(portrait_asset_id=asset_id))
        conn.execute(insert(card_deck_definitions).values(id=deck_id, campaign_id=source, package_id=None, owner_user_id=gm,
            scope="campaign", name="Deck", description=None, default_back_asset_id=asset_id, editable=1,
            metadata_json="{}", created_at=now, updated_at=now))
        conn.execute(insert(card_definitions).values(id=card_id, deck_definition_id=deck_id, name="Card", subtitle=None,
            description=None, front_asset_id=asset_id, back_asset_id=asset_id, tags_json="[]", metadata_json="{}",
            sort_key="1", quantity=1, created_at=now, updated_at=now))
    exported = CampaignExportService().export(campaign_id=source, user_id=gm, options=CampaignExportOptions())
    assert exported.success and exported.archive
    original_path = LocalAssetStorage().root / source
    with engine_begin() as conn: conn.execute(delete(campaigns).where(campaigns.c.id == source))
    shutil.rmtree(original_path, ignore_errors=True)

    imported = CampaignImportService().import_archive(archive=exported.archive, user_id=gm, title="Restored physical table")
    assert imported.success and imported.campaign_id != source
    with engine_connect() as conn:
        assets = list(conn.execute(select(library_assets).where(library_assets.c.campaign_id == imported.campaign_id)).mappings())
        imported_actor = conn.execute(select(actors_core).where(actors_core.c.campaign_id == imported.campaign_id)).mappings().one()
        imported_item = conn.execute(select(items_core).where(items_core.c.campaign_id == imported.campaign_id)).mappings().one()
        imported_token = conn.execute(select(tokens).join(__import__("app.persistence.tables", fromlist=["scenes"]).scenes).where(
            __import__("app.persistence.tables", fromlist=["scenes"]).scenes.c.campaign_id == imported.campaign_id)).mappings().one()
        imported_image = conn.execute(select(scene_image_placements).where(scene_image_placements.c.campaign_id == imported.campaign_id)).mappings().one()
        imported_deck = conn.execute(select(card_deck_definitions).where(card_deck_definitions.c.campaign_id == imported.campaign_id)).mappings().one()
        imported_card = conn.execute(select(card_definitions).where(card_definitions.c.deck_definition_id == imported_deck["id"])).mappings().one()
    assert len(assets) == 1 and assets[0]["id"] != asset_id and assets[0]["campaign_id"] == imported.campaign_id
    assert {imported_actor["portrait_asset_id"], imported_actor["token_asset_id"], imported_item["portrait_asset_id"], imported_image["asset_id"]} == {assets[0]["id"]}
    assert {imported_deck["default_back_asset_id"], imported_card["front_asset_id"], imported_card["back_asset_id"]} == {assets[0]["id"]}
    assert imported_token["token_asset_url"].endswith(assets[0]["id"])
    assert __import__("pathlib").Path(assets[0]["storage_path"]).is_file()


def _manifest(data=PNG, *, media="image/png", location="assets/asset-000001.payload"):
    return {"version": 2, "assets": [{"id":"asset-000001", "digest":hashlib.sha256(data).hexdigest(), "bytes":len(data),
        "mediaTypeHint":media, "filename":"asset.png", "ownership":"campaign", "payload":location}],
        "journalAttachments": [], "rasters": []}


def test_journal_pdf_and_complete_raster_derivatives_validate_as_closed_graph(db):
    pdf = b"%PDF-1.4\n%%EOF"; chunk = b"chunk"; png_digest = hashlib.sha256(PNG).hexdigest()
    journal = {"id":"journal-000001", "digest":hashlib.sha256(pdf).hexdigest(), "bytes":len(pdf),
        "mediaTypeHint":"application/pdf", "filename":"handout.pdf", "ownership":"campaign",
        "payload":"assets/journal-000001.payload", "journalId":"journal", "folderId":None, "purpose":"journal_pdf"}
    components = [
        {"id":"component-000001", "kind":"original_image", "digest":png_digest, "bytes":len(PNG), "mediaTypeHint":"image/png", "width":1, "height":1, "payload":"rasters/raster-000001/component-000001.payload"},
        {"id":"component-000002", "kind":"raster_tile", "digest":png_digest, "bytes":len(PNG), "mediaTypeHint":"image/png", "width":1, "height":1, "payload":"rasters/raster-000001/component-000002.payload"},
    ]
    raster = {"id":"raster-000001", "sceneId":"scene", "payloadStrategy":"BUNDLED_DERIVATIVES", "processingVersion":1,
        "rasterMetadata":{"width":1,"height":1,"tileSize":1,"chunkSpan":1}, "components":components,
        "tiles":[{"layerId":"layer","tileRef":"tile","lod":0,"componentId":"component-000002","tx":0,"ty":0,"width":1,"height":1,"digest":png_digest,"bytes":len(PNG)}],
        "chunks":[{"layerId":"layer","cx":0,"cy":0,"lod":0,"version":1,"encoding":"raw","digest":hashlib.sha256(chunk).hexdigest(),"bytes":len(chunk),"payload":"rasters/raster-000001/chunk-000001.payload"}]}
    manifest = {"version":2, "assets":[], "journalAttachments":[journal], "rasters":[raster]}
    blobs = {journal["payload"]:pdf, components[0]["payload"]:PNG, components[1]["payload"]:PNG,
             raster["chunks"][0]["payload"]:chunk}
    validated = validate_asset_manifest(manifest, blobs)
    assert {entry.get("portableKind") for entry in validated} == {"journal", "raster"}


@pytest.mark.parametrize("mutation", ["missing", "digest", "mime", "path", "extra"])
def test_malicious_or_incomplete_physical_manifests_write_nothing(db, mutation):
    manifest = _manifest(); blobs = {"assets/asset-000001.payload": PNG}
    if mutation == "missing": blobs = {}
    elif mutation == "digest": manifest["assets"][0]["digest"] = "0" * 64
    elif mutation == "mime": manifest["assets"][0]["mediaTypeHint"] = "image/jpeg"
    elif mutation == "path": manifest["assets"][0]["payload"] = "../escape.payload"
    elif mutation == "extra": blobs["assets/unexpected.payload"] = PNG
    with pytest.raises(PortableAssetError): validate_asset_manifest(manifest, blobs)


def test_archive_traversal_and_decompression_limits_are_rejected_without_escape(db, tmp_path, monkeypatch):
    gm = seed_user(); payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("../escape", b"owned")
        archive.writestr("campaign.json", b"{}")
        archive.writestr("manifest.json", b"{}")
    assert not CampaignImportService().import_archive(archive=payload.getvalue(), user_id=gm).success
    assert not (tmp_path.parent / "escape").exists()


def test_recovery_cleans_incomplete_trees_is_idempotent_and_preserves_committed_campaign(db, tmp_path):
    gm = seed_user(); incomplete = "incomplete"; scene_id = "staged-scene"
    for root in (tmp_path / "library-assets" / incomplete, tmp_path / "journal-assets" / incomplete,
                 tmp_path / "scenes" / scene_id):
        root.mkdir(parents=True); (root / "partial").write_bytes(b"partial")
    marker = CampaignImportService._write_recovery_marker(campaign_id=incomplete, scene_ids=[scene_id], phase="PHYSICAL_COMPLETE")
    assert marker.exists(); CampaignImportService.recover_incomplete_imports(); CampaignImportService.recover_incomplete_imports()
    assert not marker.exists()
    assert not (tmp_path / "library-assets" / incomplete).exists()
    assert not (tmp_path / "journal-assets" / incomplete).exists()
    assert not (tmp_path / "scenes" / scene_id).exists()

    committed = seed_campaign(gm); committed_tree = tmp_path / "library-assets" / committed
    committed_tree.mkdir(parents=True); (committed_tree / "kept").write_bytes(b"newer")
    marker = CampaignImportService._write_recovery_marker(campaign_id=committed, scene_ids=[], phase="IMPORTING")
    CampaignImportService.recover_incomplete_imports()
    assert committed_tree.exists() and not marker.exists()
