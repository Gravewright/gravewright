"""Campaign item documents and folders; available types are supplied by services."""

import uuid
from django.db import models

class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE, related_name='+')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=7, default='#c9a44c')

class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE, related_name='+')
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=80)
    system_id = models.CharField(max_length=120)
    data = models.JSONField(default=dict)
    permissions = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
