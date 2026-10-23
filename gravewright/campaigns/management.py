"""Read-only preparation state for current campaign game masters.

This service does not join a table, allocate a presence lease or select a scene.
"""

from django.db.models import Count, Q

from gravewright.accounts.services import AuthError
from gravewright.actors.models import Actor
from gravewright.items.models import Item
from gravewright.journals.data import QUEST_STATUSES, normalize_quest_data
from gravewright.journals.models import Journal
from gravewright.journals.services import JournalError, member
from gravewright.maps.models import Scene

from .catalog import get_ruleset
from .models import Membership
from .services import get_campaign, public_campaign
from .systems import resolve_system_id


def authorize(user, campaign_id):
    """Require a current GM membership, independently of the host account role."""
    if not user.is_authenticated:
        raise AuthError('authentication_required', 401)
    campaign = get_campaign(user, campaign_id, manage=True)
    try:
        who = member(campaign.pk, user.pk)
    except JournalError:
        raise AuthError('container_not_found', 404) from None
    if who.role != Membership.Role.GM:
        raise AuthError('owner_required', 403)
    return campaign, who


def _summary(campaign, ruleset):
    members = [
        {'id': str(membership.user_id), 'name': membership.user.name, 'role': membership.role}
        for membership in campaign.memberships.all() if membership.user.is_active
    ]
    journals = Journal.objects.filter(campaign_id=campaign.pk)
    journal_counts = journals.aggregate(total=Count('pk'), quests=Count('pk', filter=Q(type='quest')))
    statuses = {status: 0 for status in QUEST_STATUSES}
    objectives = {'total': 0, 'completed': 0}
    # Fetch only structured progress, excluding document bodies and GM secrets.
    for row in journals.filter(type='quest').order_by().values('data__status', 'data__objectives').iterator():
        quest = normalize_quest_data({'status': row['data__status'], 'objectives': row['data__objectives']})
        statuses[quest['status']] += 1
        objectives['total'] += len(quest['objectives'])
        objectives['completed'] += sum(objective['completed'] for objective in quest['objectives'])
    return {
        'campaign': public_campaign(campaign),
        'systemId': resolve_system_id(campaign.system),
        'memberRole': Membership.Role.GM,
        'members': members,
        'counts': {
            'scenes': Scene.objects.filter(campaign_id=campaign.pk).count(),
            'actors': Actor.objects.filter(campaign_id=campaign.pk).count(),
            'journals': journal_counts['total'],
            'items': Item.objects.filter(campaign_id=campaign.pk).count(),
            'quests': journal_counts['quests'],
            'members': len(members),
        },
        'quests': {'total': journal_counts['quests'], 'byStatus': statuses, 'objectives': objectives},
        'domains': {
            'maps': True, 'actors': True, 'journals': True, 'items': bool(ruleset.get('itemTypes')),
            'quests': True, 'library': True, 'audio': True, 'cards': True,
            'compendiums': True, 'combat': True, 'members': True,
        },
    }


def load(user, campaign_id):
    """Return authorized shell metadata and a compact campaign overview."""
    campaign, who = authorize(user, campaign_id)
    ruleset = get_ruleset(campaign.system, campaign_id=campaign.pk) or {}
    return {'campaign': campaign, 'membership': who, 'ruleset': ruleset,
            'overview': _summary(campaign, ruleset)}


def overview(user, campaign_id):
    """Project management counts without loading actor sheets or journal bodies."""
    return load(user, campaign_id)['overview']


def public_overview(campaign_id, user_id):
    """Resolve identifiers through live membership for the public Python API."""
    who = member(campaign_id, user_id)
    return overview(who.user, campaign_id)
