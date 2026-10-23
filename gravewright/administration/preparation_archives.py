"""Portable GM preparation and retained journal history in campaign archives."""

from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import PurePosixPath
import re
from uuid import UUID, uuid4

from gravewright.accounts.services import AuthError

SESSION = 'gravewright_campaigns.sessionplan'
EVENT = 'gravewright_campaigns.campaignevent'
HISTORY = 'gravewright_journals.revision'
LABELS = {SESSION, EVENT, HISTORY}
REF_MODELS = {'actor': 'gravewright_actors.actor', 'item': 'gravewright_items.item',
              'journal': 'gravewright_journals.journal', 'scene': 'gravewright_maps.scene',
              'encounter': 'gravewright_maps.scene', 'track': 'gravewright_audio.track',
              'playlist': 'gravewright_audio.playlist'}
WIDGETS = {'pins', 'session', 'pending', 'diagnostics', 'events'}


def _require(condition):
    if not condition:
        raise AuthError('invalid_archive')


def _uuid(value):
    _require(isinstance(value, str))
    try:
        _require(str(UUID(value)) == value.lower())
    except (ValueError, AttributeError):
        raise AuthError('invalid_archive') from None
    return value


def _text(value, limit, required=False):
    _require(isinstance(value, str) and len(value) <= limit and (not required or bool(value.strip())))


def _integer(value, minimum=1, maximum=2**31 - 1):
    _require(type(value) is int and minimum <= value <= maximum)


def _date(value, timestamp=False):
    if value is None:
        return
    _require(isinstance(value, str))
    try:
        (datetime if timestamp else date).fromisoformat(value)
    except ValueError:
        raise AuthError('invalid_archive') from None


def _list(value, limit):
    _require(isinstance(value, list) and len(value) <= limit)
    return value


def _refs(value, limit=24):
    for ref in _list(value, limit):
        _require(isinstance(ref, dict) and set(ref) == {'type', 'id'})
        _require(isinstance(ref['type'], str) and ref['type'] in REF_MODELS)
        _uuid(ref['id'])


def _checklist(value, limit):
    seen = set()
    for row in _list(value, limit):
        _require(isinstance(row, dict) and set(row) == {'id', 'text', 'done'})
        _text(row['id'], 40, True)
        _require(re.fullmatch(r'[A-Za-z0-9_-]{1,40}', row['id']) is not None
                 and row['id'] not in seen and type(row['done']) is bool)
        seen.add(row['id'])
        _text(row['text'], 240, True)


def _path(value):
    _text(value, 1024, True)
    path = PurePosixPath(value)
    _require(not path.is_absolute() and '..' not in path.parts and '\\' not in value and ':' not in value)


def validate_record(record):
    """Reject malformed counters, text, lists and retained-file metadata before writes."""
    kind, fields = record['model'], record['fields']
    if kind not in LABELS:
        return
    _uuid(str(record['pk']))
    _uuid(fields['campaign'])
    _text(fields['title'], 120, True)
    if kind == SESSION:
        _integer(fields['revision'])
        _date(fields['scheduled_for'])
        _date(fields['completed_at'], True)
        _require(fields['status'] in ('planned', 'completed'))
        for name in ('notes', 'summary'):
            _text(fields[name], 8000)
        _checklist(fields['checklist'], 64)
        _checklist(fields['pending'], 32)
        seen = set()
        for step in _list(fields['steps'], 64):
            _require(isinstance(step, dict) and set(step) == {'id', 'kind', 'refId', 'label', 'done'})
            _text(step['id'], 40, True)
            _require(re.fullmatch(r'[A-Za-z0-9_-]{1,40}', step['id']) is not None
                     and step['id'] not in seen and type(step['done']) is bool)
            seen.add(step['id'])
            _require(isinstance(step['kind'], str) and step['kind'] in (*REF_MODELS, 'note'))
            _text(step['label'], 240, step['kind'] == 'note')
            if step['kind'] == 'note':
                _require(step['refId'] is None)
            else:
                _uuid(step['refId'])
    elif kind == EVENT:
        _integer(fields['revision'])
        _integer(fields['position'], -10**9, 10**9)
        _text(fields['world_date'], 80)
        _text(fields['description'], 4000)
        _date(fields['date'])
        _require(type(fields['upcoming']) is bool)
        _refs(fields['links'])
    else:
        _uuid(fields['journal_id'])
        _integer(fields['version'])
        _require(fields['reason'] in ('update', 'delete'))
        _require(fields['type'] in ('diary', 'quest', 'quest_board', 'roll_table'))
        _require(fields['visibility'] in ('private', 'shared', 'handout'))
        if fields['folder_id'] is not None:
            _uuid(fields['folder_id'])
        if fields['author'] is not None:
            _uuid(fields['author'])
        _require(isinstance(fields['data'], dict) and len(json.dumps(fields['data'], allow_nan=False)) <= 512_000)
        retained = fields['retained']
        _require(isinstance(retained, dict) and not set(retained) - {'access', 'boards', 'assets'})
        for grant in _list(retained.get('access', []), 1000):
            _require(isinstance(grant, dict) and set(grant) == {'user', 'level'})
            _uuid(grant['user'])
            _require(grant['level'] in ('none', 'limited', 'read', 'owner'))
        for link in _list(retained.get('boards', []), 10000):
            _require(isinstance(link, dict) and set(link) == {'board', 'quest', 'pinned', 'sort'})
            _uuid(link['board']); _uuid(link['quest'])
            _require(type(link['pinned']) is bool)
            _integer(link['sort'], 0)
        seen = set()
        for asset in _list(retained.get('assets', []), 1000):
            _require(isinstance(asset, dict) and set(asset) == {'id', 'file', 'name', 'contentType', 'uploader'})
            _uuid(asset['id'])
            _require(asset['id'] not in seen)
            seen.add(asset['id'])
            _path(asset['file'])
            _text(asset['name'], 240)
            _text(asset['contentType'], 64)
            if asset['uploader'] is not None:
                _uuid(asset['uploader'])
    _date(fields['created_at'], True)
    if kind == SESSION:
        _date(fields['updated_at'], True)


