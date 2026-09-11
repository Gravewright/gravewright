"""Deck operations, card ownership and face visibility inside table.domain.

Card state is projected for one member: knowing a card identifier does not reveal
its front. Public entry points provide the campaign transaction and retry boundary."""

import secrets
from django.conf import settings
from gravewright.campaigns.models import Membership
from gravewright.maps.services import scene
from gravewright.table.domain import manage, identifier, version, title, boolean, number, MapError
from .models import Deck, Card, CardAsset, DeckDefinition


def card_data(row, who):
    visible=(row.zone=='hand' and row.owner_id==who.user_id) or row.zone=='scene' and row.revealed
    return dict(id=str(row.pk),deck_instance_id=str(row.deck_id),name=row.name if visible else 'Card',
        front_asset_id=str(row.pk) if visible else None,back_asset_id=str(row.deck_id),
        frontUrl=f'/game/cards/card/{row.pk}/front' if visible and row.front else None,
        backUrl=f'/game/cards/deck/{row.deck_id}/back' if row.deck.back else None,
        face_state='face_up' if row.revealed else 'face_down',sceneId=str(row.scene_id) if row.scene_id else None,
        x=row.x,y=row.y,rotation=row.rotation,scale=row.scale,z_index=row.z_index,version=row.version,canControl=who.role=='gm' or row.owner_id==who.user_id)


def state(who,scene_id=None):
    decks=Deck.objects.filter(campaign_id=who.campaign_id).order_by('name')
    rows=Card.objects.filter(deck__campaign_id=who.campaign_id).select_related('deck')
    table=[]
    if scene_id:
        target=scene(scene_id,who)
        table=[card_data(c,who) for c in rows.filter(zone='scene',scene=target)]
    return dict(decks=[dict(id=str(d.pk),name=d.name,version=d.version,draw_count=d.cards.filter(zone='draw').count(),discard_count=d.cards.filter(zone='discard').count()) for d in decks],
        hand=[card_data(c,who) for c in rows.filter(zone='hand',owner_id=who.user_id)],cards=table,isGM=who.role=='gm')


