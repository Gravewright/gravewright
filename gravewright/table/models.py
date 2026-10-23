import uuid

from django.conf import settings
from django.db import models


class DocumentAccess(models.Model):
    """Explicit ownership for resources without a native grants field."""
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    kind = models.CharField(max_length=24)
    resource_id = models.CharField(max_length=120)
    grants = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'kind', 'resource_id'], name='table_unique_document_access')]


class LobbyState(models.Model):
    membership = models.OneToOneField('gravewright_campaigns.Membership', primary_key=True, on_delete=models.CASCADE)
    is_ready = models.BooleanField(default=False)
    selected_actor = models.ForeignKey('gravewright_actors.Actor', null=True, blank=True, on_delete=models.SET_NULL)
    assets_state = models.CharField(max_length=10, default='unknown')
    updated_at = models.DateTimeField(auto_now=True)


class ProgressClock(models.Model):
    """A system-independent campaign or scene progress counter."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    scene = models.ForeignKey('gravewright_maps.Scene', null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    segments = models.PositiveSmallIntegerField(default=4)
    value = models.PositiveSmallIntegerField(default=0)
    color = models.CharField(max_length=7, default='#c9a44c')
    visibility = models.CharField(max_length=8, choices=[('gm', 'GM'), ('players', 'Players')], default='gm')
    players_can_edit = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=models.Q(segments__gte=2, segments__lte=24), name='table_clock_segments'),
            models.CheckConstraint(condition=models.Q(value__lte=models.F('segments')), name='table_clock_value'),
            models.CheckConstraint(condition=models.Q(visibility__in=['gm', 'players']), name='table_clock_visibility'),
        ]


class ClockReceipt(models.Model):
    """Clock retries stay separate from other resources' shared command cache."""
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'user', 'request_id'],
                                              name='table_unique_clock_command')]


class ProgressClue(models.Model):
    """A staged discovery whose private notes never belong to public state."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    scene = models.ForeignKey('gravewright_maps.Scene', null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    content = models.TextField(max_length=4000, blank=True, default='')
    gm_notes = models.TextField(max_length=4000, blank=True, default='')
    segments = models.PositiveSmallIntegerField(default=4)
    value = models.PositiveSmallIntegerField(default=0)
    color = models.CharField(max_length=7, default='#c9a44c')
    visibility = models.CharField(max_length=8, choices=[('gm', 'GM'), ('players', 'Players')], default='players')
    pinned = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=models.Q(segments__gte=1, segments__lte=24), name='table_clue_segments'),
            models.CheckConstraint(condition=models.Q(value__lte=models.F('segments')), name='table_clue_value'),
            models.CheckConstraint(condition=models.Q(visibility__in=['gm', 'players']), name='table_clue_visibility'),
        ]


class ClueReceipt(models.Model):
    """Keep private clue snapshots outside every other resource's retry cache."""
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'user', 'request_id'],
                                              name='table_unique_clue_command')]
