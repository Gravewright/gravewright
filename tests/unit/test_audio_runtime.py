import time
from app.engine.audio.audio_runtime_service import AudioRuntimeService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


def test_core_audio_play_idempotency_gain_and_stop(db, monkeypatch):
    gm=seed_user(); player=seed_user(); campaign=seed_campaign(gm); seed_member(campaign,player,"player"); scene=seed_scene(campaign)
    monkeypatch.setattr("app.engine.audio.audio_runtime_service.PackageAssetService.resolve",lambda self,pkg,path:(object(),"audio/ogg"))
    service=AudioRuntimeService(); values={"asset":{"kind":"package-asset","id":"audio/crypt.ogg"},"channel":"ambience","loop":True,"gain":.6,"audience":{"kind":"users","ids":[player]},"sceneId":scene["id"],"idempotencyKey":"crypt"}
    first=service.play(campaign_id=campaign,user_id=gm,package_id="haunt",values=values)
    again=service.play(campaign_id=campaign,user_id=gm,package_id="haunt",values=values)
    assert first.success and first.value["id"]==again.value["id"] and first.value["state"]=="pending-user-unlock"
    assert not service.update(campaign_id=campaign,user_id=gm,playback_id=first.value["id"],patch={"gain":float("nan")},expected_version=1).success
    stopping=service.stop(campaign_id=campaign,user_id=gm,playback_id=first.value["id"],fade={"durationMs":250,"curve":"linear"}).value
    assert stopping["state"]=="playing" and stopping["fade"]["direction"]=="out"
    time.sleep(1.05)
    assert service.get(campaign_id=campaign,user_id=gm,playback_id=first.value["id"]).value["state"]=="stopped"