def command(who,action,p):
    if action=='define':
        manage(who);rows=p.get('cards')
        if not isinstance(rows,list) or not 1<=len(rows)<=500:raise MapError('Choose 1 to 500 cards.')
        def asset(value):
            if not value:return None
            found=CardAsset.objects.filter(pk=identifier(value),campaign_id=who.campaign_id,uploader_id=who.user_id).first()
            if not found:raise MapError('Card image not found.')
            return found
        back=asset(p.get('default_back_asset_id'))
        clean=[]
        for entry in rows:
            if not isinstance(entry,dict):raise MapError('Invalid card.')
            front=asset(entry.get('front_asset_id'))
            clean.append({'name':title(entry.get('name')),'front':str(front.pk) if front else None})
        row=DeckDefinition.objects.create(campaign_id=who.campaign_id,name=title(p.get('name')),cards=clean,back=back)
        return {'deck':{'id':str(row.pk)}}
    if action=='instantiate':
        manage(who);definition=DeckDefinition.objects.filter(pk=identifier(p.get('deck_definition_id')),campaign_id=who.campaign_id).first()
        if not definition:raise MapError('Deck definition not found.')
        # Definitions own image files; instances reference them without deleting shared files.
        deck=Deck.objects.create(campaign_id=who.campaign_id,name=definition.name,back=definition.back.file.name if definition.back else '')
        for index,entry in enumerate(definition.cards):
            front=CardAsset.objects.filter(pk=entry['front'],campaign_id=who.campaign_id).first() if entry['front'] else None
            Card.objects.create(deck=deck,name=entry['name'],position=index,front=front.file.name if front else '')
        return {'id':str(deck.pk)}
    if action=='create':
        manage(who);names=p.get('cards',[])
        if not isinstance(names,list) or not 1<=len(names)<=500:raise MapError('Choose 1 to 500 cards.')
        deck=Deck.objects.create(campaign_id=who.campaign_id,name=title(p.get('name')))
        for i,name in enumerate(names):Card.objects.create(deck=deck,name=title(name),position=i)
        return {'id':str(deck.pk)}
    if action in ('draw','shuffle','reset','delete-deck'):
        deck=Deck.objects.filter(pk=identifier(p.get('deck_instance_id')),campaign_id=who.campaign_id).first()
        if not deck:raise MapError('Deck not found.')
        if action!='draw':manage(who);version(deck,p)
        if action=='delete-deck':
            from django.db import transaction
            files=[(c.front.storage,c.front.name) for c in deck.cards.all() if c.front]
            if deck.back:files.append((deck.back.storage,deck.back.name))
            deck.delete()
            for storage,path in files:
                if not CardAsset.objects.filter(file=path).exists():transaction.on_commit(lambda s=storage,n=path:s.delete(n))
            return {}
        if action=='draw':
            count=p.get('count',1)
            if type(count)is not int or not 1<=count<=50:raise MapError('Invalid card count.')
            cards=list(deck.cards.filter(zone='draw').order_by('position','id')[:count])
            if len(cards)!=count:raise MapError('There are not enough cards in this deck.')
            recipient=who.user_id
            if p.get('recipient'):
                manage(who);recipient=identifier(p['recipient'])
                if not Membership.objects.filter(campaign_id=who.campaign_id,user_id=recipient).exists():raise MapError('Recipient not found.')
            destination=p.get('destination','hand')
            if destination not in ('hand','scene','table','chat'):raise MapError('Invalid draw destination.')
            target=scene(p.get('sceneId'),who) if destination in ('scene','table') else None
            for card in cards:
                card.zone='hand' if destination=='hand' else 'discard' if destination=='chat' else 'scene';card.owner_id=recipient;card.scene=target;card.revealed=p.get('face_state','face_up')=='face_up'
                card.x=number(p.get('x',0));card.y=number(p.get('y',0));card.version+=1;card.save()
            if destination=='chat':
                import uuid
                from django.db import transaction
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                from gravewright.chat.services import say,public_message
                from gravewright.chat.models import Message
                label=', '.join(c.name if c.revealed else 'Card (face down)' for c in cards)
                message,_=say(who.pk, f'{deck.name}: {label}'[:2000], str(uuid.uuid4()), p.get('sceneId'))
                stored=Message.objects.get(pk=message['id'])
                # Capture only public faces; hidden cards never enter the payload.
                stored.metadata={'type':'cards.revealed','card_event':{'deck_id':str(deck.pk),'deck_name':deck.name,'count':len(cards)}}
                from gravewright.chat.card_attachments import capture
                capture(stored,cards)
                message=public_message(stored)
                # say() publishes the final attachment metadata after this transaction commits.
            deck.version+=1;deck.save()
            return {'cards':[card_data(c,who) for c in cards]}
        cards=list(deck.cards.all() if action=='reset' else deck.cards.filter(zone='draw'))
        secrets.SystemRandom().shuffle(cards)
        for i,card in enumerate(cards):
            card.position=i
            if action=='reset':card.zone='draw';card.owner=None;card.scene=None;card.revealed=False
            card.version+=1;card.save()
        deck.version+=1;deck.save();return {}
    row=Card.objects.select_related('deck').filter(pk=identifier(p.get('id')),deck__campaign_id=who.campaign_id).first()
    if not row or row.zone not in ('hand','scene'):raise MapError('Card not found.')
    if who.role!='gm' and row.owner_id!=who.user_id:raise MapError('You do not control this card.', 'forbidden')
    version(row,p)
    if action=='discard':row.zone='discard';row.owner=None;row.scene=None;row.revealed=False
    elif action=='return':
        row.zone='draw';row.owner=None;row.scene=None;row.revealed=False
        row.position=max(row.deck.cards.values_list('position',flat=True),default=0)+1
    elif action=='give':
        recipient=identifier(p.get('recipient'))
        if not Membership.objects.filter(campaign_id=who.campaign_id,user_id=recipient).exists():raise MapError('Recipient not found.')
        row.owner_id=recipient;row.zone='hand';row.scene=None;row.revealed=False
    elif action=='place':
        row.scene=scene(p.get('sceneId'),who);row.zone='scene';row.x=number(p.get('x'));row.y=number(p.get('y'));row.revealed=boolean(p.get('reveal',True))
    elif action=='take':row.zone='hand';row.owner_id=who.user_id;row.scene=None
    elif action=='flip':row.revealed=not row.revealed
    elif action=='move':
        if row.zone!='scene':raise MapError('Card is not on the table.')
        scene(row.scene_id,who);row.x=number(p.get('x',row.x));row.y=number(p.get('y',row.y));row.rotation=number(p.get('rotation',row.rotation))%360
    else:raise MapError('Unknown card action.')
    if action in ('place','move'):
        row.scale=number(p.get('scale',row.scale),0.01,100)
        z=p.get('z_index',row.z_index)
        if type(z) is not int or not -1000000<=z<=1000000:raise MapError('Invalid card order.')
        row.z_index=z
    row.version+=1;row.save();row.deck.version+=1;row.deck.save()
    return {'card':card_data(row,who)}


def public_state(campaign_id, user_id, scene_id=None):
    """Authorized extension entry point; raw membership-based helpers stay internal."""
    from gravewright.table.domain import state as read
    return read(campaign_id,user_id,'cards',scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    """Use the shared transaction, permission and idempotency boundary."""
    from gravewright.table.domain import command as execute
    return execute(campaign_id,user_id,'cards',action,data,request_id)
