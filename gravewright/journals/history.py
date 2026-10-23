"""Per-document journal history and the campaign trash.

Snapshots store the state that a command is about to replace. Deleting a
journal keeps its last state, grants, board links and asset files so a GM can
restore that single document without restoring a whole campaign snapshot.
"""
from datetime import timedelta
from pathlib import PurePosixPath
import re
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from . import data as shapes
from .models import Access, Asset, BoardEntry, Folder, Journal, Revision

HISTORY_LIMIT = 50
TRASH_LIMIT = 200
# Rapid saves by the same author collapse into the state before the first one.
COALESCE = timedelta(minutes=5)


def _file_name(value):
    return (isinstance(value, str) and bool(value) and len(value) <= 1024
            and not any(char in value for char in ('\\', ':', '\x00'))
            and not PurePosixPath(value).is_absolute() and '..' not in PurePosixPath(value).parts
            and PurePosixPath(value).as_posix() == value)


def retained_asset_names(value):
    """Return safe storage-relative paths owned by a retained revision record."""
    assets = value.get('assets', []) if isinstance(value, dict) else []
    return {asset['file'] for asset in assets if isinstance(asset, dict) and _file_name(asset.get('file'))} if isinstance(assets, list) else set()


def release_files(names, storage=None):
    """Delete unowned files after commit, rechecking live rows and all campaigns.

    Restoring or importing a revision may transfer a file to another owner in
    the same transaction. Checking ownership at commit protects that new owner.
    """
    names = {name for name in names if _file_name(name)}
    if not names:
        return
    storage = storage or Asset._meta.get_field('file').storage
    def remove():
        unused = names - set(Asset.objects.filter(file__in=names).values_list('file', flat=True))
        if not unused:
            return
        for value in Revision.objects.filter(retained__assets__isnull=False).values_list('retained', flat=True).iterator():
            unused.difference_update(retained_asset_names(value))
            if not unused:
                return
        for name in unused:
            storage.delete(name)
    transaction.on_commit(remove)


def _summary(row):
    return {'id': str(row.id), 'journalId': str(row.journal_id), 'title': row.title, 'type': row.type,
            'version': row.version, 'reason': row.reason, 'createdAt': row.created_at.isoformat(),
            'author': row.author.name if row.author_id and row.author else ''}


def snapshot(journal, who, force=False):
    """Record the current state before an edit, coalescing an author's rapid saves."""
    latest = Revision.objects.filter(campaign_id=journal.campaign_id, journal_id=journal.pk, reason='update').first()
    if latest and latest.version == journal.version:
        return
    if not force and latest and latest.author_id == who.user_id and timezone.now() - latest.created_at < COALESCE:
        return
    Revision.objects.create(campaign_id=journal.campaign_id, journal_id=journal.pk, author_id=who.user_id,
                            reason='update', title=journal.title, type=journal.type, visibility=journal.visibility,
                            folder_id=journal.folder_id, data=journal.data, version=journal.version)
    stale = list(Revision.objects.filter(campaign_id=journal.campaign_id, journal_id=journal.pk, reason='update').values_list('pk', flat=True)[HISTORY_LIMIT:])
    if stale:
        Revision.objects.filter(pk__in=stale).delete()


def trash(journal, who):
    """Move a journal's restorable state to the trash before the row is deleted."""
    assets = list(Asset.objects.filter(journal=journal))
    retained_state = {
        'access': [{'user': str(row.user_id), 'level': row.level} for row in Access.objects.filter(journal=journal)],
        'boards': [{'board': str(row.board_id), 'quest': str(row.quest_id), 'pinned': row.pinned, 'sort': row.sort_order}
                   for row in BoardEntry.objects.filter(board=journal) | BoardEntry.objects.filter(quest=journal)],
        'assets': [{'id': str(row.pk), 'file': row.file.name, 'name': row.name, 'contentType': row.content_type,
                    'uploader': str(row.uploader_id) if row.uploader_id else None} for row in assets],
    }
    Revision.objects.create(campaign_id=journal.campaign_id, journal_id=journal.pk, author_id=who.user_id,
                            reason='delete', title=journal.title, type=journal.type, visibility=journal.visibility,
                            folder_id=journal.folder_id, data=journal.data, version=journal.version,
                            retained=retained_state)
    journal.delete()
    overflow = list(Revision.objects.filter(campaign_id=journal.campaign_id, reason='delete')[TRASH_LIMIT:])
    for row in overflow:
        purge(row)


