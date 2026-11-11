import uuid
from django.db import models


class PresenceConnection(models.Model):
    """One renewable lease per socket, not per person."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey('gravewright_campaigns.Membership', on_delete=models.CASCADE,
                                   related_name='connections')
    expires_at = models.DateTimeField(db_index=True)


class CampaignRevision(models.Model):
    """Counts committed refresh envelopes, so sockets can detect one they missed.

    Channel layers drop a group message when a recipient's queue is full; a gap in
    this sequence makes the recipient resynchronize its subscribed projections.
    """
    campaign = models.OneToOneField('gravewright_campaigns.Campaign', on_delete=models.CASCADE,
                                    primary_key=True, related_name='realtime_revision')
    value = models.PositiveBigIntegerField(default=0)
