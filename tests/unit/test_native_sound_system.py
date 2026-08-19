from app.engine.audio.sound_domain_service import SoundDomainService
from app.engine.assets.asset_library_service import AssetLibraryService
from app.engine.scenes.geometry_semantics import sound_attenuation
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.scene_wall_repository import SceneWallRepository
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


def test_sound_library_and_spatial_emitters_are_core_owned_with_cas(db, tmp_path):
    gm=seed_user(name="GM"); campaign=seed_campaign(gm); scene=seed_scene(campaign)
    audio=tmp_path/"rain.ogg"; audio.write_bytes(b"OggS"+b"x"*128)
    asset=AssetRepository().create(campaign_id=campaign,owner_user_id=gm,filename="rain.ogg",content_type="audio/ogg",byte_size=audio.stat().st_size,storage_path=str(audio),hash="test")
    service=SoundDomainService()
    sound=service.create_sound(campaign_id=campaign,user_id=gm,values={"name":"Rain","assetId":asset["id"],"kind":"sound-effect","defaultLoop":True})
    assert sound.success and sound.value["kind"]=="sound-effect"
    emitter=service.create_spatial(campaign_id=campaign,scene_id=scene["id"],user_id=gm,values={"soundId":sound.value["id"],"x":120,"y":80,"radius":350})
    assert emitter.success and emitter.value["scene_id"]==scene["id"]
    stale=service.mutate_spatial(campaign_id=campaign,user_id=gm,rid=emitter.value["id"],patch={"gain":.5},expected_version=999)
    assert not stale.success and stale.error_key=="sound.stale"
    blocked=service.delete_sound(campaign_id=campaign,user_id=gm,sound_id=sound.value["id"],expected_version=sound.value["version"])
    assert not blocked.success and blocked.error_key=="sound.in_use"
    ambient=service.create_sound(campaign_id=campaign,user_id=gm,values={"name":"Rain loop","assetId":asset["id"],"kind":"ambience","defaultLoop":True})
    started=service.play_ambient(campaign_id=campaign,user_id=gm,sound_id=ambient.value["id"]);assert started.success
    paused=service.pause_ambient(campaign_id=campaign,user_id=gm,sound_id=ambient.value["id"]);assert paused.success and paused.value["state"]=="paused"
    resumed=service.play_ambient(campaign_id=campaign,user_id=gm,sound_id=ambient.value["id"]);assert resumed.success and resumed.value["id"]==started.value["id"] and resumed.value["state"]=="playing"
    stopped=service.stop_ambient(campaign_id=campaign,user_id=gm,sound_id=ambient.value["id"]);assert stopped.success and stopped.value["state"]=="stopped"
    restarted=service.play_ambient(campaign_id=campaign,user_id=gm,sound_id=ambient.value["id"]);assert restarted.success and restarted.value["id"]==started.value["id"] and restarted.value["state"]=="playing"


def test_acoustic_channel_changes_gain_without_disclosing_geometry():
    base={"kind":"wall","door_state":"closed","x1":50,"y1":-20,"x2":50,"y2":20}
    ray=dict(origin=(0,0,0),target=(100,0,0))
    assert sound_attenuation(walls=[{**base,"sound_behavior":"pass"}],**ray)==1
    assert sound_attenuation(walls=[{**base,"sound_behavior":"attenuate"}],**ray)==.45
    assert sound_attenuation(walls=[{**base,"sound_behavior":"block"}],**ray)==0
    assert sound_attenuation(walls=[{**base,"kind":"door","door_state":"open","sound_behavior":"block"}],**ray)==1


