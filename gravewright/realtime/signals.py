"""Invalidate cached socket authorizations when access can change (see access.py).

Code that changes these rows without model signals (QuerySet.update) must call
access.revoke itself, as campaigns.streamer.revoke does.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_out
from django.contrib.sessions.models import Session
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from gravewright.campaigns.models import Campaign, Membership, StreamerLink

from . import access


@receiver(post_save, sender=Membership, dispatch_uid="realtime-access-membership-save")
@receiver(post_delete, sender=Membership, dispatch_uid="realtime-access-membership-delete")
def membership_changed(sender, instance, **kwargs):
    # Role changes, removals and bans.
    access.revoke(instance.campaign_id, [instance.user_id])


@receiver(post_save, sender=get_user_model(), dispatch_uid="realtime-access-user-save")
@receiver(post_delete, sender=get_user_model(), dispatch_uid="realtime-access-user-delete")
def user_changed(sender, instance, **kwargs):
    # Deactivation and password changes (which change the session hash).
    access.revoke(user_ids=[instance.pk])


@receiver(post_delete, sender=Session, dispatch_uid="realtime-access-session-delete")
def session_deleted(sender, instance, **kwargs):
    from django.contrib.auth import SESSION_KEY
    try:
        user_id = instance.get_decoded().get(SESSION_KEY)
    except Exception:  # noqa: BLE001 - an unreadable session still ends access
        user_id = None
    access.revoke(user_ids=[user_id])


@receiver(user_logged_out, dispatch_uid="realtime-access-logout")
def logged_out(sender, request, user, **kwargs):
    access.revoke(user_ids=[getattr(user, "pk", None)])


@receiver(post_save, sender=StreamerLink, dispatch_uid="realtime-access-streamer-save")
@receiver(post_delete, sender=StreamerLink, dispatch_uid="realtime-access-streamer-delete")
def streamer_link_changed(sender, instance, **kwargs):
    access.revoke(instance.campaign_id, [instance.guest_id])


@receiver(post_delete, sender=Campaign, dispatch_uid="realtime-access-campaign-delete")
def campaign_deleted(sender, instance, **kwargs):
    access.revoke(instance.pk)
