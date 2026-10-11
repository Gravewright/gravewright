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


def search(campaign_id, user_id, query, *, kind='', recent=None):
    if not settings.COMMAND_PALETTE_ENABLED:
        raise JournalError('Command search is disabled.', 'forbidden')
    who = member(campaign_id, user_id)
    if not isinstance(query, str) or len(query) > 200:
        raise JournalError('Invalid search.')
    query = query.strip()
    if kind not in ('', 'actor', 'item', 'journal', 'quest', 'quest_board', 'scene', 'compendium'):
        raise JournalError('Invalid search filter.')
    recent_mode = len(query) < 2 and recent is not None
    references = []
    if recent is not None:
        from uuid import UUID
        if not isinstance(recent, list) or len(recent) > 12:
            raise JournalError('Invalid recent documents.')
        for ref in recent:
            if not isinstance(ref, dict) or ref.get('type') not in ('actor','item','journal','scene','compendium') or not isinstance(ref.get('id'),str):
                raise JournalError('Invalid recent document.')
            value=ref['id']
            try:canonical=str(UUID(value.removeprefix('native:') if ref['type']=='compendium' else value))
            except ValueError:raise JournalError('Invalid recent document.') from None
            if len(value)>43:raise JournalError('Invalid recent document.')
            value=('native:' if value.startswith('native:') else '')+canonical
            references.append((ref['type'],value))
    if len(query) < 2 and not recent_mode:
        return []
    results = []
    def rows(model, resource, field='name'):
        qs=model.objects.filter(campaign_id=campaign_id)
        if recent_mode:
            qs=qs.filter(pk__in=[value for name,value in references if name==resource and not value.startswith('native:')])
        elif resource!='journal':qs=qs.filter(**{field+'__icontains':query})
        if kind and kind!=resource and not (resource=='journal' and kind in ('quest','quest_board')):return qs.none()
        return qs.order_by(field)
    def add(row, resource):
        category=row.type if resource=='journal' and row.type in ('quest','quest_board') else resource
        if kind and kind!=category:return False
        actions=['open']+(['activate'] if resource=='scene' and who.role=='gm' else [])
        results.append(dict(id=str(row.pk), type=resource, kind=category, title=row.name if hasattr(row, 'name') else row.title,
            subtitle='', snippet='', actions=actions, icon={'actor':'ph-user','journal':'ph-book-open','scene':'ph-map'}.get(resource,'ph-stack'),
            target=dict(action='open_'+resource, id=str(row.pk))))
        return True
    for row in rows(Actor,'actor')[:200]:
        if actors.access(row, who): add(row, 'actor')
    def readable_text(value):
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ' '.join(readable_text(v) for v in value)
        if isinstance(value, dict):
            return ' '.join(readable_text(v) for k, v in value.items()
                            if k in ('text', 'content', 'doc', 'title', 'description', 'sections', 'public', 'summary', 'description_markdown', 'objectives', 'rewards', 'gm', 'notes', 'secrets'))
        return ''
    for row in rows(Journal,'journal','title').prefetch_related('access'):
        from gravewright.journals.types import via_board
        if not (permissions(row, who)[0] or via_board(row, who)):
            continue
        view = projection(row, who)
        body = readable_text([view.get('content_doc', {}), view.get('sections', []), view.get('quest', {})])
        index = body.casefold().find(query.casefold())
        if recent_mode or query.casefold() in row.title.casefold() or index >= 0:
            if not add(row, 'journal'):continue
            if index >= 0 and not recent_mode:
                results[-1]['snippet'] = body[max(0, index - 50):index + len(query) + 100]
            elif body:results[-1]['snippet']=body[:160]

    for row in rows(Scene,'scene')[:200]:
        from gravewright.maps.services import scene
        try:scene(row.pk,who)
        except MapError:continue
        add(row,'scene')
    from gravewright.items.models import Item
    from gravewright.items.services import access
    from gravewright.compendiums.models import Pack
    for row in rows(Item,'item')[:200]:
        if access(row,who):add(row,'item')
    for row in rows(Pack,'compendium')[:200]:
        from .ownership import resource_allows
        if resource_allows(who,'compendiums',row,default='read' if row.shared else 'none'):add(row,'compendium')
    from gravewright.compendiums.catalog import summaries
    for pack in summaries(who):
        if kind in ('','compendium') and ((recent_mode and ('compendium',pack['id']) in references) or (not recent_mode and query.casefold() in pack['name'].casefold())):
            results.append(dict(id=pack['id'], type='compendium', kind='compendium', title=pack['name'],
                subtitle='', snippet='', actions=['open'], icon='ph-stack',
                target=dict(action='open_compendium', id=pack['id'])))
    return sorted(results, key=lambda r: references.index((r['type'],r['id'])) if recent_mode else (r['title'].casefold(), r['type'], r['id']))[:20]
