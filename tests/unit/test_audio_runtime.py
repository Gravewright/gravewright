import time
from app.engine.audio.audio_runtime_service import AudioRuntimeService
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


def test_confirming_playback_resets_the_timeline_anchor(db, monkeypatch):
    """A track blocked by the browser's autoplay policy must not appear to have
    already advanced (or finished) once the user actually unlocks it.

    ``started_at`` used to be fixed at creation time even while the playback sat
    in ``pending-user-unlock``. If the real unlock only happens well after
    creation, position-from-elapsed-time math on the client would skip ahead by
    that whole gap. The first confirmed transition to ``playing`` must reset the
    anchor so the timeline only starts counting once something is actually
    audible.
    """
    gm = seed_user()
    campaign = seed_campaign(gm)
    monkeypatch.setattr(
        "app.engine.audio.audio_runtime_service.PackageAssetService.resolve",
        lambda self, pkg, path: (object(), "audio/ogg"),
    )
    service = AudioRuntimeService()
    values = {
        "asset": {"kind": "package-asset", "id": "audio/crypt.ogg"},
        "channel": "ambience",
        "audience": {"kind": "self"},
    }
    created = service.play(campaign_id=campaign, user_id=gm, package_id="haunt", values=values)
    assert created.success and created.value["state"] == "pending-user-unlock"
    original_started_at = created.value["startedAt"]

    time.sleep(1.05)

    confirmed = service.update(
        campaign_id=campaign,
        user_id=gm,
        playback_id=created.value["id"],
        patch={"state": "playing"},
        expected_version=created.value["version"],
    )

    assert confirmed.success
    assert confirmed.value["state"] == "playing"
    assert confirmed.value["startedAt"] > original_started_at


def test_resuming_an_already_playing_track_keeps_the_timeline_anchor(db, monkeypatch):
    """Once playback is confirmed, further gain/state patches must not resync
    everyone else's already-progressing timeline."""
    gm = seed_user()
    campaign = seed_campaign(gm)
    monkeypatch.setattr(
        "app.engine.audio.audio_runtime_service.PackageAssetService.resolve",
        lambda self, pkg, path: (object(), "audio/ogg"),
    )
    service = AudioRuntimeService()
    values = {
        "asset": {"kind": "package-asset", "id": "audio/crypt.ogg"},
        "channel": "ambience",
        "audience": {"kind": "self"},
    }
    created = service.play(campaign_id=campaign, user_id=gm, package_id="haunt", values=values)
    confirmed = service.update(
        campaign_id=campaign,
        user_id=gm,
        playback_id=created.value["id"],
        patch={"state": "playing"},
        expected_version=created.value["version"],
    )
    playing_started_at = confirmed.value["startedAt"]

    time.sleep(1.05)

    paused = service.update(
        campaign_id=campaign,
        user_id=gm,
        playback_id=created.value["id"],
        patch={"state": "paused"},
        expected_version=confirmed.value["version"],
    )
    resumed = service.update(
        campaign_id=campaign,
        user_id=gm,
        playback_id=created.value["id"],
        patch={"state": "playing"},
        expected_version=paused.value["version"],
    )

    assert resumed.success
    assert resumed.value["startedAt"] == playing_started_at


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
