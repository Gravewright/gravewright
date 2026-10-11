"""Per-scene encounter order, initiative and turn-driven effect advancement.

Internal commands receive a validated membership from table.domain. Public wrappers
supply current authorization, serialization and idempotent command handling."""

from copy import deepcopy
from gravewright.campaigns.models import Membership
from gravewright.table.domain import manage, version, identifier, MapError, number, boolean
from gravewright.maps.services import scene
from gravewright.tokens import services as tokens
from gravewright.tokens.models import Token
from gravewright.dice.engine import evaluate
from .models import Encounter
from gravewright.actors import services as actors
from gravewright.actors.models import Actor
from gravewright.dice.grammar.errors import RollError
import math


def initiative_score(entry):
    try:
        value = float(entry.get('initiative'))
        return value if math.isfinite(value) else -float('inf')
    except (TypeError, ValueError):
        return -float('inf')


def system_combat(who):
    from gravewright.campaigns.systems import bundled
    module = bundled(who.campaign.system)
    return (module or {}).get('combat') or {}


def configuration(who, row=None):
    provider = system_combat(who)
    config = {'formula': provider.get('formula', ''), **(row.config if row else {})}
    return {**config, 'input': 'roll' if config['formula'] else provider.get('manual_input', 'text'),
            'system_id': who.campaign.system}


def roll_initiative(who, formula, data):
    try:
        roll = system_combat(who).get('roll')
        result = roll(formula, data) if roll else evaluate(formula, 1)['value']['value']
        return number(result, -1e6, 1e6)
    except RollError as error:
        raise MapError(str(error)) from None


def identity(entry):
    return entry.get('tokenId') or entry.get('actorId')


def actor_for(entry):
    if entry.get('tokenId'):
        token = Token.objects.select_related('actor').filter(pk=entry['tokenId']).first()
        return token.actor if token else None
    return Actor.objects.filter(pk=entry.get('actorId')).first()



def state(who, scene_id=None):
    if not scene_id:return dict(active=False,round=0,turn=0,combatants=[],version=0)
    target=scene(scene_id,who);row=Encounter.objects.filter(scene=target).first()
    if not row:return dict(sceneId=str(target.pk),active=False,round=0,turn=0,combatants=[],version=0,config=configuration(who))
    rows=[]
    next_index=next(((row.turn+offset)%len(row.combatants) for offset in range(1,len(row.combatants))
                     if not row.combatants[(row.turn+offset)%len(row.combatants)].get('defeated')),None)
    for entry in row.combatants:
        token=Token.objects.filter(pk=entry.get('tokenId'),scene=target).select_related('actor').prefetch_related('actor__assets').first() if entry.get('tokenId') else None
        actor=token.actor if token else Actor.objects.filter(pk=entry.get('actorId'),campaign_id=who.campaign_id).prefetch_related('assets').first()
        if not actor:continue
        if who.role!='gm' and (entry.get('hidden') or (token.hidden if token else not actors.access(actor,who))):continue
        data=tokens.presentation(token) if token else {}
        index=row.combatants.index(entry)
        controlled=tokens.control(token,who) if token else actors.access(actor,who,True)
        source_bars=(data if token else actor.data).get('bars',{})
        bars=source_bars.get('bar_1',{}) if isinstance(source_bars,dict) else {}
        if not isinstance(bars, dict) or any(type(bars.get(key)) not in (int,float) or not math.isfinite(bars[key]) for key in ('value','max')):
            bars={}
        maximum=bars.get('max',0);value=bars.get('value',0)
        rows.append({'position':len(rows)+1,'conditions_count':len(token.conditions) if token else len(actor.data.get('conditions',[])),
            'bar':{'value':value,'max':maximum,'percent':value/maximum*100} if controlled and maximum>0 else None,
            'is_next':row.active and index==next_index,'has_acted':row.active and index<row.turn,
            **entry,'id':identity(entry),'token_id':entry.get('tokenId'),'actor_id':str(actor.pk),
            'portrait_url':actors.image_url(actor,'token') or actors.image_url(actor,'portrait'),
            'name':data.get('token',{}).get('name') or actor.name,'canControl':controlled,
            'current':row.active and index==row.turn,'is_current':row.active and index==row.turn,
            'can_move_up':index>0,'can_move_down':index<len(row.combatants)-1})
    return dict(sceneId=str(target.pk),active=row.active,round=row.round,turn=row.turn,combatants=rows,current_name=next((c['name'] for c in rows if c['is_current']),''),next_name=next((c['name'] for c in rows if c['is_next']),''),version=row.version,config=configuration(who, row))


