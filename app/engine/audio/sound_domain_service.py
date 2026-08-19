"""First-class native Sound library, compositions and Scene emitters."""
from __future__ import annotations
import json,math,time,uuid
from dataclasses import dataclass
from sqlalchemy import delete,func,insert,or_,select,update
from app.domain.roles import has_full_view
from app.persistence.database import all_dicts,engine_begin
from app.persistence.tables import library_assets,scene_spatial_sounds,scenes,sound_playlists,sounds,soundscapes
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.token_repository import TokenRepository
from app.engine.audio.audio_runtime_service import AudioRuntimeService
from app.engine.scenes.geometry_semantics import sound_attenuation
from app.persistence.repositories.scene_wall_repository import SceneWallRepository

@dataclass(frozen=True)
class SoundResult: success:bool;value:object=None;error_key:str|None=None

class SoundDomainService:
    KINDS={"sound-effect","music","ambience"};MODES={"sequential","shuffle","repeat-one","repeat-all","stop-at-end"};FALLOFF={"linear","smooth"}
    MAX_SPATIAL_RADIUS=100000.0
    def _manage(self,c,u):return has_full_view(CampaignRepository().get_member_role(campaign_id=c,user_id=u))
    @staticmethod
    def _json(value):return json.dumps(value,ensure_ascii=False,separators=(",",":"),allow_nan=False)
    @staticmethod
    def _decode(row):
        if not row:return None
        v=dict(row)
        for source,target in (("tags_json","tags"),("metadata_json","metadata"),("entries_json","entries"),("layers_json","layers"),("random_pools_json","randomPools"),("audience_json","audience")):
            if source in v:v[target]=json.loads(v.pop(source) or "[]")
        for key in ("default_loop","loop","enabled","constrained_by_walls"):
            if key in v:v[key]=bool(v[key])
        return v
    def _sound(self,c,sid):
        with engine_begin() as db:r=db.execute(select(sounds).where(sounds.c.id==sid,sounds.c.campaign_id==c)).mappings().first()
        return self._decode(r)
    def create_sound(self,*,campaign_id,user_id,values):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        try:
            name=str(values["name"]).strip();kind=values["kind"];asset_id=str(values["assetId"]);raw_tags=values.get("tags",[]);tags=list(dict.fromkeys(str(x).strip() for x in raw_tags if str(x).strip()));gain=float(values.get("defaultGain",1));loop=bool(values.get("defaultLoop",False));metadata=values.get("metadata",{})
            if not name or len(name)>191 or kind not in self.KINDS or not math.isfinite(gain) or not 0<=gain<=1 or not isinstance(raw_tags,list) or len(tags)>32 or any(len(tag)>64 for tag in tags) or not isinstance(metadata,dict) or len(self._json(metadata).encode("utf-8"))>8192:raise ValueError
            with engine_begin() as db:asset=db.execute(select(library_assets).where(library_assets.c.id==asset_id,library_assets.c.campaign_id==campaign_id)).mappings().first()
            if not asset or not str(asset.get("content_type") or "").startswith("audio/"):raise ValueError
            now=int(time.time());sid=uuid.uuid4().hex
            with engine_begin() as db:db.execute(insert(sounds).values(id=sid,campaign_id=campaign_id,name=name,asset_id=asset_id,kind=kind,tags_json=self._json(tags),default_gain=gain,default_loop=int(loop),metadata_json=self._json(metadata),version=1,created_at=now,updated_at=now))
            return SoundResult(True,self._sound(campaign_id,sid))
        except (KeyError,TypeError,ValueError,OverflowError):return SoundResult(False,error_key="sound.invalid")
    def list_sounds(self,*,campaign_id,user_id,q="",kind=None,cursor=0,limit=50):
        if not CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id):return SoundResult(False,error_key="sound.not_authorized")
        stmt=select(sounds).where(sounds.c.campaign_id==campaign_id)
        if kind:stmt=stmt.where(sounds.c.kind==kind)
        if q:stmt=stmt.where(or_(sounds.c.name.ilike(f"%{q[:100]}%"),sounds.c.tags_json.ilike(f"%{q[:100]}%")))
        with engine_begin() as db:rows=all_dicts(db.execute(stmt.order_by(sounds.c.name,sounds.c.id).offset(max(0,int(cursor))).limit(min(100,max(1,int(limit))))))
        return SoundResult(True,[self._decode(r) for r in rows])
    def update_sound(self,*,campaign_id,user_id,sound_id,patch,expected_version):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        values={"updated_at":int(time.time())}
        try:
            if set(patch)-{"name","kind","tags","defaultGain","defaultLoop","metadata"}:raise ValueError
            mapping={"name":"name","kind":"kind","defaultGain":"default_gain","defaultLoop":"default_loop","metadata":"metadata_json","tags":"tags_json"}
            for key,value in patch.items():values[mapping[key]]=self._json(value) if key in {"tags","metadata"} else int(value) if key=="defaultLoop" else value
            if "name" in patch and (not str(patch["name"]).strip() or len(str(patch["name"]).strip())>191):raise ValueError
            if "kind" in patch and patch["kind"] not in self.KINDS:raise ValueError
            if "defaultGain" in patch and (not math.isfinite(float(patch["defaultGain"])) or not 0<=float(patch["defaultGain"])<=1):raise ValueError
            if "tags" in patch and (not isinstance(patch["tags"],list) or len(patch["tags"])>32 or any(len(str(tag))>64 for tag in patch["tags"])):raise ValueError
            if "metadata" in patch and (not isinstance(patch["metadata"],dict) or len(self._json(patch["metadata"]).encode("utf-8"))>8192):raise ValueError
        except (TypeError,ValueError,OverflowError):return SoundResult(False,error_key="sound.invalid")
        with engine_begin() as db:changed=db.execute(update(sounds).where(sounds.c.id==sound_id,sounds.c.campaign_id==campaign_id,sounds.c.version==expected_version).values(**values,version=sounds.c.version+1)).rowcount
        return SoundResult(bool(changed),self._sound(campaign_id,sound_id) if changed else None,None if changed else "sound.stale")
    def delete_sound(self,*,campaign_id,user_id,sound_id,expected_version):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        needle=f'"soundId":"{sound_id}"'
        with engine_begin() as db:
            deps=db.execute(select(func.count()).select_from(scene_spatial_sounds).where(scene_spatial_sounds.c.sound_id==sound_id)).scalar_one()+db.execute(select(func.count()).select_from(sound_playlists).where(sound_playlists.c.campaign_id==campaign_id,sound_playlists.c.entries_json.contains(needle))).scalar_one()+db.execute(select(func.count()).select_from(soundscapes).where(soundscapes.c.campaign_id==campaign_id,soundscapes.c.layers_json.contains(needle))).scalar_one()
            if deps:return SoundResult(False,{"dependencyCount":deps},"sound.in_use")
            changed=db.execute(delete(sounds).where(sounds.c.id==sound_id,sounds.c.campaign_id==campaign_id,sounds.c.version==expected_version)).rowcount
        if changed:
            runtime=AudioRuntimeService();playback=runtime.repo.by_key(campaign_id,"core.sound",f"ambient:{sound_id}")
            if playback:runtime.stop(campaign_id=campaign_id,user_id=user_id,playback_id=playback["id"],expected_version=playback["version"])
        return SoundResult(bool(changed),{"id":sound_id,"deleted":True} if changed else None,None if changed else "sound.stale")
    def play_ambient(self,*,campaign_id,user_id,sound_id):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        sound=self._sound(campaign_id,sound_id)
        if not sound or sound["kind"] not in {"music","ambience"}:return SoundResult(False,error_key="sound.not_found")
        runtime=AudioRuntimeService();existing=runtime.repo.by_key(campaign_id,"core.sound",f"ambient:{sound_id}")
        if existing and existing["state"] not in {"playing","pending-user-unlock"}:
            return runtime.update(campaign_id=campaign_id,user_id=user_id,playback_id=existing["id"],patch={"state":"playing"},expected_version=existing["version"])
        return AudioRuntimeService().play(campaign_id=campaign_id,user_id=user_id,package_id="core.sound",values={"asset":{"kind":"library-asset","id":sound["asset_id"]},"channel":"music" if sound["kind"]=="music" else "ambience","gain":sound["default_gain"],"loop":sound["default_loop"],"audience":{"kind":"campaign"},"idempotencyKey":f"ambient:{sound_id}"})
    def pause_ambient(self,*,campaign_id,user_id,sound_id):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        runtime=AudioRuntimeService();playback=runtime.repo.by_key(campaign_id,"core.sound",f"ambient:{sound_id}")
        if not playback:return SoundResult(False,error_key="sound.not_found")
        return runtime.update(campaign_id=campaign_id,user_id=user_id,playback_id=playback["id"],patch={"state":"paused"},expected_version=playback["version"])
    def stop_ambient(self,*,campaign_id,user_id,sound_id):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        runtime=AudioRuntimeService();playback=runtime.repo.by_key(campaign_id,"core.sound",f"ambient:{sound_id}")
        if not playback:return SoundResult(False,error_key="sound.not_found")
        return runtime.stop(campaign_id=campaign_id,user_id=user_id,playback_id=playback["id"],expected_version=playback["version"])
    def create_composition(self,*,campaign_id,user_id,kind,values):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        try:
            name=str(values["name"]).strip();now=int(time.time());rid=uuid.uuid4().hex
            if kind=="playlist":
                entries=values.get("entries",[]);mode=values.get("playbackMode","sequential");cross=int(values.get("crossfadeMs",0));ids=[x.get("soundId") for x in entries]
                if mode not in self.MODES or not 0<=cross<=60000:raise ValueError
                table= sound_playlists; payload=dict(id=rid,campaign_id=campaign_id,name=name,entries_json=self._json(entries),playback_mode=mode,default_gain=values.get("defaultGain"),crossfade_ms=cross,version=1,created_at=now,updated_at=now)
            else:
                layers=values.get("layers",[]);pools=values.get("randomPools",[]);ids=[x.get("soundId") for x in layers]+[sid for p in pools for sid in p.get("soundIds",[])]
                for p in pools:
                    if not 1000<=int(p.get("minInterval",0))<=int(p.get("maxInterval",0))<=3600000 or not 0<=float(p.get("chance",1))<=1:raise ValueError
                table=soundscapes;payload=dict(id=rid,campaign_id=campaign_id,name=name,layers_json=self._json(layers),random_pools_json=self._json(pools),fade_in_ms=int(values.get("defaultFadeIn",0)),fade_out_ms=int(values.get("defaultFadeOut",0)),version=1,created_at=now,updated_at=now)
            if any(not self._sound(campaign_id,str(sid)) for sid in ids):raise ValueError
            with engine_begin() as db:db.execute(insert(table).values(**payload))
            return SoundResult(True,self._decode(payload))
        except (KeyError,TypeError,ValueError):return SoundResult(False,error_key="sound.invalid")
    def list_compositions(self,*,campaign_id,user_id,kind):
        if not CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id):return SoundResult(False,error_key="sound.not_authorized")
        table=sound_playlists if kind=="playlist" else soundscapes
        with engine_begin() as db:rows=all_dicts(db.execute(select(table).where(table.c.campaign_id==campaign_id).order_by(table.c.name)))
        return SoundResult(True,[self._decode(r) for r in rows])
    def set_scene_soundscape(self,*,campaign_id,scene_id,user_id,soundscape_id,expected_version):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        if soundscape_id:
            with engine_begin() as db: valid=db.execute(select(soundscapes.c.id).where(soundscapes.c.id==soundscape_id,soundscapes.c.campaign_id==campaign_id)).first()
            if not valid:return SoundResult(False,error_key="sound.not_found")
        with engine_begin() as db: changed=db.execute(update(scenes).where(scenes.c.id==scene_id,scenes.c.campaign_id==campaign_id,scenes.c.sound_version==expected_version).values(soundscape_id=soundscape_id,sound_version=scenes.c.sound_version+1,updated_at=int(time.time()))).rowcount
        if not changed:return SoundResult(False,error_key="sound.stale")
        with engine_begin() as db: row=db.execute(select(scenes.c.id,scenes.c.soundscape_id,scenes.c.sound_version.label("version")).where(scenes.c.id==scene_id)).mappings().first()
        return SoundResult(True,dict(row))
    def get_scene_soundscape(self,*,campaign_id,scene_id,user_id):
        if not CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id):return SoundResult(False,error_key="sound.not_authorized")
        with engine_begin() as db: row=db.execute(select(scenes.c.id,scenes.c.soundscape_id,scenes.c.sound_version.label("version")).where(scenes.c.id==scene_id,scenes.c.campaign_id==campaign_id)).mappings().first()
        return SoundResult(bool(row),dict(row) if row else None,None if row else "sound.not_found")
    def create_spatial(self,*,campaign_id,scene_id,user_id,values):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        try:
            sound=self._sound(campaign_id,str(values["soundId"]));x=float(values["x"]);y=float(values["y"]);radius=float(values.get("radius",350));gain=float(values.get("gain",sound["default_gain"] if sound else 1));falloff=values.get("falloff","smooth");audience=values.get("audience",{"kind":"campaign"});constrained=bool(values.get("constrainedByWalls",True))
            if not isinstance(audience,dict) or audience.get("kind") not in {"campaign","gm","users"}:raise ValueError
            if audience.get("kind")=="users" and (not isinstance(audience.get("ids"),list) or not audience["ids"]):raise ValueError
            if not sound or sound["kind"]!="sound-effect" or not all(map(math.isfinite,(x,y,radius,gain))) or not 0<radius<=self.MAX_SPATIAL_RADIUS or not 0<=gain<=1 or falloff not in self.FALLOFF:raise ValueError
            with engine_begin() as db:scene=db.execute(select(scenes).where(scenes.c.id==scene_id,scenes.c.campaign_id==campaign_id)).first()
            if not scene:raise ValueError
            now=int(time.time());rid=uuid.uuid4().hex
            loop=bool(values.get("loop",True));enabled=bool(values.get("enabled",True))
            with engine_begin() as db:db.execute(insert(scene_spatial_sounds).values(id=rid,scene_id=scene_id,sound_id=sound["id"],x=x,y=y,radius=radius,gain=gain,falloff=falloff,loop=int(loop),audience_json=self._json(audience),constrained_by_walls=int(constrained),enabled=int(enabled),version=1,created_at=now,updated_at=now))
            row=self.get_spatial(campaign_id,rid) or {}
            playback=AudioRuntimeService().play(campaign_id=campaign_id,user_id=user_id,package_id="core.sound",values={"asset":{"kind":"library-asset","id":sound["asset_id"]},"channel":"ambience" if sound["kind"]=="ambience" else "music" if sound["kind"]=="music" else "sfx","gain":gain,"loop":loop,"audience":audience,"sceneId":scene_id,"idempotencyKey":f"spatial:{rid}"})
            if playback.success:
                if not enabled:playback=AudioRuntimeService().stop(campaign_id=campaign_id,user_id=user_id,playback_id=playback.value["id"],expected_version=playback.value["version"])
                row["_runtimePlayback"]=playback.value
            return SoundResult(True,row)
        except (KeyError,TypeError,ValueError):return SoundResult(False,error_key="sound.invalid")
    def get_spatial(self,campaign_id,rid):
        with engine_begin() as db:r=db.execute(select(scene_spatial_sounds).join(scenes,scenes.c.id==scene_spatial_sounds.c.scene_id).where(scene_spatial_sounds.c.id==rid,scenes.c.campaign_id==campaign_id)).mappings().first()
        return self._decode(r)
    def list_spatial(self,*,campaign_id,scene_id,user_id):
        if not CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id):return SoundResult(False,error_key="sound.not_authorized")
        with engine_begin() as db:rows=all_dicts(db.execute(select(scene_spatial_sounds).join(scenes,scenes.c.id==scene_spatial_sounds.c.scene_id).where(scene_spatial_sounds.c.scene_id==scene_id,scenes.c.campaign_id==campaign_id).order_by(scene_spatial_sounds.c.created_at)))
        return SoundResult(True,[self._decode(r) for r in rows])
    def _listener_points(self,*,campaign_id,scene_id,user_id,preview_token_id=None):
        """Resolve authoritative listener points from tokens controlled by this user."""
        role=CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id)
        if not role:return []
        # GM token control is authoring authority, not an acoustic listener identity.
        # Spatial effects are projected only for player participants through their tokens.
        if role in {"gm","assistant_gm"}:
            if not preview_token_id:return []
            token=TokenRepository().get_by_id(str(preview_token_id))
            if not token or token.get("scene_id")!=scene_id:return []
            with engine_begin() as db:scene_row=db.execute(select(scenes).where(scenes.c.id==scene_id,scenes.c.campaign_id==campaign_id)).mappings().first()
            if not scene_row:return []
            scale=float(scene_row.get("image_scale") or 1);grid=float(scene_row.get("grid_size") or scene_row.get("tile_size") or 1)*scale
            return [((float(token["grid_x"])+float(token.get("width_cells") or 1)/2)*grid,(float(token["grid_y"])+float(token.get("height_cells") or 1)/2)*grid,float(token.get("elevation") or 0),token["id"])]
        with engine_begin() as db:scene_row=db.execute(select(scenes).where(scenes.c.id==scene_id,scenes.c.campaign_id==campaign_id)).mappings().first()
        if not scene_row:return []
        owners=ActorRepository().list_owners_for_campaign_actors(campaign_id=campaign_id)
        scale=float(scene_row.get("image_scale") or 1);grid=float(scene_row.get("grid_size") or scene_row.get("tile_size") or 1)*scale
        points=[]
        for token in TokenRepository().list_by_scene(scene_id):
            actor_owners={entry["id"] for entry in owners.get(token.get("actor_id") or "",[])}
            direct=set(token.get("controlled_by_user_ids") or [])
            controlled=(user_id in actor_owners or user_id in direct
                        or token.get("controlled_by_role")=="party")
            if controlled:points.append(((float(token["grid_x"])+float(token.get("width_cells") or 1)/2)*grid,(float(token["grid_y"])+float(token.get("height_cells") or 1)/2)*grid,float(token.get("elevation") or 0),token["id"]))
        return points
    def acoustic_projection(self,*,campaign_id,scene_id,user_id,listener_x=None,listener_y=None,preview_token_id=None):
        """Return listener-safe projections derived from this user's controlled tokens."""
        if not CampaignRepository().get_member_role(campaign_id=campaign_id,user_id=user_id):return SoundResult(False,error_key="sound.not_authorized")
        targets=self._listener_points(campaign_id=campaign_id,scene_id=scene_id,user_id=user_id,preview_token_id=preview_token_id)
        if listener_x is not None and listener_y is not None:
            try:targets=[(float(listener_x),float(listener_y),0.0,"direct")]
            except (TypeError,ValueError):return SoundResult(False,error_key="sound.invalid")
        listed=self.list_spatial(campaign_id=campaign_id,scene_id=scene_id,user_id=user_id)
        if not listed.success:return listed
        walls=SceneWallRepository().list_for_scene(scene_id);runtime=AudioRuntimeService();result=[]
        for emitter in listed.value:
            best=0.0;best_acoustic=1.0;listener_token_id=None;reach=max(1.0,float(emitter["radius"]))
            for target in targets:
                distance=math.hypot(target[0]-float(emitter["x"]),target[1]-float(emitter["y"]));normalized=max(0.0,min(1.0,1-distance/reach))
                falloff=1.0 if emitter["falloff"]=="constant" and distance<=reach else normalized if emitter["falloff"]=="linear" else normalized*normalized*(3-2*normalized)
                acoustic=sound_attenuation(walls=walls,origin=(float(emitter["x"]),float(emitter["y"]),0.0),target=target[:3]) if emitter.get("constrained_by_walls",True) else 1.0
                projection=falloff*acoustic if emitter.get("enabled",True) else 0.0
                if projection>best:best=projection;best_acoustic=acoustic;listener_token_id=target[3]
            playback=runtime.repo.by_key(campaign_id,"core.sound",f"spatial:{emitter['id']}")
            result.append({"spatialSoundId":emitter["id"],"playbackId":playback["id"] if playback else None,"projection":max(0.0,min(1.0,best)),"audible":best>0,"wallAttenuation":best_acoustic,"listenerTokenId":listener_token_id})
        return SoundResult(True,result)
    def mutate_spatial(self,*,campaign_id,user_id,rid,patch,expected_version,remove=False):
        if not self._manage(campaign_id,user_id):return SoundResult(False,error_key="sound.not_authorized")
        old=self.get_spatial(campaign_id,rid)
        if not old:return SoundResult(False,error_key="sound.not_found")
        try:
            if not isinstance(patch,dict) or set(patch)-{"x","y","radius","gain","falloff","loop","enabled","constrainedByWalls"}:raise ValueError
            numeric={key:float(patch[key]) for key in ("x","y","radius","gain") if key in patch}
            if not all(math.isfinite(value) for value in numeric.values()):raise ValueError
            if "radius" in numeric and not 0<numeric["radius"]<=self.MAX_SPATIAL_RADIUS:raise ValueError
            if "gain" in numeric and not 0<=numeric["gain"]<=1:raise ValueError
            if "falloff" in patch and patch["falloff"] not in self.FALLOFF:raise ValueError
        except (TypeError,ValueError,OverflowError):return SoundResult(False,error_key="sound.invalid")
        with engine_begin() as db:
            if remove:changed=db.execute(delete(scene_spatial_sounds).where(scene_spatial_sounds.c.id==rid,scene_spatial_sounds.c.version==expected_version)).rowcount
            else:
                allowed={"x","y","radius","gain","falloff","loop","enabled","constrainedByWalls"};mapping={"constrainedByWalls":"constrained_by_walls"};values={mapping.get(k,k):int(v) if k in {"loop","enabled","constrainedByWalls"} else v for k,v in patch.items() if k in allowed};changed=db.execute(update(scene_spatial_sounds).where(scene_spatial_sounds.c.id==rid,scene_spatial_sounds.c.version==expected_version).values(**values,version=scene_spatial_sounds.c.version+1,updated_at=int(time.time()))).rowcount
        value={"id":rid,"deleted":True} if remove and changed else self.get_spatial(campaign_id,rid) if changed else None
        if changed:
            runtime=AudioRuntimeService();playback=runtime.repo.by_key(campaign_id,"core.sound",f"spatial:{rid}")
            if playback:
                if remove or patch.get("enabled") is False: projected=runtime.stop(campaign_id=campaign_id,user_id=user_id,playback_id=playback["id"],expected_version=playback["version"])
                else:
                    runtime_patch={}
                    if "gain" in patch:runtime_patch["gain"]=float(patch["gain"])
                    if patch.get("enabled") is True:runtime_patch["state"]="playing"
                    projected=runtime.update(campaign_id=campaign_id,user_id=user_id,playback_id=playback["id"],patch=runtime_patch,expected_version=playback["version"]) if runtime_patch else None
                if projected and projected.success and isinstance(value,dict):value["_runtimePlayback"]=projected.value
        return SoundResult(bool(changed),value,None if changed else "sound.stale")
