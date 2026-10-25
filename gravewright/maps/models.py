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


class SceneNavigation(models.Model):
    """A member's private scene selection; null follows the campaign broadcast."""
    membership = models.OneToOneField(
        "gravewright_campaigns.Membership", primary_key=True, on_delete=models.CASCADE
    )
    scene = models.ForeignKey(Scene, null=True, blank=True, on_delete=models.SET_NULL)


class SceneAssignment(models.Model):
    """A GM-assigned player destination; absence follows the campaign broadcast."""
    membership = models.OneToOneField(
        "gravewright_campaigns.Membership", primary_key=True, on_delete=models.CASCADE,
    )
    scene = models.ForeignKey(Scene, on_delete=models.CASCADE)


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


class AutomationRun(models.Model):
    """A GM-only record of one object blueprint execution, kept per scene.

    Rows are diagnostics, not campaign content: archives do not export them and
    each scene keeps only its most recent runs. ``door_id`` is not a foreign key
    so a run stays readable after its door is deleted.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey(Scene, related_name="automation_runs", on_delete=models.CASCADE)
    door_id = models.UUIDField()
    outcome = models.CharField(max_length=16)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["scene", "-created_at"], name="map_automation_recent")]


class AutomationDelay(models.Model):
    """A private durable wait or named timer; never exported as campaign content."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey(Scene, related_name="automation_delays", on_delete=models.CASCADE)
    element = models.ForeignKey(SceneObject, related_name="automation_delays", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    chain_id = models.UUIDField()
    request_id = models.UUIDField()
    role = models.CharField(max_length=8)
    kind = models.CharField(max_length=8, default="delay")
    name = models.CharField(max_length=64, blank=True)
    event = models.CharField(max_length=80)
    node_id = models.CharField(max_length=64)
    graph_hash = models.CharField(max_length=64)
    seconds = models.FloatField()
    due_at = models.DateTimeField()
    status = models.CharField(max_length=16, default="pending")
    data = models.JSONField(default=dict)
    message = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["due_at", "created_at", "id"]
        indexes = [models.Index(fields=["status", "due_at"], name="map_delay_due"),
                   models.Index(fields=["scene", "status"], name="map_delay_scene")]
        constraints = [models.UniqueConstraint(fields=["element", "name"],
            condition=models.Q(kind="timer", status="pending"), name="map_timer_pending_name")]


class MapAsset(models.Model):
    folder = models.ForeignKey(
        "AssetFolder", null=True, blank=True, on_delete=models.SET_NULL
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE
    )
    generated_for = models.ForeignKey(
        Scene, null=True, blank=True, on_delete=models.CASCADE,
        related_name="generated_builder_assets",
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


class MapBuilderProject(models.Model):
    """Editable cell-based source, kept separate from generated scene resources."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.SET_NULL)
    scene = models.ForeignKey(Scene, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    document = models.JSONField(default=dict)
    generation = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at", "id"]


class BuilderObjectPreset(models.Model):
    """Campaign-owned object bundles with artwork and behavior kept together."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey("gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+")
    name = models.CharField(max_length=120)
    document = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]


class BlueprintTemplate(models.Model):
    """Campaign-owned, parameterized behavior snapshots without instance bindings."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "gravewright_campaigns.Campaign", on_delete=models.CASCADE, related_name="+"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    definition = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]
