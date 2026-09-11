"""Campaign audio library, scene transport state and listener-specific spatial gain.

Playback is projected against server time. Commands execute through table.domain;
file delivery and upload validation live in table.media and audio.metadata."""

import math
import time
import uuid
from copy import deepcopy
from gravewright.table.domain import manage,identifier,version,title,number,boolean,choice,MapError
from gravewright.maps.services import scene
from gravewright.maps.models import SceneObject
from gravewright.tokens.models import Token
from gravewright.tokens.services import control, geometry, data as token_data
from .models import Track,Playlist,Playback
from .geometry import sound_attenuation
from .transport import project as project_playback


def track(value,who):
    row=Track.objects.filter(pk=identifier(value),campaign_id=who.campaign_id).first()
    if not row:raise MapError('Sound not found.')
    return row


def projection(row):
    return dict(id=str(row.pk),name=row.name,kind=row.kind,src=f'/game/audio/{row.pk}',duration=row.duration,volume=row.volume,loop=row.loop,version=row.version)


def state(who,scene_id=None,preview_token_id=None):
    now=time.time();playback={};revision=0;sources=[]
    if scene_id:
        target=scene(scene_id,who);session=Playback.objects.filter(scene=target).first()
        if session:playback=deepcopy(session.data);revision=session.version
        cell,ox,oy,_,_=geometry(target)
        candidates=Token.objects.filter(scene=target).select_related('actor')
        if who.role=='gm':
            candidates=candidates.filter(pk=identifier(preview_token_id)) if preview_token_id else candidates.none()
        listeners=[(ox+(t.grid_x+token_data(t)['token']['size']/2)*cell,oy+(t.grid_y+token_data(t)['token']['size']/2)*cell,t.elevation) for t in candidates if control(t,who)]
        walls=list(SceneObject.objects.filter(scene=target,kind='walls').values_list('data',flat=True))
        for obj in SceneObject.objects.filter(scene=target,kind='spatialSounds'):
            data=deepcopy(obj.data);gain=0
            if listeners:
                radius=data['radius']*cell/max(.0001,target.settings.get('measureValue',1))
                for x,y,z in listeners:
                    distance=math.hypot(x-data['x'],y-data['y'])
                    normalized=max(0,min(1,1-distance/max(radius,.01)))
                    mode=data.get('falloff','smooth')
                    falloff=(1 if distance<=radius else 0) if mode=='constant' else normalized if mode=='linear' else normalized*normalized*(3-2*normalized)
                    acoustic=sound_attenuation(walls=walls,origin=(data['x'],data['y'],0),target=(x,y,z)) if data.get('occlusion') else 1
                    candidate=falloff*acoustic*data['gain']
                    gain=max(gain,candidate)
            sources.append({**data,'id':str(obj.pk),'version':obj.version,'effectiveGain':gain if data['enabled'] else 0})
    from .soundtrack import snapshot
    score=snapshot(playback.get('score'),now)
    ids={r['asset']['id'] for r in score['playbacks']}
    ids|={r['trackId'] for r in playback.get('ambient',[])}|{r['trackId'] for r in sources}
    if playback.get('soundtrack',{}).get('trackId'):ids.add(playback['soundtrack']['trackId'])
    tracks=Track.objects.filter(campaign_id=who.campaign_id)
    if who.role!='gm':tracks=tracks.filter(pk__in=ids)
    tracks=list(tracks)
    durations={str(t.pk):t.duration for t in tracks}
    playback['ambient']=[project_playback(p,durations.get(p['trackId'],0),now) for p in playback.get('ambient',[])]
    return dict(tracks=[projection(t) for t in tracks],playlists=[dict(id=str(p.pk),name=p.name,tracks=p.tracks,mode=p.mode,kind=p.kind,fade=p.fade,version=p.version) for p in Playlist.objects.filter(campaign_id=who.campaign_id)] if who.role=='gm' else [],
                soundscape=soundscape_state(target) if scene_id else None,playback=playback,score=score,spatialSounds=sources,version=revision,serverTime=now,isGM=who.role=='gm',sceneId=scene_id)


