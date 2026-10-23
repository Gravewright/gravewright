"""Scoped progress-clock effects delegated by GM-authored scene blueprints."""

from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID, uuid4

from django.db.models import Q

from gravewright.campaigns.models import Membership
from gravewright.journals.services import JournalError
from gravewright.table import clocks
from gravewright.table.models import ProgressClock

from .services import MapError, manage

_CURRENT_SCENE = object()
_clock_scope = ContextVar('blueprint_clock_scope', default=_CURRENT_SCENE)
_BINDING_ERROR = 'Choose a progress clock from this campaign and scene.'


def _scene_id(value):
    return str(UUID(str(value))) if value is not None else None


@contextmanager
def clock_scope(source_scene_id):
    """Bind a trusted Builder rehearsal to its authorized source scene.

    Explicit None means campaign clocks only. An absent context uses the real
    scene. Callers resolve this identifier from a campaign-owned project.
    """
    marker = _clock_scope.set(_scene_id(source_scene_id))
    try:
        yield
    finally:
        _clock_scope.reset(marker)


def effective_scene_id(scene_id):
    source = _clock_scope.get()
    return _scene_id(scene_id) if source is _CURRENT_SCENE else source


def scoped_clocks(campaign_id, scene_id):
    """Return only global clocks and those in the effective local scene."""
    return ProgressClock.objects.filter(campaign_id=campaign_id).filter(
        Q(scene__isnull=True) | Q(scene_id=effective_scene_id(scene_id)))


def validate_clock_references(identifiers, *, campaign_id=None, scene_id=None):
    """Missing targets stay inert; existing foreign bindings cannot be authored."""
    allowed_scene = effective_scene_id(scene_id)
    for row in ProgressClock.objects.filter(pk__in=identifiers).only('campaign_id', 'scene_id'):
        if (campaign_id is not None and str(row.campaign_id) != str(campaign_id)
                or row.scene_id is not None and str(row.scene_id) != allowed_scene):
            raise MapError(_BINDING_ERROR)


def catalog(who, scene_id=None, *, all_scenes=False):
    """GM-only binding choices; never delivered in public scene projections."""
    manage(who)
    rows = ProgressClock.objects.filter(campaign_id=who.campaign_id) if all_scenes else scoped_clocks(who.campaign_id, scene_id)
    return [{'id': str(row.pk), 'name': row.name, 'sceneId': str(row.scene_id) if row.scene_id else None,
             'value': row.value, 'segments': row.segments} for row in rows]


def control_clock(scene, who, node):
    """Execute one specific authored effect through the clock command boundary.

    The binding delegates this operation; it does not grant the interacting
    player clock editing access. The map transaction owns rollback and retries.
    Only the GM automation log receives the bounded numeric outcome.
    """
    if who.role == 'streamer':
        raise MapError('Streamers have read-only access.', 'forbidden')
    clock = scoped_clocks(scene.campaign_id, scene.pk).select_for_update().filter(pk=node['clockId']).first()
    if clock is None:
        raise MapError(_BINDING_ERROR)
    authorities = Membership.objects.filter(campaign_id=scene.campaign_id, role='gm', user__is_active=True)
    authority = (authorities.filter(user_id=who.user_id).first() if who.role == 'gm' else authorities.order_by('id').first())
    if authority is None:
        raise MapError('An active campaign GM is required to update this clock.', 'forbidden')
    action, amount = node['action'], node['amount']
    desired = (0 if action == 'reset' else min(clock.segments, amount) if action == 'set'
               else max(0, min(clock.segments, clock.value + (amount if action == 'advance' else -amount))))
    before = clock.value
    if desired != before:
        payload = {'id': str(clock.pk), 'version': clock.version, 'sceneId': effective_scene_id(scene.pk)}
        if action in ('advance', 'reduce'):
            payload['delta'] = amount if action == 'advance' else -amount
            operation = 'advance'
        elif action == 'reset':
            operation = 'reset'
        else:
            operation, payload['value'] = 'update', desired
        try:
            result = clocks.public_command(scene.campaign_id, authority.user_id, operation, payload, uuid4())
        except JournalError as error:
            raise MapError(str(error), error.code) from None
        version = result['version']
    else:
        version = clock.version
    return {'clockId': str(clock.pk), 'action': action, 'amount': amount, 'before': before,
            'value': desired, 'version': version, 'changed': desired != before}
