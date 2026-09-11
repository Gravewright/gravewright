"""Deck definitions, reusable image assets and mutable cards in deck instances."""

import uuid
from django.conf import settings
from django.db import models

class Deck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    back = models.FileField(upload_to='cards/backs/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Card(models.Model):
    """Mutable instance moving through draw, hand, scene and discard zones."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deck = models.ForeignKey(Deck, related_name='cards', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    front = models.FileField(upload_to='cards/fronts/', blank=True)
    position = models.PositiveIntegerField(default=0)
    zone = models.CharField(max_length=8, default='draw')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    scene = models.ForeignKey('gravewright_maps.Scene', null=True, on_delete=models.SET_NULL)
    revealed = models.BooleanField(default=False)
    x = models.FloatField(default=0)
    y = models.FloatField(default=0)
    rotation = models.FloatField(default=0)
    scale = models.FloatField(default=1)
    z_index = models.IntegerField(default=0)
    version = models.PositiveIntegerField(default=1)

class CardAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    file = models.FileField(upload_to='cards/assets/')
    purpose = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

class DeckDefinition(models.Model):
    """Reusable deck description whose images can be shared by deck instances."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    cards = models.JSONField(default=list)
    back = models.ForeignKey(CardAsset, null=True, on_delete=models.SET_NULL)
