"""Specific clue effects delegated by GM-authored scene blueprints."""

from uuid import uuid4

from django.db.models import Q

from gravewright.campaigns.models import Membership
from gravewright.journals.services import JournalError
from gravewright.table import clues
from gravewright.table.models import ProgressClue

from .blueprint_clocks import effective_scene_id
from .services import MapError, manage

_BINDING_ERROR = 'Choose a progress clue from this campaign and scene.'


def scoped_clues(campaign_id, scene_id):
    """Use the trusted source-scene override during Builder rehearsals."""
    return ProgressClue.objects.filter(campaign_id=campaign_id).filter(
        Q(scene__isnull=True) | Q(scene_id=effective_scene_id(scene_id)))


def validate_clue_references(identifiers, *, campaign_id=None, scene_id=None):
    """Retain missing portable bindings, but reject existing foreign targets."""
    allowed_scene = effective_scene_id(scene_id)
    for row in ProgressClue.objects.filter(pk__in=identifiers).only('campaign_id', 'scene_id'):
        if (campaign_id is not None and str(row.campaign_id) != str(campaign_id)
                or row.scene_id is not None and str(row.scene_id) != allowed_scene):
            raise MapError(_BINDING_ERROR)


def catalog(who, scene_id=None, *, all_scenes=False):
    """GM-only choices exclude authored content and private notes."""
    manage(who)
    rows = ProgressClue.objects.filter(campaign_id=who.campaign_id) if all_scenes else scoped_clues(who.campaign_id, scene_id)
    return [{'id': str(row.pk), 'name': row.name, 'sceneId': str(row.scene_id) if row.scene_id else None,
             'value': row.value, 'segments': row.segments} for row in rows]


def control_clue(scene, who, node):
    """Apply a delegated effect through the GM-only command boundary.

    The player receives no configuration authority. Native map transactions own
    rollback and retries; only the GM automation log receives this numeric
    outcome, never authored content or private notes.
    """
    if who.role == 'streamer':
        raise MapError('Streamers have read-only access.', 'forbidden')
    clue = scoped_clues(scene.campaign_id, scene.pk).select_for_update().filter(pk=node['clueId']).first()
    if clue is None:
        raise MapError(_BINDING_ERROR)
    authorities = Membership.objects.filter(campaign_id=scene.campaign_id, role='gm', user__is_active=True)
    authority = (authorities.filter(user_id=who.user_id).first() if who.role == 'gm' else authorities.order_by('id').first())
    if authority is None:
        raise MapError('An active campaign GM is required to update this clue.', 'forbidden')
    action, amount = node['action'], node['amount']
    before, before_visibility = clue.value, clue.visibility
    desired = (0 if action == 'reset' else clue.segments if action == 'reveal'
               else before if action == 'hide' else min(clue.segments, amount) if action == 'set'
               else max(0, min(clue.segments, before + (amount if action == 'advance' else -amount))))
    visibility = 'players' if action == 'reveal' else 'gm' if action == 'hide' else before_visibility
    changed = (desired, visibility) != (before, before_visibility)
    if changed:
        payload = {'id': str(clue.pk), 'version': clue.version, 'sceneId': effective_scene_id(scene.pk)}
        if action in ('advance', 'reduce'):
            payload['delta'] = amount if action == 'advance' else -amount
            operation = 'advance'
        elif action in ('reset', 'reveal', 'hide'):
            operation = action
        else:
            operation, payload['value'] = 'update', desired
        try:
            result = clues.public_command(scene.campaign_id, authority.user_id, operation, payload, uuid4())
        except JournalError as error:
            raise MapError(str(error), error.code) from None
        version = result['version']
    else:
        version = clue.version
    return {'clueId': str(clue.pk), 'action': action, 'amount': amount, 'before': before,
            'value': desired, 'beforeVisibility': before_visibility, 'visibility': visibility,
            'version': version, 'changed': changed}
