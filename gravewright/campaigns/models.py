"""Campaign ownership, local roles, invitations and expiring streamer access.

GPLv3 only, with the additional permission in LICENSE-EXCEPTION.
"""
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


def cover_path(instance, filename):
    return f'campaigns/{instance.id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class CampaignQuerySet(models.QuerySet):
    def visible_to(self, user):
        return self.filter(memberships__user=user)

    def with_members(self):
        return self.prefetch_related(models.Prefetch(
            'memberships', queryset=Membership.objects.select_related('user').order_by('joined_at', 'id')))


class Campaign(models.Model):
    """Top-level content boundary, shared through campaign memberships."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name='owned_campaigns')
    name = models.CharField(max_length=80)
    description = models.TextField(max_length=500, blank=True)
    system = models.CharField(max_length=120, default='gravewright-pdf-system', blank=True)
    cover = models.ImageField(upload_to=cover_path, blank=True)
    image_url = models.URLField(max_length=2048, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CampaignQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.name


class Membership(models.Model):
    """One campaign-local GM, player or streamer role for a user."""
    class Role(models.TextChoices):
        GM = 'gm', 'Game master'
        PLAYER = 'player', 'Player'
        STREAMER = 'streamer', 'Streamer'

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='campaign_memberships')
    role = models.CharField(max_length=8, choices=Role, default=Role.PLAYER)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'user'], name='campaign_unique_member'),
            models.CheckConstraint(condition=models.Q(role__in=['gm', 'player', 'streamer']), name='campaign_valid_member_role'),
        ]


class AccessCode(models.Model):
    """Hashed invite/removal code; plaintext is returned only when issuing it."""
    class Kind(models.TextChoices):
        INVITE = 'invite', 'Invite'
        REMOVE = 'remove', 'Remove'

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='codes')
    kind = models.CharField(max_length=6, choices=Kind)
    issuer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)

    max_uses = models.PositiveIntegerField(null=True, blank=True)
    use_count = models.PositiveIntegerField(default=0)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'kind'], name='campaign_one_code_per_kind')]


class JoinAttempt(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)


class Onboarding(models.Model):
    membership = models.OneToOneField(Membership, on_delete=models.CASCADE, primary_key=True)
    dismissed = models.BooleanField(default=False)
    player_shown_at = models.DateTimeField(null=True, blank=True)


class StreamerLink(models.Model):
    """Expiring, revocable access linked to a dedicated read-only guest account."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    guest = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='streamer_link')
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
