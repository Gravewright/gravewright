"""Live session authorization and database leases for connected campaign members.

Redis/Channels delivers events; presence itself is stored in renewable database
rows so multiple sockets and worker failures do not imply permanent attendance."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.models import Session
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from gravewright.campaigns.models import Campaign, Membership
from gravewright.table.views import TEXT
from .models import PresenceConnection


def authorize(session_key, campaign_id, expected_user=None):
    """Read the live session each time: a cached handshake is not authorization."""
    session = Session.objects.filter(session_key=session_key, expire_date__gt=timezone.now()).first()
    if session is None:
        return None
    data = session.get_decoded()
    if data.get(BACKEND_SESSION_KEY) not in settings.AUTHENTICATION_BACKENDS:
        return None
    member = Membership.objects.select_related('user').filter(
        campaign_id=campaign_id, user_id=data.get(SESSION_KEY), user__is_active=True).first()
    if member is None or (expected_user is not None and member.user_id != expected_user):
        return None
    if member.role == 'streamer':
        from gravewright.campaigns.streamer import active
        if not active(member.user_id,campaign_id):return None
    if not constant_time_compare(data.get(HASH_SESSION_KEY, ''), member.user.get_session_auth_hash()):
        return None
    return member


@transaction.atomic
def arrive(member):
    """Create one expiring presence lease for this socket, serialized by campaign."""
    Campaign.objects.select_for_update().get(pk=member.campaign_id)
    return PresenceConnection.objects.create(
        membership=member, expires_at=timezone.now() + timedelta(seconds=settings.GRAVEWRIGHT_PRESENCE_TTL)).pk


def renew(connection_id):
    """Extend a socket lease and report whether any expired leases were removed."""
    now = timezone.now()
    PresenceConnection.objects.filter(pk=connection_id).update(
        expires_at=now + timedelta(seconds=settings.GRAVEWRIGHT_PRESENCE_TTL))
    return PresenceConnection.objects.filter(expires_at__lte=now).delete()[0] > 0


def depart(connection_id):
    PresenceConnection.objects.filter(pk=connection_id).delete()


def roster(campaign_id):
    """Project distinct active members whose socket leases have not expired."""
    members = list(Membership.objects.filter(campaign_id=campaign_id,
        connections__expires_at__gt=timezone.now(), user__is_active=True)
        .select_related('user').distinct().order_by('joined_at', 'id'))
    rows = [{'id': str(m.user_id), 'name': m.user.name, 'role': m.role} for m in members]
    return {'tableId': str(campaign_id), 'members': rows,
            'html': render_to_string('gravewright_table/roster.html',
                                     {'members': rows, 'game': TEXT['game']}, using='jinja2')}
