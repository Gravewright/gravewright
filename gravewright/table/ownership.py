"""Document ownership, independent of transport and the table command imports.

Missing overrides use the document default. An explicit denial always wins.
Limited exposes directory metadata, never sheet/document content or assets.
"""
from .models import DocumentAccess

LEVELS = ('none', 'limited', 'read', 'owner')


def level(grants, who, default='none'):
    if who.role == 'gm':
        return 'owner'
    return grants.get(str(who.user_id), grants.get('default', default))


def allows(grants, who, *, edit=False, default='none', listing=False):
    if edit and who.role == 'streamer':
        return False
    current = level(grants, who, default)
    return current == 'owner' or (not edit and current == 'read') or (listing and current == 'limited')


def validate(grants, who, *, choices=LEVELS, bulk=False, roles=False, error_class=None):
    from gravewright.campaigns.models import Membership
    from gravewright.journals.services import JournalError
    keys = {'player', 'streamer'} if roles else {str(x) for x in Membership.objects.filter(campaign_id=who.campaign_id, user__is_active=True).values_list('user_id', flat=True)}
    keys.add('default')
    choices = set(choices) | ({'unchanged'} if bulk else set())
    if not isinstance(grants, dict) or len(grants) > 1000 or any(k not in keys or not isinstance(v, str) or v not in choices for k, v in grants.items()):
        raise (error_class or JournalError)('Invalid resource permissions.')
    return dict(grants)


def policy(who, kind, resource_id):
    # One query per resource kind and membership projection, rather than per row.
    cache = getattr(who, '_ownership_cache', None)
    if cache is None:
        cache = who._ownership_cache = {}
    if kind not in cache:
        cache[kind] = {r.resource_id: r.grants for r in DocumentAccess.objects.filter(campaign_id=who.campaign_id, kind=kind)}
    return cache[kind].get(str(resource_id))


def resource_allows(who, kind, row, *, default='none', listing=False):
    if who.role == 'gm':
        return True
    grants = policy(who, kind, row.pk)
    if grants is None:
        return default == 'read'
    if kind == 'compendiums':
        return grants.get(who.role, grants.get('default', default)) == 'read'
    return allows(grants, who, default=default, listing=listing)


def journal_grants(journal, who):
    explicit = policy(who, 'journals', journal.pk)
    return explicit if explicit is not None else {
        'default': 'read' if journal.visibility in {'shared', 'handout'} else 'none',
        **{str(a.user_id): a.level for a in journal.access.all()},
    }


def page_level(journal, section, who):
    if who.role == 'gm':
        return 'owner'
    if section['audience'] == 'gm':
        return 'none'
    grants = policy(who, 'pages', f'{journal.pk}:{section["id"]}') or {}
    current = grants.get(str(who.user_id), grants.get('default', 'inherit'))
    return level(journal_grants(journal, who), who) if current == 'inherit' else current
