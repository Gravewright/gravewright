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
    return authorization(session_key, campaign_id, expected_user)[0]


def authorization(session_key, campaign_id, expected_user=None):
    """Return ``(member, valid_until)`` from the live session, or ``(None, None)``.

    ``valid_until`` is the earliest of the session expiry and, for streamers, the
    link expiry: a socket may reuse this result briefly, never beyond that moment.
    """
    session = Session.objects.filter(session_key=session_key, expire_date__gt=timezone.now()).first()
    if session is None:
        return None, None
    data = session.get_decoded()
    if data.get(BACKEND_SESSION_KEY) not in settings.AUTHENTICATION_BACKENDS:
        return None, None
    member = Membership.objects.select_related('user').filter(
        campaign_id=campaign_id, user_id=data.get(SESSION_KEY), user__is_active=True).first()
    if member is None or (expected_user is not None and member.user_id != expected_user):
        return None, None
    valid_until = session.expire_date
    if member.role == 'streamer':
        from gravewright.campaigns.models import StreamerLink
        link = StreamerLink.objects.filter(guest_id=member.user_id, campaign_id=campaign_id,
                                           expires_at__gt=timezone.now(), revoked_at=None
                                           ).order_by('-expires_at').values_list('expires_at', flat=True).first()
        if link is None:
            return None, None
        valid_until = min(valid_until, link)
    if not constant_time_compare(data.get(HASH_SESSION_KEY, ''), member.user.get_session_auth_hash()):
        return None, None
    return member, valid_until


@transaction.atomic
def arrive(member):
    """Create one expiring presence lease for this socket, serialized by campaign."""
    Campaign.objects.select_for_update().get(pk=member.campaign_id)
    return PresenceConnection.objects.create(
        membership=member, expires_at=timezone.now() + timedelta(seconds=settings.GRAVEWRIGHT_PRESENCE_TTL)).pk


def renew(connection_id, membership_id=None):
    """Extend a socket lease; True when it had to be recreated.

    Another socket's cleanup can remove a lease whose renewal was delayed; a live
    socket recreates it with the same id instead of disappearing from the roster.
    """
    expires_at = timezone.now() + timedelta(seconds=settings.GRAVEWRIGHT_PRESENCE_TTL)
    if PresenceConnection.objects.filter(pk=connection_id).update(expires_at=expires_at):
        return False
    if membership_id is None:
        return False
    PresenceConnection.objects.get_or_create(pk=connection_id, defaults={
        'membership_id': membership_id, 'expires_at': expires_at})
    return True


def remove_expired():
    """Delete expired leases (after worker failures); True when any were removed.

    A read first, so the common case takes no write lock.
    """
    expired = PresenceConnection.objects.filter(expires_at__lte=timezone.now())
    if not expired.exists():
        return False
    return expired.delete()[0] > 0


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
