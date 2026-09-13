"""Campaign lifecycle, cover files, invitation limits and membership removal.

GPLv3 only, with the additional permission in LICENSE-EXCEPTION.
"""
from datetime import timedelta
import re
import secrets

from django.conf import settings
from django.db import transaction
from django.db.models.fields.files import FieldFile
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac

from gravewright.accounts.services import AuthError
from .models import AccessCode, Campaign, JoinAttempt, Membership

CODE_TTL = 600
JOIN_ALPHABET = 'ABCDEFGHJKMNPQRSTVWXYZ23456789'
REMOVE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def get_campaign(user, campaign_id, *, manage=False):
    """Resolve membership and optionally require a campaign GM, not host ownership."""
    campaign = Campaign.objects.visible_to(user).with_members().filter(pk=campaign_id).first()
    if campaign is None:
        raise AuthError('container_not_found', 404)
    if manage and not any(m.user_id == user.pk and m.role == Membership.Role.GM for m in campaign.memberships.all()):
        raise AuthError('owner_required', 403)
    return campaign


def public_campaign(campaign):
    return {
        'id': str(campaign.id), 'name': campaign.name, 'description': campaign.description,
        'system': campaign.system,
        'image': reverse('campaigns:cover', args=[campaign.id]) if campaign.cover else campaign.image_url or None,
        'participantNames': [m.user.name for m in campaign.memberships.all()
                             if m.role in (Membership.Role.GM, Membership.Role.PLAYER)
                             and m.user.is_active],
        'createdAt': int(campaign.created_at.timestamp() * 1000),
        'updatedAt': int(campaign.updated_at.timestamp() * 1000),
    }


def save_campaign(user, form, *, existing=None):
    """Save a validated campaign form and reconcile uploaded cover file ownership."""
    if existing is None and user.role != 'owner':
        raise AuthError('owner_required', 403)
    old_cover = (Campaign.objects.filter(pk=existing.pk).values_list('cover', flat=True).first() or '') if existing else ''
    campaign = form.save(commit=False)
    if existing is None:
        campaign.owner = user
    image = form.cleaned_data.get('image', '')
    upload = form.cleaned_data.get('cover')
    if isinstance(upload, FieldFile):
        upload = None
    retaining = existing is not None and image == f'/campaigns/{existing.id}/cover'
    if upload:
        campaign.image_url = ''
    elif retaining:
        campaign.image_url = ''
    else:
        campaign.cover = ''
        campaign.image_url = image
    try:
        with transaction.atomic():
            previous_system = None
            if existing is not None:
                # A stale form must never recreate a concurrently removed campaign.
                current = Campaign.objects.select_for_update().filter(pk=existing.pk).first()
                if current is None:
                    raise AuthError('container_not_found', 404)
                old_cover = current.cover.name
                previous_system = current.system
                if retaining and not upload:
                    campaign.cover = current.cover
            campaign.save(force_update=existing is not None)
            if existing is None:
                Membership.objects.create(campaign=campaign, user=user, role=Membership.Role.GM)
            from .catalog import activate_selected_system
            activate_selected_system(campaign, previous_system)
            if old_cover and old_cover != campaign.cover.name:
                transaction.on_commit(lambda: campaign.cover.storage.delete(old_cover))
    except Exception:
        if campaign.cover and campaign.cover.name != old_cover and campaign.cover._committed:
            campaign.cover.storage.delete(campaign.cover.name)
        raise
    return Campaign.objects.with_members().get(pk=campaign.pk)


def digest_code(kind, code):
    if not isinstance(code, str):
        raise ValueError
    if kind == AccessCode.Kind.INVITE:
        normalized = re.sub(r'[\s-]+', '', code).upper()
        if len(normalized) != 12 or any(c not in JOIN_ALPHABET for c in normalized):
            raise ValueError
    else:
        normalized = code.strip().upper()
    return salted_hmac(f'gravewright.campaign.{kind}', normalized, algorithm='sha256').hexdigest()


def issue_code(user, campaign_id, kind, *, expires_in_hours=None, max_uses=None):
    """Replace the campaign's code of this kind and return its one-time plaintext."""
    if kind == AccessCode.Kind.INVITE and not settings.CAMPAIGN_JOIN_CODE_ENABLED:
        raise AuthError('feature_disabled', 403)
    hours=settings.JOIN_CODE_DEFAULT_EXPIRES_HOURS if expires_in_hours is None else expires_in_hours
    if kind==AccessCode.Kind.INVITE:
        if type(hours) is not int or not settings.JOIN_CODE_MIN_EXPIRES_HOURS<=hours<=settings.JOIN_CODE_MAX_EXPIRES_HOURS:
            raise AuthError('invalid_expiration')
        if max_uses is not None and (type(max_uses) is not int or not 1<=max_uses<=settings.JOIN_CODE_MAX_USES_LIMIT):
            raise AuthError('invalid_max_uses')
    alphabet, groups = (JOIN_ALPHABET, 3) if kind == AccessCode.Kind.INVITE else (REMOVE_ALPHABET, 2)
    plaintext = '-'.join(''.join(secrets.choice(alphabet) for _ in range(4)) for _ in range(groups))
    expires = timezone.now() + timedelta(seconds=hours * 3600 if kind == AccessCode.Kind.INVITE else CODE_TTL)
    with transaction.atomic():
        campaign = get_campaign(user, campaign_id, manage=True)
        AccessCode.objects.update_or_create(campaign=campaign, kind=kind, defaults={
            'issuer': user, 'digest': digest_code(kind, plaintext), 'expires_at': expires,
            'max_uses':max_uses if kind==AccessCode.Kind.INVITE else None,'use_count':0,'revoked_at':None})
    return {'code': plaintext, 'expiresAt': int(expires.timestamp() * 1000)}