def test_spatial_projection_uses_owned_token_range_falloff_and_optional_walls(db,tmp_path):
    gm=seed_user(name="GM");player=seed_user(name="Player");campaign=seed_campaign(gm);seed_member(campaign,player,"player");scene=seed_scene(campaign)
    audio=tmp_path/"fountain.ogg";audio.write_bytes(b"OggS"+b"x"*64)
    asset=AssetRepository().create(campaign_id=campaign,owner_user_id=gm,filename="fountain.ogg",content_type="audio/ogg",byte_size=audio.stat().st_size,storage_path=str(audio),hash="fountain")
    domain=SoundDomainService();sound=domain.create_sound(campaign_id=campaign,user_id=gm,values={"name":"Fountain","assetId":asset["id"],"kind":"sound-effect","defaultLoop":True})
    emitter=domain.create_spatial(campaign_id=campaign,scene_id=scene["id"],user_id=gm,values={"soundId":sound.value["id"],"x":105,"y":105,"radius":140,"falloff":"smooth","constrainedByWalls":True})
    token=TokenRepository().create(scene_id=scene["id"],actor_id=None,grid_x=1,grid_y=1,controlled_by_user_ids=[player])
    gm_token=TokenRepository().create(scene_id=scene["id"],actor_id=None,grid_x=1,grid_y=1,controlled_by_user_ids=[gm],controlled_by_role="gm")
    gm_projection=domain.acoustic_projection(campaign_id=campaign,scene_id=scene["id"],user_id=gm).value[0]
    assert not gm_projection["audible"] and gm_projection["projection"]==0 and gm_projection["listenerTokenId"] is None
    gm_preview=domain.acoustic_projection(campaign_id=campaign,scene_id=scene["id"],user_id=gm,preview_token_id=gm_token["id"]).value[0]
    assert gm_preview["audible"] and gm_preview["projection"]==1 and gm_preview["listenerTokenId"]==gm_token["id"]
    centered=domain.acoustic_projection(campaign_id=campaign,scene_id=scene["id"],user_id=player).value[0]
    assert centered["audible"] and centered["projection"]==1 and centered["listenerTokenId"]==token["id"]
    moved=TokenRepository().move(token_id=token["id"],grid_x=2,grid_y=1,expected_version=token["version"])
    halfway=domain.acoustic_projection(campaign_id=campaign,scene_id=scene["id"],user_id=player).value[0]
    assert halfway["projection"]==.5
    SceneWallRepository().create(campaign_id=campaign,scene_id=scene["id"],kind="wall",x1=140,y1=0,x2=140,y2=210,created_by_user_id=gm,sound_behavior="block")
    blocked=domain.acoustic_projection(campaign_id=campaign,scene_id=scene["id"],user_id=player).value[0]
    assert not blocked["audible"] and blocked["projection"]==0
    updated=domain.mutate_spatial(campaign_id=campaign,user_id=gm,rid=emitter.value["id"],patch={"constrainedByWalls":False},expected_version=emitter.value["version"])
    assert updated.success and updated.value["constrained_by_walls"] is False
    assert domain.acoustic_projection(campaign_id=campaign,scene_id=scene["id"],user_id=player).value[0]["projection"]==.5
    TokenRepository().move(token_id=token["id"],grid_x=5,grid_y=5,expected_version=moved["version"])
    outside=domain.acoustic_projection(campaign_id=campaign,scene_id=scene["id"],user_id=player).value[0]
    assert not outside["audible"] and outside["projection"]==0


def test_deleting_audio_asset_removes_unused_semantic_sound_without_fk_500(db,tmp_path):
    gm=seed_user(name="GM");campaign=seed_campaign(gm);audio=tmp_path/"unused.ogg";audio.write_bytes(b"OggS"+b"x"*32)
    asset=AssetRepository().create(campaign_id=campaign,owner_user_id=gm,filename="unused.ogg",content_type="audio/ogg",byte_size=audio.stat().st_size,storage_path=str(audio),hash="unused")
    sound=SoundDomainService().create_sound(campaign_id=campaign,user_id=gm,values={"name":"Unused","assetId":asset["id"],"kind":"ambience"})
    result=AssetLibraryService().delete_asset(campaign_id=campaign,user_id=gm,asset_id=asset["id"])
    assert result.success and AssetRepository().get_by_id(asset["id"]) is None
    assert SoundDomainService()._sound(campaign,sound.value["id"]) is None


