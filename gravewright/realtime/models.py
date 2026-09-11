import uuid
from django.db import models


class PresenceConnection(models.Model):
    """One renewable lease per socket, not per person."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey('gravewright_campaigns.Membership', on_delete=models.CASCADE,
                                   related_name='connections')
    expires_at = models.DateTimeField(db_index=True)
