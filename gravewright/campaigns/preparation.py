"""GM preparation tools for the campaign manager.

Session plans, timeline events and each GM's dashboard are campaign records
that only current campaign GMs can read or change. Content links and usages,
player previews, journal history and pending work are computed from the
native services so they follow the same permissions as the table.
"""
from datetime import date
import json
import re
import uuid

from django.db import transaction
from django.utils import timezone

from gravewright.accounts.services import AuthError
from gravewright.journals.data import normalize_quest_data
from gravewright.journals.models import Journal

from . import management
from .models import Campaign, CampaignEvent, Membership, PreparationBoard, PreparationReceipt, SessionPlan

REFERENCE_KINDS = ('actor', 'item', 'journal', 'scene', 'encounter', 'track', 'playlist')
STEP_KINDS = REFERENCE_KINDS + ('note',)
WIDGETS = ('pins', 'session', 'pending', 'diagnostics', 'events')
SESSION_LIMIT = 200
EVENT_LIMIT = 1000
STEP_LIMIT = 64
CHECKLIST_LIMIT = 64
PIN_LIMIT = 24
LINK_LIMIT = 24
_uuid = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


class PreparationError(AuthError):
    """Validation, conflict and lookup failures reported with HTTP statuses."""
    def __init__(self, message, code='invalid_input', status=400):
        super().__init__(code, status)
        self.message = message

    def __str__(self):
        return self.message


def _text(value, limit, label, required=False):
    if value is None:
        value = ''
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise PreparationError(f'{label} must contain {"1" if required else "0"} to {limit} characters.')
    return value.strip()


def _bool(value, label):
    if type(value) is not bool:
        raise PreparationError(f'{label} must be true or false.')
    return value


def _date(value):
    if value in (None, ''):
        return None
    try:
        if isinstance(value, str):
            return date.fromisoformat(value)
    except ValueError:
        pass
    raise PreparationError('Use a valid calendar date.')


def _row_id(value):
    value = str(value or '').strip()[:40]
    return value if re.fullmatch(r'[A-Za-z0-9_-]{1,40}', value) else uuid.uuid4().hex[:12]


def _models():
    from gravewright.actors.models import Actor
    from gravewright.audio.models import Playlist, Track
    from gravewright.items.models import Item
    from gravewright.maps.models import Scene
    return {'actor': (Actor, 'name'), 'item': (Item, 'name'), 'journal': (Journal, 'title'), 'scene': (Scene, 'name'),
            'encounter': (Scene, 'name'), 'track': (Track, 'name'), 'playlist': (Playlist, 'name')}


def titles(campaign_id, refs):
    """Resolve current titles for references in one query per kind."""
    wanted = {}
    for ref in refs:
        wanted.setdefault(ref['type'], set()).add(ref['id'])
    found = {}
    for kind, ids in wanted.items():
        model, field = _models()[kind]
        for pk, name in model.objects.filter(campaign_id=campaign_id, pk__in=ids).values_list('pk', field):
            found[(kind, str(pk))] = name
    return found


def _ref(raw, campaign_id, kinds=REFERENCE_KINDS):
    if not isinstance(raw, dict) or raw.get('type') not in kinds or not _uuid.fullmatch(str(raw.get('id', '')).lower()):
        raise PreparationError('Choose a campaign document.')
    ref = {'type': raw['type'], 'id': str(raw['id']).lower()}
    model, _ = _models()[ref['type']]
    if not model.objects.filter(campaign_id=campaign_id, pk=ref['id']).exists():
        raise PreparationError('That document is no longer in this campaign.', 'not_found', 404)
    return ref


def _refs(values, campaign_id, limit, label):
    if not isinstance(values, list) or len(values) > limit:
        raise PreparationError(f'Use up to {limit} {label}.')
    unique = {}
    for value in values:
        ref = _ref(value, campaign_id)
        unique[(ref['type'], ref['id'])] = ref
    return list(unique.values())


def _steps(values, campaign_id):
    if not isinstance(values, list) or len(values) > STEP_LIMIT:
        raise PreparationError(f'Use up to {STEP_LIMIT} session steps.')
    steps, seen = [], set()
    for raw in values:
        if not isinstance(raw, dict) or raw.get('kind') not in STEP_KINDS:
            raise PreparationError('Invalid session step.')
        step = {'id': _row_id(raw.get('id')), 'kind': raw['kind'], 'refId': None,
                'label': _text(raw.get('label'), 240, 'Step label', raw['kind'] == 'note'),
                'done': _bool(raw.get('done', False), 'Step completion')}
        if raw['kind'] != 'note':
            step['refId'] = _ref({'type': raw['kind'], 'id': raw.get('refId')}, campaign_id)['id']
        if step['id'] in seen:
            raise PreparationError('Session steps must have unique identifiers.')
        seen.add(step['id'])
        steps.append(step)
    return steps


