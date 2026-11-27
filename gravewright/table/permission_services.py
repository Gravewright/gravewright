"""Revisioned GM ownership operations shared by native editors and integrations."""
import hashlib
import json
from django.db import transaction
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals.services import JournalError, identifier, member
from gravewright.maps.models import Receipt
from . import ownership as access
from .models import DocumentAccess


def _native_pack(who, record):
    """Permission view of one installed or legacy native pack from ``catalog.available``."""
    from types import SimpleNamespace
    from gravewright.compendiums.catalog import collection_key
    key, base, collection, pack = record
    explicit = DocumentAccess.objects.filter(campaign_id=who.campaign_id, kind='compendiums', resource_id=key).first()
    # ContentAccess rows use the same collection key as catalog reads and the legacy permissions command.
    return SimpleNamespace(pk=key, name=pack.get('label', pack.get('name', str(pack.get('id')))), version=explicit.version if explicit else 1,
                           shared=False, native=True, collection=collection_key(base, collection), pack=str(pack.get('id')), pack_type=pack.get('type'))


def resolve(who, kind, key):
    from gravewright.actors.models import Actor, Folder as ActorFolder
    from gravewright.items.models import Item, Folder as ItemFolder
    from gravewright.journals.models import Journal, Folder as JournalFolder
    from gravewright.maps.models import Scene, Folder as SceneFolder
    from gravewright.cards.models import Deck
    from gravewright.compendiums.models import Pack
    models = {'actors': Actor, 'items': Item, 'journals': Journal, 'scenes': Scene,
              'cards': Deck, 'compendiums': Pack, 'actor-folders': ActorFolder,
              'item-folders': ItemFolder, 'journal-folders': JournalFolder, 'scene-folders': SceneFolder}
    if kind == 'tokens':
        from gravewright.tokens.models import Token
        token = Token.objects.select_related('actor').filter(pk=identifier(key), scene__campaign_id=who.campaign_id).first()
        if not token:
            raise JournalError('Document not found.', 'not_found')
        return 'actors', token.actor, None
    if kind == 'compendiums' and key.startswith('native:'):
        from gravewright.compendiums.catalog import available
        found = next((r for r in available(who) if r[0] == key), None)
        if not found:
            raise JournalError('Document not found.', 'not_found')
        return kind, _native_pack(who, found), None
    if kind == 'compendium-folders':
        from types import SimpleNamespace
        from gravewright.compendiums.catalog import folder_packs
        path, records = folder_packs(who, key)
        if not records:
            raise JournalError('Document not found.', 'not_found')
        # Declared folders exist only through their packs; read collections once for all of them.
        return kind, SimpleNamespace(pk=key, name=path[-1], packs=[_native_pack(who, record) for record in records]), None
    if kind == 'pages':
        parts = key.split(':', 1)
        if len(parts) != 2:
            raise JournalError('Page not found.', 'not_found')
        journal = Journal.objects.filter(pk=identifier(parts[0]), campaign_id=who.campaign_id, type='diary').first()
        from gravewright.journals.data import normalize_diary_data
        section = next((s for s in normalize_diary_data(journal.data)['sections'] if s['id'] == parts[1]), None) if journal else None
        if not section:
            raise JournalError('Page not found.', 'not_found')
        return kind, journal, section
    model = models.get(kind)
    row = model.objects.filter(pk=identifier(key), campaign_id=who.campaign_id).first() if model else None
    if not row:
        raise JournalError('Document not found.', 'not_found')
    return kind, row, None


def children(kind, row):
    if kind == 'compendium-folders':
        # Unlike document folders, a compendium folder covers the packs in its subfolders.
        return row.packs
    from gravewright.actors.models import Actor
    from gravewright.items.models import Item
    from gravewright.journals.models import Journal
    from gravewright.maps.models import Scene
    model = {'actor-folders': Actor, 'item-folders': Item, 'journal-folders': Journal, 'scene-folders': Scene}[kind]
    return list(model.objects.filter(campaign_id=row.campaign_id, folder=row).order_by('pk'))


def snapshot(who, kind, row, section=None):
    bulk = kind.endswith('-folders')
    key = f'{row.pk}:{section["id"]}' if section else str(row.pk)
    choices = list(access.LEVELS) if kind in {'actors', 'items', 'journals', 'actor-folders', 'item-folders', 'journal-folders'} else ['none', 'read']
    policy = DocumentAccess.objects.filter(campaign_id=who.campaign_id, kind=kind, resource_id=key).first()
    if bulk:
        # Native packs may change through role defaults without a document version.
        rows = [(str(c.pk), c.version, snapshot(who, 'compendiums', c)['permissions'] if kind == 'compendium-folders' else None)
                for c in children(kind, row)]
        revision = hashlib.sha256(json.dumps(rows if kind == 'compendium-folders' else [r[:2] for r in rows], sort_keys=True).encode()).hexdigest()
        grants = {'default': 'unchanged'}
    elif kind in {'actors', 'items'}:
        grants, revision = {'default': 'none', **row.permissions}, row.version
    elif kind == 'journals':
        grants, revision = access.journal_grants(row, who), row.version
    elif kind == 'pages':
        # A page can restrict parent access, but cannot grant access to a private journal.
        choices = ['inherit', 'none', 'read']
        grants, revision = policy.grants if policy else {'default': 'inherit'}, row.version
    else:
        default = 'read' if kind == 'cards' or kind == 'scenes' and row.visibility == 'players' or kind == 'compendiums' and row.shared else 'none'
        grants, revision = policy.grants if policy else {'default': default}, row.version
        if getattr(row, 'native', False) and not policy:
            from gravewright.compendiums.catalog import native_defaults
            from gravewright.compendiums.models import ContentAccess
            grants.update(native_defaults(row.pack_type))
            grants.update({a.role: 'read' if a.level in {'read','owner'} else 'none' for a in ContentAccess.objects.filter(campaign_id=who.campaign_id,collection=row.collection,pack=row.pack)})
    members = [{'id': str(m.user_id), 'name': m.user.name, 'role': m.role} for m in Membership.objects.filter(campaign_id=who.campaign_id, user__is_active=True).select_related('user').order_by('user__name', 'user_id')]
    return {'kind': kind, 'id': key, 'title': section['title'] if section else getattr(row, 'name', getattr(row, 'title', getattr(row, 'label', ''))),
            'version': revision, 'permissions': grants, 'levels': choices, 'members': members, 'bulk': bulk,
            'roles': kind in {'compendiums', 'compendium-folders'}, 'gmOnlyPage': bool(section and section['audience'] == 'gm')}


