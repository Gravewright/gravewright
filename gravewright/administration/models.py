"""Host preferences, campaign snapshot archives and administrative audit records."""

import uuid

from django.conf import settings
from django.db import models


class HostSettings(models.Model):
    """Host configuration accessed through the conventional singleton primary key 1."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    channel = models.CharField(max_length=10, default="stable")
    update_status = models.JSONField(default=dict)
    app_name = models.CharField(max_length=80, blank=True)
    default_locale = models.CharField(max_length=16, blank=True)
    packages_channel = models.CharField(max_length=10, default="stable")
    channels_linked = models.BooleanField(default=True)
    privacy = models.JSONField(default=dict)


class Snapshot(models.Model):
    """Stored campaign archive and digest for preview, download and restoration."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, max_length=1000)
    archive = models.FileField(upload_to="backups/%Y/%m/")
    digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=80)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
