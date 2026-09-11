"""Expiring, revocable read-only sessions for public stream links."""
from datetime import timedelta
import secrets
import uuid
from django.contrib.auth import login, logout
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.utils.crypto import salted_hmac
from gravewright.accounts.models import User
from .models import Campaign, Membership, StreamerLink
from .services import get_campaign


def digest(token):
    return salted_hmac('gravewright.streamer', token, algorithm='sha256').hexdigest()


def active(guest_id, campaign_id=None):
    rows=StreamerLink.objects.filter(guest_id=guest_id,expires_at__gt=timezone.now(),revoked_at=None)
    if campaign_id is not None:rows=rows.filter(campaign_id=campaign_id)
    return rows.exists()


@transaction.atomic
def issue(user,campaign_id):
    campaign=get_campaign(user,campaign_id,manage=True)
    Campaign.objects.select_for_update().get(pk=campaign.pk)
    revoke(user,campaign_id)
    token=secrets.token_urlsafe(32)
    guest=User.objects.create_user(email=f'streamer-{uuid.uuid4().hex}@guest.invalid',name='Streamer',password=None)
    Membership.objects.create(campaign=campaign,user=guest,role='streamer')
    row=StreamerLink.objects.create(campaign=campaign,guest=guest,digest=digest(token),expires_at=timezone.now()+timedelta(hours=24))
    return {'url':f'/stream/{token}','expiresAt':row.expires_at.isoformat()}


@transaction.atomic
def revoke(user,campaign_id):
    campaign=get_campaign(user,campaign_id,manage=True)
    Campaign.objects.select_for_update().get(pk=campaign.pk)
    StreamerLink.objects.filter(campaign=campaign,revoked_at=None).update(revoked_at=timezone.now())
    Membership.objects.filter(campaign=campaign,role='streamer').delete()
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    transaction.on_commit(lambda:async_to_sync(get_channel_layer().group_send)(f'table.{campaign.pk.hex}',{'type':'room.presence'}))
    return {'revoked':True}


@require_GET
def consume(request,token):
    row=StreamerLink.objects.select_related('guest').filter(digest=digest(token),expires_at__gt=timezone.now(),revoked_at=None,guest__is_active=True).first() if len(token)<=128 else None
    if row is None:return redirect('/login')
    login(request,row.guest,backend='django.contrib.auth.backends.ModelBackend')
    request.session.set_expiry(row.expires_at)
    return redirect(f'/game/{row.campaign_id}')


class StreamerMiddleware:
    """Guest credentials cannot write through any HTTP app, including future routes."""
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.path=='/logout' or request.path.startswith('/stream/') and request.method=='GET':
            return self.get_response(request)
        if request.user.is_authenticated and StreamerLink.objects.filter(guest_id=request.user.pk).exists():
            if not active(request.user.pk):
                if request.path=='/login':
                    logout(request)
                    return self.get_response(request)
                return JsonResponse({'error':'stream_expired'},status=403)
            if request.method not in ('GET','HEAD','OPTIONS') and request.path!='/logout':
                return JsonResponse({'error':'stream_read_only'},status=403)
        return self.get_response(request)
