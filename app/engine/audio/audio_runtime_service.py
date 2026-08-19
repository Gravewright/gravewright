"""Authoritative semantic audio playback lifecycle.

Browser audio engines are projections of this state.  Packages never own this
runtime and never receive WebAudio or HTMLAudio primitives.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Any

from app.engine.sdk.package_asset_service import PackageAssetService
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.audio_playback_repository import AudioPlaybackRepository
from app.engine.scenes.scene_object_service import SceneObjectService
from app.engine.tokens.token_service import TokenService


@dataclass(frozen=True)
class AudioResult:
    success: bool
    value: Any = None
    error_key: str | None = None


class AudioRuntimeService:
    """Core-owned playback state shared by native UX and SDK adapters."""

    CHANNELS = {"music", "ambience", "sfx", "cinematic"}
    STATES = {"pending-user-unlock", "playing", "paused", "stopped", "failed"}
    MAX_FADE_MS = 60_000

    def __init__(self) -> None:
        self.repo = AudioPlaybackRepository()

    def _audience(self, campaign_id: str, principal: str, value: Any) -> dict:
        if not isinstance(value, dict) or value.get("kind") not in {"self", "users", "campaign", "gm"}: raise ValueError
        members = CampaignRepository().list_members(campaign_id=campaign_id); ids = {row["user_id"] for row in members}
        role = CampaignRepository().get_member_role(campaign_id=campaign_id, user_id=principal)
        kind = value["kind"]
        selected = [principal] if kind == "self" else ([m["user_id"] for m in members if m.get("role") in {"gm", "assistant_gm"}] if kind == "gm" else (list(ids) if kind == "campaign" else list(dict.fromkeys(value.get("ids", [])))))
        if len(selected) > 64 or any(user not in ids for user in selected) or (set(selected) != {principal} and role not in {"gm", "assistant_gm"}): raise PermissionError
        return {"kind": kind, "ids": selected}

    @staticmethod
    def _fade(value: Any) -> dict | None:
        if value is None: return None
        if not isinstance(value, dict) or set(value) - {"durationMs", "curve"}: raise ValueError
        duration = int(value.get("durationMs", 0)); curve = value.get("curve", "linear")
        if not 0 <= duration <= AudioRuntimeService.MAX_FADE_MS or curve not in {"linear", "ease-in", "ease-out"}: raise ValueError
        return {"durationMs": duration, "curve": curve}

    @staticmethod
    def _asset(campaign_id: str, package_id: str, value: Any) -> dict:
        if not isinstance(value, dict) or set(value) != {"kind", "id"} or value.get("kind") not in {"library-asset", "package-asset"}: raise ValueError
        identity = str(value.get("id") or "")
        if value["kind"] == "package-asset":
            resolved = PackageAssetService().resolve(package_id, identity)
            if not resolved or not str(resolved[1]).startswith("audio/"): raise ValueError
        else:
            asset = AssetRepository().get_by_id(identity)
            if not asset or asset.get("campaign_id") != campaign_id or not str(asset.get("content_type") or "").startswith("audio/"): raise ValueError
        return {"kind": value["kind"], "id": identity}

    def play(self, *, campaign_id: str, user_id: str, package_id: str, values: dict) -> AudioResult:
        try:
            asset = self._asset(campaign_id, package_id, values.get("asset")); channel = values.get("channel", "sfx")
            gain = float(values.get("gain", 1)); audience = self._audience(campaign_id, user_id, values.get("audience", {"kind": "self"}))
            if channel not in self.CHANNELS or not math.isfinite(gain) or not 0 <= gain <= 1: raise ValueError
            scene_id = values.get("sceneId")
            if scene_id:
                scene = SceneRepository().get_by_id(str(scene_id))
                if not scene or scene.get("campaign_id") != campaign_id: raise ValueError
            key = values.get("idempotencyKey")
            if key:
                if not isinstance(key, str) or len(key) > 191: raise ValueError
                existing = self.repo.by_key(campaign_id, package_id, key)
                if existing: return AudioResult(True, self._public(existing))
            loop = bool(values.get("loop", False)); duration = values.get("durationMs")
            expires = None if loop or duration is None else int(time.time()) + max(1, min(int(duration), 3_600_000)) // 1000
            anchor = values.get("worldAnchor")
            if anchor is not None and (not isinstance(anchor, dict) or anchor.get("kind") not in {"token", "scene-object"} or not isinstance(anchor.get("id"), str)): raise ValueError
            if anchor and anchor["kind"]=="scene-object":
                found=SceneObjectService().get(campaign_id=campaign_id,object_id=anchor["id"],user_id=user_id)
                if not found.success:raise PermissionError
                anchor={"kind":"scene-object","id":anchor["id"],"sceneId":found.value["sceneId"]}
            elif anchor:
                anchor_scene=str(anchor.get("sceneId") or scene_id or "")
                snapshot=TokenService().get_snapshot(campaign_id=campaign_id,scene_id=anchor_scene,user_id=user_id)
                if not any(str(token.get("id") or token.get("token_id"))==anchor["id"] for token in snapshot.tokens or []):raise PermissionError
                anchor={"kind":"token","id":anchor["id"],"sceneId":anchor_scene}
            now_ms=int(time.time()*1000); fade=self._fade(values.get("fade"))
            if fade: fade.update(direction="in",startedAt=now_ms,fromGain=0.0)
            row = self.repo.create({"campaign_id":campaign_id,"package_id":package_id,"owner_user_id":user_id,"asset_json":json.dumps(asset),"channel":channel,"state":"pending-user-unlock","loop":int(loop),"gain":gain,"audience_json":json.dumps(audience),"scene_id":scene_id,"anchor_json":json.dumps(anchor) if anchor else None,"idempotency_key":key,"started_at":int(time.time()),"expires_at":expires,"fade_json":json.dumps(fade) if fade else None})
            return AudioResult(True, self._public(row))
        except PermissionError: return AudioResult(False, error_key="sdk.audio.not_authorized")
        except (TypeError, ValueError, OverflowError): return AudioResult(False, error_key="sdk.audio.invalid_playback")

    def get(self, *, campaign_id: str, user_id: str, playback_id: str) -> AudioResult:
        row=self.repo.get(playback_id)
        if row and row.get("expires_at") and row["expires_at"]<=int(time.time()) and row["state"]!="stopped":row=self.repo.patch(playback_id,None,{"state":"stopped","fade_json":None})
        if not row or row["campaign_id"]!=campaign_id or user_id not in row["audience"]["ids"] and row["owner_user_id"]!=user_id:return AudioResult(False,error_key="sdk.audio.not_found")
        return AudioResult(True,self._public(row))

    def list(self, *, campaign_id: str, user_id: str, package_id: str | None = None, scene_id: str | None = None) -> AudioResult:
        now=int(time.time()); result=[]
        for row in self.repo.list(campaign_id):
            if row.get("expires_at") and row["expires_at"]<=now: self.repo.patch(row["id"],None,{"state":"stopped"}); row["state"]="stopped"
            if user_id not in row["audience"]["ids"] and row["owner_user_id"]!=user_id: continue
            if package_id and row["package_id"]!=package_id or scene_id and row.get("scene_id") not in {None,scene_id}:continue
            result.append(self._public(row))
        return AudioResult(True,result)

    def update(self, *, campaign_id: str, user_id: str, playback_id: str, patch: dict, expected_version: int | None) -> AudioResult:
        row=self.repo.get(playback_id)
        if not row or row["campaign_id"]!=campaign_id:return AudioResult(False,error_key="sdk.audio.not_found")
        if row["owner_user_id"]!=user_id:return AudioResult(False,error_key="sdk.audio.not_authorized")
        try:
            if set(patch)-{"gain","state","loop","fade"}:raise ValueError
            values={}
            if "gain" in patch:
                gain=float(patch["gain"])
                if not math.isfinite(gain) or not 0<=gain<=1:raise ValueError
                values["gain"]=gain
            if "state" in patch:
                if patch["state"] not in {"playing","paused"}:raise ValueError
                values["state"]=patch["state"]
                values["expires_at"]=None
            if "loop" in patch:values["loop"]=int(bool(patch["loop"]))
            if "fade" in patch:
                fade=self._fade(patch["fade"])
                if fade:fade.update(direction="in",startedAt=int(time.time()*1000),fromGain=row["gain"])
                values["fade_json"]=json.dumps(fade) if fade else None
        except (TypeError,ValueError,OverflowError):return AudioResult(False,error_key="sdk.audio.invalid_patch")
        updated=self.repo.patch(playback_id,expected_version,values)
        return AudioResult(bool(updated),self._public(updated) if updated else None,None if updated else "sdk.audio.stale_version")

    def stop(self, *, campaign_id: str, user_id: str, playback_id: str, fade: Any = None, expected_version: int | None = None) -> AudioResult:
        row=self.repo.get(playback_id)
        if not row or row["campaign_id"]!=campaign_id:return AudioResult(True,{"id":playback_id,"state":"stopped"})
        if row["owner_user_id"]!=user_id:return AudioResult(False,error_key="sdk.audio.not_authorized")
        try:
            spec=self._fade(fade)
            if spec and spec["durationMs"]:
                spec.update(direction="out",startedAt=int(time.time()*1000),fromGain=row["gain"])
                values={"state":"playing","fade_json":json.dumps(spec),"expires_at":int(time.time())+max(1,(spec["durationMs"]+999)//1000)}
            else:values={"state":"stopped","fade_json":None,"expires_at":int(time.time())}
        except (TypeError,ValueError):return AudioResult(False,error_key="sdk.audio.invalid_fade")
        updated=self.repo.patch(playback_id,expected_version,values)
        return AudioResult(bool(updated),self._public(updated) if updated else None,None if updated else "sdk.audio.stale_version")

    def stop_package(self, *, campaign_id: str, package_id: str) -> None: self.repo.stop_package(campaign_id, package_id)

    @staticmethod
    def _public(row: dict | None) -> dict | None:
        if not row:return None
        return {"id":row["id"],"asset":row["asset"],"channel":row["channel"],"state":row["state"],"loop":bool(row["loop"]),"gain":row["gain"],"audience":row["audience"],"sceneId":row.get("scene_id"),"worldAnchor":row.get("worldAnchor"),"startedAt":row["started_at"],"updatedAt":row["updated_at"]*1000,"expiresAt":row.get("expires_at"),"fade":row.get("fade"),"version":row["version"],"ownerPackageId":row["package_id"]}