def command(who,action,p):
    target=scene(p.get('sceneId'),who)
    row,created=Encounter.objects.get_or_create(scene=target)
    if not created:version(row,p)
    config = configuration(who, row)
    if who.role!='gm':
        if action!='next' or not row.active or not row.combatants:raise MapError('Only the GM can manage combat.', 'forbidden')
        active=row.combatants[row.turn]
        token=tokens.get(active['tokenId'],who) if active.get('tokenId') else None
        controlled=tokens.control(token,who) if token else actors.access(actors.get(active['actorId'],who),who,True)
        if not controlled:raise MapError('It is not your turn.', 'forbidden')
    for old in row.history:
        if 'tokenId' not in old and 0<=old.get('turn',-1)<len(row.combatants):
            old['tokenId']=identity(row.combatants[old['turn']])
    previous_round=row.round
    current_id=identity(row.combatants[row.turn]) if row.combatants and row.turn<len(row.combatants) else None
    if action=='add':
        if p.get('tokenId'):
            token=tokens.get(p['tokenId'],who)
            if token.scene_id!=target.pk:raise MapError('Token is not in this scene.')
            entry=dict(tokenId=str(token.pk))
        else:
            actor=actors.get(p.get('actorId'),who)
            entry=dict(actorId=str(actor.pk))
        if not any(identity(c)==identity(entry) for c in row.combatants):
            if len(row.combatants)>=64:raise MapError('Combatant limit reached.')
            row.combatants.append(dict(**entry,initiative=None,defeated=False,hidden=False))
    elif action=='remove':
        row.combatants=[c for c in row.combatants if identity(c)!=p.get('tokenId',p.get('actorId'))];row.turn=min(row.turn,max(0,len(row.combatants)-1))
    elif action=='configure':
        formula=p.get('formula','')
        if not isinstance(formula,str) or len(formula)>120:raise MapError('Invalid initiative formula.')
        formula = formula.strip()
        if formula:roll_initiative(who, formula, {})
        row.config={**row.config, 'formula':formula}
    elif action=='initiative':
        entry=next((c for c in row.combatants if identity(c)==p.get('tokenId',p.get('actorId'))),None)
        if not entry:raise MapError('Combatant not found.')
        entry['initiative']=number(p.get('value'),-1e6,1e6) if config['input'] != 'text' else str(p.get('value',''))[:24]
        if config['input'] != 'text':
            row.combatants.sort(key=initiative_score,reverse=True)
            row.turn=next((i for i,c in enumerate(row.combatants) if identity(c)==current_id),0) if row.active else 0
    elif action=='roll':
        if not config['formula']:raise MapError('Configure an initiative formula first.')
        scope=p.get('scope','all')
        if scope not in ('all','missing','npcs','one'):raise MapError('Invalid initiative scope.')
        if scope=='one' and not any(identity(entry)==p.get('tokenId',p.get('actorId')) for entry in row.combatants):
            raise MapError('Combatant not found.')
        for entry in row.combatants:
            if scope=='one' and identity(entry)!=p.get('tokenId',p.get('actorId')):continue
            if scope=='missing' and entry.get('initiative') is not None:continue
            if scope=='npcs':
                actor=actor_for(entry)
                if not actor:continue
                player_ids=set(str(i) for i in Membership.objects.filter(campaign_id=who.campaign_id,role='player').values_list('user_id',flat=True))
                if any(actor.permissions.get(i, actor.permissions.get('default', 'none'))=='owner' for i in player_ids):continue
            token=Token.objects.select_related('actor').filter(pk=entry['tokenId'],scene=target).first() if entry.get('tokenId') else None
            actor=token.actor if token else actor_for(entry)
            if not actor:continue
            entry['initiative']=roll_initiative(who,config['formula'],tokens.data(token) if token else actor.data)
        row.combatants.sort(key=initiative_score,reverse=True)
        row.turn=next((i for i,c in enumerate(row.combatants) if identity(c)==current_id),0) if row.active else 0
    elif action=='toggle':
        entry=next((c for c in row.combatants if identity(c)==p.get('tokenId',p.get('actorId'))),None)
        if not entry:raise MapError('Combatant not found.')
        for field in ('hidden','defeated'):
            if field in p:entry[field]=boolean(p[field])
    elif action in ('order-up','order-down','set-turn'):
        index=next((i for i,c in enumerate(row.combatants) if identity(c)==p.get('tokenId',p.get('actorId'))),None)
        if index is None:raise MapError('Combatant not found.')
        if action=='set-turn':row.turn=index
        else:
            target_index=max(0,min(len(row.combatants)-1,index+(-1 if action=='order-up' else 1)))
            row.combatants[index],row.combatants[target_index]=row.combatants[target_index],row.combatants[index]
    elif action in ('next-round','previous-round'):
        if not row.active:raise MapError('Combat has not started.')
        row.history=(row.history+[dict(round=row.round,turn=row.turn,tokenId=identity(row.combatants[row.turn]))])[-256:];row.round=max(1,row.round+(-1 if action=='previous-round' else 1));row.turn=0
    elif action=='start':
        if not row.combatants:raise MapError('Add combatants first.')
        row.active=True;row.round=1;row.turn=0;row.history=[]
    elif action=='stop':row.active=False;row.round=0;row.turn=0;row.history=[]
    elif action=='next':
        if row.combatants and all(c.get('defeated') for c in row.combatants):raise MapError('No undefeated combatants.')
        if not row.active or not row.combatants:raise MapError('Combat has not started.')
        row.history=(row.history+[dict(round=row.round,turn=row.turn,tokenId=identity(row.combatants[row.turn]))])[-256:]
        for _ in row.combatants:
            row.turn+=1
            if row.turn>=len(row.combatants):row.turn=0;row.round+=1
            if not row.combatants[row.turn].get('defeated'):break
    elif action=='previous':
        if not row.history:raise MapError('No previous turn.')
        old=row.history.pop();row.round=old['round'];row.turn=next((i for i,c in enumerate(row.combatants) if identity(c)==old.get('tokenId')),min(old['turn'],max(0,len(row.combatants)-1)))
    else:raise MapError('Unknown combat command.')
    if action in ('remove','order-up','order-down'):
        # A position change must not silently hand the turn to another token.
        row.turn=next((i for i,c in enumerate(row.combatants) if identity(c)==current_id),row.turn)
        if not row.combatants:
            row.active=False;row.turn=0;row.round=0
        # Keep historical identities; discard only references to removed tokens.
        remaining={identity(c) for c in row.combatants}
        row.history=[old for old in row.history if old.get('tokenId') in remaining]
    if action in ('next','next-round') and row.combatants:
        from .effects import advance
        active=row.combatants[row.turn]
        advance(who.campaign_id,active.get('tokenId') if action=='next' else None,actor_id=active.get('actorId') if action=='next' else None,new_round=row.round>previous_round)
    row.version+=1;row.save()
    return state(who,str(target.pk))


def public_state(campaign_id, user_id, scene_id=None):
    """Authorized extension entry point; raw membership-based helpers stay internal."""
    from gravewright.table.domain import state as read
    return read(campaign_id,user_id,'combat',scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    """Use the shared transaction, permission and idempotency boundary."""
    from gravewright.table.domain import command as execute
    return execute(campaign_id,user_id,'combat',action,data,request_id)