def _checklist(values, limit=CHECKLIST_LIMIT, label='checklist entries'):
    if not isinstance(values, list) or len(values) > limit:
        raise PreparationError(f'Use up to {limit} {label}.')
    rows, seen = [], set()
    for raw in values:
        if not isinstance(raw, dict):
            raise PreparationError('Invalid checklist entry.')
        row = {'id': _row_id(raw.get('id')), 'text': _text(raw.get('text'), 240, 'Checklist entry', True),
               'done': _bool(raw.get('done', False), 'Checklist completion')}
        if row['id'] in seen:
            raise PreparationError('Checklist entries must have unique identifiers.')
        seen.add(row['id'])
        rows.append(row)
    return rows


def _session(row, names):
    def label(kind, ref_id, fallback):
        return names.get((kind, ref_id), fallback) if ref_id else fallback
    return {'id': str(row.pk), 'title': row.title, 'status': row.status, 'revision': row.revision,
            'scheduledFor': row.scheduled_for.isoformat() if row.scheduled_for else None,
            'steps': [{**step, 'title': label(step['kind'], step['refId'], step['label']),
                       'missing': bool(step['refId']) and (step['kind'], step['refId']) not in names} for step in row.steps],
            'checklist': row.checklist, 'notes': row.notes, 'summary': row.summary, 'pending': row.pending,
            'completedAt': row.completed_at.isoformat() if row.completed_at else None}


def _event(row, names):
    return {'id': str(row.pk), 'title': row.title, 'worldDate': row.world_date, 'position': row.position,
            'date': row.date.isoformat() if row.date else None, 'upcoming': row.upcoming,
            'description': row.description, 'revision': row.revision,
            'links': [{**link, 'title': names.get((link['type'], link['id']), ''),
                       'missing': (link['type'], link['id']) not in names} for link in row.links]}


def _board(who):
    board = PreparationBoard.objects.filter(membership=who).first()
    return board or PreparationBoard(membership=who, pins=[], widgets=list(WIDGETS), revision=0)


def _diagnostics(campaign, user_id):
    """Ask the campaign system for sheet problems through the generic system API."""
    from .system_api import _providers
    from .systems import resolve_system_id
    operation = _providers.get(resolve_system_id(campaign.system), {}).get('preparation.diagnostics')
    if operation is None or operation['effect'] != 'read':
        return {'supported': False, 'issues': []}
    from gravewright.maps.services import MapError
    try:
        result = operation['handler'](campaign.pk, user_id, {}, None, None)
    except (MapError, AuthError) as error:
        return {'supported': True, 'issues': [], 'error': str(error)}
    issues = result.get('issues') if isinstance(result, dict) else None
    return {'supported': True, 'issues': [issue for issue in issues if isinstance(issue, dict)][:100] if isinstance(issues, list) else []}


def _pending(campaign, who, sessions, quests):
    pending = {'unassigned': [], 'blocked': [], 'session': None, 'carried': []}
    status = {str(row.pk): normalize_quest_data(row.data)['status'] for row in quests}
    for row in quests:
        quest = normalize_quest_data(row.data)
        if quest['status'] in {'available', 'active'} and not quest['assignees']:
            pending['unassigned'].append({'id': str(row.pk), 'title': row.title, 'status': quest['status']})
        waiting = [pk for pk in quest['prerequisites'] if status.get(pk) != 'completed']
        if quest['status'] == 'active' and waiting:
            pending['blocked'].append({'id': str(row.pk), 'title': row.title, 'waitingFor': waiting})
    planned = [row for row in sessions if row['status'] == 'planned']
    planned.sort(key=lambda row: (row['scheduledFor'] is None, row['scheduledFor'] or ''))
    if planned:
        current = planned[0]
        pending['session'] = {'id': current['id'], 'title': current['title'], 'scheduledFor': current['scheduledFor'],
                              'steps': [step for step in current['steps'] if not step['done']],
                              'checklist': [row for row in current['checklist'] if not row['done']]}
    completed = [row for row in sessions if row['status'] == 'completed']
    completed.sort(key=lambda row: row['completedAt'] or '', reverse=True)
    if completed:
        pending['carried'] = [dict(row, sessionId=completed[0]['id'], sessionTitle=completed[0]['title'])
                              for row in completed[0]['pending'] if not row['done']]
    return pending


