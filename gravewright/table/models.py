from django.db import models


class LobbyState(models.Model):
    membership = models.OneToOneField('gravewright_campaigns.Membership', primary_key=True, on_delete=models.CASCADE)
    is_ready = models.BooleanField(default=False)
    selected_actor = models.ForeignKey('gravewright_actors.Actor', null=True, blank=True, on_delete=models.SET_NULL)
    assets_state = models.CharField(max_length=10, default='unknown')
    updated_at = models.DateTimeField(auto_now=True)
