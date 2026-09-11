"""Soundtrack timeline ported from the original Gravewright engine."""
import math
import time
import uuid
import secrets
from copy import deepcopy
from gravewright.table.domain import MapError, number, boolean, identifier
from .models import Playlist

def project(session, now):
    """Project overlapping tracks against one authoritative clock, including preloading."""
    if not session or session['state']=='stopped': return []
    elapsed=session.get('position',0)+(now-session['startedAt'] if session['state']=='playing' else 0)
    rows=[]; tracks=session['tracks']; fade=session['fade']; starts=[]; cursor=0
    if session['kind']=='preset': starts=[0]*len(tracks); cycle=0
    else:
        for track in tracks:
            starts.append(cursor); cursor+=track['duration']-min(fade,track['duration']/2)
        cycle=max(.1,cursor)
    cycles=[0] if not session['repeat'] or not cycle else range(max(0,int(elapsed/cycle)-1),int((elapsed+5)/cycle)+2)
    for lap in cycles:
        for i,(track,start) in enumerate(zip(tracks,starts)):
            start+=lap*cycle
            end=math.inf if session['kind']=='preset' else start+track['duration']
            if start>elapsed+5 or end<=elapsed:continue
            offset=max(0,elapsed-start)
            origin=now-offset if start<=elapsed else now+start-elapsed
            # IDs remain stable across projections; pausing does not restart media.
            rows.append(dict(id=f"score-{session['id']}-{lap}-{i}",asset={'kind':'library-asset','id':track['asset']},channel=track['channel'],
                name=track['name'],state=session['state'],loop=session['kind']=='preset',gain=track['gain'],baseGain=track['gain'],
                startedAt=origin,position=offset if session['state']=='paused' else None,duration=track['duration'],
                fadeIn=min(fade,track['duration']/2),fadeOut=0 if session['kind']=='preset' else min(fade,track['duration']/2),
                version=session['version'],soundtrack=True))
    return rows


def gain_at(row, now):
    elapsed=row.get('position') if row.get('position') is not None else max(0,now-row['startedAt'])
    gain=row['gain']
    if row.get('fadeIn'):gain*=max(0,min(1,elapsed/row['fadeIn']))
    if row.get('fadeOut'):gain*=max(0,min(1,(row['duration']-elapsed)/row['fadeOut']))
    if row.get('fade'):
        fade=row['fade']
        gain*=max(0,1-(now*1000-fade['startedAt'])/max(1,fade['durationMs']))
    return gain


def snapshot(session,now=None):
    now=time.time() if now is None else now
    if not session:return dict(state='stopped',version=0,playbacks=[],serverTime=now)
    rows=project(session,now);previous=session.get('previous')
    if previous and now<previous['until']:
        rows += [{**r,'state':'playing','fade':{'direction':'out','fromGain':r['gain'],'startedAt':previous['at']*1000,'durationMs':(previous['until']-previous['at'])*1000}} for r in previous['rows']]
    elapsed=session.get('position',0)+(now-session['startedAt'] if session['state']=='playing' else 0)
    return {**{k:session[k] for k in ('id','name','state','version','kind','repeat')},'position':elapsed,'playbacks':rows,'serverTime':now,
            'state':'stopped' if not rows and session['state']=='playing' and not session['repeat'] else session['state']}


def command(who,playback,action,p):
    from .services import track
    now=time.time();previous=playback.data.get('score')
    if type(p.get('expectedVersion'))is not int or p['expectedVersion']!=(previous['version'] if previous else 0):raise MapError('Playback changed. Refresh and try again.','conflict')
    if action=='start':
        definition=Playlist.objects.filter(pk=identifier(p.get('id')),campaign_id=who.campaign_id).first()
        if not definition or definition.kind!=p.get('kind'):raise MapError('Composition not found.')
        tracks=[]
        for e in definition.tracks:
            sound=track(e['soundId'],who)
            tracks.append(dict(asset=str(sound.pk),name=sound.name,channel=sound.kind if sound.kind in ('music','ambience') else 'sfx',duration=e['duration'],gain=e['gain']))
        if not tracks:raise MapError('Empty composition.')
        if definition.mode=='shuffle':secrets.SystemRandom().shuffle(tracks)
        session=dict(id=uuid.uuid4().hex,name=definition.name,kind=definition.kind,tracks=tracks,fade=definition.fade,repeat=boolean(p.get('repeat',True)),position=0,startedAt=now,state='playing')
        if previous and definition.fade:
            outgoing=[]
            for r in snapshot(previous,now)['playbacks']:
                if r['state']=='playing' and r['startedAt']<=now:
                    gain=gain_at(r,now)
                    if gain>0:outgoing.append({**r,'gain':gain,'fadeIn':0,'fadeOut':0,'fade':None})
            session['previous']={'rows':outgoing,'at':now,'until':now+definition.fade}
    else:
        if not previous:raise MapError('No soundtrack selected.')
        session=deepcopy(previous);elapsed=previous.get('position',0)+(now-previous['startedAt'] if previous['state']=='playing' else 0)
        if action=='pause':session.update(state='paused',position=elapsed,startedAt=now,previous=None)
        elif action=='resume':
            if previous['state']=='stopped':raise MapError('Start a composition before resuming.')
            if previous['state']=='paused':session.update(state='playing',startedAt=now,previous=None)
        elif action=='stop':session.update(state='stopped',position=0,previous=None)
        elif action in ('next','previous') and session['kind']=='playlist':
            starts=[];cursor=0
            for t in session['tracks']:starts.append(cursor);cursor+=t['duration']-min(session['fade'],t['duration']/2)
            local=elapsed%cursor if session['repeat'] else elapsed
            current=max([i for i,s in enumerate(starts) if s<=local],default=0)
            index=(current+(1 if action=='next' else -1))%len(starts)
            session.update(id=uuid.uuid4().hex,position=starts[index],startedAt=now,state='playing',previous=None)
        else:raise MapError('Invalid transport action.')
    session['version']=(previous['version'] if previous else 0)+1
    playback.data={**playback.data,'score':session};playback.version+=1;playback.save()
    return snapshot(session,now)