def state(user, campaign_id):
    """Return the preparation records and computed pending work for one GM."""
    campaign, who = management.authorize(user, campaign_id)
    sessions = list(SessionPlan.objects.filter(campaign=campaign))
    events = list(CampaignEvent.objects.filter(campaign=campaign))
    board = _board(who)
    refs = [{'type': step['kind'], 'id': step['refId']} for row in sessions for step in row.steps if step['refId']]
    refs += [link for row in events for link in row.links] + list(board.pins)
    names = titles(campaign.pk, refs)
    session_rows = [_session(row, names) for row in sessions]
    quests = list(Journal.objects.filter(campaign=campaign, type='quest').only('id', 'title', 'data'))
    return {
        'sessions': session_rows,
        'events': [_event(row, names) for row in events],
        'board': {'pins': [{**pin, 'title': names.get((pin['type'], pin['id']), ''),
                            'missing': (pin['type'], pin['id']) not in names} for pin in board.pins],
                  'widgets': board.widgets, 'revision': board.revision},
        'pending': _pending(campaign, who, session_rows, quests),
        'diagnostics': _diagnostics(campaign, user.pk),
    }


def _revision(row, payload):
    if type(payload.get('revision')) is not int or payload['revision'] != row.revision:
        raise PreparationError('This entry changed in another window. Review the current version and try again.', 'conflict', 409)
    row.revision += 1


def _locate(model, campaign, payload):
    value = str(payload.get('id', '')).lower()
    row = model.objects.filter(campaign=campaign, pk=value).first() if _uuid.fullmatch(value) else None
    if row is None:
        raise PreparationError('This entry no longer exists.', 'not_found', 404)
    return row


def _session_fields(row, p, campaign):
    if 'title' in p:
        row.title = _text(p['title'], 120, 'Title', True)
    if 'scheduledFor' in p:
        row.scheduled_for = _date(p['scheduledFor'])
    if 'steps' in p:
        row.steps = _steps(p['steps'], campaign.pk)
    if 'checklist' in p:
        row.checklist = _checklist(p['checklist'])
    if 'notes' in p:
        row.notes = _text(p['notes'], 8000, 'Private notes')


def _event_fields(row, p, campaign):
    if 'title' in p:
        row.title = _text(p['title'], 120, 'Title', True)
    if 'worldDate' in p:
        row.world_date = _text(p['worldDate'], 80, 'In-world date')
    if 'position' in p:
        if type(p['position']) is not int or abs(p['position']) > 10**9:
            raise PreparationError('Invalid timeline position.')
        row.position = p['position']
    if 'date' in p:
        row.date = _date(p['date'])
    if 'upcoming' in p:
        row.upcoming = _bool(p['upcoming'], 'Upcoming')
    if 'description' in p:
        row.description = _text(p['description'], 4000, 'Description')
    if 'links' in p:
        row.links = _refs(p['links'], campaign.pk, LINK_LIMIT, 'linked documents')


