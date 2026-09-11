from django.conf import settings
from django.db import models


class Submission(models.Model):
    """A durable claim prevents retries, tabs or workers from rerolling a request."""
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_id = models.UUIDField()
    expires_at = models.DateTimeField()
    error = models.CharField(max_length=512, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'author', 'request_id'],
                                                name='dice_unique_submission')]