def join_campaign(user, code, ip):
    """Redeem a live invite with shared attempt limits and counted first-time joins."""
    if not settings.CAMPAIGN_JOIN_CODE_ENABLED:
        raise AuthError('feature_disabled', 403)
    now = timezone.now()
    keys = [salted_hmac('gravewright.join.attempt', part, algorithm='sha256').hexdigest()
            for part in [f'user:{user.pk}', f'ip:{ip}', f'user-ip:{user.pk}:{ip}']]
    try:
        digest = digest_code(AccessCode.Kind.INVITE, code)
    except ValueError:
        digest = ''
    error = None
    campaign_id = None
    with transaction.atomic():
        JoinAttempt.objects.filter(expires_at__lte=now).delete()
        attempts = [JoinAttempt.objects.select_for_update().get_or_create(
            key=key, defaults={'expires_at': now + timedelta(seconds=settings.JOIN_CODE_REDEEM_WINDOW_SECONDS)})[0] for key in keys]
        if any(attempt.count >= settings.JOIN_CODE_REDEEM_MAX_ATTEMPTS for attempt in attempts):
            error = AuthError('too_many_attempts', 429, settings.JOIN_CODE_REDEEM_WINDOW_SECONDS)
        else:
            invitation = AccessCode.objects.select_for_update().filter(
                kind=AccessCode.Kind.INVITE, digest=digest, expires_at__gt=now, revoked_at__isnull=True).first()
            existing=invitation is not None and Membership.objects.filter(campaign_id=invitation.campaign_id,user=user).exists()
            exhausted=invitation is not None and invitation.max_uses is not None and invitation.use_count>=invitation.max_uses
            if invitation is None or (exhausted and not existing):
                for attempt in attempts:
                    attempt.count += 1
                    attempt.save(update_fields=['count'])
                error = AuthError('invalid_or_expired_code', 400)
            else:
                campaign_id = invitation.campaign_id
                _,created=Membership.objects.get_or_create(campaign_id=campaign_id, user=user,
                                                  defaults={'role': Membership.Role.PLAYER})
                if created:
                    invitation.use_count+=1
                    invitation.save(update_fields=['use_count'])
                JoinAttempt.objects.filter(key__in=keys).delete()
    if error:
        raise error
    return get_campaign(user, campaign_id)


def delete_campaign(user, campaign_id, code):
    campaign = get_campaign(user, campaign_id, manage=True)
    try:
        digest = digest_code(AccessCode.Kind.REMOVE, code)
    except ValueError:
        raise AuthError('invalid_code') from None
    with transaction.atomic():
        if not AccessCode.objects.select_for_update().filter(
            campaign=campaign, kind=AccessCode.Kind.REMOVE, issuer=user,
            digest=digest, expires_at__gt=timezone.now()).exists():
            raise AuthError('invalid_or_expired_code')
        cover = campaign.cover.name
        storage = campaign.cover.storage
        campaign.delete()
        if cover:
            transaction.on_commit(lambda: storage.delete(cover))


@transaction.atomic
def code_status(user,campaign_id,*,revoke=False):
    campaign=get_campaign(user,campaign_id,manage=True)
    row=AccessCode.objects.select_for_update().filter(campaign=campaign,kind=AccessCode.Kind.INVITE).first()
    if row is None:return {'active':False}
    if revoke and row.revoked_at is None:
        row.revoked_at=timezone.now();row.save(update_fields=['revoked_at'])
    return {'active':row.revoked_at is None and row.expires_at>timezone.now() and (row.max_uses is None or row.use_count<row.max_uses),
            'expiresAt':int(row.expires_at.timestamp()*1000),'maxUses':row.max_uses,'useCount':row.use_count,
            'revokedAt':int(row.revoked_at.timestamp()*1000) if row.revoked_at else None}


@transaction.atomic
def ban_member(user, campaign_id, target_user_id):
    """Match the original removal contract; existing room sockets lose access."""
    campaign = get_campaign(user, campaign_id, manage=True)
    Campaign.objects.select_for_update().get(pk=campaign.pk)
    from gravewright.journals.services import identifier, JournalError
    try:
        target_id = identifier(target_user_id)
    except JournalError:
        raise AuthError('invalid_input') from None
    target = Membership.objects.filter(campaign=campaign, user_id=target_id).first()
    if target is None:
        raise AuthError('member_not_found', 404)
    if target.role == Membership.Role.GM or target.user_id == user.pk:
        raise AuthError('cannot_ban_gm', 403)
    target.delete()
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    transaction.on_commit(lambda: async_to_sync(get_channel_layer().group_send)(
        f'table.{campaign.pk.hex}', {'type':'room.presence'}))
    return {'removed': str(target_id)}