def validate_payload(payload):
    metadata = payload.get('preparation')
    own = [row for row in payload['records'] if row['model'] in LABELS]
    if 'preparation' not in payload:
        _require(not own)
        return
    _require(isinstance(metadata, dict) and set(metadata) == {'version', 'dashboards'})
    _integer(metadata['version'], 1, 1)
    users = set()
    for board in _list(metadata['dashboards'], 1000):
        _require(isinstance(board, dict) and set(board) == {'userId', 'pins', 'widgets', 'revision'})
        _uuid(board['userId'])
        _require(board['userId'] not in users)
        users.add(board['userId'])
        _refs(board['pins'])
        widgets = _list(board['widgets'], 5)
        _require(all(isinstance(widget, str) for widget in widgets))
        _require(len(set(widgets)) == len(widgets) and set(widgets) <= WIDGETS)
        _integer(board['revision'])
    for label, limit in ((SESSION, 200), (EVENT, 1000)):
        _require(sum(row['model'] == label for row in own) <= limit)
    history_counts = {}
    deleted = set()
    live = {str(row['pk']) for row in payload['records'] if row['model'] == 'gravewright_journals.journal'}
    asset_owners = {str(row['pk']): str(row['fields']['journal']) for row in payload['records']
                    if row['model'] == 'gravewright_journals.asset'}
    for row in own:
        validate_record(row)
        if row['model'] == HISTORY:
            fields = row['fields']
            _require(str(fields['campaign']) == str(payload['campaign']['id']))
            for asset in fields['retained'].get('assets', []):
                _require(asset['file'] in payload['files'])
                owner = asset_owners.setdefault(asset['id'], fields['journal_id'])
                _require(owner == fields['journal_id'])
            if fields['reason'] == 'delete':
                _require(fields['journal_id'] not in deleted and fields['journal_id'] not in live)
                deleted.add(fields['journal_id'])
            else:
                history_counts[fields['journal_id']] = history_counts.get(fields['journal_id'], 0) + 1
    _require(len(deleted) <= 200 and all(count <= 50 for count in history_counts.values()))


def validate_import_limits(campaign, payload):
    from gravewright.campaigns.models import SessionPlan, CampaignEvent
    from gravewright.journals.models import Revision
    for label, model, limit, filters in ((SESSION, SessionPlan, 200, {}), (EVENT, CampaignEvent, 1000, {}),
                                          (HISTORY, Revision, 200, {'reason': 'delete'})):
        incoming = sum(row['model'] == label and (label != HISTORY or row['fields']['reason'] == 'delete')
                       for row in payload['records'])
        if incoming:
            _require(model.objects.filter(campaign=campaign, **filters).count() + incoming <= limit)


def export_metadata(campaign, selected):
    from gravewright.campaigns.models import PreparationBoard
    boards = PreparationBoard.objects.filter(membership__campaign=campaign, membership__role='gm').select_related('membership')
    rows = [{'userId': str(board.membership.user_id), 'pins': board.pins, 'widgets': board.widgets, 'revision': board.revision}
            for board in boards] if selected['preparation'] else []
    rows.sort(key=lambda row: (row['userId'] != str(campaign.owner_id), row['userId']))
    return {'version': 1, 'dashboards': rows}


def export_record(record, *, snapshot):
    if record['model'] in LABELS:
        for name in ('created_at', 'updated_at'):
            value = record['fields'].get(name)
            if isinstance(value, datetime):
                record['fields'][name] = value.isoformat()
    if record['model'] == HISTORY and not snapshot:
        fields = record['fields'] = deepcopy(record['fields'])
        fields['author'] = None
        retained = fields['retained']
        retained['access'] = []
        retained.pop('policies', None)
        for asset in retained.get('assets', []):
            asset['uploader'] = None


def retained_files(record):
    return record['fields'].get('retained', {}).get('assets', []) if record['model'] == HISTORY else []