def test_deleting_audio_asset_in_use_is_safe_conflict_and_preserves_asset(db,tmp_path):
    gm=seed_user(name="GM");campaign=seed_campaign(gm);scene=seed_scene(campaign);audio=tmp_path/"used.ogg";audio.write_bytes(b"OggS"+b"x"*32)
    asset=AssetRepository().create(campaign_id=campaign,owner_user_id=gm,filename="used.ogg",content_type="audio/ogg",byte_size=audio.stat().st_size,storage_path=str(audio),hash="used")
    domain=SoundDomainService();sound=domain.create_sound(campaign_id=campaign,user_id=gm,values={"name":"Used","assetId":asset["id"],"kind":"sound-effect"});domain.create_spatial(campaign_id=campaign,scene_id=scene["id"],user_id=gm,values={"soundId":sound.value["id"],"x":10,"y":10,"radius":20})
    result=AssetLibraryService().delete_asset(campaign_id=campaign,user_id=gm,asset_id=asset["id"])
    assert not result.success and result.error_key=="game.assets.errors.asset_in_use"
    assert AssetRepository().get_by_id(asset["id"]) is not None and audio.exists()


def test_artistic_layer_exposes_native_scene_sound_authoring():
    template=open("templates/pages/game/index.html",encoding="utf-8").read()
    script=open("static/js/audio/native-sound-ui.js",encoding="utf-8").read()
    runtime=open("static/js/audio/core-audio-runtime.js",encoding="utf-8").read()
    spatial=open("static/js/audio/spatial-sound-layer.js",encoding="utf-8").read()
    pixi=open("static/js/board/pixi/pixi-spatial-sound-layer.js",encoding="utf-8").read()
    assert 'data-active-layer="composition"' in template
    assert 'data-artistic-domain="images"' in template and 'data-artistic-domain="sounds"' in template
    assert all(f'data-artistic-domain="{name}"' not in template for name in ("lights","shaders","particles"))
    assert 'data-active-layer="effects"' in template
    assert 'data-active-layer="lighting"' in template
    assert 'data-open-sound-modal="ambient"' in template and 'data-open-sound-modal="effect"' in template
    assert "dataset.soundProductModal=type" in script and "game-modal-window native-sound-window" in script
    assert "data-place-spatial-sound" in script and 'data-tool="sound"' in template
    assert "worldFromScreen" in script and "/game/sounds/spatial" in script
    assert 'activeLayer!=="composition"' in script and 'tool:active-tool' in script
    assert 'querySelector(`[data-spatial-id="${CSS.escape(selected)}"] [data-spatial-delete]`)' not in script
    assert 'activeLayer === "composition"' in spatial and 'document.addEventListener("tool:active-layer", requestRender)' in spatial
    assert "artisticReference" in spatial and "snapshot?.artisticReference" in pixi
    assert "gfx.moveTo" in pixi and pixi.index("gfx.moveTo") < pixi.index("gfx.arc")
    assert "soundPropagationFor" in pixi and "gfx.poly(polygon)" in pixi
    assert "data-personal-audio-toggle" in template and "data-personal-audio-popover" in template
    assert 'data-mixer-channel="sfx"' in template and "setPersonalMixer" in script
    assert template.count('data-mixer-channel="')==3 and 'data-mixer-channel="music"' not in template
    assert 'data-mixer-linked-channel="music"' in template and "mixerLinkedChannel" in script
    assert 'Math.min(scalar,master())' in runtime
    assert 'if(storedPreference(child)>scalar)' in runtime
    assert 'input.max=channel==="master"?"1":String(master)' in script
    assert 'playing?"/game/sounds/pause":"/game/sounds/play"' in script and "ph-pause" in script
    assert "sound-mixer-rail" not in script.split("function renderNativeProductModal",1)[1]