def _apply(campaign, who, action, p):
    if action == 'session-create':
        if SessionPlan.objects.filter(campaign=campaign).count() >= SESSION_LIMIT:
            raise PreparationError(f'This campaign already has {SESSION_LIMIT} session plans.')
        row = SessionPlan(campaign=campaign, title='')
        _session_fields(row, {'title': p.get('title'), **{k: v for k, v in p.items() if k != 'title'}}, campaign)
        row.save()
        return {'id': str(row.pk), 'revision': row.revision}
    if action in {'session-update', 'session-finish', 'session-reopen', 'session-delete'}:
        row = _locate(SessionPlan, campaign, p)
        _revision(row, p)
        if action == 'session-delete':
            row.delete()
            return {'id': str(row.pk)}
        if action == 'session-update':
            _session_fields(row, p, campaign)
        elif action == 'session-finish':
            row.summary = _text(p.get('summary'), 8000, 'Session summary')
            row.pending = _checklist(p.get('pending', []), 32, 'pending entries')
            row.status, row.completed_at = SessionPlan.Status.COMPLETED, timezone.now()
        else:
            row.status, row.completed_at = SessionPlan.Status.PLANNED, None
        row.save()
        return {'id': str(row.pk), 'revision': row.revision}
    if action == 'event-create':
        if CampaignEvent.objects.filter(campaign=campaign).count() >= EVENT_LIMIT:
            raise PreparationError(f'This campaign already has {EVENT_LIMIT} timeline events.')
        last = CampaignEvent.objects.filter(campaign=campaign).order_by('-position').values_list('position', flat=True).first()
        row = CampaignEvent(campaign=campaign, title='', position=(last or 0) + 10)
        _event_fields(row, p, campaign)
        if not row.title:
            raise PreparationError('Title must contain 1 to 120 characters.')
        row.save()
        return {'id': str(row.pk), 'revision': row.revision}
    if action in {'event-update', 'event-delete'}:
        row = _locate(CampaignEvent, campaign, p)
        _revision(row, p)
        if action == 'event-delete':
            row.delete()
            return {'id': str(row.pk)}
        _event_fields(row, p, campaign)
        row.save()
        return {'id': str(row.pk), 'revision': row.revision}
    if action == 'board-update':
        board = _board(who)
        if type(p.get('revision')) is not int or p['revision'] != board.revision:
            raise PreparationError('Your dashboard changed in another window. Review it and try again.', 'conflict', 409)
        if 'pins' in p:
            board.pins = _refs(p['pins'], campaign.pk, PIN_LIMIT, 'pinned documents')
        if 'widgets' in p:
            widgets = p['widgets']
            if (not isinstance(widgets, list) or any(not isinstance(widget, str) for widget in widgets)
                    or len(widgets) != len(set(widgets)) or not set(widgets) <= set(WIDGETS)):
                raise PreparationError('Invalid dashboard panels.')
            board.widgets = widgets
        board.revision += 1
        board.save()
        return {'revision': board.revision}
    raise PreparationError('Unknown preparation command.')


def command(user, campaign_id, action, payload, request_id):
    """Apply one GM preparation command once per request UUID."""
    try:
        rid = uuid.UUID(str(request_id))
    except (TypeError, ValueError, AttributeError):
        raise PreparationError('A request identifier is required.') from None
    if not isinstance(action, str) or not isinstance(payload, dict):
        raise PreparationError('Invalid preparation command.')
    with transaction.atomic():
        if not Campaign.objects.select_for_update().filter(pk=campaign_id).exists():
            raise PreparationError('Campaign not found or access denied.', 'not_found', 404)
        campaign, who = management.authorize(user, campaign_id)
        receipt = PreparationReceipt.objects.filter(campaign=campaign, user=user, request_id=rid).first()
        if receipt:
            return receipt.result
        result = _apply(campaign, who, action, payload)
        PreparationReceipt.objects.create(campaign=campaign, user=user, request_id=rid, result=result)
    return result


def _outgoing(data):
    found = re.findall(r'document=(actor|item|journal|scene):([0-9a-f-]{36})', json.dumps(data))
    return list(dict.fromkeys(found))


