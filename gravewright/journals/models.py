"""Journal documents, explicit grants, local assets and idempotent command receipts."""

import uuid
from django.conf import settings
from django.db import models


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=80)
    color = models.CharField(max_length=7, default='#c09a5a')

    class Meta:
        ordering = ['name', 'id']


class Journal(models.Model):
    """Versioned document whose type-specific JSON is normalized by services."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=120)
    type = models.CharField(max_length=16, default='diary')
    visibility = models.CharField(max_length=8, default='private')
    data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title', 'id']


class Access(models.Model):
    """Journal grant, combined with visibility and GM status by services."""
    journal = models.ForeignKey(Journal, related_name='access', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.CharField(max_length=8, choices=[('none','None'),('read','Read'),('owner','Owner')])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['journal','user'], name='journal_unique_access')]


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal = models.ForeignKey(Journal, related_name='assets', on_delete=models.CASCADE)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to='journals/%Y/%m/')
    name = models.CharField(max_length=240)
    content_type = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class Receipt(models.Model):
    """Journal command result keyed by campaign, user and request UUID."""
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign','user','request_id'], name='journal_unique_command')]


class BoardEntry(models.Model):
    board = models.ForeignKey(Journal, related_name='board_links', on_delete=models.CASCADE)
    quest = models.ForeignKey(Journal, related_name='quest_links', on_delete=models.CASCADE)
    pinned = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['sort_order', 'id']
        constraints = [models.UniqueConstraint(fields=['board', 'quest'], name='journal_unique_board_quest')]