def command(who,action,p):
    manage(who)
    if action in ('track-update','track-delete'):
        row=track(p.get('id'),who);version(row,p)
        if action=='track-delete':
            from django.db import transaction
            storage,path=row.file.storage,row.file.name
            SceneObject.objects.filter(scene__campaign_id=who.campaign_id,kind='spatialSounds',data__trackId=str(row.pk)).delete()
            for session in Playback.objects.filter(scene__campaign_id=who.campaign_id):
                data=deepcopy(session.data)
                data['ambient']=[p for p in data.get('ambient',[]) if p['trackId']!=str(row.pk)]
                if any(t['asset']==str(row.pk) for t in data.get('score',{}).get('tracks',[])):data.pop('score',None)
                elif data.get('score',{}).get('previous'):
                    previous=data['score']['previous']
                    previous['rows']=[r for r in previous['rows'] if r['asset']['id']!=str(row.pk)]
                session.data=data;session.version+=1;session.save()
            for playlist in Playlist.objects.filter(campaign_id=who.campaign_id):
                tracks=[t for t in playlist.tracks if t['soundId']!=str(row.pk)]
                if tracks!=playlist.tracks:playlist.tracks=tracks;playlist.version+=1;playlist.save()
            row.delete();transaction.on_commit(lambda:storage.delete(path));return {}
        row.name=title(p.get('name',row.name));row.volume=number(p.get('volume',row.volume),0,1);row.loop=boolean(p.get('loop',row.loop));row.kind=choice(p.get('kind',row.kind),{'music','ambience','effect'});row.loop=False if row.kind=='effect' else row.loop;row.version+=1;row.save();return {}
    if action.startswith('playlist-'):
        if action=='playlist-create':row=Playlist(campaign_id=who.campaign_id)
        else:
            row=Playlist.objects.filter(pk=identifier(p.get('id')),campaign_id=who.campaign_id).first()
            if not row:raise MapError('Playlist not found.')
            version(row,p)
        if action=='playlist-delete':
            from django.db.models import F
            from gravewright.maps.models import Scene
            Scene.objects.filter(soundscape=row).update(sound_version=F('sound_version')+1)
            row.delete();return {}
        if action not in ('playlist-create','playlist-update'):raise MapError('Unknown playlist command.')
        values=p.get('tracks',[])
        if not isinstance(values,list) or len(values)>200:raise MapError('Invalid playlist.')
        row.tracks=[{'soundId':str(track(v.get('soundId'),who).pk),'duration':number(v.get('duration'),1,86400),'gain':number(v.get('gain',1),0,1)} for v in values if isinstance(v,dict)]
        if not row.tracks or len(row.tracks)!=len(values):raise MapError('Invalid playlist tracks.')
        row.kind=choice(p.get('kind','playlist'),{'playlist','preset'});row.fade=number(p.get('fade',2),0,30)
        row.name=title(p.get('name'));row.mode=choice(p.get('mode','sequential'),{'sequential','shuffle','repeat'});row.version+=1;row.save();return {'id':str(row.pk)}
    target=scene(p.get('sceneId'),who)
    if action.startswith('spatial-'):
        if action=='spatial-create':row=SceneObject(scene=target,kind='spatialSounds')
        else:
            row=SceneObject.objects.filter(pk=identifier(p.get('id')),scene=target,kind='spatialSounds').first()
            if not row:raise MapError('Sound source not found.')
            version(row,p)
        if action=='spatial-delete':row.delete();return {}
        if action not in ('spatial-create','spatial-update'):raise MapError('Unknown spatial command.')
        data={**row.data,**p};sound=track(data.get('trackId'),who)
        row.data=dict(falloff=choice(data.get('falloff','smooth'),{'smooth','linear','constant'}),trackId=str(sound.pk),x=number(data.get('x',0)),y=number(data.get('y',0)),radius=number(data.get('radius',25),.01,1e6),gain=number(data.get('gain',.7),0,1),loop=boolean(data.get('loop',True)),enabled=boolean(data.get('enabled',True)),occlusion=boolean(data.get('occlusion',True)))
        row.version+=1;row.save();return {'id':str(row.pk)}
    row,created=Playback.objects.get_or_create(scene=target)
    if action.startswith('score-'):
        from .soundtrack import command as score_command
        return score_command(who,row,action[6:],p)
    if not created:version(row,p)
    data=deepcopy(row.data);data.setdefault('ambient',[])
    if action in ('play','pause','stop','seek','volume'):
        sound=track(p.get('trackId'),who);entry=next((v for v in data['ambient'] if v['trackId']==str(sound.pk)),None)
        if not entry:entry=dict(trackId=str(sound.pk),status='stopped',position=0,startedAt=time.time(),volume=sound.volume,loop=sound.loop);data['ambient'].append(entry)
        if sound.duration<=0 and sound.file:
            from .metadata import inspect
            with sound.file.open('rb') as stream:
                _,_,sound.duration=inspect(stream)
            sound.save(update_fields=['duration'])
        now=time.time()
        entry.update(project_playback(entry,sound.duration,now))
        if action=='play':
            if entry['status']=='stopped':
                entry['position']=0;entry['playId']=uuid.uuid4().hex
            entry['status']='playing'
        elif action=='pause':
            if entry['status']=='playing':entry['status']='paused'
        elif action=='stop':entry['status']='stopped';entry['position']=0
        elif action=='seek':entry['position']=number(p.get('position'),0,sound.duration if sound.duration>0 else 36000)
        entry['volume']=number(p.get('volume',entry['volume']),0,1)
        entry['loop']=boolean(p.get('loop',entry['loop'])) if sound.kind!='effect' else False
    else:raise MapError('Unknown audio command.')
    row.data=data;row.version+=1;row.save();return {'version':row.version}


def soundscape_state(target):
    return dict(id=str(target.pk), soundscape_id=str(target.soundscape_id) if target.soundscape_id else None,
                version=target.sound_version)


def set_soundscape(target, who, payload):
    manage(who)
    expected = payload.get('expected_version', payload.get('version'))
    if type(expected) is not int or expected != target.sound_version:
        raise MapError('The scene soundscape changed. Refresh before editing.', 'conflict')
    value = payload.get('soundscape_id')
    preset = None
    if value is not None:
        preset = Playlist.objects.filter(pk=identifier(value), campaign_id=who.campaign_id, kind='preset').first()
        if preset is None:
            raise MapError('Soundscape not found.', 'not_found')
    target.soundscape = preset
    target.sound_version += 1
    target.save(update_fields=['soundscape', 'sound_version'])
    return soundscape_state(target)


def public_state(campaign_id, user_id, scene_id=None):
    """Authorized extension entry point; raw membership-based helpers stay internal."""
    from gravewright.table.domain import state as read
    return read(campaign_id,user_id,'audio',scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    """Use the shared transaction, permission and idempotency boundary."""
    from gravewright.table.domain import command as execute
    return execute(campaign_id,user_id,'audio',action,data,request_id)