def purge(row):
    """Permanently remove a trash entry and the files that only it still owns."""
    # Revision deletion signals own file cleanup, including campaign cascades.
    Revision.objects.filter(campaign_id=row.campaign_id, journal_id=row.journal_id).delete()


def history(campaign_id, journal_id):
    rows = Revision.objects.filter(campaign_id=campaign_id, journal_id=journal_id, reason='update').select_related('author')
    return [_summary(row) for row in rows[:HISTORY_LIMIT]]


def trashed(campaign_id):
    rows = Revision.objects.filter(campaign_id=campaign_id, reason='delete').select_related('author')
    return [_summary(row) for row in rows[:TRASH_LIMIT]]


def _text(node, out):
    if isinstance(node, dict):
        if node.get('type') == 'text' and isinstance(node.get('text'), str):
            out[-1] += node['text']
        for child in node.get('content', []) if isinstance(node.get('content'), list) else []:
            _text(child, out)
        if node.get('type') in {'paragraph', 'heading', 'listItem', 'blockquote', 'horizontalRule'}:
            out.append('')
    elif isinstance(node, list):
        for child in node:
            _text(child, out)


def _doc_lines(value):
    out = ['']
    _text((value or {}).get('doc') if isinstance(value, dict) else None, out)
    return [line for line in out if line.strip()]


def readable(title, kind, data):
    """Flatten a journal into labelled text lines for comparing two states."""
    clean = shapes.normalize_data_for(kind, data)
    lines = ['# ' + title]
    if kind == 'diary':
        lines += _doc_lines(clean['content'])
        for page in clean['sections']:
            lines.append('## ' + page['title'] + (' [GM]' if page['audience'] == 'gm' else ''))
            lines += _doc_lines(page['content'])
        for key in ('notes', 'secrets'):
            body = _doc_lines(clean['gm'][key])
            if body:
                lines += ['## GM ' + key] + body
    elif kind == 'quest':
        lines.append('Status: ' + clean['status'])
        if clean['public']['summary']:
            lines.append(clean['public']['summary'])
        lines += _doc_lines(clean['public']['description'])
        lines += ['[%s] %s' % ('x' if row['completed'] else ' ', row['text']) for row in clean['objectives']]
        lines += ['Reward: ' + row['text'] for row in clean['rewards']]
        for key in ('notes', 'secrets'):
            body = _doc_lines(clean['gm'][key])
            if body:
                lines += ['## GM ' + key] + body
    elif kind == 'roll_table':
        lines += ['%s (%s): %s' % (row['name'], row['weight'], re.sub(r'\s+', ' ', row['result'])) for row in clean['entries']]
    return lines


def compare(campaign_id, revision_id):
    """Return the stored state and current state of one revision's journal as text."""
    row = Revision.objects.filter(campaign_id=campaign_id, pk=revision_id).first()
    if row is None:
        return None
    current = Journal.objects.filter(campaign_id=campaign_id, pk=row.journal_id).first()
    return {'revision': {**_summary(row), 'lines': readable(row.title, row.type, row.data)},
            'current': {'title': current.title, 'version': current.version,
                        'lines': readable(current.title, current.type, current.data)} if current else None}


def restore_revision(journal, revision_id, who):
    """Replace the journal's content with an earlier state as one new version."""
    from .services import JournalError, asset_ids, clean_data, identifier, set_visibility
    row = Revision.objects.filter(campaign_id=who.campaign_id, journal_id=journal.pk, reason='update',
                                  pk=identifier(revision_id)).first()
    if row is None or row.type != journal.type:
        raise JournalError('That version is no longer available.', 'not_found')
    _prerequisites(row.data, journal, who)
    data = clean_data(row.data, journal, who)
    requested = set(asset_ids(data))
    owned = {str(asset.pk): asset for asset in Asset.objects.filter(journal=journal)}
    if not requested <= owned.keys():
        raise JournalError('That version uses files that were removed from this document.')
    _available_files([owned[value].file.name for value in requested],
                     'That version uses files that were removed from this document.')
    # Restoring never coalesces, so the replaced state can be restored again.
    snapshot(journal, who, force=True)
    journal.title = row.title
    set_visibility(journal, who, row.visibility, force_default=True)
    journal.data = data


