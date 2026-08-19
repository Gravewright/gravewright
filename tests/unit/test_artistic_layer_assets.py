import json
from pathlib import Path
from app.engine.assets.asset_library_service import AssetLibraryService
from app.engine.sheets.pdf_system_policy import is_pdf_sheet_system
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository
from tests.conftest import seed_campaign,seed_user
from tests.conftest import TEST_SESSION_CONFIG,login
from litestar.testing import TestClient
from main import app

ROOT=Path(__file__).resolve().parents[2]

def _install(user, manifest, package_id="ruleset"):
    InstalledPackageRepository().upsert(package_id=package_id,kind="ruleset",name="Ruleset",version="1",status="enabled",package_dir=f"rulesets/{package_id}",manifest_json=json.dumps(manifest),compatibility_status="compatible",validation_errors_json="[]",installed_by_user_id=user,last_validation_status="valid")

def test_pdf_sheet_detection_is_semantic_and_centralized(db):
    user=seed_user();base={"capabilities":["pdf.read","pdf.viewer"],"provides":{"mappings":{"pdfFields":"fields.json"}}}
    _install(user,base,"pdf-semantic");_install(user,{"capabilities":["pdf.viewer"],"provides":{}},"ordinary")
    assert is_pdf_sheet_system("pdf-semantic")
    assert not is_pdf_sheet_system("ordinary") and not is_pdf_sheet_system(None)

def test_audio_uses_the_canonical_asset_store(db,tmp_path):
    user=seed_user();campaign=seed_campaign(user);service=AssetLibraryService(storage=__import__("app.infrastructure.storage.local_asset_storage",fromlist=["LocalAssetStorage"]).LocalAssetStorage(root=tmp_path/"library"))
    result=service.upload_asset(campaign_id=campaign,user_id=user,filename="rain.ogg",content_type="audio/ogg",data=b"OggS"+b"x"*32)
    assert result.success,result.error_key
    assert result.payload["asset"]["content_type"]=="audio/ogg"
    from app.engine.audio.sound_domain_service import SoundDomainService
    asset_id=result.payload["asset"]["id"]
    sounds=SoundDomainService()
    ambient=sounds.create_sound(campaign_id=campaign,user_id=user,values={"name":"Rain ambience","assetId":asset_id,"kind":"ambience"})
    effect=sounds.create_sound(campaign_id=campaign,user_id=user,values={"name":"Rain effect","assetId":asset_id,"kind":"sound-effect"})
    assert ambient.success and effect.success
    assert ambient.value["asset_id"]==effect.value["asset_id"]==asset_id
    assert len(list((tmp_path/"library").rglob("*.ogg")))==1

def test_asset_state_exposes_the_uploaded_audio_purpose(db):
    user=seed_user();campaign=seed_campaign(user)
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,user)
        uploaded=client.post("/game/assets/upload",data={"campaign_id":campaign,"purpose":"effect"},files={"file":("thunder.ogg",b"OggS"+b"x"*32,"audio/ogg")})
        assert uploaded.status_code==201,uploaded.text
        state=client.get(f"/game/assets/state/{campaign}")
    assert state.status_code==200,state.text
    assert state.json()["assets"][0]["audio_kinds"]==["sound-effect"]

def test_assets_and_artistic_ui_expose_product_complete_controls():
    template=(ROOT/"templates/pages/game/index.html").read_text(encoding="utf-8")
    assert 'data-scene-asset-upload="ambient-audio"' in template
    assert 'data-scene-asset-upload="effect-audio"' in template
    script=(ROOT/"static/js/assets/asset-library.js").read_text(encoding="utf-8")
    assert '"ambient-audio"' in script and '"effect-audio"' in script
    assert "{% if room.uses_pdf_sheet_system %}" in template
    assert 'data-artistic-domain="images"' in template and "data-asset-place-scene" in script

def test_touched_product_strings_have_three_locale_variants():
    from app.i18n.en import CATALOG as en
    from app.i18n.pt_br import CATALOG as pt
    from app.i18n.es import CATALOG as es
    keys=[key for key in en if key.startswith(("game.sound.","game.assets.")) and key in {**es}]
    assert keys and all(key in pt and key in es for key in keys)
    for key in ("game.sound.activate","game.sound.empty_spatial","game.sound.empty_ambient","game.sound.empty_library","game.sound.search_ambient","game.sound.no_ambient_match","game.assets.upload_audio","game.assets.kind_audio","game.assets.place_scene"):
        assert key in en and key in pt and key in es

def test_pdf_sheet_upload_purpose_is_rejected_without_pdf_system(db):
    user=seed_user();campaign=seed_campaign(user)
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,user);response=client.post("/game/assets/upload",data={"campaign_id":campaign,"purpose":"pdf-sheet"},files={"file":("sheet.pdf",b"%PDF-1.4\n%%EOF","application/pdf")})
    assert response.status_code==403 and response.json()["error_key"]=="game.assets.errors.pdf_system_required"

def test_pdf_sheet_upload_purpose_is_allowed_for_semantic_pdf_system(db):
    from app.persistence.repositories.campaign_repository import CampaignRepository
    user=seed_user();campaign=seed_campaign(user);manifest={"capabilities":["pdf.read","pdf.viewer"],"provides":{"mappings":{"pdfFields":"fields.json"}}};_install(user,manifest,"pdf-semantic");CampaignRepository().update_system(campaign_id=campaign,changed_by_user_id=user,next_system_id="pdf-semantic")
    with TestClient(app=app,session_config=TEST_SESSION_CONFIG) as client:
        login(client,user);response=client.post("/game/assets/upload",data={"campaign_id":campaign,"purpose":"pdf-sheet"},files={"file":("sheet.pdf",b"%PDF-1.4\n%%EOF","application/pdf")})
    assert response.status_code==201,response.text

def test_game_context_recomputes_pdf_sheet_visibility_on_ruleset_change(db):
    from app.business.game_page_service import GamePageService
    from app.persistence.repositories.campaign_repository import CampaignRepository
    user=seed_user();campaign=seed_campaign(user);manifest={"capabilities":["pdf.read","pdf.viewer"],"provides":{"mappings":{"pdfFields":"fields.json"}}};_install(user,manifest,"pdf-semantic")
    service=GamePageService();systemless=next(room for room in service.build_context(user_id=user).rooms if room["id"]==campaign);assert not systemless["uses_pdf_sheet_system"]
    CampaignRepository().update_system(campaign_id=campaign,changed_by_user_id=user,next_system_id="pdf-semantic");pdf=next(room for room in service.build_context(user_id=user).rooms if room["id"]==campaign);assert pdf["uses_pdf_sheet_system"]
    CampaignRepository().update_system(campaign_id=campaign,changed_by_user_id=user,next_system_id=None);normal=next(room for room in service.build_context(user_id=user).rooms if room["id"]==campaign);assert not normal["uses_pdf_sheet_system"]
