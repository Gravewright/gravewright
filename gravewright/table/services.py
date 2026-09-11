"""Campaign-scoped command search and the original per-participant lobby."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from gravewright.actors import services as actors
from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals.services import JournalError, member, permissions, projection
from gravewright.journals.models import Journal
from gravewright.maps.models import Scene
from gravewright.maps.services import MapError
from .models import LobbyState


def lobby(campaign_id, user_id):
    if not settings.LOBBY_READY_CHECK_ENABLED:
        raise JournalError('Ready check is disabled.', 'forbidden')
    who = member(campaign_id, user_id)
    selectable = [a for a in Actor.objects.filter(campaign_id=campaign_id) if actors.access(a, who, True)]
    visible = {a.pk: a for a in Actor.objects.filter(campaign_id=campaign_id) if actors.access(a, who)}
    states = {row.membership_id: row for row in LobbyState.objects.filter(membership__campaign_id=campaign_id)}
    members = []
    for m in Membership.objects.filter(campaign_id=campaign_id).select_related('user'):
        state = states.get(m.pk)
        actor = visible.get(state.selected_actor_id) if state else None
        members.append(dict(user_id=str(m.user_id), name=m.user.name, role=m.role,
            is_online=m.connections.filter(expires_at__gt=timezone.now()).exists(),
            is_ready=state.is_ready if state else False,
            selected_actor_id=str(actor.pk) if actor else None,
            selected_actor_name=actor.name if actor else None,
            assets_state=state.assets_state if state else 'unknown'))
    return dict(members=members, actors=[dict(id=str(a.pk), name=a.name) for a in selectable],
                summary=dict(ready=sum(m['is_ready'] for m in members), total=len(members)))


@transaction.atomic
def update_lobby(campaign_id, user_id, payload):
    if not settings.LOBBY_READY_CHECK_ENABLED:
        raise JournalError('Ready check is disabled.', 'forbidden')
    Campaign.objects.select_for_update().get(pk=campaign_id)
    who = member(campaign_id, user_id)
    from gravewright.journals.services import writable
    writable(who)
    ready = payload.get('is_ready')
    assets = payload.get('assets_state', 'unknown')
    if type(ready) is not bool or assets not in ('unknown', 'loading', 'ready', 'error'):
        raise JournalError('Invalid readiness state.')
    actor = actors.get(payload['selected_actor_id'], who, True) if payload.get('selected_actor_id') else None
    LobbyState.objects.update_or_create(membership=who, defaults=dict(is_ready=ready, selected_actor=actor, assets_state=assets))
    from gravewright.realtime.dispatch import send
    transaction.on_commit(lambda:send(campaign_id,{'type':'room.lobby'}),robust=True)
    return lobby(campaign_id, user_id)


def search(campaign_id, user_id, query):
    if not settings.COMMAND_PALETTE_ENABLED:
        raise JournalError('Command search is disabled.', 'forbidden')
    who = member(campaign_id, user_id)
    if not isinstance(query, str) or len(query) > 200:
        raise JournalError('Invalid search.')
    query = query.strip()
    if len(query) < 2:
        return []
    results = []
    def add(row, kind):
        results.append(dict(id=str(row.pk), type=kind, title=row.name if hasattr(row, 'name') else row.title,
            subtitle='', snippet='', icon={'actor':'ph-user','journal':'ph-book-open','scene':'ph-map'}.get(kind,'ph-stack'),
            target=dict(action='open_'+kind, id=str(row.pk))))
    for row in Actor.objects.filter(campaign_id=campaign_id, name__icontains=query).order_by('name')[:200]:
        if actors.access(row, who): add(row, 'actor')
    def readable_text(value):
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ' '.join(readable_text(v) for v in value)
        if isinstance(value, dict):
            return ' '.join(readable_text(v) for k, v in value.items()
                            if k in ('text', 'content', 'doc', 'title', 'description', 'sections'))
        return ''
    for row in Journal.objects.filter(campaign_id=campaign_id).prefetch_related('access').order_by('title'):
        if not permissions(row, who)[0]:
            continue
        view = projection(row, who)
        body = readable_text([view.get('content_doc', {}), view.get('sections', [])])
        index = body.casefold().find(query.casefold())
        if query.casefold() in row.title.casefold() or index >= 0:
            add(row, 'journal')
            if index >= 0:
                results[-1]['snippet'] = body[max(0, index - 50):index + len(query) + 100]

    for row in Scene.objects.filter(campaign_id=campaign_id, name__icontains=query).order_by('name')[:200]:
        from gravewright.maps.services import scene
        try:scene(row.pk,who)
        except MapError:continue
        add(row,'scene')
    from gravewright.items.models import Item
    from gravewright.items.services import access
    from gravewright.compendiums.models import Pack
    for row in Item.objects.filter(campaign_id=campaign_id,name__icontains=query)[:200]:
        if access(row,who):add(row,'item')
    for row in Pack.objects.filter(campaign_id=campaign_id,name__icontains=query)[:200]:
        if who.role=='gm' or row.shared:add(row,'compendium')
    from gravewright.compendiums.catalog import summaries
    for pack in summaries(who):
        if query.casefold() in pack['name'].casefold():
            results.append(dict(id=pack['id'], type='compendium', title=pack['name'],
                subtitle='', snippet='', icon='ph-stack',
                target=dict(action='open_compendium', id=pack['id'])))
    return sorted(results, key=lambda r: (r['title'].casefold(), r['type'], r['id']))[:20]
