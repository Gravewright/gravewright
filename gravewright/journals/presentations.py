"""Recipient-bound, short-lived read access without permanent journal grants."""

from types import SimpleNamespace

from django.conf import settings
from django.core import signing

from . import services
from .models import Journal

TTL = 90
SALT = "gravewright.journal.presentation.v1"


def present(who, payload):
    if who.role != "gm":
        raise services.JournalError("Only the GM can present a journal.", "forbidden")
    journal = services.get(payload.get("journal_id"), who)
    target = payload.get("target", "")
    if target and not settings.TARGETED_HANDOUTS_ENABLED:
        raise services.JournalError("Targeted handouts are disabled.", "forbidden")
    if target:
        target = str(
            services.member(who.campaign_id, services.identifier(target)).user_id
        )
    targets = payload.get('targets')
    if targets is not None:
        if not settings.TARGETED_HANDOUTS_ENABLED:
            raise services.JournalError('Targeted handouts are disabled.', 'forbidden')
        if not isinstance(targets, list) or not targets or len(targets) > 1000:
            raise services.JournalError('Choose at least one player.')
        targets = list(dict.fromkeys(str(services.member(who.campaign_id, services.identifier(value)).user_id) for value in targets))
    elif target:
        targets = [target]
    page_id = payload.get('page_id')
    if page_id is not None:
        from .data import normalize_diary_data
        if journal.type != 'diary' or not isinstance(page_id, str):
            raise services.JournalError('Page not found.', 'not_found')
        page = next((p for p in normalize_diary_data(journal.data)['sections'] if p['id'] == page_id), None)
        if not page or page['audience'] == 'gm':
            raise services.JournalError('Make the page public before showing it to players.')
    ownership = payload.get('ownership', 'unchanged')
    from gravewright.table.ownership import LEVELS, journal_grants, level
    if not isinstance(ownership, str) or ownership not in (*LEVELS, 'unchanged'):
        raise services.JournalError('Invalid resource permissions.')
    if ownership != 'unchanged':
        if page_id is not None:
            raise services.JournalError('Change journal access from the journal presentation.')
        from gravewright.campaigns.models import Membership
        from gravewright.table.permission_views import store
        grants = dict(journal_grants(journal, who))
        members = Membership.objects.filter(campaign_id=who.campaign_id, user__is_active=True).exclude(role='gm')
        if targets is not None:
            members = members.filter(user_id__in=targets)
        for recipient in members:
            value = 'read' if recipient.role == 'streamer' and ownership == 'owner' else ownership
            current = level(grants, recipient)
            if LEVELS.index(current) < LEVELS.index(value):
                grants[str(recipient.user_id)] = value
        if targets is None and LEVELS.index(grants.get('default', 'none')) < LEVELS.index(ownership):
            grants['default'] = ownership
        store(who, 'journals', journal, grants)
    return {
        "presentation": {
            "journal_id": str(journal.pk),
            "campaign_id": str(who.campaign_id),
            "issuer": str(who.user_id),
            "target": target,
            "targets": targets,
            "page_id": page_id,
        }
    }


def ticket(event, user_id):
    return signing.dumps({**event, "user_id": str(user_id)}, salt=SALT)


def resolve(value, user_id, campaign_id=None):
    try:
        data = signing.loads(value, salt=SALT, max_age=TTL)
        if data["user_id"] != str(user_id) or (
            campaign_id and data["campaign_id"] != str(campaign_id)
        ):
            raise ValueError()
        who = services.member(data["campaign_id"], user_id)
        if services.member(who.campaign_id, data["issuer"]).role != "gm":
            raise ValueError()
        journal = Journal.objects.prefetch_related("access").get(
            pk=data["journal_id"], campaign_id=who.campaign_id
        )
        # Presentations always project player content, including when the recipient is a GM.
        # A presentation grants temporary read access, without persisting ownership.
        # Keep explicit page restrictions and always exclude GM content.
        from gravewright.table.ownership import journal_grants
        grants = dict(journal_grants(journal, who))
        grants[str(who.user_id)] = 'read'
        viewer = SimpleNamespace(role='player', user_id=who.user_id, campaign_id=who.campaign_id,
                                 _ownership_cache={'journals': {str(journal.pk): grants}})
        page_id = data.get('page_id')
        if page_id:
            viewer._ownership_cache['pages'] = {f'{journal.pk}:{page_id}': {'default': 'read'}}
        view = services.projection(journal, viewer)
        if page_id:
            view['sections'] = [p for p in view.get('sections', []) if p['id'] == page_id]
            view['editable_sections'] = view['sections']
            view['content_doc'] = {}
            view['cover_image'] = {}
            if not view['sections']:
                raise ValueError()
        view.update(can_edit=False, can_open=True, listed=False, presentation_ticket=value)
        view.pop("permissions", None)

        def rewrite(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    item[key] = rewrite(child)
            elif isinstance(item, list):
                return [rewrite(child) for child in item]
            elif isinstance(item, str) and item.startswith("/game/journal/asset/"):
                return f"/game/handouts/presentation/{value}/asset/{item.rsplit('/', 1)[-1]}"
            return item

        return journal, rewrite(view)
    except signing.BadSignature, Journal.DoesNotExist, KeyError, ValueError, TypeError:
        raise services.JournalError(
            "The presentation expired or is unavailable.", "not_found"
        ) from None
