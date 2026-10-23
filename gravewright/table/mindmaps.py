"""Collaborative campaign mind maps with live, recipient-specific resource links.

The stored graph contains only authored text and typed references. Resource names,
URLs and permissions are resolved on reads, and never trusted from a saved graph.
"""

from copy import deepcopy
import json
import math
from uuid import UUID

from django.db.models import Q
from django.utils.crypto import salted_hmac

from gravewright.campaigns.models import Membership
from gravewright.journals.services import member
from gravewright.maps.services import MapError, color, scene, title

from .models import MindMap

MAX_MAPS = 64
MAX_NODES = 500
MAX_EDGES = 1000
MAX_LINKS = 2048
MAX_BYTES = 1024 * 1024
CONFIG_FIELDS = {'name', 'visibility', 'editorIds', 'scopeSceneId'}
CONTEXT_FIELDS = {'sceneId', 'mapId'}
NODE_FIELDS = {'id', 'parentId', 'label', 'notes', 'color', 'x', 'y', 'collapsed', 'completed', 'links'}
PATCH_FIELDS = NODE_FIELDS - {'id'}
DEFAULT_DOCUMENT = {'nodes': [], 'edges': []}
_INVALID = 'Invalid mind map.'
_NOT_FOUND = 'Mind map not found or access denied.'


