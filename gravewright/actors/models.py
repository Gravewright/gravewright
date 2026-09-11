"""Campaign actor records, reusable PDF/image assets and actor folder structure."""

import uuid

from django.db import models


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    parent = models.ForeignKey("self", null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    color = models.CharField(max_length=7, default="#c9a44c")


class Actor(models.Model):
    """Character sheet source with separate resource and sheet revision counters."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    folder = models.ForeignKey(Folder, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    data = models.JSONField(default=dict)
    permissions = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    sheet_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Asset(models.Model):
    """Campaign PDF template or actor portrait/token image served after authorization."""
    folder = models.ForeignKey("gravewright_maps.AssetFolder", null=True, blank=True, on_delete=models.SET_NULL)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    actor = models.ForeignKey(
        Actor, null=True, on_delete=models.CASCADE, related_name="assets"
    )
    kind = models.CharField(max_length=8, default="pdf")
    name = models.CharField(max_length=240)
    file = models.FileField(upload_to="actors/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)
