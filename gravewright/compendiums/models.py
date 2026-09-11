"""Reusable content packs, portable entry bundles and native collection grants."""

import uuid
from django.db import models

class Pack(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    system_id = models.CharField(max_length=120, blank=True)
    shared = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)

class Entry(models.Model):
    """Reusable document snapshot, optionally bundling an archive of dependencies."""
    bundle = models.FileField(upload_to="compendiums/bundles/", blank=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(Pack, related_name='entries', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=16)
    data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)

class EntryAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(Entry, related_name='assets', on_delete=models.CASCADE)
    source_id = models.UUIDField()
    kind = models.CharField(max_length=64)
    name = models.CharField(max_length=240)
    file = models.FileField(upload_to='compendiums/')


class ContentAccess(models.Model):
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    collection = models.CharField(max_length=120)
    pack = models.CharField(max_length=120)
    role = models.CharField(max_length=16, default='player')
    level = models.CharField(max_length=8, default='none')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign','collection','pack','role'], name='content_unique_access')]
