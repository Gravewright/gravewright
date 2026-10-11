from django.db import models


class DocumentAccess(models.Model):
    """Explicit ownership for resources without a native grants field."""
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    kind = models.CharField(max_length=24)
    resource_id = models.CharField(max_length=120)
    grants = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'kind', 'resource_id'], name='table_unique_document_access')]


class LobbyState(models.Model):
    membership = models.OneToOneField('gravewright_campaigns.Membership', primary_key=True, on_delete=models.CASCADE)
    is_ready = models.BooleanField(default=False)
    selected_actor = models.ForeignKey('gravewright_actors.Actor', null=True, blank=True, on_delete=models.SET_NULL)
    assets_state = models.CharField(max_length=10, default='unknown')
    updated_at = models.DateTimeField(auto_now=True)