def _prerequisites(data, journal, who):
    if journal.type == 'quest':
        from .types import validate_prerequisites
        validate_prerequisites(data.get('prerequisites', []) if isinstance(data, dict) else None, journal, who)


def _available_files(names, message):
    from .services import JournalError
    storage = Asset._meta.get_field('file').storage
    try:
        available = all(storage.exists(name) for name in names)
    except OSError:
        raise JournalError('Unable to check the files required by this document.') from None
    if not available:
        raise JournalError(message)


def _restore_assets(retained):
    """Preflight every retained asset before creating any restored database row."""
    from .services import JournalError
    invalid = 'This deleted document has invalid retained files.'
    assets = retained.get('assets', []) if isinstance(retained, dict) else None
    if not isinstance(assets, list):
        raise JournalError(invalid)
    normalized, identifiers = [], set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise JournalError(invalid)
        try:
            asset_id = str(UUID(str(asset['id'])))
            uploader = str(UUID(str(asset['uploader']))) if asset.get('uploader') is not None else None
        except (KeyError, TypeError, ValueError, AttributeError):
            raise JournalError(invalid) from None
        if (asset_id in identifiers or not _file_name(asset.get('file'))
                or len(asset['file']) > Asset._meta.get_field('file').max_length
                or not isinstance(asset.get('name'), str) or len(asset['name']) > 240
                or not isinstance(asset.get('contentType'), str) or not 1 <= len(asset['contentType']) <= 64):
            raise JournalError(invalid)
        identifiers.add(asset_id)
        normalized.append({**asset, 'id': asset_id, 'uploader': uploader})
    if Asset.objects.filter(pk__in=identifiers).exists():
        raise JournalError('A retained file identifier is already in use.', 'conflict')
    _available_files([asset['file'] for asset in normalized],
                     'This deleted document uses files that are missing. Restore the files before trying again.')
    return normalized


def restore_deleted(revision_id, who):
    """Recreate a trashed journal with its identifier, grants, links and files."""
    from .services import JournalError, asset_ids, clean_data, identifier
    row = Revision.objects.filter(campaign_id=who.campaign_id, reason='delete', pk=identifier(revision_id)).first()
    if row is None:
        raise JournalError('That document is no longer in the trash.', 'not_found')
    if Journal.objects.filter(pk=row.journal_id).exists():
        raise JournalError('That document already exists.', 'conflict')
    assets = _restore_assets(row.retained)
    folder = Folder.objects.filter(pk=row.folder_id, campaign_id=who.campaign_id).first() if row.folder_id else None
    journal = Journal(id=row.journal_id, campaign_id=who.campaign_id, title=row.title, type=row.type,
                      visibility=row.visibility, folder=folder, data=row.data, version=row.version + 1,
                      creator_id=who.user_id)
    _prerequisites(row.data, journal, who)
    if not set(asset_ids(row.data)) <= {asset['id'] for asset in assets}:
        raise JournalError('This deleted document has invalid retained files.')
    journal.save()
    from gravewright.campaigns.models import Membership
    members = {str(pk) for pk in Membership.objects.filter(campaign_id=who.campaign_id).values_list('user_id', flat=True)}
    Access.objects.bulk_create([Access(journal=journal, user_id=grant['user'], level=grant['level'])
                                for grant in row.retained.get('access', []) if grant['user'] in members])
    for asset in assets:
        Asset.objects.create(id=asset['id'], journal=journal, file=asset['file'], name=asset['name'],
                             content_type=asset['contentType'],
                             uploader_id=asset['uploader'] if asset['uploader'] in members else None)
    journal.data = clean_data(row.data, journal, who)
    journal.save(update_fields=['data'])
    existing = {str(pk) for pk in Journal.objects.filter(campaign_id=who.campaign_id).values_list('pk', flat=True)}
    for link in row.retained.get('boards', []):
        if link['board'] in existing and link['quest'] in existing:
            BoardEntry.objects.get_or_create(board_id=link['board'], quest_id=link['quest'],
                                             defaults={'pinned': link['pinned'], 'sort_order': link['sort']})
    row.delete()
    return journal
