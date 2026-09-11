from django.db import models

class Encounter(models.Model):
    scene = models.OneToOneField('gravewright_maps.Scene', primary_key=True, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    round = models.PositiveIntegerField(default=0)
    turn = models.PositiveIntegerField(default=0)
    combatants = models.JSONField(default=list)
    history = models.JSONField(default=list)
    config = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