def references(user, campaign_id, kind, value):
    """List what one document links to and every place that uses it."""
    campaign, _ = management.authorize(user, campaign_id)
    target = _ref({'type': kind, 'id': value}, campaign.pk, ('actor', 'item', 'journal', 'scene'))
    marker = f'document={target["type"]}:{target["id"]}'
    used, links = [], []
    for row in Journal.objects.filter(campaign=campaign).only('id', 'title', 'type', 'data'):
        if str(row.pk) == target['id']:
            links = [{'type': t, 'id': i} for t, i in _outgoing(row.data)]
            if row.type == 'quest':
                quest = normalize_quest_data(row.data)
                links += [{'type': 'actor', 'id': pk, 'via': 'assigned'} for pk in quest['assignees']]
                links += [{'type': 'journal', 'id': pk, 'via': 'prerequisite'} for pk in quest['prerequisites']]
            continue
        if marker in json.dumps(row.data):
            used.append({'type': 'journal', 'id': str(row.pk), 'title': row.title, 'kind': row.type, 'via': 'link'})
        if row.type == 'quest':
            quest = normalize_quest_data(row.data)
            if target['type'] == 'actor' and target['id'] in quest['assignees']:
                used.append({'type': 'journal', 'id': str(row.pk), 'title': row.title, 'kind': 'quest', 'via': 'assigned'})
            if target['type'] == 'journal' and target['id'] in quest['prerequisites']:
                used.append({'type': 'journal', 'id': str(row.pk), 'title': row.title, 'kind': 'quest', 'via': 'prerequisite'})
    if target['type'] == 'journal':
        from gravewright.journals.models import BoardEntry
        from gravewright.maps.models import SceneObject
        for link in BoardEntry.objects.filter(quest_id=target['id'], board__campaign=campaign).select_related('board'):
            used.append({'type': 'journal', 'id': str(link.board_id), 'title': link.board.title, 'kind': 'quest_board', 'via': 'board'})
        for pin in SceneObject.objects.filter(scene__campaign=campaign, kind='journalPins', data__journalId=target['id']).select_related('scene'):
            used.append({'type': 'scene', 'id': str(pin.scene_id), 'title': pin.scene.name, 'kind': 'scene', 'via': 'pin'})
    if target['type'] == 'actor':
        from gravewright.tokens.models import Token
        for scene_id, name in Token.objects.filter(actor_id=target['id'], scene__campaign=campaign).values_list('scene_id', 'scene__name').distinct():
            used.append({'type': 'scene', 'id': str(scene_id), 'title': name, 'kind': 'scene', 'via': 'token'})
    kinds = {target['type']} | ({'encounter'} if target['type'] == 'scene' else set())
    for row in SessionPlan.objects.filter(campaign=campaign):
        if any(step['kind'] in kinds and step['refId'] == target['id'] for step in row.steps):
            used.append({'type': 'session', 'id': str(row.pk), 'title': row.title, 'kind': 'session', 'via': 'session'})
    for row in CampaignEvent.objects.filter(campaign=campaign):
        if any(link['type'] == target['type'] and link['id'] == target['id'] for link in row.links):
            used.append({'type': 'event', 'id': str(row.pk), 'title': row.title, 'kind': 'event', 'via': 'timeline'})
    unique = {(link['type'], link['id'], link.get('via', 'link')): link for link in links}
    names = titles(campaign.pk, list(unique.values()))
    return {'target': {**target, 'title': titles(campaign.pk, [target]).get((target['type'], target['id']), '')},
            'links': [{**link, 'via': link.get('via', 'link'), 'title': names.get((link['type'], link['id']), ''),
                       'missing': (link['type'], link['id']) not in names} for link in unique.values()],
            'usedBy': used}


def view_as(user, campaign_id, member_id):
    """Project the native player-facing state of one participant for their GM."""
    campaign, _ = management.authorize(user, campaign_id)
    target = Membership.objects.select_related('user').filter(
        campaign=campaign, user_id=member_id if _uuid.fullmatch(str(member_id).lower()) else None,
        user__is_active=True).first()
    if target is None:
        raise PreparationError('Participant not found.', 'not_found', 404)
    if target.role != Membership.Role.PLAYER:
        raise PreparationError('Choose a player to preview.')
    from gravewright.actors import services as actors
    from gravewright.journals import services as journals
    from gravewright.maps import services as maps
    from gravewright.table.domain import state as resource_state
    journal_state = journals.state(campaign.pk, target.user_id)
    actor_state = actors.state(campaign.pk, target.user_id)
    items = resource_state(campaign.pk, target.user_id, 'items')
    scenes = maps.state(campaign.pk, target.user_id)
    return {
        'member': {'id': str(target.user_id), 'name': target.user.name, 'role': target.role},
        'journals': journal_state['journals'],
        'folders': journal_state['folders'],
        'actors': [{'id': row['id'], 'name': row['name'], 'canOpen': row['canOpen'], 'canEdit': row['canEdit']}
                   for row in actor_state['actors']],
        'items': [{'id': row['id'], 'name': row.get('name', ''), 'canOpen': row.get('canOpen', True), 'canEdit': row.get('canEdit', False)}
                  for row in items.get('items', [])],
        'scenes': [{'id': row['id'], 'name': row['name']} for row in scenes.get('maps', [])],
    }


def journal_history(user, campaign_id, journal_id):
    from gravewright.journals import history
    campaign, _ = management.authorize(user, campaign_id)
    value = str(journal_id).lower()
    if not _uuid.fullmatch(value):
        raise PreparationError('Invalid document identifier.')
    return {'revisions': history.history(campaign.pk, value)}


def trash(user, campaign_id):
    from gravewright.journals import history
    campaign, _ = management.authorize(user, campaign_id)
    return {'journals': history.trashed(campaign.pk)}


def compare(user, campaign_id, revision_id):
    from gravewright.journals import history
    campaign, _ = management.authorize(user, campaign_id)
    value = str(revision_id).lower()
    result = history.compare(campaign.pk, value) if _uuid.fullmatch(value) else None
    if result is None:
        raise PreparationError('That version is no longer available.', 'not_found', 404)
    return result
