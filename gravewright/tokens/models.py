"""Scene placements of actors, with either shared actor data or a private snapshot."""

import uuid

from django.db import models


class Token(models.Model):
    """A scene actor instance; linked tokens read Actor.data, others read snapshot."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey(
        "gravewright_maps.Scene", on_delete=models.CASCADE, related_name="tokens"
    )
    actor = models.ForeignKey(
        "gravewright_actors.Actor", on_delete=models.CASCADE, related_name="tokens"
    )
    linked = models.BooleanField(default=True)
    snapshot = models.JSONField(default=dict)
    sheet_version = models.PositiveIntegerField(default=1)
    grid_x = models.FloatField(default=0)
    grid_y = models.FloatField(default=0)
    hidden = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    rotation = models.FloatField(default=0)
    elevation = models.FloatField(default=0)
    disposition = models.CharField(max_length=10, default="neutral")
    vision_enabled = models.BooleanField(default=True)
    vision_range = models.FloatField(default=0)
    conditions = models.JSONField(default=list)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
