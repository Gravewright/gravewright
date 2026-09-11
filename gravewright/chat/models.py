from django.conf import settings
from django.db import models
from django.utils import timezone


class Message(models.Model):
    campaign = models.ForeignKey('gravewright_campaigns.Campaign', on_delete=models.CASCADE,
                                 related_name='chat_messages')
    scene = models.ForeignKey('gravewright_maps.Scene', null=True, blank=True, on_delete=models.CASCADE, related_name='chat_messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    author_name = models.CharField(max_length=80)
    text = models.TextField(max_length=2000)
    visibility = models.CharField(max_length=8, default='public', choices=[('public', 'Public'), ('gm', 'GM'), ('whisper', 'Whisper')])
    roll = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    deleted = models.BooleanField(default=False)
    request_id = models.UUIDField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['campaign', 'author', 'request_id'],
                                                name='chat_unique_submission')]
        indexes = [models.Index(fields=['campaign', 'id'], name='chat_campaign_history')]


class SendWindow(models.Model):
    """Shared flood limit, including across tabs and ASGI processes."""
    membership = models.OneToOneField('gravewright_campaigns.Membership', primary_key=True,
                                      on_delete=models.CASCADE)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()


class Recipient(models.Model):
    message = models.ForeignKey(Message, related_name='recipients', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['message', 'user'], name='chat_unique_recipient')]


class CardAttachment(models.Model):
    """Immutable public face snapshots; never references a mutable deck/card."""
    message = models.ForeignKey(Message, related_name='card_attachments', on_delete=models.CASCADE)
    front = models.FileField(upload_to='chat/cards/', blank=True)
    back = models.FileField(upload_to='chat/cards/', blank=True)
