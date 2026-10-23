"""Scene-scoped mind-map bindings delegated by GM-authored blueprints."""

from uuid import uuid4

from django.db.models import Q

from gravewright.campaigns.models import Membership
from gravewright.journals.services import JournalError
from gravewright.table import mindmaps
from gravewright.table.models import MindMap

from .blueprint_clocks import effective_scene_id
from .services import MapError, manage

_BINDING_ERROR = 'Choose a mind map and topic from this campaign and scene.'


def scoped_mindmaps(campaign_id, scene_id):
    return MindMap.objects.filter(campaign_id=campaign_id).filter(
        Q(scene__isnull=True) | Q(scene_id=effective_scene_id(scene_id)))


def validate_mindmap_references(nodes, *, campaign_id=None, scene_id=None):
    """Deleted bindings remain repairable; existing foreign bindings are rejected."""
    identifiers = [node['mindMapId'] for node in nodes]
    allowed_scene = effective_scene_id(scene_id)
    rows = {str(row.pk): row for row in MindMap.objects.filter(pk__in=identifiers)}
    for node in nodes:
        row = rows.get(node['mindMapId'])
        if row is None:
            continue
        if (campaign_id is not None and str(row.campaign_id) != str(campaign_id)
                or row.scene_id is not None and str(row.scene_id) != allowed_scene):
            raise MapError(_BINDING_ERROR)


def catalog(who, scene_id=None, *, all_scenes=False):
    """Only a GM receives binding choices, never notes or linked resources."""
    manage(who)
    rows = MindMap.objects.filter(campaign_id=who.campaign_id) if all_scenes else scoped_mindmaps(who.campaign_id, scene_id)
    return [{'id': str(row.pk), 'name': row.name, 'sceneId': str(row.scene_id) if row.scene_id else None,
             'nodes': [{'id': topic['id'], 'name': topic['label'], 'completed': topic.get('completed', False)}
                       for topic in row.document.get('nodes', [])]} for row in rows]


def control_node(scene, who, node):
    """Apply the specific authored effect without granting general editing access."""
    if who.role == 'streamer':
        raise MapError('Streamers have read-only access.', 'forbidden')
    row = scoped_mindmaps(scene.campaign_id, scene.pk).select_for_update().filter(pk=node['mindMapId']).first()
    topic = next((topic for topic in row.document.get('nodes', []) if topic['id'] == node['nodeId']), None) if row else None
    if topic is None:
        raise MapError(_BINDING_ERROR)
    authorities = Membership.objects.filter(campaign_id=scene.campaign_id, role='gm', user__is_active=True)
    authority = authorities.filter(user_id=who.user_id).first() if who.role == 'gm' else authorities.order_by('id').first()
    if authority is None:
        raise MapError('An active campaign GM is required to update this mind map.', 'forbidden')
    before = topic.get('completed', False)
    desired = not before if node['action'] == 'toggle' else node['action'] == 'complete'
    changed = before != desired
    version = row.version
    if changed:
        try:
            result = mindmaps.public_command(scene.campaign_id, authority.user_id, 'node', {
                'id': str(row.pk), 'version': row.version, 'nodeId': topic['id'],
                'patch': {'completed': desired}}, uuid4())
        except JournalError as error:
            raise MapError(str(error), error.code) from None
        version = result['version']
    return {'mindMapId': str(row.pk), 'nodeId': topic['id'], 'action': node['action'],
            'before': before, 'completed': desired, 'version': version, 'changed': changed}
