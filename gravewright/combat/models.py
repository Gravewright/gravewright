from django.db import models
from django.conf import settings

class Encounter(models.Model):
    scene = models.OneToOneField('gravewright_maps.Scene', primary_key=True, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    round = models.PositiveIntegerField(default=0)
    turn = models.PositiveIntegerField(default=0)
    combatants = models.JSONField(default=list)
    history = models.JSONField(default=list)
    config = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)


class InitiativeBatchReceipt(models.Model):
    """Private batch outcomes are isolated from cross-domain command receipts."""
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    scene_id = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'user', 'request_id'],
                                                name='combat_unique_initiative_batch')]
