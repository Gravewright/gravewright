"""Scene rasters, object layers, broadcasts and shared resource command receipts."""

import uuid
from django.conf import settings
from django.db import models


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    label = models.CharField(max_length=60)
    color = models.CharField(max_length=7, default="#c9a44c")
    tone = models.CharField(max_length=10, default="accent")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label", "id"]


class Scene(models.Model):
    """Raster scene metadata; block_id is the stable chat/scene context identifier."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    soundscape = models.ForeignKey('gravewright_audio.Playlist', null=True, blank=True, on_delete=models.SET_NULL)
    sound_version = models.PositiveIntegerField(default=1)
    block_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    visibility = models.CharField(
        max_length=8, default="players", choices=[("players", "Players"), ("gm", "GM")]
    )
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    tile_size = models.PositiveIntegerField(default=512)
    max_lod = models.PositiveSmallIntegerField(default=0)
    settings = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]


class Tile(models.Model):
    """One authenticated raster tile at a level of detail and grid coordinate."""
    byte_size = models.PositiveIntegerField(default=0)
    scene = models.ForeignKey(Scene, related_name="tiles", on_delete=models.CASCADE)
    lod = models.PositiveSmallIntegerField()
    x = models.PositiveIntegerField()
    y = models.PositiveIntegerField()
    file = models.FileField(upload_to="maps/tiles/%Y/%m/")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scene", "lod", "x", "y"], name="map_unique_tile"
            )
        ]


class Broadcast(models.Model):
    """The single scene selected for a campaign's player and streamer audience."""
    campaign = models.OneToOneField(
        "gravewright_campaigns.Campaign", primary_key=True, on_delete=models.CASCADE
    )
    scene = models.ForeignKey(Scene, null=True, on_delete=models.SET_NULL)


class Receipt(models.Model):
    """Retry result shared by maps, actors, tokens and table.domain resources."""
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    request_id = models.UUIDField()
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "user", "request_id"], name="map_unique_command"
            )
        ]


class SceneState(models.Model):
    """Versioned scene-wide environment state, separate from individual objects."""
    scene = models.OneToOneField(
        Scene, related_name="environment", primary_key=True, on_delete=models.CASCADE
    )
    lighting = models.JSONField(default=dict)
    fog = models.JSONField(default=dict)
    drawings = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)


class SceneObject(models.Model):
    """A typed object such as a wall, light, marker, zone or spatial sound."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey(Scene, related_name="elements", on_delete=models.CASCADE)
    kind = models.CharField(max_length=16)
    data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["scene", "kind"], name="map_objects_kind")]


class MapAsset(models.Model):
    folder = models.ForeignKey(
        "AssetFolder", null=True, blank=True, on_delete=models.SET_NULL
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=240)
    file = models.FileField(upload_to="maps/assets/%Y/%m/")
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class AssetFolder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=80)