def clear_preparation(campaign):
    from gravewright.campaigns.models import PreparationBoard
    PreparationBoard.objects.filter(membership__campaign=campaign).delete()


def validate_imported_quests(campaign, model_ids):
    from types import SimpleNamespace
    from gravewright.journals.models import Journal
    from gravewright.journals.services import JournalError
    from gravewright.journals.types import validate_prerequisites
    imported = [pk for (label, _), pk in model_ids.items() if label == 'gravewright_journals.journal']
    who = SimpleNamespace(campaign_id=campaign.pk)
    try:
        for journal in Journal.objects.filter(campaign=campaign, type='quest', pk__in=imported):
            validate_prerequisites(journal.data.get('prerequisites', []), journal, who, strict=False)
    except JournalError:
        raise AuthError('invalid_archive') from None


def import_record(record, model_ids, inert, paths, identifiers, *, snapshot):
    """Remap typed references only; authored names, notes and summaries stay exact."""
    fields = deepcopy(record['fields'])
    def binding(label, value):
        if value is None:
            return None
        key = (label, str(value))
        return str(model_ids.get(key) or inert.setdefault(key, str(value) if snapshot else str(uuid4())))
    def refs(rows):
        return [{**row, 'id': binding(REF_MODELS[row['type']], row['id'])} for row in rows]
    if record['model'] == SESSION:
        fields['steps'] = [{**step, 'refId': binding(REF_MODELS[step['kind']], step['refId'])}
                           if step['kind'] != 'note' else step for step in fields['steps']]
    elif record['model'] == EVENT:
        fields['links'] = refs(fields['links'])
    else:
        fields['journal_id'] = binding('gravewright_journals.journal', fields['journal_id'])
        fields['folder_id'] = binding('gravewright_journals.folder', fields['folder_id'])
        retained = fields['retained']
        asset_ids = {}
        for asset in retained.get('assets', []):
            old_id = asset['id']
            asset['id'] = binding('gravewright_journals.asset', old_id)
            asset_ids[old_id] = asset['id']
            _require(asset['file'] in paths)
            asset['file'] = paths.get(asset['file'], '')
        for link in retained.get('boards', []):
            link['board'] = binding('gravewright_journals.journal', link['board'])
            link['quest'] = binding('gravewright_journals.journal', link['quest'])
        # Rich-text hyperlinks and asset fields are references; leaf text is authored.
        from .archives import rewrite
        references = {**identifiers, **{old: str(new) for (label, old), new in inert.items()}, **asset_ids}
        def reference(label, value):
            if not value:
                return value
            references[value] = binding(label, value)
            return references[value]
        def document(value):
            if isinstance(value, dict):
                result = {}
                for key, child in value.items():
                    if key == 'assetId' and isinstance(child, str):
                        result[key] = reference('gravewright_journals.asset', child)
                    elif key in ('assignees', 'prerequisites') and isinstance(child, list):
                        label = 'gravewright_actors.actor' if key == 'assignees' else 'gravewright_journals.journal'
                        result[key] = [reference(label, item) for item in child]
                    elif key in ('href', 'src') and isinstance(child, str):
                        for ref_kind, old in re.findall(r'document=(actor|item|journal|scene):([0-9a-f-]{36})', child):
                            reference(REF_MODELS[ref_kind], old)
                        for old in re.findall(r'/journal/asset/([0-9a-f-]{36})', child):
                            reference('gravewright_journals.asset', old)
                        result[key] = rewrite(child, references, paths)
                    else:
                        result[key] = document(child)
                return result
            if isinstance(value, list):
                return [document(child) for child in value]
            return value
        fields['data'] = document(fields['data'])
        if not snapshot:
            fields['author'] = None
            retained['access'] = []
            retained.pop('policies', None)
            for asset in retained.get('assets', []):
                asset['uploader'] = None
    return fields


def import_dashboards(payload, campaign, user, model_ids, inert, *, snapshot, merge):
    from gravewright.campaigns.models import Membership, PreparationBoard
    rows = payload.get('preparation', {}).get('dashboards', [])
    if not rows:
        return
    if snapshot:
        selected = [(row, Membership.objects.filter(campaign=campaign, user_id=row['userId'], role='gm').first()) for row in rows]
    else:
        source = next((row for row in rows if row['userId'] == str(user.pk)), rows[0])
        selected = [(source, Membership.objects.filter(campaign=campaign, user=user, role='gm').first())]
    for source, member in selected:
        if member is None or merge and PreparationBoard.objects.filter(membership=member).exists():
            continue
        pins = []
        for pin in source['pins']:
            key = (REF_MODELS[pin['type']], pin['id'])
            identifier = model_ids.get(key) or inert.setdefault(key, pin['id'] if snapshot else str(uuid4()))
            pins.append({**pin, 'id': str(identifier)})
        PreparationBoard.objects.update_or_create(membership=member, defaults={
            'pins': pins, 'widgets': source['widgets'], 'revision': source['revision']})
