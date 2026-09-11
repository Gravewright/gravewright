"""Uploaded sounds, reusable playlists and authoritative per-scene playback state."""

import uuid
from django.db import models

class Track(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    file = models.FileField(upload_to='audio/')
    content_type = models.CharField(max_length=80)
    duration = models.FloatField(default=0)
    folder = models.ForeignKey('gravewright_maps.AssetFolder',null=True,blank=True,on_delete=models.SET_NULL)
    kind = models.CharField(max_length=16, default='ambience')
    volume = models.FloatField(default=0.7)
    loop = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

class Playlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    tracks = models.JSONField(default=list)
    mode = models.CharField(max_length=16, default='sequential')
    kind = models.CharField(max_length=12, default='playlist')
    fade = models.FloatField(default=2)
    version = models.PositiveIntegerField(default=1)

class Playback(models.Model):
    """Per-scene transport snapshot; clients derive playback positions from time."""
    scene = models.OneToOneField('gravewright_maps.Scene', primary_key=True, on_delete=models.CASCADE)
    data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