def _keys(value, allowed, required=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise MapError(_INVALID)


def _uuid(value):
    if not isinstance(value, (str, UUID)):
        raise MapError(_INVALID)
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise MapError(_INVALID) from None


def _text(value, limit, *, required=False):
    if not isinstance(value, str) or len(value) > limit or required and not value.strip():
        raise MapError(_INVALID)
    return value


def _coordinate(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 100000:
        raise MapError(_INVALID)
    return value


def _link_key(row, node_id, index, reference):
    # A link placeholder proves possession of this exact redacted slot;
    # it neither reveals its target nor allows a player to invent hidden links.
    value = json.dumps([str(row.pk), node_id, index, reference], sort_keys=True)
    return salted_hmac('gravewright.mindmap.link', value, algorithm='sha256').hexdigest()


def _reference(value, *, row=None, node_id=None, who=None, resolver=None):
    from .resource_links import validate_reference
    if isinstance(value, dict) and value.get('unavailable') is True:
        _keys(value, {'unavailable', 'key'}, {'unavailable', 'key'})
        if row is None or not isinstance(value['key'], str):
            raise MapError(_INVALID)
        for node in row.document.get('nodes', []):
            if node['id'] != node_id:
                continue
            for index, ref in enumerate(node['links']):
                from hmac import compare_digest
                if compare_digest(value['key'], _link_key(row, node_id, index, ref)):
                    return deepcopy(ref)
        raise MapError(_INVALID)
    if not isinstance(value, dict):
        raise MapError(_INVALID)
    # Display fields are recipient projections, not a way to persist forged names
    # or URLs. Canonical references retain exactly kind, id and optional pageId.
    canonical = {key: value[key] for key in ('kind', 'id', 'pageId') if key in value}
    if set(value) - {'kind', 'id', 'pageId', 'label', 'labelKey', 'name', 'sceneId', 'description', 'descriptionKey', 'url', 'available', 'key', 'ownerReference'}:
        raise MapError(_INVALID)
    result = validate_reference(canonical)
    if who is not None and resolver.resolve(result) is None:
        # An unchanged reference may have become unavailable since it was saved.
        # New references, including guessed foreign IDs, require live read access.
        prior = next((node['links'] for node in (row.document.get('nodes', []) if row else [])
                      if node['id'] == node_id), [])
        if result not in prior:
            raise MapError('Linked resource not found or access denied.', 'not_found')
    return result


def validate_document(value, *, row=None, who=None):
    """Validate bounded graph structure; archives omit membership-based resolution."""
    _keys(value, {'nodes', 'edges'}, {'nodes', 'edges'})
    try:
        size = len(json.dumps(value, allow_nan=False).encode('utf-8'))
    except (TypeError, ValueError, RecursionError):
        raise MapError(_INVALID) from None
    if size > MAX_BYTES:
        raise MapError(_INVALID)
    nodes, edges = value['nodes'], value['edges']
    if not isinstance(nodes, list) or len(nodes) > MAX_NODES or not isinstance(edges, list) or len(edges) > MAX_EDGES:
        raise MapError(_INVALID)
    from .resource_links import Resolver
    resolver = Resolver(who) if who is not None else None
    result, seen, links = [], set(), 0
    for source in nodes:
        _keys(source, NODE_FIELDS, {'id', 'label'})
        node_id = _uuid(source['id'])
        if node_id in seen:
            raise MapError(_INVALID)
        seen.add(node_id)
        refs = source.get('links', [])
        if not isinstance(refs, list) or len(refs) > 16:
            raise MapError(_INVALID)
        links += len(refs)
        if links > MAX_LINKS:
            raise MapError(_INVALID)
        for field in ('collapsed', 'completed'):
            if field in source and type(source[field]) is not bool:
                raise MapError(_INVALID)
        result.append({
            'id': node_id, 'parentId': _uuid(source['parentId']) if source.get('parentId') is not None else None,
            'label': _text(source['label'], 240, required=True),
            'notes': _text(source.get('notes', ''), 8000), 'color': color(source.get('color', '#c9a44c')),
            'x': _coordinate(source.get('x', 0)), 'y': _coordinate(source.get('y', 0)),
            'collapsed': source.get('collapsed', False), 'completed': source.get('completed', False),
            'links': [_reference(ref, row=row, node_id=node_id, who=who, resolver=resolver) for ref in refs],
        })
    parents = {node['id']: node['parentId'] for node in result}
    for node in result:
        cursor, path = node['id'], set()
        while cursor is not None:
            if cursor in path or cursor not in parents:
                raise MapError(_INVALID)
            path.add(cursor)
            cursor = parents[cursor]
    edge_rows, edge_ids, pairs = [], set(), set()
    for edge in edges:
        _keys(edge, {'id', 'from', 'to', 'label'}, {'id', 'from', 'to'})
        eid, start, end = (_uuid(edge[key]) for key in ('id', 'from', 'to'))
        if eid in edge_ids or eid in seen or start not in seen or end not in seen or start == end or (start, end) in pairs:
            raise MapError(_INVALID)
        edge_ids.add(eid)
        pairs.add((start, end))
        edge_rows.append({'id': eid, 'from': start, 'to': end, 'label': _text(edge.get('label', ''), 240)})
    return {'nodes': result, 'edges': edge_rows}


def _gm(who):
    if who.role != 'gm':
        raise MapError('Only the GM can configure mind-map access.', 'forbidden')


def can_read(row, who):
    return who.role == 'gm' or row.visibility == 'players' or (
        who.role == 'player' and str(who.user_id) in row.editor_ids)


def can_edit(row, who):
    return who.role == 'gm' or who.role == 'player' and str(who.user_id) in row.editor_ids


def get(value, who):
    try:
        pk = _uuid(value)
    except MapError:
        raise MapError(_NOT_FOUND, 'not_found') from None
    row = MindMap.objects.filter(pk=pk, campaign_id=who.campaign_id).first()
    if row is None or not can_read(row, who):
        raise MapError(_NOT_FOUND, 'not_found')
    if row.scene_id:
        scene(row.scene_id, who)
    return row


_get = get


def project(row, who, *, resolver=None):
    from .resource_links import Resolver
    graph, resolver = deepcopy(row.document), resolver or Resolver(who)
    for node in graph.get('nodes', []):
        for index, ref in enumerate(node.get('links', [])):
            resolved = resolver.resolve(ref)
            node['links'][index] = {**deepcopy(resolved), 'key': _link_key(row, node['id'], index, ref)} if resolved is not None else {
                'unavailable': True, 'key': _link_key(row, node['id'], index, ref)}
    result = {
        'id': str(row.pk), 'name': row.name, 'visibility': row.visibility,
        'scopeSceneId': str(row.scene_id) if row.scene_id else None,
        'sceneId': str(row.scene_id) if row.scene_id else None,
        'document': graph, 'version': row.version,
        'canEdit': can_edit(row, who), 'canConfigure': who.role == 'gm',
    }
    if who.role == 'gm':
        result['editorIds'] = list(row.editor_ids)
    return result


def state(who, scene_id=None):
    from .resource_links import Resolver
    target = scene(scene_id, who) if scene_id is not None else None
    rows = MindMap.objects.filter(campaign_id=who.campaign_id).select_related('scene')
    if target is not None:
        rows = rows.filter(Q(scene__isnull=True) | Q(scene=target))
    result, resolver = [], Resolver(who)
    for row in rows:
        if not can_read(row, who):
            continue
        if row.scene_id:
            try:
                scene(row.scene_id, who)
            except MapError:
                continue
        result.append(project(row, who, resolver=resolver))
    data = {'mindmaps': result, 'canManage': who.role == 'gm', 'is_gm': who.role == 'gm',
            'sceneId': str(target.pk) if target else None}
    if who.role == 'gm':
        data['editors'] = [{'id': str(row.user_id), 'name': row.user.name}
                           for row in Membership.objects.filter(campaign_id=who.campaign_id, role='player', user__is_active=True)
                           .select_related('user').order_by('user__name', 'user_id')]
    return data


def _editors(value, who):
    if not isinstance(value, list) or len(value) > 128:
        raise MapError(_INVALID)
    ids = [_uuid(item) for item in value]
    if len(set(ids)) != len(ids) or Membership.objects.filter(
            campaign_id=who.campaign_id, role='player', user__is_active=True, user_id__in=ids).count() != len(ids):
        raise MapError(_INVALID)
    return ids


def _context(row, payload, who):
    ids = [_uuid(payload[key]) if payload[key] is not None else None
           for key in ('sceneId', 'mapId') if key in payload]
    if len(ids) == 2 and ids[0] != ids[1]:
        raise MapError(_INVALID)
    target = scene(ids[0], who) if ids and ids[0] else None
    if row is not None and ids and row.scene_id and (target is None or row.scene_id != target.pk):
        raise MapError(_NOT_FOUND, 'not_found')


def _result(row, who):
    return {'id': str(row.pk), 'version': row.version, 'mindmap': project(row, who)}


def command(who, action, payload):
    if who.role == 'streamer':
        raise MapError('Streamers have read-only access.', 'forbidden')
    allowed = {
        'create': CONFIG_FIELDS | CONTEXT_FIELDS | {'document'},
        'update': CONFIG_FIELDS | CONTEXT_FIELDS | {'id', 'version', 'document'},
        'node': CONTEXT_FIELDS | {'id', 'version', 'nodeId', 'patch'},
        'delete': CONTEXT_FIELDS | {'id', 'version'},
    }
    if not isinstance(action, str) or action not in allowed:
        raise MapError('Invalid mind-map action.')
    required = {'name'} if action == 'create' else {'id', 'version'}
    if action == 'node':
        required |= {'nodeId', 'patch'}
    _keys(payload, allowed[action], required)
    if action == 'create':
        _gm(who)
        if MindMap.objects.filter(campaign_id=who.campaign_id).count() >= MAX_MAPS:
            raise MapError('A campaign can contain at most 64 mind maps.')
        row = MindMap(campaign_id=who.campaign_id, name=title(payload['name']), document=deepcopy(DEFAULT_DOCUMENT))
    else:
        row = get(payload['id'], who)
        if not can_edit(row, who):
            raise MapError('You cannot edit this mind map.', 'forbidden')
        from .domain import version
        version(row, payload)
    _context(row if action != 'create' else None, payload, who)
    if action == 'delete':
        _gm(who)
        result = {'id': str(row.pk)}
        row.delete()
        return result
    if CONFIG_FIELDS.intersection(payload) - {'name'}:
        _gm(who)
    if 'name' in payload:
        row.name = title(payload['name'])
    if 'visibility' in payload:
        if payload['visibility'] not in ('gm', 'players'):
            raise MapError(_INVALID)
        row.visibility = payload['visibility']
    if 'editorIds' in payload:
        row.editor_ids = _editors(payload['editorIds'], who)
    if 'scopeSceneId' in payload:
        row.scene = scene(_uuid(payload['scopeSceneId']), who) if payload['scopeSceneId'] is not None else None
    if 'document' in payload:
        row.document = validate_document(payload['document'], row=row if action != 'create' else None, who=who)
    if action == 'node':
        node_id = _uuid(payload['nodeId'])
        _keys(payload['patch'], PATCH_FIELDS)
        if not payload['patch']:
            raise MapError(_INVALID)
        graph = deepcopy(row.document)
        node = next((node for node in graph['nodes'] if node['id'] == node_id), None)
        if node is None:
            raise MapError('Mind-map topic not found.', 'not_found')
        node.update(payload['patch'])
        row.document = validate_document(graph, row=row, who=who)
    if action != 'create':
        row.version += 1
    row.save()
    return _result(row, who)


def validate_replay(who, action, payload, result):
    """Recheck access and reproject links rather than leaking stale receipt data."""
    if not isinstance(result, dict):
        raise MapError(_INVALID)
    if 'mindmap' not in result:
        _gm(who)
        return
    row = get(result['id'], who)
    _context(row, payload, who)
    if not can_edit(row, who):
        raise MapError('You cannot edit this mind map.', 'forbidden')
    if action in ('create', 'delete') or CONFIG_FIELDS.intersection(payload) - {'name'}:
        _gm(who)


def replay_result(who, result):
    # Receipt versions retain exactly-once semantics; names and linked resource
    # access are a fresh projection. The current row is returned for editing.
    return _result(get(result['id'], who), who) if 'mindmap' in result else result


def public_state(campaign_id, user_id, scene_id=None):
    return state(member(campaign_id, user_id), scene_id)


def public_read(campaign_id, user_id, mindmap_id, scene_id=None):
    who = member(campaign_id, user_id)
    row = get(mindmap_id, who)
    if scene_id is not None:
        _context(row, {'sceneId': scene_id}, who)
    return project(row, who)


def public_resources(campaign_id, user_id, **options):
    from .resource_links import catalog
    return catalog(member(campaign_id, user_id), **options)


def public_resolve(campaign_id, user_id, reference):
    from .resource_links import resolve, validate_reference
    return resolve(member(campaign_id, user_id), validate_reference(reference))


def public_command(campaign_id, user_id, action, data, request_id):
    from .domain import command as execute
    return execute(campaign_id, user_id, 'mindmaps', action, data, request_id)