def store(who, kind, row, grants, key=None):
    if kind in {'actors', 'items'}:
        row.permissions = grants
    else:
        DocumentAccess.objects.update_or_create(campaign_id=who.campaign_id, kind=kind, resource_id=key or str(row.pk), defaults={'grants': grants, 'version': row.version + 1})
        if kind == 'journals':
            from gravewright.journals.models import Access
            row.access.all().delete()
            Access.objects.bulk_create([Access(journal=row, user_id=k, level=v) for k, v in grants.items() if k != 'default'])
            row.visibility = 'shared' if grants.get('default') in {'read', 'owner'} else 'private'
    row.version += 1
    if not getattr(row, 'native', False):
        row.save()
    who._ownership_cache = {}


def _authorized(campaign_id, user_id, kind, resource_id):
    who = member(campaign_id, user_id)
    if who.role != "gm":
        raise JournalError("Only the GM can change access.", "forbidden")
    if (not isinstance(kind, str) or not isinstance(resource_id, str)
            or len(kind) > 40 or not 1 <= len(resource_id) <= 512):
        raise JournalError("Invalid resource permissions.")
    return who


def state(campaign_id, user_id, kind, resource_id):
    """Read the native GM editor snapshot, including revision, choices and members."""
    who = _authorized(campaign_id, user_id, kind, resource_id)
    kind, row, section = resolve(who, kind, resource_id)
    return snapshot(who, kind, row, section)


@transaction.atomic
def command(campaign_id, user_id, kind, resource_id, payload, request_id):
    """Apply native document/folder/page grants without forcing stale revisions.

    Request UUID retries return the committed result. Bulk folder revisions cover
    their current children, and omitted player keys retain their native meaning.
    """
    campaign_id = identifier(campaign_id)
    if Campaign.objects.select_for_update().filter(pk=campaign_id).first() is None:
        raise JournalError("Document not found.", "not_found")
    who = _authorized(campaign_id, user_id, kind, resource_id)
    rid = identifier(request_id)
    previous = Receipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=rid).first()
    if previous:
        return previous.result
    kind, row, section = resolve(who, kind, resource_id)
    current = snapshot(who, kind, row, section)
    try:
        valid = isinstance(payload, dict) and len(json.dumps(payload, allow_nan=False)) <= 500_000
    except (ValueError, TypeError, RecursionError):
        valid = False
    if not valid:
        raise JournalError("Invalid resource permissions.")
    if type(payload.get("version")) is not type(current["version"]) or payload["version"] != current["version"]:
        raise JournalError("This resource changed. Refresh before editing.", "conflict")
    grants = access.validate(payload.get('permissions'), who, choices=current['levels'], bulk=current['bulk'], roles=current['roles'])
    if current['bulk']:
        reset = payload.get('reset', [])
        if not isinstance(reset, list) or len(reset) > 1000 or any(not isinstance(k, str) or k not in grants or k == 'default' for k in reset):
            raise JournalError('Invalid resource permissions.')
        target_kind = {'actor-folders': 'actors', 'item-folders': 'items', 'journal-folders': 'journals', 'scene-folders': 'scenes',
                       'compendium-folders': 'compendiums'}[kind]
        for child in children(kind, row):
            existing = snapshot(who, target_kind, child)['permissions']
            for k, value in grants.items():
                if value == 'unchanged':
                    continue
                existing[k] = value
            # Missing player keys mean "unchanged" in bulk edits.
            for k in reset:
                existing.pop(k, None)
            store(who, target_kind, child, existing)
    else:
        store(who, kind, row, grants, current['id'])
    from gravewright.realtime.dispatch import changed
    resource = {"actor-folders": "actors", "item-folders": "items", "journal-folders": "journals",
                "scene-folders": "maps", "scenes": "maps", "pages": "journals",
                "compendium-folders": "compendiums"}.get(kind, kind)
    current = snapshot(who, kind, row, section)
    Receipt.objects.create(campaign_id=campaign_id, user_id=user_id, request_id=rid, result=current)
    changed(campaign_id, user_id, resource, "permissions", rid, current)
    return current
