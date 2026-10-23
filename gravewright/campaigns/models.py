"""Campaign ownership, local roles, invitations and expiring streamer access.

GPLv3 only, with the additional permission in LICENSE-EXCEPTION.
"""
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone

from .systems import default_system_id


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
    system = models.CharField(max_length=120, default=default_system_id, blank=True)
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


class SessionPlan(models.Model):
    """GM-only plan for one game session: ordered materials, checklist and wrap-up."""
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        COMPLETED = 'completed', 'Completed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='session_plans')
    title = models.CharField(max_length=120)
    scheduled_for = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status, default=Status.PLANNED)
    # Validated lists of {id, kind, refId, label, done} and {id, text, done}.
    steps = models.JSONField(default=list)
    checklist = models.JSONField(default=list)
    notes = models.TextField(max_length=8000, blank=True)
    summary = models.TextField(max_length=8000, blank=True)
    pending = models.JSONField(default=list)
    completed_at = models.DateTimeField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', 'scheduled_for', 'created_at', 'id']


class CampaignEvent(models.Model):
    """GM timeline entry with an authored in-world date and an optional calendar date."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='timeline_events')
    title = models.CharField(max_length=120)
    world_date = models.CharField(max_length=80, blank=True)
    # Authored chronological position; calendars are not interpreted by the core.
    position = models.IntegerField(default=0)
    date = models.DateField(null=True, blank=True)
    upcoming = models.BooleanField(default=False)
    description = models.TextField(max_length=4000, blank=True)
    links = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['position', 'date', 'created_at', 'id']


class PreparationBoard(models.Model):
    """One GM's own pinned documents and dashboard widget order for a campaign."""
    membership = models.OneToOneField(Membership, on_delete=models.CASCADE, primary_key=True)
    pins = models.JSONField(default=list)
    widgets = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=1)


class PreparationReceipt(models.Model):
    """Preparation command result keyed by campaign, user and request UUID."""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='+')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    request_id = models.UUIDField()
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'user', 'request_id'], name='preparation_unique_command')]
